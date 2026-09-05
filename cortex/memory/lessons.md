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
