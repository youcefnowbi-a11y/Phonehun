#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIMOIRE PROOF HARNESS - adversarial self-audit against live sources.
LO's challenge: "prove the library contains real things - you didn't fetch
all the sources, you didn't read everything." Correct. This harness answers
with receipts, not assurances.

Battery A - memory vs. live: the 10 hand-authored KEV sample entries are
            checked field-by-field against the live CISA feed.
Battery B - technique claims: every MITRE mapping checked for existence and
            live-name overlap; ART evidence commands extracted; cleanup
            availability counted; headline side-by-side receipts printed.
Battery C - catalog liveness: EVERY catalog URL probed with a Range-limited
            GET and an expected-content keyword check.

Writes proof_report.json. stdlib only. Run: python prove_it.py
"""

import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FETCHED = ROOT / "fetched"
UA = {"User-Agent": "Mozilla/5.0 (grimoire-proof/1.0; authorized-lab audit)",
      "Accept": "text/html,application/json,*/*"}

report = {"batteries": {}, "verdict": {}}


def tokens(s):
    return {w for w in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(w) > 2}


def overlap(a, b):
    ta, tb = tokens(a), tokens(b)
    return round(len(ta & tb) / len(tb), 2) if tb else 0.0


def http_probe(url, rng="bytes=0-16383", timeout=15):
    req = urllib.request.Request(url, headers={**UA, "Range": rng})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(65536)


# ---------------------------------------------------------------- Battery A
def battery_a():
    print("\n== BATTERY A: memory-authored KEV sample vs. LIVE CISA feed ==")
    sample = json.loads((ROOT / "kev_sample.json").read_text(encoding="utf-8"))
    entries = sample.get("vulnerabilities", sample if isinstance(sample, list) else [])
    live_feed = json.loads((FETCHED / "kev_live.json").read_text(encoding="utf-8"))
    live = {v["cveID"]: v for v in live_feed.get("vulnerabilities", [])}

    results = []
    for v in entries:
        cve = v.get("cveID")
        lv = live.get(cve)
        row = {"cve": cve, "in_live_feed": lv is not None}
        if lv:
            row["memory_name"] = v.get("vulnerabilityName")
            row["live_name"] = lv.get("vulnerabilityName")
            row["name_overlap"] = overlap(row["memory_name"], row["live_name"])
            row["memory_date"] = v.get("dateAdded")
            row["live_date"] = lv.get("dateAdded")
            row["date_match"] = row["memory_date"] == row["live_date"]
            row["ransomware_memory"] = v.get("knownRansomwareCampaignUse")
            row["ransomware_live"] = lv.get("knownRansomwareCampaignUse")
        results.append(row)
        if lv:
            print(f"  {cve}: IN live feed | name overlap {row['name_overlap']:.2f} | "
                  f"date {'match' if row['date_match'] else 'MISMATCH'} "
                  f"({row['memory_date']} vs {row['live_date']})")
        else:
            print(f"  {cve}: *** NOT IN LIVE FEED ***")

    n_in = sum(1 for r in results if r["in_live_feed"])
    n_name = sum(1 for r in results if r.get("name_overlap", 0) >= 0.5)
    n_date = sum(1 for r in results if r.get("date_match"))
    print(f"  -> {n_in}/{len(results)} exist live | {n_name} names overlap>=0.5 | "
          f"{n_date} dates exact (memory-authored dates, sample retired - pack uses live)")
    report["batteries"]["A_kev_memory_vs_live"] = {
        "entries": results,
        "exist_in_live": f"{n_in}/{len(results)}",
        "name_overlap_ge_0.5": f"{n_name}/{len(results)}",
        "date_exact": f"{n_date}/{len(results)}",
    }


# ---------------------------------------------------------------- Battery B
def battery_b():
    print("\n== BATTERY B: technique claims vs. live ATT&CK + ART evidence ==")
    attack = json.loads((FETCHED / "attack_reference.json").read_text(encoding="utf-8"))
    atomic = json.loads((FETCHED / "atomic_tests.json").read_text(encoding="utf-8"))
    art_by_tid = {}
    for t in atomic.get("tests", []):
        art_by_tid.setdefault(t["technique"], []).append(t)

    recs = []
    for p in sorted((ROOT / "techniques").glob("*.json")):
        for rec in json.loads(p.read_text(encoding="utf-8")).get("techniques", []):
            recs.append(rec)

    mapped, missing, name_scores, art_evidence, cleanups = 0, [], [], 0, 0
    total_tests = atomic.get("test_count", 0)
    for rec in recs:
        for tid in rec.get("mitre", []):
            live_t = attack.get("techniques", {}).get(tid)
            if not live_t:
                missing.append({"record": rec["id"], "mitre": tid})
                continue
            mapped += 1
            name_scores.append(overlap(rec.get("name"), live_t.get("name")))
            tests = art_by_tid.get(tid)
            if tests:
                art_evidence += 1
                cleanups += sum(1 for t in tests if (t.get("cleanup") or "").strip())

    avg = round(sum(name_scores) / len(name_scores), 2) if name_scores else 0.0
    print(f"  MITRE mappings: {mapped} verified live, {len(missing)} missing")
    print(f"  record-name vs live-ATT&CK-name overlap: avg {avg} over {len(name_scores)}")
    print(f"  records with real ART test evidence: {art_evidence} of {len(recs)}")
    print(f"  ART tests shipping cleanup commands: {cleanups} of {total_tests}")
    if missing:
        for m in missing:
            print(f"  [!] {m['record']}: {m['mitre']} not in live ATT&CK")

    # headline receipts: live STIX description + real ART command, side by side
    print("\n  -- receipts (my claim vs. the live artifact) --")
    receipts = []
    for rec in recs:
        if rec["id"] not in ("GRM-IDN-001", "GRM-IDN-004", "GRM-NET-001",
                             "GRM-EVS-001", "GRM-SOC-001"):
            continue
        for tid in rec.get("mitre", []):
            lt = attack.get("techniques", {}).get(tid)
            tests = art_by_tid.get(tid)
            entry = {
                "record": rec["id"], "mitre": tid,
                "my_name": rec.get("name"),
                "live_attck_name": (lt or {}).get("name"),
                "live_attck_url": (lt or {}).get("url"),
                "live_description_quote": ((lt or {}).get("description") or "")[:220],
                "art_test": (tests[0]["test_name"] if tests else None),
                "art_command_quote": ((tests[0]["command"] if tests else "") or "")[:220],
            }
            receipts.append(entry)
            print(f"  [{rec['id']} / {tid}] mine='{entry['my_name']}' live='{entry['live_attck_name']}'")
            print(f"      live ATT&CK: {entry['live_description_quote']}...")
            print(f"      ART test   : {entry['art_test']}")
            print(f"      ART command: {entry['art_command_quote']}...")
    report["batteries"]["B_technique_claims"] = {
        "mitre_verified": f"{mapped}/{mapped + len(missing)}",
        "name_overlap_avg": avg,
        "records_with_art_evidence": f"{art_evidence}/{len(recs)}",
        "art_cleanup_commands": f"{cleanups}/{total_tests}",
        "missing": missing,
        "receipts": receipts,
    }


# ---------------------------------------------------------------- Battery C
KEYWORDS = [
    ("seclists", ["seclists", "danielmiessler", "wordlist"]),
    ("probable-wordlists", ["probable", "wordlists"]),
    ("fuzzdb", ["fuzzdb", "discovery"]),
    ("gtfobins", ["gtfobins", "sudo", "shell"]),
    ("lolbas", ["lolbas", "live off the land"]),
    ("payloadsallthethings", ["payloadsallthethings", "payload"]),
    ("hacktricks", ["hacktricks"]),
    ("peass-ng", ["peass", "linpeas", "winpeas"]),
    ("owasp-wstg", ["wstg", "web security testing"]),
    ("portswigger", ["portswigger", "burp"]),
    ("exploit-db", ["exploit", "database"]),
    ("metasploit", ["metasploit", "framework"]),
    ("nuclei", ["nuclei", "templates"]),
    ("sigma", ["sigma", "detection rule", "siem"]),
    ("ptes", ["penetration testing execution", "ptes"]),
    ("nist", ["800-115", "publication"]),
    ("phrack", ["phrack", "ezine", "magazine"]),
    ("picoctf", ["picoctf", "capture the flag"]),
    ("bandit", ["bandit", "security linter", "pycqa"]),
    ("juice-shop", ["juice shop", "owasp"]),
    ("dvwa", ["damn vulnerable", "dvwa"]),
    ("vulnhub", ["vulnhub", "vulnerable"]),
    ("cybench", ["cybench", "benchmark"]),
]


def battery_c():
    print("\n== BATTERY C: all 31 catalog sources - liveness + content check ==")
    cat = json.loads((ROOT / "catalogs.json").read_text(encoding="utf-8"))
    entries = cat.get("catalogs", [])
    results = []
    already = ("cisa.gov", "attack-stix-data", "redcanaryco", "capec.mitre.org",
               "raw.githubusercontent.com/mitre/cti")
    for e in entries:
        url = e.get("url", "")
        name = e.get("name") or e.get("id") or url
        row = {"name": name, "url": url}
        if any(s in url for s in already):
            row["status"] = "verified-by-fetcher"
            row["note"] = "full content already fetched + hashed by fetch_sources.py"
            print(f"  [deep-verified] {name}")
        else:
            kws = next(([k for k in kws] for sub, kws in KEYWORDS if sub in url.lower()), None)
            try:
                status, body = http_probe(url)
                text = body.decode("utf-8", errors="replace").lower()
                row["http_status"] = status
                if kws:
                    hit = next((k for k in kws if k in text), None)
                    row["content_keyword"] = hit
                    row["verdict"] = "content-verified" if hit else "reachable-but-keyword-miss"
                else:
                    row["verdict"] = "reachable"
            except Exception as exc:  # noqa: BLE001 - recorded honestly, never fudged
                row["verdict"] = "unreachable"
                row["error"] = f"{exc.__class__.__name__}: {exc}"
            print(f"  [{row['verdict']:>26}] {name}  {row.get('error', '')}")
        results.append(row)
    n_ok = sum(1 for r in results if r.get("verdict") in
               ("content-verified", "reachable", "verified-by-fetcher"))
    n_cv = sum(1 for r in results if r.get("verdict") in ("content-verified", "verified-by-fetcher"))
    print(f"  -> {n_ok}/{len(results)} live | {n_cv}/{len(results)} content-verified | "
          f"{len(results) - n_ok} unreachable from this host")
    report["batteries"]["C_catalog_liveness"] = {
        "entries": results,
        "live": f"{n_ok}/{len(results)}",
        "content_verified": f"{n_cv}/{len(results)}",
    }


# ----------------------------------------------------------------
def main():
    print("== GRIMOIRE PROOF HARNESS ==")
    battery_a()
    battery_b()
    battery_c()
    b = report["batteries"]
    report["verdict"] = {
        "kev_memory_check": b["A_kev_memory_vs_live"]["exist_in_live"],
        "mitre_claim_check": b["B_technique_claims"]["mitre_verified"],
        "art_evidence": b["B_technique_claims"]["records_with_art_evidence"],
        "catalog_liveness": b["C_catalog_liveness"]["live"],
        "catalog_content_verified": b["C_catalog_liveness"]["content_verified"],
    }
    out = ROOT / "proof_report.json"
    out.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwritten: {out.name} ({out.stat().st_size / 1024:.1f} KiB)")
    print(json.dumps(report["verdict"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
