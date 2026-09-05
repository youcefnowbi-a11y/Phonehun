"""Verify external/boringssl repo + find spake25519 in it."""
import json, urllib.request

def gs_json(url):
    raw = urllib.request.urlopen(url + "?format=JSON", timeout=30).read()
    if raw.startswith(b")]}'"):
        raw = raw.split(b"\n", 1)[1]
    return json.loads(raw)

base = "https://android.googlesource.com/platform/external/boringssl/+/refs/heads/main/"
try:
    d = gs_json(base)
    names = sorted(e.get("name") for e in d.get("entries", []))
    print("ROOT OK:", names[:30])
    for sub in ["crypto/"]:
        try:
            s = gs_json(base + sub)
            n2 = sorted(e.get("name") for e in s.get("entries", []))
            print("crypto/ count:", len(n2))
            print("spake-ish:", [x for x in n2 if "spake" in x.lower() or "pake" in x.lower()] or "none")
            print("sample:", n2[:25])
        except Exception as e:
            print("sub fail", sub, e)
except Exception as e:
    print("ROOT FAIL:", e)
