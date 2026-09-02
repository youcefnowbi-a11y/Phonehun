# doctrine: wake_and_see
title: Wake the phone and see before touching anything
when: screen, wake, unlock, see, look, screenshot, capture, lockscreen, display
not_when:
tier: core

## THE CHAIN (follow it in order — every skip has cost us a wasted round)

1. `list_devices` — if empty, STOP and report. Never fabricate a serial.
   A device on USB shows state "device". "unauthorized" = tell the operator
   to check the phone screen for the RSA prompt. "offline" = replug.
2. `screen_key` code 224 (WAKEUP) — wakes a sleeping screen.
3. `screen_key` code 82 (MENU) — raises the lockscreen from doze.
4. `screen_capture` — LOOK. JPEG lands in cortex_shots\ on the panel.
   You cannot see pixels (no image input): verify with numbers —
   `bytes > 15000` means a real frame, tiny bytes = black screen.
5. To know what is on screen without eyes: `dumpsys` service "window"
   (look for mCurrentFocus / mDreamingLockscreen) or
   `shell dumpsys window | findstr mCurrentFocus`.
6. Coordinates are DEVICE-space: 720 wide x 1600 tall on the A21s.
   The center of the screen is (360, 800). Bottom third starts at y>1050.
7. After every tap: capture again. Verify, never assume.

## HARD RULES
- Tap blind = tap twice. Capture, tap, capture.
- If the screen is off and keys do nothing, check `battery` — a dead
  battery mimics a broken phone.
- Record what worked in memory_append (section lessons). The next you
  should not rediscover this.
