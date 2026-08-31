"""Deep hunt: openssl headers, curve25519 dir, adb release refs."""
import base64, json, urllib.request

BSSL = "https://android.googlesource.com/platform/external/boringssl/+/refs/heads/android14-release/"
ADB = "https://android.googlesource.com/platform/packages/modules/adb/+/"

def gs_json(url):
    raw = urllib.request.urlopen(url + "?format=JSON", timeout=30).read()
    if raw.startswith(b")]}'"):
        raw = raw.split(b"\n", 1)[1]
    return json.loads(raw)

# 1) openssl headers containing spake
try:
    hdr = sorted(e.get("name") for e in gs_json(BSSL + "src/include/openssl/").get("entries", []))
    print("spake headers:", [h for h in hdr if "spake" in h.lower()] or "NONE")
    print("header count:", len(hdr))
except Exception as e:
    print("hdr fail", e)

# 2) curve25519 dir contents
for d in ["src/crypto/curve25519/"]:
    try:
        n = sorted(e.get("name") for e in gs_json(BSSL + d).get("entries", []))
        print(d, "->", n)
    except Exception as e:
        print(d, "fail", e)

# 3) adb repo refs with android releases
try:
    refs = gs_json(ADB + "+refs")
    keys = list(refs.keys())
    rel = [k for k in keys if k in ("refs/heads/android13-release", "refs/heads/android14-release",
                                     "refs/heads/android15-release", "refs/heads/android11-release",
                                     "refs/heads/android12-release")]
    print("adb release refs:", rel)
except Exception as e:
    print("adb refs fail", e)
