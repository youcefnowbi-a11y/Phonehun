"""Stage 3 intake classifier — behavioral test (all six arrival states)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cortex import intake


def make_shell(kg, sa, enc=True):
    def _sh(cmd):
        if "window policy" in cmd:
            return {"stdout": kg}
        if "SystemUIService" in cmd or "trust" in cmd:
            return {"stdout": sa}
        if "getprop" in cmd:
            return {"stdout": "[ro.crypto.state]: [encrypted]\n[ro.crypto.metadata]: [mkfs]\n" if enc else ""}
        if "lock_settings" in cmd:
            return {"stdout": "user 0 credential pattern"}
        return {"stdout": ""}
    return _sh


CASES = [
    ("AFU-UNLOCKED", "device", "keyguardShowing=false mKeyguardOccluded=false", "strongAuthRequired=0x0", "user 0 credential pattern"),
    ("AFU-LOCKED", "device", "keyguardShowing=true keyguardSecure=true", "strongAuthRequired=0x0", "user 0 credential pattern"),
    ("BFU", "device", "keyguardShowing=true keyguardSecure=true", "strongAuthRequired=0x8", "user 0 credential pattern"),
    ("AFU-INSECURE", "device", "keyguardShowing=true keyguardSecure=false", "strongAuthRequired=0x0", "user 0 credential none"),
    ("UNAUTHORIZED-USB", "unauthorized", "keyguardShowing=true", "strongAuthRequired=0x8", "user 0 credential pattern"),
    ("NO-ADB", None, "keyguardShowing=true", "strongAuthRequired=0x8", "user 0 credential pattern"),
]

ok = 0
for expect, adb, kg, sa, ls in CASES:
    devs = {"devices": [{"serial": "X", "status": adb}]} if adb else {"devices": []}
    sh = make_shell(kg, sa)
    sh_orig = sh

    def make_shell2(kg, sa, ls):
        def _sh(cmd):
            if "lock_settings" in cmd:
                return {"stdout": ls}
            return sh_orig(cmd)
        return _sh

    r = intake.classify(make_shell2(kg, sa, ls), list_devices_result=devs, adb_state=adb, serial="X")
    v = r["verdict"]
    mark = "PASS" if v == expect else "FAIL"
    ok += (v == expect)
    fronts = len(r["front_order"])
    print(f"{mark}: {expect:18} -> got {v:18} | fronts: {fronts}")
print(f"{ok}/6 VERDICTS CORRECT")
