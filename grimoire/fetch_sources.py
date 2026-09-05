#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIMOIRE FETCHER
Replaces authored-from-memory knowledge with live, field-tested material.

Fetches (all public, legitimate sources):
  1. CISA KEV feed          - what is ACTUALLY exploited in the wild, full & live
  2. MITRE ATT&CK STIX      - the real technique spine: names, descriptions,
                              x_mitre_detection text, tactics, deprecation status
  3. Atomic Red Team YAMLs  - real TESTED simulation tests (command / executor /
                              cleanup) per technique, maintained by Red Canary
                              for detection validation in YOUR lab
  4. CAPEC full CSV         - verifies every CAPEC id the library references

Cross-verifies the library:
  - every MITRE id in techniques/*.json  -> exists in live ATT&CK? revoked? deprecated?
  - every CAPEC id in techniques/*.json  -> exists in live CAPEC?

Writes normalized output to fetched/*.json with complete provenance.
Standard library + PyYAML (for ART). Run: python fetch_sources.py
"""

import csv
import datetime
import hashlib
import io
import json
import sys
import urllib.request
import zipfile
from pathlib import Path

import yaml  # pyyaml 6.x

ROOT = Path(__file__).resolve().parent
FETCHED = ROOT / "fetched"
FETCHED.mkdir(exist_ok=True)

UA = {"User-Agent": "grimoire-fetcher/1.0 (authorized-lab training corpus)"}
provenance = {"fetched_at": datetime.datetime.now().isoformat(timespec="seconds"),
              "sources": [], "notes": []}


def fetch(url, timeout=60):
    """GET bytes with UA + timeout. Raises on failure."""
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def record_source(name, url, data=None, method="https"):
    entry = {"name": name, "url": url, "method": method,
             "sha256": hashlib.sha256(data).hexdigest()[:16] if data else None,
             "bytes": len(data) if data else None}
    provenance["sources"].append(entry)
    print(f"  [ok] {name}: {entry['bytes'] if entry['bytes'] is not None else '?'} bytes "
          f"sha256:{entry['sha256']}")


def safe_json(path, obj):
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"  [write] {path.name} ({path.stat().st_size / 1024:.1f} KiB)")


# --------------------------------------------------------------------------
# Load library MITRE / CAPEC references
# --------------------------------------------------------------------------
def library_refs():
    tids, capecs = set(), set()
    for p in sorted((ROOT / "techniques").glob("*.json")):
        for rec in json.loads(p.read_text(encoding="utf-8")).get("techniques", []):
            tids.update(rec.get("mitre", []))
            capecs.update(rec.get("capec", []))
    return sorted(tids), sorted(capecs)


# --------------------------------------------------------------------------
# 1. CISA KEV (live)
# --------------------------------------------------------------------------
def fetch_kev():
    url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    print("[1/4] CISA KEV live feed...")
    data = fetch(url)
    record_source("CISA KEV", url, data)
    feed = json.loads(data.decode("utf-8", errors="replace"))
    vulns = feed.get("vulnerabilities", [])
    safe_json(FETCHED / "kev_live.json", {
        "_provenance": {"fetched_at": provenance["fetched_at"], "url": url,
                        "catalog_version": feed.get("catalogVersion"),
                        "date_released": feed.get("dateReleased"),
                        "count": len(vulns), "verified": True},
        "vulnerabilities": vulns,
    })
    rw = sum(1 for v in vulns if v.get("knownRansomwareCampaignUse") == "Known")
    print(f"        {len(vulns)} known-exploited CVEs, {rw} flagged in ransomware campaigns")
    return feed


# --------------------------------------------------------------------------
# 2. MITRE ATT&CK STIX (release asset, with fallbacks)
# --------------------------------------------------------------------------
def fetch_attack(tids):
    url = "https://github.com/mitre-attack/attack-stix-data/releases/latest/download/enterprise-attack.json"
    print("[2/4] MITRE ATT&CK STIX (enterprise)...")
    raw, method = None, None
    for candidate, m in [
        (url, "stix-release"),
        ("https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json", "cti-raw"),
    ]:
        try:
            raw = fetch(candidate, timeout=180)
            method = m
            print(f"        downloading via {m}... {len(raw) / 1048576:.1f} MiB")
            break
        except Exception as exc:  # noqa: BLE001
            provenance["notes"].append(f"ATT&CK source failed: {candidate} ({exc.__class__.__name__})")
            print(f"        [skip] {m} failed: {exc.__class__.__name__}")
    if raw is None:
        return None

    record_source("MITRE ATT&CK STIX", candidate, data=raw, method=method)
    bundle = json.loads(raw.decode("utf-8", errors="replace"))
    objects = bundle.get("objects", [])

    techniques = {}
    for o in objects:
        if o.get("type") != "attack-pattern":
            continue
        ext = [r.get("external_id") for r in o.get("external_references", [])
               if r.get("source_name") == "mitre-attack" and r.get("external_id")]
        if not ext:
            continue
        tid = ext[0]
        tactics = [kc.get("phase_name") for kc in o.get("kill_chain_phases", [])
                   if kc.get("kill_chain_name") == "mitre-attack"]
        techniques[tid] = {
            "id": tid,
            "name": o.get("name"),
            "tactics": tactics,
            "description": (o.get("description") or "")[:700],
            "detection": (o.get("x_mitre_detection") or "")[:700],
            "permissions_required": o.get("x_mitre_permissions_required", []),
            "platforms": o.get("x_mitre_platforms", []),
            "revoked": bool(o.get("revoked")),
            "deprecated": bool(o.get("x_mitre_deprecated")),
            "url": f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}/",
        }
    tactics_all = sorted({t for v in techniques.values() for t in v["tactics"]})

    status = {}
    for tid in tids:
        t = techniques.get(tid)
        if not t:
            status[tid] = "MISSING"
        elif t["revoked"]:
            status[tid] = "REVOKED"
        elif t["deprecated"]:
            status[tid] = "DEPRECATED"
        else:
            status[tid] = "verified"
    out = {
        "_provenance": {"fetched_at": provenance["fetched_at"], "method": method,
                        "object_count": len(techniques), "verified": True},
        "tactics": tactics_all,
        "techniques": techniques,
        "library_mitre_status": status,
    }
    safe_json(FETCHED / "attack_reference.json", out)
    ok = sum(1 for v in status.values() if v == "verified")
    print(f"        {len(techniques)} techniques parsed; library refs verified: {ok}/{len(tids)}")
    for tid, st in status.items():
        if st != "verified":
            print(f"        [!] {tid}: {st}")
    return out


# --------------------------------------------------------------------------
# 3. Atomic Red Team tests (real tested simulations)
# --------------------------------------------------------------------------
def fetch_atomic(tids):
    print("[3/4] Atomic Red Team simulation tests...")
    tests, missing = [], []
    for tid in tids:
        url = f"https://raw.githubusercontent.com/redcanaryco/atomic-red-team/master/atomics/{tid}/{tid}.yaml"
        try:
            raw = fetch(url, timeout=30)
        except Exception:  # noqa: BLE001 - no ART coverage for this technique
            missing.append(tid)
            continue
        try:
            doc = yaml.safe_load(raw.decode("utf-8", errors="replace"))
        except yaml.YAMLError as exc:
            missing.append(tid)
            provenance["notes"].append(f"ART yaml parse failed for {tid}: {exc}")
            continue
        if not doc or doc.get("attack_technique") is False:
            missing.append(tid)
            continue
        display = doc.get("display_name", "")
        for t in doc.get("atomic_tests", []):
            ex = t.get("executor") or {}
            tests.append({
                "technique": tid,
                "test_name": t.get("name"),
                "description": (t.get("description") or "")[:400],
                "supported_platforms": t.get("supported_platforms", []),
                "executor": ex.get("name"),
                "command": (ex.get("command") or "")[:600],
                "cleanup": (ex.get("cleanup_command") or "")[:300],
                "elevation_required": bool(t.get("elevation_required")),
                "input_arguments": sorted((t.get("input_arguments") or {}).keys()),
                "url": f"https://github.com/redcanaryco/atomic-red-team/blob/master/atomics/{tid}/{tid}.yaml",
            })
        record_source(f"ART {tid}", url, raw)
    out = {
        "_provenance": {"fetched_at": provenance["fetched_at"],
                        "repo": "https://github.com/redcanaryco/atomic-red-team",
                        "techniques_with_tests": sorted({t["technique"] for t in tests}),
                        "techniques_without_ART_coverage": missing,
                        "verified": True},
        "test_count": len(tests),
        "tests": tests,
    }
    safe_json(FETCHED / "atomic_tests.json", out)
    print(f"        {len(tests)} real tested simulations across "
          f"{len(out['_provenance']['techniques_with_tests'])} techniques")
    return out


# --------------------------------------------------------------------------
# 4. CAPEC CSV (verification of library CAPEC ids)
# --------------------------------------------------------------------------
def fetch_capec(capecs):
    print("[4/4] CAPEC full catalog (verification)...")
    url = "https://capec.mitre.org/data/csv/2000.csv.zip"
    try:
        raw = fetch(url, timeout=60)
        record_source("CAPEC CSV", url, raw)
        zf = zipfile.ZipFile(io.BytesIO(raw))
        member = next(n for n in zf.namelist() if n.lower().endswith(".csv"))
        # MITRE's CSV export carries a stray Excel-style apostrophe before the
        # header ('ID,Name,...) - strip it or every fieldname lookup misses.
        text = zf.read(member).decode("utf-8-sig", errors="replace").lstrip("'")
        known = {}
        for row in csv.DictReader(io.StringIO(text)):
            cid = (row.get("ID") or "").strip().lstrip("'")
            if cid:
                known[f"CAPEC-{cid}"] = (row.get("Name") or "").strip().lstrip("'")
        status = {c: ("verified:" + known[c] if c in known and known[c]
                      else ("verified" if c in known else "UNKNOWN")) for c in capecs}
        out = {
            "_provenance": {"fetched_at": provenance["fetched_at"], "url": url,
                            "catalog_size": len(known), "verified": True},
            "library_capec_status": status,
        }
        safe_json(FETCHED / "capec_verification.json", out)
        ok = sum(1 for v in status.values() if v.startswith("verified"))
        print(f"        library CAPEC refs verified: {ok}/{len(capecs)}")
        for c, st in status.items():
            if st == "UNKNOWN":
                print(f"        [!] {c}: not in live CAPEC - library record needs fixing")
        return out
    except Exception as exc:  # noqa: BLE001
        provenance["notes"].append(f"CAPEC fetch failed: {exc.__class__.__name__}: {exc}")
        print(f"        [skip] CAPEC verification unavailable: {exc}")
        return None


# --------------------------------------------------------------------------
def main():
    print("== GRIMOIRE FETCHER ==")
    tids, capecs = library_refs()
    print(f"  library references: {len(tids)} MITRE ids, {len(capecs)} CAPEC ids")

    if "--capec-only" in sys.argv:
        # merge into the existing provenance record instead of clobbering it
        prev_path = FETCHED / "provenance.json"
        if prev_path.exists():
            try:
                prev = json.loads(prev_path.read_text(encoding="utf-8"))
                prev_sources = {s["name"]: s for s in prev.get("sources", [])}
                for s in provenance["sources"]:
                    prev_sources[s["name"]] = s
                provenance["sources"] = list(prev_sources.values())
                provenance["notes"] = prev.get("notes", [])
            except (json.JSONDecodeError, OSError, KeyError):
                pass
        capec = fetch_capec(capecs)
        provenance["summary"] = {"capec_verification": "done" if capec else "failed"}
        safe_json(FETCHED / "provenance.json", provenance)
        print("VERDICT: " + ("CAPEC verified" if capec else "CAPEC still unreachable"))
        return 0

    fetch_kev()
    attack = fetch_attack(tids)
    atomic = fetch_atomic(tids)
    capec = fetch_capec(capecs)

    provenance["summary"] = {
        "kev": "live",
        "attack": "live" if attack else "failed",
        "atomic_tests": len(atomic["tests"]) if atomic else 0,
        "capec_verification": "done" if capec else "failed",
    }
    safe_json(FETCHED / "provenance.json", provenance)

    # quick verification verdict for the library
    if attack:
        bad = {k: v for k, v in attack["library_mitre_status"].items() if v != "verified"}
        print(f"\nVERDICT: MITRE mappings {'ALL VERIFIED' if not bad else f'{len(bad)} issue(s)'}")
    if capec:
        unknown = [c for c, st in capec["library_capec_status"].items() if st == "UNKNOWN"]
        print(f"VERDICT: CAPEC mappings {'ALL VERIFIED' if not unknown else f'{len(unknown)} unknown -> fix records'}")
    print("rebuild the pack with:  python loader.py --pack --demo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
