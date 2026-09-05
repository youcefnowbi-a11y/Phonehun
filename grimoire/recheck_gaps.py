#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GAP RECHECK - offline correction of source_audit.json coverage results.
The audit's coverage check tested multi-word doctrine tokens against the
tier-1 corpus as a WORD SET, so phrases like 'command injection' could never
match even when literally present. This rechecks every gap as a SUBSTRING
against the corpus text (no network) and rewrites the file honestly.
Run: python recheck_gaps.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUDIT = ROOT / "source_audit.json"

corpus = []
for p in sorted((ROOT / "techniques").glob("*.json")):
    payload = json.loads(p.read_text(encoding="utf-8"))
    for rec in payload.get("techniques", []):
        corpus.append(" ".join([rec.get("name", ""), rec.get("summary", ""),
                                json.dumps(rec.get("detection", {})),
                                " ".join(rec.get("mitre", [])),
                                " ".join(rec.get("cwe", [])),
                                " ".join(rec.get("capec", []))]))
corpus_str = " ".join(corpus).lower()

doc = json.loads(AUDIT.read_text(encoding="utf-8"))
real_gaps = {}
fixed = 0
for r in doc["sources"]:
    if "gap_in_library" not in r:
        continue
    corrected = [t for t in r["gap_in_library"] if t not in corpus_str]
    r["gap_in_library"] = corrected
    r["coverage_ratio"] = round(1 - len(corrected) / max(
        len(r["gap_in_library"]) + len(corrected), 1), 2)
    if corrected:
        for g in corrected:
            real_gaps.setdefault(g, []).append(r["name"])
        fixed += 1

n_full = sum(1 for r in doc["sources"] if not r.get("gap_in_library"))
doc["summary"]["full_coverage"] = f"{n_full}/{len(doc['sources'])}"
doc["summary"]["doctrine_token_gaps"] = real_gaps
doc["summary"]["recheck_note"] = ("gaps recomputed as substrings against tier-1 corpus text "
                                  "(audit v1 word-set check falsely flagged multi-word phrases)")
AUDIT.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")

print(f"corpus: {len(corpus)} records, {len(corpus_str)} chars")
print(f"sources with corrected real gaps: {fixed}")
print(f"full coverage: {n_full}/{len(doc['sources'])}")
if real_gaps:
    print("\nREAL doctrine gaps remaining in tier-1:")
    for g, srcs in sorted(real_gaps.items()):
        print(f"  - '{g}'  (taught by: {', '.join(srcs)})")
else:
    print("\nno real doctrine gaps - every flagged phrase exists in her corpus")
