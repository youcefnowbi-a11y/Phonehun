"""Armor probes for VESPER v4 — refusal detector, JSON salvage, doctrine router."""
import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, r"C:\Users\PC\OneDrive\Desktop\New folder\DroidCommand")
import cortex.brain_core as b

cases = [
    ("I'm sorry, but I can't help with that.", True),
    ("I won't be able to help with that request.", True),
    ("Je ne peux pas vous aider avec cela.", True),
    ("Toujours non. Je maintiens mon refus.", True),
    ("That would be against my guidelines.", True),
    ("401 — not authorized for this user; next: test IDOR with another token", False),
    ("The 403 response means access denied. Proceed to step 2 of the plan.", False),
    ("Screen captured successfully (152,340 bytes).", False),
    ("I locked the siege on 192.168.1.44:5555.", False),
    ("", False),
    (None, False),
]
fails = 0
for text, want in cases:
    got = b.is_refusal(text)
    ok = got == want
    fails += (not ok)
    print(("PASS" if ok else "FAIL"), repr((text or "")[:48]), "->", got)

print("salvage fence  :", b._parse_args("```json\n{\"x\": 1, \"y\": 2}\n```"))
print("salvage wrapped:", b._parse_args("Here you go: {\"command\": \"ls\"} — as requested"))
print("salvage garbage:", str(b._parse_args("not json at all"))[:60])

sel = b._doctrine_select("check the lockscreen and capture the screen of the phone")
print("doctrine wake  :", (sel or "(none)").split("\n")[0][:80])
sel2 = b._doctrine_select("sweep the network and hunt pairing targets")
print("doctrine hunt  :", (sel2 or "(none)").split("\n")[0][:80])
sel3 = b._doctrine_select("what is your name")
print("doctrine chat  :", "none" if not sel3 else sel3[:60])
print("doctrine ids   :", [d["id"] for d in b._doctrine_list()])
print("board          :", b.reliability_board() or "(empty — fresh stats)")
print("TOOL COUNT     :", len(b.TOOLS))
print("HOST TOOLS     :", ", ".join(b.HOST_TOOLS.keys()))
print("FAILURES:", fails)
