//! h264core — DroidCommand's hot-path H.264 core.
//!
//! Faithful port of the per-frame hot loop of h264_math.py:
//!   • split_nals / is_keyframe — Annex-B scan, emulation prevention
//!   • H264FrameDemuxer         — scrcpy 12-byte header framing, tear-tolerant
//! Cold paths (parse_sps, make_sps) stay in Python: they run once per stream.

#![allow(clippy::needless_range_loop)]

pub const NAL_SLICE_NON_IDR: u8 = 1;
pub const NAL_SLICE_IDR: u8 = 5;
pub const NAL_SEI: u8 = 6;
pub const NAL_SPS: u8 = 7;
pub const NAL_PPS: u8 = 8;

/// One NAL unit: type, ref_idc, and the RBSP (header byte stripped,
/// emulation-prevention removed, trailing zero delimiters stripped).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Nal {
    pub nal_type: u8,
    pub ref_idc: u8,
    pub rbsp: Vec<u8>,
}

/// Remove 0x03 after any 00 00 0x00-03 run (reader-side).
pub fn remove_emulation_prevention(data: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(data.len());
    let mut zeros: u32 = 0;
    let mut i = 0;
    while i < data.len() {
        if zeros == 2 && data[i] == 3 {
            // 00 00 03 -> drop the 03 unconditionally. Oracle parity: pure
            // Python drops ANY 0x03 after two zeros — even at buffer end or
            // followed by >3. (The differential proved a spec-strict guard
            // here was drift; the oracle is the contract.)
            zeros = 0;
            i += 1;
            continue;
        }
        let b = data[i];
        out.push(b);
        zeros = if b == 0 { zeros + 1 } else { 0 };
        i += 1;
    }
    out
}

/// Insert 0x03 so no 00 00 0x00-03 run appears (writer-side).
pub fn add_emulation_prevention(data: &[u8]) -> Vec<u8> {
    let mut out = Vec::with_capacity(data.len() + 8);
    let mut zeros: u32 = 0;
    for &b in data {
        if zeros == 2 && b <= 3 {
            out.push(3);
            zeros = 0;
        }
        out.push(b);
        zeros = if b == 0 { zeros + 1 } else { 0 };
    }
    out
}

/// Split an Annex-B payload into NAL units. Mirrors h264_math.split_nals
/// exactly: 3-byte start code wins over 4-byte at the same position.
pub fn split_nals(frame: &[u8]) -> Vec<Nal> {
    // find start-code positions (pos, len)
    let mut positions: Vec<(usize, usize)> = Vec::new();
    let n = frame.len();
    let mut i = 0usize;
    while i + 2 < n {
        if frame[i] == 0 && frame[i + 1] == 0 && frame[i + 2] == 1 {
            positions.push((i, 3));
            i += 3;
        } else if i + 3 < n && frame[i] == 0 && frame[i + 1] == 0 && frame[i + 2] == 0 && frame[i + 3] == 1 {
            positions.push((i, 4));
            i += 4;
        } else {
            i += 1;
        }
    }

    let mut nals = Vec::with_capacity(positions.len());
    for (idx, &(pos, sc)) in positions.iter().enumerate() {
        let start = pos + sc;
        let end = if idx + 1 < positions.len() { positions[idx + 1].0 } else { n };
        if start >= end {
            continue;
        }
        let unit = &frame[start..end];
        if unit.is_empty() {
            continue;
        }
        let header = unit[0];
        let nal_type = header & 0x1F;
        let ref_idc = (header >> 5) & 0x3;
        let mut rbsp = remove_emulation_prevention(&unit[1..]);
        while rbsp.last() == Some(&0) {
            rbsp.pop();
        }
        nals.push(Nal { nal_type, ref_idc, rbsp });
    }
    nals
}

/// A frame carrying an IDR slice is a keyframe. Allocation-free scan:
/// peek each start code's header byte, never copy RBSP.
pub fn is_keyframe(frame: &[u8]) -> bool {
    let n = frame.len();
    let mut i = 0usize;
    while i + 2 < n {
        if frame[i] == 0 && frame[i + 1] == 0 && frame[i + 2] == 1 {
            if i + 3 < n && (frame[i + 3] & 0x1F) == NAL_SLICE_IDR {
                return true;
            }
            i += 3;
        } else if i + 3 < n && frame[i] == 0 && frame[i + 1] == 0 && frame[i + 2] == 0 && frame[i + 3] == 1 {
            if i + 4 < n && (frame[i + 4] & 0x1F) == NAL_SLICE_IDR {
                return true;
            }
            i += 4;
        } else {
            i += 1;
        }
    }
    false
}

/// Streaming demuxer for scrcpy's video socket framing.
/// feed(chunk) -> frames (pts, payload). Handles chunks torn anywhere.
pub struct Demuxer {
    buf: Vec<u8>,
    want_hdr: bool,
    pts: u64,
    length: usize,
}

pub const HEADER_SIZE: usize = 12; // >QI
pub const MAX_SANE_FRAME: usize = 16 * 1024 * 1024; // refuse to allocate lies

#[derive(Debug)]
pub enum DemuxError {
    InsaneFrame { pts: u64, length: usize },
}

impl Demuxer {
    pub fn new() -> Self {
        Demuxer { buf: Vec::new(), want_hdr: true, pts: 0, length: 0 }
    }

    pub fn feed(&mut self, chunk: &[u8]) -> Result<Vec<(u64, Vec<u8>)>, DemuxError> {
        self.buf.extend_from_slice(chunk);
        let mut frames = Vec::new();
        loop {
            if self.want_hdr {
                if self.buf.len() < HEADER_SIZE {
                    break;
                }
                let pts = u64::from_be_bytes(self.buf[0..8].try_into().unwrap());
                let len = u32::from_be_bytes(self.buf[8..12].try_into().unwrap()) as usize;
                if len == 0 || len > MAX_SANE_FRAME {
                    return Err(DemuxError::InsaneFrame { pts, length: len });
                }
                self.buf.drain(..HEADER_SIZE);
                self.pts = pts;
                self.length = len;
                self.want_hdr = false;
            } else {
                if self.buf.len() < self.length {
                    break;
                }
                frames.push((self.pts, self.buf[..self.length].to_vec()));
                self.buf.drain(..self.length);
                self.want_hdr = true;
            }
        }
        Ok(frames)
    }

    /// Writer-side mirror: 12B header + payload.
    pub fn pack_frame(pts: u64, payload: &[u8]) -> Result<Vec<u8>, DemuxError> {
        if payload.is_empty() || payload.len() > MAX_SANE_FRAME {
            return Err(DemuxError::InsaneFrame { pts, length: payload.len() });
        }
        let mut out = Vec::with_capacity(HEADER_SIZE + payload.len());
        out.extend_from_slice(&pts.to_be_bytes());
        out.extend_from_slice(&(payload.len() as u32).to_be_bytes());
        out.extend_from_slice(payload);
        Ok(out)
    }
}

impl Default for Demuxer {
    fn default() -> Self {
        Self::new()
    }
}

/// Incremental Annex-B NAL splitter for raw rivers (screenrecord mode).
/// TCP reads tear NALs apart at arbitrary boundaries — including inside a
/// start code itself. feed(chunk) keeps the torn tail buffered and returns
/// only COMPLETE NAL units (start-code payload, trailing zero delimiters
/// stripped per spec: trailing_zero_8bits are not part of a NAL unit).
/// Emulation prevention is NOT removed here; the parser does that per-NAL.
///
/// Faithful port of h264_math.AnnexBStreamSplitter (differential goldens:
/// STREAMCASE vectors). Subtle semantics preserved:
///   • 3-byte codes found first; a 4-byte code surfaces one byte later and
///     its leading 00 rides along, then is rstripped as a delimiter zero.
///   • Bytes before the FIRST start code of the stream are garbage.
///   • feed() never emits a partial tail; flush() emits it at river end.
pub struct AnnexBStreamSplitter {
    buf: Vec<u8>,
    pending: bool,
}

impl AnnexBStreamSplitter {
    pub fn new() -> Self {
        AnnexBStreamSplitter { buf: Vec::new(), pending: false }
    }

    pub fn feed(&mut self, chunk: &[u8]) -> Vec<Vec<u8>> {
        self.buf.extend_from_slice(chunk);
        self.drain(false)
    }

    /// River end: emit the final NAL if the buffer holds a valid one.
    pub fn flush(&mut self) -> Vec<Vec<u8>> {
        self.drain(true)
    }

    fn drain(&mut self, final_pass: bool) -> Vec<Vec<u8>> {
        let n = self.buf.len();
        let mut positions: Vec<usize> = Vec::new();
        let mut i = 0usize;
        while i + 2 < n {
            // (Python scans i < n-2 — identical range; no usize underflow.)
            if self.buf[i] == 0 && self.buf[i + 1] == 0 && self.buf[i + 2] == 1 {
                positions.push(i);
                i += 3;
            } else {
                i += 1;
            }
        }

        let mut out: Vec<Vec<u8>> = Vec::new();
        {
            let mut emit = |seg: &[u8]| {
                let mut end = seg.len();
                while end > 0 && seg[end - 1] == 0 {
                    end -= 1;
                }
                if end > 0 {
                    out.push(seg[..end].to_vec());
                }
            };

            for k in 0..positions.len().saturating_sub(1) {
                let a = positions[k] + 3;
                let bnd = positions[k + 1];
                emit(&self.buf[a..bnd]);
            }
            if !positions.is_empty() {
                let p0 = positions[0];
                if self.pending {
                    // buffer start .. first code = the pending NAL, now proven
                    emit(&self.buf[..p0]);
                }
                // else: bytes before the FIRST code of the stream are garbage
                self.pending = true;
                let keep = positions[positions.len() - 1] + 3;
                self.buf.drain(..keep.min(self.buf.len()));
            } else if !final_pass {
                if self.pending {
                    // payload accumulating; keep ALL of it
                } else if n > 2 {
                    let keep = n - 2; // pre-first-code: keep possible torn code
                    self.buf.drain(..keep);
                }
            }
            if final_pass {
                if !positions.is_empty() {
                    // Unreachable by invariant (feed() consumed all codes),
                    // kept for parity with the oracle's defensive branch.
                    let last = positions[positions.len() - 1] + 3;
                    if last <= self.buf.len() {
                        emit(&self.buf[last..]);
                    }
                } else if self.pending && n > 0 {
                    emit(&self.buf[..n]);
                }
                // Oracle parity: Python's flush() ends with self._buf.clear()
                // (h264_math.py final block) — a second flush emits nothing.
                // _pending intentionally persists, matching the oracle.
                self.buf.clear();
            }
        }
        out
    }
}

impl Default for AnnexBStreamSplitter {
    fn default() -> Self {
        Self::new()
    }
}
