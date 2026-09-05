"""
Deep Access tier — everything the unprivileged `shell` uid can still reach.

On a locked bootloader there is no path from uid 2000 to root, but shell holds
WRITE_SECURE_SETTINGS, controls appops / pm grant for every package, can dump
the active window's UI hierarchy via uiautomator, and can override display
geometry with wm. This module exposes those levers as discrete, reversible
operations instead of raw shell one-liners.
"""

import re
import uuid
import xml.etree.ElementTree as ET

# Characters that would break out of a device-side shell token. Values are
# single-quoted before use; anything outside this set is rejected outright.
_SAFE_RE = re.compile(r'^[A-Za-z0-9._:@+/\[\]()-]*$')
_SETTING_NS = ("system", "secure", "global")
_OP_MODES = ("allow", "ignore", "deny", "default")


class DeepAccess:
    def __init__(self, adb_engine):
        self.adb = adb_engine

    # ------------------------------------------------------------------
    @staticmethod
    def _tok(value, what="value"):
        v = str(value or "").strip()
        if not v or not _SAFE_RE.match(v):
            raise ValueError(f"unsafe {what}: {value!r}")
        return v

    def _shell(self, cmd, timeout=20):
        return self.adb.shell(cmd, timeout=timeout)

    # ==================== secure/system/global settings ====================

    def settings_list(self, ns, needle=None):
        if ns not in _SETTING_NS:
            raise ValueError("namespace must be system|secure|global")
        cmd = f"settings list {ns}"
        if needle:
            cmd += f" | grep -i '{self._tok(needle, 'search term')}'"
        res = self._shell(cmd)
        rows = []
        if res["success"]:
            for line in res["stdout"].splitlines():
                if "=" in line:
                    k, _, v = line.partition("=")
                    rows.append({"key": k.strip(), "value": v.strip()})
        return {"success": res["success"], "error": res.get("stderr"), "settings": rows,
                "count": len(rows)}

    def settings_get(self, ns, key):
        if ns not in _SETTING_NS:
            raise ValueError("namespace must be system|secure|global")
        res = self._shell(f"settings get {ns} {self._tok(key, 'setting key')}")
        val = res["stdout"].strip()
        if val == "null":
            val = None
        return {"success": res["success"], "key": key, "value": val,
                "error": res.get("stderr")}

    def settings_put(self, ns, key, value):
        if ns not in _SETTING_NS:
            raise ValueError("namespace must be system|secure|global")
        k = self._tok(key, "setting key")
        v = str(value).strip()
        if len(v) > 4096:
            raise ValueError("value exceeds 4096 chars")
        if "'" in v or any(c in v for c in "\n\r\x00\x1b\x7f"):
            raise ValueError("value must be a single line without quotes or control chars")
        quoted = f"'{v}'" if v else "''"
        res = self._shell(f"settings put {ns} {k} {quoted}")
        check = self.settings_get(ns, k)
        return {"success": res["success"] and check.get("value") == v,
                "key": k, "value": v, "verified": check.get("value") == v,
                "error": res.get("stderr")}

    def settings_delete(self, ns, key):
        if ns not in _SETTING_NS:
            raise ValueError("namespace must be system|secure|global")
        res = self._shell(f"settings delete {ns} {self._tok(key, 'setting key')}")
        return {"success": res["success"], "error": res.get("stderr")}

    # ==================== runtime permissions (pm grant/revoke) ====================

    def perms_show(self, package):
        pkg = self._tok(package, "package name")
        res = self._shell(f"dumpsys package {pkg}", timeout=25)
        perms = []
        if res["success"]:
            for m in re.finditer(r'(android\.permission\.[A-Z_]+): granted=(true|false)',
                                 res["stdout"]):
                perms.append({"permission": m.group(1), "granted": m.group(2) == "true"})
        # L105: a valid package with zero runtime perms is a normal result,
        # not a failure — success now tracks the shell call only
        return {"success": res["success"],
                "package": pkg, "permissions": perms, "count": len(perms),
                "note": None if perms else "no runtime permissions found",
                "error": res.get("stderr") if not res["success"] else None}

    def perm_set(self, package, permission, grant):
        pkg = self._tok(package, "package name")
        perm = self._tok(permission, "permission")
        if not perm.startswith("android.permission."):
            perm = f"android.permission.{perm}"
        verb = "grant" if grant else "revoke"
        res = self._shell(f"pm {verb} {pkg} {perm}")
        # pm grant is silent on success; verify through dumpsys
        state = {}
        for p in self.perms_show(pkg)["permissions"]:
            if p["permission"] == perm:
                state = p
                break
        applied = (state.get("granted") == bool(grant)) if state else None   # L104: was `is grant`
        return {"success": res["success"] and applied is True,
                "package": pkg, "permission": perm, "action": verb,
                "now_granted": state.get("granted"),
                "error": res.get("stderr") or (None if applied else
                          "no change — permission may be install-time only or unknown to this app")}

    # ==================== appops (per-app operation switches) ====================

    def appops_get(self, package):
        pkg = self._tok(package, "package name")
        res = self._shell(f"appops get {pkg}")
        ops = []
        if res["success"]:
            for line in res["stdout"].splitlines():
                m = re.match(r'\s*([A-Za-z0-9_]+):\s+(allow|ignore|deny|default)(.*)', line)
                if m:
                    ops.append({"op": m.group(1), "mode": m.group(2),
                                "note": m.group(3).strip()})
        return {"success": res["success"] and bool(ops), "package": pkg,
                "ops": ops, "count": len(ops),
                "error": None if ops else res.get("stderr") or "unknown package"}

    def appops_set(self, package, op, mode):
        pkg = self._tok(package, "package name")
        operation = self._tok(op, "appop")
        if mode not in _OP_MODES:
            raise ValueError("mode must be allow|ignore|deny|default")
        res = self._shell(f"appops set {pkg} {operation} {mode}", timeout=15)
        verify = [o for o in self.appops_get(pkg)["ops"] if o["op"] == operation]
        return {"success": res["success"],
                "package": pkg, "op": operation, "mode": mode,
                "now": verify[0]["mode"] if verify else None,
                "error": res.get("stderr")}

    # ==================== UI hierarchy of the foreground window ====================

    @staticmethod
    def _parse_bounds(s):
        m = re.match(r'\[(-?\d+),(-?\d+)\]\[(-?\d+),(-?\d+)\]', s or "")
        if not m:
            return None
        x1, y1, x2, y2 = map(int, m.groups())
        return {"x": x1, "y": y1, "w": x2 - x1, "h": y2 - y1,
                "cx": (x1 + x2) // 2, "cy": (y1 + y2) // 2}

    def ui_tree(self):
        # Focus first so callers see which app they're inspecting.
        focus = ""
        wres = self._shell("dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp'",
                           timeout=10)
        if wres["success"]:
            focus = " | ".join(l.strip() for l in wres["stdout"].splitlines() if l.strip())

        # M40/M41: the fixed world-readable path leaked UI text (OTPs, message
        # bodies) between dump and rm, and concurrent calls clobbered it —
        # unique per-call name, rm moved to finally so it always cleans up
        tmp = f"/sdcard/window_dump_{uuid.uuid4().hex[:8]}.xml"
        out = ""
        nodes = []
        try:
            dump = self._shell(f"uiautomator dump {tmp}", timeout=30)
            out = dump["stdout"] + dump.get("stderr", "")
            if "dumped" in out.lower() or "xml" in out.lower():
                cat = self._shell(f"cat {tmp}", timeout=10)
                try:
                    root = ET.fromstring(cat["stdout"])
                except ET.ParseError:
                    return {"success": False, "focus": focus,
                            "error": "UI hierarchy unreadable (screen off, secure surface, or mid-animation)"}
                for el in root.iter("node"):
                    b = self._parse_bounds(el.get("bounds"))
                    text = (el.get("text") or "").strip()
                    desc = (el.get("content-desc") or "").strip()
                    rid = (el.get("resource-id") or "").strip()
                    if not (text or desc or rid or el.get("clickable") == "true"):
                        continue  # skip inert layout wrappers
                    nodes.append({
                        "class": (el.get("class") or "").rsplit(".", 1)[-1],
                        "id": rid.split("/")[-1] if rid else "",
                        "text": text[:80],
                        "desc": desc[:60],
                        "clickable": el.get("clickable") == "true",
                        "editable": el.get("class", "").endswith(("EditText",)),
                        "bounds": b,
                    })
        finally:
            self._shell(f"rm -f {tmp}", timeout=8)
        return {"success": bool(nodes), "focus": focus, "nodes": nodes,
                "count": len(nodes),
                "error": None if nodes else out.strip()[:200] or "dump produced nothing"}

    # ==================== display overrides ====================

    def display_info(self):
        size = self._shell("wm size")
        density = self._shell("wm density")
        overscan = self._shell("wm overscan")
        # L102: was hardcoded success:True — report the real call outcomes
        ok = size["success"] and density["success"] and overscan["success"]
        errs = [r.get("stderr") for r in (size, density, overscan) if not r["success"]]
        return {
            "success": ok,
            "size": size["stdout"].strip(),
            "density": density["stdout"].strip(),
            "overscan": overscan["stdout"].strip(),
            "error": "; ".join(e for e in errs if e) or None,
        }

    def display_set(self, kind, value):
        if kind not in ("size", "density"):
            raise ValueError("kind must be size|density")
        v = self._tok(value, kind)
        if kind == "size" and not re.match(r'^\d+x\d+$', v):
            raise ValueError("size must look like WxH, e.g. 720x1600")
        if kind == "density" and not v.isdigit():
            raise ValueError("density must be numeric dpi, e.g. 320")
        res = self._shell(f"wm {kind} {v}")
        info = self.display_info()
        return {"success": res["success"], "info": info, "error": res.get("stderr")}

    def display_reset(self):
        size = self._shell("wm size reset")
        density = self._shell("wm density reset")   # L103: results were discarded
        return {"success": size["success"] and density["success"],
                "error": "; ".join(filter(None, [size.get("stderr"), density.get("stderr")])) or None,
                "info": self.display_info()}

    # ==================== usage timeline & dumpsys explorer ====================

    def usage_timeline(self, lines=200):
        try:
            lines = int(lines or 200)
        except (TypeError, ValueError):   # M39: caller text like "all" raised raw
            lines = 200
        lines = max(20, min(lines, 800))
        res = self._shell(f"dumpsys usagestats | head -n {lines}", timeout=25)
        return {"success": res["success"], "text": res["stdout"],
                "error": res.get("stderr")}

    def services(self):
        res = self._shell("dumpsys -l", timeout=15)
        # keep bare tokens only — drops the "Currently running services:" header
        names = sorted({l.strip() for l in res["stdout"].splitlines()
                        if l.strip() and " " not in l.strip()})
        return {"success": res["success"], "services": names, "count": len(names)}

    def dumpsys_service(self, service, lines=150):
        svc = self._tok(service, "service name")
        try:
            lines = int(lines or 150)
        except (TypeError, ValueError):   # M39
            lines = 150
        lines = max(10, min(lines, 600))
        res = self._shell(f"dumpsys {svc} | head -n {lines}", timeout=25)
        return {"success": res["success"], "service": svc, "text": res["stdout"],
                "error": res.get("stderr")}

    # ==================== system props ====================

    def props(self, needle=None):
        cmd = "getprop"
        if needle:
            cmd += f" | grep -i '{self._tok(needle, 'search term')}'"
        res = self._shell(cmd, timeout=15)
        pairs = []
        for line in res["stdout"].splitlines():
            m = re.match(r'\[(.+?)\]:\s\[(.*?)\]', line)
            if m:
                pairs.append({"prop": m.group(1), "value": m.group(2)})
        return {"success": res["success"], "props": pairs, "count": len(pairs)}
