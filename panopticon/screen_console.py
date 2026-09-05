"""
PANOPTICON :: screen_console.py — live interactive remote screen, zero deps.

Honest engineering choice for tonight: full scrcpy H.264 piping needs an
ffmpeg transcode layer and a version-pinned client protocol — that's the
roadmap. What THIS module ships is immediately real:

  - fast single-frame JPEG grabs (`exec-out screencap`) — no base64 SSE tax
  - browser-coordinates → device-coordinates mapping
  - tap / swipe / long-press injection straight off the live image

Result: you see the phone's screen refreshing in the War Room and CLICK
it like a VNC console. Every interaction rides serial targeting.
"""

import io
import logging
import math

from flask import Blueprint, jsonify, request, Response, send_file

from adb_engine import ADBEngine

log = logging.getLogger("panopticon.screen")

screen_bp = Blueprint("screen_console", __name__, url_prefix="/api/screen")
engine = ADBEngine()


def _serial():
    data = request.get_json(silent=True) or {}
    return (request.args.get("serial") or data.get("serial") or "").strip() or None


_COORD_MAX = 100000   # sanity ceiling so junk never reaches `input` cmds


def _int_or_none(v):
    """float→int; NaN/inf/junk rejected (isfinite + conversion guarded)."""
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(f):
        return None
    try:
        return int(f)
    except (ValueError, OverflowError):
        return None


def _clamp_coord(v):
    return max(0, min(int(v), _COORD_MAX))


def _clamp_duration(v):
    return max(50, min(int(v), 60000))   # ms — outside this `input swipe` misbehaves


@screen_bp.route("/frame")
def frame():
    """One fresh PNG frame of the device screen (auto-wakes if asleep)."""
    serial = (request.args.get("serial") or "").strip() or None
    res = engine.run_binary_cmd(["exec-out", "screencap", "-p"],
                                timeout=15, serial=serial)
    if not res["success"] or not res["stdout"]:
        return jsonify({"success": False,
                        "error": res.get("stderr") or "capture vide"}), 502
    data = res["stdout"]

    # If phone screen is OFF/Dozing (black 7.9KB PNG), automatically wake it!
    if len(data) < 15000:
        engine.shell("input keyevent 224", serial=serial, timeout=5)  # KEYCODE_WAKEUP
        res = engine.run_binary_cmd(["exec-out", "screencap", "-p"],
                                    timeout=15, serial=serial)
        if res["success"] and res["stdout"]:
            data = res["stdout"]

    # Only fix CRLF if adb on Windows mangled \n into \r\r\n
    if data.startswith(b"\x89PNG\r\r\n\x1a\r\n"):
        data = data.replace(b"\r\r\n", b"\r\n")
    return Response(data, mimetype="image/png",
                    headers={"Cache-Control": "no-store"})


@screen_bp.route("/tap", methods=["POST"])
def tap():
    data = request.get_json() or {}
    serial = (data.get("serial") or "").strip() or None
    x = _int_or_none(data.get("x"))
    y = _int_or_none(data.get("y"))
    if x is None or y is None:
        return jsonify({"success": False, "error": "x/y requis"}), 400
    x, y = _clamp_coord(x), _clamp_coord(y)
    res = engine.shell(f"input tap {x} {y}", serial=serial, timeout=10)
    return jsonify({"success": res["success"], "tapped": [x, y],
                    "stderr": res.get("stderr")})


@screen_bp.route("/swipe", methods=["POST"])
def swipe():
    data = request.get_json(silent=True) or {}
    serial = (data.get("serial") or "").strip() or None

    # Format A: Direct device coordinates {x1, y1, x2, y2, duration}
    if "x1" in data and "y1" in data and "x2" in data and "y2" in data:
        x1 = _int_or_none(data["x1"])
        y1 = _int_or_none(data["y1"])
        x2 = _int_or_none(data["x2"])
        y2 = _int_or_none(data["y2"])
        duration = _int_or_none(data.get("duration", data.get("ms", 300)))
        if None in (x1, y1, x2, y2, duration):
            return jsonify({"success": False, "error": "Coordonnées invalides"}), 400
        x1, y1, x2, y2 = (_clamp_coord(v) for v in (x1, y1, x2, y2))
        duration = _clamp_duration(duration)
        res = engine.shell(f"input swipe {x1} {y1} {x2} {y2} {duration}", serial=serial, timeout=12)
        return jsonify({"success": res["success"], "swiped": [x1, y1, x2, y2], "stderr": res.get("stderr")})

    # Format B: Browser scaled coordinates {points: [[x1, y1], [x2, y2]], view: {w, h}}
    try:
        pts = data["points"]                    # [[x,y],[x,y]] browser coords
        dims = data["view"]                     # {w,h} of the displayed img
        duration_ms = _int_or_none(data.get("ms", 300))
        if duration_ms is None:
            return jsonify({"success": False, "error": "Format de swipe invalide"}), 400
        duration_ms = _clamp_duration(duration_ms)
        if len(pts) != 2:
            return jsonify({"success": False, "error": "exactement deux points"}), 400
        vw, vh = int(dims["w"]), int(dims["h"])
        if not vw or not vh:
            return jsonify({"success": False, "error": "dimensions invalides"}), 400
        (x1, y1), (x2, y2) = pts
        sx = sy = None
        dev_dims = engine.shell("wm size", serial=serial, timeout=8)
        import re as _re
        m = _re.search(r"(\d+)x(\d+)", dev_dims.get("stdout") or "")
        if m:
            dw, dh = int(m.group(1)), int(m.group(2))
            sx, sy = dw / vw, dh / vh
        cmd_pts = (
            f"{_clamp_coord(x1 * sx)} {_clamp_coord(y1 * sy)} "
            f"{_clamp_coord(x2 * sx)} {_clamp_coord(y2 * sy)}"
            if sx else (f"{_clamp_coord(x1)} {_clamp_coord(y1)} "
                        f"{_clamp_coord(x2)} {_clamp_coord(y2)}")
        )
        res = engine.shell(f"input swipe {cmd_pts} {duration_ms}", serial=serial, timeout=12)
        return jsonify({"success": res["success"], "scale_applied": bool(sx), "stderr": res.get("stderr")})
    except (KeyError, TypeError, ValueError) as e:
        log.debug("swipe invalide: %s", e)
        return jsonify({"success": False, "error": "Format de swipe invalide"}), 400


@screen_bp.route("/size")
def size():
    """Real panel resolution so browser clicks map 1:1 onto the glass."""
    serial = (request.args.get("serial") or "").strip() or None
    res = engine.shell("wm size", timeout=8, serial=serial)
    return jsonify({"success": res["success"],
                    "output": (res.get("stdout") or "").strip()})


@screen_bp.route("/text", methods=["POST"])
def text():
    """Type text into whatever field holds focus on the device."""
    data = request.get_json() or {}
    serial = (data.get("serial") or "").strip() or None
    payload = data.get("text") or ""
    if not payload:
        return jsonify({"success": False, "error": "texte vide"}), 400
    if len(payload) > 2000:
        return jsonify({"success": False, "error": "texte trop long (2000 caractères max)"}), 400
    import shlex as _shlex
    safe = _shlex.quote(payload.replace(" ", "%s"))   # input text space quirk
    res = engine.shell(f"input text {safe}", serial=serial, timeout=12)
    return jsonify({"success": res["success"], "stderr": res.get("stderr")})


# ==================== H264 CAST (gate ③) ====================
# Native encoder river: `screenrecord --output-format=h264 -` rides exec-out.
# Zero jars, zero ffmpeg — the phone's own MediaCodec is the tool. The
# grammar (NAL splitting, SPS exp-Golomb, keyframe census) lives in
# h264_math.py; this class is the plumbing around a torn TCP river.

import subprocess
import threading
import time as _time
from datetime import datetime, timezone

from h264_math import (AnnexBStreamSplitter, parse_sps, NAL_SPS,
                       NAL_SLICE_IDR, remove_emulation_prevention)

_RING_MAX = 1 << 22          # 4 MB river backlog for a future consumer


class H264CastSession:
    """One live H.264 river per panel. start/stop/status, honest stats."""

    def __init__(self):
        self._proc = None
        self._thread = None
        self._pump_stale = False   # set when stop() outlives the pump join
        self._lock = threading.Lock()
        self._splitter = None
        self._ring = bytearray()
        self._stat = {"running": False, "started": None, "nals": 0,
                      "keyframes": 0, "bytes": 0, "sps": None,
                      "error": None, "serial": None}

    def start(self, serial=None, bitrate=None, max_width=None):
        with self._lock:
            if self._pump_stale:
                return {"success": False,
                        "error": "cast pump still draining — retry shortly"}
            if self._proc and self._proc.poll() is None:
                return {"success": False, "error": "cast already running",
                        **self._snapshot_locked()}
            cmd = [engine.adb_path]
            if serial:
                cmd += ["-s", serial]
            cmd += ["exec-out", "screenrecord", "--output-format=h264"]
            if bitrate:
                try:
                    br = int(bitrate)
                    if 1_000_000 <= br <= 50_000_000:
                        cmd += ["--bit-rate", str(br)]
                except (TypeError, ValueError):
                    pass
            if max_width:
                try:
                    mw = int(max_width)
                    if mw in (1920, 1080, 720, 480):
                        cmd += ["--size", f"{mw}x-1"]
                except (TypeError, ValueError):
                    pass
            try:
                self._proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                              stderr=subprocess.DEVNULL)
            except OSError as e:
                return {"success": False, "error": f"adb spawn failed: {e}"}
            self._splitter = AnnexBStreamSplitter()
            self._ring.clear()
            self._stat.update({"running": True, "nals": 0, "keyframes": 0,
                               "bytes": 0, "sps": None, "error": None,
                               "started_ts": _time.time(),
                               "started": datetime.now(timezone.utc)
                                          .isoformat(timespec="seconds"),
                               "serial": serial})
            self._thread = threading.Thread(target=self._pump, daemon=True)
            self._thread.start()
            return {"success": True, "note":
                    "device encoder caps at 180 s — re-arm to recap",
                    **self._snapshot_locked()}

    def _pump(self):
        proc = self._proc
        splitter = self._splitter   # local ref: start() swaps self._splitter under the lock
        try:
            while True:
                chunk = proc.stdout.read1(65536)
                if not chunk:
                    break
                nals = splitter.feed(chunk)
                with self._lock:
                    self._stat["bytes"] += len(chunk)
                    self._ring.extend(chunk)
                    if len(self._ring) > _RING_MAX:
                        del self._ring[:-_RING_MAX]
                    for unit in nals:
                        self._stat["nals"] += 1
                        htype = unit[0] & 0x1F
                        if htype == NAL_SLICE_IDR:
                            self._stat["keyframes"] += 1
                        elif htype == NAL_SPS and self._stat["sps"] is None:
                            try:
                                rbsp = remove_emulation_prevention(unit[1:])
                                meta = parse_sps(rbsp)
                                self._stat["sps"] = {
                                    "width": meta["width"],
                                    "height": meta["height"],
                                    "fps": meta["fps"],
                                    "profile_idc": meta["profile_idc"]}
                            except Exception:
                                self._stat["sps"] = {"error": "sps parse"}
        except Exception as e:                      # river died loud
            with self._lock:
                self._stat["error"] = repr(e)
        finally:
            try:
                proc.stdout.close()
            except OSError:
                pass
            if proc.poll() is None:
                try:
                    proc.terminate()
                except OSError:
                    pass
            with self._lock:
                # exit code 0 = clean stop or the 180 s device cap;
                # anything else is a real fault worth naming
                rc = proc.poll()
                if self._stat["running"] and rc not in (0, None):
                    self._stat["error"] = f"encoder exited rc={rc}"
                self._stat["running"] = False
                self._pump_stale = False   # pump drained — re-arm allowed again

    def stop(self):
        with self._lock:
            proc = self._proc
            thread = self._thread
            if not proc or proc.poll() is not None:
                self._stat["running"] = False
                self._stat["error"] = None
                return {"success": True, "was_running": False,
                        **self._snapshot_locked()}
        try:
            proc.terminate()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                proc.kill()
            except OSError:
                pass
        if thread:
            thread.join(timeout=3)
        with self._lock:
            if thread and thread.is_alive():
                # pump wedged in read1 — refuse re-start until it drains
                self._pump_stale = True
            self._stat["running"] = False
            self._stat["error"] = None
            return {"success": True, "was_running": True,
                    **self._snapshot_locked()}

    def status(self):
        with self._lock:
            return {"success": True, **self._snapshot_locked()}

    def _snapshot_locked(self):
        s = dict(self._stat)
        ts = s.get("started_ts")
        s["elapsed_s"] = round(_time.time() - ts, 1) if ts else None
        s["mbps"] = (round(s["bytes"] * 8 / 1e6 / s["elapsed_s"], 2)
                     if s["elapsed_s"] and s["elapsed_s"] > 0.5 else None)
        return s


_CAST = H264CastSession()


@screen_bp.route("/cast/start", methods=["POST"])
def cast_start():
    """Open the phone's native H.264 river (exec-out screenrecord)."""
    data = request.get_json() or {}
    serial = (data.get("serial") or "").strip() or None
    attached = [d for d in engine.get_devices()
                if (d.get("status") or "") == "device"]
    if not attached:
        return jsonify({"success": False,
                        "error": "no device attached — nothing to cast"})
    return jsonify(_CAST.start(serial=serial,
                               bitrate=data.get("bitrate"),
                               max_width=data.get("max_width")))


@screen_bp.route("/cast/status")
def cast_status():
    """River vitals — NAL count, keyframes, SPS geometry, Mbps."""
    return jsonify(_CAST.status())


@screen_bp.route("/cast/stop", methods=["POST"])
def cast_stop():
    """Terminate the encoder river cleanly."""
    return jsonify(_CAST.stop())
