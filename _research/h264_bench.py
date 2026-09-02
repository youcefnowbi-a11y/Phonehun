#!/usr/bin/env python3
"""THE YARDSTICK — h264 hot-path benchmark (the before/after judge).

Measures the two per-frame hot paths of h264_math.py exactly as the glass
pipe uses them:
  1. NAL WORK   : split_nals + is_keyframe on a realistic IDR frame
  2. DEMUX      : H264FrameDemuxer.feed() over a torn TCP stream (4KB chunks)

Usage:  python _research/h264_bench.py [frames] [reps]
Same yardstick for Python tonight and the Rust h264core later (dc_bench).
"""
import sys, time, os, random
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from h264_math import (H264FrameDemuxer, split_nals, is_keyframe,
                       add_emulation_prevention, NAL_SPS, NAL_SLICE_IDR)


def build_idr_frame(payload_kb: int, rng: random.Random) -> bytes:
    """A realistic scrcpy IDR: SPS-ish NAL + fat pseudo-random IDR slice."""
    sps_rbsp = bytes([0x67, 0x64, 0x00, 0x1F, 0xAC]) + bytes(rng.randrange(256) for _ in range(20))
    slice_rbsp = bytes([0x65]) + bytes(rng.randrange(256) for _ in range(payload_kb * 1024))
    out = bytearray()
    for rbsp in (sps_rbsp, slice_rbsp):
        out += b"\x00\x00\x00\x01" + add_emulation_prevention(rbsp)
    return bytes(out)


def build_stream(n_frames: int, rng: random.Random):
    frames = [build_idr_frame(48, rng) for _ in range(n_frames)]  # ~48KB each
    demux = H264FrameDemuxer()
    stream = bytearray()
    for pts, f in enumerate(frames):
        stream += H264FrameDemuxer.pack_frame(pts, f)
    return frames, bytes(stream)


def bench(frames, stream, reps: int):
    n = len(frames)
    stream_mb = len(stream) / 1e6

    # 1. NAL WORK
    t0 = time.perf_counter()
    for _ in range(reps):
        for f in frames:
            nals = split_nals(f)
            kf = is_keyframe(f)
    t_nal = time.perf_counter() - t0

    # 2. DEMUX (torn 4KB TCP reads)
    t0 = time.perf_counter()
    for _ in range(reps):
        d = H264FrameDemuxer()
        got = 0
        for i in range(0, len(stream), 4096):
            got += len(d.feed(stream[i:i + 4096]))
        assert got == n, f"demux lost frames: {got} != {n}"
    t_demux = time.perf_counter() - t0

    return t_nal, t_demux


def main():
    n_frames = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    reps = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    rng = random.Random(1551)
    frames, stream = build_stream(n_frames, rng)
    print(f"yardstick: {n_frames} frames x {len(frames[0])//1024}KB, stream {len(stream)/1e6:.1f}MB, {reps} reps")

    # correctness sanity before timing (a bench of a broken port is a lie)
    assert is_keyframe(frames[0]) is True
    nals = split_nals(frames[0])
    assert nals[0][0] == NAL_SPS and nals[1][0] == NAL_SLICE_IDR

    t_nal, t_demux = bench(frames, stream, reps)
    total = n_frames * reps
    print(f"NAL WORK : {t_nal*1000/total:8.3f} ms/frame   ({n_frames*reps/1000/t_nal:7.1f} kframes/s)")
    print(f"DEMUX    : {t_demux*1000/total:8.3f} ms/frame   ({len(stream)*reps/1e6/t_demux:7.1f} MB/s)")
    glass_load = 15  # fps our glass pipe targets
    per_frame = (t_nal + t_demux) * 1000 / total
    core_pct = per_frame * glass_load / 10  # ms/frame * fps / 1000ms * 100%
    print(f"@{glass_load}fps glass budget: {per_frame:.2f} ms of {1000/glass_load:.0f} ms  -> {core_pct:.1f}% of one core")
    print("SANITY: sps+idr split OK, keyframe OK, demux lossless OK")


if __name__ == "__main__":
    main()
