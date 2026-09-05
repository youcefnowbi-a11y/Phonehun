#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
REPAIR PASS - restore x_mitre_detection text into fetched/attack_reference.json.
The cti-raw fallback bundle came back without detection bodies (0/858), while the
attack-stix-data release asset normally carries them. This tries the release URL
first, counts coverage, and merges only if it beats what we already hold.
Run: python repair_detection.py
"""
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REF = ROOT / "fetched" / "attack_reference.json"
URLS = [
    ("stix-release", "https://github.com/mitre-attack/attack-stix-data/releases/latest/download/enterprise-attack.json"),
    ("cti-raw", "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"),
]

ref = json.loads(REF.read_text(encoding="utf-8"))
techniques = ref.get("techniques", {})
cur = sum(1 for v in techniques.values() if (v.get("detection") or "").strip())
print(f"current detection coverage: {cur}/{len(techniques)}")

best, best_name = None, None
for name, url in URLS:
    try:
        print(f"trying {name} ...")
        req = urllib.request.Request(url, headers={"User-Agent": "grimoire-repair/1.0"})
        with urllib.request.urlopen(req, timeout=240) as r:
            raw = r.read()
        bundle = json.loads(raw.decode("utf-8", errors="replace"))
        det = {}
        for o in bundle.get("objects", []):
            if o.get("type") != "attack-pattern":
                continue
            for r_ in o.get("external_references", []):
                if r_.get("source_name") == "mitre-attack" and r_.get("external_id"):
                    det[r_["external_id"]] = (o.get("x_mitre_detection") or "").strip()
                    break
        n = sum(1 for v in det.values() if v)
        print(f"  {name}: {n}/{len(det)} techniques carry detection text ({len(raw)//1048576} MiB)")
        if n > (sum(1 for v in (best or {}).values() if v)):
            best, best_name = det, name
    except Exception as exc:  # noqa: BLE001
        print(f"  [skip] {name}: {exc.__class__.__name__}")

if not best:
    print("no source reachable - keeping current data")
    raise SystemExit(0)

new_cov = sum(1 for v in best.values() if v)
if new_cov <= cur:
    print(f"nothing to gain ({new_cov} <= {cur}) - keeping current data")
    raise SystemExit(0)

merged = 0
for tid, t in techniques.items():
    d = best.get(tid, "")
    if d and d != t.get("detection", ""):
        t["detection"] = d[:700]
        merged += 1
ref["_provenance"]["detection_repair"] = {
    "source": best_name,
    "merged_into": merged,
    "note": "x_mitre_detection bodies restored from release STIX bundle",
}
REF.write_text(json.dumps(ref, indent=1, ensure_ascii=False), encoding="utf-8")
print(f"merged detection text into {merged} techniques from {best_name}")
print(f"new coverage: {sum(1 for v in techniques.values() if (v.get('detection') or '').strip())}/{len(techniques)}")
