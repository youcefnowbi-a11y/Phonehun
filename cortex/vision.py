#!/usr/bin/env python3
"""vision.py — THE C++ MUSCLE (via OpenCV bindings).

Where C++ wins in DroidCommand: per-frame pixel localization. The Python
bits-loop took 17.3 ms/frame; naive pure-Python NCC would take seconds per
frame. cv2 IS compiled C++ — SIMD, multithreaded — and runs this in
single-digit milliseconds. She starts to SEE here.

  find_template(image, template, threshold) -> (score, (x, y), (w, h))
  selftest() -> 0 — proves sub-image localization through JPEG artifacts
"""
import os
import sys
import time

import cv2
import numpy as np

SHOTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "cortex_shots")


def find_template(image, template, threshold=0.80):
    """Locate `template` inside `image` (BGR or gray). Returns
    (score, (x, y), (w, h)) — score<0 if not found above threshold.
    Single scale: screenshots are same-resolution by construction (720x1600)."""
    g = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    t = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY) if template.ndim == 3 else template
    if t.shape[0] > g.shape[0] or t.shape[1] > g.shape[1]:
        return -1.0, None, t.shape[::-1]
    res = cv2.matchTemplate(g, t, cv2.TM_CCOEFF_NORMED)
    _, score, _, loc = cv2.minMaxLoc(res)
    if score < threshold:
        return float(score), None, t.shape[::-1]
    return float(score), (int(loc[0]), int(loc[1])), t.shape[::-1]


def _render_pad(canvas, x, y):
    """Draw a 3x4 PIN keypad (digits 1-9, 0) at (x, y); 300x420 region."""
    d = 90  # button size
    for row in range(4):
        for col in range(3):
            cx, cy = x + col * d, y + row * 105
            cv2.rectangle(canvas, (cx, cy), (cx + d - 8, cy + d - 8), (90, 90, 90), -1)
            label = "123456789*0#"[row * 3 + col]
            cv2.putText(canvas, label, (cx + 30, cy + 60),
                        cv2.FONT_HERSHEY_SIMPLEX, 1.4, (255, 255, 255), 3, cv2.LINE_AA)


def selftest():
    """Existence proof: find the keypad in a JPEG-compressed screenshot."""
    # full 720x1600 lockscreen-like frame
    screen = np.full((1600, 720, 3), (40, 40, 48), np.uint8)
    cv2.putText(screen, "22:34", (280, 300), cv2.FONT_HERSHEY_SIMPLEX, 2.5, (230, 230, 230), 6, cv2.LINE_AA)
    pad_x, pad_y = 205, 900
    _render_pad(screen, pad_x, pad_y)
    template = screen[pad_y:pad_y + 420, pad_x:pad_x + 300].copy()  # exact crop, pre-JPEG

    # realistic capture: JPEG q70 artifacts + mild sensor-ish noise
    ok, buf = cv2.imencode(".jpg", screen, [cv2.IMWRITE_JPEG_QUALITY, 70])
    assert ok
    noisy = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    noise = np.random.default_rng(15).normal(0, 4.0, noisy.shape).astype(np.int16)
    captured = np.clip(noisy.astype(np.int16) + noise, 0, 255).astype(np.uint8)

    t0 = time.perf_counter()
    _warm = find_template(captured, template[10:110, 10:110], threshold=0.0)  # warmup: cvtColor/plan init
    warm_ms = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    score, loc, (w, h) = find_template(captured, template, threshold=0.80)
    ms = (time.perf_counter() - t0) * 1000

    dx = abs(loc[0] - pad_x) if loc else 999
    dy = abs(loc[1] - pad_y) if loc else 999
    print(f"vision selftest: score={score:.4f} loc={loc} (truth=({pad_x},{pad_y})) err=({dx},{dy})px")
    print(f"timing: first-call {warm_ms:.1f} ms (init) | steady-state {ms:.1f} ms/frame")
    assert loc is not None, "keypad NOT found through JPEG+noise"
    assert score >= 0.80, f"score too low: {score}"
    assert dx <= 2 and dy <= 2, f"localization drift {dx},{dy}px"
    assert ms < 50, f"steady-state too slow for per-frame use: {ms} ms"

    # negative control: wrong template must NOT match
    score2, loc2, _ = find_template(captured, cv2.flip(template, 1), threshold=0.80)
    print(f"negative control (flipped pad): score={score2:.4f} loc={loc2} (must be None)")
    assert loc2 is None, "false positive on wrong template"

    print("SELFTEST PASS — she can SEE through capture artifacts, per-frame budget intact")
    return 0


if __name__ == "__main__":
    sys.exit(selftest())
