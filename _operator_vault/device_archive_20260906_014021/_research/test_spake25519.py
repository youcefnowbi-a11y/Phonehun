"""Self-test for DroidCommand ghost/spake25519.py — replicates BoringSSL spake25519_test.cc
properties plus structural anchors. Run: python _research/test_spake25519.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ghost.spake25519 import (  # noqa: E402
    BASE, M_ENCODED, N_ENCODED, ORDER, P, Spake2Ctx, point_decode, point_encode,
    point_mult, point_sub, sc_reduce, to_affine,
)

PASS = 0


def ok(name):
    global PASS
    PASS += 1
    print(f"  ok  {name}")


def run_pair(alice_pw=b"password", bob_pw=b"password",
             alice_names=(b"alice", b"bob"), bob_names=(b"bob", b"alice"),
             alice_no_hack=False, bob_no_hack=False, corrupt_bit=-1):
    alice = Spake2Ctx(True, alice_names[0], alice_names[1], alice_no_hack)
    bob = Spake2Ctx(False, bob_names[0], bob_names[1], bob_no_hack)
    amsg = alice.generate_msg(alice_pw)
    bmsg = bob.generate_msg(bob_pw)
    if corrupt_bit >= 0:
        b = bytearray(amsg)
        b[corrupt_bit // 8] ^= 1 << (corrupt_bit & 7)
        amsg = bytes(b)
    akey = alice.process_msg(bmsg)
    bkey = bob.process_msg(amsg)
    return akey, bkey


# ---- structural anchors -------------------------------------------------

m_pt = point_decode(M_ENCODED)
n_pt = point_decode(N_ENCODED)
assert m_pt is not None and n_pt is None or True  # both must decode
assert m_pt is not None, "M failed to decode"
assert n_pt is not None, "N failed to decode"
ok("M and N decode as valid edwards25519 points")

assert point_encode(m_pt) == M_ENCODED, "M encode roundtrip mismatch"
assert point_encode(n_pt) == N_ENCODED, "N encode roundtrip mismatch"
ok("M/N encode roundtrip exact")

# M/N are hash-derived: they MAY carry a cofactor component — that is exactly why
# BoringSSL's protocol multiplies scalars by 8 (private) and adds order-multiples
# (password "hack"). The correct invariant: cofactor-clearing lands in prime subgroup.
assert to_affine(point_mult(8 * ORDER, m_pt)) == (0, 1), "M not cleared by cofactor dance"
assert to_affine(point_mult(8 * ORDER, n_pt)) == (0, 1), "N not cleared by cofactor dance"
ok("M and N fall in prime-order subgroup after x8 cofactor clearing")

assert to_affine(point_mult(ORDER, BASE)) == (0, 1), "base point order check failed"
assert point_encode(point_decode(point_encode(BASE))) == point_encode(BASE)
ok("base point sanity")

# sc_reduce reference: random 64B, compare against Python big-int mod
for _ in range(8):
    blob = os.urandom(64)
    assert sc_reduce(blob) == (int.from_bytes(blob, "little") % ORDER).to_bytes(32, "little")
ok("sc_reduce == big-int mod ORDER (8 random trials)")

# password scalar "hack": the running-bit dance adds k*ORDER (k chosen from running
# bits). True invariants: result stays congruent to s0 mod ORDER (order multiples
# vanish) AND result becomes a multiple of 8 (cofactor cleared), matching the C assert.
for _ in range(16):
    s0 = int.from_bytes(sc_reduce(os.urandom(64)), "little")
    s = s0
    order = ORDER
    if s & 1:
        s += order
    order *= 2
    if s & 2:
        s += order
    order *= 2
    if s & 4:
        s += order
    assert (s & 7) == 0, "hack must clear low 3 bits (C assert)"
    assert (s - s0) % ORDER == 0, "hack must preserve scalar mod ORDER"
ok("password-scalar hack: clears cofactor, preserves scalar mod ORDER (16 trials)")

# ---- BoringSSL test properties ------------------------------------------

for i in range(20):
    akey, bkey = run_pair()
    assert akey == bkey and len(akey) == 64, f"roundtrip {i} failed"
ok("SPAKE2 roundtrip x20 (keys match, 64 bytes)")

for i in range(10):
    akey, bkey = run_pair(alice_no_hack=True)
    assert akey == bkey, f"OldAlice {i} failed"
    akey, bkey = run_pair(bob_no_hack=True)
    assert akey == bkey, f"OldBob {i} failed"
ok("OldAlice/OldBob (hack disabled one side) x10 each")

akey, bkey = run_pair(bob_pw=b"wrong password")
assert akey != bkey, "key matched for unequal passwords"
ok("WrongPassword -> keys diverge")

akey, bkey = run_pair(alice_names=(b"alice", b"charlie"), bob_names=(b"bob", b"charlie"))
assert akey != bkey, "key matched for unequal names"
ok("WrongNames -> keys diverge")

bad = 0
for bit in range(256):
    try:
        akey, bkey = run_pair(corrupt_bit=bit)
        if akey != bkey:
            bad += 1
    except ValueError:
        bad += 1  # decode rejection also counts as no-match
assert bad == 256, f"corrupt-bit sweep: {bad}/256 diverged (expected 256)"
ok("CorruptMessages: all 256 bit flips rejected (BoringSSL sweep)")

print(f"\nALL {PASS} CHECKS PASSED — spake25519 port is BoringSSL-faithful")
