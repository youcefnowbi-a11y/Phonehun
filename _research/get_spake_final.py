"""Fetch spake25519.c + test vectors from android14 pin (curve25519 dir)."""
import base64, urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
BSSL = "https://android.googlesource.com/platform/external/boringssl/+/refs/heads/android14-release/"
for f, out in [
    ("src/crypto/curve25519/spake25519.c", "spake25519.c"),
    ("src/crypto/curve25519/spake25519_test.cc", "spake25519_test.cc"),
    ("src/crypto/curve25519/internal.h", "curve25519_internal.h"),
]:
    try:
        data = base64.b64decode(urllib.request.urlopen(BSSL + f + "?format=TEXT", timeout=30).read())
        with open(os.path.join(OUT, out), "wb") as fh:
            fh.write(data)
        print("OK  ", out, len(data), "bytes")
    except Exception as e:
        print("FAIL", out, e)
