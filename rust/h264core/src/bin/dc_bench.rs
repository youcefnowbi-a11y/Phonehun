//! Equality bench: h264core (Rust) vs the Python yardstick, same synthetic
//! corpus semantics. Rust side reports its numbers; the harness compares
//! against Python's 17.323 ms/frame NAL baseline (same generator, same seed).

use std::time::Instant;
use h264core::{add_emulation_prevention, is_keyframe, split_nals, Demuxer, NAL_SPS, NAL_SLICE_IDR};

/// xorshift PRNG — deterministic corpus, no external crates needed.
struct Rng(u64);
impl Rng {
    fn next(&mut self) -> u64 {
        let mut x = self.0;
        x ^= x << 13;
        x ^= x >> 7;
        x ^= x << 17;
        self.0 = x;
        x
    }
    fn byte(&mut self) -> u8 {
        (self.next() >> 24) as u8
    }
}

fn build_idr_frame(payload_kb: usize, rng: &mut Rng) -> Vec<u8> {
    let mut sps_rbsp = vec![0x67, 0x64, 0x00, 0x1F, 0xAC];
    for _ in 0..20 {
        sps_rbsp.push(rng.byte());
    }
    let mut slice_rbsp = vec![0x65u8];
    for _ in 0..payload_kb * 1024 {
        slice_rbsp.push(rng.byte());
    }
    let mut out = Vec::new();
    for rbsp in [&sps_rbsp, &slice_rbsp] {
        out.extend_from_slice(&[0, 0, 0, 1]);
        out.extend_from_slice(&add_emulation_prevention(rbsp));
    }
    out
}

fn build_stream(n_frames: usize, rng: &mut Rng) -> (Vec<Vec<u8>>, Vec<u8>) {
    let frames: Vec<Vec<u8>> = (0..n_frames).map(|_| build_idr_frame(48, rng)).collect();
    let mut stream = Vec::new();
    for (pts, f) in frames.iter().enumerate() {
        stream.extend_from_slice(&Demuxer::pack_frame(pts as u64, f).unwrap());
    }
    (frames, stream)
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let n_frames: usize = args.get(1).map(|s| s.parse().unwrap()).unwrap_or(200);
    let reps: usize = args.get(2).map(|s| s.parse().unwrap()).unwrap_or(20);

    let mut rng = Rng(1551);
    let (frames, stream) = build_stream(n_frames, &mut rng);
    println!(
        "yardstick: {} frames x {}KB, stream {:.1}MB, {} reps",
        n_frames,
        frames[0].len() / 1024,
        stream.len() as f64 / 1e6,
        reps
    );

    // correctness sanity before timing
    assert!(is_keyframe(&frames[0]));
    let nals = split_nals(&frames[0]);
    assert_eq!(nals[0].nal_type, NAL_SPS);
    assert_eq!(nals[1].nal_type, NAL_SLICE_IDR);

    // 1. NAL WORK
    let t0 = Instant::now();
    for _ in 0..reps {
        for f in &frames {
            let nals = split_nals(f);
            let kf = is_keyframe(f);
            std::hint::black_box((nals, kf));
        }
    }
    let t_nal = t0.elapsed();

    // 2. DEMUX (torn 4KB TCP reads)
    let t0 = Instant::now();
    for _ in 0..reps {
        let mut d = Demuxer::new();
        let mut got = 0usize;
        for i in (0..stream.len()).step_by(4096) {
            let end = (i + 4096).min(stream.len()); // python [i:i+4096] clamps; rust panics
            got += d.feed(&stream[i..end]).unwrap().len();
        }
        assert_eq!(got, n_frames, "demux lost frames");
    }
    let t_demux = t0.elapsed();

    let total = (n_frames * reps) as f64;
    let per_nal_ms = t_nal.as_secs_f64() * 1000.0 / total;
    let per_demux_ms = t_demux.as_secs_f64() * 1000.0 / total;
    println!(
        "NAL WORK : {:8.3} ms/frame   ({:7.1} kframes/s)",
        per_nal_ms,
        total / 1000.0 / t_nal.as_secs_f64()
    );
    println!(
        "DEMUX    : {:8.3} ms/frame   ({:7.1} MB/s)",
        per_demux_ms,
        stream.len() as f64 * reps as f64 / 1e6 / t_demux.as_secs_f64()
    );
    let per_frame = per_nal_ms + per_demux_ms;
    let core_pct = per_frame * 15.0 / 10.0; // ms/frame * fps / 1000ms * 100%
    println!(
        "@15fps glass budget: {:.2} ms of 67 ms -> {:.1}% of one core",
        per_frame, core_pct
    );
    println!("SANITY: sps+idr split OK, keyframe OK, demux lossless OK");
    println!("PYTHON BASELINE (same yardstick): NAL 17.323 ms/frame");
    println!("SPEEDUP vs Python: {:.0}x", 17.323 / per_nal_ms);
}
