import os
import re
import time
import shlex
import hashlib
import logging
from pathlib import Path
from config import TEMP_DIR

log = logging.getLogger(__name__)

# M6: durée de vie d'un aperçu local — au-delà, le fichier a pu changer sur
# l'appareil, on re-tire. Clé de cache = (serial, chemin) pour éviter les
# collisions multi-appareils.
_PREVIEW_TTL = 600
# H5/L13: surface d'entrée — le chemin vient du navigateur, jamais interpolé
# brut. Chasse aux métacaractères shell côté appareil + aux caractères
# illégaux NTFS (`* ? " < > |` : WinError 123 / Alternate Data Stream).
_PATH_RE = re.compile(r"[A-Za-z0-9 ._/\,\-\[\]()&#']+")


class MediaBrowser:
    def __init__(self, adb_engine):
        self.adb = adb_engine

    def _device_serial(self):
        try:
            res = self.adb.shell("getprop ro.serialno", timeout=5)
            return (res.get("stdout") or "").strip() or "unknown"
        except Exception:
            return "unknown"

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
        # L13: chemin absolu exigé — ferme la surface des flags adb
        # (un argument en tiret serait interprété par `adb pull`)
        if not isinstance(remote_path, str) or not remote_path.startswith("/"):
            return {"success": False, "error": "chemin distant invalide"}
        # H5: le chemin vient du navigateur — liste blanche stricte,
        # traversée `..` interdite, longueur plafonnée
        if len(remote_path) > 512 or not _PATH_RE.fullmatch(remote_path) \
                or any(part == ".." for part in remote_path.split("/")):
            return {"success": False, "error": "chemin distant invalide"}

        filename = Path(remote_path).name
        # H5: nom local blanchi — le filename de l'appareil n'atteint
        # jamais le système de fichiers hôte en brut
        safe_filename = re.sub(r"[^A-Za-z0-9._-]", "_", filename)[:100] or "file"
        serial = self._device_serial()
        cache_key = hashlib.md5(f"{serial}::{remote_path}".encode()).hexdigest()[:12]
        safe_name = f"preview_{cache_key}_{safe_filename}"
        local_path = TEMP_DIR / safe_name

        # M6: cache frais → touch (recyclage LRU); périmé → re-tir
        if local_path.exists():
            try:
                age = time.time() - local_path.stat().st_mtime
            except OSError:
                age = _PREVIEW_TTL + 1
            if age < _PREVIEW_TTL:
                try:
                    os.utime(local_path, None)
                except OSError:
                    pass
                return {"success": True, "local_path": str(local_path),
                        "filename": safe_name, "cached": True}
            try:
                local_path.unlink()
            except OSError:
                pass

        try:
            pull_res = self.adb.run_cmd(["pull", remote_path, str(local_path)], timeout=60)
            if not pull_res.get("success"):
                # jamais de fichier partiel qui traîne dans TEMP_DIR
                try:
                    if local_path.exists():
                        local_path.unlink()
                except OSError:
                    pass
                log.debug("fetch_preview pull échoué: %s", pull_res.get("stderr"))
                return {"success": False, "error": "pull de l'aperçu échoué"}
            return {"success": True, "local_path": str(local_path),
                    "filename": safe_name, "cached": False}
        except Exception as e:
            log.warning("fetch_preview a échoué: %s", e)
            return {"success": False, "error": "échec aperçu (voir logs)"}
