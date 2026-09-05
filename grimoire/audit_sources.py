#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GRIMOIRE SOURCE AUDITOR - deep verification per LO's apex-doctrine challenge.
"Analyse and audit every source to create this library."

For each catalog source this auditor:
  1. READS the live source (page or raw content fetch, ~64 KiB window)
  2. Confirms the URL serves what the catalog claims (content keywords)
  3. Extracts real evidence tokens (technique/tool/topic words present)
  4. Checks LIBRARY COVERAGE: does her 50-record Tier-1 actually reference
     the doctrine items this source teaches (via mitre/cwe/name tokens)?
Outputs source_audit.json + printed gap list. stdlib only. python audit_sources.py
"""

import datetime
import json
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FETCHED = ROOT / "fetched"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) grimoire-audit/1.0",
      "Accept": "text/html,text/plain,application/json,*/*;q=0.8"}

# Per-source: fetch target (prefer raw content over HTML chrome) + claim keywords.
# keywords: at least one must appear for the catalog CLAIM to hold.
# coverage_tokens: tokens that, if in her Tier-1 corpus, prove she absorbed
# the classes this source teaches (checked against her records' text).
SOURCES = [
    {"name": "SecLists", "url": "https://raw.githubusercontent.com/danielmiessler/SecLists/master/README.md",
     "keywords": ["seclists", "wordlist"], "coverage_tokens": ["credential", "brute force", "wordlist"]},
    {"name": "PayloadsAllTheThings", "url": "https://raw.githubusercontent.com/swisskyrepo/PayloadsAllTheThings/master/README.md",
     "keywords": ["payload", "injection"], "coverage_tokens": ["sql", "ssti", "deserialization", "xxe", "command injection"]},
    {"name": "HackTricks", "url": "https://book.hacktricks.xyz",
     "keywords": ["hacktricks", "pentest"], "coverage_tokens": ["kerberoast", "privesc", "relay"]},
    {"name": "GTFOBins", "url": "https://gtfobins.github.io",
     "keywords": ["gtfobins", "sudo"], "coverage_tokens": ["sudo", "unix", "privilege"]},
    {"name": "LOLBAS", "url": "https://lolbas-project.github.io",
     "keywords": ["lolbas", "living off the land"], "coverage_tokens": ["living off the land", "signed binary", "windows"]},
    {"name": "PEASS-ng", "url": "https://raw.githubusercontent.com/carlospolop/PEASS-ng/master/README.md",
     "keywords": ["peass", "privilege escalation"], "coverage_tokens": ["privilege escalation", "enumeration", "misconfiguration"]},
    {"name": "OWASP WSTG", "url": "https://owasp.org/www-project-web-security-testing-guide/",
     "keywords": ["web security testing"], "coverage_tokens": ["authentication", "session", "authorization"]},
    {"name": "PortSwigger Web Security Academy", "url": "https://portswigger.net/web-security",
     "keywords": ["web security", "sql injection"], "coverage_tokens": ["ssrf", "sql", "race condition"]},
    {"name": "Exploit-DB", "url": "https://www.exploit-db.com",
     "keywords": ["exploit"], "coverage_tokens": ["exploit", "public", "cve"]},
    {"name": "Metasploit Framework", "url": "https://raw.githubusercontent.com/rapid7/metasploit-framework/master/README.md",
     "keywords": ["metasploit", "exploit"], "coverage_tokens": ["exploitation", "payload", "post"]},
    {"name": "MITRE ATT&CK STIX Data", "url": "https://raw.githubusercontent.com/mitre-attack/attack-stix-data/master/README.md",
     "keywords": ["stix", "attack"], "coverage_tokens": ["mitre", "tactic", "technique"]},
    {"name": "Atomic Red Team", "url": "https://raw.githubusercontent.com/redcanaryco/atomic-red-team/master/README.md",
     "keywords": ["atomic", "test"], "coverage_tokens": ["simulation", "detection", "test"]},
    {"name": "Nuclei Templates", "url": "https://raw.githubusercontent.com/projectdiscovery/nuclei-templates/main/README.md",
     "keywords": ["nuclei", "template"], "coverage_tokens": ["webapp", "cve", "template"]},
    {"name": "Sigma Rules", "url": "https://raw.githubusercontent.com/SigmaHQ/sigma/master/README.md",
     "keywords": ["sigma", "detection", "siem"], "coverage_tokens": ["detection", "event", "log"]},
    {"name": "CISA KEV Catalog", "url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog",
     "keywords": ["known exploited"], "coverage_tokens": ["kev", "known exploited", "cve"]},
    {"name": "NVD / CVE", "url": "https://nvd.nist.gov",
     "keywords": ["vulnerability", "cve"], "coverage_tokens": ["cvss", "cve", "vulnerability"]},
    {"name": "PTES", "url": "http://www.pentest-standard.org",
     "keywords": ["penetration testing", "execution"], "coverage_tokens": ["scope", "methodology", "reporting"]},
    {"name": "NIST SP 800-115", "url": "https://csrc.nist.gov/pubs/sp/800/115/final",
     "keywords": ["800-115", "assessment"], "coverage_tokens": ["assessment", "methodology", "scope"]},
    {"name": "Phrack", "url": "http://phrack.org",
     "keywords": ["phrack", "magazine"], "coverage_tokens": ["memory corruption", "shellcode", "exploitation"]},
    {"name": "picoCTF", "url": "https://picoctf.org",
     "keywords": ["picoctf", "capture the flag"], "coverage_tokens": ["ctf", "gym", "practice"]},
    {"name": "OverTheWire Bandit", "url": "https://overthewire.org/wargames/bandit/",
     "keywords": ["bandit", "wargame"], "coverage_tokens": ["unix", "ssh", "gym"]},
    {"name": "cybench", "url": "https://raw.githubusercontent.com/andyzorigin/cybench/main/README.md",
     "keywords": ["cybench", "benchmark"], "coverage_tokens": ["benchmark", "agent", "ctf"]},
    {"name": "OWASP Juice Shop", "url": "https://raw.githubusercontent.com/juice-shop/juice-shop/master/README.md",
     "keywords": ["juice shop", "vulnerab"], "coverage_tokens": ["webapp", "owasp", "practice"]},
    {"name": "DVWA", "url": "https://raw.githubusercontent.com/digininja/DVWA/master/README.md",
     "keywords": ["dvwa", "damn vulnerable"], "coverage_tokens": ["injection", "webapp", "practice"]},
    {"name": "VulnHub", "url": "https://www.vulnhub.com",
     "keywords": ["vulnhub", "virtual machine"], "coverage_tokens": ["vm", "practice", "lab"]},
    {"name": "Probable-Wordlists", "url": "https://raw.githubusercontent.com/berzerk0/Probable-Wordlists/master/README.md",
     "keywords": ["probable", "password"], "coverage_tokens": ["credential", "password", "brute force"]},
    {"name": "fuzzdb", "url": "https://raw.githubusercontent.com/fuzzdb-project/fuzzdb/master/README.md",
     "keywords": ["fuzz"], "coverage_tokens": ["fuzzing", "payload", "discovery"]},
    {"name": "Kali wordlists package", "url": "https://www.kali.org/tools/wordlists/",
     "keywords": ["wordlist", "kali"], "coverage_tokens": ["rockyou", "wordlist", "credential"]},
    {"name": "CWE (downloads)", "url": "https://cwe.mitre.org/data/downloads.html",
     "keywords": ["cwe", "weakness"], "coverage_tokens": ["cwe", "weakness", "injection"]},
    {"name": "CAPEC (downloads)", "url": "https://capec.mitre.org/data/downloads.html",
     "keywords": ["capec", "attack pattern"], "coverage_tokens": ["capec", "attack pattern", "social engineering"]},
    {"name": "Assetnote Wordlists", "url": "https://wordlists.assetnote.io",
     "keywords": ["wordlist"], "coverage_tokens": ["subdomain", "discovery", "wordlist"]},
]


def fetch(url, rng=None, timeout=20):
    headers = dict(UA)
    if rng:
        headers["Range"] = rng
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read(131072)


def tokens_of(text):
    return {t for t in re.split(r"[^a-z0-9+#]+", text.lower()) if len(t) > 2}


def main():
    print("== GRIMOIRE SOURCE AUDITOR (deep read + coverage) ==")

    # her Tier-1 corpus text, once
    corpus_text = []
    for p in sorted((ROOT / "techniques").glob("*.json")):
        payload = json.loads(p.read_text(encoding="utf-8"))
        for rec in payload.get("techniques", []):
            blob = " ".join([rec.get("name", ""), rec.get("summary", ""),
                             json.dumps(rec.get("detection", {})),
                             " ".join(rec.get("mitre", [])),
                             " ".join(rec.get("cwe", [])),
                             " ".join(rec.get("capec", []))])
            corpus_text.append(blob)
    corpus_tokens = tokens_of(" ".join(corpus_text))
    print(f"tier-1 corpus: {len(corpus_text)} records, {len(corpus_tokens)} distinct tokens\n")

    results = []
    for src in SOURCES:
        name, url = src["name"], src["url"]
        row = {"name": name, "url": url}
        try:
            status, body = fetch(url)
            text = body.decode("utf-8", errors="replace").lower()
            kw_hits = [k for k in src["keywords"] if k in text]
            row["http_status"] = status
            row["claim_keywords_found"] = kw_hits
            row["claim_holds"] = bool(kw_hits)
            # evidence: which coverage tokens does the LIVE source text carry
            live_tokens = tokens_of(text)
            present = sorted(src_tok for src_tok in src["coverage_tokens"]
                             if src_tok in live_tokens or src_tok in text)
            row["evidence_in_source"] = present
            # coverage: does HER corpus carry the same doctrine tokens
            # (substring match against full corpus text - multi-word phrases
            # like 'command injection' must be checked literally, not as
            # individual words, or every phrase falsely reports as a gap)
            corpus_str = " ".join(corpus_text).lower()
            missing_in_her = sorted(t for t in src["coverage_tokens"]
                                    if t not in corpus_str)
            row["gap_in_library"] = missing_in_her
            row["coverage_ratio"] = round(
                1 - len(missing_in_her) / max(len(src["coverage_tokens"]), 1), 2)
            verdict = "CLAIM VERIFIED" if row["claim_holds"] else "CLAIM WEAK"
            print(f"[{verdict:^14}] {name}: kw={kw_hits or '-'} "
                  f"evidence={len(present)}/{len(src['coverage_tokens'])} "
                  f"gap={missing_in_her or 'none'}")
        except Exception as exc:  # noqa: BLE001 - honest failure per source
            row["error"] = f"{exc.__class__.__name__}: {exc}"
            print(f"[{'UNREACHABLE':^14}] {name}: {row['error']}")
        results.append(row)

    n_ver = sum(1 for r in results if r.get("claim_holds"))
    n_cov = sum(1 for r in results if r.get("coverage_ratio", 0) >= 0.99)
    gaps = {}
    for r in results:
        for g in r.get("gap_in_library", []):
            gaps.setdefault(g, []).append(r["name"])
    doc = {
        "_provenance": {"audited_at": datetime.datetime.now().isoformat(timespec="seconds"),
                        "method": "live fetch of raw content per source; claim keywords + "
                                  "evidence extraction + tier-1 corpus coverage check",
                        "sources_checked": len(results)},
        "sources": results,
        "summary": {"claims_verified": f"{n_ver}/{len(results)}",
                    "full_coverage": f"{n_cov}/{len(results)}",
                    "doctrine_token_gaps": gaps},
    }
    out = ROOT / "source_audit.json"
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nsummary: {n_ver}/{len(results)} claims verified live, "
          f"{n_cov}/{len(results)} full library coverage")
    if gaps:
        print("doctrine tokens missing from tier-1 (candidates for promotion/new records):")
        for g, srcs in sorted(gaps.items()):
            print(f"  - '{g}'  (taught by: {', '.join(srcs[:3])})")
    print(f"written: {out.name} ({out.stat().st_size / 1024:.1f} KiB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
