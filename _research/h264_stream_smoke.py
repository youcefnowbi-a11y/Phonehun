# -*- coding: utf-8 -*-
"""End-to-end glass-pipe smoke: synthetic 4-frame stream, torn rivers.

Proves the LIVE import path panopticon/screen_console.py uses —
``from h264_math import AnnexBStreamSplitter, parse_sps, NAL_SPS,
NAL_SLICE_IDR, remove_emulation_prevention`` — reassembles a synthetic
SPS/PPS + IDR + P-slices stream torn at hostile offsets, with ZERO source
change in screen_console, and that the river agrees with the whole-buffer
parser (split_nals) on the recovered RBSPs.

Exit 0 = the cast river runs on whatever heart h264_math picked.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# EXACT import surface screen_console.py uses — zero source change required.
from h264_math import (AnnexBStreamSplitter, NAL_SLICE_IDR, NAL_SPS,  # noqa: E402
                       parse_sps, remove_emulation_prevention, rust_heart)

heart = "RUST" if rust_heart() else "PURE"
print("heart:", heart)
fails = 0


def check(name, cond, detail=""):
    global fails
    if cond:
        print("PASS " + name)
    else:
        fails += 1
        print("FAIL " + name + ((" :: " + str(detail)) if detail else ""))


# --- synthetic river: SPS + PPS + IDR + two P slices --------------------------
sps_nal = b"\x00\x00\x00\x01" + b"\x67" + bytes([0x42, 0x40, 0x1F]) + b"\xA1\x00\x03\x01"
pps_nal = b"\x00\x00\x00\x01" + b"\x68" + b"\xEB\xCB\x80\x40"
idr_nal = b"\x00\x00\x00\x01" + b"\x65" + b"\x88\x84\x00\x21\xCF\xFC\x00\x00\x01\x02\x99"
p1_nal = b"\x00\x00\x00\x01" + b"\x41" + b"\x0A\xB2\x11\x22\x00\x00\x03\x00\x44"
p2_nal = b"\x00\x00\x00\x01" + b"\x41" + b"\x55\x66\x77\x00\x00"

stream = sps_nal + pps_nal + idr_nal + p1_nal + p2_nal

# expected units: bytes after each start code (trailing zeros stripped by
# the splitter contract). The IDR payload deliberately embeds 00 00 01 —
# the splitter's contract treats ANY 00 00 01 as a boundary, so the IDR
# surface-splits into two units (oracle-verified behavior).
sps_unit = sps_nal[4:]
pps_unit = pps_nal[4:]
expected = [
    sps_unit,                                   # 67 42 40 1F A1 00 03 01
    pps_unit,                                   # 68 EB CB 80 40
    idr_nal[4:11],                              # 65 88 84 00 21 CF FC
    b"\x02\x99",                                # IDR continuation
    p1_nal[4:],                                 # 41 0A B2 11 22 00 00 03 00 44
    p2_nal[4:].rstrip(b"\x00"),                 # 41 55 66 77
]

# 1. whole-buffer reference
ref = AnnexBStreamSplitter()
whole = ref.feed(stream) + ref.flush()
check("whole-buffer split == expected units", whole == expected, whole)

# 2. torn rivers at hostile offsets (1/2/3 kill start codes; 7 splits
#    4-byte codes; 4096 mimics a lazy TCP read)
for tear in (1, 2, 3, 7, 4096):
    sp = AnnexBStreamSplitter()
    got = []
    for i in range(0, len(stream), tear):
        got += sp.feed(stream[i:i + tear])
    got += sp.flush()
    check("river tear@%d == whole-buffer" % tear, got == whole,
          (tear, len(got), len(whole)))
    sp2 = AnnexBStreamSplitter()
    for i in range(0, len(stream), tear):
        sp2.feed(stream[i:i + tear])
    sp2.flush()
    check("river tear@%d double-flush silent" % tear, sp2.flush() == [])

# 3. cross-contract: river units re-fed through the whole-buffer parser must
#    yield the same RBSPs as parsing the original stream
import h264_math as m2  # noqa: E402
reparsed = [r for _, _, r in m2.split_nals(
    b"".join(b"\x00\x00\x00\x01" + u for u in whole))]
direct = [r for _, _, r in m2.split_nals(stream)]
check("river RBSPs == whole-buffer parse", reparsed == direct)

# 4. SPS round trip through the LIVE writer/parser pair (synthesis, not a
#    hand-faked NAL): make_sps_nal -> split_nals -> parse_sps -> geometry
sps_nal_real = m2.make_sps_nal(1920, 1080, fps=30)
sps_rbsp = None
for t, _ridc, rbsp in m2.split_nals(sps_nal_real):
    if t == NAL_SPS:
        sps_rbsp = rbsp
info = parse_sps(sps_rbsp)
check("make_sps_nal/parse_sps round trip (1920x1080@30)",
      info["width"] == 1920 and info["height"] == 1080 and info["fps"] == 30.0,
      info)
check("IDR type constant sane", NAL_SLICE_IDR == 5)

print()
print("STREAM SMOKE: %s (heart=%s, %d failure(s))"
      % ("PASSED" if fails == 0 else "FAILED", heart, fails))
sys.exit(0 if fails == 0 else 1)
