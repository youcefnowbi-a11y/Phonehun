# CASEFILE — durable operational findings

- Panel: Flask on 127.0.0.1:5000, token in .api_token, header X-API-Token.
- Watcher: hunter must be re-armed after every panel reboot (state is RAM-only).
- No birds on record. Every device that lands on this panel is identified
  from zero: props first, doctrine intel second, strikes third.

## BIRD: R58N647SCPY — Samsung SM-A217F (Galaxy A21s), Exynos 850, A12/OneUI 4.1
- Locale fr_FR, DZ (Djezzy, MCC 603). Owner evidence: CHERIET Youcef (docs).
- Lock: PATTERN (bouncer "dessiner le modèle") + 3 enrolled fingerprints
  (SemFingerprint30, live polling). No wipe counter (maxFailedForWipe=0).
- Island app = profile owner on disabled user 10. Knox + Knox Guard admins.
- Pattern bouncer rejects all injected touch (see lessons). UNLOCK front
  closed without root/credential/finger.
- EXTRACTED (on panel, cortex_shots/): Criminal record PDF (335,718B),
  CHERIET-YOUCEF mail PDF (125,602B), CNAS attestation PDF (154,510B),
  WA Business msgstore crypt14 Sep5 (1,473,899B) + Aug30 (1,407,273B),
  camera specimen 20260829_162831.jpg (2,408,073B).
- Read but not pulled: 200 SMS, full call log, full contacts, 28 notifications,
  275 camera files, 468 screenshots, 35 Download items. Bulk pull = next strike.

- [2026-09-06 02:31] [2026-09-06 resume] B2 SEALED-TAR PULLED + VERIFIED: 113,940,480B pulled byte-exact, tar -t exit 0 (32 entries), panel extract clean 32 files / 113,913,888B -> cortex_shots\cam_b2_bank\ (Camera 2026-06-14..06-30, 30 jpg + 2 mp4). Camera coverage 32/275. COMMS BANKED as scratch pointers: SMS 200 msgs = read_sms_36_50991 (38KB), calls = read_calls_37_50994 (113KB), contacts = read_contacts_38_50995 (5.6KB, ~25 entries; Wife✨ 0774148612, Shemso Bro 0798191464 top contact). b2 tar deleted from bird after verify (97% full, frees 114MB). Battery 11% USB charging. Chunk plan: c3+ = Camera rest 243 files (~1.0GB) by name-exclusion vs b2 manifest, ~150MB/tar, then Screenshots 468f/142MB one tar, Facebook+Videocaptures tail tar.

- [2026-09-06 02:51] [2026-09-06 HARVEST LEDGER — R58N647SCPY /sdcard COMPLETE] All chunks tar -t verified + extracted exit 0 on panel (cortex_shots\*_bank\): Camera 275/275 = 1,216,421,888B (b2 32 + c3 77 + c4 37 + c6 28 + c7 15 + c8 14 + c9 43 + c10 14 + c11 2 + c12 13); Screenshots 468/468 = 147,525,592B; DCIM tail 12 = 6,101,997B (incl. stranger VID-20260705-WA0008_001.mp4 in Video Editor — the 755th file old scan missed); WA Business media 834/834 = 214,909,171B (Android/media/com.whatsapp.w4b); Telegram 1,210/1,210 = 115,324,160B (data+media); Pictures 1,039/1,039 = 85,287,448B; Download+root docs 37/37 = 55,168,066B. SESSION TOTAL: 3,875 files / ~1.84GB banked+verified. Skipped with cause: Android/data/com.reddit.frontpage 140MB (regenerable cache, zero owner intel). Bird staging CLEAN, 0.9G freed. COMMS banked as pointers (sms/calls/41 contacts). CREDENTIAL FRONT: walls re-verified unchanged (uid2000, flash.locked=1, oem_unlock_allowed=0, spblob denied, no hashcat on panel, panel offline) BUT strongAuthRequired flipped 0x8→0x0 — FINGERPRINT DOOR LIVE for an enrolled finger (engineering intel: strongAuth windows are a real attack surface). GATE-17.14 REFRAME: the product is AUTONOMOUS unlock — owner-absent. Owner pattern/finger are NOT doors (job unsold); engineered doors = offline artifact attack (needs artifacts via root/recovery/flash), physical rig (combination flash on sacrificial bird, ISP, chip-off eMMC), remote account keys (Samsung FMM-armed). Enrolled biometrics = access agents AFTER engineered unlock, never the unlock itself.
