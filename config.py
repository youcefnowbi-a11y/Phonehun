import shutil
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# Persistent API token: generated once, reused across restarts so the UI stays paired.
TOKEN_FILE = BASE_DIR / ".api_token"
if TOKEN_FILE.exists():
    API_TOKEN = TOKEN_FILE.read_text(encoding="utf-8").strip()
else:
    API_TOKEN = secrets.token_urlsafe(32)
    TOKEN_FILE.write_text(API_TOKEN, encoding="utf-8")

# Find ADB executable
user_home = Path.home()
custom_adb_path = user_home / "Downloads" / "platform-tools" / "adb.exe"

if custom_adb_path.exists():
    ADB_PATH = str(custom_adb_path)
elif shutil.which("adb"):
    ADB_PATH = "adb"
else:
    ADB_PATH = str(custom_adb_path)

HOST = "127.0.0.1"
PORT = 5000
DEBUG = False
