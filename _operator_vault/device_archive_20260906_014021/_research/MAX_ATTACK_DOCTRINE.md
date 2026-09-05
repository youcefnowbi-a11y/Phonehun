# MAX ATTACK DOCTRINE — DroidCommand Engagement Charter
*Gate ⑦ · the plan of max attack · every tool, every vector, one machine.*

---

## 0. CREED

1. **We strike doors, not walls.** Every Android version has a weakness, but
   the weakness is never magic — it is a **STATE**: a dialog left open, a
   port forgotten on, a service broadcasting, a hotspot with no isolation.
   We do not hunt versions. We hunt states.
2. **Zero human latency.** The moment a door opens on the wire, the strike
   is already in flight. Prey attacks itself by opening the menu.
3. **Honesty is a weapon system.** Every strike reports its true verdict:
   HIT, GATED, DORMANT, REFUSED. A tool that lies about a breach is worse
   than no tool.
4. **The scalpel rule.** Scope stays local, one siege at a time, one
   ABORT button. Force is organized or it is noise.

---

## 1. THE FIVE DOOR CLASSES (triage table)

| Class | State on target | Our weapon | Result |
|---|---|---|---|
| `OPEN_ADB` | Legacy tcpip 5555 answering, no TLS wall | `adb connect` walk-in (`_adb_connect_and_verify`) | Full shell in seconds |
| `PAIRING_DIALOG` | Wireless-debugging pairing dialog LIVE (mDNS `_adb-tls-pairing`) | Auto-siege (mathcore biased 6-digit stream, real SPAKE2 client) | Pair = permanent trust |
| `STLS` | ADB demanding TLS upgrade, CNXN open | Type-confusion chain (`_cve_bypass_chain`, EC then RSA cert flavors) | Shell if unpatched |
| `GATED` | adbd up, RSA gate closed, no dialog | Watch — strike when dialog opens | No wasted attempts |
| `DORMANT` | Nothing answering | Watch for state change | No wasted attempts |

Classification is computed by `Hunter._classify` from `full_sweep` triage:
`pairing_dialog_open` flag first, then banner verdict `OPEN|STLS|AUTH|NOT_ADB`.

---

## 2. VECTOR INVENTORY (what the war room can actually fire)

### 2.1 Wi-Fi / network vectors — `ghost/`
| Vector | Tool | Endpoint | Status |
|---|---|---|---|
| Ear + wire sweep (mDNS + tcp 5555 + banner fingerprint) | `discovery.full_sweep` | `/api/ghost/sweep` | LIVE |
| Hotspot census ("which SSIDs smell like phone hotspots") | `hotspot_opportunities` | `/api/ghost/radio` | LIVE |
| Join a target hotspot, get its gateway | `connect_hotspot` | `/api/ghost/join` | LIVE |
| ADB decision tree per target (banner → walk-in / STLS chain / verdict) | `/attack` route | `/api/ghost/attack` | LIVE |
| Pairing siege, sync | `_siege_loop` | `/api/ghost/pairing-siege` | LIVE |
| Pairing siege, long-haul async | `start_siege` | `/api/ghost/pairing-siege/async` | LIVE |
| Real SPAKE2 pairing (code known / read off the screen) | `pairing_client.pair_async` | `/api/ghost/pair` | LIVE |
| QR pairing gate (workstation = server; phone scans, stores our RSA key) | `pairing_server` | `/api/ghost/qr/start` | LIVE |
| **Hunter orchestrator** — triage → strike → enroll → watch | `hunter.Hunter` | `/api/ghost/hunter/*` | LIVE (gate ⑦) |

### 2.2 USB vectors — `app.py` + `adb_engine`
| Vector | Condition | Status |
|---|---|---|
| Full device control (screen, mic, cam, GPS, notif, keylog, clipboard, SMS, history) | USB debugging **enabled + authorized** | LIVE |
| Skeleton agents (PIN siege on-device, neutralizer, cred harvest) | Authorized ADB | LIVE |
| USB *without* debugging | MTP/PTP only — photo pull needs an on-screen tap; no ADB surface | HONEST LIMIT |

### 2.3 Senses once enrolled — `panopticon/`
Screen console (tap/swipe/type), H.264 native cast (device MediaCodec,
180 s cap per arm), geo trilateration (Wi-Fi RSSI WLS + cell TA + GPS
last-known, honest RMS), all token-gated at `/api/screen/*`, war room panels.

---

## 3. THE ENGAGEMENT LOOP (how the machine thinks)

```
        ┌────────────────────────────────────────────┐
        ▼                                            │
  [ LISTEN ]  mDNS watcher, 4 s cadence ──── new _adb-tls-pairing?
        │                          yes ──► [ STRIKE: auto-siege ]
  [ TRIAGE ]  /hunter/sweep                       │
        │                          PAIRED ──► [ ENROLL: adb connect ]
  [ STRIKE ]  per-target best vector  ◄── manual or auto
        │
  [ REPORT ]  verdict to war log — HIT / GATED / DORMANT / REFUSED
        │
  [ WATCH ]   dormant & gated targets stay marked; door opens → strike
        └────────────────────────────────────────────┘
```

- **Arm** (`/hunter/arm`): watcher thread live; strikes new dialogs in < 1 s
  after announcement.
- **Strike Sweep** (`/hunter/sweep`): full triage, no strikes — pure intel.
- **Strike** (`/hunter/engage`): one target, best vector, honest verdict.
- **Stand Down** (`/hunter/standdown`): watcher stops, siege abort signaled.
  Nothing deleted — the log remembers the war.

## 4. HONEST LIMITS (named, not hidden)

- Android 11+ mints pairing codes **only** inside the open dialog, 6 digits,
  ~60 s life, ~10 dialogs per window: the siege math models exactly this.
  A phone that never opens the dialog is a wall — we watch, we don't bleed.
- `STLS` chain is a hand-built CVE-class probe: unpatched targets fall,
  patched targets log the rejection — that log is intel, not failure.
- USB without developer debugging = MTP/PTP at best; there is no ADB
  surface to ride. Honest.
- Monitor-mode Wi-Fi attacks (handshake capture, WPS) need a monitor-capable
  adapter — not present in this lab. Doctrine notes it; we don't fake it.
- Everything binds 127.0.0.1 behind `X-API-Token`; the war stays local.

## 5. ROADMAP (the queue after gate ⑦)

- ④ beaconDB / OpenCellID fusion → geo gets a second eye (DB file vs API key)
- ⑤ Passive LAN recon → DHCP 55/60 fingerprints, mDNS census diff, ARP watch
- ⑥ IMMORTAL hardening → Android 15/16 FGS types, dataSync quota math
- Sub-gates: fMP4/MSE glass (paint the H.264 river in the browser),
  cast-to-file recording toggle, scrcpy-server jar upgrade for input mux.

---
*Doctrine written with the Hunter live. Strikes doors, not walls.*
