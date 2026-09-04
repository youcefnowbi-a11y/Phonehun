# AUDIT HANDOFF — DroidCommand Native Backend Exhaustive Audit

**You are the successor AI.** Your mission: continue and finish the exhaustive backend code
quality & architecture audit of DroidCommand. A prior audit (inventory-style, machine-generated)
covered older code and is STALE on several counts — this handoff is the live ledger. Work from
this file, verify everything yourself by reading the actual source, and append your findings
below in the same format when done.

- Repo HEAD at handoff: `1983a97` GATE-16.4-LEDGER (branch `main`); the pairing-wave +
  pipeline-wave ledger fold lands as GATE-16.5-*.
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

Fully audited (every line read): `app.py` (1012 ln), `agent_relay.py` (285 ln),
`network_scanner.py` (282 ln), `file_manager.py` (168 ln), `system_controls.py` (77 ln),
`toolkit_manager.py` (345 ln), `media_browser.py` (66 ln), `ghost/pairing_server.py` (368 ln),
`ghost/pairing_client.py` (461 ln — triple coverage: full read d7069368 + two slice
corroborators), `ghost/spake25519.py` (286 ln — parent-audited in full + 67c728b5 slice
corroboration), `ghost/pipeline.py` (612 ln — two half-slices 6637a64a/44ac34b3 + parent
seam verification L265-394, L485-559). Every finding re-verified against source by the
parent before entering this ledger.

Partially audited (heads/tails read, middle sections need line-by-line pass):
`adb_engine.py` (233 ln — L1-101, L218-233 done), `cve_bypass.py` (466 ln — L1-115, L440-466 done).

Untouched (the remaining work, in recommended order):
1. `ghost/` — `wlan_join.py` (201: L175 mkstemp WiFi profile XML — passphrase on
   disk + cleanup?), `discovery.py` (217), `hunter.py` (228), `mathcore.py` (285).
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
| H5 | `media_browser.py` L53-55 | `fetch_preview` composes the device-controlled `Path(remote_path).name` RAW into the host path: `safe_name = f"preview_{md5[:12]}_{filename}"`. Windows-illegal chars (`* ? " < > |`) in a device filename raise WinError 123 → unhandled 500; a mid-name colon becomes an NTFS Alternate Data Stream (miswrite/cache confusion). Traversal NOT possible (`.name` strips separators + md5 prefix keeps it inside TEMP_DIR). Fix: `re.sub(r'[^A-Za-z0-9._-]', '_', filename)` + length cap. VERIFIED by parent read of the full file. |

### MED
| # | Where | Finding |
|---|-------|---------|
| M1 | `agent_relay.py` L171-172 | `mic_<sid>.pcm` appended unbounded — no rotation/size cap. |
| M2 | `app.py` ~L748/804 | SSE screen-stream `time.sleep(0.5)` loops hold Flask worker threads ~2.5min; `threaded=True` (L1012) mitigates, cap the stream lifetime anyway. |
| M3 | `cve_bypass.py` L84-89 | `recv_packet` trusts the header length field without capping at `ADB_MAXDATA` (defined L49, unused on recv path) → malicious device can force a huge allocation. |
| M4 | `cve_bypass.py` ~L226-229 | Ephemeral client cert/key written via `NamedTemporaryFile(delete=False)`; no cleanup visible in `main()` (L440-466) → private-key tempfiles accumulate. Verify + delete in `finally`. |
| M5 | `system_controls.py` L39-53 | `type_text` escapes `\ ' " & ; ( ) | < >` and space→`%s`, but NOT backtick/`$` → device-side shell expansion (`` `cmd` ``, `$VAR`) through `adb shell`. Defense-in-depth escape or base64 the text. |
| M6 | `media_browser.py` L54-58 | Preview cache keyed on `md5(remote_path)` only — no device serial in the key, no TTL: with two devices attached, `/sdcard/DCIM/x.jpg` on device A serves device B's cached pull; changed device files serve stale previews forever. Fix: hash `(serial, path)`, re-pull past a TTL. |
| M7 | `ghost/pairing_server.py` L175-195, L203-257 | Pairing-gate monopoly DoS: accept loop is strictly sequential, `MAX_ATTEMPTS = 3` (L56) is a global budget, each stalled connection burns up to ~15s per TLS op → 3 connect-and-stall LAN peers cover the whole 300s QR window and the legitimate phone can never pair. Availability only (SPAKE2 gates secrets). Fix: per-connection wall-clock deadline (~10s) inside `_serve_once`. PARENT-VERIFIED L170-205. |
| M8 | `ghost/pairing_server.py` L159-171, L196 | `stop()` joins the accept thread for only 3s while `_serve_once` can chain ~6 × 15s ops (~90s worst case) → zombie thread keeps writing `state` and closing sockets after stop() returns; mDNS already unregistered while thread may be mid-protocol. Fix: force-close server sock in stop() to unblock accept, join with worst-case deadline. |
| M9 | `ghost/pairing_server.py` L222, L240 | **RESOLVED — CHECKED SAFE.** Server reads all headers via `pc._read_header` (L219, L237), which enforces the cap client-side: `payload == 0 or payload > K_MAX_PAYLOAD_SIZE (16384)` → ValueError (pairing_client.py L236), before any sized read. Attacker-controlled length cannot reach `_tls_recv_exact` unbounded. Parent read of pairing_server L210-250 + client-side cap verified by full-file audit. |
| M10 | `ghost/pairing_client.py` L136-148, L152, L157 | Single AES-128-GCM key used for BOTH directions with `enc_seq`/`dec_seq` counters starting at 0 → identical (key, nonce) pair when both sides encrypt their first record. Client's first slab is ~99% zero bytes → identical keystream XOR ~identical plaintext = keystream + GHASH-key recovery on collision. LATENT/CONTAINED: runs inside TLS 1.3, gated by exporter-bound SPAKE2; a loopback selftest cannot catch it. Fix first requires confirming whether AOSP `aes_128_gcm.cpp` splits the key per direction — verify before patching (may be AOSP parity). |
| M11 | `ghost/pairing_client.py` L98 | Missing `adbkey.pub` → placeholder `b"droidcommand"` is sent as ADB_RSA_PUB_KEY; the device "stores" junk and pair() reports success, but no usable identity was persisted — subsequent `adb connect` fails with no obvious cause. Detect absence and fail loud or generate a key. |
| M12 | `ghost/pairing_client.py` L347-353 | `pair_async` on timeout: `join(timeout+5)` then abandons a daemon thread holding an open socket mid-TLS-handshake → thread + fd leak vs a hostile/slow host (mirrors M8 pattern). Force-close the socket in the join path so the thread actually dies. |
| M13 | `ghost/pipeline.py` L358-369, L373-378, L382, L389, L434, L302-311 | `_SIEGE_LOCK` guards only the L358-369 reset. Unlocked writes: probe-failure reset L373-378, worker `status` L382, `running=False` L389, `/stop` abort flag L434, and every `_siege_loop` per-iteration write (`tried/hits/errors/last_code` L302-311 — PARENT-VERIFIED). GIL keeps each op atomic but snapshots can tear and start/stop can interleave with the probe-failure reset. Take the lock at every site (same discipline as L14). |

### LOW / HARDENING
| # | Where | Finding |
|---|-------|---------|
| L1 | `app.py` gate | API token also accepted via `request.args.get("token")` → token lands in URLs/logs. Header/body only. |
| L2 | `app.py` routes | Uncaught `int()` on `camera_id` / mic `duration` params → 500 on garbage. |
| L3 | `agent_relay.py` L272-285 | Broadcast is unauthenticated-by-design (gated only by being a TCP peer) — acceptable for lab use, document it. |
| L4 | `network_scanner.py` L232-233 | `except Exception: pass` around `future.result()` silently swallows scan errors. |
| L5 | `adb_engine.py` L51 | `run_binary_cmd` catches broad Exception, losing the "timed out" distinction that `run_cmd` has (L31-32). |
| L6 | `config.py` | `API_TOKEN = secrets.token_urlsafe(32)` persisted plaintext to `.api_token` — accepted design, file is gitignored; NEVER commit or push it. |
| L7 | `toolkit_manager.py` L120-124 | `dump_wifi_passwords` zips two independent `re.findall` lists (SSIDs, PSKs) — any open network (no `PreSharedKey`) shifts indices and misattributes later passwords to wrong SSIDs. Parse whole `<WifiConfiguration>` blocks instead. |
| L8 | `toolkit_manager.py` L242,247,252 | `int()` on client input (`duration_ms` etc.) raises uncaught ValueError before the clamp → 500. Wrap in try/except. |
| L9 | `toolkit_manager.py` L116,147,231-233 et al | Many `adb.shell` calls pass no explicit timeout. RESOLVED: engine default `timeout=30` applies (`adb_engine.py` L54-56, enforced in `run_cmd` L13-24, `TimeoutExpired` caught L31) — no hang possible. Downgraded from the survivor's conditional MED per her own criterion. Explicit per-call args still preferred for auditability. |
| L10 | `toolkit_manager.py` L214-222 | `package_name` is `shlex.quote`d (no metachar injection) but not format-validated — a bare token like `-k` reaches pm's flag parser. Fix: `re.fullmatch(r'[A-Za-z][\w]*(\.[\w]+)+', ...)` before dispatch. |
| L11 | `toolkit_manager.py` L125 | Wi-Fi PSKs leave the function as plaintext in the API response. Mask by default, full reveal behind an explicit flag. |
| L12 | `toolkit_manager.py` L253-254 | `record_screen` uses fixed device tmp + epoch-second local name → concurrent recordings clobber. Use uuid names both sides. |
| L13 | `media_browser.py` L58 | `remote_path` passed to `adb pull` unvalidated (leading-dash flag surface). Require `remote_path.startswith("/")`. |
| L14 | `ghost/pairing_server.py` L157, L184, L187-193, L244-245, L261-268 | `self._lock` exists but most `state` writes and `snapshot()` reads go unlocked. GIL masks corruption; monitoring accuracy + `already_running` race vs TTL expiry remain. Take the lock at every site. PARENT-VERIFIED L184. |
| L15 | `ghost/pairing_server.py` L163-169 vs L177, L194-196 | mDNS/Zeroconf never unregistered on TTL-expiry or attempt-exhaustion (only `stop()` cleans) → LAN keeps seeing a dead `_adb-tls-pairing` advertisement, zc threads leak. |
| L16 | `ghost/pairing_server.py` L252, L157 | Raw exception text stored into `state["error"]` → surfaced via `snapshot()` to UI (SSL error strings, IPs). Map to stable error codes, keep detail in logs. |
| L17 | `ghost/pairing_server.py` L198-201 | Dead code: both `if/else` branches assign `running = False` (comment admits it). Collapse. PARENT-VERIFIED verbatim. |
| L18 | `ghost/pairing_server.py` L153/156, L121, L266 | `mdns_ok` / `_identity` never initialized in `__init__` → `snapshot()` on a constructed-but-unstarted server raises AttributeError. |
| L19 | `ghost/pairing_server.py` L123-128, L286-288 | If `bind`/`listen` raises, the open server socket is never closed (thread never started to clean it). try/except-close-rethrow. |
| L20 | `ghost/pairing_server.py` L207 vs L211-240 | Socket timeout honors `pc.PAIRING_IO_TIMEOUT_S` but all twelve pc-layer calls hardcode `15` — divergent contract, fallback constant decorative. Resolve once, pass everywhere. |
| L21 | HARDENING `ghost/pairing_server.py` L125 | `0.0.0.0` bind is REQUIRED for the QR LAN flow (distinct from the agent_relay finding) — optional improvement: pin to `self.lan_ip`. |
| L22 | HARDENING `ghost/pairing_server.py` L124 | `SO_REUSEADDR` on Windows permits double-bind port theft; serves no purpose on an ephemeral port — drop or gate per-platform. |
| L23 | HARDENING `ghost/pairing_server.py` L70-79 | `esc()` covers all five WIFI-grammar metachars (selftest-asserted) but operator strings with `\n`/`\r`/`\x00` pass unfiltered into the QR blob — reject non-printables. |
| L24 | HARDENING `ghost/pairing_server.py` L341-342 | Selftest binds `0.0.0.0` + advertises mDNS on the real LAN; loopback bind + skip `_advertise` in test mode. |
| L25 | `ghost/pairing_client.py` L211 | `_tls_recv_exact` wall-deadline checked only when SSL raises `WantReadError/WantWriteError` — a peer trickling 1 byte per cycle (each within socket timeout) restarts the deadline indefinitely → slowloris inside the 16384 cap. Count total bytes against the deadline too. |
| L26 | `ghost/pairing_client.py` L177-178 | `SSL.VERIFY_NONE` + no hostname check on the pairing TLS link. DELIBERATE AOSP parity (adbd pairing uses self-signed certs + SPAKE2-bound channel binding). Document in-file or flag-gate; never copy the pattern to any TLS path that authenticates a server. |
| L27 | `ghost/pairing_client.py` L344-345 | Exception text + traceback formatted into the returned error string → lands in panel state/logs. Stable error codes internally, detail to host logs only. |
| L28 | `ghost/pairing_client.py` L318-323 | On `peer_type` mismatch the code proceeds and reports `success=True`/`device_stored_cert=True` regardless — a protocol-desync pairing is reported as success. Raise on mismatch or mark the result degraded. |
| L29 | `ghost/pairing_client.py` L64, L99 | `_cert_cache` unlocked read-modify-write (benign: duplicate work only, GIL) + the cached private key lives in module-global memory for the process lifetime. Keyring/DPAPI optional hardening. |
| L30 | `ghost/pairing_client.py` L58 | ADB key dir falls back to CWD when `USERPROFILE`/`ANDROID_*` are unset — keys materialize wherever the app was launched. Prefer an explicit config dir. |
| L31 | `ghost/pairing_client.py` L382 | Selftest result includes the raw SPAKE2 shared secret key. Test-only path, but keep secret material out of any dict that ever gets printed. |
| L32 | HARDENING `ghost/spake25519.py` L133-143 | Scalar mult is classic double-and-add on secret scalars — not constant-time. SPAKE2 scalars derive from `os.urandom(64)`; timing surface requires a local high-resolution side channel on the same host. Note only; matching BoringSSL's constant-time ladder is a rewrite, not a patch. PARENT-VERIFIED loop structure. |
| L33 | LOW `ghost/spake25519.py` L134 | Docstring claims "MSB-first" while the loop is LSB-first (`while b:` over `b >>= 1`) — wrong comment on security-critical code. Fix the docstring. |
| L34 | LOW `ghost/spake25519.py` L279-286 | `spake2_client`/`spake2_server` factory functions accept a `password` param and silently ignore it (key comes from `start()`/`finish()` flow). Resolves 67c728b5's "suspicious double pass" — harmless, but drop the param or assert it's unused. |
| L35 | `ghost/pipeline.py` L391-392 | Async siege worker is `daemon=True` fire-and-forget: no handle kept, no join, no observable shutdown; abort is cooperative only. Mirror the M8 fix: keep the Thread ref, offer join with wall_s deadline. |
| L36 | `ghost/pipeline.py` L587, L605 | `repr(exc)` returned in HTTP 500 bodies — internal paths/types leak to any caller. Map to stable codes. |
| L37 | `ghost/pipeline.py` L599, L146 | `hunter_engage` port skips the 1-65535 check that the siege route HAS (L252 — inconsistent), and `ip` is only `.strip()`ed everywhere — no `ipaddress` parse. Reaches `adb connect` argv + sockets (list-args, so no injection — arbitrary-endpoint only, by design). Validate once, reuse. |
| L38 | `ghost/pipeline.py` L451 | `qr_start` `ttl_s`: uncaught `float()` (junk → 500) and no upper clamp (1e12 accepted). Clamp like wall_s. |
| L39 | `ghost/pipeline.py` L407, L509 | Dead `except KeyError` clauses — both sites use `dict.get`/`data.get`, which never raises KeyError. PARENT-VERIFIED L509 tuple. Drop the clause. |
| L40 | HARDENING `ghost/pipeline.py` L341 | `_code_stream` zero-pads caller-supplied custom codes too (`zfill(6)` applied to the `codes` list), contradicting the L330-331 docstring ("custom codes keep their literal digits"). Logic/doc mismatch — align one or the other. |
| L41 | LOW `ghost/pipeline.py` L86-87 | `line.startswith(ep)` prefix match: endpoint `1.2.3.4:5555` matches device line `1.2.3.4:55550\tdevice` → false-positive "already connected". Compare `line.split("\t")[0] == ep`. |
| L42 | LOW `ghost/pipeline.py` L269, L204-212 | Caller-supplied `codes` list held whole + `seen` set grows with it; no request-size cap visible → memory DoS via giant JSON body. Cap list length (e.g. 20k) or rely on a global `MAX_CONTENT_LENGTH`. |
| L43 | LOW `ghost/pipeline.py` L270, L49-52 | Sync siege/sweep routes run the whole loop inline in a Flask worker (wall_s up to 600) — with `threaded=True` this starves workers under concurrency, not the process. Prefer the async route as default. |
| L44 | LOW `ghost/pipeline.py` L224-232 | `_probe_pairing_server`: `s.close()` not in `finally` — mid-flow exception between connect and close leaks the socket. |
| L45 | LOW `ghost/pipeline.py` L49, L264-265 | Uncaught `float(request.args.get("window"))` (junk → 500; also no lower clamp → negative mdns_window) and `int(...max_attempts)`/`float(...wall_clock_s)` in the async route (junk → 500). Wrap + clamp. |
| L46 | HARDENING `ghost/pipeline.py` L34, L245, L265, L367 | `SAFETY_FLOOR_S` is imported and referenced only in a docstring — both floor sites hardcode `max(5.0, ...)` instead. Use the constant (PARENT-VERIFIED via grep: no code reference). |
| L47 | HARDENING `ghost/pipeline.py` L128-129 | Attempt-loop `except Exception` also swallows TypeErrors into "target likely patched"; `str(exc)` echoed to the client may leak internals. Split expected/unexpected exception classes. |
| L48 | HARDENING `ghost/pipeline.py` whole file | Blueprint-level defense-in-depth: all `ghost_bp` routes are unauthenticated IN-MODULE. The app-wide `@app.before_request` gate (app.py L62-77) covers them (PARENT-VERIFIED L38-44 registration + L62-63 hook — refutes both slices' "zero-auth MED"), but any future standalone mount of ghost_bp would be naked. Optional per-blueprint token check. |

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
- `toolkit_manager.py` middle section (first survivor wave, parent-verified): `remove_gesture_keys` L89-101 fixed literal commands; `dump_wifi_passwords` L105-116 literal `cat` list; `dump_raw_service` L171-177 `shlex.quote` + `timeout=15` (the file's model citizen); `record_screen` L252/256 duration cap `max(1, min(30, int(...)))` + `timeout=duration_sec + 10`; L319 `return this.exec(cmd);` is JS inside the triple-quoted Frida `root_bypass` string (L301-326) — device-agent payload, never executed by the Python host, no user input interpolated.
- `media_browser.py` L30-32: `shlex.quote(sdir)` on fixed dirs + `timeout=20`; L58 list-args + `timeout=60`.
- `ghost/pairing_server.py` (43ba4cb8, full file): `secrets` only — `secrets.choice` password (L60, 28^8 ≈ 2^38.6), `secrets.token_hex` service name (L102), `random` never imported; no `==` on any secret (password feeds SPAKE2 math only, L216); `esc()` covers all 5 grammar metachars (L63-79, selftest L338-339); `snapshot()` excludes the password (L261-268, L310-316); module singleton guarded by `_SESSION_LOCK` at every entry; TTL clamped [30, 3600] (L286); peer socket closed in `finally` (L254-257); no eval/exec/shell/subprocess/SSRF surface in the whole file; state machine rejects out-of-order messages (L219-221, L237-239).
- `ghost/pairing_client.py` (full file, triple coverage: d7069368 + ced65cfd L1-230 + 36ecaeb1 L231-461, mutually corroborating): Q1 — `K_MAX_PAYLOAD_SIZE = 16384` (L51) enforced at L236 (`payload == 0 or payload > cap → ValueError`), ALL wire recvs go through `_read_header` (L230, L299, L313); Q2 — `_tls_recv_exact` (L210-226) reads are bounded by caller-supplied n, deadline checked (trickle caveat = L25); Q3 — VERIFY_NONE deliberate AOSP parity (L26); Q4 — exporter `b"adb-label\x00"`, olen 64, context None (L287-299): TLS 1.3 session-bound → no cross-session replay; `password = code_bytes + exported` (L287); Q5 — client SENDS first (L292-299), agreeing with server read-first (pairing_server L219) — wire order confirmed both sides. Auth-before-trust: pubkey sent only inside the encrypted channel (L266-333). Loopback selftest binds 127.0.0.1 (L404-407, L441-443). `random` never imported; no `==`/`!=` on secrets; SSL excepts narrow (L182-207).
- `ghost/spake25519.py` (parent-audited full file + 67c728b5 L1-120 corroboration): **M/N constants byte-identical to `_research/aosp/spake25519.c` L36/L41 (grep-verified)** — closes the highest-stakes verification; P/ORDER/D/SQRT_M1 standard (L32-35); `_x_recover` correct RFC 8032 sqrt recovery incl. None failure path (L47-55); `point_decode` full validation — len 32, y < P (canonical), on-curve, x=0-negative reject (BoringSSL parity, L58-73); `point_add` = add-2008-hwcd-3 unified, a=-1, every component reduced mod P (L87-105); `point_double` = RFC 8032 dbl exact (L120-130); password-scalar "hack" replicates BoringSSL C sequentially — worked example s≡1 mod 8 → 3·ORDER adds, independently verified twice (L134-143); randomness is `os.urandom(64)` ONLY (L193); invalid-curve surface closed — peer message must be len==32 and passes `point_decode` (L239-241); transcript = SHA512 over role-ordered, 8-byte-LE length-prefixed name+msg fields, binds dh_encoded + password_hash (L254-274); key = full 64B digest → HKDF-SHA256 → AES-128-GCM; `BASE`/`os` both live (L199/L193 — closes 67c728b5's usage question); no `random`, no secrets printed or compared.
- `ghost/pipeline.py` (two half-slices 6637a64a L1-306 + 44ac34b3 L307-612, seam closed by parent reads L265-394 + L485-559): every engine call carries explicit timeout (15/10/15; L83, L85, L90); list-argv subprocess only, no `shell=True` (L80-99, L541-545 `["connect", ep]` timeout=15); probe recv bounded 64 B (L226-230); wall_s/max_attempts clamped at reset (5-21600 s, ≤20000, L358-369); abort flag IS honored inside `_siege_loop` (`if st["abort"]: break`, L290 — PARENT-VERIFIED); `/pair` validates port 1-65535 (L507), code digits-only ≤8 (L515), timeout_s [2,30] (L521); `_attempt_code` clean — delegates to audited `pair_async` with timeout flowing through, no shell (L485-491); `engine.run_cmd` returns utf-8 str (adb_engine L13-34) so the L542 `ep in stdout` membership test is str-in-str; QR password in single response, status password-free (L441-471); code never logged (L485-491); `/stop` sets cooperative flag only (L431-436); both slices' "zero-auth MED" REFUTED — app-wide `@app.before_request` gate covers all blueprints (app.py L38-44, L62-63, PARENT-VERIFIED); dead-import claim 6637a64a #9 mostly REFUTED — `threading` L322/391, `pacing_delay` L312, `siege_codes` L335/346, `dialog_window` L394 all live; only `SAFETY_FLOOR_S` decorative (→ L46). No `random`, no secret-compare, no path surfaces in either slice.

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

### Entry 1 — first survivor wave (subagent `b47d2ef3`)
- `toolkit_manager.py` + `media_browser.py` + `network_scanner.py` audited; all findings re-verified against source by the parent before entering this ledger (H5 confirmed by direct read; the timeout question resolved via `adb_engine` default). Ledger updated: H5, M6, L7–L13 added; both files moved to fully audited.
- Next up for the next wave: **`ghost/pairing_server.py` + `spake25519.py` + `pairing_client.py`**, then the Section 2 order.

### Entry 2 — wave two: the pairing protocol
- `ghost/pairing_server.py` DONE (subagent 43ba4cb8, full 368 ln): zero CRITICAL/HIGH. Ledger adds **M7-M9, L14-L24**; file moved to fully audited. Parent spot-verified L170-205 against source before folding: sequential accept gate with global `MAX_ATTEMPTS=3` budget, unlocked `attempts` mutation (L184), and dead-code if/else (L198-201) all confirmed verbatim.
- **M9 is CONTINGENT**: unbounded `payload` length from the wire header (L222/L240) only becomes a real memory-DoS if `pairing_client.py` lacks recv caps. `d7069368` was dispatched with targeted questions Q1-Q4 (`_read_header` cap, `_tls_recv_exact` max, `_tls_context` verify policy, `_export_key_material` replay binding) — its answers finalize or downgrade M9.
- **Casualty report, spake25519.py (286 ln): two agents dead.** `9040eb56` died of context exhaustion on the FULL file — zero report, not even a closing line. Respawn `b27e2587` on L1-150 was stopped the same way, also zero report. Hand-rolled field arithmetic is the most context-dense code in the repo; line count is not a slice-size proxy for it. **Doctrine: crypto files get half-file slices or smaller.** Third attempt `67c728b5` is running L1-120 only with a terse-output contract.
- Pipeline state at entry close: `d7069368` (pairing_client.py, 461 ln + Q1-Q4) and `67c728b5` (spake25519.py L1-120) in flight — the max-2 slots. Next into the first free slot: `spake25519.py` L121-286, then Section 2 order.

### Entry 3 — the pairing wave + pipeline wave (wave three)
- **pairing_client.py DONE** — triple coverage converged: `d7069368` (full 461 ln, Q1-Q5) + `ced65cfd` (L1-230) + `36ecaeb1` (L231-461). No material discrepancies between the three reads. Ledger adds **M10-M12, L25-L31**; Q1-Q5 closed in the CHECKED-SAFE bullet; file moved to fully audited.
- **spake25519.py DONE — parent-audited in full** after three slice deaths on this file. `67c728b5` (presumed dead, actually alive) delivered L1-120 independently; its findings resolved by parent: M/N constants **byte-identical to `_research/aosp/spake25519.c` L36/L41** (grep receipts), `os`/`BASE` live at L193/L199, small-order acceptance is BoringSSL parity. Ledger adds **L32-L34** + the CHECKED-SAFE bullet. Doctrine CONFIRMED: crypto files are audited by the parent — 3 subagent deaths on 286 ln, zero on the parent read.
- **M9 RESOLVED**: parent read of pairing_server L210-250 + the client-side cap (L236) — both header reads flow through `pc._read_header`, payload capped at 16384 before any sized read.
- **pipeline.py DONE** — `6637a64a` (L1-306) + `44ac34b3` (L307-612) landed in the same round. Parent closed the seam: `_siege_loop` (L285-315) abort honored (L290), M13 lock-coverage MED confirmed verbatim, `_attempt_code` clean (L485-491), `run_cmd` returns str so the L542 test is safe. Two slice claims corrected by parent: "zero-auth MED" refuted (app-wide `before_request` gate, app.py L62); dead-import claim refuted for 4 of 5 names (`SAFETY_FLOOR_S` alone is decorative → L46). Ledger adds **M13, L35-L48**; file moved to fully audited.
- **Slot-discipline lesson**: one protocol breach this session (replacements spawned while `d7069368` still lived — LO corrected it). Rule locked: two slots max, respawn ONLY on an explicit death notice, never on assumption. Both "dead" agents delivered — corpses in this pipeline are provisional until the notice arrives.
- Next per Section 2 order: `brain_core.py` (1106 ln) — three ~370-ln slices per the fat-slice doctrine, two slots, third queued.
