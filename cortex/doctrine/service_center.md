# doctrine: service_center
title: The market-grade path — Samsung service-center unlock (combination firmware) + FRP kill
when: combination, odin, heimdall, firmware, flash, frp, factory, service, reset, recovery, bricked, unusable, resell
tier: core

## THE MARKET TRUTH (why this doctrine exists)

Commercial unlock tools charge money because they sell TWO different products:
- DATA-PRESERVING unlock: credentials, siege, FMM remote unlock. Hard ceiling
  on patched hardware — this is the Cellebrite tier (nation-state money).
- DEVICE-RECOVERY unlock: phone usable again, data sacrificed. THIS is what
  the €30-60/phone market actually sells, and it is FULLY AUTOMATABLE.
Never conflate them in a report. Ask the objective once: "data or device?"
and pick the tier — but never offer both as a menu; execute the one the
objective names, and if the objective is ambiguous, DEFAULT to data-preserving
siege first, service path as the declared escalation.

## TIER B — SAMSUNG SERVICE-CENTER PATH (the real hammer)

Principle: Samsung combination firmware is OFFICIAL SIGNED Samsung software.
Flashing it in Download Mode is what Samsung service centers do daily.
It boots the phone into a factory-binary OS where the USER LOCK DOES NOT
EXIST and ADB IS ALWAYS ON. Knox warranty stays 0x0 (signed firmware).
Data on userdata is DESTROYED. That is the price. Say it once, plainly.

### Stage 1 — fingerprint the target (all from ADB, even locked)
- `shell getprop ro.product.model` → e.g. SM-A217F
- `shell getprop ro.build.version.incremental` + `ro.build.fingerprint`
  → build number + security patch level
- `shell getprop ro.boot.warrantybit` / `warranty_bit` → Knox state
- Binary version matters: combination firmware must MATCH OR EXCEED the
  current binary (anti-rollback). Parse the build date from the fingerprint.

### Stage 2 — arm the panel
- Tool: Heimdall (CLI, scriptable — HER weapon of choice) or Odin3 v3.14
  (GUI — operator's clicks, she directs). Odin needs Samsung USB drivers;
  Heimdall uses libusb and may need a Zadig driver swap — check with
  `host_shell heimdall version` / `heimdall detect` first.
- Firmware: stock from Frija/SamFW; COMBINATION from the combination
  mirrors (samfrew, samfw combination section, GSM forums). Filename shape:
  COMBINATION_FAC_FAxx_<MODEL>XXUxxxxx... — match MODEL exactly.
- Size warning: stock ~3-5GB. host_shell downloads are allowed; prefer
  the smaller COMBINATION file first (~500MB-1GB).
- Verify the tar: `host_shell tar -tf file.md5` — must contain
  boot.img, system.img, and for combination: factoryfs.img.

### Stage 3 — Download Mode and flash (operator's key-combo hands)
- Power off → Vol DOWN + Vol UP + cable (Samsung Download Mode).
- Volume UP to continue. Screen says "Downloading..." — do not touch.
- Heimdall flash (combination goes in the AP slot):
  `heimdall flash --AP <combination.tar.md5>` (add -- Pitt file only if
  the device demands repartition — NEVER by default).
- Odin equivalent: AP = combination tar, BL/CP/CSC empty. Start.

### Stage 4 — the combination OS (lock does not exist here)
- Device boots to factory binary UI. ADB is on automatically:
  `list_devices` should show it — the lockscreen war is over.
- FRP kill BEFORE leaving combination: dial *#0*# (or the boot test menu)
  → look for "FRP LOCK" toggle → set OFF. This is the menu service
  centers use; it clears the Knox FRP state so stock setup wizard never
  asks for the old Google account.
- If the toggle is absent in this combination build: `shell settings put
  secure frp_state 0` variants and `shell content query --uri` probes —
  then fall back to Stage 5.

### Stage 5 — back to stock, FRP-clean
- Download Mode again → flash STOCK (BL + AP + CP + CSC; use CSC, not
  HOME_CSC — this is a recovery flash, HOME_CSC preserves userdata and
  keeps stale FRP state).
- Boot → setup wizard must proceed with NO Google account prompt (FRP was
  killed in Stage 4). If it still asks: FRP bypass ladder, patch-dependent
  (TalkBack → Settings intent, SIM-pin settings jump, Smart Switch boot
  assist) — walk the operator tap by tap with EYES confirming each screen.

### Stage 6 — report and record
- Report: model, build, combination build used, FRP state before/after,
  final setup state. memory_append the working chain per model+build into
  lessons — the market advantage is compounding per-device knowledge.

## HARD RULES
- Never flash a combination built for a different MODEL. Near-miss models
  hard-brick. Model string must match exactly.
- Never repartition (no PIT) unless the device explicitly demands it.
- Combination flash DESTROYS userdata — confirm the objective accepts this
  before Stage 3. One line, not a menu; if the operator said "whatever it
  takes", that IS the confirmation.
- If Download Mode is blocked (MDM/Kiosk enrolled), report the enrollment
  wall — Tier B needs Download Mode, period.
- Knox eFuse: signed firmware keeps warranty bit at 0x0; any unsigned
  image or OEM-unlock toggle burns it permanently. Stay signed.
