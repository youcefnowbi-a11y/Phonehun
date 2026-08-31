"""Deep tree walk: full root listing + candidate dirs + adb_wifi.h."""
import base64, json, urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
os.makedirs(OUT, exist_ok=True)
BASE = "https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/"

def gs_json(path):
    raw = urllib.request.urlopen(BASE + path + "?format=JSON", timeout=30).read()
    if raw.startswith(b")]}'"):
        raw = raw.split(b"\n", 1)[1]
    return json.loads(raw)

def save_gs(path, name=None):
    data = base64.b64decode(urllib.request.urlopen(BASE + path + "?format=TEXT", timeout=30).read())
    fn = name or path.replace("/", "__")
    with open(os.path.join(OUT, fn), "wb") as f:
        f.write(data)
    print("OK  ", path, len(data))

for d in ["", "client/", "daemon/"]:
    try:
        entries = gs_json(d)
        names = sorted(e.get("name") for e in entries.get("entries", []))
        interesting = [n for n in names if any(k in n.lower() for k in
                       ["pair", "tls", "wifi", "mdns", "crypto", "auth", "include", "daemon"])]
        print("TREE", repr(d), len(names), "entries")
        print("      interesting:", interesting)
        print("      all:", names if d == "" else "(suppressed)")
    except Exception as e:
        print("FAIL TREE", repr(d), e)

for p in ["adb_wifi.h", "adb_mdns.h"]:
    try:
        save_gs(p)
    except Exception as e:
        print("FAIL", p, e)
