"""Fetch tls_connection.cpp (exporter label) + BoringSSL spake25519.c + its test vectors."""
import urllib.request, os

OUT = os.path.join(os.path.dirname(__file__), "aosp")
os.makedirs(OUT, exist_ok=True)

def fetch(url, out):
    data = urllib.request.urlopen(url, timeout=30).read()
    with open(os.path.join(OUT, out), "wb") as f:
        f.write(data)
    print("OK  ", out, len(data))

ADB = "https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/"
BSSL_GS = "https://boringssl.googlesource.com/boringssl/+/refs/heads/main/"
BSSL_GH = "https://raw.githubusercontent.com/google/boringssl/master/"

try:
    fetch(ADB + "tls/tls_connection.cpp?format=TEXT", "tls_connection.cpp.b64")
except Exception as e:
    print("FAIL tls_connection.cpp", e)
for path, out in [
    ("crypto/spake25519/spake25519.c", "spake25519.c"),
    ("crypto/spake25519/spake25519_test.cc", "spake25519_test.cc"),
]:
    try:
        fetch(BSSL_GH + path, out)
    except Exception as e:
        print("FAIL GH", path, e)
        try:
            fetch(BSSL_GS + path + "?format=TEXT", out)
            print(" (note: got base64 from googlesource)")
        except Exception as e2:
            print("FAIL GS", path, e2)
