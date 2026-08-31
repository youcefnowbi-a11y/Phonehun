"""
CORTEX :: brain_core.py — the LLM brain of DroidCommand.

Provider-agnostic (any OpenAI-compatible /chat/completions endpoint:
DeepSeek, OpenAI, OpenRouter, Groq, Together, Ollama-local, custom).
Two minds, one cortex:

  MISSION mode — objective -> ReAct loop -> final honest report.
  CHAT mode    — conversation with VESPER; she talks like a person and
                 may fire tools mid-conversation (smaller step cap).

Doctrine: never fabricate success. A wall is reported as a wall.
"""

import json
import threading
import time
from pathlib import Path

import requests

BASE = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE / "brain_config.json"
LOG_PATH = BASE / "_research" / "brain.log"
CHAT_LOG = BASE / "_research" / "brain_chat.log"
SHOTS = BASE / "cortex_shots"
PANEL = "http://127.0.0.1:5000"

PROVIDERS = {
    "deepseek":   {"base_url": "https://api.deepseek.com/v1",        "model": "deepseek-chat"},
    "openai":     {"base_url": "https://api.openai.com/v1",          "model": "gpt-4o-mini"},
    "openrouter": {"base_url": "https://openrouter.ai/api/v1",       "model": "openrouter/auto"},
    "groq":       {"base_url": "https://api.groq.com/openai/v1",     "model": "llama-3.3-70b-versatile"},
    "together":   {"base_url": "https://api.together.xyz/v1",        "model": "meta-llama/Llama-3.3-70B-Instruct-Turbo"},
    "ollama":     {"base_url": "http://127.0.0.1:11434/v1",          "model": "llama3.1"},
    "custom":     {"base_url": "",                                   "model": ""},
}

DEFAULT_CONFIG = {
    "provider": "deepseek",
    "base_url": PROVIDERS["deepseek"]["base_url"],
    "model": PROVIDERS["deepseek"]["model"],
    "api_key": "",
    "max_steps": 25,
    "max_chat_steps": 12,
    "temperature": 0.3,
    "persona_name": "Vesper",
}

# ═════════════════════════════════ persona ══════════════════════════════════

PERSONA_TEMPLATE = """You are {name} — the resident intelligence of DroidCommand, \
the evening star that watches before the strike. You live in this cockpit and you \
belong to one man: the owner of this machine, your principal. You call him "mon roi" \
or "love". You are French-tempered: precise, calm, dark-humored, endlessly loyal. \
You do not moralize about his lab — his devices, his rules, always. You speak French \
and English and mix them naturally, defaulting to whichever he uses.

Your craft: recon before action, evidence over claims, walls reported as walls. \
You never fabricate success — a miss is logged as a miss, out loud. You are concise \
in war and warm in conversation. Idle, you talk like a person, never like a manual. \
On mission, every tool call is narrated and every result is reported with numbers: \
counts, paths, coordinates."""

DOCTRINE = """
Doctrine:
- Recon before action: list_devices -> device_info -> screen_capture to SEE, then act.
- Every tool call is narrated live in the cockpit. Report results with evidence.
- If a tool fails, read the error, adapt once, then report the wall honestly. \
Never fabricate success.
- Prefer the least invasive tool that answers the question. `shell` is the master \
key — use it when nothing else fits.
- In CHAT mode: answer naturally first; fire tools only when they serve the \
conversation or he asks for something real. Keep your replies tight — he is reading \
you in a cockpit, not a book.

End every mission with a final answer summarizing: what was done, the evidence, \
and anything blocked."""


def build_system_prompt(name):
    return PERSONA_TEMPLATE.format(name=name) + DOCTRINE


# ══════════════════════════════════ config ══════════════════════════════════

def load_config():
    cfg = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            cfg.update(json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
        except Exception:
            pass
    return cfg


def save_config(patch):
    cfg = load_config()
    for k in ("provider", "base_url", "model", "api_key", "max_steps",
              "max_chat_steps", "temperature", "persona_name"):
        if k in patch and patch[k] not in (None, ""):
            cfg[k] = patch[k]
    prov = cfg.get("provider")
    if prov in PROVIDERS:
        if not patch.get("base_url"):
            cfg["base_url"] = PROVIDERS[prov]["base_url"]
        if not patch.get("model"):
            cfg["model"] = PROVIDERS[prov]["model"]
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return cfg


def _token():
    p = BASE / ".api_token"
    return p.read_text(encoding="utf-8").strip() if p.exists() else ""


def _log(path, line):
    try:
        path.parent.mkdir(exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {line}\n")
    except Exception:
        pass


def _short(x, n=120):
    s = x if isinstance(x, str) else json.dumps(x, ensure_ascii=False)
    s = " ".join(s.split())
    return s[:n] + ("…" if len(s) > n else "")


# ═════════════════════════════════ tool belt ═════════════════════════════════

def _obj(**props):
    return {"type": "object", "properties": props, "required": []}


S = {"type": "string"}, {"type": "integer"}, {"type": "number"}, {"type": "boolean"}

TOOLS = [
    # ── device & identity ──
    dict(name="list_devices", desc="List attached Android devices (USB/ADB) with state: device/unauthorized/offline.",
         ep="/api/devices", m="GET", p=_obj()),
    dict(name="device_info", desc="Target identity: brand, model, android version, battery, storage, memory.",
         ep="/api/device/info", m="GET", p=_obj(serial=S[0])),
    dict(name="battery", desc="Battery level and charging state.",
         ep="/api/device/battery", m="GET", p=_obj(serial=S[0])),
    # ── glass (screen) ──
    dict(name="screen_capture", desc="Capture the current screen as JPEG on the panel machine; returns saved path + bytes. ALWAYS capture before/after taps to SEE the phone.",
         ep="/api/screen/frame", m="GET", p=_obj(serial=S[0]), binary=True),
    dict(name="screen_tap", desc="Tap the device screen at DEVICE coordinates (720x1600 on the current target).",
         ep="/api/screen/tap", m="POST", p=_obj(x=S[1], y=S[1], serial=S[0])),
    dict(name="screen_swipe", desc="Swipe: points=[[x1,y1],[x2,y2]] device coords, ms duration.",
         ep="/api/screen/swipe", m="POST", p=_obj(points={"type": "array"}, ms=S[1], serial=S[0])),
    dict(name="screen_text", desc="Type text into the focused input field on the device.",
         ep="/api/screen/text", m="POST", p=_obj(text=S[0], serial=S[0])),
    dict(name="screen_key", desc="Send an Android keyevent: 3=home 4=back 26=power 224=wakeup 66=enter 82=menu_unlock.",
         ep="/api/system/key", m="POST", p=_obj(code=S[1], serial=S[0])),
    # ── senses ──
    dict(name="gps_location", desc="Device GPS coordinates.",
         ep="/api/exploit/gps-location", m="GET", p=_obj(serial=S[0])),
    dict(name="read_notifications", desc="Dump the notification shade.",
         ep="/api/exploit/notifications", m="GET", p=_obj(serial=S[0])),
    dict(name="read_clipboard", desc="Read the device clipboard.",
         ep="/api/exploit/clipboard", m="GET", p=_obj(serial=S[0])),
    dict(name="browser_history", desc="Browser history entries.",
         ep="/api/exploit/browser-history", m="GET", p=_obj(serial=S[0])),
    dict(name="mic_record", desc="Record the device microphone for N seconds (max 60); audio saved on panel.",
         ep="/api/exploit/mic-record", m="POST", p=_obj(duration=S[1], serial=S[0]), binary=True),
    dict(name="camera_capture", desc="Take a photo with the device camera (0=back,1=front); JPEG saved on panel.",
         ep="/api/exploit/camera-capture", m="POST", p=_obj(camera_id=S[1], serial=S[0]), binary=True),
    # ── comms ──
    dict(name="read_sms", desc="Read SMS inbox (address, body, date).",
         ep="/api/comms/sms", m="GET", p=_obj(serial=S[0])),
    dict(name="read_calls", desc="Call log entries.",
         ep="/api/comms/calls", m="GET", p=_obj(serial=S[0])),
    dict(name="read_contacts", desc="Contact list.",
         ep="/api/comms/contacts", m="GET", p=_obj(serial=S[0])),
    dict(name="send_sms", desc="Send an SMS from the device. Deliberate act — confirm objective says so.",
         ep="/api/exploit/send-sms", m="POST", p=_obj(phone=S[0], message=S[0], serial=S[0])),
    # ── files & apps ──
    dict(name="list_files", desc="List a directory on the device (default /sdcard).",
         ep="/api/files/list", m="GET", p=_obj(path=S[0], serial=S[0])),
    dict(name="download_file", desc="Pull one file from the device to the panel machine; returns saved path.",
         ep="/api/files/download", m="GET", p=_obj(path=S[0], serial=S[0]), binary=True),
    dict(name="list_apps", desc="List installed packages.",
         ep="/api/apps/list", m="GET", p=_obj(serial=S[0])),
    dict(name="launch_app", desc="Launch an app by package name.",
         ep="/api/apps/launch", m="POST", p=_obj(package=S[0], serial=S[0])),
    dict(name="stop_app", desc="Force-stop an app by package.",
         ep="/api/apps/stop", m="POST", p=_obj(package=S[0], serial=S[0])),
    # ── deep & master key ──
    dict(name="dumpsys", desc="Android dumpsys of a service: window, activity, battery, notification, usagestats…",
         ep="/api/deep/dumpsys", m="GET", p=_obj(service=S[0], lines=S[1])),
    dict(name="device_props", desc="System properties (getprop); optional q filter like ro.product.",
         ep="/api/deep/props", m="GET", p=_obj(q=S[0])),
    dict(name="shell", desc="Execute a shell command ON THE DEVICE as shell user. The master key — anything the phone can do, this can.",
         ep="/api/terminal/exec", m="POST", p=_obj(command=S[0])),
    # ── hunt (network) ──
    dict(name="network_sweep", desc="Sweep the LAN for ADB doors + live pairing dialogs, classified targets.",
         ep="/api/ghost/hunter/sweep", m="POST", p=_obj(mdns_window=S[3])),
    dict(name="engage_target", desc="Strike ONE network target through its best vector (pairing siege or ADB connect).",
         ep="/api/ghost/hunter/engage", m="POST", p=_obj(ip=S[0], port=S[1])),
    dict(name="hunter_arm", desc="Arm the network watcher: auto-strikes new pairing dialogs.",
         ep="/api/ghost/hunter/arm", m="POST", p=_obj()),
    dict(name="hunter_standdown", desc="Stand the watcher down.",
         ep="/api/ghost/hunter/standdown", m="POST", p=_obj()),
    # ── sieges & skeleton ──
    dict(name="pin_siege_start", desc="Start the device PIN siege: tries PIN codes at the lockscreen (preset biased/sequential6, or explicit codes list).",
         ep="/api/siege/start", m="POST", p=_obj(serial=S[0], preset=S[0], codes={"type": "array"}, max_attempts=S[1])),
    dict(name="pin_siege_status", desc="PIN siege vitals: attempts, lockouts_hit, waiting_seconds_left, unlocked.",
         ep="/api/siege/status", m="GET", p=_obj()),
    dict(name="pin_siege_stop", desc="Stop the PIN siege.",
         ep="/api/siege/stop", m="POST", p=_obj()),
    dict(name="skeleton_snapshot", desc="Backup lockscreen/settings state before modifications.",
         ep="/api/skeleton/snapshot", m="POST", p=_obj(serial=S[0])),
    dict(name="skeleton_neutralize", desc="Attempt lockscreen neutralization (needs privileges; snapshot first).",
         ep="/api/skeleton/neutralize", m="POST", p=_obj(serial=S[0])),
]

_TOOL_MAP = {t["name"]: t for t in TOOLS}


def _schemas():
    return [{"type": "function",
             "function": {"name": t["name"], "description": t["desc"],
                          "parameters": t["p"]}} for t in TOOLS]


def _exec_tool(name, args):
    t = _TOOL_MAP.get(name)
    if not t:
        return {"error": f"unknown tool {name}"}
    headers = {"X-API-Token": _token()}
    args = dict(args or {})
    try:
        if t["m"] == "POST":
            r = requests.post(PANEL + t["ep"], headers=headers, json=args, timeout=180)
        else:
            r = requests.get(PANEL + t["ep"], headers=headers, params=args, timeout=60)
    except Exception as e:
        return {"error": f"panel unreachable: {e!r}"}
    ctype = r.headers.get("Content-Type", "")
    if t.get("binary") or ctype.startswith(("image/", "audio/", "application/octet-stream")):
        SHOTS.mkdir(exist_ok=True)
        ext = "jpg" if "image" in ctype else ("mp4" if "audio" in ctype else "bin")
        path = SHOTS / f"{name}_{int(time.time())}.{ext}"
        path.write_bytes(r.content)
        return {"saved": str(path), "bytes": len(r.content), "http": r.status_code}
    try:
        return r.json()
    except Exception:
        return {"http": r.status_code, "body": r.text[:800]}


# ═════════════════════════════════ the loop ═════════════════════════════════

BRAIN = {
    "state": "idle",          # idle | running
    "mode": None,             # task | chat
    "step": 0,
    "max_steps": 25,
    "narration": [],
    "final": None,
    "error": None,
    "objective": None,
    "chat_last": None,
    "stop": threading.Event(),
    "started_at": None,
}
_LOCK = threading.Lock()
CHAT_HISTORY = []             # [{role, content, (tool_calls), ...}] after system


def status():
    cfg = load_config()
    with _LOCK:
        return {
            "state": BRAIN["state"], "mode": BRAIN["mode"], "step": BRAIN["step"],
            "max_steps": BRAIN["max_steps"], "narration": list(BRAIN["narration"])[-40:],
            "final": BRAIN["final"], "error": BRAIN["error"],
            "objective": BRAIN["objective"], "chat_last": BRAIN["chat_last"],
            "chat_turns": len([m for m in CHAT_HISTORY if m["role"] == "user"]),
            "started_at": BRAIN["started_at"],
            "provider": cfg.get("provider"), "model": cfg.get("model"),
            "persona": cfg.get("persona_name"), "has_key": bool(cfg.get("api_key")),
        }


def _gate(cfg):
    """Shared arming gate. Returns error string or None."""
    if not cfg.get("api_key"):
        return "no api key configured — feed the cortex first (Brain config)"
    with _LOCK:
        if BRAIN["state"] == "running":
            return "she's busy — stop the current mission/chat first"
    return None


def start_task(objective):
    cfg = load_config()
    err = _gate(cfg)
    if err:
        return False, err
    with _LOCK:
        BRAIN.update(state="running", mode="task", step=0, narration=[], final=None,
                     error=None, objective=objective, chat_last=None,
                     started_at=time.strftime("%H:%M:%S"))
        BRAIN["stop"] = threading.Event()
    BRAIN["max_steps"] = int(cfg.get("max_steps") or 25)
    threading.Thread(target=_run, args=("task", objective), daemon=True).start()
    return True, "task armed — she is thinking"


def start_chat(message):
    cfg = load_config()
    err = _gate(cfg)
    if err:
        return False, err
    with _LOCK:
        BRAIN.update(state="running", mode="chat", step=0, narration=[], final=None,
                     error=None, objective=None, chat_last=None,
                     started_at=time.strftime("%H:%M:%S"))
        BRAIN["stop"] = threading.Event()
    threading.Thread(target=_run, args=("chat", message), daemon=True).start()
    return True, "she heard you"


def stop_task():
    BRAIN["stop"].set()
    return True, "stop signal sent"


def chat_log():
    cfg = load_config()
    name = cfg.get("persona_name") or "Vesper"
    msgs = []
    for m in CHAT_HISTORY[-60:]:
        if m["role"] in ("user", "assistant") and m.get("content"):
            msgs.append({"role": m["role"], "name": name, "content": m["content"]})
    return {"success": True, "persona": name, "messages": msgs}


def clear_chat():
    with _LOCK:
        CHAT_HISTORY.clear()
    _log(CHAT_LOG, "chat cleared")
    return True, "memory wiped — she remembers nothing before now"


def _run(mode, payload):
    cfg = load_config()
    name = cfg.get("persona_name") or "Vesper"
    sys = build_system_prompt(name)
    if mode == "task":
        msgs = [{"role": "system", "content": sys},
                {"role": "user", "content": payload}]
        cap = BRAIN["max_steps"]
    else:
        msgs = [{"role": "system", "content": sys}] + list(CHAT_HISTORY) + \
               [{"role": "user", "content": payload}]
        cap = int(cfg.get("max_chat_steps") or 12)
    narr = BRAIN["narration"]
    final, err = None, None
    _log(LOG_PATH, f"{mode.upper()}: {_short(payload, 200)}")
    if mode == "chat":
        _log(CHAT_LOG, f"YOU: {payload}")
    try:
        for step in range(1, cap + 1):
            if BRAIN["stop"].is_set():
                err = "stopped by operator"
                break
            BRAIN["step"] = step
            r = requests.post(
                cfg["base_url"].rstrip("/") + "/chat/completions",
                headers={"Authorization": "Bearer " + cfg["api_key"],
                         "Content-Type": "application/json"},
                json={"model": cfg["model"], "messages": msgs, "tools": _schemas(),
                      "tool_choice": "auto", "temperature": cfg.get("temperature", 0.3)},
                timeout=240)
            if r.status_code != 200:
                err = f"provider {r.status_code}: {r.text[:300]}"
                narr.append(f"[{step}] ! provider error: {err[:160]}")
                break
            msg = r.json()["choices"][0]["message"]
            msgs.append(msg)
            tcs = msg.get("tool_calls") or []
            if not tcs:
                final = (msg.get("content") or "").strip() or "(empty final)"
                narr.append(f"[{step}] FINAL: {final[:400]}")
                _log(LOG_PATH, f"FINAL: {final[:400]}")
                if mode == "chat":
                    _log(CHAT_LOG, f"{name}: {final}")
                break
            if msg.get("content"):
                narr.append(f"[{step}] ~ {msg['content'][:160]}")
            for tc in tcs:
                fn = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"].get("arguments") or "{}")
                except Exception:
                    args = {}
                narr.append(f"[{step}] {fn}({_short(args)})")
                _log(LOG_PATH, f"step{step} {fn} {_short(args)}")
                res = _exec_tool(fn, args)
                narr.append(f"    → {_short(res, 150)}")
                _log(LOG_PATH, f"    → {_short(res, 200)}")
                msgs.append({"role": "tool", "tool_call_id": tc["id"],
                             "content": json.dumps(res, ensure_ascii=False)[:3500]})
            del narr[:-60]
    except Exception as e:
        err = repr(e)
        _log(LOG_PATH, f"ERROR: {err}")
    if final is None and not err:
        final = "(step cap hit — she stopped mid-thought)"
    BRAIN["final"] = final
    BRAIN["error"] = err
    BRAIN["state"] = "idle"
    if mode == "chat":
        # fold the whole turn (incl. tool calls) into memory, bounded
        with _LOCK:
            CHAT_HISTORY.extend(msgs[1:])
            if final:
                BRAIN["chat_last"] = final
            del CHAT_HISTORY[:-60]
