"""Locate pairing sources: walk googlesource tree JSON + try github mirror raw paths."""
import base64, json, urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
os.makedirs(OUT, exist_ok=True)

def gs_json(path):
    url = "https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/" + path + "?format=JSON"
    raw = urllib.request.urlopen(url, timeout=30).read()
    if raw.startswith(b")]}'"):
        raw = raw.split(b"\n", 1)[1]
    return json.loads(raw)

def save_gs(path, name=None):
    url = "https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/" + path + "?format=TEXT"
    data = base64.b64decode(urllib.request.urlopen(url, timeout=30).read())
    fn = name or path.replace("/", "__")
    with open(os.path.join(OUT, fn), "wb") as f:
        f.write(data)
    print("OK  ", path, len(data))
    return True

def gh_raw(path, out):
    url = "https://raw.githubusercontent.com/aosp-mirror/platform_system_core/master/" + path
    data = urllib.request.urlopen(url, timeout=30).read()
    with open(os.path.join(OUT, out), "wb") as f:
        f.write(data)
    print("OK  GH", path, len(data))
    return True

# 1) github mirror, old-but-known location
for src, out in [
    ("adb/libs/adb_pairing/pairing_auth.cpp", "pairing_auth.cpp"),
    ("adb/libs/adb_pairing/pairing_auth.h", "pairing_auth.h"),
    ("adb/libs/adb_pairing/pairing_connection.cpp", "pairing_connection.cpp"),
    ("adb/libs/adb_pairing/pairing_connection.h", "pairing_connection.h"),
    ("adb/include/adb/pairing/pairing_auth.h", "include_pairing_auth.h"),
    ("adb/include/adb/pairing/pairing_connection.h", "include_pairing_connection.h"),
]:
    try:
        gh_raw(src, out)
    except Exception as e:
        print("FAIL GH", src, e)

# 2) googlesource tree listing to find current layout
for d in ["", "libs/", "libs/adb_pairing/", "include/adb/"]:
    try:
        entries = gs_json(d)
        names = [e.get("name") for e in entries.get("entries", [])]
        print("TREE", repr(d), "->", names[:40])
    except Exception as e:
        print("FAIL TREE", repr(d), e)
