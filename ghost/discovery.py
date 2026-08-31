"""
GHOST :: discovery.py — find Android wireless-debugging surfaces on the airwaves.

Two ears:
  1. mDNS browsing for _adb-tls-connect / _adb-tls-pairing announcements.
     Wireless debugging ports randomize into the ephemeral range on every
     toggle — mDNS is the map; blind scanning is only the fallback.
  2. Legacy TCP sweep of the local subnet(s) on port 5555 (adb tcpip mode)
     reusing DroidCommand's proven scanner primitives.

Every discovered endpoint gets banner-fingerprinted with the same CNXN probe
network_scanner already uses, so the pipeline can branch instantly:
open_cnxn | STLS(TLS-required) | AUTH(key-required).
"""

import threading
import time
import logging

from network_scanner import (
    probe_adb_banner,
    get_local_ip,
    get_subnet_prefix,
    scan_subnet,
)

log = logging.getLogger("ghost.discovery")

try:
    from zeroconf import Zeroconf, ServiceBrowser
    HAVE_ZEROCONF = True
except ImportError:
    HAVE_ZEROCONF = False
    log.warning("zeroconf not installed — mDNS ear is deaf, TCP sweep only")

# Service types as seen across Android 11 → 15 builds (trailing dot varies).
CONNECT_TYPES = [
    "_adb-tls-connect._tcp.local.",
    "_adb-tls-connect._tcp.",
]
PAIRING_TYPES = [
    "_adb-tls-pairing._tcp.local.",
    "_adb-tls-pairing._tcp.",
]


class _Collector:
    """Thread-safe sink for zeroconf callbacks."""

    def __init__(self):
        self.lock = threading.Lock()
        self.connect_records = {}
        self.pairing_records = {}

    def _record(self, bucket, zc, type_, name):
        try:
            info = zc.get_service_info(type_, name)
            if info is None:
                return
            addresses = info.parsed_addresses() or []
            rec = {
                "name": name,
                "service_type": type_,
                "host": info.server.rstrip(".") if info.server else "",
                "ip": addresses[0] if addresses else "",
                "port": int(info.port or 0),
                "properties": {
                    str(k, "utf-8", "replace"): str(v, "utf-8", "replace")
                    for k, v in (info.properties or {}).items()
                },
                "seen_at": time.time(),
            }
            if not rec["ip"] or not rec["port"]:
                return
            with self.lock:
                bucket[rec["ip"]] = rec   # keyed by IP — latest wins
        except Exception as exc:
            log.debug("mDNS record parse failed for %s: %s", name, exc)

    def add_service(self, zc, type_, name):
        bucket = (self.pairing_records if "_pairing_" in type_
                  else self.connect_records)
        self._record(bucket, zc, type_, name)

    def update_service(self, zc, type_, name):
        self.add_service(zc, type_, name)

    def remove_service(self, zc, type_, name):
        pass  # short listening windows make removal tracking pointless


def _browse_types(types, window):
    """Browse a set of mDNS types concurrently for `window` seconds."""
    collector = _Collector()
    browsers = []
    zc = Zeroconf()
    try:
        for t in types:
            try:
                browsers.append(ServiceBrowser(zc, t, collector))
            except Exception as exc:
                log.debug("browser failed on %s: %s", t, exc)
        time.sleep(window)
    finally:
        zc.close()
    return collector


def discover_mdns(window=8.0):
    """Listen for wireless-debugging announcements.

    Returns {"connect": [rec...], "pairing": [rec...], "zeroconf": bool}.
    Pairing records are gold — they mean the pairing dialog is OPEN on a
    screen right now, which is the one window the SPAKE2+ siege can fire.
    """
    if not HAVE_ZEROCONF:
        return {"connect": [], "pairing": [], "zeroconf": False}
    collector = _browse_types(CONNECT_TYPES + PAIRING_TYPES, window)
    with collector.lock:
        return {
            "connect": list(collector.connect_records.values()),
            "pairing": list(collector.pairing_records.values()),
            "zeroconf": True,
        }


def _banner_tag(rec):
    """Attach an ADB fingerprint verdict to a discovered record."""
    try:
        banner = probe_adb_banner(rec["ip"], rec["port"], timeout=3)
    except Exception as exc:
        banner = {"is_adb": False, "error": str(exc)}
    out = dict(rec)
    out["banner"] = banner
    if banner.get("open_cnxn"):
        out["verdict"] = "OPEN"          # unauthenticated CNXN — legacy tcpip
    elif banner.get("tls_required"):
        out["verdict"] = "STLS"          # TLS upgrade demanded — CVE territory
    elif banner.get("auth_required"):
        out["verdict"] = "AUTH"          # classic RSA token gate
    elif banner.get("is_adb"):
        out["verdict"] = "ADB_UNKNOWN"
    else:
        out["verdict"] = "NOT_ADB"
    return out


def sweep_subnet(ports=(5555,), timeout=0.8):
    """Fallback ear: TCP sweep every local subnet prefix on legacy ADB ports."""
    targets = []
    prefixes = set()
    for local_ip in {get_local_ip()}:
        if local_ip:
            prefixes.add(get_subnet_prefix(local_ip))
    # ARP table neighbors often sit on a different /24 than our primary
    # (hotspot subnets!) — harvest their prefixes too.
    try:
        from network_scanner import get_arp_table
        for entry in get_arp_table():
            ip = entry.get("ip") if isinstance(entry, dict) else None
            if ip:
                prefixes.add(get_subnet_prefix(ip))
    except Exception:
        pass

    for prefix in prefixes:
        try:
            for hit in scan_subnet(prefix, ports=list(ports), timeout=timeout):
                if hit.get("open"):
                    targets.append({"ip": hit["ip"], "port": hit["port"],
                                    "source": f"tcp-sweep:{prefix}"})
        except Exception as exc:
            log.debug("subnet sweep failed on %s: %s", prefix, exc)
    return targets


def full_sweep(mdns_window=8.0, include_subnet=True):
    """One call: listen to the air, sweep the wire, fingerprint everything.

    Returns a unified target list, deduplicated by ip:port, each tagged:
      source, verdict (OPEN|STLS|AUTH|NOT_ADB), banner details,
      and `pairing_open` flag when a live pairing service advertises.
    """
    merged = {}

    mdns = discover_mdns(window=mdns_window)
    for rec in mdns["connect"]:
        key = f'{rec["ip"]}:{rec["port"]}'
        merged[key] = _banner_tag({**rec, "source": "mdns:connect"})
    pairing_hosts = list(mdns["pairing"])
    pairing_ips = {rec["ip"] for rec in pairing_hosts}

    if include_subnet:
        for hit in sweep_subnet():
            key = f"{hit['ip']}:{hit['port']}"
            if key not in merged:
                merged[key] = _banner_tag({**hit, "source": "tcp-sweep",
                                           "name": "", "host": ""})
            else:
                merged[key].setdefault("source", hit["source"])

    targets = list(merged.values())
    # Tag AFTER the merge so every record from a pairing-announcing host
    # lights up — including adbd instances found later by the tcp sweep
    # (order of discovery must not decide what the UI can see).
    for t in targets:
        t["pairing_dialog_open"] = t["ip"] in pairing_ips

    return {
        "targets": targets,
        "pairing_services": [
            {"name": r["name"], "ip": r["ip"], "port": r["port"]}
            for r in pairing_hosts
        ],
        "zeroconf_available": mdns["zeroconf"],
        "scanned_at": time.time(),
    }
