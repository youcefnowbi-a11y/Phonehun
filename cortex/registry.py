"""
CORTEX :: registry.py — VESPER v6 STAGE 1 — the dispatch indirection.

Laws this module enforces (grand_mission/02_llm_orchestrator_architecture.md §3, §8):
- DANGER CLASSES gate every dispatch: read_only runs free; state_write runs
  narrated; destructive/flash require OPERATOR SIGN-OFF before the call fires.
- The shell escalation law: command text escalates the shell tool's class
  (rm -rf / dd / flash utilities / wipe verbs = destructive regardless of row).
- Sign-offs are one-shot, held for a named tool+args-hash, and expire at
  mission end. Crown and scope-guard laws live above this module (persona,
  doctrine) — this is the mechanical gate beneath them.

Stage 1 scope: gate + sign-off API. The snapshot/diff engine (Stage 2) and
registry-driven schema generation (Stage 3) wrap this module, never replace it.
"""

import hashlib
import json
import re
import threading
import time
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent / "registry" / "tools.json"
SIGNOFF_TTL_S = 3600          # one hour unless consumed
MISSION_SIGNOFFS = {}        # {signoff_id: {"tool": str, "arg_hash": str, "ts": float}}
_SIGNOFF_LOCK = threading.Lock()

_REGISTRY_CACHE = None
_REGISTRY_TS = None


def load_registry(force=False):
    """Load and cache tools.json; reload on file mtime change."""
    global _REGISTRY_CACHE, _REGISTRY_TS
    try:
        mtime = REGISTRY_PATH.stat().st_mtime
    except OSError:
        return {"_meta": {}, "tools": []}
    if not force and _REGISTRY_CACHE is not None and _REGISTRY_TS == mtime:
        return _REGISTRY_CACHE
    try:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            reg = json.load(f)
        _REGISTRY_CACHE, _REGISTRY_TS = reg, mtime
        return reg
    except (OSError, json.JSONDecodeError):
        return {"_meta": {}, "tools": []}


def tool_row(name):
    """Return the registry row for a tool name (or a minimal safe default).

    Default policy: unknown tools get state_write class — narrated, no sign-off.
    Belt tools absent from the registry (should not happen after Stage 0) fall
    here rather than open the gate silently.
    """
    for t in load_registry().get("tools", []):
        if t.get("name") == name:
            return t
    return {"name": name, "plane": "interior", "danger_class": "state_write",
            "interface": "api", "preconditions": [], "verification": None,
            "rollback": None, "_unregistered": True}


# ── shell escalation law ─────────────────────────────────────────────────────
# The shell tool (and any tool whose args carry free-form command text) escalates
# BY CONTENT: destructive command text escalates the call to the destructive gate.

_DESTRUCTIVE_PATTERNS = [
    r"\brm\s+(-[a-z]*r[a-z]*f?|-[a-z]*f[a-z]*r?)\b",   # rm -rf family
    r"\bmkfs\b", r"\bdd\s+if=", r"\bflash_(all|partition)\b",
    r"\bfactory\s*reset\b", r"\bwipe\b(?!.*data-sacred)", r"\bformat\b\s+(?:/|data)",
    r"\bfastboot\s+(?:erase|oem\s+unlock|flashing\s+unlock)\b",
    r"\breboot\s+(?:recovery|edl|download|bootloader)\b",
    r"\bda\s+seccfg\b", r"\bes\s+frp\b", r"\b--wipe\b",
    r"\bsvc\s+.*(wipe|factory)", r"\bmpcli\b.*(?:erase|format)",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _DESTRUCTIVE_PATTERNS]


def escalated_class(tool_name, args):
    """Compute the EFFECTIVE danger class for this call, post shell-escalation."""
    row = tool_row(tool_name)
    cls = row.get("danger_class", "state_write")
    if tool_name in ("shell", "host_shell") or row.get("_unregistered"):
        text = " ".join(str(v) for v in (args or {}).values()) if isinstance(args, dict) else str(args)
        if any(p.search(text or "") for p in _COMPILED):
            return "destructive", row
    return cls, row


# ── operator sign-off ────────────────────────────────────────────────────────

def _arg_hash(tool_name, args):
    blob = json.dumps({"t": tool_name, "a": args or {}}, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def request_signoff(tool_name, args):
    """Create a pending sign-off for tool+args; returns the id the operator approves."""
    with _SIGNOFF_LOCK:
        # collapse duplicates: same tool+args pending -> same id
        ah = _arg_hash(tool_name, args)
        for sid, e in MISSION_SIGNOFFS.items():
            if e["tool"] == tool_name and e["arg_hash"] == ah and not e.get("consumed"):
                return sid, "pending"
        sid = "so_" + hashlib.sha256(f"{tool_name}{ah}{time.time()}".encode()).hexdigest()[:12]
        MISSION_SIGNOFFS[sid] = {"tool": tool_name, "arg_hash": ah, "ts": time.time(),
                                 "consumed": False, "approved": False}
        return sid, "created"


def approve_signoff(sid):
    """Operator approves a pending sign-off (one-click in the cockpit).

    Approving does NOT consume the token — consumption happens at dispatch
    time (consume_signoff), so the approved call fires exactly once and a
    replay needs a fresh sign-off.
    """
    with _SIGNOFF_LOCK:
        e = MISSION_SIGNOFFS.get(sid)
        if not e or e.get("consumed"):
            return False, "no such pending sign-off"
        e["approved"] = True
        return True, "approved"


def decline_signoff(sid):
    """Operator declines — the gated call must never fire."""
    with _SIGNOFF_LOCK:
        e = MISSION_SIGNOFFS.get(sid)
        if not e:
            return False, "no such sign-off"
        e["consumed"] = True
        e["approved"] = False
        return True, "declined"


def consume_signoff(tool_name, args):
    """At dispatch time: is there an APPROVED, unconsumed sign-off for this call?"""
    with _SIGNOFF_LOCK:
        now = time.time()
        ah = _arg_hash(tool_name, args)
        dead = [k for k, v in MISSION_SIGNOFFS.items() if now - v["ts"] > SIGNOFF_TTL_S]
        for k in dead:
            del MISSION_SIGNOFFS[k]
        for e in MISSION_SIGNOFFS.values():
            if (e["tool"] == tool_name and e["arg_hash"] == ah
                    and e.get("approved") and not e.get("consumed")):
                e["consumed"] = True
                return True
        return False


def pending_signoffs():
    """Cockpit view: all pending sign-offs awaiting operator action."""
    with _SIGNOFF_LOCK:
        now = time.time()
        return [{"id": sid, "tool": e["tool"], "age_s": int(now - e["ts"]),
                 "approved": e.get("approved", False), "consumed": e.get("consumed", False)}
                for sid, e in MISSION_SIGNOFFS.items()
                if not e.get("consumed") and now - e["ts"] <= SIGNOFF_TTL_S]


def clear_signoffs():
    """Mission end: all unconsumed sign-offs die."""
    with _SIGNOFF_LOCK:
        MISSION_SIGNOFFS.clear()


# ── the gate — single dispatch chokepoint ────────────────────────────────────

def gate(tool_name, args):
    """The pre-dispatch gate. Returns (verdict_dict, effective_class, row).

    verdicts:
      {"ok": True}                      — dispatch proceeds
      {"ok": False, "reason": ...}      — dispatch blocked (with sign-off id if gated)
    """
    cls, row = escalated_class(tool_name, args)
    if cls in ("read_only", "state_write"):
        return {"ok": True}, cls, row
    # destructive / flash: need an approved, unconsumed sign-off
    if consume_signoff(tool_name, args):
        return {"ok": True, "signoff_used": True}, cls, row
    sid, _ = request_signoff(tool_name, args)
    return {"ok": False, "reason": f"OPERATOR SIGN-OFF REQUIRED ({cls})",
            "signoff_id": sid, "danger_class": cls, "tool": tool_name}, cls, row
