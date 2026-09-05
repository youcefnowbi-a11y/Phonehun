import re
import shlex
from pathlib import Path
from config import TEMP_DIR

# BUG 7 FIX: Regex-based ls -la parser that handles filenames with spaces
LS_LINE_RE = re.compile(
    r'^([dlrwxsStT\-]{10})\s+'   # permissions
    r'(\d+)\s+'                   # link count
    r'(\S+)\s+'                   # owner
    r'(\S+)\s+'                   # group
    r'([\d,]+(?:,\s*\d+)?)\s+'   # fix: size — /dev device nodes carry "major, minor" (item 14)
    r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s+'  # date time
    r'(.+)$'                      # name (may contain spaces, arrows for symlinks)
)

class FileManager:
    def __init__(self, adb_engine):
        self.adb = adb_engine

    def list_dir(self, remote_path="/sdcard"):
        if not remote_path:
            remote_path = "/sdcard"
        remote_path = remote_path.replace("\\", "/")
        if not remote_path.startswith("/"):
            remote_path = "/" + remote_path

        target_dir = remote_path.rstrip("/") + "/"
        safe_path = shlex.quote(target_dir)

        res = self.adb.shell(f"ls -la {safe_path}")
        
        items = []
        if not res["success"] and not res["stdout"]:
            # fix: shared payload shape — error payloads carry the same keys (item 13)
            return {"path": remote_path, "parent_path": None, "items": [],
                    "count": 0, "error": res["stderr"] or "Cannot access directory"}

        lines = res["stdout"].splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("total "):
                continue

            m = LS_LINE_RE.match(line)
            if not m:
                continue

            perms = m.group(1)
            size_field = m.group(5)
            # fix: device-node sizes are "major, minor", not bytes (item 14)
            try:
                size_bytes = 0 if "," in size_field else int(size_field)
            except ValueError:
                size_bytes = 0
            name_field = m.group(7)

            is_dir = perms.startswith("d")
            is_link = perms.startswith("l")

            # Parse symlink target
            link_target = None
            name = name_field
            if is_link and " -> " in name_field:
                name, link_target = name_field.split(" -> ", 1)

            if name in [".", ".."]:
                continue

            item_path = f"{remote_path.rstrip('/')}/{name}"
            ext = Path(name).suffix.lower().lstrip(".")

            # BUG 6 FIX: Don't guess symlink type from name heuristic.
            # Mark symlinks as their own thing; frontend treats them as navigable.
            items.append({
                "name": name,
                "path": item_path,
                "is_dir": is_dir,
                "is_link": is_link,
                "link_target": link_target,
                "size_bytes": size_bytes,
                "size_formatted": self.format_size(size_bytes),
                "permissions": perms,
                "extension": ext,
            })

        # Sort: directories first, then links, then files; alphabetical within
        items.sort(key=lambda x: (not x["is_dir"], not x["is_link"], x["name"].lower()))

        parent_path = str(Path(remote_path).parent).replace("\\", "/")
        if parent_path == remote_path or remote_path == "/":
            parent_path = None

        return {
            "path": remote_path,
            "parent_path": parent_path,
            "items": items,
            "count": len(items),
            "error": None  # fix: shared payload shape, error None on success (item 13)
        }

    def pull_file(self, remote_path, local_dest=None):
        if not local_dest:
            filename = Path(remote_path).name
            local_dest = TEMP_DIR / filename
        else:
            local_dest = Path(local_dest)

        res = self.adb.run_cmd(["pull", remote_path, str(local_dest)], timeout=120)
        return {
            "success": res["success"],
            "local_path": str(local_dest),
            "error": res["stderr"] if not res["success"] else None
        }

    def push_file(self, local_path, remote_path):
        res = self.adb.run_cmd(["push", str(local_path), remote_path], timeout=120)
        return {
            "success": res["success"],
            "remote_path": remote_path,
            "error": res["stderr"] if not res["success"] else None
        }

    def delete_item(self, remote_path):
        safe_path = shlex.quote(remote_path)
        res = self.adb.shell(f"rm -rf {safe_path}")
        return {"success": res["success"], "error": res["stderr"] if not res["success"] else None}

    def make_dir(self, remote_path):
        safe_path = shlex.quote(remote_path)
        res = self.adb.shell(f"mkdir -p {safe_path}")
        return {"success": res["success"], "error": res["stderr"] if not res["success"] else None}

    def rename_item(self, old_path, new_path):
        safe_old = shlex.quote(old_path)
        safe_new = shlex.quote(new_path)
        res = self.adb.shell(f"mv {safe_old} {safe_new}")
        return {"success": res["success"], "error": res["stderr"] if not res["success"] else None}

    def read_text_file(self, remote_path, max_lines=500):
        safe_path = shlex.quote(remote_path)
        res = self.adb.shell(f"head -n {max_lines} {safe_path}")
        return {
            "success": res["success"],
            "content": res["stdout"],
            "error": res["stderr"] if not res["success"] else None
        }

    def search(self, remote_path="/sdcard", query=""):
        if not query:
            # fix: shared payload shape (item 13)
            return {"items": [], "count": 0, "parent_path": None, "error": None}
        safe_path = shlex.quote(remote_path)
        safe_query = shlex.quote(f"*{query}*")
        # fix: -type f so results are truly files (item 12)
        res = self.adb.shell(f"find {safe_path} -type f -iname {safe_query} -maxdepth 5 2>/dev/null | head -n 100", timeout=30)

        results = []
        if res["success"]:
            for line in res["stdout"].splitlines():
                p = line.strip()
                if p:
                    results.append({
                        "name": Path(p).name,
                        "path": p,
                        "is_dir": False
                    })
            # fix: shared payload shape (item 13)
            return {"items": results, "count": len(results), "parent_path": None, "error": None}
        # fix: honest failure instead of silent empty success (item 12)
        return {"items": [], "count": 0, "parent_path": None, "error": res.get("stderr")}

    @staticmethod
    def format_size(bytes_val):
        if not bytes_val or bytes_val <= 0:
            return "0 B"
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if bytes_val < 1024.0:
                return f"{bytes_val:.1f} {unit}" if unit != "B" else f"{int(bytes_val)} B"
            bytes_val /= 1024.0
        return f"{bytes_val:.1f} PB"
