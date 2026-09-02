# h264core-py — `import h264core`

The PyO3 skin over the pure `h264core` crate (gate ⑯½). Exposes the
h264_math.py hot path to Python as a native extension: split_nals,
is_keyframe, pack_frame, Demuxer, emulation prevention — with exact
error-message parity against the pure oracle.

## Rebuild (GNU toolchain — msvc host has no link.exe)

```powershell
$env:PYO3_PYTHON = "C:\Users\PC\AppData\Local\Programs\Python\Python311\python.exe"
& "$env:USERPROFILE\.cargo\bin\cargo.exe" +stable-x86_64-pc-windows-gnu build --release
Copy-Item target\release\h264core.dll `
  "C:\Users\PC\AppData\Local\Programs\Python\Python311\Lib\site-packages\h264core.pyd"
```

## Escape hatch

`DROID_H264_PURE=1` forces h264_math.py onto the pure Python path
(fallback + golden oracle). gen_goldens.py pins this automatically —
the oracle must never generate from the implementation it judges.

## Proof chain (2026-09-03)

- pyd_probe: ALL PASS (roundtrip, torn reads, error parity)
- h264_math selftest: PASSED with heart AND pure (15/15 checks each)
- goldens: Python oracle -> dc_test replay, 0 failures
- yardstick through the bridge: NAL 14.40 ms -> 0.080 ms (~180x)
