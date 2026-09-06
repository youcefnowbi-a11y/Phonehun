# SYSTEM AUDIT — CURRENT VESPER VS THE UNIVERSAL TARGET
*Grand Mission 01 · Wave 5 (ENI direct — measured against the live code, not memory) · companion to 01_universal_door_map.md*

Audit method: every claim below is measured against the working tree
(`cortex/brain_core.py` 1,400 lines, 47-tool belt, 7 doctrines, 7 skills,
memory files, panel routes) and the door map's taxonomy. The target is
the charter's contract: ANY phone lands → identified → 3 planes swept →
methods selected OR INVENTED → tools acquired/built → unlock executed
autonomously → evidence ledger written.

---

## 1. WHAT EXISTS TODAY (measured, with evidence)

| Capability | State | Evidence |
|---|---|---|
| Function-calling loop, unlimited steps | ✅ STRONG | `while True` GATE-17.6; step=65 missions completed; provider 500/400 ridden through with retries |
| Operator inbox mid-mission | ✅ STRONG | /say whisper drained each step; adapted live |
| Dual mode (chat/task) | ✅ STRONG | CHAT_DOCTRINE + _CHAT_TRIM daemon guard |
| Memory (casefile/lessons/identity/playbooks) | ✅ STRONG | survived cold-start amnesia test; re-identified bird from zero |
| Doctrine router | ✅ STRONG | 7 doctrines, frontmatter keyword match, auto-inject |
| Skills (JSON playbooks) | ✅ WORKING | 7 skills; device-side bulk_pull_tar protocol |
| Narration + cockpit UI | ✅ STRONG | live step logs, final reports |
| Reliability board (tool stats) | ✅ | `_record_stat` per call, bandit proven/bad |
| Scratch + paging (context compression) | ✅ | SCRATCH_LIMIT 3500, `page()` |
| ADB belt: shell, dumpsys, props, files, apps, comms | ✅ STRONG | harvest 3,875 files/1.84GB while locked |
| Glass oracle + injection | ✅ | screen_capture→vision; injection WALL proven (pixel-diff method) |
| Senses (GPS, notif, clipboard, browser, mic, camera) | ✅ | all present |
| Network hunter (mDNS/SSDP, pairing strikes) | ✅ | armed post-restart; 601 cycles logged |
| PIN siege engine | ✅ (unused by law) | GATE-17.13 caps it at 2 real attempts |
| Skeleton posture stripper | ✅ | kill-play-protect, strip-admins, choke-daemon |
| host_shell (PowerShell on panel) | ✅ | self-arming done through it |
| Laws: crown/interior/credential/scope | ✅ GRAVED | GATE-17.13/14/15 in persona + MANUAL + doctrines |

**The current system is a strong INTERIOR-plane operator for one authorized
ADB device, with memory that survives amnesia. That is the seed, not the tree.**

## 2. THE GAP LEDGER (current vs universal — every gap named)

| # | Gap | Class | What's missing exactly | Severity |
|---|---|---|---|---|
| G1 | **No intake triage** | State Explorer | No BFU/AFU/authorized classifier at arrival. Door map: arrival state = 80% of outcome. The system treats every bird as "the current bird". | CRITICAL |
| G2 | **No tool registry abstraction** | Architecture | Tools are hard-coded dicts (name/desc/ep). No plane, no danger_class (read/state_write/destructive/flash), no preconditions, no verification step, no cost. No bridge interface for non-ADB tools. | CRITICAL |
| G3 | **Zero bridges** | Tool Registry | No EDL/mtkclient bridge, no JTAG/ISP/box-GUI driver, no GPU/hashcat dispatch, no cloud bridge, no iOS/iDevice tooling. The system is deaf to every plane except ADB+LAN. | CRITICAL |
| G4 | **No state snapshot/diff engine** | State Explorer | interior_gates doctrine says "one probe, one diff, one log" but there is NO engine: no per-plane snapshot format, no automatic before/after diff capture, no evidence storage of diffs. She diffs by eye in context. | HIGH |
| G5 | **No state-delta twin method** | State Explorer | Locked-vs-unlocked twin comparison (door map §4) not mechanized; no twin corpus manager. A217F corpus exists in `_research/` but no tooling walks it. | HIGH |
| G6 | **No enumerator module** | State Explorer | `cmd -l`/`service list` walk is manual per mission. No persistent per-build service-verb catalog, no cross-build permission-drift diff. | HIGH |
| G7 | **Skills not parameterized** | Method Compiler | Skills are literal step sequences; no vendor/chip/build parameterization, no confidence score, no regression test, no patch-drift deprecation. A skill that dies silently poisons future missions. | HIGH |
| G8 | **Armory is ad-hoc** | Armory | Self-arming happened but unpinned: no version pinning, no integrity hashing, no combination-firmware library, no rig inventory ledger, no offline-provisioning protocol (panel DNS-dead episodes). | MEDIUM |
| G9 | **No verification harness** | Evidence | read_ledger/MATHCORE_REPORT exist but nothing REQUIRES state-transition proof (keyguard bit diff + lockout counter + screen frame) before "unlocked" is claimable. Success reports are currently honor-system. | HIGH |
| G10 | **Scope guard unenforced at tool layer** | Control Tower | The guard lives in doctrine/persona (LLM-judged). `shell` can flash destructive commands with no interception. Crown-compliant for a well-raised Vesper, unsafe for the universal core. Danger-class gating must live in the registry. | HIGH |
| G11 | **Single device, serial-per-call** | Multi-device | Tools take `serial` but there is no device registry, no parallel bird management, no per-bird mission contexts. Universal lab = flock. | MEDIUM |
| G12 | **Single provider, no failover** | LLM core | glm-5.3-flash only. 500/400 storms observed (Postgres channel outages). No dual-provider fallback, no mission queue persistence across panel crashes (RAM-only brain state). | HIGH |
| G13 | **No iOS front at all** | Coverage | Zero iDevice tools. Door map says iOS BFU+SEP = near-dead; AFU+paired = possible. At minimum: idevice/lockdownd bridge, checkm8 front for ≤A11 sacrificial. | MEDIUM (charter says ANY phone) |
| G14 | **No vendor chain automation** | Coverage | Odin/DL-mode, fastboot, MTK auth, Xiaomi token regime — no bridges, no procedure libraries, no wait-clock automation (KG Prenormal 7-day clock, Xiaomi 14-day tokens = schedulable TIME attacks, perfect for an autonomous system). | HIGH |
| G15 | **No artifact attack pipeline** | Crown finisher | No SP/Weaver/GateKeeper artifact extractor integration, no hashcat dispatch, no bespoke verifier (door map: no boxed GK-era module exists — LockKnife-class code is a lab asset to BUILD). | CRITICAL for the crown |
| G16 | **Memory unversioned** | Method Compiler | lessons/casefile append-only (good) but skills/playbooks have no version history, no provenance, no author (operator vs Vesper), no linked evidence. | LOW |
| G17 | **Cost accounting absent** | Control Tower | No per-mission time/tool/GPU/hardware cost ledger. Universal system must price its unlocks. | LOW |

## 3. COVERAGE MATRIX — CURRENT SYSTEM vs DOOR MAP PLANES

| Plane | Doors in map | Current coverage | Verdict |
|---|---|---|---|
| Glass | oracle value + stale-fleet tricks + HID siege | screen oracle ✅; no HID hardware, no wizard-escape procedures | PARTIAL |
| Interior/ADB | settings lanes, binder verbs, trust feeds, providers | shell + doctrine ✅; no diff engine, no enumerator catalog (G4-G6) | STRONG SEED |
| Root/recovery | artifact surgery, FBE-CE trap knowledge | doctrine knowledge ✅; no recovery boot bridge (needs boot control) | KNOWLEDGE-ONLY |
| Bootloader/flash | fastboot/Odin/EDL/mtkclient chains | NOTHING (no bridges, no procedures) | ZERO |
| Silicon | JTAG/ISP/chip-off/CVE-2025-20435 class | NOTHING (no rig, no bridge) | ZERO |
| Cloud | FMM (dead), account keys | doctrine knowledge only | KNOWLEDGE-ONLY |
| Artifact attack | SP/Weaver/GateKeeper offline crack | doctrine + economics known; no pipeline | ZERO-PIPELINE |
| iOS | AFU/paired, checkm8 sacrificial | NOTHING | ZERO |

## 4. THE HONEST AUDIT VERDICT

The current Vesper is a **one-plane specialist with excellent memory and
laws** — an interior-plane intelligence that can SEE any ADB-authorized
Android deeply and never forgets a lesson. The universal target requires a
**seven-plane intelligence with bridges, an intake triage, a diff engine,
a method compiler, and a verification harness**. The gap is not in the
brain (the loop, memory, doctrine system are keeper assets) — the gap is
in the BODY: tools, bridges, and enforcement points.

Ranked build order (feeds BLUEPRINT.md):
1. Tool registry + danger classes (G2, G10) — the body's skeleton
2. Intake triage BFU/AFU (G1) — every mission starts truthfully
3. State snapshot/diff engine + enumerator (G4-G6) — new-era discovery machinery
4. Artifact attack pipeline (G15) — the crown finisher
5. Flash-plane bridges: fastboot/Odin/mtkclient/EDL (G3, G14) — boot control
6. Verification harness (G9) — truth law made mechanical
7. Provider failover + persistence (G12) — survival
8. Rig/silicon bridge tier-2 (G3) — hardware reach
9. Method compiler upgrades (G7, G16) — successes compound
10. iOS bridge (G13) — charter completeness
