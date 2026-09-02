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
        if zeros == 2 && data[i] == 3 && i + 1 < data.len() && data[i + 1] <= 3 {
            // 00 00 03 xx -> drop the 03
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
