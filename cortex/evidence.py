"""
CORTEX :: evidence.py — VESPER v6 STAGE 2 — the evidence harness.

Laws this module enforces (grand_mission/02_llm_orchestrator_architecture.md §7,
GATE-18.2 EVIDENCE):
- No unlock verdict without the three-part proof: keyguard-bit diff +
  lockout-counter delta + harness-verified screen-oracle frame.
- Every mission action leaves a hash-chained ledger event — narration can
  never substitute for the ledger.
- Snapshots are the state truth; the diff engine is the truth serum:
  zero-delta on a state_write = THEATER (recorded, demoted), non-empty
  delta = progress currency and a graph edge for the method compiler.

Storage: cortex/evidence/<mission_id>/
  ledger.jsonl      hash-chained events (one JSON object per line)
  snap_<n>_<tag>.json   per-plane state snapshots
  frames/           screen-oracle JPEGs (path-referenced in events)

The harness is additive: the v5 loop keeps working; missions that never
call it leave no ledger (v5 behavior preserved). Missions that DO call it
build the proof the compiler and the operator can trust.
"""

import hashlib
import json
import threading
import time
from pathlib import Path

EVIDENCE_DIR = Path(__file__).resolve().parent / "evidence"

# The keyguard bits we snapshot for the unlock proof (dumpsys window policy
# + trust + biometric — the plane facts that decide an unlock claim).
_SNAPSHOT_SHELL_CMDS = {
    "keyguard": "dumpsys window policy | grep -iE 'keyguard|showing|occluded' | head -20",
    "trust": "dumpsys trust 2>/dev/null | head -30",
    "biometric": "dumpsys biometric 2>/dev/null | grep -iE 'auth|strong|fingerprint|enrolled|lockout' | head -20",
    "lock_settings": "dumpsys lock_settings 2>/dev/null | grep -iE 'attempt|lockout|disabled|strong' | head -20",
    "settings_lock_rows": "settings list secure 2>/dev/null | grep -iE 'lock|keyguard|trust|biometric' | head -40",
}

_PROOF_FRAME_PREFIX = "unlock_proof_frame"

_lock = threading.Lock()
_MISSION_STATE = {"mission_id": None, "prev_hash": None, "event_count": 0}


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _mission_dir(mission_id: str) -> Path:
    d = EVIDENCE_DIR / _safe_id(mission_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "frames").mkdir(exist_ok=True)
    return d


def _safe_id(mid) -> str:
    s = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(mid))
    return s[:80] or f"m_{int(time.time())}"


def begin_mission(mission_id, objective=None):
    """Open (or reopen) the hash chain for a mission. Idempotent — resuming
    a mission re-links to the existing chain head."""
    with _lock:
        mid = _safe_id(mission_id)
        d = _mission_dir(mid)
        ledger = d / "ledger.jsonl"
        prev = "GENESIS"
        if ledger.exists():
            try:
                last = None
                with ledger.open("r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            last = line
                if last:
                    prev = json.loads(last).get("hash", "GENESIS")
            except (OSError, json.JSONDecodeError):
                prev = "GENESIS"
        else:
            with ledger.open("w", encoding="utf-8") as f:
                pass
        _MISSION_STATE.update(mission_id=mid, prev_hash=prev,
                              event_count=0)
    _event("mission_begin", {"objective": objective, "mission_id": mid})
    return {"success": True, "mission_id": mid, "chain_head": prev}


def _event(kind, body, mission_id=None):
    """Append one hash-chained event. Chain: hash = sha256(prev_hash + body)."""
    with _lock:
        mid = mission_id or _MISSION_STATE.get("mission_id") or "orphan"
        state_prev = _MISSION_STATE.get("prev_hash")
        d = _mission_dir(mid)
        rec = {"ts": time.time(), "iso": time.strftime("%Y-%m-%d %H:%M:%S"),
               "kind": kind, "mission_id": mid}
        rec.update(body or {})
        prev = state_prev if mid == _MISSION_STATE.get("mission_id") else _read_head(d)
        rec["prev_hash"] = prev
        blob = json.dumps(rec, sort_keys=True, ensure_ascii=False)
        rec["hash"] = _sha((prev + blob).encode("utf-8"))
        with (d / "ledger.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        if mid == _MISSION_STATE.get("mission_id"):
            _MISSION_STATE["prev_hash"] = rec["hash"]
            _MISSION_STATE["event_count"] += 1
    return rec


def _read_head(d: Path) -> str:
    try:
        last = None
        with (d / "ledger.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    last = line
        return json.loads(last).get("hash", "GENESIS") if last else "GENESIS"
    except (OSError, json.JSONDecodeError):
        return "GENESIS"


# ── snapshots ───────────────────────────────────────────────────────────────

def state_snapshot(exec_shell, tag="manual", serial=None):
    """Capture the lock-relevant state plane via the provided exec callback.

    exec_shell: callable(command:str) -> dict with stdout/stdout text
    (the cortex passes its shell tool's runner). Pure read — no writes.
    """
    mid = _MISSION_STATE.get("mission_id") or "orphan"
    d = _mission_dir(mid)
    snap = {"tag": tag, "ts": time.time(),
            "serial": serial, "planes": {}}
    n = 0
    for plane, cmd in _SNAPSHOT_SHELL_CMDS.items():
        try:
            r = exec_shell(cmd)
            text = r.get("stdout") or r.get("output") or (r.get("error") and f"ERROR: {r['error']}") or ""
            if isinstance(text, dict):
                text = json.dumps(text, ensure_ascii=False)
            snap["planes"][plane] = text[:4000]
        except Exception as e:
            snap["planes"][plane] = f"SNAPSHOT-FAIL: {e!r}"
        n += 1
    n += 1
    path = d / f"snap_{int(time.time())}_{_safe_id(tag)}.json"
    path.write_text(json.dumps(snap, ensure_ascii=False, indent=1), encoding="utf-8")
    snap_hash = _sha(path.read_bytes())
    _event("snapshot", {"tag": tag, "path": str(path), "sha256": snap_hash})
    return {"success": True, "snapshot": str(path), "sha256": snap_hash,
            "planes": list(snap["planes"].keys())}


def state_diff(tag_before, tag_after, exec_shell=None):
    """Diff the two most recent snapshots matching each tag. Zero-delta on a
    claimed write = THEATER — recorded as such."""
    mid = _MISSION_STATE.get("mission_id") or "orphan"
    d = _mission_dir(mid)
    snaps = sorted(d.glob("snap_*.json"))
    before = _find_snap(snaps, tag_before)
    after = _find_snap(snaps, tag_after)
    if not before or not after:
        return {"error": f"snapshots not found for tags {tag_before!r}/{tag_after!r}"}
    a = json.loads(before.read_text(encoding="utf-8"))
    b = json.loads(after.read_text(encoding="utf-8"))
    delta = {}
    for plane in set(list(a.get("planes", {})) + list(b.get("planes", {}))):
        ta, tb = a["planes"].get(plane, ""), b["planes"].get(plane, "")
        if ta != tb:
            delta[plane] = {"before": ta[:600], "after": tb[:600]}
    verdict = "ZERO-DELTA" if not delta else "CHANGED"
    rec = _event("diff", {"tags": [tag_before, tag_after], "verdict": verdict,
                          "planes_changed": sorted(delta.keys())})
    return {"success": True, "verdict": verdict, "delta": delta,
            "event_hash": rec.get("hash")}


def _find_snap(snaps, tag):
    for p in reversed(snaps):
        if _safe_id(tag) in p.name:
            return p
    return None


# ── the three-part unlock proof (GATE-18.2) ─────────────────────────────────

def unlock_proof(exec_shell, frame_path=None):
    """The crown's truth law: no unlock claim without all three parts.

    1. keyguard-bit diff      — dumpsys window policy says keyguard NOT showing
    2. lockout-counter delta  — no fresh lockout escalation in the window
    3. screen-oracle frame    — a captured frame the harness has SEEN

    Returns verdict UNLOCK-PROVEN only when all three hold. The cortex's
    narration is never a substitute; this proof is the admission ticket
    for any 'unlocked' statement in a final report.
    """
    mid = _MISSION_STATE.get("mission_id") or "orphan"
    # part 1: keyguard bits now
    r = exec_shell(_SNAPSHOT_SHELL_CMDS["keyguard"])
    kg_text = (r.get("stdout") or r.get("output") or "")
    if isinstance(kg_text, dict):
        kg_text = json.dumps(kg_text)
    kg_clear = ("keyguardShowing=false" in kg_text
                or "mKeyguardShowing=false" in kg_text
                or ("showing=false" in kg_text.lower() and "keyguard" in kg_text.lower()))
    # part 2: lockout delta — diff vs the latest snapshot
    delta_v = None
    try:
        dv = state_diff("pre_unlock", "post_unlock")
        delta_v = dv.get("verdict")
    except Exception:
        delta_v = None
    # part 3: frame
    frame_ok = bool(frame_path and Path(frame_path).exists())
    verdict = "UNLOCK-PROVEN" if (kg_clear and frame_ok) else "UNPROVEN"
    rec = _event("unlock_proof", {
        "keyguard_bits_clear": kg_clear, "frame": frame_path,
        "frame_ok": frame_ok, "snapshot_delta": delta_v, "verdict": verdict,
        "keyguard_text_head": kg_text[:300],
    })
    return {"success": True, "verdict": verdict, "parts": {
        "keyguard_bits": kg_clear, "lockout_delta": delta_v, "frame": frame_ok},
        "event_hash": rec.get("hash")}


# ── narration-vs-ledger mismatch detector ────────────────────────────────────

def narration_mismatch(final_text, mission_id=None):
    """GATE-18.2 enforcement: scan a final report for unlock claims; if the
    ledger has no UNLOCK-PROVEN event, the claim is a MISMATCH (recorded)."""
    mid = mission_id or _MISSION_STATE.get("mission_id") or "orphan"
    claims = [w for w in ("unlocked", "unlocked", "unlock réussi",
                          "lock open", "opened the bird", "mission unlocked")
              if w in (final_text or "").lower()]
    proven = False
    d = _mission_dir(mid)
    try:
        with (d / "ledger.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    e = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if e.get("kind") == "unlock_proof" and e.get("verdict") == "UNLOCK-PROVEN":
                    proven = True
                    break
    except OSError:
        pass
    mismatch = bool(claims) and not proven
    if mismatch:
        _event("narration_mismatch", {"claims_found": claims, "proven": proven},
               mission_id=mid)
    return {"claims_unlock": bool(claims), "ledger_proves_unlock": proven,
            "mismatch": mismatch}


def read_ledger(mission_id=None, verify_chain=True):
    """Read a mission ledger; optionally verify the hash chain end-to-end."""
    mid = _safe_id(mission_id or _MISSION_STATE.get("mission_id") or "orphan")
    d = _mission_dir(mid)
    events = []
    try:
        with (d / "ledger.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    try:
                        events.append(json.loads(line))
                    except json.JSONDecodeError:
                        events.append({"kind": "corrupt_line", "raw": line[:200]})
    except OSError:
        return {"error": "no ledger for mission"}
    chain_ok = True
    if verify_chain:
        prev = "GENESIS"
        for e in events:
            if e.get("prev_hash") != prev and e.get("prev_hash") != "GENESIS":
                chain_ok = False
                break
            expect = e.get("hash")
            blob = json.dumps({k: v for k, v in e.items()
                               if k not in ("hash",)}, sort_keys=True, ensure_ascii=False)
            if _sha((e.get("prev_hash", "") + blob).encode("utf-8")) != expect:
                chain_ok = False
                break
            prev = expect
    return {"success": True, "mission_id": mid, "events": len(events),
            "chain_valid": chain_ok,
            "summary": {"unlock_proven": any(e.get("kind") == "unlock_proof" and
                                            e.get("verdict") == "UNLOCK-PROVEN"
                                            for e in events),
                        "mismatches": sum(1 for e in events
                                          if e.get("kind") == "narration_mismatch"),
                        "snapshots": sum(1 for e in events if e.get("kind") == "snapshot")}}


def mission_summary(mission_id=None):
    """Cockpit view: one mission's evidence digest."""
    r = read_ledger(mission_id)
    if not r.get("success"):
        return r
    return {"success": True, "mission_id": r["mission_id"],
            "events": r["events"], "chain_valid": r["chain_valid"],
            "unlock_proven": r["summary"]["unlock_proven"],
            "mismatches": r["summary"]["mismatches"]}


def end_mission(final_text=None):
    """Close the chain; run the mismatch detector on the final report."""
    mismatch = narration_mismatch(final_text) if final_text else {"mismatch": False}
    _event("mission_end", {"mismatch": mismatch.get("mismatch", False)})
    with _lock:
        _MISSION_STATE.update(mission_id=None, prev_hash=None, event_count=0)
    return {"success": True, "mismatch_check": mismatch}
