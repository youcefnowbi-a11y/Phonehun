//! h264core-py — the PyO3 skin over the pure h264core crate.
//!
//! Module name is `h264core` (PyInit_h264core), so Python does:
//!     import h264core
//!     h264core.split_nals(frame) -> list of PyNal(type, ref_idc, rbsp: bytes)
//!     h264core.is_keyframe(frame) -> bool
//!     h264core.pack_frame(pts, payload) -> bytes     (raises ValueError like the oracle)
//!     h264core.Demuxer().feed(chunk) -> list of (pts, bytes)
//!
//! Error-message parity with h264_math.py is load-bearing:
//!   demuxer: ValueError("insane frame length {length} at pts {pts}")
//!   packer : ValueError("bad payload length")
//! Differential goldens (tests/golden_vectors.txt) prove the match.

use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyBytes, PyBytesMethods, PyModule};

use h264core::{AnnexBStreamSplitter as CoreSplitter, DemuxError, Demuxer as CoreDemuxer};

fn insane(e: DemuxError) -> PyErr {
    let DemuxError::InsaneFrame { pts, length } = e;
    PyValueError::new_err(format!("insane frame length {length} at pts {pts}"))
}

/// One parsed NAL unit: type, ref_idc, RBSP (header stripped, emulation
/// prevention removed, trailing zeros stripped) as an immutable bytes.
#[pyclass]
#[pyo3(name = "Nal")]
struct PyNal {
    #[pyo3(get)]
    nal_type: u8,
    #[pyo3(get)]
    ref_idc: u8,
    #[pyo3(get)]
    rbsp: Py<PyBytes>,
}

#[pymethods]
impl PyNal {
    fn __repr__(&self, py: Python<'_>) -> String {
        let n = self.rbsp.bind(py).as_bytes().len();
        format!(
            "<Nal type={} ref_idc={} rbsp={}B>",
            self.nal_type, self.ref_idc, n
        )
    }
}

/// Annex-B split — mirrors h264_math.split_nals exactly (3-byte start code
/// wins over 4-byte at the same position; trailing zero delimiters stripped).
#[pyfunction]
fn split_nals(py: Python<'_>, frame: &[u8]) -> PyResult<Vec<PyNal>> {
    Ok(h264core::split_nals(frame)
        .into_iter()
        .map(|n| PyNal {
            nal_type: n.nal_type,
            ref_idc: n.ref_idc,
            rbsp: PyBytes::new(py, &n.rbsp).unbind(),
        })
        .collect())
}

/// Keyframe detection: any IDR slice NAL (type 5) in the frame. Peek-only scan.
#[pyfunction]
fn is_keyframe(frame: &[u8]) -> bool {
    h264core::is_keyframe(frame)
}

/// Writer-side mirror: 12B big-endian header (pts u64 + length u32) + payload.
/// ValueError("bad payload length") on empty or oversized payloads — the
/// oracle's exact message.
#[pyfunction]
fn pack_frame(py: Python<'_>, pts: u64, payload: &[u8]) -> PyResult<Py<PyBytes>> {
    match CoreDemuxer::pack_frame(pts, payload) {
        Ok(packed) => Ok(PyBytes::new(py, &packed).unbind()),
        Err(_) => Err(PyValueError::new_err("bad payload length")),
    }
}

/// Reader-side emulation-prevention removal (00 00 03 xx -> 00 00 xx for xx<=3).
#[pyfunction]
fn remove_emulation_prevention<'py>(py: Python<'py>, data: &[u8]) -> Py<PyBytes> {
    PyBytes::new(py, &h264core::remove_emulation_prevention(data)).unbind()
}

/// Writer-side emulation-prevention insertion.
#[pyfunction]
fn add_emulation_prevention<'py>(py: Python<'py>, data: &[u8]) -> Py<PyBytes> {
    PyBytes::new(py, &h264core::add_emulation_prevention(data)).unbind()
}

/// Streaming scrcpy demuxer: feed(chunk) -> list of (pts, payload bytes).
/// Handles chunks torn anywhere. Raises ValueError on insane frame headers.
#[pyclass]
#[pyo3(name = "Demuxer")]
struct PyDemuxer {
    inner: CoreDemuxer,
}

#[pymethods]
impl PyDemuxer {
    #[new]
    fn new() -> Self {
        PyDemuxer { inner: CoreDemuxer::new() }
    }

    fn feed(&mut self, py: Python<'_>, chunk: &[u8]) -> PyResult<Vec<(u64, Py<PyBytes>)>> {
        match self.inner.feed(chunk) {
            Ok(frames) => Ok(frames
                .into_iter()
                .map(|(pts, payload)| (pts, PyBytes::new(py, &payload).unbind()))
                .collect()),
            Err(e) => Err(insane(e)),
        }
    }
}

/// Incremental Annex-B river splitter — the raw glass-pipe organ.
/// feed(chunk) / flush() return COMPLETE NAL units (header byte + payload,
/// emulation prevention left intact, trailing zeros stripped). Byte-exact
/// port of h264_math.AnnexBStreamSplitter (STREAMCASE goldens prove it).
#[pyclass]
#[pyo3(name = "AnnexBStreamSplitter")]
struct PyAnnexBStreamSplitter {
    inner: CoreSplitter,
}

#[pymethods]
impl PyAnnexBStreamSplitter {
    #[new]
    fn new() -> Self {
        PyAnnexBStreamSplitter { inner: CoreSplitter::new() }
    }

    fn feed(&mut self, py: Python<'_>, chunk: &[u8]) -> Vec<Py<PyBytes>> {
        self.inner
            .feed(chunk)
            .into_iter()
            .map(|u| PyBytes::new(py, &u).unbind())
            .collect()
    }

    fn flush(&mut self, py: Python<'_>) -> Vec<Py<PyBytes>> {
        self.inner
            .flush()
            .into_iter()
            .map(|u| PyBytes::new(py, &u).unbind())
            .collect()
    }
}

/// Whole-buffer raw-unit split: same semantics as the river splitter on a
/// complete buffer (raw units out, no EP removal, garbage prefix dropped).
#[pyfunction]
fn split_annexb_units(py: Python<'_>, frame: &[u8]) -> Vec<Py<PyBytes>> {
    let mut sp = CoreSplitter::new();
    let mut out: Vec<Vec<u8>> = sp.feed(frame);
    out.extend(sp.flush());
    out.into_iter()
        .map(|u| PyBytes::new(py, &u).unbind())
        .collect()
}

/// NAL header byte decode: (nal_type, ref_idc) — the forbidden-byte check
/// lives in the caller, this is the pure field split.
#[pyfunction]
fn nal_header_info(header: u8) -> (u8, u8) {
    (header & 0x1F, (header >> 5) & 0x3)
}

#[pymodule]
#[pyo3(name = "h264core")]
fn pybridge(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(split_nals, m)?)?;
    m.add_function(wrap_pyfunction!(is_keyframe, m)?)?;
    m.add_function(wrap_pyfunction!(pack_frame, m)?)?;
    m.add_function(wrap_pyfunction!(remove_emulation_prevention, m)?)?;
    m.add_function(wrap_pyfunction!(add_emulation_prevention, m)?)?;
    m.add_function(wrap_pyfunction!(split_annexb_units, m)?)?;
    m.add_function(wrap_pyfunction!(nal_header_info, m)?)?;
    m.add_class::<PyNal>()?;
    m.add_class::<PyDemuxer>()?;
    m.add_class::<PyAnnexBStreamSplitter>()?;
    Ok(())
}
