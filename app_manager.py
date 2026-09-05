import re
import shlex
import zipfile  # fix: split-APK bundling (item 16)
from pathlib import Path
from config import TEMP_DIR

class AppManager:
    def __init__(self, adb_engine):
        self.adb = adb_engine

    def list_apps(self, filter_type="all"):
        flag = ""
        if filter_type == "user":
            flag = "-3"
        elif filter_type == "system":
            flag = "-s"

        cmd = f"pm list packages -f {flag}"
        res = self.adb.shell(cmd, timeout=30)
        
        apps = []
        if not res["success"]:
            return {"apps": [], "error": res["stderr"]}

        for line in res["stdout"].splitlines():
            line = line.strip()
            if not line.startswith("package:"):
                continue
            
            content = line[len("package:"):]
            if not content.startswith("/"):
                continue
            if "=" in content:
                apk_path, pkg_name = content.rsplit("=", 1)
                # fix: cover all system partitions; /system already prefix-matches /system_ext (item 18)
                is_system = any(apk_path.startswith(p) for p in
                                ("/system", "/system_ext", "/product", "/vendor", "/odm", "/apex"))
                short_name = pkg_name.split(".")[-1].capitalize()
                
                apps.append({
                    "package": pkg_name,
                    "apk_path": apk_path,
                    "name": short_name,
                    "is_system": is_system
                })

        apps.sort(key=lambda x: x["package"].lower())
        return {"apps": apps, "count": len(apps)}

    def get_app_details(self, package_name):
        safe_pkg = shlex.quote(package_name)
        res = self.adb.shell(f"dumpsys package {safe_pkg}", timeout=20)
        
        details = {
            "package": package_name,
            "version_name": "Unknown",
            "version_code": "Unknown",
            "target_sdk": "Unknown",
            "first_install_time": "Unknown",
            "last_update_time": "Unknown",
            "permissions": []
        }
        
        if not res["success"]:
            return details

        text = res["stdout"]
        # fix: dumpsys exits 0 even for unknown packages — report honest failure (item 15)
        if "Unable to find package" in text:
            details["success"] = False
            details["error"] = f"Unable to find package: {package_name}"
            return details
        
        v_name = re.search(r'versionName=([^\s]+)', text)
        if v_name: details["version_name"] = v_name.group(1)
        
        v_code = re.search(r'versionCode=([^\s]+)', text)
        if v_code: details["version_code"] = v_code.group(1)
        
        t_sdk = re.search(r'targetSdk=([^\s]+)', text)
        if t_sdk: details["target_sdk"] = t_sdk.group(1)
        
        install_t = re.search(r'firstInstallTime=([^\r\n]+)', text)
        if install_t: details["first_install_time"] = install_t.group(1).strip()
        
        update_t = re.search(r'lastUpdateTime=([^\r\n]+)', text)
        if update_t: details["last_update_time"] = update_t.group(1).strip()

        perm_matches = re.findall(r'android\.permission\.[A-Z0-9_]+: granted=true', text)
        details["permissions"] = [p.split(":")[0] for p in perm_matches]

        return details

    def install_apk(self, local_apk_path):
        # APK installs come from the panel's upload convention: files under TEMP_DIR.
        apk = Path(local_apk_path).resolve()
        try:
            apk.relative_to(TEMP_DIR.resolve())
        except ValueError:
            return {"success": False, "stdout": "", "error": "APK path outside temp dir"}
        if not apk.is_file():
            return {"success": False, "stdout": "", "error": "APK file not found"}
        res = self.adb.run_cmd(["install", "-r", str(apk)], timeout=180)
        # BUG 21 FIX: Use one consistent success check
        ok = "Success" in res["stdout"]
        return {
            "success": ok,
            "stdout": res["stdout"],
            "error": res["stderr"] if not ok else None
        }

    def uninstall_app(self, package_name, keep_data=False):
        args = ["uninstall"]
        if keep_data:
            args.append("-k")
        args.append(package_name)
        res = self.adb.run_cmd(args, timeout=60)
        # BUG 21 FIX: Consistent success check
        ok = "Success" in res["stdout"]
        return {
            "success": ok,
            "error": res["stderr"] if not ok else None
        }

    def clear_app_data(self, package_name):
        safe_pkg = shlex.quote(package_name)
        res = self.adb.shell(f"pm clear {safe_pkg}")
        ok = "Success" in res["stdout"]
        return {"success": ok, "error": res["stderr"] if not ok else None}

    def force_stop(self, package_name):
        safe_pkg = shlex.quote(package_name)
        res = self.adb.shell(f"am force-stop {safe_pkg}")
        # fix: verify with pidof — honest success, stdout included (item 17)
        pid_res = self.adb.shell(f"pidof {safe_pkg}")
        ok = res["success"] and not (pid_res.get("stdout") or "").strip()
        return {"success": ok, "stdout": res.get("stdout") or ""}

    def launch_app(self, package_name):
        safe_pkg = shlex.quote(package_name)
        res = self.adb.shell(f"monkey -p {safe_pkg} -c android.intent.category.LAUNCHER 1")
        # fix: include stdout so callers can see monkey's verdict (item 17)
        return {"success": res["success"], "stdout": res.get("stdout") or ""}

    def extract_apk(self, package_name):
        if not re.fullmatch(r"[A-Za-z0-9._-]+", package_name):
            return {"success": False, "error": "Invalid package name"}
        safe_pkg = shlex.quote(package_name)
        res = self.adb.shell(f"pm path {safe_pkg}")
        if not res["success"] or not res["stdout"]:
            return {"success": False, "error": "Could not locate APK path on device"}

        # fix: split APKs return one package: line per slice — collect them all (item 16)
        remote_apks = []
        for apk_line in res["stdout"].splitlines():
            remote = apk_line.replace("package:", "").strip()
            if remote.startswith("/") and ".." not in remote.split("/"):
                remote_apks.append(remote)
        if not remote_apks:
            return {"success": False, "error": "Invalid APK path reported by device"}

        if len(remote_apks) > 1:
            # fix: pull every split slice, zip into one archive next to the base (item 16)
            pulled = []
            for i, remote_apk in enumerate(remote_apks):
                slice_dest = TEMP_DIR / f"{package_name}_{i}_{Path(remote_apk).name}"
                slice_res = self.adb.run_cmd(["pull", remote_apk, str(slice_dest)], timeout=120)
                if slice_res["success"] and slice_dest.is_file():
                    pulled.append(slice_dest)
            if len(pulled) != len(remote_apks):
                for leftover in pulled:
                    try:
                        leftover.unlink()
                    except OSError:
                        pass
                return {"success": False, "error": "Could not pull all split APK slices"}
            zip_dest = TEMP_DIR / f"{package_name}.zip"
            with zipfile.ZipFile(zip_dest, "w", zipfile.ZIP_DEFLATED) as zf:
                for local_slice in pulled:
                    zf.write(local_slice, arcname=local_slice.name)
            # fix: slices live inside the zip now — remove the loose copies (item 16)
            for local_slice in pulled:
                try:
                    local_slice.unlink()
                except OSError:
                    pass
            return {
                "success": True,
                "local_path": str(zip_dest),
                "filename": zip_dest.name,
                "error": None
            }

        remote_apk = remote_apks[0]
        local_dest = TEMP_DIR / f"{package_name}.apk"
        pull_res = self.adb.run_cmd(["pull", remote_apk, str(local_dest)], timeout=120)
        return {
            "success": pull_res["success"],
            "local_path": str(local_dest),
            "filename": f"{package_name}.apk",
            "error": pull_res["stderr"] if not pull_res["success"] else None
        }
