"""Route inventory — every capability the panel exposes (scratch, safe to delete)."""
import re
import pathlib

BASE = pathlib.Path(__file__).resolve().parent
FILES = ["app.py", "panopticon/screen_console.py", "panopticon/geo_tri.py",
         "skeleton/pin_siege.py", "skeleton/neutralizer.py",
         "skeleton/cred_harvester.py", "ghost/pipeline.py", "agent_relay.py"]

PAT = re.compile(r'@(\w+)\.route\("([^"]+)"(?:,\s*methods=\[([^\]]+)\])?\)')

for f in FILES:
    p = BASE / f
    if not p.exists():
        continue
    routes = PAT.findall(p.read_text(encoding="utf-8"))
    if routes:
        print("==", f)
        for bp, r, m in routes:
            methods = (m or "GET").replace("'", "").strip()
            print(f"  {methods:12s} {r}")
