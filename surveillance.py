"""
DroidCommand — Surveillance Module
Modules 1-4: Screen Mirroring, Mic Capture, Camera Capture, GPS Location
"""

import subprocess
import time
import re
import os
import uuid
import base64
import logging
from pathlib import Path
from config import ADB_PATH, TEMP_DIR
from adb_engine import ADBEngine

adb = ADBEngine()

log = logging.getLogger(__name__)

# L97: upper bound before buffering/encoding a frame
_MAX_FRAME_BYTES = 12 * 1024 * 1024


# ==================== MODULE 1: LIVE SCREEN MIRRORING ====================

def capture_screen_frame(serial=None):
    """Capture a single screen frame as PNG bytes."""
    try:
        # fix: optional serial targeting for multi-device hosts (item 5)
        argv = [adb.adb_path]
        if serial:
            argv += ["-s", serial]
        argv += ["exec-out", "screencap", "-p"]
        res = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8
        )
        if res.returncode == 0 and len(res.stdout) > _MAX_FRAME_BYTES:
            # L97: frame hors bornes — rejetée avant encodage/buffering
            log.warning("capture_screen_frame: frame rejetée (%d octets)", len(res.stdout))
            return {"success": False, "error": "Frame trop volumineuse"}
        if res.returncode == 0 and len(res.stdout) > 100:
            return {"success": True, "frame": res.stdout, "size": len(res.stdout)}
        return {"success": False, "error": "Capture écran vide ou échouée"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout capture écran"}
    except Exception as e:
        # L96: détail en log, message générique au client
        log.warning("capture_screen_frame a échoué: %s", e)
        return {"success": False, "error": "échec capture écran (voir logs)"}


def capture_screen_jpeg(quality=60, serial=None):
    """Capture screen and return as JPEG base64 for web streaming."""
    # fix: name kept for compat, payload is PNG (item 10)
    try:
        # Capture as PNG first
        # fix: optional serial targeting for multi-device hosts (item 5)
        argv = [adb.adb_path]
        if serial:
            argv += ["-s", serial]
        argv += ["exec-out", "screencap", "-p"]
        res = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=8
        )
        if res.returncode != 0 or len(res.stdout) < 100 or len(res.stdout) > _MAX_FRAME_BYTES:
            # L97: cap appliqué aussi sur le chemin JPEG
            log.warning("capture_screen_jpeg: frame rejetée (%d octets)", len(res.stdout))
            return {"success": False, "error": "Capture échouée"}

        # Return raw PNG bytes (browser can handle PNG directly)
        img_b64 = base64.b64encode(res.stdout).decode("ascii")
        return {"success": True, "image_b64": img_b64, "format": "png"}

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        # L96: détail en log, message générique au client
        log.warning("capture_screen_jpeg a échoué: %s", e)
        return {"success": False, "error": "échec streaming écran (voir logs)"}


# ==================== MODULE 2: MIC / AUDIO CAPTURE ====================

def record_audio(duration=10):
    """Record device audio via screenrecord — the artifact also contains a
    320x240 screen video track (NOT audio-only; kept for compatibility)."""
    try:
        duration = min(max(int(duration), 3), 60)  # Clamp 3-60s
        # fix: uuid remote filename — concurrent recordings collided on one path (item 6)
        remote_path = f"/sdcard/.dc_audio_cap_{uuid.uuid4().hex[:8]}.mp4"
        local_path = str(TEMP_DIR / f"audrec_{uuid.uuid4().hex[:8]}_{int(time.time())}.mp4")

        try:
            # screenrecord captures screen + audio (internal audio on Android 10+)
            adb.shell(
                f"screenrecord --time-limit {duration} --size 320x240 --bit-rate 500000 {remote_path}",
                timeout=duration + 10
            )

            # Pull the recorded file
            pull_res = adb.run_cmd(["pull", remote_path, local_path], timeout=15)
        finally:
            # M36: the remote artifact must not survive an exception
            adb.shell(f"rm -f {remote_path}")

        if pull_res["success"] and os.path.exists(local_path):
            file_size = os.path.getsize(local_path)
            if file_size > 100:
                return {
                    "success": True,
                    "filepath": local_path,
                    "duration": duration,
                    "size": file_size,
                    "filename": os.path.basename(local_path)
                }

        # L95: pull failed or file empty — remove the partial local artifact
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
        except OSError:
            pass

        return {"success": False, "error": "Fichier audio vide ou pull échoué"}

    except Exception as e:
        log.warning("record_audio a échoué: %s", e)
        return {"success": False, "error": "échec d'enregistrement audio (voir logs)"}


# ==================== MODULE 3: CAMERA CAPTURE ====================

def capture_camera(camera_id=0, serial=None):
    """
    Take a photo using the device camera.
    camera_id: 0 = back camera, 1 = front camera
    """
    camera_opened = False
    backs_sent = False

    def _close_camera():
        # M37: BACK x2 envoyés exactement une fois, quel que soit le déroulement
        nonlocal backs_sent
        if camera_opened and not backs_sent:
            adb.shell("input keyevent 4", serial=serial)  # BACK
            time.sleep(0.5)
            adb.shell("input keyevent 4", serial=serial)  # BACK again
            backs_sent = True

    try:
        camera_id = int(camera_id)
        timestamp = int(time.time())

        # Method: Open camera app, switch if needed, take photo
        # Step 1: Open camera
        adb.shell("am start -a android.media.action.STILL_IMAGE_CAMERA", serial=serial)  # fix: serial (item 5)
        camera_opened = True
        time.sleep(3)

        # fix: skip the blind tap when the camera app is not in the foreground
        # (probe mCurrentFocus like pin_siege.py:107-127 does) (item 8)
        camera_focused = False
        focus_res = adb.shell("dumpsys window | grep mCurrentFocus", serial=serial)
        focus_raw = (focus_res.get("stdout") or "")
        camera_focused = "camera" in focus_raw.lower()  # camera package expected
        if not camera_focused:
            log.warning("capture_camera: caméra non au premier plan, switch/tap ignorés")

        # Step 2: If front camera requested, send switch event
        if camera_id == 1 and camera_focused:  # fix: focus-gated (item 8)
            # Samsung camera switch button or generic toggle
            adb.shell("input keyevent 1000054", serial=serial)  # KEYCODE_CAMERA_SWITCH (some devices)
            time.sleep(1)
            # Fallback: tap typical front camera switch location
            adb.shell("input tap 120 120", serial=serial)
            time.sleep(1)

        # Step 3: Take photo via shutter keyevent
        adb.shell("input keyevent 27", serial=serial)  # KEYCODE_CAMERA
        time.sleep(3)

        # Step 4: Find most recent photo
        ls_res = adb.shell("ls -t /sdcard/DCIM/Camera/ 2>/dev/null | head -3", serial=serial)
        if ls_res["success"] and ls_res["stdout"]:
            files = [f.strip() for f in ls_res["stdout"].splitlines() if f.strip()]
            if files:
                # H13: le nom vient de l'appareil — basename + liste blanche,
                # jamais interpolé brut côté hôte
                newest = os.path.basename(files[0])
                if re.fullmatch(r"[A-Za-z0-9._-]+", newest):
                    remote_path = f"/sdcard/DCIM/Camera/{newest}"
                    local_path = str(TEMP_DIR / f"camera_{camera_id}_{uuid.uuid4().hex[:8]}_{newest}")

                    pull_res = adb.run_cmd(["pull", remote_path, local_path], timeout=15, serial=serial)  # fix: serial (item 5)
                    _close_camera()

                    if pull_res["success"] and os.path.exists(local_path):
                        return {
                            "success": True,
                            "filepath": local_path,
                            "filename": os.path.basename(local_path),
                            "camera": "front" if camera_id == 1 else "back",
                            "size": os.path.getsize(local_path)
                        }

                    # L95: pull échoué — retirer le fichier local partiel
                    try:
                        if os.path.exists(local_path):
                            os.remove(local_path)
                    except OSError:
                        pass

        # Fallback: take a screenshot instead — camera fermée AVANT la capture
        # pour que l'écran ne montre pas l'UI caméra
        _close_camera()
        frame = capture_screen_frame()
        if frame["success"]:
            fallback_path = str(TEMP_DIR / f"camera_fallback_{uuid.uuid4().hex[:8]}_{timestamp}.png")
            with open(fallback_path, "wb") as f:
                f.write(frame["frame"])
            return {
                "success": True,
                "filepath": fallback_path,
                "filename": os.path.basename(fallback_path),
                "camera": "screenshot_fallback",
                "size": os.path.getsize(fallback_path)
            }

        return {"success": False, "error": "Impossible de capturer une photo"}

    except Exception as e:
        log.warning("capture_camera a échoué: %s", e)
        return {"success": False, "error": "échec de capture caméra (voir logs)"}
    finally:
        _close_camera()


# ==================== MODULE 4: GPS LOCATION ====================

def get_gps_location():
    """Get the device's GPS/network location."""
    try:
        result = {
            "success": False,
            "lat": None,
            "lon": None,
            "accuracy": None,
            "provider": None,
            "altitude": None,
            "raw": ""
        }

        # Check if location is enabled
        loc_enabled = adb.shell("settings get secure location_providers_allowed")
        result["location_enabled"] = (loc_enabled.get("stdout") or "").strip()  # fix: None-value crash (item 7)

        # Method 1: dumpsys location — look for last known location
        dump = adb.shell("dumpsys location", timeout=10)
        raw_output = (dump.get("stdout") or "")  # fix: None-value crash (item 7)
        result["raw"] = raw_output[:2000]  # Cap raw output

        # fix: sweep only the capped slice, not the full output (item 9)
        capped_output = raw_output[:2000]

        # Parse location patterns
        # Pattern: "last location=Location[gps 48.856614,2.352222 hAcc=10.0 ..."
        # Or: "fused: Location[fused 48.856614,2.352222 ..."
        patterns = [
            r'last\s+location\s*=\s*Location\[(\w+)\s+([-\d.]+),([-\d.]+)\s+(?:hAcc|acc)=([\d.]+)',
            r'Location\[(\w+)\s+([-\d.]+),([-\d.]+)\s+(?:hAcc|acc)=([\d.]+)',
            r'(\w+):\s*Location\[.*?([-\d.]+),([-\d.]+).*?(?:hAcc|acc)=([\d.]+)',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, capped_output)  # fix: capped slice (item 9)
            if matches:
                # Take the first valid match
                for match in matches:
                    provider, lat, lon, acc = match[0], match[1], match[2], match[3]
                    try:
                        lat_f = float(lat)
                        lon_f = float(lon)
                        # Validate reasonable coordinates
                        if -90 <= lat_f <= 90 and -180 <= lon_f <= 180:
                            result["success"] = True
                            result["lat"] = lat_f
                            result["lon"] = lon_f
                            result["accuracy"] = float(acc)
                            result["provider"] = provider
                            break
                    except (ValueError, IndexError):
                        continue
                if result["success"]:
                    break

        # Method 2 fallback: try dumpsys activity for location-related services
        if not result["success"]:
            gms_dump = adb.shell(
                'dumpsys activity service com.google.android.gms/.location.reporting.service.LocationReportingService 2>/dev/null | head -50',
                timeout=8
            )
            gms_out = (gms_dump.get("stdout") or "")  # fix: None-value crash (item 7)
            # L98: coordonnées GPS exigées — ancrées, signe explicite,
            # ≥3 décimales (versions/compteurs du dump ne matchent plus)
            coord_match = re.search(
                r'(?<![\d.])(-?\d{1,3}\.\d{3,}),(-?\d{1,3}\.\d{3,})(?![\d.])',
                gms_out
            )
            if coord_match:
                try:
                    lat_f = float(coord_match.group(1))
                    lon_f = float(coord_match.group(2))
                    if -90 <= lat_f <= 90 and -180 <= lon_f <= 180:
                        result["success"] = True
                        result["lat"] = lat_f
                        result["lon"] = lon_f
                        result["provider"] = "gms"
                except ValueError:
                    pass

        # Method 3: try getting last known via settings
        if not result["success"]:
            geo_res = adb.shell("settings get secure location_providers_allowed")
            result["providers_status"] = (geo_res.get("stdout") or "").strip()  # fix: None-value crash (item 7)

        return result

    except Exception as e:
        # L96 (dernier site): détail en log, message générique au client
        log.warning("get_gps_location a échoué: %s", e)
        return {"success": False, "error": "échec localisation GPS (voir logs)"}
