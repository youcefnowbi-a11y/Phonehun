"""Dep check for the QR pairing gate: zeroconf (mDNS advertise) + segno (QR SVG)."""
import importlib.util
import sys

for mod in ("zeroconf", "segno", "cryptography", "OpenSSL"):
    spec = importlib.util.find_spec(mod)
    print(f"{mod:14s} {'OK' if spec else 'MISSING'}")

sys.exit(0)
