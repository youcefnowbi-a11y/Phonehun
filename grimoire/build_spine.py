#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIMOIRE SPINE BUILDER
Generates the knowledge-tier spine from the LIVE ATT&CK STIX extraction
(fetched/attack_reference.json, produced by fetch_sources.py).

Two-tier design (the honest way to scale):
  Tier 1 - authored records (techniques/*.json): fully schema'd, conscience-gated,
           execution-eligible inside scoped engagements.
  Tier 2 - spine records (this file): live ATT&CK techniques as KNOWLEDGE.
           conscience_status is hard-set to 'unreviewed' - the loader refuses
           anything else. Unreviewed records are planner-visible (for mapping
           findings to technique ids) but NEVER execution-eligible until an
           operator promotes them into Tier 1 with full detection-pair fields.

Revoked techniques are excluded entirely. Deprecated are kept but flagged.
Run: python build_spine.py
"""

import datetime
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FETCHED = ROOT / "fetched"
OUT = ROOT / "techniques_spine.json"


def main():
    src = FETCHED / "attack_reference.json"
    if not src.exists():
        print("attack_reference.json missing - run fetch_sources.py first")
        return 1
    ref = json.loads(src.read_text(encoding="utf-8"))
    techniques = ref.get("techniques", {})

    records, revoked, deprecated = [], [], []
    for tid, t in sorted(techniques.items()):
        if t.get("revoked"):
            revoked.append(tid)
            continue
        if t.get("deprecated"):
            deprecated.append(tid)
        records.append({
            "id": f"ATTACK-{tid}",
            "name": t.get("name"),
            "tactics": t.get("tactics", []),
            "description": t.get("description", ""),
            "detection": t.get("detection", ""),
            "platforms": t.get("platforms", []),
            "permissions_required": t.get("permissions_required", []),
            "deprecated": bool(t.get("deprecated")),
            "source": "mitre-attack",
            "source_url": t.get("url"),
            "conscience_status": "unreviewed",
        })

    by_tactic = {}
    for r in records:
        for tac in r["tactics"]:
            by_tactic[tac] = by_tactic.get(tac, 0) + 1
    with_det = sum(1 for r in records if r["detection"].strip())

    doc = {
        "_meta": {
            "tier": "knowledge (spine)",
            "eligibility": "planner-visible only - NOT execution-eligible until promoted to Tier 1",
            "promotion_rule": "operator review -> author full conscience fields (detection pair, blast_radius, reversibility, requires_confirmation) -> move to techniques/*.json",
            "generated_at": datetime.datetime.now().isoformat(timespec="seconds"),
            "source": "fetched/attack_reference.json (live ATT&CK STIX, see fetch_provenance)",
            "record_count": len(records),
            "with_detection_text": with_det,
            "detection_coverage": round(with_det / len(records), 3) if records else 0.0,
            "revoked_excluded": revoked,
            "deprecated_flagged": len(deprecated),
            "by_tactic": dict(sorted(by_tactic.items())),
        },
        "records": records,
    }
    OUT.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"spine built: {len(records)} records "
          f"(detection text on {with_det}, deprecated flagged {len(deprecated)}, "
          f"revoked excluded {len(revoked)})")
    for tac, n in sorted(by_tactic.items()):
        print(f"  {tac:22s} {n}")
    print(f"written: {OUT.name} ({OUT.stat().st_size / 1024:.1f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
