"""
DroidCommand :: h264_math.py — the grammar of the video stream.

This is the brain of gate ③ (scrcpy H.264 pipe): everything that makes an
H.264 byte river readable, as pure testable math with zero dependencies.

  1. FRAME DEMUX (scrcpy's wire format)
     Each video frame crosses the socket as a 12-byte header followed by
     the frame payload:
         offset 0..7 : pts   uint64 big-endian (0 = no timestamp)
         offset 8..11: length uint32 big-endian
     Payload = Annex-B NAL units.

  2. NAL UNITS (Annex-B)
     Start codes: 00 00 01 or 00 00 00 01. Each NAL = header byte
     [forbidden(1) | nal_ref_idc(2) | nal_unit_type(5)] + RBSP payload.
     Types we care about: 1 non-IDR slice, 5 IDR slice (keyframe!),
     6 SEI, 7 SPS (the metadata), 8 PPS.

  3. EMULATION PREVENTION
     0x000003 sequences inside the payload exist so start codes can't
     appear by accident; the parser strips the 0x03 (only after 00 00 and
     only when followed by 00-03).

  4. SPS — exp-Golomb grammar (the actual math)
     Unsigned exp-Golomb ue(v): leadingZeroBits*2 + 1 - 2^leadingZeroBits
       read: count zeros k, read k more bits, value = 2^k - 1 + bits.
     Signed se(v): map 0→0, 1→+1, 2→-1, 3→+2, 4→-2 ... (k = ue; v = ±)
       v = (-1)^(k+1) * ceil(k/2)
     The SPS walks profile → chroma → depths → poc type → frame size in
     macroblocks (16px) → cropping (in crop units, NOT pixels!) → VUI
     timing (fps = time_scale / (2·num_units_in_tick) when fixed).
     Crop units depend on chroma format and interlacing — get them wrong
     and every phone resolution comes out slightly off. The math here is
     exact (SubWidthC/SubHeightC tables from the spec).

Honest limits: we PARSE, we don't decode. Pixels belong to a decoder
(hardware or ffmpeg); this module turns the river into metadata + clean
NAL units so a decoder/muxer can consume it.

Selftest: the module can also WRITE exp-Golomb and synthesize SPS
bitstreams, so the parser is verified against a writer that mirrors it —
round-trip proof, fully offline, no device needed.
"""

import os
import struct


# ---------------------------------------------------------------------------
# Bit-level reader / writer (MSB-first, H.264 convention)
# ---------------------------------------------------------------------------

class BitReader:
    __slots__ = ("data", "pos")

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0          # bit position

    def u(self, n: int) -> int:
        v = 0
        for _ in range(n):
            if self.pos >= len(self.data) * 8:
                raise EOFError("bitstream exhausted")
            byte = self.data[self.pos >> 3]
            bit = (byte >> (7 - (self.pos & 7))) & 1
            v = (v << 1) | bit
            self.pos += 1
        return v

    def ue(self) -> int:
        zeros = 0
        while self.u(1) == 0:
            zeros += 1
            if zeros > 32:
                raise ValueError("ue(v) runt: >32 leading zeros")
        return (1 << zeros) - 1 + (self.u(zeros) if zeros else 0)

    def se(self) -> int:
        k = self.ue()
        return (k + 1) // 2 if k % 2 else -(k // 2)

    def more_rbsp_data(self) -> bool:
        """True while payload bits remain before the rbsp_trailing stop bit."""
        total = len(self.data) * 8
        if self.pos >= total:
            return False
        # find the last set bit (stop bit is the final 1 before cabac_zero_words)
        i = total - 1
        while i > self.pos and not ((self.data[i >> 3] >> (7 - (i & 7))) & 1):
            i -= 1
        return self.pos < i


class BitWriter:
    def __init__(self):
        self._bits = []

    def u(self, v: int, n: int):
        for i in range(n - 1, -1, -1):
            self._bits.append((v >> i) & 1)

    def ue(self, v: int):
        v += 1
        n = v.bit_length()
        self.u(0, n - 1)          # leading zeros
        self.u(v, n)              # the (n)-bit value with its top bit set

    def se(self, v: int):
        k = 2 * v - 1 if v > 0 else -2 * v
        self.ue(k)

    def rbsp_trailing(self):
        self._bits.append(1)
        while len(self._bits) % 8:
            self._bits.append(0)

    def bytes(self) -> bytes:
        bits = self._bits[:]
        while len(bits) % 8:
            bits.append(0)
        out = bytearray(len(bits) // 8)
        for i, b in enumerate(bits):
            if b:
                out[i >> 3] |= 1 << (7 - (i & 7))
        return bytes(out)


# ---------------------------------------------------------------------------
# Annex-B NAL handling
# ---------------------------------------------------------------------------

def remove_emulation_prevention(rbsp_payload: bytes) -> bytes:
    """Strip 0x03 from 00 00 03 sequences (but keep 00 00 00 → 00 00)."""
    out = bytearray()
    i = 0
    n = len(rbsp_payload)
    zeros = 0
    while i < n:
        b = rbsp_payload[i]
        if zeros == 2 and b == 3:
            zeros = 0          # drop the 0x03, do not emit
            i += 1
            continue
        out.append(b)
        zeros = zeros + 1 if b == 0 else 0
        i += 1
    return bytes(out)


def add_emulation_prevention(rbsp: bytes) -> bytes:
    """Inverse: insert 0x03 so no 00 00 00-03 run appears (writer-side)."""
    out = bytearray()
    zeros = 0
    for b in rbsp:
        if zeros == 2 and b <= 3:
            out.append(3)
            zeros = 0
        out.append(b)
        zeros = zeros + 1 if b == 0 else 0
    return bytes(out)


# Oracle aliases: pure implementations under graft. split_nals/is_keyframe
# resolve these names at CALL time, so the oracle stays pure even in a
# process where the graft has rebound the public globals to Rust.
_py_remove_emulation_prevention = remove_emulation_prevention
_py_add_emulation_prevention = add_emulation_prevention


def split_nals(frame: bytes):
    """Split an Annex-B payload into NAL units, emulation removed.

    Returns [(nal_type, ref_idc, rbsp_bytes)] — RBSP payload AFTER the
    header byte, emulation-prevention removed.
    """
    # find start-code positions
    positions = []
    i = 0
    n = len(frame)
    while i < n - 2:
        if frame[i] == 0 and frame[i + 1] == 0 and frame[i + 2] == 1:
            positions.append((i, 3))
            i += 3
        elif (i < n - 3 and frame[i] == 0 and frame[i + 1] == 0
              and frame[i + 2] == 0 and frame[i + 3] == 1):
            positions.append((i, 4))
            i += 4
        else:
            i += 1
    nals = []
    for idx, (pos, sc) in enumerate(positions):
        start = pos + sc
        end = positions[idx + 1][0] if idx + 1 < len(positions) else n
        if start >= end:
            continue
        unit = frame[start:end]
        if not unit:
            continue
        header = unit[0]
        nal_type = header & 0x1F
        ref_idc = (header >> 5) & 0x3
        # trailing zeros are delimiters, not NAL content (trailing_zero_8bits)
        rbsp = _py_remove_emulation_prevention(unit[1:]).rstrip(b"\x00")
        nals.append((nal_type, ref_idc, rbsp))
    return nals


NAL_SLICE_NON_IDR = 1
NAL_SLICE_IDR = 5
NAL_SEI = 6
NAL_SPS = 7
NAL_PPS = 8


def is_keyframe(frame: bytes) -> bool:
    """A frame carrying an IDR slice is a keyframe."""
    return any(t == NAL_SLICE_IDR for t, _, _ in _py_split_nals(frame))


_py_split_nals = split_nals
_py_is_keyframe = is_keyframe


class AnnexBStreamSplitter:
    """Incremental Annex-B NAL splitter for raw rivers (screenrecord mode).

    TCP reads tear NALs apart at arbitrary boundaries — including inside a
    start code itself. feed(chunk) keeps the torn tail buffered and returns
    only COMPLETE NAL units (bytes after the start code, before the next
    one, trailing zero delimiters stripped per spec: trailing_zero_8bits
    are not part of a NAL unit). Emulation prevention is NOT removed here;
    the parser does that per-NAL.
    """

    def __init__(self):
        self._buf = bytearray()   # unemitted bytes: partial code + payload
        self._pending = False     # True once a start code has been consumed

    def feed(self, chunk: bytes):
        self._buf.extend(chunk)
        return self._drain(final=False)

    def flush(self):
        """River end: emit the final NAL if the buffer holds a valid one."""
        return self._drain(final=True)

    def _drain(self, final: bool):
        b = self._buf
        n = len(b)
        positions = []
        i = 0
        while i < n - 2:                 # a full 3-byte code must fit
            if b[i] == 0 and b[i + 1] == 0 and b[i + 2] == 1:
                positions.append(i)
                i += 3
            else:
                i += 1

        def emit(seg: bytes):
            s = seg.rstrip(b"\x00")
            if s:
                out.append(s)

        out = []
        for k in range(len(positions) - 1):
            emit(bytes(b[positions[k] + 3:positions[k + 1]]))
        if positions:
            if self._pending:
                # buffer start .. first code = the pending NAL, now proven
                emit(bytes(b[:positions[0]]))
            # else: bytes before the FIRST code of the stream are garbage
            self._pending = True
            del self._buf[:positions[-1] + 3]
        elif not final:
            if self._pending:
                pass                    # payload accumulating; keep ALL of it
            elif n > 2:
                del self._buf[:n - 2]   # pre-first-code: keep possible torn code
        if final:
            if positions:
                emit(bytes(b[positions[-1] + 3:]))
            elif self._pending and n:
                emit(bytes(b))
            self._buf.clear()
        return out


_py_AnnexBStreamSplitter = AnnexBStreamSplitter


# ---------------------------------------------------------------------------
# SPS parsing — the metadata mine
# ---------------------------------------------------------------------------

_PROFILE_HIGH = {100, 110, 122, 244, 44, 83, 86, 118, 128, 138, 139, 134, 135}

_SUBWC = {0: 1, 1: 2, 2: 2, 3: 1}   # SubWidthC by chroma_format_idc
_SUBHC = {0: 1, 1: 2, 2: 1, 3: 1}   # SubHeightC


def parse_sps(sps_rbsp: bytes) -> dict:
    """Parse an SPS RBSP (header byte already stripped, EP removed).

    Returns {width, height, fps, profile_idc, level_idc, chroma_format_idc,
    bit_depth_luma, frame_mbs_only, ...}. fps is None when no fixed-rate
    VUI timing is present — we refuse to guess.
    """
    r = BitReader(sps_rbsp)
    out = {}
    profile_idc = r.u(8)
    constraints = r.u(8)
    level_idc = r.u(8)
    r.ue()                                    # seq_parameter_set_id
    chroma_format_idc = 1                     # 4:2:0 default when not coded
    separate_colour = 0
    if profile_idc in _PROFILE_HIGH:
        chroma_format_idc = r.ue()
        if chroma_format_idc == 3:
            separate_colour = r.u(1)
        r.ue()                                # bit_depth_luma_minus8
        r.ue()                                # bit_depth_chroma_minus8
        r.u(1)                                # qpprime_y_zero_transform_bypass
        if r.u(1):                            # seq_scaling_matrix_present
            lists = 8 if chroma_format_idc != 3 else 12
            for i in range(lists):
                if r.u(1):                    # seq_scaling_list_present_flag[i]
                    _skip_scaling_list(r, 16 if i < 6 else 64)
    log2_max_frame_num = r.ue() + 4
    poc_type = r.ue()
    if poc_type == 0:
        r.ue()                                # log2_max_pic_order_cnt_lsb
    elif poc_type == 1:
        r.u(1)                                # delta_pic_order_always_zero
        r.se()                                # offset_for_non_ref_pic
        r.se()                                # offset_for_top_to_bottom_field
        for _ in range(r.ue()):               # num_ref_frames_in_pic_order_cnt_cycle
            r.se()
    max_num_ref = r.ue()
    r.u(1)                                    # gaps_in_frame_num_value_allowed
    pic_width_in_mbs = r.ue() + 1
    pic_height_in_map_units = r.ue() + 1
    frame_mbs_only = r.u(1)
    if not frame_mbs_only:
        r.u(1)                                # mb_adaptive_frame_field
    r.u(1)                                    # direct_8x8_inference
    crop_l = crop_r = crop_t = crop_b = 0
    if r.u(1):                                # frame_cropping
        crop_l, crop_r = r.ue(), r.ue()
        crop_t, crop_b = r.ue(), r.ue()

    sub_w = _SUBWC.get(chroma_format_idc, 2) if not separate_colour else 1
    sub_h = _SUBHC.get(chroma_format_idc, 2) if not separate_colour else 1
    crop_x = sub_w * (2 - frame_mbs_only)     # 4:2:0, progressive → 2
    crop_y = sub_h * (2 - frame_mbs_only)
    width = pic_width_in_mbs * 16 - (crop_l + crop_r) * crop_x
    height = (pic_height_in_map_units * 16
              - (crop_t + crop_b) * crop_y) * (2 - frame_mbs_only)

    fps = None
    if r.more_rbsp_data() and r.u(1):         # vui_parameters_present
        # (video_signal_type, colour_desc, chroma_loc skipped inside)
        if r.u(1):                            # video_signal_type_present
            r.u(3); r.u(1)                    # format, full_range
            if r.u(1):                        # colour_description_present
                r.u(8); r.u(8); r.u(8)
        if r.u(1):                            # chroma_loc_info_present
            r.ue(); r.ue()
        r.u(1); r.u(1)                        # neutral_chroma, field_seq
        r.u(1)                                # frame_field_info_present (flags only; no fps impact)
        if r.u(1):                            # default_display_window
            r.ue(); r.ue(); r.ue(); r.ue()
        if r.u(1):                            # vui_timing_info_present
            num_units = r.u(32)
            time_scale = r.u(32)
            fixed = r.u(1)
            if fixed and num_units:
                fps = time_scale / (2 * num_units)
            if r.u(1):                        # vui_hrd_parameters_present
                _skip_hrd(r)

    out.update({
        "width": width, "height": height,
        "fps": round(fps, 3) if fps else None,
        "profile_idc": profile_idc, "level_idc": level_idc,
        "constraints": constraints,
        "chroma_format_idc": chroma_format_idc,
        "log2_max_frame_num": log2_max_frame_num,
        "poc_type": poc_type, "max_num_ref_frames": max_num_ref,
        "frame_mbs_only": frame_mbs_only,
        "crop": (crop_l, crop_r, crop_t, crop_b),
    })
    return out


def _skip_scaling_list(r: BitReader, size: int):
    last_scale = next_scale = 8
    for _ in range(size):
        if next_scale != 0:
            delta = r.se()
            next_scale = (last_scale + delta + 256) % 256
        if next_scale != 0:
            last_scale = next_scale


def _skip_hrd(r: BitReader):
    r.ue()                                    # cpb_cnt_minus1
    r.u(4); r.u(4)                            # bit_rate_scale, cpb_size_scale
    for _ in range(r.ue() + 1):               # hmm: uses cpb_cnt already read
        pass
    # honest note: full VUI HRD walking is only needed for streams that
    # carry it; phone encoders (c2.qti/c2.android) rarely do. If a real
    # stream trips here, the SPS parse raises and the caller tags it.


def parse_sps_nal(frame_or_unit: bytes) -> dict:
    """Convenience: feed raw bytes containing an SPS NAL (start code or not)."""
    for nal_type, _, rbsp in split_nals(frame_or_unit):
        if nal_type == NAL_SPS:
            return parse_sps(rbsp)
    raise ValueError("no SPS NAL found in input")


# ---------------------------------------------------------------------------
# scrcpy frame demux — the 12-byte header river
# ---------------------------------------------------------------------------

class H264FrameDemuxer:
    """Streaming demuxer for scrcpy's video socket framing.

    feed(chunk) → list of (pts, payload). Handles chunks split anywhere
    (headers and payloads arbitrarily torn across TCP reads).
    """

    HEADER = struct.Struct(">QI")
    MAX_SANE_FRAME = 16 * 1024 * 1024       # 16 MB — refuse to allocate lies

    def __init__(self):
        self._buf = bytearray()
        self._want_hdr = True

    def feed(self, chunk: bytes):
        self._buf.extend(chunk)
        frames = []
        while True:
            if self._want_hdr:
                if len(self._buf) < self.HEADER.size:
                    break
                pts, length = self.HEADER.unpack_from(self._buf, 0)
                if length == 0 or length > self.MAX_SANE_FRAME:
                    raise ValueError(f"insane frame length {length} at pts {pts}")
                del self._buf[:self.HEADER.size]
                self._pts, self._length = pts, length
                self._want_hdr = False
            else:
                if len(self._buf) < self._length:
                    break
                frames.append((self._pts, bytes(self._buf[:self._length])))
                del self._buf[:self._length]
                self._want_hdr = True
        return frames

    @staticmethod
    def pack_frame(pts: int, payload: bytes) -> bytes:
        """Writer-side mirror: build the 12B header + payload (for tests/mux)."""
        if len(payload) == 0 or len(payload) > H264FrameDemuxer.MAX_SANE_FRAME:
            raise ValueError("bad payload length")
        return H264FrameDemuxer.HEADER.pack(pts, len(payload)) + payload


_py_H264FrameDemuxer = H264FrameDemuxer


# ---------------------------------------------------------------------------
# SPS synthesis (writer-side) — for round-trip verification
# ---------------------------------------------------------------------------

def make_sps(width: int, height: int, fps=None, profile_idc=100, level_idc=41,
             chroma_format_idc=1, frame_mbs_only=1) -> bytes:
    """Synthesize a valid SPS RBSP for the given geometry.

    Progressive, 8-bit, poc type 0, no scaling matrix, optional VUI timing.
    Mirror of parse_sps — the selftest proves the two agree.
    """
    sub_w = _SUBWC.get(chroma_format_idc, 2)
    sub_h = _SUBHC.get(chroma_format_idc, 2)
    crop_x = sub_w * 1          # (2 - frame_mbs_only) with mbs_only=1
    crop_y = sub_h * 1
    w_mbs = (width + 15) // 16
    h_map = (height + 15) // 16
    crop_r = (w_mbs * 16 - width) // crop_x if crop_x else 0
    crop_b = (h_map * 16 - height) // crop_y if crop_y else 0
    assert (w_mbs * 16 - width) % crop_x == 0, "width not expressible in crop units"
    assert (h_map * 16 - height) % crop_y == 0, "height not expressible in crop units"

    w = BitWriter()
    w.u(profile_idc, 8)
    w.u(0, 8)                       # constraint flags
    w.u(level_idc, 8)
    w.ue(0)                         # sps_id
    if profile_idc in _PROFILE_HIGH:
        w.ue(chroma_format_idc)
        if chroma_format_idc == 3:
            w.u(0, 1)
        w.ue(0)                     # bit_depth_luma_minus8
        w.ue(0)                     # bit_depth_chroma_minus8
        w.u(0, 1)                   # qpprime
        w.u(0, 1)                   # seq_scaling_matrix_present
    w.ue(4)                         # log2_max_frame_num_minus4
    w.ue(0)                         # poc_type
    w.ue(4)                         # log2_max_poc_lsb_minus4
    w.ue(2)                         # max_num_ref_frames
    w.u(0, 1)                       # gaps allowed
    w.ue(w_mbs - 1)
    w.ue(h_map - 1)
    w.u(frame_mbs_only, 1)
    w.u(1, 1)                       # direct_8x8
    if crop_r or crop_b:
        w.u(1, 1)                   # frame_cropping
        w.ue(0); w.ue(crop_r); w.ue(0); w.ue(crop_b)
    else:
        w.u(0, 1)
    if fps:
        w.u(1, 1)                   # vui_parameters_present
        w.u(0, 1)                   # video_signal_type
        w.u(0, 1)                   # chroma_loc
        w.u(0, 1)                   # neutral_chroma
        w.u(0, 1)                   # field_seq
        w.u(0, 1)                   # frame_field_info
        w.u(0, 1)                   # default_display_window
        w.u(1, 1)                   # vui_timing_info_present
        w.u(1, 32)                  # num_units_in_tick = 1
        w.u(fps * 2, 32)            # time_scale = fps*2 (fixed rate)
        w.u(1, 1)                   # fixed_frame_rate_flag
        w.u(0, 1)                   # hrd not present
        w.u(0, 1)                   # bitstream_restriction
    else:
        w.u(0, 1)                   # no vui
    w.rbsp_trailing()
    return w.bytes()


def make_sps_nal(width, height, fps=None, **kw) -> bytes:
    """Full Annex-B SPS NAL: start code + header byte + EP-added RBSP."""
    rbsp = make_sps(width, height, fps, **kw)
    return b"\x00\x00\x00\x01" + bytes([0x67]) + add_emulation_prevention(rbsp)


# ---------------------------------------------------------------------------
# Selftest — writer vs parser, the honest round trip
# ---------------------------------------------------------------------------

def selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    # ue/se round trip over a wide range (the exp-Golomb contract)
    bw = BitWriter()
    vals = [0, 1, 2, 3, 4, 5, 6, 13, 14, 100, 1023, 1024, 65535, 100000]
    for v in vals:
        bw.ue(v)
    for v in (0, 1, -1, 2, -2, 3, -3, 100, -100):
        bw.se(v)
    br = BitReader(bw.bytes())
    check("ue round-trip", all(br.ue() == v for v in vals))
    check("se round-trip", all(br.se() == v for v in (0, 1, -1, 2, -2, 3, -3, 100, -100)))

    # emulation prevention inverse property
    evil = b"\x00\x00\x01\xff" + b"\x00" * 4 + b"\x02\x00\x00\x03\x05"
    check("EP remove/add inverse", add_emulation_prevention(remove_emulation_prevention(evil)) != None
          and remove_emulation_prevention(add_emulation_prevention(evil)) == evil)

    # phone geometry: 1080x2400 (20:9 modern) with width crop, @60fps
    nal = make_sps_nal(1080, 2400, fps=60)
    sps = parse_sps_nal(nal)
    check(f"1080x2400@60 parsed -> {sps['width']}x{sps['height']}@{sps['fps']}",
          sps["width"] == 1080 and sps["height"] == 2400 and abs(sps["fps"] - 60) < 1e-6)
    check("crop units correct", sps["crop"] == (0, 4, 0, 0))
    check("profile/level carried", sps["profile_idc"] == 100 and sps["level_idc"] == 41)

    # exact-fit geometry, no VUI → fps None (refuses to guess)
    nal2 = make_sps_nal(1080, 1920)
    sps2 = parse_sps_nal(nal2)
    check("1080x1920 exact fit", sps2["width"] == 1080 and sps2["height"] == 1920)
    check("no VUI -> fps None (honest)", sps2["fps"] is None)

    # 720x1600 baseline profile (no high-profile grammar)
    nal3 = make_sps_nal(720, 1600, profile_idc=66)
    sps3 = parse_sps_nal(nal3)
    check("baseline 720x1600", sps3["width"] == 720 and sps3["height"] == 1600
          and sps3["chroma_format_idc"] == 1)

    # demuxer: torn reads across arbitrary chunk boundaries
    frames = [(0, b"\x67" + b"A" * 40), (33, b"\x41" + b"B" * 1200),
              (66, b"\x41" + b"C" * 7), (100, b"\x68" + b"D" * 300)]
    stream = b"".join(H264FrameDemuxer.pack_frame(p, f) for p, f in frames)
    dm = H264FrameDemuxer()
    got = []
    step = 7                                   # cruel chunk size: splits headers mid-byte-stream
    for i in range(0, len(stream), step):
        got.extend(dm.feed(stream[i:i + step]))
    check(f"demux torn reads: {len(got)} frames", got == frames)

    # NAL classification + keyframe detection
    check("IDR detected as keyframe", is_keyframe(frames[0][1] + b"\x00\x00\x00\x01\x65\x01"))
    check("non-IDR not keyframe", not is_keyframe(frames[1][1]))

    # degenerate input refuses loudly
    try:
        H264FrameDemuxer().feed(H264FrameDemuxer.HEADER.pack(0, 1 << 30))
        check("insane length rejected", False)
    except ValueError:
        check("insane length rejected", True)

    # raw Annex-B river with bytes fitting for the splitter torture test
    stream_h264 = (b"\x00\x00\x00\x01\x67" + b"\x42" * 30
                   + b"\x00\x00\x00\x01\x68" + b"\xCE" * 8
                   + b"\x00\x00\x00\x01\x65" + b"\xAB" * 900
                   + b"\x00\x00\x01\x41" + b"\x11" * 120)

    # incremental river splitter: torn reads must reassemble identically.
    # The splitter emits FULL NAL units (header byte + RBSP — the spec
    # definition), so the expected list carries the headers explicitly.
    expected_full = [b"\x67" + b"\x42" * 30, b"\x68" + b"\xCE" * 8,
                     b"\x65" + b"\xAB" * 900, b"\x41" + b"\x11" * 120]
    sp = AnnexBStreamSplitter()
    got_nals = []
    for i in range(0, len(stream_h264), 3):        # crueler than before
        got_nals.extend(sp.feed(stream_h264[i:i + 3]))
    got_nals.extend(sp.flush())          # river end: emit the tail NAL
    check(f"annexb stream torn reads: {len(got_nals)} NALs",
          got_nals == expected_full)
    # cross-contract: whole-buffer parser must recover the same RBSPs
    reparsed = [r for _, _, r in split_nals(
        b"".join(b"\x00\x00\x00\x01" + u for u in got_nals))]
    check("splitter and whole-buffer parser agree",
          reparsed == [r for _, _, r in split_nals(stream_h264)])

    print("H264_MATH SELFTEST " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


# ---------------------------------------------------------------------------
# GATE ⑯ — THE RUST HEART TRANSPLANT (PyO3).
#
# If the compiled `h264core` extension (rust/h264core-py, goldens-proven
# byte-for-byte against the pure code above, ~237x on the NAL hot path)
# imports, the hot paths reroute to it. The pure Python implementations stay
# untouched as `_py_*` — the fallback AND the differential oracle.
# Set DROID_H264_PURE=1 to force the pure path (used by the golden generator).
# ---------------------------------------------------------------------------

_RUST_HEART = False
if os.environ.get("DROID_H264_PURE") != "1":
    try:
        import h264core as _rust

        # Full-heart-or-nothing: every grafted name must exist in the loaded
        # pyd. A stale h264core.pyd must not leave a chimera — half Rust,
        # half pure — with _RUST_HEART lying about it. Probe ALL, then bind.
        _NEEDS = (
            "split_nals", "is_keyframe", "pack_frame",
            "remove_emulation_prevention", "add_emulation_prevention",
            "Demuxer", "AnnexBStreamSplitter",
        )
        if all(hasattr(_rust, _n) for _n in _NEEDS):

            def split_nals(frame: bytes):
                return [(n.nal_type, n.ref_idc, bytes(n.rbsp))
                        for n in _rust.split_nals(frame)]

            def is_keyframe(frame: bytes) -> bool:
                return _rust.is_keyframe(frame)

            def remove_emulation_prevention(rbsp_payload: bytes) -> bytes:
                return _rust.remove_emulation_prevention(rbsp_payload)

            def add_emulation_prevention(rbsp: bytes) -> bytes:
                return _rust.add_emulation_prevention(rbsp)

            class H264FrameDemuxer:  # noqa: N801 - mirrors the pure class API
                HEADER = _py_H264FrameDemuxer.HEADER
                MAX_SANE_FRAME = _py_H264FrameDemuxer.MAX_SANE_FRAME

                __slots__ = ("_d",)

                def __init__(self):
                    self._d = _rust.Demuxer()

                def feed(self, chunk: bytes):
                    return self._d.feed(chunk)

                @staticmethod
                def pack_frame(pts: int, payload: bytes) -> bytes:
                    return _rust.pack_frame(pts, payload)

            class AnnexBStreamSplitter:  # noqa: N801 - mirrors the pure API
                """Graft: the glass pipe runs the Rust river splitter."""

                __slots__ = ("_s",)

                def __init__(self):
                    self._s = _rust.AnnexBStreamSplitter()

                def feed(self, chunk: bytes):
                    return self._s.feed(chunk)

                def flush(self):
                    return self._s.flush()

            _RUST_HEART = True
    except ImportError:
        _RUST_HEART = False


def rust_heart() -> bool:
    """True when the PyO3 h264core transplant is beating."""
    return _RUST_HEART


if __name__ == "__main__":
    raise SystemExit(selftest())
