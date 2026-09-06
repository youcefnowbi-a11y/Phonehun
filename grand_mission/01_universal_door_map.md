# THE UNIVERSAL DOOR MAP — W1a
*Grand Mission 01 · DroidCommand / Vesper · compiled for the crown law:
any locked phone arrives, owner absent, no owner biometrics or credentials ever.
Laws carried: GATE-17.14 (THE CROWN), GATE-17.15 (THE INTERIOR), GATE-17.13 (credential = state).*

Verdict vocabulary: **ALIVE** (works on current patched builds or needs only cheap hardware),
**CONDITIONAL** (works per-model / per-build / per-arrival-state), **DEAD** (patched era, kept for
doctrine lineage). Confidence flags: CONFIDENCE: LOW where a single source or memory only.
Prices approximate: `~$` with CONFIDENCE: LOW unless a vendor publishes.
Verification date: 2024–2025 web reality plus repo evidence (`_research/extracted_A217F`).

---

## 1. TAXONOMY OF LOCKS — WHAT ACTUALLY LOCKS A PHONE

Most of the world confuses seven different gates. A phone is not "locked"; it is
SEVEN state machines, each gating a different thing. The doors differ per layer.

| # | Lock layer | What it really is | Gates DATA? | Gates BOOT? | Gates CLOUD? | Notes |
|---|---|---|---|---|---|---|
| 1 | Screen lock (PIN/pattern/password) | Keyguard UI + LockSettingsService credential + GateKeeper enrollment | Indirect: gates entry to a running session, not the raw key material | No | No | See layer 4 — the credential WRAPS the data keys. Guessing at the glass is the least leveraged attack on it |
| 2 | Biometric unlock | Fingerprint/face → TEE-verified token → unlocks Keyguard; still gated by secure flag + 24h/72h re-challenge rules | No (it's a convenience surface of #1) | No | No | After reboot biometrics are dead until first credential entry. Biometrics never unwrap keys alone — TEE allows a token only while credential-derived state is already resident (AFU window) |
| 3 | User data encryption (FBE, file-based / legacy FDE) | Per-file AES keys; CE (credential-encrypted) keys wrapped by the Synthetic Password (SP), SP wrapped by GateKeeper/Weaver secrets in the TEE; DE (device-encrypted) keys available pre-unlock | YES — this is the real wall | No | No | FBE is default since Android 7–10 (A1C: `fileencryption=ice`/`a` variants). BFU (before first unlock) = CE unreadable even with root/EDL. AFU (after first unlock) = CE keys live in kernel keyring; every commercial extractor's favorite state |
| 4 | GateKeeper + Weaver + Synthetic Password | TEE-stored throttled verifiers (GateKeeper: scrypt-stretched PIN blobs, per-user handles in `/data/misc/gatekeeper/`; Weaver: HMAC slot table on Pixel-class hardware, throttling in TEE, secrets in TEE secure storage / RPMB; SP blob in `/data/system/spblob/`) | YES — the credential never decrypts data directly; it unwraps SP which unwraps CE keys | No | No | Weaver missing on many SoCs (fallback to GateKeeper-only throttling). Throttling lives in TEE = offline brute-force immune only as long as the artifacts can't be READ |
| 5 | Bootloader / AVB (verified boot) | Locked BL refuses unsigned boot/recovery; AVB rollback indices; `fastboot oem unlock`/`flashing unlock` triggers wipe + VaultKeeper-class checks | No (does not encrypt) — but blocks the flash plane and enforces DM-verity | YES — the boot/flash gate | No | Unlock on modern devices = userdata wipe (KV/credentials destroyed). Relock restores AVB yellow/orange state |
| 6 | FRP (Google Factory Reset Protection) | Cloud-tied: after factory reset, setup wizard demands the Google account previously on the device; enforced in setup flow, not by crypto | No — it is a wizard-state gate | No | YES | Post-2015 era. The data is already wiped by the time FRP speaks; FRP guards re-enrollment, not secrets |
| 7 | Vendor anti-relock | Samsung KG/RMM/Knox Guard state machine (+ VaultKeeper bootloader gate), Xiaomi Mi account bind / unlock tokens, Huawei ID, BBK accounts | Partial: Samsung KG ACTIVE can hard-lock the device from the cloud; most vendor accounts gate flashing/re-enrollment, not keys | YES (Samsung: OEM-unlock toggle + flash permission) | YES (remote state) | KG/RMM born ~Android 9 era (verified: XDA/chimeratool docs) |
| 8 | SIM / carrier lock (NCK/SPCK) | Baseband NV lock bits — network subsidy lock | No | No | No (stored on-device) | Adjacent to the mission: unlocking SIM ≠ accessing data. Cheap commercial unlocks exist (~$10–50); never the data door |
| 9 | Activation lock (Apple; also Samsung Reactivation Lock legacy, Huawei cloud) | Cloud-tied device ownership check at activation/wizard | iCloud: gates reactivation, not disk keys (SEP holds those) | No | YES | Out of Android scope but listed for taxonomy completeness — see 06_ios_front.md wave |
| 10 | MDM / EMM / Knox Guard financed-device lock | Policy state machine, can pin password, block ADB, remote-wipe | Can block every plane; can also REMOVE a lock (policy can reset credentials on unsecured devices) | Partial | YES | For Vesper: an MDM on board is usually a wall, rarely a door |

**Reading order for any arriving phone:** layers 3+4 are the data wall; 5 is the boot wall;
6/7 are re-enrollment walls; 1 is only the UI face of 3+4. Any method that "unlocks the
screen" without touching 3+4 (glass-plane tricks) yields session access at best; any
method that touches 5 (flash) without 3+4 leaves CE data sealed. That asymmetry drives
this entire map.

---

## 2. THE DOOR MAP BY PLANE

### 2a. GLASS-PHONE METHODS (no tools beyond hands)

Doctrine note: this is the closed map of the classic world. Every named trick below is a
UI state machine bug; they die by patch and never touch the key material. Kept for lineage
+ arrival-state value (an arriving phone already inside a broken state is a free win).

| Method | Era / death | Mechanism | 2024–25 status |
|---|---|---|---|
| Emergency-dialer crash bypass | Android 5.0–5.1; CVE-2015-3860 class; dead by 5.1.1 (~2015) | Crash the dialer/compositor from the lockscreen → SystemUI restarts with keyguard lost | DEAD |
| Camera → gallery → settings escape | 4.1–4.4 era (~2013); multiple CVEs; dead by 5.0 | Camera shortcut on lockscreen → share/attach intent → picker → file manager → settings app | DEAD |
| Notification reply escape (WhatsApp/ Messenger attach, "manage notifications" → settings) | Samsung/LG ~2016–2018 builds; died with One UI patches (notifications-on-lockscreen hardening, ~2019) | Reply to a lockscreen notification → attach file → file picker reaches storage/settings | DEAD on patched; CONDITIONAL on unpatched budget builds (common in Transsion/itel class) |
| Quick-settings gear from lockscreen | 5.x–7.x OEM builds; killed when "secure lockscreen blocks QS expansion to settings" (~2018 across majors) | Pull QS → settings gear reachable despite lock | DEAD on majors; CONDITIONAL on old BSP budget devices |
| TalkBack/setup-wizard escape (FRP era) | 2016–2019 per-OEM; Google hardened SetupWizard repeatedly | Enable TalkBack in wizard → tutorial web link → browser → download/opens settings shortcut | DEAD on patched; ALIVE on stale-firmware budget fleet (huge installed base) |
| Setup-wizard intent-escape family (FRP) | Continuous arms race 2016–2021: maps → "open web" → download APK; keyboard settings; "Switch Access" → help | Reach any non-wizard surface from the wizard without completing Google sign-in | DEAD on current; patch coverage per vendor is ragged — CONDITIONAL on unpatched build levels |
| Factory-reset-into-wizard FRP tricks (SIM PIN change race, second space, OTG HID APK sideload) | 2017–2022 (Redmi Second Space trick, SIM-lock trick era) | Race the wizard, land in a secondary user/space with weaker gating; or sideload via OTG before policy applies | DEAD on patched (Google blocks OTG unknown sources in wizard); CONDITIONAL old ROMs |
| OTA side-load during wizard | ~2017–2019 per-OEM | Wizard checks update → injects UI state/reaches settings via update flow | DEAD |
| Emergency/ICE contact abuse (add contact → share → escape) | 2015–2017 Samsung class | Emergency info editor reachable from lockscreen → share intent escapes | DEAD |
| HID glass brute (USB-OTG keyboard emulating digit entry) | Alive concept, device-dependent throttling | OTG HID types PINs; phone throttles (30s→1min→5min backoff schedule since ~5.0); auto-detect unlock by screen brightness (SBC 2024 paper: 66% of 18 devices in ≤2 weeks with stop/resume) | ALIVE as a siege on short PINs / no-wipe-config devices; use as Vesper side-channel: keystroke cadence reveals timeout schedule |
| Android Auto PIN brute | Reported 2025; fixed by vendor/app update (Google told press fixed in May 2025 security cycle). CONFIDENCE: MEDIUM (press-verified, primary not fetched) | Android Auto's PIN-pairing screen on the head unit lacked the phone-side failure-count/throttle state → unthrottled verification loop (~hours for 4-digit) | DEAD on patched Auto app + 2025-05 patch level; CONDITIONAL on stale Auto installs (users rarely patch the car side) |
| PIN-guess oracle via Bluetooth/wearables (companion unlocks) | Device-specific; Wear trusted-device unlock is a Smart Lock surface | If a paired wearable is present, some OEM builds keep the session unlockable | CONDITIONAL — depends on arrival state; belongs to trust-feed section 2b |

Glass-plane verdict: no patched current-major phone opens by glass alone. The glass plane's
residual value for Vesper: (a) arrival states that are already inside a broken wizard/FRP
flow (cheap wins on stale fleet), (b) the HID siege as a slow oracle on the FLEET of
unpatched budget devices, (c) glass as an ORACLE only — screen readout of state, per GATE-17.15.

### 2b. ADB / SOFTWARE-ONLY (shell uid 2000 — the Vesper plane)

Precondition for nearly all: debugging authorized (RSA-accepted) — normally impossible on a
locked phone with debugging off. The exceptions are the interesting part: wizard/FRP-era
flows that enabled ADB, dev-unlockable bootloaders, devices previously paired (wireless ADB
trust survives reboots — a previously-paired lab phone re-appears as a door), and DPM
provisioning on fresh devices.

| Surface | Command class | Surgery vs theater | 2024–25 status |
|---|---|---|---|
| `adb backup` | `-apk -all -shared` pulls debuggable apps' data | THEATER for locks (never yields lock artifacts; most apps opt out since 12+) | DEAD as a lock door; marginal data exfil on legacy ROMs |
| `settings put secure/global/system` (shell holds WRITE_SECURE_SETTINGS) | Direct row writes into SettingsProvider | Mixed: legacy keys like `lockscreen.disabled` died pre-N; some OEM keys still toggle keyguard behavior per-build | CONDITIONAL — the single most under-mapped surface; see section 4.2 (state-delta doctrine) |
| `cmd lock_settings` (`set-disabled`, `verify`, `get-disabled`) | Official verbs over LockSettingsService | `set-disabled true` works ONLY on credential-less devices; `verify` requires the credential | THEATER on locked-credentialed devices; real on none/low-security states |
| `wm dismiss-keyguard` | WindowState verbs; also `service call window` variants | Dismisses insecure keyguard; on secure lock it only summons the bouncer | THEATER for secure locks; real shortcut once credentialed session exists (AFU arrival) |
| Trust agents / Smart Lock (BLE trusted device, places, on-body) | `dumpsys trust`, settings rows, BLE advertisement spoof | If Smart Lock trusted-device is configured and the session is AFU, spoofing/being the trusted BLE peripheral keeps Keyguard disarmed (on-body continues unlock chains) | ALIVE as a state-amplifier — NOT a first-unlock tool (post-reboot all trust dies until credential). Crown-compatible when arrival is AFU |
| `dpm set-device-owner / set-profile-owner` via shell | DevicePolicyManager provisioning | On unprovisioned/debuggable-fresh devices shell CAN provision an owner; owner can resetPassword only where no credential exists | CONDITIONAL — real on no-lock fresh devices (dev fleet, post-wizard), useless against credentialed locks |
| `service call` verb abuse | Raw binder transaction codes to any system service | Unmapped per-build; shell's permission set is larger than the UI exposes (per-build drift) | CONDITIONAL — the flagship unexplored surface; section 4.1 |
| Content-provider reads (`content query --uri content://…`) | `settings`, `telephony`, `media`, `call_log`, some OEM providers | Exfil of unsecured provider data on authorized ADB | ALIVE as data exfil (DE-reachable data in BFU), THEATER for lock removal |
| Input injection (`input keyevent`, scrcpy-class) | Screen-injection walls | Injection is allowed on secure keyguard for bouncer typing — i.e., glass over wire; no bypass semantics | THEATER (it's just glass); useful as oracle for siege timing |
| `svc` / `am start` intent verbs | Launch wizards, emergency, settings sub-screens on builds that still honor exported activities from shell uid | Per-BUILD truth; exported-activity leaks are the classic per-OEM FRP companions | CONDITIONAL — enumerated per build, dies per patch |

State-surgery verdict: on an AFU phone with authorized ADB, uid 2000 can extract anything
DE-reachable + most CE-reachable (apps dump via `run-as` on debuggables, media, providers)
without ever touching the lock. That is already a data win under the crown law: the lock is
irrelevant if the state is AFU + authorized shell. On a BFU or unauthorized-ADB phone, uid
2000 alone has never opened a modern device.

### 2c. ROOT / RECOVERY (boot control assumed)

Precondition chain: unlocked bootloader (fastboot unlock / Odin flash of custom recovery) OR
a boot exploit (fuzzboot-class fastboot bug, MTK BROM). This is state surgery against layer
1/4 artifacts — and the FBE trap defines everything:

| Artifact / move | Effect | FBE-CE trap? |
|---|---|---|
| `/data/system/locksettings.db` — delete `credential` row (pre-6.0 era) | Instant lock removal on pre-6.0/early-7.0 devices | Those eras were FDE/none — row deletion was a real unlock on Samsung ~4.4 (password.key era). DEAD as universal method on FBE |
| Delete `password.key` / gesture.key (legacy, pre-6) | Classic instant bypass; gesture.key = SHA1(pattern) → trivially crackable offline instead | Legacy only; gesture crack still valid on that old fleet |
| Remove `/data/system/spblob/<userId>/*` + `/data/misc/gatekeeper/*` rows | Clears the credential enrollments — KEYGUARD may open (no lock) | **TRAP**: on FBE, the CE keys are wrapped by the SP you just destroyed → CE NEVER mounts; phone behaves unlocked-but-empty for user 0, apps/user data unreadable. This is the lock-out, not the unlock |
| Weaver table zeroing (Pixel-class; slots in TEE storage / persist-backed) | Kills the throttled verifier; combined with removing the SP chain the device can be re-enrolled with a NEW PIN | Same TRAP: new PIN = new keys for NEW data; old CE data stays sealed forever |
| TWRP + file manager over `/data` | TWRP asks for the PIN to decrypt CE — it does not have a TEE to verify against, so FBE decryption needs the credential or AFU key extraction | On FDE-era (pre-7/8) TWRP could decrypt with PIN offline-captured or not at all; on FBE TWRP is a file browser for DE only unless PIN known |
| App pulls with root file managers (MT Manager class) / `tar` of `/data/data` | Full user-data snapshot — only while CE is unlocked (AFU live system or known PIN) | Data-only door: with root on an AFU phone this is total access, lock untouched |
| FBE key extraction from a live AFU system (kernel keyring / vold key dumps) | Extract CE key material directly → offline decrypt of `/data` copies | ALIVE and crown-compatible IF root exists while phone is AFU. This is the state the commercial boxes sell as "physical extraction of unlocked devices" |
| Flash patched recovery/boot to alter LockSettingsService checks (boot-control tampering) | Making the SERVICE believe no credential exists | Same TRAP + AVB: re-locked chain rejects tampered images; tampered boot with unlocked BL works for UI but never for CE keys |

Verdict: boot control alone stopped opening phones at FBE. Its 2025 value is threefold:
(1) AFU key extraction, (2) ARTIFACT EXTRACTION for the offline credential attack (2g),
(3) flashing the diagnostic/combination builds that expose service surfaces (2d/3).

### 2d. BOOTLOADER / FLASH

| Method | Mechanism | Data survives? | 2024–25 status |
|---|---|---|---|
| `fastboot oem unlock` / `flashing unlock` | Unlock bit → wipe + KV wipe (GateKeeper/Weaver state destroyed = keys destroyed on FBE) | NO (by design) | ALIVE as a reset tool (opens FLASH, not data). Vendor gating: Samsung OEM-unlock behind KG/RMM + carrier builds without the toggle; Xiaomi behind token quota (see §3); Pixels free; BBK free-ish |
| Samsung Odin / Download Mode | Powered-off button combo → proprietary download protocol; flashes signed images only | Data survives flashing when not wiping — but custom images are refused unless KG state allows and bootloader is unlockable; combination firmware era (§3) | ALIVE as flash plane; cannot flash unsigned on locked chain |
| Combination firmware (Samsung) | Engineering builds signed by Samsung; ship without KG/FRP enforcement; historically enabl(ed) ADB from locked state, factory-reset-with-sign-in bypass | Data wiped on flash | CONDITIONAL: per-model availability grey market; modern One UI combos hardened (ADB in combos restricted), still central to Samsung chains |
| MTK BROM / DA (mtkclient + forks) | Boot ROM accepts commands via USB pre-auth on many SoCs; mtkclient writes partitions, can wipe FRP/weaver-ish blocks, dump `/data` blocks | Yes for raw dumps (FBE still needs keys); wipes targeted blocks | ALIVE for a huge legacy fleet; CONDITIONAL per-SoC: post-~2021 MTK enforces SLA/DAA signed DA auth on new chips; mtkclient's bootrom exploit family (pre-auth memory R/W) is the single most valuable open tool in this class |
| Qualcomm EDL 9008 + firehose programmers | SoC falls to EDL (buttons/test point); firehose loader must be SIGNED per-model (leak-dependent); once loaded: full R/W flash | Yes for raw dumps; FBE sealed unless keys dumped | ALIVE CONDITIONAL — entirely loader-availability-gated. Loaders leak from OEM service packs (the box vendors' bread and butter). No public loader = no public EDL. Exynos SoCs: NO equivalent public 9008/firehose path (see §3 note) |
| Xiaomi unlock tokens (MiUnlock → HyperOS community approval) | Account-bound signed unlock permission → `fastboot oem unlock` | NO (wipe) | CONDITIONAL and narrowing: HyperOS 2.0 (Oct 2024) + Jan 1 2025 policy = community-app approval tiers, 1 device/account/year, ~14-day token validity, quota walls (xiaomi.eu thread documents daily quota exhaustion) |
| Huawei test-point + HiSilicon EDL | Post-2018 no official bootloader codes; third-party paid firehose loaders per model; test-point entry | Data survives flash; FBE sealed | CONDITIONAL per-model, paid loader ecosystem, dying with each Kirin generation; DC-unlock class handles the SIM/account-adjacent locks |
| BBK (OPPO/vivo/realme/iQOO/OnePlus) MSM/EDL rescue + engineering modes | MSM Download Tool per-model packs (leaked) flash in EDL even on locked BL for rescue; dial-code engineer menus (`*#808#` OPPO class) | Rescue flash keeps data unless wipe chosen | CONDITIONAL; MSM packs = grey-market per-model downloads; OnePlus historically the most permissive fastboot unlock of the family |
| Pixel fastboot/AVB bug class | Bootloader code itself vulnerable: CVE-2024-22012 (Pixel 6a ABL USB stack, function-pointer overwrite → arbitrary boot code; disclosed 2023-11, patched), CVE-2025-36907 (bootloader heap overflow via fastboot, USB), plus Google's own `fuzzy_fastboot` harness and the WOOT'17 fastboot-oem lineage (Motorola/OnePlus 3 secure-boot bypasses, Hay/Aleph) | Boot exploit ≠ wipe → data survives while you take boot control | ALIVE as a research class: the boot plane is code, code has bugs; each ABL generation ships new surface. This is where per-build fuzzing (LLM-operable) pays |
| VaultKeeper-style post-unlock guardians (Samsung) | After `oem unlock` flag set, guardian verifies before permitting flash; KG ACTIVE = refused | — | ALIVE on Samsung; part of the KG state machine (§3) |

### 2e. SILICON (hardware rig)

| Method | What it is | Data survives / readable? | 2024–25 status & economics |
|---|---|---|---|
| JTAG / UART | Debug pads on PCB → halt SoC, read memory, dump keys from a live/AFU boot chain | AFU: yes; BFU: usually no (keys not resident) | CONDITIONAL: pads increasingly fused off/disabled in production; engineering samples and budget boards leak JTAG. Needs per-board pinout work (~hours) |
| eMMC chip-off | Desolder eMMC, read raw NAND in a reader | Pre-FBE legacy (unencrypted/FDE with recoverable keys): readable; post-2016 FBE: sealed — CE keys are SP-wrapped and never live on flash in the clear; you also lose the TEE/RPMB key held by the SoC | DEAD as a data door on modern FBE; ALIVE for legacy fleet |
| UFS chip-off | UFS is NOT raw NAND — a SCSI-like controller IC; desoldering yields a chip whose controller you must speak UFS to, with per-device provisioning | Same crypto wall as eMMC, plus brutal logistics (BGA reball, LGA111/HS-BGA footprints, one-shot removal) | BRUTAL/DEAD for data; still used for repair/forensics of unencrypted legacy |
| ISP (in-system programming) — Medusa Pro / Riff Box / UFSxx-box class / EasyJTAG Plus / UFI Box | Clip/test-point harness reads/writes the storage WHILE soldered, no reball | Same wall; ISP's real 2025 use = targeted partition ops on devices with dead boot (write persist/misc blocks, wipe FRP-era blocks, restore boot) | ALIVE as a service-mode rig; ~$100–1,000/box (CONFIDENCE: LOW on prices) |
| Direct eMMC/UFS reader + offline artifact attack | Read raw image → extract lock artifacts → offline crack (2g) | Artifacts readable if they live in plaintext partitions (persist, misc, EFS, /data DE-visible files); SP itself can be read from a raw image only if the storage-level encryption allows — FBE metadata encrypted → typically NOT | CONDITIONAL: works where per-model layout puts blobs readable; per-model forensic homework |
| Reballing services / microsoldering economics | Third-party shops swap storage/SoC | Reball = repair economics: ~$50–300/device, days of turnaround, needs donor parts (CONFIDENCE: LOW on prices) | ALIVE as outsourced capability; not a data door by itself |
| Fuse/efuse notes | AVB rollback fuses, MTK/Kirin anti-rollback, KG/Knox eFuse (trips on unlock/tamper — permanently on Samsung; kills Knox-secured data paths like Secure Folder/Knox vault keys) | Samsung Knox fuse trip is one-way: Knox-wrapped data dies even if you later get in | Doctrine: on Samsung, the LAST usable backup of Knox-wrapped data exists only before you trip it — sequence matters |
| Pre-boot key dumping (TEE/boot-ROM exploits) | Donjon/Ledger CVE-2025-20435 (MediaTek secure-boot chain): physical + USB → dump keys BEFORE Android loads → offline PIN brute → full decrypt in ~45s on CMF Phone 1 (Dimensity 7300); fixes to OEMs Jan 2026; ~875M-device class per press | Data survives; keys extracted pre-boot | ALIVE and THE 2024–25 headline door. Patched chips arriving through 2026; the installed base lags years. This is the silicon/software hybrid that beats FBE without the credential ever being guessed on-device |

### 2f. CLOUD / REMOTE

| Channel | What it can do | 2024–25 status |
|---|---|---|
| Samsung Find My Mobile remote unlock | HISTORICALLY could unlock the screen remotely (Samsung account auth). Dead: moderator-confirmed removal from FMM (2024, Samsung Community EU thread) | DEAD as remote unlock. Ring/locate/erase remain. Doctrine: any phone still offering "unlock" in FMM UI = stale Samsung account state, arrival-state jackpot |
| Google Find My Device | Ring, locate, erase, lock-with-message — NEVER data unlock; no PIN reveal | ALIVE but useless for the crown law (erase ≠ access) |
| Xiaomi Mi Cloud / Find Device | Locate/lock/erase; account removal central to the unlock-token regime | ALIVE as wall-keeper: bound account gates bootloader tokens (§3) |
| Carrier channels | SIM-unlock codes (NCK) trivially purchasable (~$10–50); financed-device KG locks are the real carrier wall | Data-irrelevant; KG/MDM locks move via carrier finance servers — not reachable without owner/legal channel |
| Law-enforcement / vendor channels (Cellebrite Advanced Services, Google/L/Samsung LE portals, Apple gov troves) | Warrant-driven: cloud backups, location history, vendor-held telemetry; LE-only | Out of scope for autonomous arrival (owner absent ≠ warrant present), listed for map completeness |

Cloud verdict: no vendor cloud unlocks data for an uncredentialed third party in 2025.
The cloud plane's only crown-compatible artifacts are cloud BACKUPS (photos/sync history)
reachable when the operator owns the account — a different mission door.

### 2g. CREDENTIAL-ARTIFACT ATTACKS (offline)

The single most important modern chain: **read the artifacts → attack the credential
offline where no TEE throttles you → boot the phone normally with the recovered PIN →
full AFU session → data.** GATE-17.13 compatible: the credential is a STATE — we compute
it, we don't guess it on the glass.

Precondition (the whole attack's bottleneck): artifact READ requires one of:
root/recovery on reachable storage (2c), EDL/firehose raw dump (2d), BROM dump (mtkclient),
ISP/reader raw image (2e), or pre-boot key dump exploit (2e last row). Weaker devices
(exposed persist partitions, DE-readable blobs) need less.

Artifact classes and their crackers:

| Credential class | Artifact | Tooling landscape | Notes |
|---|---|---|---|
| Legacy pattern (≤ Android 5/6 unencrypted) | `gesture.key` = SHA1 of dot-sequence | Any SHA1 cracker (JtR/hashcat mode-agnostic); instant on modern GPUs for the 389k space | Trivial; fleet of legacy devices still falls |
| Legacy Samsung PIN/password (pre-~2014) | SHA1-style lockscreen hash | hashcat mode **5800** (Samsung Android PIN) | Verified present in hashcat example hashes |
| Android FDE (5.x–7.x era devices) | Disk-encryption key stretched from PIN (PBKDF2) | hashcat **8800** (Android FDE, Samsung class) and **8900** (Android FDE) | Verified modes; the FDE fleet is shrinking but real |
| Android backup encryption (ADB backups) | AED header PBKDF2 | JtR jumbo `androidbackup` format (CONFIDENCE: MEDIUM on exact format name in current jumbo) | Useful when backups are the evidence, not the lock |
| GateKeeper-era (7.0+ → current) SP blob + Weaver | `/data/system/spblob/` (SP wrapped with Weaver secret + GK handles), `/data/misc/gatekeeper/*`, Weaver slot table in TEE storage | **No boxed first-class hashcat/JtR module.** Public attacks are bespoke verifiers emulating SyntheticPasswordManager/Weaver math (community scripts; repo evidence: `tools_clone/LockKnife`, `blackshibe/android-fbe-decrypt` notes "extract device keys, brute separately"). TEE-emulation code (port the verify path off the target) is the working pattern | Attack is only as good as artifact READ: where the Weaver secret stays inside TEE/RPMB (Pixel class), offline verification is impossible without a TEE/boot-ROM exploit → that's why CVE-2025-20435-class matters |
| Samsung variant | Knox TEE equivalents of GK/weaver; Knox Vault (S21+ class discrete secure element) holds keys in a separate chip | Same doctrine; Knox Vault raises the silicon bar further | TEE exploit or AFU extraction, not offline math alone |

**PIN/pattern complexity economics — the real numbers:**

| Credential | Space size | At 10 k guesses/s (optimistic scrypt rig, ~) | At 1 k/s (realistic per-core-bound rig, ~) |
|---|---|---|---|
| 4-digit PIN | 10^4 = **10,000** | ~1 s | ~10 s |
| 6-digit PIN | 10^6 = **1,000,000** | ~100 s | ~17 min |
| 8-digit PIN | 10^8 = **100,000,000** | ~2.8 h | ~28 h |
| Pattern 3×3 (no revisits) | 9! = **362,880** | ~36 s | ~6 min |
| Pattern 3×3 (all legal, jumps included) | **389,112** | ~39 s | ~6.5 min |
| 16-dot pattern (4×4) | 16! ≈ 2.09×10^13 | ~24 days | ~243 days |
| 8-char alphanumeric | 62^8 ≈ **2.18×10^14** | ~251 days | ~6.9 years |
| 12-char random | 95^12 ≈ 5.4×10^23 | heat death of the lab | — |

Reading: the gatekeeper scrypt stretch is deliberately memory-hard (GPU-hostile); rates
above are ~estimates for a beefy CPU box; the POINT of the table is the topology: any 4- or
6-digit PIN is dead on arrival for a lab with weeks of time; patterns are a rounding error;
alphanumeric ≥10 is out of reach offline — for those, only the AFU/TEE-exploit planes remain.
Human PIN reality (birthdays, repeats) collapses these spaces by orders of magnitude:
wordlist-first, brute-second.

---

## 3. VENDOR-SPECIFIC REALITY TABLE

| Vendor | Boot/flash plane | Anti-relock state machine | Current 2024–25 door reality |
|---|---|---|---|
| **Samsung** | Odin/Download Mode (powered-off combo), signed-only on locked chain; OEM-unlock toggle absent on carrier builds | KG/Knox Guard states: ACTIVE / PRENORMAL / COMPLETED; RMM "Prenormal" (~Android 9 era, verified): OEM-unlock hidden/greyed for a 7-day online window with SIM+network, then flips COMPLETED; VaultKeeper guards flash after unlock; Knox eFuse trips one-way | Best-mapped vendor. Doors: KG-state wait-out (7-day clock — a TIME attack the LLM can automate), combination-firmware chains (grey-market per-model combos), paid KG/RMM unlock functions (chimeratool docs KG/RMM unlock; SamKEY/z3x/Octoplus sell relock removal ~$50–300, CONFIDENCE: LOW on prices). US carrier models: bootloader permanently locked → flash plane sealed → EDL loaders not public for Exynos either. See A21s note below |
| **Xiaomi / Redmi / POCO** | fastboot unlock via account token; Mi Unlock Tool → HyperOS: Xiaomi Community app approval tiers + quiz + wait (72h+), **1 device/account/year, ~14-day token validity**, daily application quotas exhausted within seconds (xiaomi.eu reports) | Mi account FRP-style re-enrollment bind; unlocked devices lose Widevine L1 + some payment features | The regime that closed 2024→2025. MIUI-era devices (pre-HyperOS) still unlock freely with the old wait — the fleet is split. EDL firehose for QCOM models exists in service-ecosystem, MTK models ride mtkclient where BROM allows |
| **Huawei / Honor (pre-split)** | Bootloader codes stopped 2018; no official unlock since; Kirin SoCs have no public 9008/firehose standard | Huawei ID re-enrollment bind | Test-point + paid HiSilicon loaders per model (shrinking availability per generation; post-2020 Kirin near-dead). The most closed major ecosystem; doors are per-model paid services or nothing |
| **OPPO / vivo / realme / iQOO (BBK)** | Mixed MTK/QCOM; dial-code engineering menus (OPPO `*#808#` class; deeper menus per model, CONFIDENCE: LOW on codes), MSM/EDL rescue packs per model | Vendor account re-enrollment; vivo/OPPO "bootloader unlock" officially none (vivo historically none for global) | MTK units → mtkclient family where BROM allows; QCOM units → leaked firehose availability per model; deep diag menus used by box tools as service lanes |
| **Google Pixel** | `fastboot flashing unlock` free + wipe; relock restores AVB; ABL/bootloader bug class live (CVE-2024-22012, CVE-2025-36907) | No vendor relock beyond Google account FRP | The most open AND the best-defended: FBE+Weaver in TEE/RPMB means offline crack needs a TEE/boot exploit or AFU arrival. Boot plane research (fuzzy_fastboot, WOOT'17 lineage) shows the unlock-permission logic itself is attack surface |
| **Transsion (TECNO/Infinix/itel)** | Mostly MTK, loose bootloaders, old BSP levels, factory-test modes; mtkclient-friendly | Vendor locks rare; account FRP via Google only | The softest major fleet: legacy glass bugs live for years, BROM doors common, unpatched CVEs dense. First-priority fleet for autonomous sweep value |
| **OnePlus** | free fastboot unlock (historically), MSM EDL rescue packs per model | Nothing beyond Google FRP | Historically the most researcher-friendly BBK line; MSM packs double as unbrick + downgrade lanes (downgrade → re-open old bugs: the classic chain) |

**Exynos vs Snapdragon in the SAME model line (A21s class — repo bird is SM-A217F):**
- Snapdragon variants (e.g., A21 US class, SD450) sit on Qualcomm EDL 9008: IF a signed
  firehose loader for that exact model is available (leaked/service-ecosystem), raw
  partition R/W is possible WITHOUT bootloader unlock — a boot-control door that bypasses
  Odin/KG entirely.
- Exynos variants (A217F, Exynos 850) have **no public EDL/firehose equivalent**: Samsung's
  own Download Mode is the only flash lane, KG/VaultKeeper gated. For the A21s, the flash
  plane is Odin-or-nothing; artifact read for the offline PIN attack must come from
  root-after-unlock (impossible pre-credential), ISP/reader of raw flash (FBE-sealed for CE;
  DE/persist visible), or glass-era bugs on its One UI build (see `_research/extracted_A217F`
  corpus in repo — the bird's own state is the lab's standing experiment).
Doctrine: same marketing name ≠ same doors; silicon family is a primary index key of the map.

---

## 4. THE UNCATALOGED (new-era doors — the LLM-native map)

The classic world cataloged NAMED doors (§2a). Each named door died by patch. The map
below is of UNNAMEABLE doors: per-build state surface that no handbook enumerates because
no human has had the patience to. This is where an LLM operator is not a tool but a
new instrument class. These are the Vesper research program's actual frontier.

**4.1 Binder/service-call verb enumeration per build.**
What: `service list` + `service call <svc> <code> i32 …` over every code, every service, on
the exact build; `cmd -l` for shell-facing verbs; diffing responses.
Why unmapped: transaction codes are unversioned raw ints; AOSP drifts per release and per
OEM; the human cost of enumerating 100+ services × dozens of codes was prohibitive; every
published "service call trick" was found by hand, once, then patched.
LLM leverage: enumerate the full verb matrix on a fresh/dev twin of the model, diff against
the locked target's responses, and hunt for verbs that mutate lock/trust/keyguard state
from uid 2000. Each diff is a candidate state transition. This turns "the lockscreen bug
lottery" into a systematic sweep the patch lifecycle cannot fully keep up with.

**4.2 Settings-table write lanes.**
What: `settings list secure|global|system` on a credentialed-vs-fresh device; the full set
of rows whose writes have keyguard/trust/lock-timeout side effects (per-build).
Why unmapped: SettingsProvider holds hundreds of rows; which writes do real work vs which
are dead prefs is a per-build empirical question nobody tabulates.
LLM leverage: write-lane enumeration with rollback; observe via `dumpsys window/trust/
notification` whether the write moved keyguard state; keep only state-surgery rows,
discard theater rows. Feed survivors into the chain synthesizer (4.6).

**4.3 Trust-feed manipulation.**
What: the trust agent surface (Smart Lock BLE trusted devices, places, on-body) accepts
environmental state: BLE advertisements, SSIDs, sensor patterns.
Why unmapped: treated as a feature, not a door; the classic world never fuzzed trust feeds.
LLM leverage: with shell on an AFU device, map `dumpsys trust`, enumerate configured agents,
then synthesize the feed (BLE spoof of the trusted device address class, Wi-Fi BSSID
presence) to keep the session permanently disarmed — a state AMPLIFIER converting a
momentary AFU arrival into a standing open session without ever touching the credential.

**4.4 Cross-build state comparison — the "state delta" method.**
What: buy two identical models, bring one to unlocked/AFU, keep the other locked; dump
everything enumerable from both (`settings`, `dumpsys`, `service` responses, files visible
to shell/root); **the delta IS the lock** — a finite, machine-readable artifact.
Why unmapped: costs a second device; classic experts eyeball single devices.
LLM leverage: the delta is small (hundreds of rows), versionable, and reusable as a
per-model "lock signature": any future arriving unit of the same model can be triaged
against it instantly; and every delta row is a candidate lever to flip. This converts the
entire fog of "what does locked mean on build X" into data. The repo's A217F corpus is
exactly this experiment already in motion.

**4.5 Per-build service permission drift (what uid 2000 can call on build X vs Y).**
What: same service, two build levels → the set of binder verbs permitted to shell differs
(denials move with SELinux/service policy per patch).
Why unmapped: drift is invisible without a twin; nobody audits uid-2000 reachability
across patch levels.
LLM leverage: maintain a per-model reachability matrix over time; patch levels that LOST
a denial (vendor backport gaps — rampant on budget fleet) are standing doors.

**4.6 LLM-driven chain synthesis.**
What: the doors in §2 are single steps; the unlocks that work in 2025 are CHAINS
(SIM-state + wizard bug → ADB → write-lane → trust feed → AFU extraction) nobody lists
because each step is boring alone.
Why unmapped: chain space is combinatorial; handbooks list atoms, not compounds.
LLM leverage: the agent's core competency — treat every verified state transition as a
node with preconditions/effects (the feasibility matrix below is exactly that ledger),
then search the graph per arriving device. The deliverable contract in 00_CHARTER.md is
this search running autonomously.

**4.7 Dynamic instrumentation once any boot control exists.**
What: Frida-class hooks against Keyguard/LockSettings/TEE-proxy services on a rooted/dev
twin, to trace which code paths consume which settings/service verbs.
Why unmapped: instrumentation needs boot control, which classic manuals treat as end-state
rather than instrument.
LLM leverage: instrument the twin to OBSERVE the effects of every candidate lever from
4.1/4.2 — closing the loop "write → who reads it → what state moved". Turns theater-
detection from folklore into measurement.

**4.8 Side-channel reading of lockout state via dumpsys.**
What: throttling state, keyguard flags, trust state, user CE-lock status
(`dumpsys user`, `dumpsys window`, `dumpsys trust`, `dumpsys notification`) are READABLE
by shell on many builds even when everything else is closed.
Why unmapped: reading is boring; humans want the bypass.
LLM leverage: precise timing of any on-device siege (HID class): the schedule of backoffs
is exposed, not guessed; plus live verification that a state flip landed. Also the intake
triage: BFU/AFU detection on arrival — THE most important fact about a new bird.

**4.9 Multi-user / profile surfaces.**
What: user 0 vs user 10+ (work/clones/second-space): per-user LockSettings, per-user CE
keys; `pm create-user`-class verbs where permitted; profile-owner surfaces (Island-class).
Why unmapped: consumer practice is single-user; per-user lock state is niche.
LLM leverage: per-user walls are per-user WEAK: sometimes only ONE user on a device holds
a credential; secondary users may be credentialed weaker or the clone spaces of budget
brands leak state. Arrival triage enumerates users, not just "the phone".

**4.10 Samsung hidden diagnostic/service modes reachable from locked state.**
What: powered-off button combos expose Download/Recovery/Maintenance menus independent of
the lock (the lock lives in Android; these live below it); KG/RMM state is READABLE there;
diag menus (`*#0*#` class) reachable once ANY session exists.
Why unmapped: menus are per-model folklore scattered across forums.
LLM leverage: per-model menu map = free pre-boot intel (KG state, eFuse state, OEM-unlock
permission) — exactly the preconditions table of §5 filled in from the bird itself, no
owner required.

---

## 5. FEASIBILITY MATRIX

Legend: DATA SURVIVES = does the method leave user data intact/accessible. COST = money/skill.
LLM-LEVERAGE = what an LLM operator multiplies.

| Method | Plane | Preconditions | Data survives? | Cost | Alive 24–25 | Who sells it | LLM leverage |
|---|---|---|---|---|---|---|---|
| Glass bugs (wizard/FRP/notif/talkback) | Glass | Unpatched build level | YES (no wipe) | $0 / low | CONDITIONAL (stale fleet) | Nobody sells; YouTube folklore | Arrival-state triage: recognize stale-build birds instantly; run the whole dead-trick catalogue automatically per model/build |
| HID glass brute | Glass+USB | OTG HID; short PIN; no wipe-on-fail config | YES | ~$20 cable / low | ALIVE on fleet | Android-PIN-Bruteforce (free, urbanadventurer); NetHunter rigs | Read throttling state via dumpsys (4.8); schedule stop/resume sieges; wordlist-first PIN priors |
| Android Auto PIN brute | Glass-ish (head unit) | Stale Auto app + 2025-05 patch gap; car pairing flow | YES | car/USB / low | CONDITIONAL (stale installs) | None (research, 2025) | Detect Auto-version on arrival; queue as one more stale-fleet lane |
| ADB authorized state | Software | Prior RSA trust / wireless-ADB trust / wizard-enabled debugging | YES | $0 / low | ALIVE where trust exists | — | The Vesper home plane: full exfil on AFU arrival; trust-feed (4.3) to keep session alive |
| `settings`/`service call` write lanes | Software | Authorized ADB (or any shell) | YES | $0 / skill | CONDITIONAL per build | Nobody (the gap) | §4.1/4.2: systematic enumeration = the flagship research program |
| DPM provisioning | Software | Fresh/unprovisioned device + ADB | YES (fresh anyway) | $0 / med | CONDITIONAL | — | Intake robot provisions dev fleet; never a credentialed-lock door |
| Bootloader unlock (fastboot/Odin/Mi token) | Flash | Vendor unlock permission (KG state, tokens) | NO (wipe+KV loss) | $0 / low-med | CONDITIONAL per vendor (§3) | Xiaomi community regime; boxes sell "unlock/relock" services | Time attacks on KG 7-day clock; quota/token logistics automation; treat as reset-to-usable, never data access |
| Combination firmware (Samsung) | Flash | Download Mode + KG state permitting + per-model combo file | NO (wipe) | ~$50–150 combo (grey) / med | CONDITIONAL | Grey-market combo vendors; SamKEY/z3x ecosystem reference them | Armory automation: per-model combo acquisition, flash-chain scripting, KG-state-aware sequencing |
| mtkclient / BROM | Flash/silicon | MTK SoC, pre-auth BROM window, not SLA/DAA-fused | YES (raw R/W; CE sealed) | $0 / med | ALIVE for legacy + budget fleet (CONDITIONAL per-SoC) | mtkclient (free, bkerler); boxes wrap it (Sigma/Octoplus MTK lanes) | Rig-bridge: BROM detection, partition ops, artifact dumps scripted per SoC family |
| EDL 9008 + firehose | Flash/silicon | Signed loader for EXACT model (leak-gated) | YES (raw R/W; CE sealed) | $0 if loader / med | CONDITIONAL (loader availability) | Box vendors bundle loaders (Octoplus, Sigma, UFI, EasyJTAG ecosystems) | Loader-database curation per model = the armory's core asset; LLM matches bird→loader automatically |
| ISP / box rigs | Silicon | Test points, clip, per-model pinouts | YES (raw; CE sealed) | ~$100–1,000 (LOW) / high | ALIVE as service rig | Medusa Pro, Riff Box, EasyJTAG Plus, UFI Box, UFSxx class | Only for boot-dead birds; LLM drives via rig bridge with per-model pinout library |
| Chip-off | Silicon | BGA rework, donor boards | Usually NO (FBE) | ~$50–300 + skill (LOW) / very high | DEAD for modern data; legacy only | Forensic labs, reball shops | Not LLM-multiplied; deprecated in doctrine |
| Pre-boot key dump (TEE/secure-boot exploit) | Silicon+software | Vulnerable SoC (CVE-2025-20435 class: MTK wide fleet), USB, exploit code | YES | exploit / very high | ALIVE (unpatched installed base for years) | Nobody retail (research); box vendors integrate similar in-house | The highest-value 2025 door: match SoC+patch level to public exploit chains; then offline PIN finish |
| Offline artifact attack (GateKeeper/Weaver/SP) | Software (offline) | Artifact read achieved (root/recovery/EDL/BROM/ISP) | YES | rig + time / high | CONDITIONAL (artifact readability per device) | hashcat 5800/8800/8900 for legacy classes; bespoke verifiers for GK-era (LockKnife-class, community code) | GPU rig orchestration, PIN priors from OSINT, scrypt cost scheduling; per-model artifact location map |
| AFU live extraction (rooted or ADB) | Software | Device AFU at arrival + root or authorized shell | YES | $0–rig / med | ALIVE (the industry standard too) | Cellebrite/GrayKey sell this state's extraction; free paths via ADB | Arrival-state detection (BFU/AFU) is the FIRST triage question; 4.3 keeps the window open |
| TWRP/recovery file surgery | Flash | Unlocked BL + FDE-era device (or known PIN) | YES on FDE legacy | $0 / med | DEAD as universal (FBE trap) | TWRP (free) | Only for legacy fleet; LLM sequences the FDE-era artifacts |
| Cloud remote unlock | Cloud | Vendor still offering it (nobody does) | YES | — | DEAD (FMM unlock removed 2024) | — | Detect stale-feature birds on arrival |
| SIM/carrier unlock | Cloud/NV | IMEI + a few dollars | YES (irrelevant to data) | ~$10–50 / low | ALIVE | DC-Unlocker, box tools, IMEI services | Off-mission (network ≠ data) but cheap arrival add-on |

---

## 6. SOURCES — REAL TOOLS, PRODUCTS, LANDSCAPE

Verification: mtkclient repo, hashcat example-hashes page, XDA/Samsung Community threads,
MediaTek/Google bulletins, Donjon-coverage articles fetched 2024–26 window. License models
marked where known; prices approximate.

**Forensic/LE commercial:**
- **Cellebrite UFED / Premium** — physical/logical extraction, lock bypass via exploit
  chains per device; annual per-seat licensing (enterprise contract, ~$10k–30k+/yr, LOW).
  Does NOT magic-open BFU modern devices; sells AFU-era extraction plus per-firmware exploits.
- **GrayKey (Grayshift)** — LE-only brute/bypass appliance; current-gen exploits cached
  per iOS/Android build; subscription model (~$9.5k–30k/yr historically reported, LOW).
- **Oxygen/MobiSecret/XRY (MSAB) etc.** — mid-tier forensic suites; dongle/subscription.

**Box / service tools (the unlock-shop world):**
- **Octoplus / Octopus Box** — multi-vendor flash/unlock/FRP; box + per-module activations
  (~$200–500 + credits, LOW). Bundles leaked EDL firehose loaders (its real moat).
- **z3x (Samsung/Chimera ecosystem competitor)** — Samsung flash/unlock/FRP/relock
  removal (~$150–300/card, LOW).
- **ChimeraTool** — Samsung/HTC/LG/Xiaomi repair/unlock incl. explicit **KG/RMM unlock
  functions** (docs verified); per-license ~$150–400/yr (LOW).
- **Sigma / SigmaKey** — MTK/QCOM/Broadcom service unlock king (~$100–300, LOW); rides
  BROM/EDL lanes for SIM/FRP.
- **SamKEY / similar credit servers** — remote Samsung FRP/unlock via credit logs
  (~$50–150, LOW).
- **DC-Unlocker** — modem/router/Huawei-class unlock via credits (~$10–100/unlock, LOW);
  the Huawei-adjacent stopgap.
- **Medusa Pro / Riff Box / easyJTAG-class (JTAG/ISP), UFI Box, UFSxx-class** — ISP/JTAG
  eMMC/UFS read/write rigs (~$100–1,000, LOW); partition surgery, unbrick, persist wipes.
- **MSM Download Tool packs (BBK)** — per-model leaked rescue flashers; free-floating in
  grey channels (no vendor).

**Open-source / research:**
- **mtkclient (bkerler)** — free, MIT-class OSS; MTK BootROM flash/dump; the single most
  valuable open door tool of its class; BROM window shrinks on post-2021 SoCs.
- **TWRP** — free recovery; FBE-era value limited without PIN (see 2c).
- **Frida (+ friTap)** — dynamic instrumentation; needs boot control; §4.7.
- **hashcat / John the Ripper (jumbo)** — free; Android-relevant modes verified: 5800
  (Samsung PIN), 8800/8900 (Android FDE), plus generic SHA1 for gesture.key; GK-era SP
  blobs → bespoke verifiers, no boxed module (see 2g).
- **Android-PIN-Bruteforce (urbanadventurer)** — free; OTG HID siege with unlock detection.
- **LockKnife-class toolkits** — OSS-style forensic orchestration wrappers (repo clone
  present in `tools_clone/LockKnife-main`); consolidate extraction + artifact attack.
- **fuzzboot / fuzzy_fastboot / FuzzUSB** — boot/USB fuzzing lineage (Hay WOOT'17 → Google
  harness → USB gadget fuzzers); the boot-plane research toolkit.
- **Google/Android Security Bulletins + CVE/NVD** — 2024-43093 (ExternalStorageProvider
  path bypass, exploited in the wild, Mar-2025 ASB), 2024-22012 (Pixel 6a ABL), 2025-36907
  (bootloader fastboot heap overflow), 2025-20435 (MediaTek secure-boot chain — Donjon).
- **SBC 2024 HID brute-force paper (Nunes & Schneider)** — stop/resume PIN/pattern siege
  with brightness-based unlock detection; 66%-in-two-weeks empirical result.

**Web anchors used:** mtkclient GitHub; hashcat example-hashes wiki; Samsung Community EU
(FMM unlock removal, 2024); XDA RMM/KG threads; thecustomdroid/droidwin KG guides;
chimeratool KG/RMM docs; xiaomi.eu / ximitime / gizmochina HyperOS unlock policy articles;
androidauthority/cybersecuritynews/quokka Donjon coverage; Google ASB 2025-03; USENIX WOOT'17
paper page; Black Hat Asia practical-attacks deck (Pixel ABL CVE-2024-22012); NVD CVE pages.

---

## STATE-OF-THE-MAP SUMMARY

Honest big picture, 2025:

1. **No patched, current, BFU, credentialed phone opens by software alone.** Not glass,
   not ADB, not settings, not service calls. Every universal claim of that kind is a lie
   about some other arrival state. The crown law is satisfiable only through state: AFU
   arrivals, stale fleet, silicon, or artifact math.

2. **The arrival state is 80% of the outcome.** AFU + authorized shell/root = data in
   minutes with zero lock contact (the quiet truth the commercial boxes monetize).
   BFU + modern TEE = offline math is blocked unless a TEE/boot exploit or artifact read
   exists. Intake must classify BFU/AFU/authorized/rooted BEFORE any door is chosen.

3. **"Unlock the screen" and "get the data" are different missions that diverged at FBE.**
   Boot control (flash/EDL/BROM) opens the FLASH plane, not the data plane. Artifact
   deletion (spblob/gatekeeper/weaver) LOCKS YOU OUT of CE rather than in. The only
   credential-era surgeries that matter are: extract CE keys while AFU, or extract the
   artifacts and compute the credential offline, then boot normally.

4. **The offline credential attack is the crown-compatible finisher** — 4-digit and 6-digit
   PINs are lab-hours of scrypt once artifacts are readable; patterns are minutes;
   alphanumeric 10+ is forever. Its bottleneck is artifact READ, which is a per-model
   hardware/forensics question — exactly the kind of per-model matrix an armory holds.

5. **Silicon is back.** The Donjon CVE-2025-20435 class (pre-boot key dump over USB) beats
   FBE without ever meeting the keyguard. Chip-off died at UFS+FBE; TEE exploit chains
   replaced it. The silicon plane is now exploit-driven, not solder-driven.

6. **The vendor walls moved from crypto to bureaucracy.** Xiaomi's quota regime,
   Samsung's KG clock, combination-firmware grey markets: the boot plane of 2025 is gated
   by tokens, 7-day timers, and file availability — all time-and-logistics attacks an
   autonomous system is uniquely good at waiting out and automating.

7. **The classic glass map is dead on current majors and alive as a fleet-fleet.**
   Transsion/itel class devices carry 5–8-year-old bugs for years; the HID siege is real
   on short-PIN populations; Auto-class bypasses linger on unpatched car-side apps. The
   stale fleet is the volume business.

8. **The unexplored value is the enumerated state surface (§4).** Service verbs, settings
   lanes, permission drift, trust feeds, per-model state deltas: none of it is in any
   handbook, all of it is machine-walkable, and patch levels cannot keep pace with a
   systematic sweeper the way they kill named tricks. That is the frontier this mission
   actually owns — the classic world's map ends where §4 begins.

The map is complete where the world has walked it, and honest about the fog where it
has not. Every CONDITIONAL row above is a per-model experiment the Vesper loop can run.
