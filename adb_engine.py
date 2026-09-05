import subprocess
import re
from config import ADB_PATH

class ADBEngine:
    def __init__(self, adb_path=ADB_PATH):
        self.adb_path = adb_path

    def _serial_prefix(self, serial=None):
        """Device-targeting prefix; None = whatever adb picks (legacy single-device)."""
        return ["-s", serial] if serial else []

    def run_cmd(self, args, timeout=30, serial=None):
        cmd = [self.adb_path] + self._serial_prefix(serial) + args
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout
            )
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout.strip(),
                "stderr": res.stderr.strip(),
                "returncode": res.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": "", "stderr": "Command timed out", "returncode": -1}
        except Exception as e:
            return {"success": False, "stdout": "", "stderr": str(e), "returncode": -1}

    def run_binary_cmd(self, args, timeout=30, serial=None):
        cmd = [self.adb_path] + self._serial_prefix(serial) + args
        try:
            res = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout
            )
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout,
                "stderr": res.stderr.decode("utf-8", errors="replace"),
                "returncode": res.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "stdout": b"", "stderr": "Command timed out", "returncode": -1}
        except Exception as e:
            return {"success": False, "stdout": b"", "stderr": str(e), "returncode": -1}

    def shell(self, command, timeout=30, serial=None):
        args = self._serial_prefix(serial) + ["shell", command]
        return self.run_cmd(args, timeout=timeout)

    def get_devices(self):
        res = self.run_cmd(["devices", "-l"])
        devices = []
        if not res["success"]:
            return devices

        for line in res["stdout"].splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                status = parts[1]
                extra = " ".join(parts[2:])
                
                model_match = re.search(r'model:([^\s]+)', extra)
                device_match = re.search(r'device:([^\s]+)', extra)
                model = model_match.group(1) if model_match else ""
                device_name = device_match.group(1) if device_match else ""

                devices.append({
                    "serial": serial,
                    "status": status,
                    "model": model,
                    "device": device_name,
                    "raw": line
                })
        return devices

    def get_device_info(self):
        info = {
            "model": "Unknown",
            "manufacturer": "Unknown",
            "brand": "Unknown",
            "android_version": "Unknown",
            "sdk_version": "Unknown",
            "cpu_abi": "Unknown",
            "serial": "Unknown",
            "security_patch": "Unknown",
            "screen_res": "Unknown",
            "screen_density": "Unknown",
            "uptime": "Unknown",
            "hostname": "Unknown",
        }
        
        # BUG 17 FIX: Use a unique separator instead of '---'
        sep = "<<<DROIDCMD_SEP>>>"
        props_cmd = (
            f"getprop ro.product.model; echo '{sep}';"
            f"getprop ro.product.manufacturer; echo '{sep}';"
            f"getprop ro.product.brand; echo '{sep}';"
            f"getprop ro.build.version.release; echo '{sep}';"
            f"getprop ro.build.version.sdk; echo '{sep}';"
            f"getprop ro.product.cpu.abi; echo '{sep}';"
            f"getprop ro.serialno; echo '{sep}';"
            f"getprop ro.build.version.security_patch; echo '{sep}';"
            f"wm size; echo '{sep}';"
            f"wm density; echo '{sep}';"
            f"uptime"
        )
        res = self.shell(props_cmd)
        if res["success"]:
            blocks = [b.strip() for b in res["stdout"].split(sep)]
            if len(blocks) >= 11:
                info["model"] = blocks[0] or "Unknown"
                info["manufacturer"] = blocks[1] or "Unknown"
                info["brand"] = blocks[2] or "Unknown"
                info["android_version"] = blocks[3] or "Unknown"
                info["sdk_version"] = blocks[4] or "Unknown"
                info["cpu_abi"] = blocks[5] or "Unknown"
                info["serial"] = blocks[6] or "Unknown"
                info["security_patch"] = blocks[7] or "Unknown"
                
                wm_size = blocks[8]
                m_size = re.search(r'Physical size:\s*([0-9x]+)', wm_size)
                info["screen_res"] = m_size.group(1) if m_size else wm_size
                
                wm_density = blocks[9]
                m_den = re.search(r'Physical density:\s*([0-9]+)', wm_density)
                info["screen_density"] = m_den.group(1) if m_den else wm_density
                
                info["uptime"] = blocks[10]

        return info

    def get_battery_info(self):
        res = self.shell("dumpsys battery")
        battery = {
            "level": 0,
            "scale": 100,
            "status": "Unknown",
            "health": "Good",
            "voltage_mv": 0,
            "temperature_c": 0,
            "technology": "Li-ion",
            "plugged": "Unplugged"
        }
        if not res["success"]:
            return battery

        status_map = {1: "Unknown", 2: "Charging", 3: "Discharging", 4: "Not Charging", 5: "Full"}
        health_map = {1: "Unknown", 2: "Good", 3: "Overheat", 4: "Dead", 5: "Over Voltage", 6: "Unspecified Failure", 7: "Cold"}

        # BUG 8 FIX: Track plugged source with priority, only set once
        plugged_set = False
        for line in res["stdout"].splitlines():
            line = line.strip()
            if ":" in line:
                key, val = [x.strip() for x in line.split(":", 1)]
                if key == "level":
                    battery["level"] = int(val) if val.isdigit() else 0
                elif key == "scale":
                    battery["scale"] = int(val) if val.isdigit() else 100
                elif key == "status":
                    code = int(val) if val.isdigit() else 1
                    battery["status"] = status_map.get(code, "Unknown")
                elif key == "health":
                    code = int(val) if val.isdigit() else 2
                    battery["health"] = health_map.get(code, "Good")
                elif key == "voltage":
                    battery["voltage_mv"] = int(val) if val.isdigit() else 0
                elif key == "temperature":
                    raw_temp = int(val) if val.isdigit() else 0
                    battery["temperature_c"] = round(raw_temp / 10.0, 1)
                elif key == "technology":
                    battery["technology"] = val
                elif not plugged_set and key == "AC powered" and val.lower() == "true":
                    battery["plugged"] = "AC Charger"
                    plugged_set = True
                elif not plugged_set and key == "USB powered" and val.lower() == "true":
                    battery["plugged"] = "USB Cable"
                    plugged_set = True
                elif not plugged_set and key == "Wireless powered" and val.lower() == "true":
                    battery["plugged"] = "Wireless"
                    plugged_set = True
                    
        return battery

    def get_storage_info(self):
        res = self.shell("df -h /data /sdcard /storage/emulated/0")
        storages = []
        if res["success"]:
            lines = res["stdout"].splitlines()
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 6:
                    storages.append({
                        "filesystem": parts[0],
                        "size": parts[1],
                        "used": parts[2],
                        "avail": parts[3],
                        "use_pct": parts[4],
                        "mounted": parts[5]
                    })
        return storages

    def get_memory_info(self):
        res = self.shell("cat /proc/meminfo")
        # BUG 19 FIX: Initialize all keys the frontend expects
        mem = {"total_mb": 0, "free_mb": 0, "available_mb": 0, "used_mb": 0, "used_pct": 0}
        if res["success"]:
            for line in res["stdout"].splitlines():
                if "MemTotal:" in line:
                    val = re.search(r'(\d+)', line)
                    if val: mem["total_mb"] = round(int(val.group(1)) / 1024, 1)
                elif "MemFree:" in line:
                    val = re.search(r'(\d+)', line)
                    if val: mem["free_mb"] = round(int(val.group(1)) / 1024, 1)
                elif "MemAvailable:" in line:
                    val = re.search(r'(\d+)', line)
                    if val: mem["available_mb"] = round(int(val.group(1)) / 1024, 1)
            mem["used_mb"] = round(mem["total_mb"] - mem["available_mb"], 1)
            if mem["total_mb"] > 0:
                mem["used_pct"] = round((mem["used_mb"] / mem["total_mb"]) * 100, 1)
        return mem
