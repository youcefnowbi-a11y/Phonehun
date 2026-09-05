"""
PANOPTICON :: geo_tri.py — locate the phone with GPS OFF.

Three ears, fused:
  1. Wi-Fi scan results (BSSID + signal) via `cmd wifi` — the strongest
     passive locator on modern Android from shell uid.
  2. Cell identity from `dumpsys telephony.registry` (MCC/MNC/LAC/CID per
     registered cell) — coarse but works everywhere with SIM service.
  3. Last-known GPS from your existing surveillance module when it's there.

Optional enrichment: set env WIGLE_API_KEY=<token> and BSSIDs resolve to
lat/lon estimates automatically (api.wigle.net). Without a key, output is
a structured dossier ready for manual resolution — nothing fake.
"""

import os
import re
import time
import json
import math
import logging
import urllib.request
import urllib.parse

from flask import Blueprint, jsonify, request

from adb_engine import ADBEngine
from panopticon import geo_math

log = logging.getLogger("panopticon.geo")

geo_bp = Blueprint("geo", __name__, url_prefix="/api/geo")
engine = ADBEngine()

WIGLE_KEY = os.environ.get("WIGLE_API_KEY", "").strip()


def _shell(cmd, serial=None, timeout=20):
    return engine.shell(cmd, timeout=timeout, serial=serial)


def _valid_latlon(lat, lon):
    """True iff both coords are finite and inside the globe's ranges."""
    try:
        lat, lon = float(lat), float(lon)
    except (TypeError, ValueError):
        return False
    return (math.isfinite(lat) and math.isfinite(lon)
            and -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0)


def _clean(obj):
    """jsonify-safe: non-finite floats → None (bare NaN is invalid JSON)."""
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


# --------------------------------------------------------------------------
# Wi-Fi ear
# --------------------------------------------------------------------------
_BSSID_LINE = re.compile(
    r"(?P<bssid>(?:[0-9a-f]{2}:){5}[0-9a-f]{2})\s+"
    r"(?P<freq>\d{4})\s+"
    r"(?P<level>-?\d+)\s+"
    r"(?P<flags>\S+)\s*"
    r"(?P<ssid>.*)$")


def wifi_ear(serial=None):
    """Trigger a fresh scan and harvest surrounding access points."""
    _shell("cmd wifi start-scan", serial=serial, timeout=10)
    time.sleep(3.0)
    res = _shell("cmd wifi list-scan-results", serial=serial, timeout=15)
    aps = []
    for line in (res.get("stdout") or "").splitlines():
        line = line.rstrip()
        m = _BSSID_LINE.search(line)
        if m:
            aps.append({
                "bssid": m.group("bssid").lower(),
                "freq_mhz": int(m.group("freq")),
                "rssi_dbm": int(m.group("level")),
                "ssid": m.group("ssid").strip(),
            })
    aps.sort(key=lambda a: a["rssi_dbm"], reverse=True)   # strongest first
    return {"aps": aps, "count": len(aps),
            "raw_ok": bool(res.get("success"))}


# --------------------------------------------------------------------------
# Cell ear
# --------------------------------------------------------------------------
def cell_ear(serial=None):
    """Registered cell identities from telephony registry + getprop fallbacks."""
    res = _shell("dumpsys telephony.registry", serial=serial, timeout=20)
    raw = res.get("stdout") or ""
    cells = []

    # mLteCellIdentity / mGsmCellIdentity blocks: { mcc=XXX mnc=XX lac=... cid=... }
    for m in re.finditer(
            r"m(?:Lte|Gsm|Tdscdma|Cdma)CellIdentity=\{?[^}]*?"
            r"mcc=(\d{2,3})[^}]*?mnc=(\d{1,3})[^}]*?"
            r"(?:lac=(\d+))?[^}]*?(?:cid=(\d+))?", raw):
        cells.append({"radio": "lte-or-older", "mcc": m.group(1),
                      "mnc": m.group(2), "lac": m.group(3), "cid": m.group(4)})
    # NR (5G) identity shape differs; catch nci if present
    for m in re.finditer(r"mNrCellIdentity=\{?[^}]*?mcc=(\d{2,3})[^}]*?"
                         r"mnc=(\d{1,3})[^}]*?nci=(\d+)", raw):
        cells.append({"radio": "nr", "mcc": m.group(1), "mnc": m.group(2),
                      "nci": m.group(3)})

    props = {}
    for prop in ("gsm.operator.alpha", "gsm.operator.numeric",
                 "gsm.sim.operator.numeric", "gsm.network.type"):
        r = _shell(f"getprop {prop}", serial=serial, timeout=8)
        props[prop] = (r.get("stdout") or "").strip()
    return {"cells": cells, "props": props}


# --------------------------------------------------------------------------
# GPS ear (last-known only; your surveillance module owns live fixes)
# --------------------------------------------------------------------------
def gps_last_known(serial=None):
    res = _shell("dumpsys location", serial=serial, timeout=20)
    out = res.get("stdout") or ""
    last = None
    # PRIMARY: the documented "last location: Location[...]" block — coords
    # live inside the brackets (labeled lat/lon or a bare "lat,lon" pair)
    m = re.search(r"last location[^:]*:\s*Location\[([^\]]*)\]", out, re.I)
    if m:
        blk = m.group(1)
        mp = (re.search(r"lat[: =]+(-?\d+\.\d+)[,;\s]+lon(?:gitude|g)?[: =]+(-?\d+\.\d+)",
                        blk, re.I)
              or re.search(r"(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)", blk))
        if mp:
            acc = re.search(r"acc[=:]\s*(\d+(?:\.\d+)?)", blk, re.I)
            last = {"lat": float(mp.group(1)), "lon": float(mp.group(2)),
                    "accuracy_m": float(acc.group(1)) if acc else None,
                    "source": "dumpsys-last-known"}
    # FALLBACK: loose first-lat/lon anywhere in dumpsys (also matches the
    # "Longitude:" spelling)
    if last is None:
        m2 = re.search(r"[Ll](?:at|atitude)[: =]+(-?\d+\.\d+)[^\n]*?"
                       r"[Ll]on(?:gitude|g)?[: =]+(-?\d+\.\d+)", out)
        if m2:
            acc = re.search(r"acc[=:]\s*(\d+(?:\.\d+)?)", out[m2.start():m2.end()+80], re.I)
            last = {"lat": float(m2.group(1)), "lon": float(m2.group(2)),
                    "accuracy_m": float(acc.group(1)) if acc else None,
                    "source": "dumpsys-last-known"}
    return {"fix": last}


# --------------------------------------------------------------------------
# Wigle enrichment (optional; honest skip without key)
# --------------------------------------------------------------------------
def _wigle_bssid(bssid):
    if not WIGLE_KEY:
        return None
    try:
        url = ("https://api.wigle.net/api/v2/network/detail?" +
               urllib.parse.urlencode({"netid": bssid}))
        req = urllib.request.Request(url, headers={
            "Authorization": f"Basic {WIGLE_KEY}",
            "User-Agent": "DroidCommand-GeoTri/1.0",
        })
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        res = data.get("results", {})
        return {"lat": res.get("trilat"), "lon": res.get("trilong"),
                "ssid": res.get("ssid"), "last_seen": res.get("lasttime"),
                "source": "wigle"}
    except Exception as exc:
        log.debug("wigle %s failed: %s", bssid, exc)
        return None


# --------------------------------------------------------------------------
# Fused snapshot
# --------------------------------------------------------------------------
@geo_bp.route("/snapshot")
def snapshot():
    """One call: wifi ear + cell ear + last-known GPS, fused & enriched."""
    serial = (request.args.get("serial") or "").strip() or None
    started = time.time()

    # Each ear fails honest & separate — one deaf ear never sinks the dossier.
    def _safe(ear):
        try:
            return ear()
        except Exception as exc:      # adb absent / no device / timeout
            log.debug("ear %s failed: %s", ear.__name__, exc)
            return {"error": str(exc)}
    wifi = _safe(lambda: wifi_ear(serial))
    cell = _safe(lambda: cell_ear(serial))
    gps = _safe(lambda: gps_last_known(serial))
    if not isinstance(wifi, dict):        # noqa: defensive (never happens)
        wifi = {}
    wifi.setdefault("aps", [])
    wifi.setdefault("count", 0)

    # Enrich top 8 APs by signal — those pin the room, not the city.
    # Ears with a junk coordinate are skipped BEFORE fusion so one bad
    # WiGLE hit can't raise inside fuse_position.
    resolved = []
    for ap in wifi["aps"][:8]:
        hit = _wigle_bssid(ap["bssid"])
        if hit and _valid_latlon(hit.get("lat"), hit.get("lon")):
            resolved.append({**ap, **hit})
    estimate = None
    if resolved:
        # Physics layer: log-distance ranges + weighted linearized LS
        # trilateration, degrading honestly to circle-intersection /
        # range-circle / power-centroid as anchors thin out. The old
        # (100 + rssi_dbm) linear-in-dBm weighting is retired — dBm is a
        # logarithm; the physical weight is 10^(rssi/10) milliwatts.
        gps_fix = gps.get("fix")
        if gps_fix and not _valid_latlon(gps_fix.get("lat"), gps_fix.get("lon")):
            gps_fix = None
        estimate = geo_math.fuse_position(resolved, gps_last_known=gps_fix)

    cell_unavailable = None
    if cell.get("error"):
        cell_unavailable = "cell ear failed"      # detail stays in log
    elif not cell.get("cells"):
        cell_unavailable = "no cell identity reported"

    return jsonify(_clean({
        "success": True,
        "serial": serial,
        "elapsed_s": round(time.time() - started, 1),
        "wifi": wifi,
        "wifi_aps_truncated": len(wifi["aps"]) > 8,
        "cell": cell,
        "cell_unavailable": cell_unavailable,
        "gps_last_known": gps.get("fix"),
        "wigle_resolved": resolved,
        "estimate": estimate,
        "wigle_enabled": bool(WIGLE_KEY),
        "note": "sans clé wigle: dossier structuré prêt pour résolution "
                "manuelle (mylnikov/wigle web). avec clé: estimation directe.",
    }))
