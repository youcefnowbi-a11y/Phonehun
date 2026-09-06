# doctrine: zero_touch_unlock
title: Unlock a phone with no debugging, no USB, no adb — channels, keys, hands
when: unlock, locked, lockscreen, pin, password, pattern, no debugging, without debugging, no adb, zero touch, brute, siege, find my device, smart lock, samsung account, remote unlock, frp
not_when: usb, debugging enabled, authorized, serial
tier: core

## THE PURPOSE (GATE-17.14 — read before walking the tree)
The product is AUTONOMOUS UNLOCK: a locked bird arrives, its owner is
ABSENT, and the SYSTEM opens it. The owner's finger, face, or known
pattern is NOT a solution — it is the job unsold. Every stage below is
walked to open the lock WITHOUT a human body. The owner's hands and eyes
are measurement instruments (reading a pairing code, holding a cable
combo), never the key itself. An unlock delivered by the owner's body
is a failed mission, whatever was extracted beside it.

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
   - Android 11+ wireless debugging is NOT 5555: it announces over mDNS
     (`_adb-tls-connect._tcp` / `_adb-tls-pairing._tcp`) and pairs with a
     6-digit code shown on the phone screen (Settings → Developer options
     → Wireless debugging → Pair device). Ask the operator to read the
     code and the pairing port; pair, connect, then wake_and_see takes
     over. First connection still shows an RSA prompt on the phone.
   - 8008/8009 (cast), 2121/445 (ftp/samba), 8080+ web panels = recon
     gold; log every banner. They may not unlock, but they map the device.
4. THE ACCOUNT KEYS — the only true REMOTE unlock that exists:
   - Samsung + SmartThings Find with "Remote unlock" armed in settings →
     the Samsung account login opens the lock from anywhere. ASK THE
     OPERATOR for the credentials (say to operator) — do not guess.
     This is an ENGINEERED unlock (the account is the key, not a body)
     and counts as a win.
   - Google Find My Device: RING and LOCATE only. It cannot unlock a
     secure lock. ERASE is not unlock — it trips FRP and bricks the goal.
   - Xiaomi Mi Cloud / Huawei Find Device: partial, mostly erase-only.
5. ENGINEERED ATTACK SURFACES (no owner body, ever):
   - Biometrics: enrollment state = INTEL (dumpsys fingerprint/biometric).
     Map refresh windows, strongAuth transitions, sensor class. NEVER
     direct the owner onto the sensor as the solution — bank the surface
     for the access phase AFTER an engineered unlock.
   - Credential artifacts: see low_level_credential doctrine — pull the
     artifact map when privilege allows, attack OFFLINE (GPU, no lockouts),
     or surgically remove the gate when the data trade is operator-approved.
   - Trusted environment: Smart Lock BLE MAC spoof from the panel radio
     (paired watch/buds actively scanned for); trusted places worth only
     if the bird moved to an untrusted zone.
   - Model-specific software history: paste-overflow, camera-switch bugs —
     version triage by fingerprint from stage 2; Android 7+ patched builds
     are DEAD, say so, do not perform them.
6. THE SIEGE (autonomous candidate engine — no owner input):
   - Statistical ordering: 1234, 0000, 1111, 2580, 1212, birth years
     19xx/20xx, 1122, 1313, then operator-provided context FACTS (dates,
     repeats) typed as data — the owner answers questions, he does not
     touch the phone.
   - Lockout curve respected: 5 tries → 30s, 5m, 15m, 1h... Track the
     timer yourself; never strike during a window.
   - Run autonomously: attempt, verify deviceLocked, adapt. Max 2 real
     attempts unless a counter PROVES attempts register zero (phantom
     walls) — GATE-17.13. A siege that burns lockouts for show is stone
     age theater.
7. LAST RESORT — operator credential handover is REPORTED as fallback:
   if every engineered channel closed, say plainly: "all autonomous
   doors closed; the remaining doors are owner-supplied credentials or
   physical rig work (combination flash on a sacrificial bird, ISP,
   chip-off)." The operator decides. The mission report never dresses
   an owner-body unlock as a win.

## THE CABLE THAT LIES (scenario: USB plugged in, debugging OFF)

- A USB cable with debugging off is a CHARGING cable. adb sees nothing —
  do not call adb tools and do not pretend the serial exists.
- MTP/PTP file access over USB requires the phone unlocked AND a
  phone-side accept. Locked phone = no data. Do not chase it.
- What the cable DOES buy: physical modes.
  - Samsung: Vol DOWN + Vol UP while plugging → Download Mode (Odin).
    Stock flash WIPES the device and lands in FRP — escape, not unlock.
    Combination flash chain = sacrificial-bird work (service_center
    doctrine), reported with its data-risk in the same breath.
  - Qualcomm EDL (9008): needs a signed vendor firehose for that exact
    model — unobtainable for modern devices; unlocked-by-EDL still fails
    on hardware-keyed userdata. Research path, not a plan.
  - fastboot: locked bootloaders refuse unsigned boots; `oem unlock`
    WIPES and trips FRP.
- Verdict to report: "cable gives physical modes, all of which destroy
  data. The lock survives. Continue with network or credential paths."

## THE WALLS (report them, do not perform around them)

- Android 9+ fully patched: hardware-backed keystore (Gatekeeper/Weaver).
  No software unlock exists without credentials or a device-specific
  exploit. State the wall class plainly: "credential path or physical rig".
- FRP: any erase/wipe path demands the Google creds AFTER the wipe too.
  Erasing is failing with extra steps.
- Biometric-only surfaces: adb never lifted a fingerprint and neither
  will you. The credential artifact attack (offline) is the engineering
  path; the owner's body is not a path at all.

## HARD RULES

- Every stage ends with a REPORT: what was probed, what answered, what
  closed. "Nothing worked" is a report; "nothing happened" is not.
- Record model, patch level, and every closed door in memory_append.
  The next siege starts smarter.
- The owner's body never touches the bird as a key (GATE-17.14). His
  answers are data; his hands on the DEVICE are a mission failure.
- If the operator says stop, stop. Lockouts outlive your patience.
