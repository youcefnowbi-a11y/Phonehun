"""List external/boringssl refs, then fetch spake25519 from a release branch."""
import base64, json, urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
ROOT = "https://android.googlesource.com/platform/external/boringssl/"

def gs_json(url):
    raw = urllib.request.urlopen(url + "?format=JSON", timeout=30).read()
    if raw.startswith(b")]}'"):
        raw = raw.split(b"\n", 1)[1]
    return json.loads(raw)

def fetch_text(url, out):
    data = base64.b64decode(urllib.request.urlopen(url + "?format=TEXT", timeout=30).read())
    with open(os.path.join(OUT, out), "wb") as f:
        f.write(data)
    print("OK  ", out, len(data), "bytes")
    return True

# 1) list refs
refs = None
try:
    refs = gs_json(ROOT + "+refs")
    keys = list(refs.keys()) if isinstance(refs, dict) else refs
    rel = [k for k in keys if "release" in k or k.startswith("refs/tags/android-1")]
    print("release-ish refs:", rel[:30])
except Exception as e:
    print("refs fail", e)

# 2) candidate refs, newest-first for phone realism (Android 14/15 era pins)
candidates = []
if refs:
    for k in refs:
        kk = k if k.startswith("refs/") else k
        if any(t in k for t in ["android14-release", "android13-release", "android15-release"]):
            candidates.append(kk)
print("trying:", candidates[:4])

for ref in candidates[:4] or ["refs/heads/android14-release"]:
    for layout in ["src/crypto/spake25519/spake25519.c", "crypto/spake25519/spake25519.c"]:
        url = ROOT + "+/" + ref + "/" + layout
        out = "spake25519_" + ref.split("/")[-1] + ".c"
        if fetch_text(url, out):
            try:
                t = urllib.request.urlopen(ROOT + "+/" + ref + "/crypto/spake25519/spake25519_test.cc?format=TEXT", timeout=30)
                data = base64.b64decode(t.read())
                open(os.path.join(OUT, "spake25519_test.cc"), "wb").write(data)
                print("OK   spake25519_test.cc", len(data))
            except Exception as e:
                print("no test file at", ref, e)
            break
