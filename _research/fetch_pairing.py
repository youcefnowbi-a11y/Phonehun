"""Fetch the complete pairing protocol source set."""
import base64, urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
os.makedirs(OUT, exist_ok=True)
BASE = "https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/"

PATHS = [
    "pairing_auth/pairing_auth.cpp",
    "pairing_auth/pairing_auth.h",
    "pairing_connection/pairing_connection.cpp",
    "pairing_connection/pairing_connection.h",
    "client/pairing/pairing_client.cpp",
    "client/pairing/pairing_client.h",
    "proto/pairing_proto.proto",
    "tls/tls.h",
    "daemon/adb_wifi.cpp",
]

def list_dir(d):
    raw = urllib.request.urlopen(BASE + d + "?format=JSON", timeout=30).read()
    if raw.startswith(b")]}'"):
        raw = raw.split(b"\n", 1)[1]
    import json
    return [e.get("name") for e in json.loads(raw).get("entries", [])]

print("proto/:", list_dir("proto/"))
print("crypto/:", list_dir("crypto/"))
print("pairing_auth/:", list_dir("pairing_auth/"))

for p in PATHS:
    try:
        data = base64.b64decode(urllib.request.urlopen(BASE + p + "?format=TEXT", timeout=30).read())
        with open(os.path.join(OUT, p.replace("/", "__")), "wb") as f:
            f.write(data)
        print("OK  ", p, len(data))
    except Exception as e:
        print("FAIL", p, e)
