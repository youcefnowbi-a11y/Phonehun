import shlex
import re
import uuid
from pathlib import Path
from flask import request
from config import TEMP_DIR

class ToolkitManager:
    """
    Advanced Android Power Toolkit integrated from LockKnife & Android_Hacking collections.
    Provides forensic extraction, security & lock audits, debloater, hardware diagnostics,
    live screen recording, Frida script generator, and build.prop performance tweaks.
    """
    def __init__(self, adb_engine):
        self.adb = adb_engine

    # ==================== 1. SECURITY & LOCK AUDIT ====================
    def get_security_status(self):
        """
        Inspect root access, Knox warranty bits, SELinux enforcement, FRP partition,
        encryption state, keyguard lock state, and build tags.
        """
        # Root status test
        su_check = self.adb.shell("which su; id")
        is_rooted = ("uid=0(root)" in su_check.get("stdout", "") or 
                     "/su" in su_check.get("stdout", "") or 
                     "/magisk" in su_check.get("stdout", ""))

        # Knox & Bootloader state
        props_cmd = (
            "getprop ro.crypto.state; echo '<<<SEP>>>';"
            "getprop ro.crypto.type; echo '<<<SEP>>>';"
            "getprop ro.boot.warranty_bit; echo '<<<SEP>>>';"
            "getprop ro.boot.flash.locked; echo '<<<SEP>>>';"
            "getprop ro.boot.verifiedbootstate; echo '<<<SEP>>>';"
            "getprop ro.build.tags; echo '<<<SEP>>>';"
            "getprop ro.frp.pst; echo '<<<SEP>>>';"
            "getenforce; echo '<<<SEP>>>';"
            "dumpsys trust"
        )
        res = self.adb.shell(props_cmd)
        blocks = res.get("stdout", "").split("<<<SEP>>>") if res.get("success") else []
        
        crypto_state = blocks[0].strip() if len(blocks) > 0 else "unknown"
        crypto_type = blocks[1].strip() if len(blocks) > 1 else "unknown"
        warranty_void = blocks[2].strip() if len(blocks) > 2 else "0"
        flash_locked = blocks[3].strip() if len(blocks) > 3 else "unknown"
        verified_boot = blocks[4].strip() if len(blocks) > 4 else "unknown"
        build_tags = blocks[5].strip() if len(blocks) > 5 else "release-keys"
        frp_pst = blocks[6].strip() if len(blocks) > 6 else ""
        selinux = blocks[7].strip() if len(blocks) > 7 else "Enforcing"
        trust_dump = blocks[8] if len(blocks) > 8 else ""

        is_locked = ("mTrustState=UNTRUSTED" in trust_dump or 
                     "deviceLocked=true" in trust_dump or 
                     "mDeviceLocked=true" in trust_dump)

        return {
            "is_rooted": is_rooted,
            "root_info": su_check.get("stdout", "Non rooté").strip(),
            "crypto_state": crypto_state,
            "crypto_type": crypto_type,
            "knox_warranty_void": warranty_void,
            "bootloader_locked": flash_locked,
            "verified_boot": verified_boot,
            "build_tags": build_tags,
            "selinux_mode": selinux,
            "is_keyguard_locked": is_locked,
            "frp_partition": frp_pst
        }

    def attempt_pin_unlock(self, pin):
        """
        Simulate screen wakeup and PIN keypad entry
        """
        pin_clean = re.sub(r'\D', '', str(pin))
        if not pin_clean:
            return {"success": False, "error": "Code PIN invalide"}

        # Wakeup & swipe up to show keypad
        self.adb.shell("input keyevent 224; sleep 0.2; input swipe 360 1200 360 300 200; sleep 0.3")
        # Type the pin and enter
        res = self.adb.shell(f"input text {pin_clean}; input keyevent 66")
        return {"success": res["success"], "pin_attempted": pin_clean}

    def remove_gesture_keys(self):
        """
        Direct lock removal command sequence (LockKnife technique for root / custom recovery)
        """
        commands = [
            "rm -f /data/system/gesture.key",
            "rm -f /data/system/password.key",
            "rm -f /data/system/locksettings.db",
            "rm -f /data/system/locksettings.db-wal",
            "rm -f /data/system/locksettings.db-shm",
            "rm -f /data/system/gatekeeper.password.key",
            "rm -f /data/system/gatekeeper.pattern.key"
        ]
        results = []
        for cmd in commands:
            r = self.adb.shell(cmd)
            results.append({"cmd": cmd, "success": r["success"], "output": r.get("stdout") or r.get("stderr")})
        return {"operations": results, "note": "Nécessite les permissions root pour modifier /data/system"}

    # ==================== 2. FORENSIC & SYSTEM EXTRACTION ====================
    def dump_wifi_passwords(self):
        """
        Extract saved Wi-Fi networks and plain WPA/WPA2 pre-shared keys
        """
        paths = [
            "/data/misc/wifi/WifiConfigStore.xml",
            "/data/misc/wifi/wpa_supplicant.conf",
            "/data/misc/apexdata/com.android.wifi/WifiConfigStore.xml"
        ]
        reveal = request.args.get("reveal") == "1"

        def _mask(psk):
            # Open-network placeholders stay as-is; real PSKs are masked by
            # default (last 2 chars) unless ?reveal=1.
            open_net = psk in ("(Réseau ouvert / Aucun)", "(Aucun)")
            if open_net or reveal:
                return psk, False
            return ("••" + psk[-2:] if len(psk) >= 2 else "••"), True

        found = []
        for p in paths:
            res = self.adb.shell(f"cat {p}")
            if res.get("success") and ("<WifiConfiguration>" in res.get("stdout", "") or "network={" in res.get("stdout", "")):
                content = res["stdout"]
                # XML style — parse per <WifiConfiguration> block so a missing
                # PreSharedKey simply means an open network (no list-zip misattribution)
                for block in content.split("</WifiConfiguration>"):
                    s_m = re.search(r'<string name="SSID">"?(.*?)"?</string>', block)
                    if not s_m:
                        continue
                    p_m = re.search(r'<string name="PreSharedKey">"?(.*?)"?</string>', block)
                    pw, was_masked = _mask(p_m.group(1) if p_m else "(Réseau ouvert / Aucun)")
                    found.append({"ssid": s_m.group(1), "password": pw, "psk_masked": was_masked, "source": p})

                # WPA style
                wpa_blocks = re.findall(r'network=\{([^}]+)\}', content)
                for block in wpa_blocks:
                    s_m = re.search(r'ssid="?([^"\n]+)"?', block)
                    p_m = re.search(r'psk="?([^"\n]+)"?', block)
                    if s_m:
                        pw, was_masked = _mask(p_m.group(1) if p_m else "(Aucun)")
                        found.append({
                            "ssid": s_m.group(1),
                            "password": pw,
                            "psk_masked": was_masked,
                            "source": p
                        })
                if found:
                    break

        out = {"wifi_networks": found, "count": len(found)}
        if not reveal:
            out["masked"] = True
            out["note"] = "PSK masqués — ajoutez ?reveal=1 pour révéler"
        return out

    def dump_accounts(self):
        """
        Extract registered accounts (Google, WhatsApp, Telegram, Microsoft, Samsung, etc.)
        """
        res = self.adb.shell("dumpsys account")
        accounts = []
        if res.get("success"):
            matches = re.findall(r'Account\s*\{\s*name\s*=\s*([^,]+),\s*type\s*=\s*([^}]+)\}', res["stdout"])
            for name, acc_type in matches:
                accounts.append({
                    "name": name.strip(),
                    "type": acc_type.strip()
                })
        return {"accounts": accounts, "count": len(accounts)}

    def dump_clipboard(self):
        """
        Extract current clipboard text from Android framework service
        """
        res = self.adb.shell("dumpsys clipboard")
        raw = res.get("stdout", "")
        # Try to parse clip text
        clip_matches = re.findall(r'text=([^\r\n,]+)', raw)
        return {
            "raw_dump": raw[:2000],
            "extracted_clips": clip_matches
        }

    def dump_raw_service(self, service_name="telephony.registry"):
        """
        Dump any system service state (notification, location, battery, audio, etc.)
        """
        safe_name = shlex.quote(service_name)
        res = self.adb.shell(f"dumpsys {safe_name} | head -n 300", timeout=15)
        return {"service": service_name, "dump": res.get("stdout", "")}

    # ==================== 3. DEBLOATER & PRIVACY HARDENING ====================
    def get_bloatware_catalog(self):
        """
        Catalog of known tracking, bloatware & telemetry packages with one-click disable/restore
        """
        catalog = [
            ("com.facebook.katana", "Facebook", "Réseau social & Traçage"),
            ("com.facebook.system", "Facebook App Installer", "Bloatware constructeur"),
            ("com.facebook.appmanager", "Facebook App Manager", "Gestionnaire OEM"),
            ("com.facebook.services", "Facebook Services", "Télémétrie en arrière-plan"),
            ("com.samsung.android.bixby.agent", "Bixby Voice", "Assistant vocal Samsung"),
            ("com.samsung.android.bixby.service", "Bixby Service", "Service Bixby"),
            ("com.samsung.android.spay", "Samsung Pay", "Paiement & Télémétrie"),
            ("com.sec.android.app.sbrowser", "Samsung Internet", "Navigateur OEM Samsung"),
            ("com.google.android.youtube", "YouTube", "Application vidéo Google"),
            ("com.google.android.apps.tachyon", "Google Meet / Duo", "Appels vidéo Google"),
            ("com.google.android.feedback", "Google Feedback", "Envoi de rapports télémétriques"),
            ("com.netflix.partner.activation", "Netflix Activation", "Bloatware partenaire"),
            ("com.microsoft.skydrive", "Microsoft OneDrive", "Stockage Cloud préinstallé"),
            ("com.microsoft.appmanager", "Lien avec Windows", "Service Microsoft")
        ]

        installed_res = self.adb.shell("pm list packages")
        installed_pkgs = set(l.replace("package:", "").strip() for l in installed_res.get("stdout", "").splitlines())

        result = []
        for pkg, name, cat in catalog:
            result.append({
                "package": pkg,
                "name": name,
                "category": cat,
                "is_installed": pkg in installed_pkgs
            })
        return {"bloatware": result}

    def disable_bloat_package(self, package_name):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+", package_name):
            return {"success": False, "error": "Nom de package invalide"}
        safe_pkg = shlex.quote(package_name)
        res = self.adb.shell(f"pm uninstall -k --user 0 {safe_pkg}")
        ok = "Success" in res.get("stdout", "")
        return {"success": ok, "stdout": res.get("stdout", ""), "error": res.get("stderr", "")}

    def restore_bloat_package(self, package_name):
        if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+", package_name):
            return {"success": False, "error": "Nom de package invalide"}
        safe_pkg = shlex.quote(package_name)
        res = self.adb.shell(f"cmd package install-existing {safe_pkg}")
        ok = "Installed" in res.get("stdout", "") or res.get("success", False)
        return {"success": ok, "stdout": res.get("stdout", "")}

    # ==================== 4. HARDWARE & LIVE DIAGNOSTICS ====================
    def get_hardware_info(self):
        """
        Fetch sensors, cameras, and audio volume channels
        """
        sensors_res = self.adb.shell("dumpsys sensorservice | grep -E 'Handle|Name|Vendor|Type'")
        cam_res = self.adb.shell("dumpsys media.camera | grep -E 'Camera ID|Facing|Resource|Device'")
        audio_res = self.adb.shell("dumpsys audio | grep -E 'STREAM_|Volume'")

        return {
            "sensors": sensors_res.get("stdout", "").strip(),
            "cameras": cam_res.get("stdout", "").strip(),
            "audio": audio_res.get("stdout", "").strip()
        }

    def trigger_vibration(self, duration_ms=500):
        try:
            duration_ms = max(50, min(5000, int(duration_ms)))
        except (TypeError, ValueError):
            return {"success": False, "error": "Paramètre invalide"}
        res = self.adb.shell(f"cmd vibrator vibrate {duration_ms}")
        return {"success": res["success"]}

    def set_brightness(self, level=150):
        try:
            level = max(0, min(255, int(level)))
        except (TypeError, ValueError):
            return {"success": False, "error": "Paramètre invalide"}
        res = self.adb.shell(f"settings put system screen_brightness {level}")
        return {"success": res["success"], "brightness": level}

    def record_screen(self, duration_sec=5):
        try:
            duration_sec = max(1, min(30, int(duration_sec)))
        except (TypeError, ValueError):
            return {"success": False, "error": "Paramètre invalide"}
        rec_id = uuid.uuid4().hex
        remote_tmp = f"/sdcard/screen_record_{rec_id}.mp4"
        local_dest = TEMP_DIR / f"rec_{rec_id}.mp4"
        
        self.adb.shell(f"screenrecord --time-limit {duration_sec} {remote_tmp}", timeout=duration_sec + 10)
        pull_res = self.adb.run_cmd(["pull", remote_tmp, str(local_dest)], timeout=60)
        self.adb.shell(f"rm {remote_tmp}")
        
        return {
            "success": pull_res["success"] and local_dest.exists(),
            "local_path": str(local_dest),
            "filename": local_dest.name
        }

    # ==================== 5. FRIDA SCRIPT GENERATOR & TWEAKS ====================
    def get_frida_scripts(self):
        """
        Provide ready-to-use Frida hooks extracted from LockKnife (SSL Pinning bypass, Root bypass, Debug bypass)
        """
        ssl_bypass = """// [LockKnife] Universal SSL Pinning Bypass
Java.perform(function () {
    try {
        var X509TrustManager = Java.use('javax.net.ssl.X509TrustManager');
        var SSLContext = Java.use('javax.net.ssl.SSLContext');
        var TrustManager = Java.registerClass({
            name: 'com.lockknife.TrustManagerImpl',
            implements: [X509TrustManager],
            methods: {
                checkClientTrusted: function (_c, _a) {},
                checkServerTrusted: function (_c, _a) {},
                getAcceptedIssuers: function () { return []; }
            }
        });
        var TrustManagers = [TrustManager.$new()];
        SSLContext.init.overload('[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;', 'java.security.SecureRandom')
            .implementation = function (km, _tm, sr) {
                console.log('[+] SSLContext.init Universal Hooked!');
                return this.init(km, TrustManagers, sr);
            };
    } catch (e) { console.log('[-] SSL Hook: ' + e); }

    try {
        var CertificatePinner = Java.use('okhttp3.CertificatePinner');
        CertificatePinner.check.overload('java.lang.String', 'java.util.List').implementation = function () {
            console.log('[+] OkHttp3 CertificatePinner.check bypassed');
        };
    } catch(e) {}
});"""

        root_bypass = """// [LockKnife] Universal Root Detection Bypass
Java.perform(function() {
    var File = Java.use('java.io.File');
    File.exists.implementation = function() {
        var path = this.getAbsolutePath();
        if (path.indexOf('su') !== -1 || path.indexOf('magisk') !== -1 || path.indexOf('Superuser') !== -1 || path.indexOf('busybox') !== -1) {
            console.log('[+] Root check blocked for: ' + path);
            return false;
        }
        return this.exists();
    };

    var Runtime = Java.use('java.lang.Runtime');
    Runtime.exec.overload('java.lang.String').implementation = function(cmd) {
        if (cmd === 'su' || cmd.indexOf('which su') !== -1) {
            console.log('[+] Runtime.exec blocked su query');
            return Runtime.exec.overload('java.lang.String').call(this, 'echo not_root');
        }
        return this.exec(cmd);
    };
});"""

        return {
            "ssl_pinning_bypass": ssl_bypass,
            "root_detection_bypass": root_bypass
        }

    def apply_tweak(self, tweak_key):
        """
        Apply performance & privacy build.prop tweaks from Android_Hacking
        """
        tweaks_map = {
            "hide_adb_notify": "setprop persist.adb.notify 0",
            "show_adb_notify": "setprop persist.adb.notify 1",
            "camera_hal3_enable": "setprop persist.camera.HAL3.enabled 1",
            "low_ram_flag": "setprop ro.config.low_ram false",
            "disable_touch_sounds": "settings put system sound_effects_enabled 0",
            "disable_haptic_feedback": "settings put system haptic_feedback_enabled 0",
            "keep_screen_on_usb": "settings put global stay_on_while_plugged_in 3"
        }
        cmd = tweaks_map.get(tweak_key)
        if not cmd:
            return {"success": False, "error": "Unknown tweak key"}
        res = self.adb.shell(cmd)
        return {"success": res["success"], "tweak": tweak_key, "output": res.get("stdout")}
