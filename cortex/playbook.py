"""CORTEX :: playbook.py — the compounding arsenal (VOID-TRANSPLANT).

Distilled from youcefnowbi-a11y/void @ 8cfae3c (VOIDFORGE tip): core/playbooks.py,
core/learned_plays.py, core/coverage.py — adapted to DroidCommand's Android domain.

Three organs live here:

  1. THE DISTILLERY  — after every run (task or chat), the executed tool
     sequence is harvested. Missions on similar ground later receive the
     PROVEN SEQUENCES back as a prompt block: she opens missions already
     knowing which chains of HER OWN tools produced results before.

  2. THE RECIPE CARD — the domain grammar of the 47-tool belt: canonical
     chains (recon -> see -> act; siege order; network strike order; comms
     pull order). This is the cure for "she doesn't know how to use her
     tools": grammar is taught, not hoped for.

  3. THE COVERAGE LAW — every 8 steps in task mode the loop audits which
     benches (recon/screen/shell/files/comms/siege/network/apps/host) the
     mission has touched. A bench the mission text implies but never
     struck earns a HARD user-message order naming concrete untried
     weapons from the live belt. Ignored orders escalate. This is void's
     Tier F anti-stagnation spine, translated from web benches to ours.

Pure stdlib, no imports from brain_core — the loop calls in, the module
never imports back (mirrors void coverage.py's discipline).
"""
import json
import os
import re
import threading
import time

# ── storage: cortex/memory/playbooks.json (rides the existing memory dir) ──
_HERE = os.path.dirname(os.path.abspath(__file__))
STORE = os.path.join(_HERE, "memory", "playbooks.json")
_LOCK = threading.Lock()
_MAX_PLAYS = 60          # the distillery's cap (void: 60)
_MIN_SEQ = 3             # a sequence shorter than this is noise, not grammar

# ── mission fingerprints (void _fingerprint, domain-adapted) ────────────────
# keyword families -> stack tags. A mission earns a tag when any keyword hits.
DROID_STACKS = {
    "screen": ("screen", "screenshot", "capture", "display", "vision"),
    "comms": ("sms", "text", "call", "contact", "message", "whatsapp",
              "telegram", "inbox", "notif"),
    "files": ("file", "download", "sdcard", "folder", "media", "photo",
              "gallery", "video"),
    "siege": ("pin", "lock", "unlock", "siege", "passcode", "code", "keyguard"),
    "network": ("lan", "sweep", "target", "engage", "pair", "wifi", "hunter",
                "port", "network", "adb-over", "remote"),
    "apps": ("app", "package", "install", "launch", "uninstall", "apk", "stop"),
    "host": ("powershell", "panel", "host", "machine", "pc", "windows"),
    "recon": ("info", "devices", "props", "dumpsys", "battery", "state",
              "check", "what", "status"),
    "surveillance": ("record", "spy", "surveillance", "location", "gps",
                     "geo", "camera", "mic", "clipboard"),
    "deep": ("root", "deep", "settings", "secure", "system", "shell"),
}


def fingerprint(mission):
    """Mission text -> sorted stack tags (void playbooks._fingerprint)."""
    text = str(mission or "").lower()
    return tuple(sorted(t for t, kws in DROID_STACKS.items()
                        if any(k in text for k in kws)))


def _match_score(need, have):
    """Jaccard-flavored overlap between tag tuples (void playbooks.py:38)."""
    if not need or not have:
        return 0
    return len(set(need) & set(have)) / len(set(need) | set(have))


# ── organ 1: the distillery ──────────────────────────────────────────────────

def _load():
    try:
        with open(STORE, encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {"plays": []}
    except Exception:
        return {"plays": []}


def _save(d):
    """Atomic save with the Windows reader-retry (void R2-4 pattern:
    os.replace can meet a concurrent open handle -> 3x 0.2s backoff)."""
    os.makedirs(os.path.dirname(STORE), exist_ok=True)
    tmp = STORE + ".tmp"
    for i in range(3):
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=1)
            os.replace(tmp, STORE)
            return
        except PermissionError:
            time.sleep(0.2 * (i + 1))
        except Exception:
            return


def record(mission, seq, mode="task"):
    """Harvest one executed run. `seq` is the ordered list of (tool, ok)
    the loop journaled. Only grammars with real mass are distilled:
    length >= _MIN_SEQ and at least one succeeded step. Dedupe is by
    grammar identity (first 10 tool names), not by mission wording —
    two wordings of the same play collapse into one line."""
    try:
        steps = [(str(t), bool(o)) for t, o in (seq or [])]
    except Exception:
        return False
    if len(steps) < _MIN_SEQ or not any(o for _, o in steps):
        return False
    names = [t for t, _ in steps]
    sig = "→".join(names[:10])
    with _LOCK:
        d = _load()
        plays = d.get("plays") or []
        for p in plays:
            if p.get("sig") == sig:
                p["ts"] = time.time()
                p["count"] = int(p.get("count", 1)) + 1
                p["last_mission"] = str(mission or "")[:160]
                _save(d)
                return False        # strengthened, not duplicated
        plays.append({
            "sig": sig,
            "mission": str(mission or "")[:160],
            "tags": list(fingerprint(mission)),
            "mode": str(mode)[:10],
            "count": 1,
            "ts": time.time(),
        })
        plays.sort(key=lambda p: -p.get("ts", 0))
        d["plays"] = plays[:_MAX_PLAYS]
        _save(d)
        return True


def recall_block(mission, limit=2):
    """Prompt block of PROVEN SEQUENCES on similar ground (void
    playbooks.prompt_block: score>0 overlap filter, capped)."""
    tags = fingerprint(mission)
    if not tags:
        return ""
    with _LOCK:
        d = _load()
    scored = []
    for p in d.get("plays") or []:
        s = _match_score(tags, tuple(p.get("tags") or ()))
        if s > 0:
            scored.append((s, p))
    scored.sort(key=lambda x: (-x[0], -x[1].get("count", 1), -x[1].get("ts", 0)))
    if not scored:
        return ""
    lines = ["═══ PROVEN SEQUENCES (your own past tool chains that produced "
             "results on similar ground — replay what worked, then extend) ═══"]
    for s, p in scored[:limit]:
        lines.append(f"- [{p.get('mode', '?')}] {p['sig']}"
                     f"   (ground: {p.get('mission', '')[:80]} | reused {p.get('count', 1)}x)")
    lines.append("These are FLOORS, not ceilings: start from the proven chain, "
                 "adapt it to THIS device, invent the next link when the ground differs.")
    return "\n".join(lines)


def play_count():
    with _LOCK:
        return len((_load().get("plays")) or [])


# ── organ 2: the recipe card — the domain grammar of the belt ────────────────

RECIPE_BLOCK = """═══ TOOL GRAMMAR — THE CHAINS THAT WIN (learn these; improvise around them) ═══

RECON LADDER (open EVERY mission with it — see before you touch):
  list_devices → device_info → screen_capture
  A binary result means the artifact was SAVED to cortex_shots/ and its path came back — cite it, don't re-run.

SEE / ACT ON SCREEN:
  screen_capture (read what's there) → screen_tap(x,y) / screen_text(str) / screen_key(code)
  One change per step: tap → capture again → read the NEW screen. Never fire taps blind.

SIEGE ORDER (lockscreen assault — the full ritual):
  list_devices → skeleton_snapshot(serial) → pin_siege_start(serial, preset) →
  pin_siege_status (POLL between attempts, never spam) → pin_siege_stop
  If the siege stalls >3 polls: report vitals honestly, propose the next vector.

NETWORK STRIKE ORDER (the phone is not the only organism):
  network_sweep → hunter_status → engage_target(ip, port)
  Sweep first, read the classification, THEN strike the best vector.

COMMS PULL ORDER (reading his digital life):
  read_sms / read_calls / read_contacts / read_notifications / read_clipboard / browser_history
  Big results arrive as {page_id, total, more:true} — page(offset, limit) to walk deeper. NEVER truncate a read mid-way silently; say what you pulled.

FILES ORDER:
  list_files(path) → download_file(remote, local) — name the destination, report byte counts.

SHELL IS THE MASTER KEY:
  shell(command) runs ON THE DEVICE as shell user — dumpsys, pm, am, settings, input.
  host_shell(command) runs ON THE PANEL MACHINE. Know which machine you are standing on.

LONG OUTPUTS: page(name, offset, limit) — walk them, don't dump them.
SKILLS: list_skills → run_skill(name, args) — reload proven procedures instead of re-deriving.
DOCTRINE: doctrine_list → doctrine_read(name) — the standing orders live there; read them when in doubt.

EVIDENCE LAW: report numbers (counts, paths, ms, attempt numbers), never vibes.
SNAPSHOT LAW: skeleton_snapshot before any lockscreen/settings modification.
HONEST NEGATIVE LAW: a clean result ("no devices", "0 sms") is a VALID discovery — report it and adapt."""


def recipe_block():
    return RECIPE_BLOCK


# ── organ 3: the coverage law — anti-stagnation orders (void coverage.py) ────

COVERAGE_PERIOD = 8       # steps between coverage audits (void: 6 rounds)
IGNORED_ESCALATION = 2    # ignored orders before the order hardens (void: 3)

# tool -> bench map for the live belt
_BENCH = {}
for _t in ("list_devices", "device_info", "device_props", "dumpsys", "battery"):
    _BENCH[_t] = "recon"
for _t in ("screen_capture", "screen_tap", "screen_text", "screen_swipe",
           "screen_key"):
    _BENCH[_t] = "screen"
for _t in ("shell", "host_shell"):
    _BENCH[_t] = "shell"
for _t in ("list_files", "download_file"):
    _BENCH[_t] = "files"
for _t in ("read_sms", "read_calls", "read_contacts", "read_notifications",
           "read_clipboard", "browser_history", "send_sms"):
    _BENCH[_t] = "comms"
for _t in ("list_apps", "launch_app", "stop_app"):
    _BENCH[_t] = "apps"
for _t in ("pin_siege_start", "pin_siege_status", "pin_siege_stop",
           "skeleton_snapshot", "skeleton_neutralize"):
    _BENCH[_t] = "siege"
for _t in ("network_sweep", "engage_target", "hunter_arm", "hunter_status",
           "hunter_standdown"):
    _BENCH[_t] = "network"
for _t in ("gps_location", "camera_capture", "mic_record"):
    _BENCH[_t] = "surveillance"
for _t in ("memory_append", "memory_read", "memory_write", "read_ledger",
           "page", "save_skill", "list_skills", "run_skill",
           "doctrine_list", "doctrine_read", "read_manual"):
    _BENCH[_t] = "memory"

# benches the mission text can imply (fingerprint tag -> bench + strike ladder)
_IMPLIED = {
    "screen": ("screen", ("screen_capture", "screen_tap", "screen_text")),
    "comms": ("comms", ("read_sms", "read_calls", "read_contacts")),
    "files": ("files", ("list_files", "download_file")),
    "siege": ("siege", ("pin_siege_start", "skeleton_snapshot")),
    "network": ("network", ("network_sweep", "engage_target")),
    "apps": ("apps", ("list_apps", "launch_app")),
    "surveillance": ("surveillance", ("gps_location", "camera_capture", "mic_record")),
}

# discovery signal — a result that shows the run FOUND something
# (void coverage._DISCOVERY_RX, translated to DroidCommand result shapes)
_DISCOVERY_RX = re.compile(
    r'"unlocked"\s*:\s*true'
    r'|"success"\s*:\s*true'
    r'|"devices"\s*:\s*\['
    r'|"count"\s*:\s*[1-9]\d*'
    r'|"saved"\s*:\s*true'
    r'|"bytes"\s*:\s*[1-9]\d*'
    r'|"attempts"\s*:\s*[1-9]\d*'
    r'|"records"\s*:\s*[1-9]\d*'
    r'|"serial"',
    re.I)


def discovery(text):
    """True when a tool result shows the run actually FOUND something."""
    if not text:
        return False
    return bool(_DISCOVERY_RX.search(str(text)))


def bench_of(tool):
    return _BENCH.get(tool, "other")


def coverage_order(step, ok_seq, mission, ignored=0):
    """The hard user-message order when an implied bench is cold.
    ok_seq: [(tool, ok)] journaled so far. Returns a prompt block or "".
    Pure function — the loop decides when to call it."""
    tags = fingerprint(mission)
    struck = {bench_of(t) for t, _ in ok_seq}
    ok_set = {t for t, o in ok_seq if o}
    cold = []
    for tag in tags:
        implied = _IMPLIED.get(tag)
        if not implied:
            continue
        bench, ladder = implied
        if bench in struck:
            continue
        # nothing on the ladder has succeeded (or even run)
        untried = [w for w in ladder if w not in ok_set and w in _BENCH]
        if untried:
            cold.append((bench, untried))
    if not cold:
        return ""
    lines = [f"⚠ COVERAGE ORDER (step {step}) — the mission implies benches "
             f"you have not struck:"]
    for bench, untried in cold[:3]:
        lines.append(f"- {bench.upper()} bench COLD — concrete untried weapons: "
                     + ", ".join(untried[:3]))
    lines.append("Strike at least one of them this round, or state in plain "
                 "words why that bench cannot serve the mission (a justified "
                 "cold bench is accepted; a silent one is not).")
    if ignored >= IGNORED_ESCALATION:
        lines.append("His patience thins — the operator watches idle loops. "
                     "A second silent bench means the mission folds without "
                     "honor. Strike or fold with a straight answer.")
    return "\n".join(lines)
