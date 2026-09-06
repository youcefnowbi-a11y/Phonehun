"""
CORTEX :: brain_api.py â€” HTTP surface of the LLM brain (VESPER).

/api/brain/config      GET/POST  provider, model, base_url, api_key, caps, persona_name
/api/brain/task        POST      {"objective": "..."} â€” mission mode
/api/brain/chat        GET       conversation history with VESPER
/api/brain/chat        POST      {"message": "..."} â€” chat mode (tools allowed)
/api/brain/chat/clear  POST      wipe her memory
/api/brain/status      GET       state, mode, step, narration, final, error
/api/brain/stop        POST      stop signal
/api/brain/say         POST      {"message": "..."} â€” whisper MID-mission into her
                                 inbox (drained next step) or start a chat when idle
"""

from flask import Blueprint, jsonify, request

from cortex import brain_core
from cortex import registry as _registry   # v6 Stage 1: import at module level â€”
# brain_core only lazy-imports it inside _exec_tool, so brain_core.registry
# does not exist as an attribute and route handlers 500'd (bug caught by smoke).

brain_bp = Blueprint("brain", __name__, url_prefix="/api/brain")


@brain_bp.route("/config", methods=["GET"])
def brain_config_get():
    # fix: missing/unreadable memory file -> serve empty defaults, not a 500.
    try:
        cfg = brain_core.load_config()
    except OSError:
        cfg = {}
    key = cfg.get("api_key") or ""
    return jsonify({
        "success": True,
        "provider": cfg.get("provider"),
        "base_url": cfg.get("base_url"),
        "model": cfg.get("model"),
        "max_steps": cfg.get("max_steps"),
        "max_chat_steps": cfg.get("max_chat_steps"),
        "temperature": cfg.get("temperature"),
        "persona_name": cfg.get("persona_name"),
        "has_key": bool(key),
    })


@brain_bp.route("/config", methods=["POST"])
def brain_config_post():
    data = request.get_json(silent=True) or {}
    # fix: reject non-dict bodies â€” save_config expects a mapping.
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "JSON object required"}), 400
    try:
        cfg = brain_core.save_config(data)
    except Exception as e:  # fix: write failures -> clean 400, not a 500
        return jsonify({"success": False, "error": f"Config save failed: {e}"}), 400
    key = cfg.get("api_key") or ""
    return jsonify({"success": True, "provider": cfg.get("provider"),
                    "model": cfg.get("model"), "base_url": cfg.get("base_url"),
                    "max_steps": cfg.get("max_steps"),
                    "persona_name": cfg.get("persona_name"), "has_key": bool(key)})


@brain_bp.route("/task", methods=["POST"])
def brain_task():
    data = request.get_json(silent=True) or {}
    obj = (data.get("objective") or "").strip()
    if not obj:
        return jsonify({"success": False, "error": "objective requise"}), 400
    ok, msg = brain_core.start_task(obj)
    return jsonify({"success": ok, "message": msg}), (200 if ok else 409)


@brain_bp.route("/chat", methods=["GET"])
def brain_chat_get():
    return jsonify(brain_core.chat_log())


@brain_bp.route("/chat", methods=["POST"])
def brain_chat_post():
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"success": False, "error": "message vide"}), 400
    ok, resp = brain_core.start_chat(msg)
    return jsonify({"success": ok, "message": resp}), (200 if ok else 409)


@brain_bp.route("/chat/clear", methods=["POST"])
def brain_chat_clear():
    ok, msg = brain_core.clear_chat()
    return jsonify({"success": ok, "message": msg})


@brain_bp.route("/status")
def brain_status():
    return jsonify(brain_core.status())


@brain_bp.route("/stop", methods=["POST"])
def brain_stop():
    ok, msg = brain_core.stop_task()
    return jsonify({"success": ok, "message": msg})


@brain_bp.route("/say", methods=["POST"])
def brain_say():
    """Operator channel: mid-mission whisper (drained per step) or chat when idle.
    '__ABORT__' folds the campaign from inside her own loop."""
    data = request.get_json(silent=True) or {}
    msg = (data.get("message") or "").strip()
    if not msg:
        return jsonify({"success": False, "error": "message vide"}), 400
    ok, resp = brain_core.say(msg)
    return jsonify({"success": ok, "message": resp}), (200 if ok else 409)


# â”€â”€ VESPER v6 STAGE 1 â€” registry danger gates + operator sign-off â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# The cortex's dispatch gate lives in cortex/registry.py; these routes are the
# cockpit's hands on that gate. Destructive/flash calls park with a signoff_id;
# the operator approves here and the retried call fires exactly once.

@brain_bp.route("/signoffs", methods=["GET"])
def brain_signoffs():
    return jsonify({"success": True,
                    "pending": _registry.pending_signoffs()})


@brain_bp.route("/signoff/approve", methods=["POST"])
def brain_signoff_approve():
    data = request.get_json(silent=True) or {}
    sid = (data.get("signoff_id") or "").strip()
    if not sid:
        return jsonify({"success": False, "error": "signoff_id required"}), 400
    ok, msg = _registry.approve_signoff(sid)
    return jsonify({"success": ok, "message": msg}), (200 if ok else 404)


@brain_bp.route("/signoff/decline", methods=["POST"])
def brain_signoff_decline():
    data = request.get_json(silent=True) or {}
    sid = (data.get("signoff_id") or "").strip()
    if not sid:
        return jsonify({"success": False, "error": "signoff_id required"}), 400
    ok, msg = _registry.decline_signoff(sid)
    return jsonify({"success": ok, "message": msg}), (200 if ok else 404)


@brain_bp.route("/registry", methods=["GET"])
def brain_registry():
    reg = _registry.load_registry()
    tools = [{"name": t.get("name"), "plane": t.get("plane"),
              "danger_class": t.get("danger_class"), "interface": t.get("interface")}
             for t in reg.get("tools", [])]
    return jsonify({"success": True, "count": len(tools), "tools": tools})


@brain_bp.route("/memory", methods=["GET"])
def brain_memory():
    """Serve Vesper's live memory organs: casefile, lessons, identity, skills."""
    from pathlib import Path
    section = request.args.get("section", "casefile").strip().lower()
    cortex_dir = Path(__file__).parent
    mem_dir = cortex_dir / "memory"
    skills_dir = cortex_dir / "skills"

    if section in ("casefile", "lessons", "identity"):
        p = (mem_dir / f"{section}.md").resolve()
        # Defense-in-depth: allowlisted section must resolve inside mem_dir.
        if p.parent != mem_dir.resolve():
            return jsonify({"success": False, "error": "Invalid memory section"}), 404
        # fix: missing dir/file or read failure -> serve empty default, not 500.
        try:
            content = p.read_text(encoding="utf-8", errors="replace") if p.exists() else f"# {section.upper()}\nNo {section} entries recorded yet."
        except OSError:
            content = f"# {section.upper()}\nNo {section} entries recorded yet."
        return jsonify({"success": True, "section": section, "content": content})
    elif section == "skills":
        skills_text = ["# CRYSTALLIZED SKILLS (Python Tools)"]
        if skills_dir.exists():
            for f in sorted(skills_dir.glob("*.py")):
                if f.name.startswith("__"):
                    continue
                # fix: unreadable/ vanished skill file -> skip it, not a 500.
                try:
                    with open(f, "r", encoding="utf-8", errors="replace") as fh:
                        # Cap the preview read at 4 KB â€” don't slurp huge skill files.
                        first_lines = "\n".join(fh.read(4096).splitlines()[:6])
                except OSError:
                    continue
                skills_text.append(f"### {f.stem}\n```python\n{first_lines}\n```")
        content = "\n\n".join(skills_text) if len(skills_text) > 1 else "No custom skills compiled yet."
        return jsonify({"success": True, "section": section, "content": content})
    return jsonify({"success": False, "error": f"Unknown memory section: {section}"}), 400
