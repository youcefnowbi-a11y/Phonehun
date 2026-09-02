# -*- coding: utf-8 -*-
"""Pure-vs-Rust differential for every organ of h264_math.

Discipline: the `_py_*` aliases are the PURE oracle implementations (bound
before any graft rebinding, so they stay pure even in a grafted process).
`import h264core` is the Rust heart, called directly. Byte-exact parity is
required — including error messages, per-chunk emission attribution, and
API misuse (double flush must return [] the second time, oracle-true).

Exit 0 = hearts agree everywhere. Exit 1 = divergence (with the case).
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import h264_math as m          # noqa: E402  (grafted view)
import h264core as rust        # noqa: E402  (the heart, called directly)

fails = 0


def check(name, cond, detail=""):
    global fails
    if cond:
        print("PASS " + name)
    else:
        fails += 1
        print("FAIL " + name + ((" :: " + str(detail)) if detail else ""))


# --- pure oracle handles -----------------------------------------------------
py_split = m._py_split_nals
py_kf = m._py_is_keyframe
py_demux = m._py_H264FrameDemuxer
py_splitter = m._py_AnnexBStreamSplitter
py_rm_ep = m._py_remove_emulation_prevention
py_add_ep = m._py_add_emulation_prevention


def rust_nals(f):
    return [(n.nal_type, n.ref_idc, bytes(n.rbsp)) for n in rust.split_nals(f)]


# --- corpus ------------------------------------------------------------------
rng = random.Random(1642)


def synth_frame(n_units=1):
    out = bytearray()
    for _ in range(n_units):
        sc = rng.choice([b"\x00\x00\x01", b"\x00\x00\x00\x01"])
        hdr = rng.choice([0x67, 0x68, 0x65, 0x41, 0x01, 0x06, 0x09, 0x0F])
        plen = rng.randrange(0, 60)
        payload = bytes(rng.randrange(256) for _ in range(plen))
        out += sc + bytes([hdr]) + payload
    if rng.random() < 0.5:
        out += b"\x00" * rng.randrange(1, 4)
    return bytes(out)


frames = [
    b"",                                     # empty
    b"\x00\x00\x01",                         # lone 3B code
    b"\x00\x00\x00\x01",                     # lone 4B code
    b"\x00\x00\x02",                         # near-code, not a code
    b"\x00\x00",
    b"\x00",
    b"JUNKJUNK",                             # garbage
    b"\x00\x00\x01\x00\x00\x01\x65\x11",     # adjacent codes
    b"\x00\x00\x00\x01\x67\x42\x43\x00\x00\x01\x65\x99",   # 4B then 3B
    b"\x00\x00\x00\x00\x00\x01\x65\xAA",     # zeros before start code
    b"\x00\x00\x01\x65" + b"\xAB" * 17,      # 17-byte payload frame
    b"\x00\x00\x01\x67" + b"\x00" * 8,       # all-zero payload (rstrip case)
]
frames += [synth_frame(rng.randrange(1, 5)) for _ in range(40)]

# --- 1. split_nals -----------------------------------------------------------
bad = [(i, f) for i, f in enumerate(frames) if py_split(f) != rust_nals(f)]
check("split_nals parity (%d frames)" % len(frames), not bad, bad[:3])

# --- 2. is_keyframe ----------------------------------------------------------
bad = [(i, f) for i, f in enumerate(frames) if py_kf(f) != rust.is_keyframe(f)]
check("is_keyframe parity", not bad, bad[:3])

# --- 3. emulation prevention -------------------------------------------------
ep_inputs = [
    b"", b"\x00", b"\x00\x00", b"\x00\x00\x00", b"\x00\x00\x03",
    b"\x00\x00\x03\x00", b"\x00\x00\x03\x03", b"\x00\x00\x04",
    b"\x41\x00\x00\x01\x99\x00\x00\x03\x02", b"\x00\x00\x01\xff\x00\x00\x00",
]
for _ in range(30):
    base = bytes(rng.randrange(256) for _ in range(rng.randrange(0, 80)))
    ep_inputs.append(base)
    ep_inputs.append(base + b"\x00\x00\x03\x05")

bad_rm = [x for x in ep_inputs if py_rm_ep(x) != rust.remove_emulation_prevention(x)]
check("remove_emulation_prevention parity (%d inputs)" % len(ep_inputs),
      not bad_rm, bad_rm[:2])
bad_add = [x for x in ep_inputs if py_add_ep(x) != rust.add_emulation_prevention(x)]
check("add_emulation_prevention parity", not bad_add, bad_add[:2])

# --- 4. demuxer --------------------------------------------------------------
payloads = [
    b"\x00\x00\x00\x01\x67\x42\x43",
    b"\xAB" * 17,                            # the 17-byte payload
    b"\x00\x00\x01\x65" + bytes(rng.randrange(256) for _ in range(100_000)),
    b"\x99",
]
stream = b"".join(py_demux.pack_frame(pts, p) for pts, p in zip((0, 33, 66, 100), payloads))

for tear in (1, 2, 3, 5, 11, 12, 13, 64, 4096):
    pd, rd = py_demux(), rust.Demuxer()
    pout, rout = [], []
    for i in range(0, len(stream), tear):
        pout += pd.feed(stream[i:i + tear])
        rout += rd.feed(stream[i:i + tear])
    check("demux tear@%d parity (%d frames)" % (tear, len(pout)),
          pout == rout and pout == list(zip((0, 33, 66, 100), payloads)),
          (len(pout), len(rout)))

# 17-byte payload vs a buffer CLAIMING 21: both must wait, then complete.
d1, d2 = py_demux(), rust.Demuxer()
hdr = py_demux.HEADER.pack(7, 21)
o1 = d1.feed(hdr + b"\xCD" * 17)
o2 = d2.feed(hdr + b"\xCD" * 17)
check("demux short-payload wait parity (17 vs claimed 21)",
      o1 == o2 == [] , (o1, o2))
o1 = d1.feed(b"\xCD" * 4)
o2 = d2.feed(b"\xCD" * 4)
check("demux short-payload complete parity",
      o1 == o2 == [(7, b"\xCD" * 21)], (o1, o2))

# insane-length error parity (exact message)
errs = []
for d in (py_demux(), rust.Demuxer()):
    try:
        d.feed((12345).to_bytes(8, "big") + (32 * 1024 * 1024).to_bytes(4, "big"))
        errs.append("no-raise")
    except ValueError as e:
        errs.append(str(e))
check("demux insane-length message parity", errs[0] == errs[1], errs)

# zero length + pack error parity
errs = []
for d in (py_demux(), rust.Demuxer()):
    try:
        d.feed((5).to_bytes(8, "big") + (0).to_bytes(4, "big"))
        errs.append("no-raise")
    except ValueError as e:
        errs.append(str(e))
check("demux zero-length message parity", errs[0] == errs[1], errs)

for maker in (py_demux.pack_frame, rust.pack_frame):
    try:
        maker(1, b"")
        check("pack_frame empty parity (%r)" % maker, False, "no-raise")
    except ValueError as e:
        check("pack_frame empty parity (%s)" % ("py" if maker is py_demux.pack_frame else "rust"),
              str(e) == "bad payload length", str(e))

# --- 5. AnnexBStreamSplitter --------------------------------------------------
def stream_case(chunks):
    """Run one river through BOTH hearts; per-chunk, flush, double-flush."""
    ps, rs = py_splitter(), rust.AnnexBStreamSplitter()
    pc, rc = [], []
    for c in chunks:
        pc.append(ps.feed(c))
        rc.append(rs.feed(c))
    pf, rf = ps.flush(), rs.flush()
    pf2, rf2 = ps.flush(), rs.flush()   # oracle clears at flush → silent
    return pc, rc, pf, rf, pf2, rf2


# 5a. garbage prefix, torn codes, seams, empty chunks
body = (b"\x00\x00\x00\x01\x67\x42\x43\xA1"
        b"\x00\x00\x01\x65\x11\x22\x33"
        b"\x00\x00\x00\x01\x68\xEE\xBB\x00\x00")
streams = [
    ("torn@1", [body[i:i + 1] for i in range(0, len(body), 1)]),
    ("garbage-prefix", [b"JUNK\x00\x00", body]),
    ("4B-code-split", [b"\x00\x00", b"\x00\x01\x68\xEE\xBB"]),
    ("no-codes", [b"\x01\x02", b"\x03\x04", b"\x05"]),
    ("lone-code-payload", [b"\x00\x00\x01", b"\x65\xAA", b"\xBB"]),
    ("empty-chunks", [b"", body, b"", b"\x00\x00", b""]),
    ("zeros-only", [b"\x00" * 5, b"\x00" * 5]),
    ("adjacent-codes", [b"\x00\x00\x01\x00\x00\x01\x41\x42"]),
    ("seam-zeros", [body + b"\x00\x00", b"", body]),
]
for name, chunks in streams:
    pc, rc, pf, rf, pf2, rf2 = stream_case(chunks)
    check("splitter %s per-chunk parity" % name, pc == rc,
          next((k for k in range(len(pc)) if pc[k] != rc[k]), None))
    check("splitter %s flush parity" % name, pf == rf, (pf, rf))
    # oracle-true: buffer cleared at flush, so a second flush emits nothing
    check("splitter %s double-flush silent" % name, pf2 == rf2 == [],
          (pf2, rf2))

# 5b. tear at EVERY offset 1..40 over the composite body
worst = None
for tear in range(1, 41):
    chunks = [body[i:i + tear] for i in range(0, len(body), tear)]
    pc, rc, pf, rf, pf2, rf2 = stream_case(chunks)
    if pc != rc or pf != rf:
        worst = (tear, pc, rc, pf, rf)
        break
check("splitter exhaustive tears 1..40 parity", worst is None, worst)

# 5c. whole-buffer helper vs torn river (if the pyd ships split_annexb_units)
if hasattr(rust, "split_annexb_units"):
    whole = [bytes(u) for u in rust.split_annexb_units(body)]
    ps = py_splitter()
    torn = []
    for i in range(0, len(body), 7):
        torn += ps.feed(body[i:i + 7])
    torn += ps.flush()
    check("split_annexb_units == torn river (tear@7)", whole == torn, (whole, torn))

print()
print("DIFF CHECK: %s (%d failure(s))" % ("PASSED" if fails == 0 else "FAILED", fails))
sys.exit(0 if fails == 0 else 1)
