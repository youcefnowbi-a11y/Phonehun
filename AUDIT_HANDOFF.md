# AUDIT HANDOFF — DroidCommand Native Backend Exhaustive Audit

**You are the successor AI.** Your mission: continue and finish the exhaustive backend code
quality & architecture audit of DroidCommand. A prior audit (inventory-style, machine-generated)
covered older code and is STALE on several counts — this handoff is the live ledger. Work from
this file, verify everything yourself by reading the actual source, and append your findings
below in the same format when done.

- Repo HEAD at handoff: `bb4444a` GATE-16.3-WARFRONTS (branch `main`)
- Remote: https://github.com/youcefnowbi-a11y/Phonehun.git
- Tree state: audited state == pushed state. Nothing was papered over.

---

## 1. METHOD (non-negotiable rules)

Severity scale: `CRITICAL` (exploitable now by LAN/local client) / `HIGH` (needs preconditions) /
`MED` (reliability, leak, race) / `LOW` / `HARDENING`.

Rubric — check every file for:
- **SECURITY**: path traversal, command injection / `shell=True`, deserialization/eval, weak
  randomness (`random` vs `secrets`), timing-unsafe comparisons, TLS verify disabled, secrets
  logged/hardcoded, raw-socket auth/bind scope/recv caps, SSRF.
- **CONCURRENCY**: lock coverage at EVERY access site (not just the declaration), thread
  lifecycle (daemon/join/stop-flags), TOCTOU.
- **RESOURCES**: subprocess timeout on EVERY call, unbounded buffers/session maps, socket timeouts.
- **ERROR HANDLING**: broad `except Exception` judged per-site (boundary-ok vs mid-logic-swallow).
- **CORRECTNESS**: dead/duplicated/mismatched contracts, tool-schema↔dispatch reconciliation,
  bytes-vs-str, Windows GBK/UTF-8 (Python 3.11, Windows host).

Iron rule: **verify before claiming**. If you checked and it's fine, write `CHECKED, SAFE` with a
file:line citation. No invented findings. Locate files under `DroidCommand/`.

## 2. PROGRESS STATE

Fully audited (every line read by the prior auditor personally):
`app.py` (1012 ln), `agent_relay.py` (285 ln), `network_scanner.py` (282 ln),
`file_manager.py` (168 ln), `system_controls.py` (77 ln).

Partially audited (heads/tails read, middle sections need line-by-line pass):
`adb_engine.py` (233 ln — L1-101, L218-233 done), `cve_bypass.py` (466 ln — L1-115, L440-466 done),
`toolkit_manager.py` (345 ln — L1-85, L329-345 done).

Untouched (the remaining work, in recommended order):
1. `ghost/` — `pairing_server.py` (368), `spake25519.py` (286: infinity handling, scalar
   clamping, constant-time), `pairing_client.py` (461: framing, 0.001s sleep spin), `wlan_join.py`
   (201: L175 mkstemp WiFi profile XML — passphrase on disk + cleanup?), `pipeline.py` (612),
   `discovery.py` (217), `hunter.py` (228), `mathcore.py` (285).
2. `skeleton/` — `pin_siege.py` (323: STATE.lock coverage at EVERY site, restart-while-running
   race, time.sleep L133/135/196/233/250/269), `neutralizer.py` (263), `cred_harvester.py` (181:
   where do harvested secrets land — disk/logs/responses?).
3. `deep_access.py` (260), `spy_extractor.py` (319), `surveillance.py` (256: camera/mic cleanup on
   error paths), `offensive_actions.py` (313: L240 time.sleep(2)).
4. Managers: `app_manager.py` (139), `comms_manager.py` (130), `media_browser.py` (66).
5. `cortex/brain_core.py` (1106 ln — audit ALONE, three passes): tool-schema↔_execute_tool full
   reconciliation list, tool-output size caps before re-entering model context (prompt injection),
   refusal-wipe false positives, compaction termination, `.api_token` read L153, backoff L786/794,
   lock coverage on session state. Then `brain_api.py` (128), `vision.py` (91), `config.py` (30).
6. `panopticon/` — `screen_console.py` (319: video socket recv timeout, pump-thread cleanup),
   `geo_math.py` (378), `geo_tri.py` (199: div-by-zero, degenerate triangles, L55 sleep).
7. `h264_math.py` (727): bitstream caps, buffer growth, oracle purity (`_py_*` aliases,
   `_NEEDS` full-heart-or-nothing gate, `DROID_H264_PURE=1` escape).

Out of scope (do NOT audit, do NOT push): `tools_clone\`, `_xrefs\`, `scratch\`, `temp\`,
`agent\check_java.py`, `generate_vesper_icons.py`.

## 3. FINDINGS LEDGER (verified, carry these into the final report)

### HIGH
| # | Where | Finding |
|---|-------|---------|
| H1 | `app.py` ~L670-756 | `/api/toolkit/cve-scan` references `key_type`, `target_port`, `cmd_to_run` that are never defined in scope → NameError → HTTP 500 whenever an IP is supplied. The exploit-attempt branch is DEAD CODE as shipped. Top fix candidate. |
| H2 | `agent_relay.py` L191 | `srv.bind(("0.0.0.0", RELAY_PORT))` with ZERO authentication — any LAN host can `hello` and register/replace a session. `sid` is derived from attacker-controlled brand/model fields (L112-116). Reconnect replaces `SESSIONS[sid]` without closing the old conn (fd leak + session hijack). |
| H3 | `agent_relay.py` L140-145, L94 | JSON frames are capped at 8MB, but the raw follow-up path (`frame.get("size")` → `_read_raw`/`_recv_exact`) has NO cap → memory-exhaustion DoS from any LAN peer. |
| H4 | `cve_bypass.py` L235-236 | `ctx.check_hostname = False` / `ssl.CERT_NONE`. Defensible for the ADB-TLS exploit tool (target presents forged cert) but must be documented/flag-gated, never copied to client-facing code. |

### MED
| # | Where | Finding |
|---|-------|---------|
| M1 | `agent_relay.py` L171-172 | `mic_<sid>.pcm` appended unbounded — no rotation/size cap. |
| M2 | `app.py` ~L748/804 | SSE screen-stream `time.sleep(0.5)` loops hold Flask worker threads ~2.5min; `threaded=True` (L1012) mitigates, cap the stream lifetime anyway. |
| M3 | `cve_bypass.py` L84-89 | `recv_packet` trusts the header length field without capping at `ADB_MAXDATA` (defined L49, unused on recv path) → malicious device can force a huge allocation. |
| M4 | `cve_bypass.py` ~L226-229 | Ephemeral client cert/key written via `NamedTemporaryFile(delete=False)`; no cleanup visible in `main()` (L440-466) → private-key tempfiles accumulate. Verify + delete in `finally`. |
| M5 | `system_controls.py` L39-53 | `type_text` escapes `\ ' " & ; ( ) | < >` and space→`%s`, but NOT backtick/`$` → device-side shell expansion (`` `cmd` ``, `$VAR`) through `adb shell`. Defense-in-depth escape or base64 the text. |

### LOW / HARDENING
| # | Where | Finding |
|---|-------|---------|
| L1 | `app.py` gate | API token also accepted via `request.args.get("token")` → token lands in URLs/logs. Header/body only. |
| L2 | `app.py` routes | Uncaught `int()` on `camera_id` / mic `duration` params → 500 on garbage. |
| L3 | `agent_relay.py` L272-285 | Broadcast is unauthenticated-by-design (gated only by being a TCP peer) — acceptable for lab use, document it. |
| L4 | `network_scanner.py` L232-233 | `except Exception: pass` around `future.result()` silently swallows scan errors. |
| L5 | `adb_engine.py` L51 | `run_binary_cmd` catches broad Exception, losing the "timed out" distinction that `run_cmd` has (L31-32). |
| L6 | `config.py` | `API_TOKEN = secrets.token_urlsafe(32)` persisted plaintext to `.api_token` — accepted design, file is gitignored; NEVER commit or push it. |

### CHECKED, SAFE (verified by direct read — do not re-flag)
- `app.py` L62-77 `gate_request`: hostname allowlist (DNS-rebinding guard) + `secrets.compare_digest` token check.
- `app.py` ~L996-1003 loot endpoint: filename guarded against `/` `\`, dir pinned to TEMP_DIR/cortex_shots.
- `app.py` L172 md5 of remote path: benign cache-name dedup (not crypto).
- `agent_relay.py` L64: events capped at 500; `_WAITERS` keyed (sid,id) with timeout, popped on both paths.
- `network_scanner.py`: full file clean — list-args PowerShell L46-49 (no injection), `ipconfig`/`arp` list-args, `check_port` L110-120 settimeout+connect_ex+finally-close, `probe_adb_banner` bounded 24-byte recv, `scan_subnet` ThreadPoolExecutor capped at 50 workers with validated `_SUBNET_RE` L203, arp results capped at 20 (L280).
- `file_manager.py`: every shell interpolation `shlex.quote`d (L29, 117, 122-129, 133, 144-145); pull/push timeout=120; search timeout=30.
- `system_controls.py`: tap/swipe/keyevent `int()`-cast before f-string (L28, 32, 36); logcat `int(lines)` L72 + `shlex.quote(filter_tag)` L75, timeout=15; screenshot fallback removes its remote tmp L24.
- `toolkit_manager.py`: `apply_tweak` keyed dispatch map L332-344 (no interpolation); `attempt_pin_unlock` digits-only via `re.sub(r'\D','',pin)` L75; L319 `return this.exec(cmd);` is JS-in-a-string for the device agent — benign, not Python eval.
- `adb_engine.py`: `run_cmd` list-args + always-timeout + utf-8/replace encoding (GBK-safe) L13-34; serial targeting via `["-s", serial]` L9-11.
- Syntax health: `compileall` clean for ALL native modules.

## 4. STALE CLAIMS IN THE OLD (PRIOR) AUDIT — do not repeat them
- Claimed 10,621 LOC / app.py 932 / h264_math 683 — all stale. True inventory: 34 native modules,
  10,754 LOC; app.py 1012; h264_math 727. Count with `(Get-Content f).Count`
  (`Measure-Object -Line` skips blanks and lies).
- The old audit's PASS on the cve-scan route missed the H1 NameError — the route was added later.

## 5. OPERATIONAL NOTES
- Windows host, PowerShell 5.1: no inline `python -c` with quotes; always `Set-Location` absolute;
  fresh cwd every shell.
- Secret guard before every commit: `git add -u` (or explicit paths), then check
  `git diff --cached --name-only` against `\.api_token|brain_config` — abort if matched.
  `.api_token` / `brain_config.json` must never be staged or pushed (plaintext token on disk is
  accepted design).
- Push may fail once on IPv6 flake — retry once.
- Commit gate naming: `GATE-16.4-*` and onward.
- The app runs via `python app.py` (Flask dev server, `threaded=True`); panel token in
  `%TEMP%\dpanel_*.log` for liveness checks.

## 6. SUCCESSOR'S LOG (append here)

_(nothing yet — start with ghost/pairing_server.py + spake25519.py)_
