import shlex
from pathlib import Path
from config import TEMP_DIR

class SystemControls:
    def __init__(self, adb_engine):
        self.adb = adb_engine

    def take_screenshot(self):
        # BUG 5 FIX: Use a fixed filename to prevent disk accumulation
        filename = "live_screen.png"
        local_path = TEMP_DIR / filename
        
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
        res = self.adb.shell(f"input tap {int(x)} {int(y)}")
        return {"success": res["success"]}

    def swipe(self, x1, y1, x2, y2, duration=300):
        res = self.adb.shell(f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration)}")
        return {"success": res["success"]}

    def send_key(self, keycode):
        res = self.adb.shell(f"input keyevent {int(keycode)}")
        return {"success": res["success"]}

    def type_text(self, text):
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
        # Ensure lines is an integer to prevent injection
        lines = int(lines)
        cmd = f"logcat -d -t {lines} -v time"
        if filter_tag:
            cmd += f" -s {shlex.quote(filter_tag)}"
        res = self.adb.shell(cmd, timeout=15)
        return {"logs": res["stdout"] if res["success"] else res["stderr"]}
