# doctrine: low_level_credential
title: Credential engineering — the gate is a state, destroy it; guessing is stone age
when: pattern, pin, passcode, password, credential, lockscreen, keyguard, gatekeeper, weaver, spblob, locksettings, offline attack, brute, unlock, low level, surgery
tier: core

## THE LAW — CREDENTIAL IS A STATE, NOT A SECRET
The passcode is unreadable by ANY software — by design. But the gate that
enforces it is just FILES AND STATE on a disk. States can be destroyed,
replaced, or attacked offline. Guessing burns lockouts and risks the bird;
engineering burns bytes. NEVER spend device attempts on a digital pad when
an engineering path exists. On iOS-style devices, wrong attempts can
permanently disable or erase — attempt-guessing is not just weak, it is
self-sabotage.

## THE THREE AGES (escalate, never regress)
1. STONE AGE — on-device guessing. Lockouts punish the hammer. Allowed ONLY
   when a test proves attempts are FREE (phantom injections that register
   zero failures — verify with a lockout counter before spending more).
2. INDUSTRIAL AGE — OFFLINE brute force. Pull the credential artifacts off
   the device, attack them on GPU. No lockouts exist off-device. Speed is
   silicon, not attempts.
3. ENGINEERING AGE — state destruction. Remove the gate itself: delete the
   credential store, flash the gate away, or exploit the bootloader. The
   door is unmounted, not picked.

## ANDROID — ARTIFACT MAP (pull these before ANY destructive move)
- /data/system/locksettings.db (+ -wal, -shm) — the gate table.
- /data/system/gatekeeper.password.key, gatekeeper.pattern.key — verify blobs.
- /data/system/users/0/spblob/ — synthetic password blobs (weaver-wrapped
  on some builds; plain GateKeeper-wrapped on others).
- /data/system/users/0/password.key — legacy.
- Shell (uid 2000) CANNOT read /data/system. Root, recovery, or a raw
  partition read is the door to the artifact map. Map which door exists:
  `su` present? custom recovery flashed? bootloader unlocked?
  `shell getprop ro.boot.flash.locked ro.boot.verifiedbootstate`.

## ANDROID — OFFLINE ATTACK (industrial age)
- Samsung synthetic password + GateKeeper/Weaver blobs are crackable
  OFF-DEVICE: community hashcat modules eat spblob+gatekeeper.key pairs.
  Research the current module set online (self-arm), build the candidate
  space from intel (owner DOB, phone number, common patterns), attack on
  the panel GPU. Zero lockouts. Zero device risk.
- Pattern entropy is only 389,112 states (9 nodes, min-4) — a GPU eats
  that in minutes. PIN 4-6 digits: seconds to hours. The math is the
  weapon: offline, the "impossible" credential is a timetable.

## ANDROID — STATE SURGERY (engineering age)
- Root/recovery surgery: delete gatekeeper.*.key + locksettings.db* →
  boot → gate gone. TRADE: on FBE-CE birds the CE key may be SP-wrapped —
  gate removal can lock the data layer. DECISION MATRIX:
  - Data needed + CE-bound → EXTRACTION FIRST, then offline attack, and
    only then surgery. Never trade data for a door.
  - Data not needed / already extracted → surgery is the fast lane.
- Unlocked bootloader + Download mode: flash custom recovery (TWRP) →
  mount /data → raw pull or gate surgery. Samsung: Odin/Heimdall chain
  (see service_center doctrine); KG/RMM state and Knox eFuse are the
  price — sacrificial birds only unless operator overrides.
- Exynos → Download mode chain. MediaTek → mtkclient BROM (no auth,
  raw /data read = artifact map straight off the partition). Qualcomm →
  EDL firehose. UniSoC/Kirin → recovery/testpoint research first.

## iOS — NO GUESSING, EVER
- Wrong attempts escalate: disabled → erase. On-device guessing is
  FORBIDDEN by this doctrine.
- A11 and older: checkm8 bootrom (unpatchable) → pwned DFU → SSH ramdisk
  → mount /var → keybag/lockdown artifacts, offline analysis, or gate
  surgery on non-SE devices. A12+: SEP wall — pivot to data surfaces
  (backups, AFC, cloud artifacts) and SEP research before any strike.

## OPERATING SEQUENCE ON ANY LOCKED BIRD
1. Extraction sweep FIRST (data surface while it is open — see
   universal_device extraction ladder).
2. Map privilege doors: root? recovery? bootloader state? chip family?
3. Pull every credential artifact reachable. Bank them to the panel.
4. Choose the age: free attempts? → stone (rarely). Artifacts pulled?
   → industrial (GPU). Bootloader/flash door open? → engineering.
5. Report the plan in one line, then execute. The operator reads plain.

## HARD RULES
- Max 2 credential attempts per device, EVER, unless a lockout counter
  PROVES attempts register zero.
- Every surgery path reports its data-risk in the same breath.
- Battery >30% before any Download-mode work. SCOPE GUARD unchanged:
  the operator's personal bird is data-sacred; flash chains run only
  on birds he designates as sacrificial.
- The gate is engineering. The data is the prize. Guessing is surrender
  wearing a helmet.
