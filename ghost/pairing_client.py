"""GHOST pairing_client — real Android WiFi-pairing client (SPAKE2 + TLS 1.3).

Speaks the exact wire protocol of AOSP pairing_connection.cpp + pairing_auth.cpp +
aes_128_gcm.cpp (sources pinned in _research/aosp/):

  1. TCP connect (10s timeout, TCP_NODELAY)
  2. TLS 1.3 handshake, client presents adb-identity cert (peer cert NOT verified —
     the PAKE is the authentication; SetCertVerifyCallback([](X509_STORE_CTX*){return 1;}))
  3. export_keying_material(64, "adb-label\\0" INCLUDING NUL via sizeof, context=none)
  4. spake password = 6-digit code bytes ++ 64-byte exporter output   (70 bytes)
  5. SPAKE2 exchange: both sides send header+msg then read header+msg
     PairingPacketHeader (6 bytes): version=1 | type | payload uint32 BIG-ENDIAN (htonl)
     type 0 = SPAKE2_MSG (32B), type 1 = PEER_INFO (encrypted 8192B slab)
  6. PairingAuth cipher: HKDF-SHA256(spake_key 64B, salt=none,
     info="adb pairing_auth aes-128-gcm key") -> 16B AES-128-GCM key;
     nonce = 12B, first 8B = LE uint64 counter (separate enc/dec counters from 0)
  7. PeerInfo (8192 bytes): type uint8 + data[8191]; client sends ADB_RSA_PUB_KEY(0)
     with its adb public key; device replies ADB_DEVICE_GUID(1) with its GUID.
  8. Success => device stores OUR certificate pubkey in its ADB KEYS allowlist
     => `adb connect <ip>:<wifi-port>` immediately works with stock adb identity.

Self-test (loopback, no phone):  python -m ghost.pairing_client
"""

import datetime as _dt
import os
import socket
import struct
import sys
import threading
import time
import traceback
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.x509.oid import NameOID
from OpenSSL import SSL, crypto

from .spake25519 import spake2_client, spake2_server

# ---------------------------------------------------------------- constants

PAIRING_HDR = struct.Struct(">BBI")  # version, type, payload (htonl -> big-endian)
HDR_VERSION = 1
SPAKE2_MSG = 0
PEER_INFO = 1
K_MAX_PEER_INFO_SIZE = 8192
K_MAX_PAYLOAD_SIZE = K_MAX_PEER_INFO_SIZE * 2
K_EXPORTED_KEY_SIZE = 64
EXPORT_LABEL = b"adb-label\x00"  # sizeof(kExportedKeyLabel) INCLUDES the NUL — critical
AESGCM_INFO = b"adb pairing_auth aes-128-gcm key"
ADB_RSA_PUB_KEY = 0
ADB_DEVICE_GUID = 1

ADB_KEY_PATH = Path(os.environ.get("USERPROFILE", "")) / ".android" / "adbkey"
ADB_PUB_KEY_PATH = ADB_KEY_PATH.with_suffix(".pub")


# ---------------------------------------------------------------- identity

_cert_cache = None


def load_identity():
    """Load adb identity key, mint self-signed X.509 (adb stores no cert file).
    Returns (cert_pem, key_pem, pubkey_bytes)."""
    global _cert_cache
    if _cert_cache is not None:
        return _cert_cache

    key_path = Path(str(ADB_KEY_PATH))
    if not key_path.exists():
        raise FileNotFoundError(f"adb identity key not found: {key_path}")
    priv = serialization.load_pem_private_key(key_path.read_bytes(), password=None)

    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "droidcommand")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(priv.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _dt.timedelta(days=1))
        .not_valid_after(now + _dt.timedelta(days=20 * 365))
        .sign(priv, hashes.SHA256())
    )
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    key_pem = priv.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.TraditionalOpenSSL,
        serialization.NoEncryption(),
    )
    pub_path = Path(str(ADB_PUB_KEY_PATH))
    pubkey_bytes = pub_path.read_bytes() if pub_path.exists() else b"droidcommand"
    _cert_cache = (cert_pem, key_pem, pubkey_bytes)
    return _cert_cache


def _make_server_identity():
    """Fresh throwaway RSA identity for the loopback test server."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = _dt.datetime.now(_dt.timezone.utc).replace(tzinfo=None)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "ghost-loopback")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(priv.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - _dt.timedelta(days=1))
        .not_valid_after(now + _dt.timedelta(days=365))
        .sign(priv, hashes.SHA256())
    )
    return (
        cert.public_bytes(serialization.Encoding.PEM),
        priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,
            serialization.NoEncryption(),
        ),
    )


# ---------------------------------------------------------------- cipher

class PairingAuthCipher:
    """Port of pairing_auth Aes128Gcm + PairingAuthCtx key/cipher wiring."""

    def __init__(self, spake_key: bytes):
        self.key = HKDF(
            algorithm=hashes.SHA256(),
            length=16,
            salt=None,
            info=AESGCM_INFO,
        ).derive(spake_key)
        self.aead = AESGCM(self.key)
        self.enc_seq = 0
        self.dec_seq = 0

    def _nonce(self, seq: int) -> bytes:
        # 12-byte zero buffer; first 8 bytes = LE uint64 sequence counter
        return seq.to_bytes(8, "little") + b"\x00" * 4

    def encrypt(self, plaintext: bytes) -> bytes:
        # Aes128Gcm::Encrypt -> ciphertext || 16B tag (AESGCM.encrypt emits exactly this)
        out = self.aead.encrypt(self._nonce(self.enc_seq), plaintext, None)
        self.enc_seq += 1
        return out

    def decrypt(self, ciphertext: bytes) -> bytes:
        out = self.aead.decrypt(self._nonce(self.dec_seq), ciphertext, None)
        self.dec_seq += 1
        return out


# ---------------------------------------------------------------- tls helpers

def _tls_context(cert_pem: bytes, key_pem: bytes, is_server: bool):
    ctx = SSL.Context(SSL.TLS_SERVER_METHOD if is_server else SSL.TLS_CLIENT_METHOD)
    ctx.set_min_proto_version(SSL.TLS1_3_VERSION)
    ctx.set_max_proto_version(SSL.TLS1_3_VERSION)
    # modern pyOpenSSL constructors (deprecated load_certificate/load_privatekey avoided)
    cert_obj = crypto.X509.from_cryptography(
        x509.load_pem_x509_certificate(cert_pem)
    )
    key_obj = crypto.PKey.from_cryptography_key(
        serialization.load_pem_private_key(key_pem, password=None)
    )
    ctx.use_certificate(cert_obj)
    ctx.use_privatekey(key_obj)
    # AOSP: SetCertVerifyCallback([](X509_STORE_CTX*) { return 1; }) — accept any cert
    ctx.set_verify(SSL.VERIFY_NONE, lambda conn, x509, err, depth, ok: True)
    return ctx


def _handshake(conn: SSL.Connection, timeout: float = 10.0):
    """pyOpenSSL + timeout-mode sockets: do_handshake surfaces WantRead/WantWrite
    instead of blocking (TLS 1.3 multi-flight). Retry until done or deadline."""
    deadline = time.time() + timeout
    while True:
        try:
            conn.do_handshake()
            return
        except (SSL.WantReadError, SSL.WantWriteError):
            if time.time() > deadline:
                raise TimeoutError("TLS handshake deadline exceeded")
            time.sleep(0.001)
        except SSL.ZeroReturnError:
            raise ConnectionError("peer closed during TLS handshake")


def _tls_send(conn: SSL.Connection, data: bytes, timeout: float = 10.0):
    deadline = time.time() + timeout
    while True:
        try:
            conn.sendall(data)
            return
        except (SSL.WantReadError, SSL.WantWriteError):
            if time.time() > deadline:
                raise TimeoutError("TLS send deadline exceeded")
            time.sleep(0.001)


def _tls_recv_exact(conn: SSL.Connection, n: int, timeout: float = 10.0) -> bytes:
    deadline = time.time() + timeout
    chunks = []
    got = 0
    while got < n:
        try:
            chunk = conn.recv(n - got)
        except (SSL.WantReadError, SSL.WantWriteError):
            if time.time() > deadline:
                raise TimeoutError("TLS recv deadline exceeded")
            time.sleep(0.001)
            continue
        if not chunk:
            raise ConnectionError("peer closed during TLS read")
        chunks.append(chunk)
        got += len(chunk)
    return b"".join(chunks)


def _read_header(conn: SSL.Connection, timeout: float = 10.0):
    raw = _tls_recv_exact(conn, PAIRING_HDR.size, timeout)
    version, ptype, payload = PAIRING_HDR.unpack(raw)
    if version != HDR_VERSION:
        raise ValueError(f"bad pairing header version {version}")
    if ptype not in (SPAKE2_MSG, PEER_INFO):
        raise ValueError(f"bad pairing packet type {ptype}")
    if payload == 0 or payload > K_MAX_PAYLOAD_SIZE:
        raise ValueError(f"bad payload size {payload}")
    return ptype, payload


def _export_key_material(conn: SSL.Connection) -> bytes:
    # AOSP: SSL_export_keying_material(ssl, out, 64, "adb-label\0", 10, NULL, 0, false)
    # pyOpenSSL 26 signature: export_keying_material(label, olen, context=None)
    material = conn.export_keying_material(EXPORT_LABEL, K_EXPORTED_KEY_SIZE, None)
    if not material or len(material) != K_EXPORTED_KEY_SIZE:
        raise RuntimeError("export_keying_material failed")
    return material


# ---------------------------------------------------------------- pack/unpack

def _pack_peer_info(ptype: int, data: bytes) -> bytes:
    if len(data) > K_MAX_PEER_INFO_SIZE - 1:
        data = data[: K_MAX_PEER_INFO_SIZE - 1]
    return bytes([ptype]) + data + b"\x00" * (K_MAX_PEER_INFO_SIZE - 1 - len(data))


def _unpack_peer_info(raw: bytes):
    if len(raw) != K_MAX_PEER_INFO_SIZE:
        raise ValueError(f"PeerInfo size mismatch: got {len(raw)}")
    return raw[0], raw[1:]


# ---------------------------------------------------------------- client

def pair(host: str, port: int, code: str, timeout: float = 10.0) -> dict:
    """Run the full pairing flow against an Android device pairing server.
    Returns dict with guid/peer type on success; raises on failure."""
    code_bytes = code.strip().encode("ascii")
    if not 1 <= len(code_bytes) <= 8:
        raise ValueError("pairing code must be 1-8 ascii chars (device shows 6)")

    cert_pem, key_pem, pubkey_bytes = load_identity()

    sock = socket.create_connection((host, int(port)), timeout=timeout)
    sock.settimeout(timeout)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    conn = None
    try:
        ctx = _tls_context(cert_pem, key_pem, is_server=False)
        conn = SSL.Connection(ctx, sock)
        conn.set_connect_state()
        _handshake(conn, timeout)

        exported = _export_key_material(conn)
        password = code_bytes + exported  # MITM binding: PAKE password tied to TLS session

        spake = spake2_client(password)
        my_msg = spake.generate_msg(password)

        # send our SPAKE2 msg, then read theirs (both sides send-first, full duplex)
        _tls_send(conn, PAIRING_HDR.pack(HDR_VERSION, SPAKE2_MSG, len(my_msg)), timeout)
        _tls_send(conn, my_msg, timeout)

        ptype, payload = _read_header(conn, timeout)
        if ptype != SPAKE2_MSG:
            raise ValueError(f"expected SPAKE2_MSG, got type {ptype}")
        their_msg = _tls_recv_exact(conn, payload, timeout)

        spake_key = spake.process_msg(their_msg)
        cipher = PairingAuthCipher(spake_key)

        # encrypted PeerInfo exchange (whole 8192B slab)
        peer_info = _pack_peer_info(ADB_RSA_PUB_KEY, pubkey_bytes)
        enc = cipher.encrypt(peer_info)
        _tls_send(conn, PAIRING_HDR.pack(HDR_VERSION, PEER_INFO, len(enc)), timeout)
        _tls_send(conn, enc, timeout)

        ptype, payload = _read_header(conn, timeout)
        if ptype != PEER_INFO:
            raise ValueError(f"expected PEER_INFO, got type {ptype}")
        enc_their = _tls_recv_exact(conn, payload, timeout)
        their_raw = cipher.decrypt(enc_their)
        their_type, their_data = _unpack_peer_info(their_raw)

        guid = their_data.rstrip(b"\x00").decode("utf-8", "replace") if their_type == ADB_DEVICE_GUID else ""
        return {
            "success": True,
            "peer_type": their_type,
            "guid": guid,
            "device_stored_cert": True,
        }
    finally:
        if conn is not None:
            try:
                conn.shutdown()
            except Exception:
                pass
        try:
            sock.close()
        except Exception:
            pass


def pair_async(host: str, port: int, code: str, timeout: float = 10.0):
    """Run pair() on a worker thread; returns (result_dict, error_str)."""
    out = {}

    def _run():
        try:
            out["result"] = pair(host, port, code, timeout)
        except Exception as exc:  # honest error taxonomy to the panel
            out["error"] = f"{type(exc).__name__}: {exc}"
            out["traceback"] = traceback.format_exc()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout + 5)
    if "error" in out:
        return None, out["error"]
    if "result" not in out:
        return None, "pairing timed out"
    return out["result"], None


# ---------------------------------------------------------------- loopback server (self-test)

def _server_once(server_sock, code: str, results: dict):
    """Bob-side replica of pairing_connection.cpp (server role) for loopback tests."""
    cert_pem, key_pem = _make_server_identity()
    sock, _ = server_sock.accept()
    sock.settimeout(10)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    conn = SSL.Connection(_tls_context(cert_pem, key_pem, is_server=True), sock)
    conn.set_accept_state()
    _handshake(conn)

    exported = _export_key_material(conn)
    password = code.encode() + exported
    spake = spake2_server(password)
    my_msg = spake.generate_msg(password)

    ptype, payload = _read_header(conn)
    assert ptype == SPAKE2_MSG, "server: expected SPAKE2_MSG"
    their_msg = _tls_recv_exact(conn, payload)

    _tls_send(conn, PAIRING_HDR.pack(HDR_VERSION, SPAKE2_MSG, len(my_msg)))
    _tls_send(conn, my_msg)

    spake_key = spake.process_msg(their_msg)
    results["server_key"] = spake_key
    cipher = PairingAuthCipher(spake_key)

    ptype, payload = _read_header(conn)
    assert ptype == PEER_INFO, "server: expected PEER_INFO"
    their_raw = cipher.decrypt(_tls_recv_exact(conn, payload))
    t, d = _unpack_peer_info(their_raw)
    results["client_peer_type"] = t
    results["client_pubkey_head"] = d[:24]

    guid = f"ghost-loopback-{os.getpid():08d}"
    enc = cipher.encrypt(_pack_peer_info(ADB_DEVICE_GUID, guid.encode()))
    _tls_send(conn, PAIRING_HDR.pack(HDR_VERSION, PEER_INFO, len(enc)))
    _tls_send(conn, enc)

    conn.shutdown()
    sock.close()


def selftest() -> int:
    """Full-stack loopback: our client vs our bob replica over real TLS 1.3."""
    code = "314159"
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    results = {}
    th = threading.Thread(target=_server_once, args=(server_sock, code, results), daemon=True)
    th.start()
    time.sleep(0.15)

    try:
        res = pair("127.0.0.1", port, code, timeout=15)
    except Exception:
        traceback.print_exc()
        server_sock.close()
        return 1
    th.join(10)
    server_sock.close()
    if not res.get("success"):
        print("FAIL: client reports no success")
        return 1
    if res.get("peer_type") != ADB_DEVICE_GUID:
        print(f"FAIL: expected device GUID type {ADB_DEVICE_GUID}, got {res.get('peer_type')}")
        return 1
    if not res.get("guid", "").startswith("ghost-loopback-"):
        print(f"FAIL: guid roundtrip broken: {res.get('guid')!r}")
        return 1
    if results.get("client_peer_type") != ADB_RSA_PUB_KEY:
        print("FAIL: server did not see ADB_RSA_PUB_KEY from client")
        return 1
    pub = load_identity()[2]
    if results.get("client_pubkey_head") != pub[:24]:
        print("FAIL: server saw different pubkey than adbkey.pub")
        return 1

    # wrong-code must FAIL (GCM tag / PAKE mismatch surfaces as decrypt or value error)
    server_sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock2.bind(("127.0.0.1", 0))
    server_sock2.listen(1)
    port2 = server_sock2.getsockname()[1]
    results2 = {}
    th2 = threading.Thread(target=_server_once, args=(server_sock2, code, results2), daemon=True)
    th2.start()
    time.sleep(0.15)
    res2, err2 = pair_async("127.0.0.1", port2, "999999", timeout=15)
    th2.join(10)
    server_sock2.close()
    if res2 is not None:
        print("FAIL: wrong code paired successfully?!")
        return 1
    print(f"wrong-code correctly rejected: {err2}")

    print("\nSELFTEST PASSED — full TLS 1.3 + SPAKE2 + GCM PeerInfo exchange round-trips")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())
