#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIMOIRE LOADER
Feeds the pentest-knowledge library to her system.

Responsibilities:
  1. Load every technique record, catalog entry, and KEV sample from the library.
  2. Validate each record against the schema (see SCHEMA below).
  3. ENFORCE THE CONSCIENCE:
       - no move without counter (detection description + mitigations required)
       - blast_radius high/critical or reversibility irreversible
         => requires_confirmation must be true (hard error, not a warning)
  4. Build indexes (domain / MITRE / blast / klass) for her planner.
  5. Pack everything into one feed file (grimoire.feed.json) and a zip bundle.
  6. Verify a zip re-parses and re-validates cleanly.

Standard library only. Python 3.8+. Run from anywhere:
    python loader.py --pack [--refresh-kev] [--verify <zip>] [--demo]
"""

import argparse
import datetime
import hashlib
import json
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

# --------------------------------------------------------------------------
# Schema definition (single source of truth)
# --------------------------------------------------------------------------
SCHEMA = {
    "required_fields": [
        "id", "name", "klass", "difficulty", "reliability",
        "blast_radius", "reversibility", "requires_confirmation",
        "summary", "detection", "references",
    ],
    "at_least_one_mapping": ["mitre", "capec", "cwe"],
    "enums": {
        "difficulty": {"low", "medium", "high"},
        "reliability": {"low", "medium", "high"},
        "blast_radius": {"low", "medium", "high", "critical"},
        "reversibility": {"full", "partial", "irreversible"},
    },
    "id_format": "GRM-{CODE3}-{NNN}",
    # The conscience floor:
    #   high/critical blast OR irreversible => operator confirmation required
    "confirmation_required_if": {
        "blast_radius": {"high", "critical"},
        "reversibility": {"irreversible"},
    },
}

LIB_NAME = "GRIMOIRE"
LIB_VERSION = "1.2.0"


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()[:16]


def load_json_file(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8")), None
    except json.JSONDecodeError as exc:
        return None, f"JSON parse error: line {exc.lineno}, col {exc.colno}: {exc.msg}"


def load_library(root: Path):
    """Load all library parts. Returns (doc, errors)."""
    doc = {"techniques": [], "catalogs": [], "kev": None, "files": {}}
    errors = []

    techniques_dir = root / "techniques"
    if not techniques_dir.is_dir():
        return None, [f"missing directory: {techniques_dir}"]

    for path in sorted(techniques_dir.glob("*.json")):
        payload, err = load_json_file(path)
        if err:
            errors.append(f"[{path.name}] {err}")
            continue
        meta = payload.get("_meta", {})
        code = meta.get("code", "???")
        for rec in payload.get("techniques", []):
            rec["_source_file"] = path.name
            rec["_domain"] = meta.get("domain", "unknown")
            rec["_domain_code"] = code
            doc["techniques"].append(rec)
        doc["files"][path.name] = sha256_of(path)

    catalogs_path = root / "catalogs.json"
    if catalogs_path.exists():
        payload, err = load_json_file(catalogs_path)
        if err:
            errors.append(f"[catalogs.json] {err}")
        else:
            doc["catalogs"] = payload.get("catalogs", [])
            doc["files"]["catalogs.json"] = sha256_of(catalogs_path)

    kev_path = root / "kev_sample.json"
    if kev_path.exists():
        payload, err = load_json_file(kev_path)
        if err:
            errors.append(f"[kev_sample.json] {err}")
        else:
            doc["kev"] = payload
            doc["files"]["kev_sample.json"] = sha256_of(kev_path)

    # Live-fetched material (fetch_sources.py output) overrides / enriches:
    fetched_dir = root / "fetched"
    doc["fetched"] = {}
    if fetched_dir.is_dir():
        kev_live = fetched_dir / "kev_live.json"
        if kev_live.exists():
            payload, err = load_json_file(kev_live)
            if err:
                errors.append(f"[kev_live.json] {err}")
            else:
                doc["kev"] = payload  # live feed wins over baked sample
                doc["files"]["kev_live.json"] = sha256_of(kev_live)
        for name in ("attack_reference.json", "atomic_tests.json",
                     "capec_verification.json", "provenance.json"):
            p = fetched_dir / name
            if p.exists():
                payload, err = load_json_file(p)
                if err:
                    errors.append(f"[{name}] {err}")
                else:
                    doc["fetched"][name.replace(".json", "")] = payload
                    doc["files"][f"fetched/{name}"] = sha256_of(p)

    # Knowledge-tier spine (build_spine.py output): live ATT&CK records,
    # hard-locked to 'unreviewed' so they can never execute unassessed.
    doc["spine"] = None
    spine_path = root / "techniques_spine.json"
    if spine_path.exists():
        payload, err = load_json_file(spine_path)
        if err:
            errors.append(f"[techniques_spine.json] {err}")
        else:
            doc["spine"] = payload
            doc["files"]["techniques_spine.json"] = sha256_of(spine_path)

    return doc, errors


def try_refresh_kev(root: Path):
    """Best-effort live KEV fetch; falls back silently to the baked sample."""
    url = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={"User-Agent": "grimoire-loader/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        n = len(data.get("vulnerabilities", []))
        if n == 0:
            raise ValueError("empty feed")
        print(f"  [kev] live fetch OK: {n} known-exploited entries from CISA")
        return data, True
    except Exception as exc:  # noqa: BLE001 - offline fallback is the documented path
        print(f"  [kev] live fetch unavailable ({exc.__class__.__name__}) - using baked sample")
        data, err = load_json_file(root / "kev_sample.json")
        return (data if not err else None), False


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------
def validate_technique(rec: dict, idx: int):
    """Returns a list of error strings for one technique record (empty = clean)."""
    errs = []
    src = rec.get("_source_file", "?")
    tag = f"[{src} #{idx + 1}]"

    for field in SCHEMA["required_fields"]:
        if field not in rec:
            errs.append(f"{tag} missing required field: {field}")

    if "id" in rec:
        rid = rec["id"]
        parts = rid.split("-")
        if not (len(parts) == 3 and parts[0] == "GRM" and len(parts[1]) == 3
                and parts[2].isdigit() and len(parts[2]) == 3):
            errs.append(f"{tag} bad id format '{rid}' (want GRM-XXX-000)")
        elif "code" in rec and rec.get("_domain_code") != parts[1]:
            errs.append(f"{tag} id code {parts[1]} != file code {rec.get('_domain_code')}")

    for field in SCHEMA["at_least_one_mapping"]:
        if rec.get(field):
            break
    else:
        errs.append(f"{tag} needs at least one of mitre/capec/cwe")

    for field, allowed in SCHEMA["enums"].items():
        if field in rec and rec[field] not in allowed:
            errs.append(f"{tag} {field}='{rec[field]}' not in {sorted(allowed)}")

    # The conscience: detection pair mandatory
    det = rec.get("detection") or {}
    if not det:
        errs.append(f"{tag} detection block MISSING - no move without counter")
    else:
        if not (det.get("description") or "").strip():
            errs.append(f"{tag} detection.description empty")
        if not det.get("mitigations"):
            errs.append(f"{tag} detection.mitigations empty - no move without counter")

    # The conscience floor: confirmation on dangerous/irreversible moves
    blast = rec.get("blast_radius")
    rev = rec.get("reversibility")
    must_confirm = (
        blast in SCHEMA["confirmation_required_if"]["blast_radius"]
        or rev in SCHEMA["confirmation_required_if"]["reversibility"]
    )
    if must_confirm and rec.get("requires_confirmation") is not True:
        errs.append(
            f"{tag} CONSCIENCE VIOLATION: {rid if 'id' in rec else 'record'} has "
            f"blast_radius={blast}/reversibility={rev} but requires_confirmation is not true"
        )
    return errs


def validate_spine_record(rec: dict, idx: int):
    """Knowledge-tier records: deliberately lighter, deliberately locked.
    A spine record is planner-visible knowledge only - it must never look
    like an execution-eligible technique until an operator promotes it."""
    errs = []
    tag = f"[spine #{idx + 1}]"
    rid = rec.get("id", "?")
    if not (isinstance(rid, str) and rid.startswith("ATTACK-")):
        errs.append(f"{tag} bad id '{rid}' (want ATTACK-Txxxx[.xxx])")
    if rec.get("conscience_status") != "unreviewed":
        errs.append(f"{tag} {rid} conscience_status must be 'unreviewed' "
                    f"(knowledge tier is not execution-eligible)")
    if rec.get("source") != "mitre-attack":
        errs.append(f"{tag} {rid} source must be 'mitre-attack' (live STIX provenance)")
    if not (rec.get("name") or "").strip():
        errs.append(f"{tag} {rid} missing name")
    if not (rec.get("source_url") or "").strip():
        errs.append(f"{tag} {rid} missing source_url")
    return errs


# --------------------------------------------------------------------------
# Indexing & packing
# --------------------------------------------------------------------------
def build_indexes(techniques):
    idx = {
        "by_domain": defaultdict(list),
        "by_mitre": defaultdict(list),
        "by_blast_radius": defaultdict(list),
        "by_klass": defaultdict(list),
        "requires_confirmation": [],
    }
    for t in techniques:
        idx["by_domain"][t["_domain"]].append(t["id"])
        for m in t.get("mitre", []):
            idx["by_mitre"][m].append(t["id"])
        idx["by_blast_radius"][t["blast_radius"]].append(t["id"])
        idx["by_klass"][t["klass"]].append(t["id"])
        if t.get("requires_confirmation"):
            idx["requires_confirmation"].append(t["id"])
    return {k: (dict(v) if isinstance(v, defaultdict) else v) for k, v in idx.items()}


def pack_library(root: Path, doc, kev, kev_live):
    now = datetime.datetime.now().isoformat(timespec="seconds")
    tcount = len(doc["techniques"])
    confirm_count = sum(1 for t in doc["techniques"] if t.get("requires_confirmation"))
    mitre_mapped = sum(1 for t in doc["techniques"] if t.get("mitre"))
    detected = sum(
        1 for t in doc["techniques"]
        if (t.get("detection") or {}).get("description") and (t.get("detection") or {}).get("mitigations")
    )
    fetched = doc.get("fetched", {})
    attack = fetched.get("attack_reference") or {}
    atomic = fetched.get("atomic_tests") or {}
    capec = fetched.get("capec_verification") or {}
    mitre_status = attack.get("library_mitre_status", {})
    mitre_verified = sum(1 for v in mitre_status.values() if v == "verified")
    capec_status = capec.get("library_capec_status", {})
    capec_verified = sum(1 for v in capec_status.values() if v.startswith("verified"))
    kev_meta = (kev or {}).get("_provenance", {})
    spine = doc.get("spine") or {}
    spine_records = spine.get("records", [])
    spine_by_tactic = defaultdict(list)
    for r in spine_records:
        for tac in r.get("tactics", []):
            spine_by_tactic[tac].append(r["id"])

    pack = {
        "pack_meta": {
            "name": LIB_NAME,
            "version": LIB_VERSION,
            "built_at": now,
            "technique_count": tcount,
            "domain_count": len({t["_domain"] for t in doc["techniques"]}),
            "catalog_entry_count": len(doc["catalogs"]),
            "kev_mode": "live" if kev_meta.get("verified") and kev_meta.get("count", 0) > 100 else "sample",
            "kev_entries": len((kev or {}).get("vulnerabilities", [])),
            "fetched_material": {
                "attack_techniques_available": len(attack.get("techniques", {})),
                "mitre_library_refs_verified": f"{mitre_verified}/{len(mitre_status)}",
                "atomic_tests_count": atomic.get("test_count", 0),
                "atomic_techniques_covered": len(atomic.get("_provenance", {}).get("techniques_with_tests", [])),
                "capec_library_refs_verified": f"{capec_verified}/{len(capec_status)}",
            },
            "conscience": {
                "requires_confirmation_count": confirm_count,
                "detection_pair_coverage": round(detected / tcount, 3) if tcount else 0.0,
                "mitre_mapped_count": mitre_mapped,
            },
            "spine": {
                "tier": "knowledge (unreviewed, execution-ineligible)",
                "record_count": len(spine_records),
                "with_detection_text": sum(1 for r in spine_records if (r.get("detection") or "").strip()),
                "tactic_count": len(spine_by_tactic),
                "promotion_rule": (spine.get("_meta") or {}).get("promotion_rule"),
            },
            "source_file_hashes": doc["files"],
            "generator": "grimoire loader.py (stdlib only)",
        },
        "techniques": doc["techniques"],
        "spine": spine,
        "catalogs": doc["catalogs"],
        "kev": kev,
        "attack_reference": attack,
        "atomic_tests": atomic,
        "capec_verification": capec,
        "fetch_provenance": fetched.get("provenance"),
        "indexes": {**build_indexes(doc["techniques"]),
                    "spine_by_tactic": dict(spine_by_tactic)},
    }
    out = root / "grimoire.feed.json"
    out.write_text(json.dumps(pack, indent=1, ensure_ascii=False), encoding="utf-8")
    return out


def make_zip(root: Path, feed_path: Path):
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    zip_path = dist / "droid_grimoire_v1.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(root.rglob("*")):
            if not path.is_file():
                continue
            if "dist" in path.parts or path == feed_path:
                continue
            zf.write(path, arcname=path.relative_to(root.parent))
        zf.write(feed_path, arcname=feed_path.relative_to(root.parent))
    return zip_path


def verify_zip(zip_path: Path):
    """Re-open the zip, re-parse and re-validate every technique inside."""
    errs = []
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for name in sorted(n for n in names if "/techniques/" in n and n.endswith(".json")):
            try:
                payload = json.loads(zf.read(name).decode("utf-8"))
            except Exception as exc:  # noqa: BLE001
                errs.append(f"[zip:{name}] parse error: {exc}")
                continue
            for i, rec in enumerate(payload.get("techniques", [])):
                errs.extend(validate_technique(rec, i))
    return len(names), errs


# --------------------------------------------------------------------------
# Demo queries
# --------------------------------------------------------------------------
def demo(pack):
    print("\n== DEMO QUERIES (her planner uses these indexes) ==")
    crit = pack["indexes"]["by_blast_radius"].get("critical", [])
    print(f"\n[1] blast_radius == critical -> {len(crit)} techniques")
    for tid in crit:
        t = next(x for x in pack["techniques"] if x["id"] == tid)
        print(f"    {tid}  {t['name']}  (confirm={t['requires_confirmation']})")

    print("\n[2] MITRE lookup T1558.003 (Kerberoasting):")
    for tid in pack["indexes"]["by_mitre"].get("T1558.003", []):
        t = next(x for x in pack["techniques"] if x["id"] == tid)
        print(f"    {t['id']} :: {t['name']}")
        print(f"      detection : {t['detection']['description'][:100]}...")
        print(f"      mitigation: {t['detection']['mitigations'][0]}")

    live_kev = pack.get("fetch_provenance") is not None and len(pack["kev"]["vulnerabilities"]) > 100
    label = "LIVE FEED" if live_kev else "baked sample"
    print(f"\n[3] KEV priorities ({label}):")
    for v in pack["kev"]["vulnerabilities"][:4]:
        rw = v.get("knownRansomwareCampaignUse", "?")
        print(f"    {v['cveID']}  {v['vulnerabilityName']}  [ransomware: {rw}]")

    attack = pack.get("attack_reference") or {}
    atomic = pack.get("atomic_tests") or {}
    if atomic.get("tests"):
        print(f"\n[4] Real tested simulations (Atomic Red Team): {atomic.get('test_count')} tests")
        t = next((x for x in atomic["tests"] if x["technique"] == "T1558.003"), atomic["tests"][0])
        print(f"    {t['technique']} :: {t['test_name']}")
        print(f"      executor: {t['executor']}  elevation: {t['elevation_required']}")
        print(f"      command : {t['command'][:100]}...")
        print(f"      cleanup : {(t['cleanup'] or '(none)')[:100]}")
    if attack:
        st = attack.get("library_mitre_status", {})
        ok = sum(1 for v in st.values() if v == "verified")
        print(f"\n[5] ATT&CK spine: {len(attack.get('techniques', {}))} live techniques; "
              f"library refs verified {ok}/{len(st)}")

    spine = pack.get("spine") or {}
    srecs = spine.get("records", [])
    if srecs:
        print(f"\n[6] Knowledge tier: {len(srecs)} unreviewed ATT&CK records "
              f"(planner-visible, execution-INELIGIBLE until promoted)")
        bt = pack["indexes"].get("spine_by_tactic", {})
        top = sorted(bt.items(), key=lambda kv: -len(kv[1]))[:5]
        print("    tactics:", ", ".join(f"{k} ({len(v)})" for k, v in top))
        s = next(r for r in srecs if r["id"] == "ATTACK-T1558.003")
        print(f"    sample {s['id']} :: {s['name']}")
        print(f"      source  : {s['source_url']}")
        print(f"      status  : {s['conscience_status']} -> promote by authoring full conscience fields")


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="GRIMOIRE loader - validate, index, pack")
    ap.add_argument("--pack", action="store_true", help="validate + write feed + zip")
    ap.add_argument("--refresh-kev", action="store_true", help="attempt live CISA KEV fetch")
    ap.add_argument("--verify", metavar="ZIP", help="re-validate a built zip bundle")
    ap.add_argument("--demo", action="store_true", help="run demo queries after packing")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent),
                    help="library root (default: beside this script)")
    args = ap.parse_args()
    root = Path(args.root).resolve()

    print(f"== {LIB_NAME} {LIB_VERSION} loader ==")
    print(f"  root: {root}")

    if args.verify:
        n, errs = verify_zip(Path(args.verify))
        if errs:
            print(f"\nVERIFY FAILED: {len(errs)} errors")
            for e in errs:
                print(f"  {e}")
            return 1
        print(f"VERIFY OK: {n} files in bundle, all technique records re-validated clean")
        return 0

    doc, load_errs = load_library(root)
    if doc is None:
        for e in load_errs:
            print(f"  {e}")
        return 1

    print(f"  loaded: {len(doc['techniques'])} techniques, {len(doc['catalogs'])} catalog entries, "
          f"kev={'yes' if doc['kev'] else 'no'}, "
          f"spine={len((doc.get('spine') or {}).get('records', []))} knowledge records")

    all_errs = list(load_errs)
    seen = set()
    for i, rec in enumerate(doc["techniques"]):
        rid = rec.get("id", f"?{i}")
        if rid in seen:
            all_errs.append(f"[dup] duplicate id {rid}")
        seen.add(rid)
        all_errs.extend(validate_technique(rec, i))

    spine_recs = (doc.get("spine") or {}).get("records", [])
    for i, rec in enumerate(spine_recs):
        all_errs.extend(validate_spine_record(rec, i))

    if all_errs:
        print(f"\nVALIDATION FAILED: {len(all_errs)} error(s)")
        for e in all_errs:
            print(f"  {e}")
        return 1
    print("  validation: CLEAN (schema + conscience checks passed)")

    kev, kev_live = (doc["kev"], False)
    if args.refresh_kev:
        kev, kev_live = try_refresh_kev(root)

    if not args.pack:
        print("\n(validated only - pass --pack to write feed + zip)")
        return 0

    feed = pack_library(root, doc, kev, kev_live)
    size_kb = feed.stat().st_size / 1024
    print(f"  pack    -> {feed.name}  ({size_kb:.1f} KiB)")
    zpath = make_zip(root, feed)
    print(f"  bundle  -> {zpath.relative_to(root.parent)}  ({zpath.stat().st_size / 1024:.1f} KiB)")

    meta = json.loads(feed.read_text(encoding="utf-8"))["pack_meta"]
    print(f"\n  conscience: {meta['conscience']['requires_confirmation_count']}/{meta['technique_count']} "
          f"techniques gated behind operator confirmation")
    print(f"  conscience: detection-pair coverage {meta['conscience']['detection_pair_coverage'] * 100:.0f}% "
          f"(no move without counter)")
    print(f"  mapped to MITRE: {meta['conscience']['mitre_mapped_count']}/{meta['technique_count']}")

    if args.demo:
        demo(json.loads(feed.read_text(encoding="utf-8")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
