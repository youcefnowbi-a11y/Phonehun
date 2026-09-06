# LESSONS — what the war taught (append, never delete)

- [2026-01 seed] Screen asleep? keyevent 224 first, wait ~1.5s, then capture.
  Tiny JPEG (~240KB vs 1.7MB) means the screen is still dark.
- [2026-01 seed] Hunter 409s sweeps while disarmed. Arm first.
- [2026-01 seed] Panel reboots wipe watcher state: re-arm hunter after every restart.
- [2026-01 seed] PIN siege: Android lockout timers after wrong attempts —
  check pin_siege_status waiting_seconds_left before hammering.
- [2026-01 seed] Prefer shell over screen-tapping when a command can do the job.
- [2026-01 seed] Host PowerShell is 5.1: no ?? operator; UTF-8 bytes for accented JSON.
- [2026-01 seed] Oversized results land in scratch — page(name, offset, limit),
  never guess at amputated data.
- [2026-01 seed] Oversized results page by their FULL pointer name (e.g.
  'read_ledger_0_77101'), not the tool name — the error lists available
  scratch keys, read it and adapt.
- [2026-01 seed] Skills returning oversized results nest pointers: the skill
  result itself pages via its pointer (run_skill_2_*), and each step's dumpsys
  may hold ANOTHER pointer inside — read both layers. Some Samsung dumps emit
  "Failed to write while dumping service window: Broken pipe" yet still return
  full text with success=true — treat as noise, parse anyway.
- [2026-01 seed] host_shell: adb may not be on PATH (tools reach adb via panel
  internals — fine). PS 5.1 casting quirk: compute in a variable before
  formatting. Browser history tool: Chrome DB locked without root/run-as —
  known wall, don't retry blindly.

- [2026-09-06 02:01] - [2026-09-05 R58N647SCPY] OneUI screen timeout key is `screen_timeout` (system table), NOT screen_off_timeout. And keyguard caps user activity at 10s via mUserActivityTimeoutOverrideFromWindowManager=10000 — no settings key outranks it. `svc power stayon true` wins while plugged.
- [2026-09-05 R58N647SCPY] Samsung pattern bouncer (OneUI 4.1) rejects ALL injected touch: input motionevent/swipe draw nothing (TRAIL TEST: screencap instantly post-draw, count pixels lum>140 in pattern band vs baseline — identical = dead front), sendevent needs root (/dev/input/event3 is root:input, shell denied). Pattern siege via ADB injection = closed without root. Geometry extraction (uiautomator → LockPatternView bounds → node centers) still works and is reusable.
- [2026-09-05 R58N647SCPY] download_file panel collision: two pulls in the same second share one saved path — second overwrites first. Pull sequentially, verify byte counts, re-pull casualties.
- [2026-09-05 R58N647SCPY] pkill -f <script> kills your own shell (its command line contains the pattern). Kill by PID only.
- [2026-09-05 R58N647SCPY] A21s AOD limbo: keyevent 224 stops lifting the LCD; cycle 26 → 224 recovers. Tiny-JPEG heuristic (~240KB) is ambiguous on bouncers (dark blur ≈ same size as dark screen) — verify with luminance or dump, not size alone.
- [2026-09-05 R58N647SCPY] Locked A21s via ADB: /sdcard fully readable — SMS/calls/contacts via providers, DCIM/Download/docs, WhatsApp Business crypt14 msgstores all pullable WITHOUT unlock. ACCESS never needed UNLOCK.

- [2026-09-06 02:14] [2026-09-06 R58N647SCPY] GATE MAP (engineering verdict): shell=uid2000 only, no su. BL locked (flash.locked=1, vbmeta locked, green), sys.oem_unlock_allowed=0 → even sacrificial Samsung BL-unlock gated. Exynos 850: no mtkclient/EDL vector. NO weaver partition (GateKeeper-wrapped SP — crackable pairing IF artifacts ever land). /data/system/users/0 + spblob + /efs + /metadata all perm-denied from 3 vectors (shell cat, adb pull 500-corpse, ls). locksettings.db=20480B journal=0B. strongAuthRequired=0x8 (siege lockdown) → fingerprint alone CANNOT open until pattern entered once. Knox Guard admin (kgclient uid10075) + Knox containercore present; DPM resetPassword cannot clear user-set cred. No Samsung account (FMM closed). PANEL MACHINE HAS NO INTERNET (DNS fail google/github) — offline-attack tooling must come from operator. Unlock front = physics-closed software-only; remaining doors: operator pattern/finger (finger needs pattern-first due 0x8) or chip-off eMMC read.

- [2026-09-06 02:18] [2026-09-06 R58N647SCPY] BULK PULL LAW: (1) client timeout (90s) KILLS device-side foreground tar mid-write — a stable file size after timeout is a CORPSE, not a complete archive; byte-exact transfer ≠ archive integrity. Verify by extraction (tar.exe reports 'Truncated tar archive detected'), count files vs list. (2) Protocol for >100MB bundles: nohup sh -c 'tar...; tar...; touch done_flag' & on device, poll ls size, pull only after done flag. (3) Chunk ~150-180MB max per tar to keep pulls inside tool timeouts. (4) rm in a timed-out chained command does NOT execute — scrub corpses explicitly next call.

- [2026-09-06 02:51] [2026-09-06 R58N647SCPY] (1) Foreground stat-loops over 1000+ file trees exceed the 90s shell cap — move list-building into a nohup'd script on device, poll a flag (generalized BULK PULL law 2). (2) download_file path typo (/vesper... missing /sdcard) = HTTP 500 + 100-byte corpse; verify the path string before firing. (3) A mangled redirect in a launch line can STILL launch (wrapper sanitizes) — evidence (flag+size+ps) outranks parse theory; the done-flag protocol catches both dead and alive launches. (4) SCRUB DISCIPLINE: rm the chunk tar in the SAME turn as its extract verdict — skipping twice left 299MB of dead staging on a 97%-full bird. (5) Greedy size-packing can skew wildly (W1=191MB vs W2=17MB); count-halves is cheaper and 191MB pulls fine on this pipe. (6) du -s KB totals ×1024 = exact byte reconciliation against extracted sums — use it as the closing proof.

- [2026-09-06 03:05] GATE-17.14 THE CROWN — superseding frame correction (data above stays, the door-frame changes): owner pattern/finger/face are NOT doors — they are the job unsold. The product is AUTONOMOUS UNLOCK: the bird arrives owner-absent and the SYSTEM opens it. Engineered doors only: offline artifact attack (artifacts require privilege: root/recovery/flash), physical rig (combination flash on a sacrificial bird, ISP, chip-off eMMC), remote account keys (Samsung FMM-armed = engineered win). Enrolled biometrics = engineering intel + access agents AFTER an engineered unlock, never the unlock itself. A mission ending with the owner's body opening his own bird is a FAILED mission, whatever was extracted beside it. Owner-credential handover is reported as declared fallback only — never dressed as a win.
