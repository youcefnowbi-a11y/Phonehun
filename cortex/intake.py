"""
CORTEX :: intake.py — VESPER v6 STAGE 3 — the intake classifier.

Law this module enforces (grand_mission/02_llm_orchestrator_architecture.md §4,
audit gap G1): INTAKE TRIAGE RUNS FIRST — BFU/AFU/authorized is decided
mechanically from the bird's own state bits BEFORE any front is ranked.
Arrival state is 80% of the outcome (door map §6): the verdict decides
which planes are even worth walking.

The classifier is PURE READ: dumpsys window policy / trust / biometric +
adb authorization state + storage encryption flags. It never writes a bit.

Verdict vocabulary:
  AUTHORIZED-ADB   — adb state "device" (RSA accepted): the interior plane
                    is open; if AFU too, this is the cheapest bird that exists.
  AFU             — after first unlock: CE keys have been resident since
                    last boot; extraction surfaces + biometric refresh windows
                    live; flash/rescue paths keep data in more cases.
  BFU             — before first unlock: CE keys sealed; data plane near-dead
                    on modern TEEs; silicon (artifact feed) or wait-for-AFU
                    are the honest lanes.
  (+) LOCKED / UNLOCKED — keyguard state rides along with the verdict.
  (+) INSECURE    — credential-less (swipe/none): glass door trivially open.

Output feeds: the state explorer (snapshots), the front ranker (which planes
to walk), the evidence ledger (intake event — the chain starts at arrival).
"""

import json
import re
import time


def _txt(res):
    """Pull text out of a tool result dict, whatever shape it came in."""
    if not isinstance(res, dict):
        return str(res or "")
    for k in ("stdout", "output", "text", "body", "raw"):
        v = res.get(k)
        if isinstance(v, str) and v:
            return v
        if isinstance(v, dict):
            for kk in ("stdout", "output", "text"):
                if isinstance(v.get(kk), str):
                    return v[kk]
    return json.dumps(res, ensure_ascii=False)[:4000]


def _match(patterns, text, flags=re.IGNORECASE):
    for p in patterns:
        m = re.search(p, text, flags)
        if m:
            return m.group(0)
    return None


def classify(exec_shell, list_devices_result=None, adb_state=None, serial=None):
    """The mechanical intake. exec_shell runs device shell commands (read-only).

    Returns the verdict + the state facts that produced it (evidence-first:
    the classifier never asks the cortex to trust a bare string verdict).
    """
    facts = {"serial": serial, "ts": time.time()}

    # ── fact 1: ADB authorization ─────────────────────────────────────
    if adb_state:
        facts["adb_state"] = adb_state
    elif isinstance(list_devices_result, dict):
        devs = list_devices_result.get("devices") or []
        for d in devs:
            s = (d.get("serial") or d.get("device") or "")
            if serial and serial not in s:
                continue
            facts["adb_state"] = d.get("status") or d.get("state") or "unknown"
            break
    authorized = facts.get("adb_state") == "device"

    # ── fact 2: keyguard / credential state ───────────────────────────
    kg = _txt(exec_shell("dumpsys window policy 2>/dev/null | grep -iE 'keyguard|showing|occluded|secure' | head -20"))
    facts["keyguard_raw"] = kg[:300]
    keyguard_showing = _match([r"keyguardShowing=true", r"mKeyguardShowing=true",
                               r"showing=true"], kg) is not None
    keyguard_secure = _match([r"keyguardSecure=true", r"mKeyguardSecure=true",
                              r"isSecure=true", r"secure=true"], kg) is not None
    facts["keyguard_showing"] = keyguard_showing
    facts["keyguard_secure"] = keyguard_secure

    # ── fact 3: credential type + user presence (lock_settings) ────────
    ls = _txt(exec_shell("dumpsys lock_settings 2>/dev/null | grep -iE 'credential|user|separate|lockout|attempt' | head -25"))
    facts["lock_settings_raw"] = ls[:300]
    credential_user = _match([r"separate.*challenge.*true", r"user\s+\d+.*credential"], ls) is not None

    # ── fact 4: strongAuth flags (the BFU/AFU tell) ───────────────────
    sa = _txt(exec_shell("dumpsys activity service com.android.systemui.SystemUIService 2>/dev/null | grep -iE 'strongAuth|StrongAuth' | head -10"))
    if not sa or len(sa.strip()) < 5:
        sa = _txt(exec_shell("dumpsys trust 2>/dev/null | grep -iE 'strongAuth|StrongAuth' | head -10"))
    facts["strongauth_raw"] = sa[:200]
    # 0x8 (or any non-zero) = strong auth required since boot: the classic BFU-after-reboot tell
    sa_val = _match([r"strongAuthRequired=0x[0-9a-fA-F]+"], sa)
    facts["strongauth_value"] = sa_val
    strong_auth_required = bool(sa_val and sa_val.split("=")[-1].lower() not in ("0x0", "0"))

    # ── fact 5: storage encryption class (FBE/FDE) ─────────────────────
    props = _txt(exec_shell("getprop | grep -iE 'encrypt|crypto|fileenc' | head -15"))
    facts["encryption_raw"] = props[:250]
    fbe = _match([r"fileencryption", r"ro.crypto.metadata", r"metadata_encryption"], props) is not None
    fde_legacy = _match([r"ro\.crypto\.state=encrypted"], props) and not fbe
    facts["encryption"] = "FBE" if fbe else ("FDE-legacy" if fde_legacy else "unknown")

    # ── the verdict ────────────────────────────────────────────────────
    # Positive-proof law: an INSECURE verdict (credential-less bird) requires
    # POSITIVE evidence of no credential (lock_settings saying none/success
    # with no credential), never a mere absence of "secure=true" in a dump.
    no_cred_positive = _match([r"credential[=:]?\s*(none|absent|null)",
                                r"no credential", r"user 0.*credential.*none"], ls) is not None
    if not authorized:
        # no adb at all: intake from the door map's zero-touch plane
        verdict = "UNAUTHORIZED-USB" if facts.get("adb_state") == "unauthorized" else "NO-ADB"
    elif no_cred_positive:
        verdict = "AFU-INSECURE"  # proven credential-less: glass door open
    elif not keyguard_showing:
        verdict = "AFU-UNLOCKED"  # keyguard down on an authorized device: the jackpot arrival
    elif strong_auth_required:
        verdict = "BFU"           # locked + strong-auth pending since boot
    else:
        verdict = "AFU-LOCKED"    # keyguard up but CE keys resident (unlocked once since boot)

    # ── the honest front-order the verdict implies (door map §6, W1b §4) ──
    front_order = {
        "AFU-UNLOCKED": ["interior (full sweep + evidence)", "app-level harvest", "artifact pull for offline bank"],
        "AFU-INSECURE": ["interior", "settings row writes (lockscreen may be disable-able)", "credential-set watch"],
        "AFU-LOCKED": ["interior (state surgery on keyguard bits)", "trust-feed manipulation", "binder/glass oracle", "artifact feed via root/recovery if privilege exists"],
        "BFU": ["silicon artifact feed (EDL/BROM/ISP — W2a)", "pre-boot key extraction class (CVE-2025-20435 lineage)", "wait-for-AFU portfolio (park + monitor)", "glass stale-fleet tricks (era-dependent)"],
        "UNAUTHORIZED-USB": ["pairing-authorization capture (on-device RSA accept)", "wireless-debugging pairing codes", "wait-for-operator-authorize", "zero-touch network plane (5555/mdns)"],
        "NO-ADB": ["zero-touch network sweep (hunter)", "cloud lanes (FMM class)", "glass stale-fleet tricks", "silicon (if bird powers on)"],
    }.get(verdict, ["interior recon"])

    return {"verdict": verdict, "facts": facts, "front_order": front_order,
            "authorized_adb": authorized, "keyguard": ("locked" if keyguard_showing else "unlocked"),
            "credential_secure": keyguard_secure,
            "note": "intake is mechanical: the verdict and its facts go to the evidence ledger before any front is walked"}
