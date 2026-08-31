"""
GHOST :: wlan_join.py — see the phone's radio from Windows, walk onto its hotspot.

When the target phone IS the access point, no lure is needed: join its
hotspot and its entire loopback-adjacent surface (wireless debugging,
mDNS chatter, cast protocols) becomes reachable at 192.168.43.1-class
gateway addresses.

Windows-native, netsh-driven — no fragile wlanapi ctypes, works on Win10/11.
"""

import os
import re
import subprocess
import tempfile
import time
import logging
from xml.sax.saxutils import escape as xml_escape

from network_scanner import get_gateway_ip

log = logging.getLogger("ghost.wlan")

# Known Android hotspot SSID grammars (stock + major OEM skins).
HOTSPOT_PATTERNS = [
    (re.compile(r"^AndroidAP", re.I),            "stock-android", 0.9),
    (re.compile(r"^AndroidShare", re.I),         "stock-tether", 0.8),
    (re.compile(r"^AndroidHotspot", re.I),       "lg/xiaomi", 0.85),
    (re.compile(r"^Direct-", re.I),              "wifi-direct-group", 0.7),
    (re.compile(r"^(Galaxy|SM-)[A-Za-z0-9]+", re.I), "samsung-hotspot", 0.75),
    (re.compile(r"^Redmi|^POCO|^Mi \d", re.I),   "xiaomi-hotspot", 0.7),
    (re.compile(r"'s (Galaxy|phone|Pixel)", re.I), "named-hotspot", 0.65),
]


def _netsh(*args, timeout=15):
    """Run netsh wlan and return stdout (raises nothing)."""
    try:
        res = subprocess.run(
            ["netsh", "wlan", *args],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
        )
        return res.stdout or ""
    except Exception as exc:
        log.debug("netsh %s failed: %s", args, exc)
        return ""


def current_connection():
    """Parse `netsh wlan show interfaces` → state/ssid/bssid/radio."""
    out = _netsh("show", "interfaces")
    info = {"state": None, "ssid": None, "bssid": None, "radio": None}
    m = re.search(r"State\s*:\s*(.+)", out)
    if m:
        info["state"] = m.group(1).strip()
    m = re.search(r"\n\s*SSID\s*:\s*(\S.*)", out)
    if m:
        ssid = m.group(1).strip()
        info["ssid"] = None if ssid.lower() == "<name of network not available>" else ssid
    m = re.search(r"BSSID\s*:\s*([0-9a-f:]+)", out, re.I)
    if m:
        info["bssid"] = m.group(1).lower()
    m = re.search(r"Radio type\s*:\s*(.+)", out)
    if m:
        info["radio"] = m.group(1).strip()
    return info


def list_networks():
    """Parse `netsh wlan show networks mode=Bssid` into candidate records."""
    out = _netsh("show", "networks", "mode=Bssid")
    networks = []
    cur = None
    for line in out.splitlines():
        s = line.strip()
        m = re.match(r"SSIDs?\s*\d*\s*:\s*(.+)", s)
        if m:
            if cur:
                networks.append(cur)
            cur = {
                "ssid": m.group(1).strip(),
                "auth": None, "signal": None, "bssids": [],
                **_classify(m.group(1).strip()),
            }
            continue
        if cur is None:
            continue
        m = re.match(r"Authentication\s*:\s*(.+)", s)
        if m:
            cur["auth"] = m.group(1).strip()
        m = re.match(r"Signal\s*:\s*(\d+)%", s)
        if m and cur["signal"] is None:
            cur["signal"] = int(m.group(1))
        m = re.match(r"BSSID\s*:\s*([0-9a-f:]+)", s, re.I)
        if m:
            cur["bssids"].append(m.group(1).lower())
    if cur:
        networks.append(cur)

    # OUI heuristic: Samsung/Xiaomi/Google vendor prefixes raise hotspot odds.
    for n in networks:
        for bssid in n["bssids"]:
            oui = bssid[:8].lower()
            if any(p in oui for p in ("d4:57:63", "ac:5f:3e", "f4:f5:d8",
                                      "dc:0b:34", "3c:5a:b4")):
                # Samsung Electronics OUIs among others — bump confidence
                n["confidence"] = min(1.0, round(n["confidence"] + 0.1, 2))
                break
    networks.sort(key=lambda n: n["confidence"], reverse=True)
    return networks


def _classify(ssid):
    """Pattern-match an SSID against known hotspot grammars."""
    for rx, family, conf in HOTSPOT_PATTERNS:
        if rx.search(ssid):
            return {"hotspot_family": family, "confidence": conf,
                    "likely_hotspot": True}
    return {"hotspot_family": None, "confidence": 0.1,
            "likely_hotspot": False}


def hotspot_opportunities():
    """Scan + classify, flagging joinable phone hotspots."""
    nets = list_networks()
    for n in nets:
        n["joinable"] = bool(n["auth"]) and "Open" not in (n["auth"] or "") \
            or (n["auth"] == "Open")
    return {
        "current": current_connection(),
        "networks": nets,
        "hotspot_candidates": [n for n in nets if n["likely_hotspot"]],
    }


def _profile_xml(ssid, password):
    """Build a Windows WLAN profile (WPA2PSK/AES, or open when no password)."""
    if password:
        security = (
            "<authEncryption>"
            "<authentication>WPA2PSK</authentication>"
            "<encryption>AES</encryption><useOneX>false</useOneX>"
            "</authEncryption>"
            "<sharedKey><keyType>passPhrase</keyType>"
            "<protected>false</protected>"
            f"<keyMaterial>{xml_escape(password)}</keyMaterial></sharedKey>"
        )
    else:
        security = (
            "<authEncryption>"
            "<authentication>open</authentication>"
            "<encryption>none</encryption><useOneX>false</useOneX>"
            "</authEncryption>"
        )
    return (
        '<?xml version="1.0"?><WLANProfile '
        'xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">'
        f"<name>{xml_escape(ssid)}</name>"
        f"<SSIDConfig><SSID><name>{xml_escape(ssid)}</name></SSID></SSIDConfig>"
        "<connectionType>ESS</connectionType>"
        "<connectionMode>manual</connectionMode>"
        f"<MSM><security>{security}</security></MSM>"
        "</WLANProfile>"
    )


def connect_hotspot(ssid, password=None, settle_seconds=18):
    """Add (if needed) a profile and associate; poll until Windows agrees.

    Returns dict with success, final state, gateway IP once associated.
    """
    profile_path = ""
    try:
        fd, profile_path = tempfile.mkstemp(suffix=".xml")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(_profile_xml(ssid, password))
        add = _netsh("add", "profile", f"filename={profile_path}", "user=all")
        if "already exists" not in add.lower() and not add.strip():
            pass  # some builds print nothing on success — verify by connecting

        conn = _netsh("connect", f"name={ssid}", "iface=Wi-Fi",
                      f"profile={ssid}")
        deadline = time.time() + settle_seconds
        while time.time() < deadline:
            time.sleep(2)
            state = current_connection()
            if state["ssid"] == ssid and state["state"] in ("connected",):
                gw = get_gateway_ip()
                return {"success": True, "ssid": ssid,
                        "state": state["state"], "gateway_ip": gw,
                        "note": "on the phone's subnet — run ghost sweep now"}
        return {"success": False, "ssid": ssid,
                "error": conn.strip() or "association timed out",
                "last_state": current_connection()}
    finally:
        if profile_path and os.path.exists(profile_path):
            try:
                os.remove(profile_path)
            except OSError:
                pass
