import shlex
import hashlib
from pathlib import Path
from config import TEMP_DIR

class MediaBrowser:
    def __init__(self, adb_engine):
        self.adb = adb_engine

    def get_media(self, media_type="photos"):
        extensions = {
            "photos": [".jpg", ".jpeg", ".png", ".webp", ".gif", ".heic"],
            "videos": [".mp4", ".mkv", ".3gp", ".mov", ".webm", ".avi"],
            "audio": [".mp3", ".m4a", ".aac", ".wav", ".ogg", ".flac"],
            "downloads": []
        }

        search_dirs = {
            "photos": ["/sdcard/DCIM", "/sdcard/Pictures", "/sdcard/Download"],
            "videos": ["/sdcard/DCIM", "/sdcard/Movies", "/sdcard/Pictures", "/sdcard/Download"],
            "audio": ["/sdcard/Music", "/sdcard/Audio", "/sdcard/Podcasts", "/sdcard/Download", "/sdcard/Notifications"],
            "downloads": ["/sdcard/Download"]
        }

        target_dirs = search_dirs.get(media_type, ["/sdcard/DCIM"])
        target_exts = extensions.get(media_type, [])

        items = []
        for sdir in target_dirs:
            safe_dir = shlex.quote(sdir)
            cmd = f"find {safe_dir} -maxdepth 4 -type f 2>/dev/null | head -n 250"
            res = self.adb.shell(cmd, timeout=20)
            if not res["success"]:
                continue

            for line in res["stdout"].splitlines():
                path = line.strip()
                if not path:
                    continue
                ext = Path(path).suffix.lower()
                
                if media_type == "downloads" or ext in target_exts:
                    items.append({
                        "name": Path(path).name,
                        "path": path,
                        "extension": ext.lstrip("."),
                        "type": media_type
                    })

        return {"items": items, "count": len(items)}

    def fetch_preview(self, remote_path):
        filename = Path(remote_path).name
        safe_name = f"preview_{hashlib.md5(remote_path.encode()).hexdigest()[:12]}_{filename}"
        local_path = TEMP_DIR / safe_name
        
        if not local_path.exists():
            pull_res = self.adb.run_cmd(["pull", remote_path, str(local_path)], timeout=60)
            if not pull_res["success"]:
                return {"success": False, "error": pull_res["stderr"]}

        return {
            "success": True,
            "local_path": str(local_path),
            "filename": safe_name
        }
