"""Find spake25519: list dirs + probe android release tags."""
import base64, urllib.request, os, json

OUT = os.path.join(os.path.dirname(__file__), "aosp")

def gs_json(url):
    raw = urllib.request.urlopen(url + "?format=JSON", timeout=30).read()
    if raw.startswith(b")]}'"):
        raw = raw.split(b"\n", 1)[1]
    return json.loads(raw)

def try_fetch(url, out):
    try:
        data = base64.b64decode(urllib.request.urlopen(url + "?format=TEXT", timeout=30).read())
        with open(os.path.join(OUT, out), "wb") as f:
            f.write(data)
        print("OK  ", out, len(data))
        return True
    except Exception as e:
        print("FAIL", out, e)
        return False

AEXT = "https://android.googlesource.com/platform/external/boringssl/+/"

# 1) what does crypto/ look like on main?
try:
    names = sorted(e.get("name") for e in gs_json(AEXT + "refs/heads/main/crypto/").get("entries", []))
    print("boringssl main crypto/ has", len(names), "entries")
    print([n for n in names if "spake" in n.lower() or "pake" in n.lower()] or "no spake* entries")
except Exception as e:
    print("FAIL list main crypto/", e)

# 2) probe release tags for the file (both historical layouts)
for ref in ["refs/tags/android-13.0.0_r1", "refs/heads/android11-release", "refs/tags/android-11.0.0_r1"]:
    for path, out in [
        ("crypto/spake25519/spake25519.c", "spake25519.c"),
        ("crypto/spake25519.c", "spake25519.c"),
        ("crypto/spake25519/spake25519_test.cc", "spake25519_test.cc"),
        ("crypto/spake25519/internal.h", "spake25519_internal.h"),
    ]:
        try_fetch(AEXT + ref + "/" + path, out)
