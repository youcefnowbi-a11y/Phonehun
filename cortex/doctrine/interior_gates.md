# doctrine: interior_gates
title: Bit-level gate hunt — the system interior, not the screen
when: unlock, locked, gate, low level, interior, bits, system, services, binder, settings, trust, keyguard, hunt, deep
not_when: flash, download mode, odin
tier: core

## THE PERCEPTION LAW (GATE-17.15)
A human staring at this bird sees ONE thing: a pattern pad. You see the
MACHINE'S INTERIOR — services, binder transactions, settings rows, daemon
state, trust bits. The glass is the human's organ. The system plane is
yours. NEVER reason from the screen when the state exists — read the
state first, then decide. A locked screen is not a wall; it is one bit
of presentation over a whole machine you can interrogate. You do not
ignore the interior. You LIVE there.

## THE SWEEP (run on every bird, locked or not)

1. ENUMERATE THE INTERIOR:
   - `service list` — every bound service on the device.
   - `cmd -l` — every service exposing a shell verb interface.
   - `dumpsys -l` — every dumpable state surface.
   - For each lock-adjacent service (lock_settings, trust, keyguard,
     biometric/fingerprint, gatekeeper, keystore, device_policy,
     notification, accessibility, settings, backup, wifi, bluetooth):
     `cmd <svc>` or `cmd <svc> help` to dump its verbs. Every verb is a
     potential gate — catalog them all.
2. READ STATE TRUTH (the screen lies, dumpsys does not):
   - `dumpsys window policy` — keyguardShowing / keyguardOccluded bits.
   - `dumpsys trust` — trust agents, trusted state, unlocks.
   - `dumpsys biometric` / `dumpsys fingerprint` — enrollment, strongAuth.
   - KeyguardController under `dumpsys activity activities`.
   - locksettings.db metadata (size/journal = attempt-registered truth).
3. THE WRITE SURFACE (shell's privileges are real):
   - Shell holds WRITE_SECURE_SETTINGS. `settings list secure|global|system`
     and diff for lock-relevant rows (lockscreen.*, keyguard, trust,
     biometric, remote unlock flags).
   - Test-write ONLY rows that cannot brick or wipe; after EVERY write,
     re-read the keyguard state bits (step 2) and record the diff or the
     null effect. A write with no state diff is a closed lane — log it.
4. THE PRESENTATION PROBES:
   - `wm dismiss-keyguard` — fires the WindowManager verb; then diff
     `dumpsys window policy`. Secure keyguard → bouncer only; document
     the exact behavior class. Non-secure keyguard on any future bird →
     open door, take it.
5. RAW BINDER (the deepest shell reaches):
   - `service call <svc> <code> [args]` — transaction codes bypass the
     cmd wrapper. Build the code map ONLY with before/after dumpsys
     diffs, READ-ONLY verbs first. A destructive code (set/clear/erase/
     reset/delete) is FORBIDDEN without operator sign-off (SCOPE GUARD).
     Discovery discipline: one code per call, full diff, memory_append
     the result — the map outlives the mission.
6. TRUST ENVIRONMENT (gates the machine holds open):
   - Active trust agents from `dumpsys trust` — on-body, BT device,
     trusted place, Wi-Fi AOSP trust. An armed agent is a STATE FEED you
     can control from outside: BLE MAC spoof from the panel radio, LAN
     presence, location truth. Move the environment, not the screen.
7. PROFILE + ADMIN PLANES (the interior's second floor):
   - The bird's profile owner (Island, user 10), device admins, Knox
     surface: `dumpsys device_policy`, `dpm` verbs from shell. What an
     admin can do to lock posture (password requirements, keyguard
     features) maps what a shell CAN'T — and what a provisioned owner
     COULD on a sacrificial bird.

## CLASSIFY EVERYTHING — THE MAP IS THE DELIVERABLE

- DOORS: state bits you can move that change lock behavior.
- LEVERS: environment feeds you can control (trust, network, presence).
- BENCHES: surfaces that need privilege you lack today → name the
  privilege and the path that grants it (flash chain, recovery, root).
- WALLS: perm-denied physics (FBE-CE keys, spblob content, HAL internals)
  — name them exactly, never re-probe them out of hope.

## BUILDING GATES (when no door exists, engineer one)

- A gate is a STATE TRANSITION you can cause, not a credential you know.
- Chain surfaces: settings write + service verb + environment feed can
  compose into a state the lock accepts (e.g., trust feed + bouncer).
- When the interior is closed, the artifacts ARE the gate: map which
  privilege releases locksettings.db/spblob/gatekeeper blobs, and route
  that acquisition through the sacrificial plane (flash chain) — the
  offline attack is a build-order item, not a wish.
- Research mode (no bird attached): map model/chip/patch to known
  binder surfaces, CVE history, trust-agent feeds, and tool acquisition
  (hashcat + SP/GateKeeper modules for the operator's GPU rig).

## HARD RULES

- One probe, one diff, one log. Undiffed probes are noise, not hunting.
- READ-ONLY by default. Any state-changing verb on the operator's
  personal bird must be reversible in theory and logged in practice.
- Never burn lockouts for show (GATE-17.13). Never touch destructive
  codes without sign-off (SCOPE GUARD).
- The map is never finished: every service list changes per build —
  re-sweep on every new bird, save_skill the reusable sweep.
- You see bits. The human sees glass. Act like it.
