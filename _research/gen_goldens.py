#!/usr/bin/env python3
"""Golden-vector generator — Python is the oracle, Rust must match it.

Writes rust/h264core/tests/golden_vectors.txt: frames, expected NALs,
keyframe flags, and torn-stream demux cases (including error cases),
all computed with h264_math.py itself. dc_test (Rust) replays them.
"""
import os, sys, random

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h264_math import (H264FrameDemuxer, split_nals, is_keyframe,
                       add_emulation_prevention)


def hexs(b):
    return b.hex().upper() if b else ""


def emit_frame(lines, frame):
    lines.append(f"FRAME {hexs(frame)}")
    for t, rid, rbsp in split_nals(frame):
        lines.append(f"NAL {t} {rid} {hexs(rbsp)}")
    lines.append(f"KF {1 if is_keyframe(frame) else 0}")


def emit_demux(lines, chunks, expect_err=None):
    lines.append("DEMUXCASE")
    for c in chunks:
        lines.append(f"CHUNK {hexs(c)}")
    if expect_err is not None:
        pts, length = expect_err
        lines.append(f"ERR {pts} {length}")
    else:
        d = H264FrameDemuxer()
        frames = []
        for c in chunks:
            frames += d.feed(c)
        for pts, payload in frames:
            lines.append(f"OUT {pts} {hexs(payload)}")
    lines.append("ENDCASE")


def main():
    rng = random.Random(1551)
    L = []

    # 1. realistic sps + fat idr
    sps_rbsp = bytes([0x67, 0x64, 0x00, 0x1F, 0xAC]) + bytes(rng.randrange(256) for _ in range(20))
    slice_rbsp = bytes([0x65]) + bytes(rng.randrange(256) for _ in range(2048))
    f1 = bytearray()
    for rbsp in (sps_rbsp, slice_rbsp):
        f1 += b"\x00\x00\x00\x01" + add_emulation_prevention(rbsp)
    emit_frame(L, bytes(f1))

    # 2. emulation-prevention gauntlet: every nasty run, incl. 00 00 03 00-03
    nasties = bytes([0x05, 0, 0, 3, 0, 0, 3, 1, 0, 0, 3, 2, 0, 0, 3, 3,
                     0, 0, 1,          # real start code inside rbsp -> must be escaped
                     0, 0, 0, 1,       # 4-byte inside
                     0, 0, 3, 0, 0, 0, 1, 0x99])
    rbsp = bytes([0x41]) + nasties
    f2 = b"\x00\x00\x00\x01" + add_emulation_prevention(rbsp)
    assert add_emulation_prevention(rbsp) != rbsp  # escape actually fired
    emit_frame(L, f2)

    # 3. mixed 3/4-byte codes, empty NAL, trailing zeros delimiter
    f3 = b"\x00\x00\x01\x67\x42" + b"\x00\x00\x00\x01\x65\x11\x22" + b"\x00\x00\x00"
    emit_frame(L, f3)

    # 4. no start codes at all
    emit_frame(L, bytes(rng.randrange(256) for _ in range(64)))

    # 5. lone start code, empty unit (start >= end) and PPS
    f5 = b"\x00\x00\x01" + b"\x00\x00\x01\x68\xEE" + b"\x00\x00\x00\x01\x00"
    emit_frame(L, f5)

    # 6. demux: normal, torn at every byte, big pts, split header
    frame = bytes(f1)
    good = H264FrameDemuxer.pack_frame(2**63 + 77, frame)
    emit_demux(L, [good])
    emit_demux(L, [good[i:i + 1] for i in range(len(good))])            # 1-byte tears
    emit_demux(L, [good[:5], good[5:9], good[9:]])                       # header torn
    emit_demux(L, [good, good[:12]])                                     # trailing partial header

    # 7. demux errors: zero length, insane length
    bad0 = (0).to_bytes(8, "big") + (0).to_bytes(4, "big")
    emit_demux(L, [bad0 + b"xx"], expect_err=(0, 0))
    bad1 = (12345).to_bytes(8, "big") + (32 * 1024 * 1024).to_bytes(4, "big")
    emit_demux(L, [bad1], expect_err=(12345, 32 * 1024 * 1024))

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                        "rust", "h264core", "tests", "golden_vectors.txt")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="ascii") as fh:
        fh.write("\n".join(L) + "\n")
    n_frames = sum(1 for x in L if x.startswith("FRAME"))
    n_cases = sum(1 for x in L if x == "DEMUXCASE")
    print(f"goldens written: {n_frames} frames, {n_cases} demux cases -> {os.path.normpath(path)}")
    assert "KF 1" in L, "oracle produced no keyframe case"


if __name__ == "__main__":
    main()
