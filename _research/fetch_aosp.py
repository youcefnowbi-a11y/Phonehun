"""Fetch AOSP pairing protocol source + RFC 9382 (SPAKE2+) test vectors."""
import base64, urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
os.makedirs(OUT, exist_ok=True)
BASE = "https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/"
PATHS = [
    "libs/adb_pairing/pairing_auth.cpp",
    "libs/adb_pairing/pairing_auth.h",
    "libs/adb_pairing/pairing_connection.cpp",
    "libs/adb_pairing/pairing_connection.h",
    "include/adb/pairing/pairing_auth.h",
    "include/adb/pairing/pairing_connection.h",
    "libs/adb_pairing/pairing_exit_codes.h",
]
for p in PATHS:
    url = BASE + p + "?format=TEXT"
    try:
        raw = urllib.request.urlopen(url, timeout=30).read()
        data = base64.b64decode(raw)
        name = p.replace("/", "__")
        with open(os.path.join(OUT, name), "wb") as f:
            f.write(data)
        print("OK  ", p, len(data), "bytes")
    except Exception as e:
        print("FAIL", p, e)

try:
    rfc = urllib.request.urlopen("https://www.rfc-editor.org/rfc/rfc9382.txt", timeout=30).read()
    with open(os.path.join(OUT, "rfc9382.txt"), "wb") as f:
        f.write(rfc)
    print("OK   rfc9382.txt", len(rfc), "bytes")
except Exception as e:
    print("FAIL rfc9382", e)
