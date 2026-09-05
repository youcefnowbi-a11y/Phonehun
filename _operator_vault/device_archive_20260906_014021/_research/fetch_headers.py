"""Fetch headers + proto (final round)."""
import base64, urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
BASE = "https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/"
PATHS = [
    "pairing_auth/include/adb/pairing/pairing_auth.h",
    "pairing_connection/include/adb/pairing/pairing_connection.h",
    "proto/pairing.proto",
    "pairing_auth/aes_128_gcm.cpp",
    "pairing_auth/include/adb/pairing/aes_128_gcm.h",
]
for p in PATHS:
    try:
        data = base64.b64decode(urllib.request.urlopen(BASE + p + "?format=TEXT", timeout=30).read())
        with open(os.path.join(OUT, p.replace("/", "__")), "wb") as f:
            f.write(data)
        print("OK  ", p, len(data))
    except Exception as e:
        print("FAIL", p, e)
