"""Retry: adb tls_connection.cpp + boringssl spake25519 via android external pin."""
import base64, urllib.request, os, json

OUT = os.path.join(os.path.dirname(__file__), "aosp")
os.makedirs(OUT, exist_ok=True)

def fetch_text(url, out):
    data = base64.b64decode(urllib.request.urlopen(url, timeout=30).read())
    with open(os.path.join(OUT, out), "wb") as f:
        f.write(data)
    print("OK  ", out, len(data))

ADB = "https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/"
AEXT = "https://android.googlesource.com/platform/external/boringssl/+/refs/heads/main/"
BMAIN = "https://boringssl.googlesource.com/boringssl/+/refs/heads/main/"

for url, out in [
    (ADB + "tls/tls_connection.cpp?format=TEXT", "tls_connection.cpp"),
    (AEXT + "crypto/spake25519/spake25519.c?format=TEXT", "spake25519.c"),
    (AEXT + "crypto/spake25519.c?format=TEXT", "spake25519.c"),
    (AEXT + "crypto/spake25519/spake25519_test.cc?format=TEXT", "spake25519_test.cc"),
    (AEXT + "crypto/spake25519/internal.h?format=TEXT", "spake25519_internal.h"),
    (BMAIN + "crypto/spake25519/spake25519.c?format=TEXT", "spake25519_main.c"),
]:
    try:
        fetch_text(url, out)
    except Exception as e:
        print("FAIL", out, e)
