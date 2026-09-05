"""Check android14-release: spake2.h existence, full crypto listing, adb pairing_auth."""
import base64, json, urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
BSSL = "https://android.googlesource.com/platform/external/boringssl/+/refs/heads/android14-release/"
ADB = "https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/android14-release/"

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
        print("OK  ", out, len(data), "bytes")
    except Exception as e:
        print("FAIL", out, "->", e)

# 1) does openssl/spake2.h exist on android14 pin?
try_fetch(BSSL + "src/include/openssl/spake2.h", "bssl14_spake2.h")

# 2) full crypto listing for eyeballing
try:
    names = sorted(e.get("name") for e in gs_json(BSSL + "src/crypto/").get("entries", []))
    print("android14 src/crypto/ ALL:", names)
except Exception as e:
    print("list fail", e)

# 3) android14-release adb pairing sources (what phones actually run)
for p, out in [
    ("pairing_auth/pairing_auth.cpp", "adb14_pairing_auth.cpp"),
    ("pairing_auth/include/adb/pairing/pairing_auth.h", "adb14_pairing_auth.h"),
    ("pairing_connection/pairing_connection.cpp", "adb14_pairing_connection.cpp"),
]:
    try_fetch(ADB + p + "?format=TEXT", out)
