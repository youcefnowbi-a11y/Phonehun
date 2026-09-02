"""
CORTEX :: brain_api.py — HTTP surface of the LLM brain (VESPER).

/api/brain/config      GET/POST  provider, model, base_url, api_key, caps, persona_name
/api/brain/task        POST      {"objective": "..."} — mission mode
/api/brain/chat        GET       conversation history with VESPER
/api/brain/chat        POST      {"message": "..."} — chat mode (tools allowed)
/api/brain/chat/clear  POST      wipe her memory
/api/brain/status      GET       state, mode, step, narration, final, error
/api/brain/stop        POST      stop signal
/api/brain/say         POST      {"message": "..."} — whisper MID-mission into her
                                 inbox (drained next step) or start a chat when idle
"""

from flask import Blueprint, jsonify, request

from cortex import brain_core

brain_bp = Blueprint("brain", __name__, url_prefix="/api/brain")


@brain_bp.route("/config", methods=["GET"])
def brain_config_get():
    cfg = brain_core.load_config()
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
        "key_tail": key[-4:] if key else "",
    })


@brain_bp.route("/config", methods=["POST"])
def brain_config_post():
    data = request.get_json(silent=True) or {}
    cfg = brain_core.save_config(data)
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
