"""_research/test_warroom.py — functional gate for the VESPER v5 transplant."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cortex.playbook as pb                      # noqa: E402
import cortex.brain_core as bc                    # noqa: E402

pb.STORE = os.path.join(os.getcwd(), "_research", "test_plays.json")
if os.path.exists(pb.STORE):
    os.remove(pb.STORE)

# ── distillery: record, dedupe, reject-noise, recall ──
seq = [("list_devices", True), ("device_info", True),
       ("screen_capture", True), ("screen_tap", True)]
a = pb.record("take a screenshot of his phone", seq)
b = pb.record("screenshot the phone screen now", seq)   # same grammar → strengthen
c = pb.record("short one", [("list_devices", True)])    # too short → reject
blk = pb.recall_block("grab a photo of the current screen")
print("record new:", a, "| dedupe:", (b is False), "| too-short rejected:", (c is False))
print("play_count:", pb.play_count())
print("recall has PROVEN SEQUENCES:", "PROVEN SEQUENCES" in blk,
      "| has chain:", ("list_devices" in blk and "screen_tap" in blk))

# ── fingerprint + coverage law ──
print("fingerprint sms:", pb.fingerprint("read his sms messages"))
cov = pb.coverage_order(8, [("list_devices", True)], "read his sms messages", ignored=0)
print("coverage order fired:", "COVERAGE ORDER" in cov, "| names read_sms:", "read_sms" in cov)
cov_ok = pb.coverage_order(8, [("read_sms", True)], "read his sms messages", ignored=0)
print("covered bench silent:", cov_ok == "")
print("discovery true:", pb.discovery('{"count": 3}'),
      "| discovery false:", pb.discovery('{"count": 0}'))
print("bench of shell:", pb.bench_of("shell"))

# ── brain_core: the war-room split ──
sys_chat = bc.build_system_prompt("Vesper", "", "chat")
sys_task = bc.build_system_prompt("Vesper", "", "task")
print("chat has WAR ROOM doctrine:", "WAR ROOM" in sys_chat,
      "| chat clean of war doctrine:", "Recon before action" not in sys_chat)
print("task has war doctrine:", "Recon before action" in sys_task,
      "| task clean of war room:", "WAR ROOM (conversation" not in sys_task)
full, chat = bc._schemas(), bc._schemas("chat")
trimmed = sorted({t["function"]["name"] for t in full} -
                 {t["function"]["name"] for t in chat})
print("full belt:", len(full), "| chat belt:", len(chat), "| trimmed:", trimmed)
print("chat whisper silent:", "no device probes" in bc._chat_whisper())
print("recipe card present:", "TOOL GRAMMAR" in pb.recipe_block())
print("OK: all organ tests executed")
