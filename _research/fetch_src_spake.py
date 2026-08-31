"""Fetch spake25519 from external/boringssl/src + revision pin."""
import base64, json, urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
base = "https://android.googlesource.com/platform/external/boringssl/+/refs/heads/main/"

def gs_json(url):
    raw = urllib.request.urlopen(url + "?format=JSON", timeout=30).read()
    if raw.startswith(b")]}'"):
        raw = raw.split(b"\n", 1)[1]
    return json.loads(raw)

def fetch_text(url, out):
    data = base64.b64decode(urllib.request.urlopen(url + "?format=TEXT", timeout=30).read())
    with open(os.path.join(OUT, out), "wb") as f:
        f.write(data)
    print("OK  ", out, len(data))

try:
    rev = urllib.request.urlopen(base + "BORINGSSL_REVISION?format=TEXT", timeout=30).read()
    print("PINNED REVISION:", base64.b64decode(rev).decode(errors="replace").strip())
except Exception as e:
    print("rev fail", e)

try:
    n = sorted(e.get("name") for e in gs_json(base + "src/crypto/").get("entries", []))
    print("src/crypto/ count:", len(n))
    print("spake-ish:", [x for x in n if "spake" in x.lower()] or "none")
except Exception as e:
    print("list fail", e)

for path, out in [
    ("src/crypto/spake25519/spake25519.c", "spake25519.c"),
    ("src/crypto/spake25519/spake25519_test.cc", "spake25519_test.cc"),
    ("src/crypto/spake25519/internal.h", "spake25519_internal.h"),
    ("src/include/openssl/spake2.h", "spake2.h"),
]:
    try:
        fetch_text(base + path, out)
    except Exception as e:
        print("FAIL", out, e)
