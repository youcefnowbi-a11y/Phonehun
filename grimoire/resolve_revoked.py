#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RESOLVE REVOKED MITRE IDS
Downloads the enterprise-attack STIX bundle and resolves, from the data itself,
what replaced each revoked technique (relationship_type: 'revoked-by').
Saves fetched/revoked_resolution.json - no guessing, ground truth only.
"""
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FETCHED = ROOT / "fetched"
TARGETS = ["T1562.001", "T1562.002", "T1574.002"]
URL = ("https://github.com/mitre-attack/attack-stix-data/releases/"
       "latest/download/enterprise-attack.json")

req = urllib.request.Request(URL, headers={"User-Agent": "grimoire-resolver/1.0"})
with urllib.request.urlopen(req, timeout=180) as r:
    raw = r.read()
print(f"bundle: {len(raw) / 1048576:.1f} MiB")
bundle = json.loads(raw.decode("utf-8", errors="replace"))

# stix_id -> external mitre id
stix_to_mitre, names = {}, {}
for o in bundle.get("objects", []):
    if o.get("type") != "attack-pattern":
        continue
    for ref in o.get("external_references", []):
        if ref.get("source_name") == "mitre-attack" and ref.get("external_id"):
            stix_to_mitre[o["id"]] = ref["external_id"]
            names[o["id"]] = o.get("name")
            break

revocations = {}
for o in bundle.get("objects", []):
    if o.get("type") == "relationship" and o.get("relationship_type") == "revoked-by":
        src = stix_to_mitre.get(o.get("source_ref"))
        tgt = stix_to_mitre.get(o.get("target_ref"))
        if src and tgt:
            revocations[src] = {"replaced_by": tgt,
                                "replacement_name": names.get(o.get("target_ref"))}

resolution = {t: revocations.get(t, {"replaced_by": None,
                                     "replacement_name": "no revoked-by relationship found"})
              for t in TARGETS}

out = {"_provenance": {"source": URL, "note": "resolved from STIX revoked-by relationships"},
       "resolutions": resolution}
(FETCHED / "revoked_resolution.json").write_text(
    json.dumps(out, indent=1), encoding="utf-8")

for t, info in resolution.items():
    print(f"{t} -> {info['replaced_by']}  ({info['replacement_name']})")
