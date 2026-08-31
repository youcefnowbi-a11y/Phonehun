"""GHOST spake25519 — faithful pure-Python port of BoringSSL crypto/curve25519/spake25519.c
as pinned by Android (external/boringssl, curve25519 dir), which is what adbd's pairing
server actually runs.

Ground truth (fetched to DroidCommand/_research/aosp/):
  - spake25519.c            : SPAKE2 over edwards25519, password-scalar "hack", SHA-512 transcript
  - spake25519_test.cc      : round-trip / wrong-password / wrong-names / corrupt-bit properties
  - pairing_auth.cpp        : names "adb pair client"/"adb pair server" WITH NUL (sizeof), 16 bytes
  - aes_128_gcm.cpp         : HKDF-SHA256 -> AES-128-GCM, LE-seq nonces (see pairing_client.py)

Port notes (exact semantics, not approximations):
  - x25519_sc_reduce(b64)        == int.from_bytes(b,'little') % ORDER -> 32B LE
  - left_shift_3(b32)            == scalar * 8 (no wraparound: reduced < ORDER < 2**253)
  - password scalar "hack"       == three SEQUENTIAL conditional adds of ORDER, 2*ORDER,
                                    4*ORDER checking bits of the *running* scalar
                                    (NOT equivalent to s + (s&7)*ORDER: each add feeds
                                    the next check, so e.g. s == 1 mod 8 adds 3*ORDER
                                    while s+(s&7)*ORDER would add only 1*ORDER. The dance
                                    always terminates with (s & 7) == 0 because it clears
                                    the low 3 bits of the running scalar — we replicate
                                    the C verbatim and assert (s & 7) == 0 like it does)
  - M / N                        == hardcoded compressed edwards points from the C source header
  - transcript                   == SHA512 over 8-byte-LE length-prefixed fields
  - key                          == full 64-byte SHA512 digest (adb uses it as HKDF input)
"""

import hashlib
import os

# ---------------------------------------------------------------- curve

P = 2**255 - 19
ORDER = 2**252 + 27742317777372353535851937790883648493
D = (-121665 * pow(121666, P - 2, P)) % P
SQRT_M1 = pow(2, (P - 1) // 4, P)  # 2^((p-1)/4) mod p == sqrt(-1)

# ed25519 base point
_BX = 15112221349535400772501151409588531511454012693041857206046113283949847762202
_BY = 46316835694926478169428394003475163141307993866256225615783033603165251855960
BASE = (_BX % P, _BY % P)

# BoringSSL SPAKE2 generator points (encoded edwards, from spake25519.c header comment)
M_ENCODED = bytes.fromhex("5ada7e4bf6ddd9adb6626d32131c6b5c51a1e347a3478f53cfcf441b88eed12e")
N_ENCODED = bytes.fromhex("10e3df0ae37d8e7a99b5fe74b44672103dbddcbd06af680d71329a11693bc778")


def _x_recover(y):
    """Recover x from y (RFC 8032 §5.1.3 step 2-4). Returns None if not on curve."""
    xx = (y * y - 1) * pow(D * y * y + 1, P - 2, P) % P
    x = pow(xx, (P + 3) // 8, P)
    if (x * x - xx) % P != 0:
        x = x * SQRT_M1 % P
    if (x * x - xx) % P != 0:
        return None
    return x


def point_decode(encoded):
    """Decode a 32-byte compressed edwards25519 point. None if invalid."""
    if len(encoded) != 32:
        return None
    y = int.from_bytes(encoded, "little") & ((1 << 255) - 1)
    x_sign = encoded[31] >> 7
    if y >= P:
        return None
    x = _x_recover(y)
    if x is None:
        return None
    if x == 0 and x_sign == 1:
        return None  # BoringSSL frombytes_vartime rejects x=0 with negative bit
    if x & 1 != x_sign:
        x = P - x
    return (x, y)


def point_encode(pt):
    """Compress a point (affine or extended) into 32-byte edwards encoding (y LE + sign of x)."""
    x, y = to_affine(pt)
    out = bytearray(y.to_bytes(32, "little"))
    out[31] |= (x & 1) << 7
    return bytes(out)


IDENTITY = (0, 1)  # affine identity, used by public API


def point_add(p1, p2):
    """Extended-coordinate unified addition (RFC 8032 §5.1.4, a=-1).
    Internal points are (X, Y, Z, T); affine tuples are converted on entry."""
    if p1 is None:
        return p2
    if p2 is None:
        return p1
    X1, Y1, Z1, T1 = p1 if len(p1) == 4 else (*p1, 1, p1[0] * p1[1] % P)
    X2, Y2, Z2, T2 = p2 if len(p2) == 4 else (*p2, 1, p2[0] * p2[1] % P)

    A = (Y1 - X1) * (Y2 - X2) % P
    B = (Y1 + X1) * (Y2 + X2) % P
    C = T1 * 2 * D * T2 % P
    Dc = Z1 * 2 * Z2 % P
    E = B - A
    F = Dc - C
    G = Dc + C
    H = B + A
    return (E * F % P, G * H % P, F * G % P, E * H % P)


def point_neg(pt):
    if pt is None or len(pt) == 2:
        x, y = pt
        return ((P - x) % P, y)
    X, Y, Z, T = pt
    return ((P - X) % P, Y, Z, (P - T) % P)


def point_sub(a, b):
    return point_add(a, point_neg(b))


def point_double(pt):
    """Extended doubling (RFC 8032 §5.1.4 dbl-2008-hwcd)."""
    X1, Y1, Z1, T1 = pt if len(pt) == 4 else (*pt, 1, pt[0] * pt[1] % P)
    A = X1 * X1 % P
    B = Y1 * Y1 % P
    C = 2 * Z1 * Z1 % P
    H = (A + B) % P
    E = (H - (X1 + Y1) * (X1 + Y1)) % P
    G = (A - B) % P
    F = (C + G) % P
    return (E * F % P, G * H % P, F * G % P, E * H % P)


def point_mult(scalar, pt):
    """Scalar multiplication, double-and-add (MSB-first). scalar: non-negative int.
    Accepts affine or extended input; returns extended coordinates."""
    result = (0, 1, 1, 0)
    addend = pt if len(pt) == 4 else (pt[0], pt[1], 1, pt[0] * pt[1] % P)
    while scalar:
        if scalar & 1:
            result = point_add(result, addend)
        addend = point_double(addend)
        scalar >>= 1
    return result


def to_affine(pt):
    """Extended (X, Y, Z, T) -> affine (x, y)."""
    if len(pt) == 2:
        return pt
    X, Y, Z, _ = pt
    if Z == 0:
        return IDENTITY
    zinv = pow(Z, P - 2, P)
    return (X * zinv % P, Y * zinv % P)


def sc_reduce(b64):
    """x25519_sc_reduce: reduce 64-byte LE input mod ORDER -> 32-byte LE."""
    return (int.from_bytes(b64, "little") % ORDER).to_bytes(32, "little")


# ---------------------------------------------------------------- SPAKE2

CLIENT_NAME = b"adb pair client\x00"  # kClientName, sizeof includes NUL -> 16 bytes
SERVER_NAME = b"adb pair server\x00"  # kServerName, sizeof includes NUL -> 16 bytes

SPAKE2_MAX_MSG_SIZE = 32
SPAKE2_MAX_KEY_SIZE = 64


class Spake2Ctx:
    """Port of BoringSSL SPAKE2_CTX (spake25519.c), with disable_password_scalar_hack."""

    def __init__(self, role_alice, my_name, their_name, disable_password_scalar_hack=False):
        self.role_alice = bool(role_alice)
        if not 0 < len(my_name) <= 255 or not 0 < len(their_name) <= 255:
            raise ValueError("SPAKE2 name lengths must be 1..255")
        self.my_name = my_name
        self.their_name = their_name
        self.disable_hack = bool(disable_password_scalar_hack)
        self.state = "init"
        self.private_key = 0
        self.password_hash = b""
        self.password_scalar = 0
        self.my_msg = b"\x00" * 32

    def generate_msg(self, password):
        """SPAKE2_generate_msg -> 32-byte SPAKE2 message."""
        if self.state != "init":
            raise RuntimeError("SPAKE2 state error: generate_msg after use")

        # private_tmp = RAND_bytes(64); sc_reduce; left_shift_3
        private_tmp = os.urandom(64)
        private_tmp = sc_reduce(private_tmp)
        private_int = int.from_bytes(private_tmp, "little") * 8  # left_shift_3, no wraparound
        self.private_key = private_int

        # P = [private] * B
        base_pt = point_mult(private_int, BASE)

        # password_hash = SHA512(password); password_scalar = sc_reduce(password_hash)
        pw_hash = hashlib.sha512(password).digest()
        self.password_hash = pw_hash
        pw_scalar = int.from_bytes(sc_reduce(pw_hash), "little")

        # the copy-paste-fix: three sequential conditional order-adds
        if not self.disable_hack:
            order = ORDER
            if pw_scalar & 1:
                pw_scalar += order
            order *= 2
            if pw_scalar & 2:
                pw_scalar += order
            order *= 2
            if pw_scalar & 4:
                pw_scalar += order
            assert (pw_scalar & 7) == 0, "password scalar hack must clear low 3 bits"
        self.password_scalar = pw_scalar

        # mask = [password_scalar] * (M if alice else N)
        gen = point_decode(M_ENCODED if self.role_alice else N_ENCODED)
        if gen is None:
            raise RuntimeError("internal: SPAKE2 generator point failed to decode")
        mask = point_mult(pw_scalar, gen)

        # P* = P + mask, encode
        pstar = point_add(base_pt, mask)
        self.my_msg = point_encode(pstar)
        self.state = "msg_generated"
        return self.my_msg

    def process_msg(self, their_msg):
        """SPAKE2_process_msg -> shared key (<= 64 bytes; adb uses the full 64)."""
        if self.state != "msg_generated":
            raise RuntimeError("SPAKE2 state error: process_msg before generate_msg")
        if len(their_msg) != 32:
            raise ValueError("SPAKE2 peer msg must be 32 bytes")

        qstar = point_decode(their_msg)
        if qstar is None:
            raise ValueError("SPAKE2 peer msg is not a valid curve point")

        # peers_mask = [password_scalar] * (N if alice else M)
        gen = point_decode(N_ENCODED if self.role_alice else M_ENCODED)
        if gen is None:
            raise RuntimeError("internal: SPAKE2 generator point failed to decode")
        peers_mask = point_mult(self.password_scalar, gen)

        # Q = Qstar - peers_mask; dh = [private_key] * Q
        q_ext = point_sub(qstar, peers_mask)
        dh_pt = point_mult(self.private_key, q_ext)
        dh_encoded = point_encode(dh_pt)

        # SHA512 over 8-byte-LE length-prefixed transcript
        sha = hashlib.sha512()

        def upd(data):
            sha.update(len(data).to_bytes(8, "little"))
            sha.update(data)

        if self.role_alice:
            upd(self.my_name)
            upd(self.their_name)
            upd(self.my_msg)
            upd(their_msg)
        else:
            upd(self.their_name)
            upd(self.my_name)
            upd(their_msg)
            upd(self.my_msg)
        upd(dh_encoded)
        upd(self.password_hash)

        key = sha.digest()  # 64 bytes; adb copies min(64, max_out) = 64
        self.state = "key_generated"
        return key


def spake2_client(password):
    """Client-side SPAKE2 (adb pair client == alice), as used by pairing_auth_client_new."""
    return Spake2Ctx(True, CLIENT_NAME, SERVER_NAME)


def spake2_server(password=None):
    """Server-side SPAKE2 (adb pair server == bob), for loopback replicas/tests."""
    return Spake2Ctx(False, SERVER_NAME, CLIENT_NAME)
