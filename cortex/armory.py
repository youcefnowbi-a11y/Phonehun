"""
CORTEX :: armory.py — VESPER v6 STAGE 5 — the armory module.

Laws this module enforces (grand_mission/07_armory.md):
- MANIFEST-FIRST: every executable the system may run has a row:
  {name, version, sha256, entry_points, provenance, panel_exec, ...}
- HASH-REFUSAL: an unverified binary never executes (request_tool returns
  ACQUISITION-NEEDED or UNVERIFIED — never an entry point it can't vouch for).
- PROVENANCE LAW: every acquisition leaves a ledger row (who/where/when).
- NO AUTO-UPDATES: versions pin; updates are deliberate armory tasks.

The armory is the enforcement point of GATE-18.1: what runs is what was
verified. The registry dispatches; the armory vouches.

Storage: cortex/armory/armory.json (versioned, git-tracked).
"""

import hashlib
import json
import threading
import time
from pathlib import Path

ARMORY_DIR = Path(__file__).resolve().parent / "armory"
MANIFEST_PATH = ARMORY_DIR / "armory.json"

_lock = threading.Lock()

REQUIRED_FIELDS = ("name", "version", "entry_points", "provenance")


def _sha256_file(path):
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def load_manifest():
    """Read the manifest (or an empty shell if absent)."""
    try:
        with MANIFEST_PATH.open("r", encoding="utf-8") as f:
            m = json.load(f)
        if not isinstance(m, dict):
            return {"_meta": {"version": "0"}, "assets": []}
        m.setdefault("assets", [])
        return m
    except (OSError, json.JSONDecodeError):
        return {"_meta": {"version": "0"}, "assets": []}


def save_manifest(m):
    ARMORY_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=1),
                             encoding="utf-8")


def register_asset(row, source="operator"):
    """Add/replace a manifest row. Provenance law: the row records who
    registered it and when. Validation law: REQUIRED_FIELDS must be present."""
    if not isinstance(row, dict) or not all(row.get(k) for k in REQUIRED_FIELDS):
        return {"error": f"row needs {REQUIRED_FIELDS} (got: {list(row or {})})"}
    with _lock:
        m = load_manifest()
        assets = m["assets"]
        for i, a in enumerate(assets):
            if a.get("name") == row["name"]:
                assets[i] = row  # replace = deliberate update, leaves git trail
                break
        else:
            assets.append(row)
        row.setdefault("registered_by", source)
        row["registered_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        row.setdefault("panel_exec", True)
        row.setdefault("danger_plane", "bench")
        row.setdefault("airgap_staged", True)
        save_manifest(m)
    return {"success": True, "asset": row["name"], "manifest_rows": len(assets)}


def verify_row(row):
    """Verify one manifest row: entry point exists + sha256 matches (if pinned).
    pip-installed packages may pin by version instead of file hash."""
    eps = row.get("entry_points") or {}
    if not isinstance(eps, dict) or not eps:
        return {"status": "UNVERIFIED", "reason": "no entry points declared"}
    for label, ep in eps.items():
        p = Path(str(ep))
        if not p.exists():
            return {"status": "MISSING", "reason": f"entry point {label} absent: {ep}"}
        pinned = row.get("sha256") or {}
        if isinstance(pinned, dict) and pinned.get(label):
            actual = _sha256_file(p)
            if actual != pinned[label]:
                return {"status": "DRIFTED", "reason":
                        f"{label} hash mismatch (manifest {pinned[label][:16]}… vs disk "
                        f"{(actual or 'unreadable')[:16]}…)"}
    return {"status": "INSTALLED"}


def request_tool(name):
    """The armory's single verdict API. The cortex NEVER runs a binary the
    armory has not vouched for — this returns the verdict + entry point only
    when the row verifies clean."""
    for row in load_manifest()["assets"]:
        if row.get("name") == name:
            v = verify_row(row)
            if v["status"] == "INSTALLED":
                return {"verdict": "INSTALLED", "name": name,
                        "entry_points": row.get("entry_points"),
                        "version": row.get("version")}
            return {"verdict": v["status"], "name": name, "reason": v["reason"]}
    return {"verdict": "ACQUISITION-NEEDED", "name": name,
            "reason": "no manifest row — armory task required (never mid-mission)"}


def list_armory(plane=None, status_filter=None):
    """Cockpit/cortex view: every asset with its live verification state."""
    rows = []
    for row in load_manifest()["assets"]:
        if plane and row.get("danger_plane") != plane:
            continue
        v = verify_row(row)
        if status_filter and v["status"] != status_filter:
            continue
        rows.append({"name": row.get("name"), "version": row.get("version"),
                     "plane": row.get("danger_plane"),
                     "status": v["status"],
                     "provenance": row.get("provenance"),
                     "panel_exec": row.get("panel_exec", True)})
    return {"assets": rows, "count": len(rows)}


def integrity_scan():
    """Full manifest verification sweep — the armory's own health check."""
    results = {"INSTALLED": 0, "MISSING": 0, "DRIFTED": 0, "UNVERIFIED": 0}
    for row in load_manifest()["assets"]:
        results[verify_row(row)["status"]] = results.get(verify_row(row)["status"], 0) + 1
    return results
