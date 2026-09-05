import shlex
import time
import uuid
from pathlib import Path
from config import TEMP_DIR


def _to_int(v, default, lo=None, hi=None):
    # fix: guarded cast — app-layer garbage ("abc", None, 10**12) never
    # reaches the f-string shell command (item 31)
    try:
        n = int(v)
    except (TypeError, ValueError):
        return default
    if lo is not None and n < lo:
        return lo
    if hi is not None and n > hi:
        return hi
    return n

class SystemControls:
    def __init__(self, adb_engine):
        self.adb = adb_engine

    def take_screenshot(self):
        # fix: per-call uuid filename — the fixed "live_screen.png" made
        # concurrent viewers race on one path; a 5-min reap keeps the original
        # no-disk-accumulation goal (item 30)
        filename = f"live_screen_{uuid.uuid4().hex[:8]}.png"
        local_path = TEMP_DIR / filename

        try:
            cutoff = time.time() - 300
            for old in TEMP_DIR.glob("live_screen_*.png"):
                try:
                    if old.is_file() and old.stat().st_mtime < cutoff:
                        old.unlink()
                except OSError:
                    pass
        except OSError:
            pass

        res = self.adb.run_binary_cmd(["exec-out", "screencap", "-p"], timeout=15)
        if res["success"] and len(res["stdout"]) > 100:
            with open(local_path, "wb") as f:
                f.write(res["stdout"])
            return {"success": True, "filename": filename, "local_path": str(local_path)}
        else:
            # Fallback to file pull
            remote_tmp = "/sdcard/screenshot_tmp.png"
            self.adb.shell(f"screencap -p {remote_tmp}")
            pull_res = self.adb.run_cmd(["pull", remote_tmp, str(local_path)])
            self.adb.shell(f"rm {remote_tmp}")
            return {"success": pull_res["success"], "filename": filename, "local_path": str(local_path)}

    def tap(self, x, y):
        res = self.adb.shell(f"input tap {_to_int(x, 0, 0, 100000)} {_to_int(y, 0, 0, 100000)}")
        return {"success": res["success"]}

    def swipe(self, x1, y1, x2, y2, duration=300):
        res = self.adb.shell(f"input swipe {_to_int(x1, 0, 0, 100000)} {_to_int(y1, 0, 0, 100000)} "
                             f"{_to_int(x2, 0, 0, 100000)} {_to_int(y2, 0, 0, 100000)} {_to_int(duration, 300, 0, 60000)}")
        return {"success": res["success"]}

    def send_key(self, keycode):
        res = self.adb.shell(f"input keyevent {_to_int(keycode, 0, 0, 300)}")
        return {"success": res["success"]}

    def type_text(self, text):
        # fix: None/absent text no longer raises AttributeError mid-request (item 32)
        text = text if isinstance(text, str) else ""
        if not text:
            return {"success": False, "error": "texte vide"}
        # BUG 4 FIX: Android `input text` uses %s for space.
        # Build the escaped string directly without shlex.quote wrapping.
        escaped = text.replace("\\", "\\\\")
        escaped = escaped.replace("'", "\\'")
        escaped = escaped.replace('"', '\\"')
        escaped = escaped.replace("&", "\\&")
        escaped = escaped.replace(";", "\\;")
        escaped = escaped.replace("(", "\\(")
        escaped = escaped.replace(")", "\\)")
        escaped = escaped.replace("|", "\\|")
        escaped = escaped.replace("<", "\\<")
        escaped = escaped.replace(">", "\\>")
        escaped = escaped.replace("`", "\\`")
        escaped = escaped.replace("$", "\\$")
        escaped = escaped.replace(" ", "%s")
        res = self.adb.shell(f"input text {escaped}")
        return {"success": res["success"]}

    def open_url(self, url):
        # fix: None/empty URL → clean failure shape instead of TypeError (item 33)
        url = str(url).strip() if isinstance(url, str) else ""
        if not url:
            return {"success": False, "error": "URL vide"}
        safe_url = shlex.quote(url)
        res = self.adb.shell(f"am start -a android.intent.action.VIEW -d {safe_url}")
        return {"success": res["success"]}

    def reboot(self, mode="normal"):
        if mode == "recovery":
            res = self.adb.run_cmd(["reboot", "recovery"])
        elif mode == "bootloader":
            res = self.adb.run_cmd(["reboot", "bootloader"])
        else:
            res = self.adb.run_cmd(["reboot"])
        return {"success": res["success"]}

    def get_logcat(self, lines=150, filter_tag=None):
        # fix: guarded cast — bad lines values clamp instead of raising (item 31)
        lines = _to_int(lines, 150, 1, 10000)
        cmd = f"logcat -d -t {lines} -v time"
        if filter_tag:
            cmd += f" -s {shlex.quote(filter_tag)}"
        res = self.adb.shell(cmd, timeout=15)
        return {"logs": res["stdout"] if res["success"] else res["stderr"]}
