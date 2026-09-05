# -*- coding: utf-8 -*-
"""scrcpy framing smoke: the 12-byte header river on the live heart.

Replays what scrcpy's video socket does to the demuxer — >QI headers,
payloads torn at hostile offsets (1, 12, 13, 4097), a frame that lies about
its length — and pins the exact error-message contract against the pure
oracle aliases. Exit 0 = the demuxer is wire-ready.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import h264_math as m  # noqa: E402  (grafted view; _py_* = pure oracle)

heart = "RUST" if m.rust_heart() else "PURE"
print("heart:", heart)
fails = 0


def check(name, cond, detail=""):
    global fails
    if cond:
        print("PASS " + name)
    else:
        fails += 1
        print("FAIL " + name + ((" :: " + str(detail)) if detail else ""))


HEADER = m.H264FrameDemuxer.HEADER  # grafted class carries the same Struct

frames = [
    (0, b"\x00\x00\x00\x01\x67\x42\x43"),                    # SPS-ish
    (33, b"\xAB" * 17),                                      # the 17B payload
    (66, bytes((i * 7) & 0xFF for i in range(100_000))),     # 100KB IDR
    (100, b"\x99"),                                          # 1B sliver
]
stream = b"".join(m.H264FrameDemuxer.pack_frame(pts, p) for pts, p in frames)

for tear in (1, 12, 13, 4097):
    d = m.H264FrameDemuxer()
    got = []
    for i in range(0, len(stream), tear):
        got += d.feed(stream[i:i + tear])
    check("demux tear@%d recovers 4 frames" % tear,
          got == frames, (tear, [(pt, len(pl)) for pt, pl in got]))

# a frame that LIES: header claims 21, only 17 arrive, then the rest
d = m.H264FrameDemuxer()
hdr = HEADER.pack(7, 21)
early = d.feed(hdr + b"\xCD" * 17)
check("liar frame waits (no premature emit)", early == [], early)
late = d.feed(b"\xCD" * 4)
check("liar frame completes at 21", late == [(7, b"\xCD" * 21)], late)

# error contract vs the pure oracle — exact strings
def insane_msg(demuxer_cls, pts, length):
    d = demuxer_cls()
    try:
        d.feed(struct.pack(">QI", pts, length))
        return "no-raise"
    except ValueError as e:
        return str(e)


got_py = insane_msg(m._py_H264FrameDemuxer, 12345, 32 * 1024 * 1024)
got_live = insane_msg(m.H264FrameDemuxer, 12345, 32 * 1024 * 1024)
check("insane-length message parity", got_py == got_live
      == "insane frame length 33554432 at pts 12345", (got_py, got_live))

got_py = insane_msg(m._py_H264FrameDemuxer, 5, 0)
got_live = insane_msg(m.H264FrameDemuxer, 5, 0)
check("zero-length message parity", got_py == got_live
      == "insane frame length 0 at pts 5", (got_py, got_live))

for label, maker in (("py", m._py_H264FrameDemuxer.pack_frame),
                     ("live", m.H264FrameDemuxer.pack_frame)):
    try:
        maker(1, b"")
        check("pack empty parity (%s)" % label, False, "no-raise")
    except ValueError as e:
        check("pack empty parity (%s)" % label, str(e) == "bad payload length",
              str(e))

# pack/unpack round trip through the live heart at a >QI boundary
big_pts = 2 ** 63 + 77
big = m.H264FrameDemuxer.pack_frame(big_pts, b"\xDE\xAD\xBE\xEF")
d = m.H264FrameDemuxer()
out = []
for i in range(0, len(big), 3):
    out += d.feed(big[i:i + 3])
check(">QI boundary pts round trip", out == [(big_pts, b"\xDE\xAD\xBE\xEF")], out)

print()
print("SCRCPY DEMUX SMOKE: %s (heart=%s, %d failure(s))"
      % ("PASSED" if fails == 0 else "FAILED", heart, fails))
sys.exit(0 if fails == 0 else 1)
