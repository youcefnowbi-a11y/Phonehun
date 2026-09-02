# -*- coding: utf-8 -*-
"""h264core.pyd first-breath probe: import, parity of errors, roundtrip."""
import sys
import h264core

print("module file:", h264core.__file__)

# 1. split: SPS + IDR with a 3-byte code inside
frame = b"\x00\x00\x00\x01\x67\x42\x43" + b"\xA1\x00\x00\x01" + b"\x00\x00\x01\x65\x11\x22"
nals = h264core.split_nals(frame)
for n in nals:
    print("  NAL", n)
assert [n.nal_type for n in nals] == [7, 5], "types"
assert nals[0].rbsp == b"\x42\x43\xA1", "sps rbsp"
assert nals[1].rbsp == b"\x11\x22", "idr rbsp"
print("OK split_nals types+rbsp")

# 2. keyframe
assert h264core.is_keyframe(frame) is True
assert h264core.is_keyframe(b"\x00\x00\x01\x41\x99") is False
print("OK is_keyframe")

# 3. demux roundtrip
packed = h264core.pack_frame(2**63 + 77, frame)
d = h264core.Demuxer()
out = []
for i in range(0, len(packed), 5):
    out += d.feed(packed[i:i + 5])
assert out == [(2**63 + 77, frame)], "roundtrip"
print("OK demux roundtrip (torn at 5B)")

# 4. error parity with the pure oracle
try:
    h264core.Demuxer().feed((12345).to_bytes(8, "big") + (32 * 1024 * 1024).to_bytes(4, "big"))
    raise AssertionError("should have raised")
except ValueError as e:
    assert str(e) == "insane frame length 33554432 at pts 12345", repr(str(e))
print("OK demux error message parity")

try:
    h264core.pack_frame(1, b"")
    raise AssertionError("should have raised")
except ValueError as e:
    assert str(e) == "bad payload length", repr(str(e))
print("OK pack error message parity")

# 5. emulation prevention roundtrips
raw = bytes([0x41, 0, 0, 1, 0x99, 0, 0, 3, 2])
esc = h264core.add_emulation_prevention(raw)
back = h264core.remove_emulation_prevention(esc)
assert back == raw, (back.hex(), raw.hex())
print("OK emulation prevention roundtrip")

print("PYD PROBE: ALL PASS")
