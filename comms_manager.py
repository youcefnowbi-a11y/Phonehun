import re
import datetime

# Fields the consumers below actually read — only these act as key= boundaries,
# so unknown 'foo=' sequences inside values (SMS bodies) stay part of the value.
_KNOWN_FIELDS = frozenset({
    "_id", "address", "body", "date", "type",
    "display_name", "number", "name", "duration",
})

class CommsManager:
    def __init__(self, adb_engine):
        self.adb = adb_engine

    def parse_content_rows(self, output):
        """
        BUG 9 FIX: Parse content provider output more carefully.
        Each row starts with 'Row: N' followed by key=value pairs separated by ', '.
        We parse left-to-right, matching key=value where key is a known field name,
        to avoid misinterpreting values that contain '=' or ','.
        """
        rows = []
        if not output:
            return rows

        current_row = {}
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("Row:"):
                if current_row:
                    rows.append(current_row)
                current_row = {}
                # Strip "Row: N " prefix
                line = re.sub(r'^Row:\s*\d+\s*', '', line)

            if not line:
                continue

            # Split by ', ' but be aware that values may contain commas.
            # Strategy: find all 'key=' boundaries, then extract values between them.
            # Restrict boundaries to known field names — unknown 'foo=' stays in the value.
            key_positions = [(m.start(), m.group(1)) for m in re.finditer(r'(?:^|,\s*)(\w+)=', line)
                             if m.group(1) in _KNOWN_FIELDS]

            if not key_positions:
                # Multiline SMS bodies arrive as continuation lines — join them
                # onto the previous record's body field.
                if current_row and "body" in current_row:
                    current_row["body"] += "\n" + line
                continue

            for i, (pos, key) in enumerate(key_positions):
                # Value starts after 'key='
                val_start = pos + line[pos:].index('=') + 1
                # Value ends at the next key boundary or end of line
                if i + 1 < len(key_positions):
                    next_pos = key_positions[i + 1][0]
                    # Strip trailing ', ' before the next key
                    val = line[val_start:next_pos].rstrip(', ')
                else:
                    val = line[val_start:]
                
                current_row[key.strip()] = val.strip()

        if current_row:
            rows.append(current_row)
        return rows

    def get_contacts(self):
        # Android 12's `content` rejects comma-joined projections and keeps only
        # the last repeated flag — so query full rows and pick fields client-side.
        # fix: no `| head` pipe — it masked device-side failures (pipeline exit =
        # head's 0); rows are sliced in Python instead (item 19)
        cmd = "content query --uri content://contacts/phones/"
        res = self.adb.shell(cmd, timeout=15)

        contacts = []
        if res["success"]:
            rows = self.parse_content_rows((res.get("stdout") or ""))[:250]  # fix: python slice (item 19)
            for r in rows:
                name = r.get("display_name", "Unknown")
                num = r.get("number", "Unknown")
                if num != "Unknown" or name != "Unknown":
                    contacts.append({
                        "name": name,
                        "number": num,
                        "type": r.get("type", "Mobile")
                    })

        # fix: error surfaced on device-side failure (item 19)
        return {"contacts": contacts, "count": len(contacts),
                "error": None if res["success"] else res.get("stderr")}

    def get_sms(self):
        # fix: no `| head` pipe — it masked device-side failures; python slice instead (item 19)
        cmd = "content query --uri content://sms/ --projection _id,address,body,date,type --sort 'date DESC'"
        res = self.adb.shell(cmd, timeout=15)

        messages = []
        if res["success"]:
            rows = self.parse_content_rows((res.get("stdout") or ""))[:200]  # fix: python slice (item 19)
            for r in rows:
                date_ms = r.get("date")
                date_str = "Unknown"
                if date_ms and date_ms.isdigit():
                    try:
                        date_str = datetime.datetime.fromtimestamp(int(date_ms) / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pass

                # fix: full SMS type map — Draft/Outbox/Failed/Queued were collapsed (item 20)
                sms_type_map = {"1": "Received", "2": "Sent", "3": "Draft",
                                "4": "Outbox", "5": "Failed", "6": "Queued"}
                msg_type = sms_type_map.get(r.get("type"), "Unknown")
                messages.append({
                    "id": r.get("_id", ""),
                    "address": r.get("address", "Unknown"),
                    "body": r.get("body", ""),
                    "date": date_str,
                    "type": msg_type
                })

        # fix: error surfaced on device-side failure (item 19)
        return {"messages": messages, "count": len(messages),
                "error": None if res["success"] else res.get("stderr")}

    def get_call_logs(self):
        # Provider returns newest-first natively; no --sort needed.
        # fix: no `| head` pipe — it masked device-side failures; python slice instead (item 19)
        cmd = "content query --uri content://call_log/calls"
        res = self.adb.shell(cmd, timeout=15)

        calls = []
        if res["success"]:
            rows = self.parse_content_rows((res.get("stdout") or ""))[:150]  # fix: python slice (item 19)
            type_map = {"1": "Incoming", "2": "Outgoing", "3": "Missed", "4": "Voicemail", "5": "Rejected", "6": "Blocked"}
            for r in rows:
                date_ms = r.get("date")
                date_str = "Unknown"
                if date_ms and date_ms.isdigit():
                    try:
                        date_str = datetime.datetime.fromtimestamp(int(date_ms) / 1000.0).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        pass

                call_type = type_map.get(r.get("type"), "Other")
                calls.append({
                    "name": r.get("name") or "Unknown",
                    "number": r.get("number", "Unknown"),
                    "date": date_str,
                    "duration": f"{r.get('duration', '0')}s",
                    "type": call_type
                })

        # fix: error surfaced on device-side failure (item 19)
        return {"calls": calls, "count": len(calls),
                "error": None if res["success"] else res.get("stderr")}
