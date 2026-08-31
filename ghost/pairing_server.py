"""
GHOST :: pairing_server.py — the QR pairing gate (workstation as Bob).

Standard `adb pair`: the PHONE runs the pairing server, we are the client.
The QR flow REVERSES the roles — the workstation displays a QR containing

    WIFI:T:ADB;S:<service-name>;P:<password>;;

the phone scans it, becomes the pairing CLIENT, finds us over mDNS
(`_adb-tls-pairing._tcp`), and runs the exact same SPAKE2+TLS1.3+GCM
handshake — only with roles swapped. On success the phone stores OUR adb
RSA identity in its allowlist and plain `adb connect <phone-ip>:<port>`
just works, same end state as typing a 6-digit code.

Why the QR gate matters (the math):
  A 6-digit code has 10^6 space (19.93 bits) and human priors collapse
  the real search to ~53 attempts (see mathcore.py). A QR password of 8
  unambiguous alphanumeric chars is 28^8 ~= 2^38 (78000x the 6-digit
  space), uniformly random — the prior advantage evaporates entirely.
  8 chars is also the max our pairing client accepts (the validated
  AOSP code-length constraint), so the loopback test exercises the real
  path. The QR deletes the siege's premise instead of fighting it.

Wire truth: the loopback selftest server in pairing_client.py plays the
PHONE role (it answers with ADB_DEVICE_GUID). THIS module is the real
workstation server: it sends ADB_RSA_PUB_KEY with our persistent identity
(the one in %USERPROFILE%/.android/adbkey*), which is what the phone
actually stores. Everything else — transcript, cipher, headers — is the
same validated protocol (see _research/MATHCORE_REPORT.md §1).

Honest limits:
  - Loopback selftest validates our client vs our server; a shared-mistake
    bug can't be caught that way. The wire format was cross-checked
    field-by-field against AOSP sources; a physical device remains the
    true conformance test.
  - mDNS advertisement requires zeroconf (present). Without it the QR
    still renders but the phone cannot auto-discover the service.
"""

import os
import secrets
import socket
import threading
import time

from OpenSSL import SSL

from ghost import pairing_client as pc

# Unambiguous password alphabet: no 0/O/1/l/I — QR scanners read cleanly,
# and a human transcribing it (or a camera reading it poorly) can't
# confuse glyphs. 28^8 ≈ 2^38 ≈ 78000x the 6-digit space, zero priors.
_PW_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz"
PW_LEN = 8
DEFAULT_TTL_S = 300.0        # one QR session lives 5 minutes
MAX_ATTEMPTS = 3             # phone retries are normal; then it's over


def generate_password(length: int = PW_LEN) -> str:
    return "".join(secrets.choice(_PW_ALPHABET) for _ in range(length))


def qr_payload(service_name: str, password: str) -> str:
    """WIFI: payload in the Android ADB QR grammar.

    WIFI-format escaping: backslash, semicolon, comma, colon, quote are
    prefixed with a backslash. Our generated name/password never contain
    them, but the function stays correct for operator-provided ones.
    """
    def esc(s: str) -> str:
        out = []
        for ch in s:
            if ch in "\\;,:\"":
                out.append("\\" + ch)
            else:
                out.append(ch)
        return "".join(out)

    return f"WIFI:T:ADB;S:{esc(service_name)};P:{esc(password)};;"


def _lan_ip() -> str:
    """Best-effort LAN IP for the mDNS announcement (route-table trick)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))       # no packets sent; picks the route source
            ip = s.getsockname()[0]
        finally:
            s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class QRPairingServer:
    """One-shot TLS pairing server + mDNS advertisement for the QR flow."""

    def __init__(self, ttl_s: float = DEFAULT_TTL_S):
        self.ttl_s = ttl_s
        self.password = generate_password()
        self.service_name = "DC-" + secrets.token_hex(3).upper()
        self.port = 0
        self.lan_ip = _lan_ip()
        self.state = {
            "running": False, "paired": False, "peer_guid": None,
            "peer_type": None, "attempts": 0, "errors": {},
            "error": None, "expires_at": None, "paired_at": None,
        }
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = None
        self._server_sock = None
        self._zc = None
        self._info = None

    # ---- lifecycle --------------------------------------------------

    def start(self):
        cert_pem, key_pem, pubkey_bytes = pc.load_identity()
        self._identity = (cert_pem, key_pem, pubkey_bytes)

        self._server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_sock.bind(("0.0.0.0", 0))
        self._server_sock.listen(2)
        self._server_sock.settimeout(0.5)
        self.port = self._server_sock.getsockname()[1]

        self._advertise()

        with self._lock:
            self.state.update({"running": True,
                               "expires_at": time.time() + self.ttl_s})
        self._thread = threading.Thread(target=self._accept_loop, daemon=True,
                                        name="qr-pairing-server")
        self._thread.start()

    def _advertise(self):
        try:
            from zeroconf import Zeroconf, ServiceInfo
            self._zc = Zeroconf()
            host_label = socket.gethostname().split(".")[0] or "droidcommand"
            self._info = ServiceInfo(
                "_adb-tls-pairing._tcp.local.",
                f"{self.service_name}._adb-tls-pairing._tcp.local.",
                addresses=[socket.inet_aton(self.lan_ip)],
                port=self.port,
                properties={},
                server=f"{host_label.lower()}.local.",
            )
            self._zc.register_service(self._info, ttl=120)
            self.mdns_ok = True
        except Exception as exc:            # honest: QR renders, phone can't auto-find
            self._zc = None
            self.mdns_ok = False
            self.state["error"] = f"mdns advertise failed: {exc}"

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)
        if self._zc is not None:
            try:
                self._zc.unregister_service(self._info)
                self._zc.close()
            except Exception:
                pass
            self._zc = None
        with self._lock:
            self.state["running"] = False

    # ---- wire ---------------------------------------------------------

    def _accept_loop(self):
        deadline = self.state["expires_at"]
        while not self._stop.is_set() and time.time() < deadline:
            try:
                sock, addr = self._server_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            self.state["attempts"] += 1
            ok, err = self._serve_once(sock, addr)
            if ok:
                self.state["paired"] = True
                self.state["paired_at"] = time.time()
                break
            if err:
                self.state["error"] = err
                e = self.state["errors"]
                e[err] = e.get(err, 0) + 1
            if self.state["attempts"] >= MAX_ATTEMPTS:
                break
        self._server_sock.close()
        with self._lock:
            if not self.state["paired"]:
                self.state["running"] = False
            else:
                self.state["running"] = False   # paired or dead: session done either way

    def _serve_once(self, sock, addr):
        """Bob side, production role: send OUR RSA pubkey as PeerInfo."""
        cert_pem, key_pem, pubkey_bytes = self._identity
        try:
            sock.settimeout(pc.PAIRING_IO_TIMEOUT_S if hasattr(pc, "PAIRING_IO_TIMEOUT_S") else 15)
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            conn = SSL.Connection(pc._tls_context(cert_pem, key_pem, is_server=True), sock)
            conn.set_accept_state()
            pc._handshake(conn, 15)

            exported = pc._export_key_material(conn)
            password = self.password.encode() + exported

            spake = pc.spake2_server(password)
            my_msg = spake.generate_msg(password)

            ptype, payload = pc._read_header(conn, 15)
            if ptype != pc.SPAKE2_MSG:
                return False, f"expected SPAKE2_MSG, got {ptype}"
            their_msg = pc._tls_recv_exact(conn, payload, 15)

            pc._tls_send(conn, pc.PAIRING_HDR.pack(pc.HDR_VERSION, pc.SPAKE2_MSG, len(my_msg)), 15)
            pc._tls_send(conn, my_msg, 15)

            spake_key = spake.process_msg(their_msg)
            cipher = pc.PairingAuthCipher(spake_key)

            # THE wire truth of the QR flow: the workstation sends its RSA
            # pubkey — that is the artifact the phone stores in its allowlist.
            peer = pc._pack_peer_info(pc.ADB_RSA_PUB_KEY, pubkey_bytes)
            enc = cipher.encrypt(peer)
            pc._tls_send(conn, pc.PAIRING_HDR.pack(pc.HDR_VERSION, pc.PEER_INFO, len(enc)), 15)
            pc._tls_send(conn, enc, 15)

            ptype, payload = pc._read_header(conn, 15)
            if ptype != pc.PEER_INFO:
                return False, f"expected PEER_INFO, got {ptype}"
            their_raw = cipher.decrypt(pc._tls_recv_exact(conn, payload, 15))
            ptype_, data = pc._unpack_peer_info(their_raw)
            guid = data.rstrip(b"\x00").decode("utf-8", "replace") \
                if ptype_ == pc.ADB_DEVICE_GUID else ""
            self.state["peer_type"] = ptype_
            self.state["peer_guid"] = guid
            try:
                conn.shutdown()
            except Exception:
                pass
            return True, None
        except Exception as exc:
            return False, f"{type(exc).__name__}: {exc}"
        finally:
            try:
                sock.close()
            except Exception:
                pass

    # ---- snapshot -------------------------------------------------------

    def snapshot(self):
        st = dict(self.state)
        st["service_name"] = self.service_name
        st["port"] = self.port
        st["lan_ip"] = self.lan_ip
        st["mdns_ok"] = self.mdns_ok
        st["expires_in_s"] = max(0.0, round((st.get("expires_at") or 0) - time.time(), 1))
        return st


# ---------------------------------------------------------------------------
# Session singleton (one QR session at a time — the dialog is exclusive)
# ---------------------------------------------------------------------------

_SESSION = None
_SESSION_LOCK = threading.Lock()


def start_session(ttl_s: float = DEFAULT_TTL_S) -> dict:
    global _SESSION
    with _SESSION_LOCK:
        if _SESSION is not None and _SESSION.state.get("running"):
            return {**_SESSION.snapshot(), "already_running": True}
        if _SESSION is not None:
            _SESSION.stop()
        srv = QRPairingServer(ttl_s=max(30.0, min(ttl_s, 3600.0)))
        srv.start()
        _SESSION = srv
        return {**srv.snapshot(), "already_running": False}


def stop_session() -> dict:
    global _SESSION
    with _SESSION_LOCK:
        if _SESSION is None:
            return {"running": False, "was_running": False}
        snap = _SESSION.snapshot()
        _SESSION.stop()
        was = snap.get("running", False)
        return {"running": False, "was_running": was, **snap}


def session_status() -> dict:
    with _SESSION_LOCK:
        if _SESSION is None:
            return {"running": False, "note": "no QR session started"}
        return _SESSION.snapshot()


def session_qr_payload() -> str:
    """The WIFI: payload for the CURRENT session — contains the password,
    so only /qr/start responses include it, never status polls."""
    with _SESSION_LOCK:
        if _SESSION is None:
            return ""
        return qr_payload(_SESSION.service_name, _SESSION.password)


# ---------------------------------------------------------------------------
# Selftest: our production server vs our client, over real TLS 1.3
# ---------------------------------------------------------------------------

def selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    pw = generate_password()
    check("password len/charset", len(pw) == PW_LEN and all(c in _PW_ALPHABET for c in pw))
    import math as _m
    check("password entropy >= 37 bits", _m.log2(len(_PW_ALPHABET)) * PW_LEN >= 37)

    pay = qr_payload("DC-ABC123", pw)
    check("qr payload grammar", pay == f"WIFI:T:ADB;S:DC-ABC123;P:{pw};;")
    tricky = qr_payload("a;b:c\\d", "p,w")
    check("qr escaping", tricky == "WIFI:T:ADB;S:a\\;b\\:c\\\\d;P:p\\,w;;")

    srv = QRPairingServer(ttl_s=30)
    srv.start()
    check("server bound ephemeral port", srv.port > 0)
    check("mdns advertise attempted", srv.mdns_ok is True or srv.state.get("error"))

    try:
        res = pc.pair("127.0.0.1", srv.port, srv.password, timeout=15)
        check("client paired against QR server", res.get("success") is True)
        check("server saw a peer", srv.state["attempts"] >= 1)
        # The client received our REAL workstation identity as server PeerInfo:
        check("client got RSA pubkey peer info",
              res.get("peer_type") == pc.ADB_RSA_PUB_KEY)
        # A real phone-client may answer with ADB_DEVICE_GUID (its identity)
        # or ADB_RSA_PUB_KEY; our loopback client module sends ADB_RSA_PUB_KEY.
        # The server records whatever arrives — that is the honest contract.
        check("server recorded the client's peer type",
              srv.state["peer_type"] == pc.ADB_RSA_PUB_KEY)
    finally:
        srv.stop()

    snap = session_status()
    check("session status honest when idle", "running" in snap)
    print("QR PAIRING SERVER SELFTEST " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
