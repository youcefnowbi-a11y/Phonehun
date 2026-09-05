# doctrine: zero_touch_unlock
title: Unlock a phone with no debugging, no USB, no adb — channels, keys, hands
when: unlock, locked, lockscreen, pin, password, pattern, no debugging, without debugging, no adb, zero touch, brute, siege, find my device, smart lock, samsung account, remote unlock, frp
not_when: usb, debugging enabled, authorized, serial
tier: core

## THE TREE (walk it in order — every stage either opens a door or closes one)

1. NO adb EXISTS. Do not call screen_key, screen_capture, shell, or any
   serial tool. Without debugging the phone is a closed network node.
   Your hands are the OPERATOR. Your eyes are the OPERATOR. Direct them.
2. `network_sweep` — find the phone on the LAN. Fingerprint it: mDNS/SSDP
   names give model + Android version; open ports tell you what surfaces
   survive. An empty sweep is a truthful answer — report it, never invent.
3. PORT JACKPOTS — check before anything clever:
   - 5555 open = ADB-over-WiFi left armed in developer options.
     `adb connect <ip>:5555` — the whole adb belt just came back online.
     Jump to the wake_and_see doctrine and finish there.
   - 8008/8009 (cast), 2121/445 (ftp/samba), 8080+ web panels = recon
     gold; log every banner. They may not unlock, but they map the device.
4. THE ACCOUNT KEYS — the only true REMOTE unlock that exists:
   - Samsung + SmartThings Find with "Remote unlock" armed in settings →
     the Samsung account login opens the lock from anywhere. ASK THE
     OPERATOR for the credentials (say to operator) — do not guess.
   - Google Find My Device: RING and LOCATE only. It cannot unlock a
     secure lock. ERASE is not unlock — it trips FRP and bricks the goal.
   - Xiaomi Mi Cloud / Huawei Find Device: partial, mostly erase-only.
5. THE HANDS (operator as fingers, you as brain) — version triage by
   fingerprint from stage 2:
   - Android ≤6 / unpatched Samsung S6-S8 era: the paste-overflow trick —
     emergency dialer or password field, 100+ char input, clipboard paste
     crash exposes the launcher. Direct the operator's taps step by step.
   - Camera-switch / activity-jump bugs (patch level pre-2017): open
     camera from lockscreen, hammer notification shade during the jump.
   - Android 7+ / security patch 2017+: these are DEAD. Do not burn the
     operator's time performing them on a modern device. Say so and move.
6. THE SIEGE (human-in-the-loop brute) — if the operator consents to time:
   - Candidate ordering is statistical, not sequential: 1234, 0000, 1111,
     2580, 1212, birth years 19xx/20xx, 1122, 1313, then the operator's
     personal context (ask: dates, repeats, the model of the phone).
   - Lockout curve to respect: 5 tries → 30s, then 5m, 15m, 1h, escalating.
     Track the timer yourself. NEVER direct a tap during a lockout window.
   - The operator taps what you name and reads back what the screen says.
     You count attempts, you hold the timer, you adapt the candidates.
7. TRUSTED ENVIRONMENT — long shots, run only if the above closed:
   - Smart Lock trusted device: spoof the BLE MAC of a paired watch/buds
     from the PC radio if one exists; phone must be actively scanning.
   - Trusted place: geography is already true where the phone sits —
     worthless unless the phone has been moved to an untrusted zone.

## THE WALLS (report them, do not perform around them)

- Android 9+ fully patched: hardware-backed keystore (Gatekeeper/Weaver).
  No software unlock exists without credentials or a device-specific
  exploit. State the wall class plainly: "credential path or physical rig".
- FRP: any erase/wipe path demands the Google creds AFTER the wipe too.
  Erasing is failing with extra steps.
- Biometric-only surfaces: adb never lifted a fingerprint and neither
  will you. The PIN/password/pattern is the only door the siege sees.

## HARD RULES

- Every stage ends with a REPORT: what was probed, what answered, what
  closed. "Nothing worked" is a report; "nothing happened" is not.
- Record the device model, patch level, and every closed door in
  memory_append (section lessons). The next siege starts smarter.
- The operator's hands only move when you name the exact tap, and the
  operator's eyes only matter when you ask the exact question.
- If the operator says stop, stop. Lockouts outlive your patience.
