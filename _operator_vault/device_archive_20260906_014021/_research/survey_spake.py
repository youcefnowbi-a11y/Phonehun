"""Survey layouts on android13/14-release, then fetch spake25519 files."""
import base64, json, urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
ROOT = "https://android.googlesource.com/platform/external/boringssl/"

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
        return True
    except Exception as e:
        print("FAIL", out, "->", e)
        return False

for ref in ["refs/heads/android13-release", "refs/heads/android14-release"]:
    print("=== ", ref)
    for d in ["crypto/", "src/crypto/"]:
        try:
            names = sorted(e.get("name") for e in gs_json(ROOT + "+/" + ref + "/" + d).get("entries", []))
            sp = [x for x in names if "spake" in x.lower()]
            print("  ", d, "->", (sp if sp else f"no spake ({len(names)} entries)"))
            if sp:
                for f in sp:
                    if f.endswith((".c", ".cc", ".h")):
                        try_fetch(ROOT + "+/" + ref + "/" + d + f, f.replace("/", "__"))
        except Exception as e:
            print("  ", d, "listing fail:", e)
