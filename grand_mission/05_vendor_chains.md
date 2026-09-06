# VENDOR CHAINS — W3
*Grand Mission 05 · DroidCommand / Vesper · per-vendor operating doctrine for the universal
unlock system. Builds on 01_universal_door_map.md (taxonomy, vendor table, FRP layer-6) and
03_silicon_plane.md (EDL/BROM/Download-Mode mechanics) — this wave goes deeper: full vendor
state machines and the step-by-step chains, as skill candidates for the method compiler.*

Laws carried: GATE-17.14 (THE CROWN — owner absent, no biometrics/credentials ever),
GATE-17.15 (THE INTERIOR — reason from state), GATE-17.13 (credential = state, computed
offline), SCOPE GUARD (data-sacred birds: recon only, nothing one-way).
Vocabulary inherited: ALIVE / CONDITIONAL / DEAD; planes glass→software→flash→silicon→cloud.
Danger classes (this wave, feeding the one-way-door ledger): **D0** pure read, **D1**
reversible state change, **D2** wipe/data-destructive, **D3** one-way (eFuse/anti-rollback/
KG transition), **D4** brick-risk. Prices ~$ with CONFIDENCE: LOW unless vendor-published.
Verification base: live DDG-HTML + primary fetches this wave (Samsung Knox admin docs,
NVD/CVE records, Black Hat Asia deck, Knox/Community/XDA/xiaomi.eu/lokey0905/repos) plus
both prior waves. Web_search dead in-session — DDG-HTML discipline throughout.

---

## 1. SAMSUNG — THE KG/RMM STATE MACHINE IN FULL

### 1.1 The two state machines (do not conflate them)

Samsung runs TWO separate Knox Guard state machines — one on-device (readable pre-boot),
one console-side (Samsung/financier servers). Most folklore mixes them.

**Device-side (Download Mode screen, the pre-boot readout):**

| Device state | Meaning | Gates what | Verdict |
|---|---|---|---|
| **PRENORMAL** | Fresh/unverified device: KG client hasn't done a successful server check-in yet | OEM-unlock toggle hidden from Developer Options; Odin refuses custom binaries ("Only official released binaries are allowed to be flashed") | The 7-day clock state — a TIME attack |
| **CHECKING** | Check-in in progress / conditional pass | Flash of custom binaries still refused until COMPLETED | Transient; read it as "clock running" |
| **COMPLETED** | Device verified with Samsung servers, no financing hold | OEM-unlock toggle appears (if build allows); custom binaries permitted after `oem unlock` | The free state |
| **ACTIVE** | Device is enrolled in live Knox Guard management (financed/carrier-locked class) | Hardest wall: remote lock policy, ADB/dev-mode block, SIM control, firmware-update control, offline lock | Financed-bird state — release only via server |
| *(LOCKED 01 variant)* | KG-managed + remotely locked | Everything above + lock screen policy | Payment-overdue bird |

- **"LGM" — verdict: folklore.** No Samsung doc, Download Mode screenshot corpus, or
  community thread this wave shows an "LGM" KG state. Likely garbled retelling of "KG STATE:
  LOCKED" screens or the RLC (Reactivation Lock Client) app name. Treat any claim of an LGM
  state as CONFIDENCE: LOW / not operational. The canonical set is PRENORMAL / CHECKING /
  COMPLETED (+ ACTIVE on managed birds). CONFIDENCE: HIGH (official Knox docs + Reddit S22
  screenshot + XDA corpus).
- **Legacy RMM vs KG:** December 2017 the bootloader gate shipped as "RMM State" (Remote
  Mobile Management); Android 9/One UI era renamed the readout "KG State" (Knox Guard) —
  same gate, rebranded (thecustomdroid lineage). Older screens may show both lines.

**Console-side (docs.samsungknox.com, fetched this wave — the financier's view):**
Pending → Activating → **Active** → (Locking/Locked, Unlocking, Starting/Stopping Reminder,
Exchanging, Resetting) → Completing (2-day cancel window) → **Completed** (management over,
device freed; stays in list until deleted). Key facts: devices must reach Activating within
**7 days of first boot** to auto-activate; after that the user must visit
guard.samsungknox.com manually or factory-reset. Rejected devices: KG client deactivated.
Combinations like "Locked | Offline" exist (server remembers last state). Auto-lock,
overdue-payment wallpaper, blinking reminder, SIM-control, ADB/developer-mode block, offline
device lock with relock timestamp are all KG policy levers (each a how-to doc page).

### 1.2 The 7-day Prenormal clock — exact mechanics

| Mechanic | Reality | Confidence |
|---|---|---|
| Clock requirement | **168 hours of uptime** (7 days) with SIM inserted, network connected, **no reboot** — read uptime in Settings > About > Status | HIGH (community consensus, thecustomdroid/droidwin/XDA) |
| What happens on day 7 WITH connectivity | Device checks in with Samsung servers → state walks PRENORMAL → CHECKING → **COMPLETED**; the OEM-unlock toggle appears in Developer Options | HIGH |
| Without network | No check-in ever runs — state sits at PRENORMAL indefinitely; the toggle never appears. Connectivity, not wall-clock, drives the transition | HIGH (community) |
| The date-rollback trick | Offline, set auto-date OFF, wind date back 1–2 months, reboot, reconnect → some units flip to Completed early (server trusts a stale timestamp). Patched per-build; ragged coverage on budget fleet | MEDIUM (XDA threads; verify per bird) |
| Date trick lineage | The original altai1963 method (S8/S9/Note8/9 era) was patched; variants keep resurfacing per One UI build — each dies, each is reborn on stale BSPs | MEDIUM |
| Reboot behavior | A reboot during the window resets the uptime clock (community consensus) — the scheduler must keep the bird powered and undisturbed | MEDIUM (no official doc; empirically repeated) |
| After-unlock guardian | **VaultKeeper**: once the unlock bit is set, the boot-side guardian must finish its own verification before flashing is permitted; flashing custom recovery before VaultKeeper clears = refused — boot straight to recovery after Odin flash, never into the OS, or the bird re-locks to PRENORMAL | HIGH (community doctrine: "Auto Reboot OFF in Odin, boot directly to TWRP") |
| The root cause (patchable surface) | Prenormal enforcement lives in a `services.jar` string + the preinstalled KnoxGuard.apk/RLC.apk — the corsicanu/BlackMesa123 KG-RMM Bypass v3 zip patches it from TWRP. Requires boot control already achieved; re-flash needed per ROM flash | HIGH (XDA lineage) |

### 1.3 How state is READ (all pre-boot or shell-cheap)

| Read lane | What it shows | Plane | Cost |
|---|---|---|---|
| **Download Mode warning screen** (Vol-Dn + USB from power-off) | KG STATE / RMM STATE, OEM LOCK: ON (L)/(U), FRP LOCK: ON/OFF, Current Binary: Samsung Official/Custom, Warranty bit, RPMB Fuse/PROVISIONED, Qualcomm Secureboot (SD only) | Pre-boot, below the lock | $0, D0 — the canonical intake read |
| Developer Options | OEM-unlock toggle present/greyed/absent = PRENORMAL proxy | Glass (needs a session) | $0 |
| Odin attempt | "Only official released binaries are allowed to be flashed" = PRENORMAL/Checking refusal message | Flash | $0, no-write probe |
| Dial codes (`*#0*#` diag, `*#1234#` firmware) | Build/versions, diag surfaces — but only with a live session; useless on locked birds | Glass | $0 |
| adb (authorized) | `getprop` KG/RLC properties, settings rows | Software | $0 |

### 1.4 Knox Guard vs legacy RMM vs Reactivation Lock — per era

| Era | Lock | What it was | Fate |
|---|---|---|---|
| Android 5.1 → ~2018 | **Reactivation Lock** (Samsung account, tied to Find My Mobile) | Post-reset Samsung-account re-enrollment wall; on S5-class (G900) anchored in QSEE secure storage via libterterrier.so — ENG builds exposed a device-binding acceptance check (amoamare/Legacy-Samsung-Reactivation-Lock-Removal repo) | Superseded by Google FRP + folded into Samsung account; gone as a distinct One UI toggle. Legacy fleet still arrives with it |
| Dec 2017 → Android 9/One UI | **RMM State** → renamed **KG State** | Bootloader gate on flashing/unlock (the 7-day machine) | Alive — it IS the modern gate |
| ~2019 → now | **Knox Guard (KG)** proper | Full financed-device management (PAYG/financing): remote lock, wallpaper, SIM control, ADB block, offline lock, wipe | Alive; the financed-bird wall. FMM's remote *unlock* feature died 2024 (door map); KG's remote *lock* very much alive |
| Always | **Knox eFuse** | One-way trip on unlock/tamper; kills Knox-wrapped data paths (Secure Folder, vault keys) permanently | D3 — the sequence-matters fuse |

### 1.5 The four Samsung chains (details in §8)

(a) **OEM-allowed bird:** toggle visible → enable OEM unlock → Odin/Download Mode long-press
Vol-Up to unlock → wipe (D2, KV destroyed) → VaultKeeper verifies → flash freedom. For the
crown law this is reset-to-usable, never data recovery (FBE).
(b) **OEM-forbidden + PRENORMAL:** park the bird 168 h (SIM + network + uptime) → day-7
check-in → COMPLETED → chain (a). The scheduler owns this (§9).
(c) **Combination firmware:** engineering builds SIGNED BY SAMSUNG (official binaries — they
flash on locked chains where the state allows). What they give historically: ADB enabled
from locked state, FRP bypass surface, DRK fix, OEM-unlock visibility, downgrade testing.
Reality check on modern One UI: combos are hardened (door map — ADB restricted), hard to
source for the newest Android versions (XDA: "very hard to find a combination file for the
latest Android version"), per-model CSC/version matched; freely listed for many models on
firmware sites (samfw.com class — free), grey sellers charge ~$50–150 for curated/newest
(LOW). Cost of use: **wipe on flash** (D2). They remain central for FRP-era birds ≤ 2022
patch levels and DRK-rescue work.
(d) **KG-financed (ACTIVE) birds:** remote lock = KG lock-screen policy + wallpaper +
blinking reminder + possible offline lock (server-side combination states). Release paths:
financier marks management Completing → 2-day cancel window → **Completed** (device freed);
on-device Support > Refresh account status fetches latest policies (troubleshoot doc);
mistaken locks resolved server-side. No software bypass exists — box vendors sell KG/RMM
unlock functions (ChimeraTool docs: prenormal→unlock present OEM item, ~$150–400/yr class,
LOW) — treat as paid-reset, never data.
**Exynos vs SD split (restated from W2a, A21s as worked example):** SD Samsungs structurally
sit on Qualcomm 9008 but Samsung service firehoses don't leak publicly (box vendors claim
SD-Samsung lanes, LOW) → effectively loader-or-nothing. Exynos Samsungs (incl. SM-A217F,
Exynos 850) have **no EDL lane at all** — Download Mode (Odin, signed-only) is the entire
flash plane, KG/VaultKeeper-gated. Our A21s: KG read = Download Mode screen, OEM forbidden,
data-sacred → recon only until a sacrificial twin exists.

---

## 2. XIAOMI / REDMI / POCO — THE UNLOCK BUREAUCRACY (2025)

### 2.1 The full regime, layer by layer

| Layer | Rule (verified this wave) | Confidence |
|---|---|---|
| Account bind | Mi account added in Dev options ("Mi Unlock status → Add account and device") — binds account+device pre-unlock | HIGH |
| Application | **Xiaomi Community app** (≥5.3.31), region set to Global, "Unlock bootloader → Apply for unlocking" | HIGH (xiaomi.eu threads) |
| Daily quota | Applications capped ~**2000 licenses/day**; resets **00:00 Beijing (GMT+8)**; quota exhausts in seconds-to-minutes on busy days | HIGH (reddit/xiaomi.eu, consistent) |
| Per-account quota | 2024: 3 devices/account/year (global). **Jan 2025 rule: 1 device/account/year** (ximitime: "limiting unlocking to one device per application effective January 2025") | MEDIUM-HIGH (press + policy posts) |
| CN extras | Community level ≥5 (quiz grind), 3 unlocks per qualification, **365-day qualification validity** (reddit PocoPhones CN rules) | MEDIUM (CN-market sources) |
| Post-bind wait | **72 hours of "normal use"** after binding before Mi Unlock Tool will execute (c.mi.com official guide: "may still ask you to wait for 168 hours (7 days)" on some accounts) | HIGH (official forum + community) |
| Token window | The bound unlock permission decays — re-bind if weeks pass; door map's ~14-day token validity (LOW-MEDIUM). Treat the bind as fresh-only | LOW-MEDIUM |
| Execution | Mi Unlock Tool (Windows, signed-in account) → `fastboot oem unlock`-class → **wipe** (D2) | HIGH |
| Post-unlock costs | Widevine drops L1→L3, some payment/Play-integrity features lost; updates on unlocked HyperOS require relock dance | HIGH (community) |

The 72h wait + the 00:00-Beijing quota reset are the two schedulable resources (§9). The
**lokey0905/Xiaomi-Bootloader-Unlock-Request-Helper** repo proves the pattern: it extracts
the new_bbs_serviceToken, syncs to UTC+8 with millisecond offsets from timeshift.txt, and
fires the authorization request at ~00:00 Beijing — an automated quota sniper. The lab's
scheduler generalizes this.

### 2.2 What the unlock actually does / MTK-SD / HyperOS FRP

- Unlock chain of custody: BL unlock bit → fastboot accepts `flashing`/custom recovery →
  recovery can reach `/data` blocks but **FBE-CE stays sealed without the credential**
  (W1a §2c trap). Data on unlock: **gone** (wipe + KV). Custom recovery afterwards = flash
  freedom, not data freedom.
- **MTK vs SD for EDL rescue:** SD Xiaomis = vast leaked-firehose ecosystem (edl.py
  autodetect, per-model loaders); newer SD models demand authenticated EDL (edl Issues
  admit unsupported walls — box tools hold the auth'd loaders). MTK Xiaomis ride mtkclient
  (pre-V6 BROM exploit era) or the V6 loader route (W2a §3.2). EDL rescue on locked birds
  = service-lane flash (stock ROM restore) + raw partition reads feeding W2b — never a
  shortcut past the credential.
- **HyperOS FRP additions:** stock Google FRP (wizard account check) PLUS the Mi-account
  bind regime — the account that gates your bootloader also gates re-enrollment; Mi Cloud
  Find Device is the remote wall-keeper. Practical read: a wiped HyperOS bird presents two
  re-enrollment walls, but both are post-wipe walls — data already gone (§7 ordering).

---

## 3. HUAWEI / HONOR — THE GRAVEYARD, DATED

| Era | Unlock mechanism | Death | 2025 status |
|---|---|---|---|
| ≤ May 2018 | **Official bootloader codes** (EMUI website, free, IMEI→code) | Website closed May 2018 | DEAD (codes still work on those old devices if you have one) |
| 2016–2018 Kirin (65x/95x class) | **PotatoNV** (kitsuned): NVME-partition `nvecommand` R/W via board-software bootloader — writes unlock flag; free, test-point-ish | Kirin 980+ | ALIVE on that specific old fleet (GitHub, CONFIDENCE: MEDIUM-HIGH) |
| Kirin 710/970/980 era | **DC-Unlocker / HCU / NCK** paid loaders + test point (credits $4–150 per unlock class, LOW) | Kirin 980+/EMUI 10+ mostly fail (hosbootloader 2025 writeup) | SHRINKING per generation |
| Post-2020 Kirin (9000-class) | Nothing public; HiSilicon boot chain is Huawei-proprietary — **no public 9008/firehose standard**. "FTD": the box ecosystem's name for Huawei's proprietary test-point+loader rescue lane (CONFIDENCE: LOW — treat as HCU/DCU protocol, not an open lane) | — | DEAD for OSS; paid-box per-model at best |
| HarmonyOS 4.2+ | Claim: kernel-level attestation zeroes the unlock flag every reboot — unlocks temporary at best (hosbootloader, single source) | — | CONFIDENCE: LOW until reproduced |
| **HarmonyOS NEXT (5.x)** | New arch: no AOSP kernel, no APKs, no fastboot unlock concept — the entire Android unlock doctrine is inapplicable | — | Out of scope; treat as a different OS planet |
| 2023+ SD-SOC Huawei tablets/phones | XDA 2025: free rewritten tool, permanent BL unlock for SOME new Snapdragon Huawei devices (no paid tools) | per-model | CONDITIONAL — the one live lane (CONFIDENCE: MEDIUM, XDA thread) |
| Honor (post-Nov 2020 split) | No official unlock; early Honor (SD/MTK) shares paid-server routes; some deep-testing-like programs appeared and closed | — | Mostly paid/DEAD |

**FRP:** GMS-era Huawei (≤2019) = Google FRP, bypassable with stale-firmware tricks on old
patch levels (CONDITIONAL). Post-2019 (no GMS) = **Huawei ID** activation wall instead —
the wizard demands the Huawei account. HarmonyOS = Huawei ID + cloud. **Realistic doors
2025:** (1) stale-EMUI FRP tricks on the old GMS fleet, (2) PotatoNV on Kirin-65x/95x
sacrificial twins, (3) the new SD-Huawei tool where the model qualifies, (4) silicon lane
(raw dumps → W2b) as with any bird. Everything else is paid-server archaeology.

---

## 4. OPPO / vivo / realme / iQOO (BBK)

| Surface | Reality | Confidence |
|---|---|---|
| SoC mix | Flagships QCOM; budget lines (OPPO A, realme C, vivo Y, iQOO Z-variants) **MTK-heavy** — the BROM lane's home turf (W2a §3) | HIGH |
| Engineer modes | OPPO `*#808#` lineage (engineer mode), `*#899#` service/diag class; vivo `*#558#`-lineage — per-model, used by box tools as service lanes; dial-code folklore drifts per build | MEDIUM (codes LOW per-model) |
| Deep Testing (OPPO/realme official unlock app) | Requests a device-specific fastboot key from oplus servers, **writes it to the oplus/oppo `reserve1` partition**, which fastboot later reads during unlock — verified mechanics (bootloader-unlock-wall-of-shame). Availability per-model/per-region, programs open and close | HIGH (repo-documented) |
| vivo/iQOO official unlock | **None. No portal, no working `fastboot flashing unlock`**, no Deep Testing equivalent (wall-of-shame verdict). Historical exception: `fastboot bbk unlock` verb on CN iQOO 3-class (XDA). CN OriginOS downgrade+exploit paths exist, anti-rollback trips on global FuntouchOS (hosbootloader, MEDIUM-LOW) | HIGH on "none" |
| MSM Download Tool | Per-model leaked packs flash in EDL 9008 (rescue/unbrick/downgrade on locked BL); edl.py V3 identity path tested on OPPO/OnePlus SM8350-class (W2a §2.2). Downgrade = old-bug reopening chain | HIGH |
| BBK account locks | lock.oppo.com (OPPO find-my/activation lock class), vivo/iQOO cloud account — gate re-enrollment + find-my; what they lock: post-reset re-activation with the vendor account on top of Google FRP | MEDIUM |
| Community unlock reality | Mostly **paid third-party servers** (credit-based unlock/FRP services); no free official lane except Deep Testing windows | HIGH |

Chains: MTK budget birds → mtkclient (BROM/V6 loader route) → FRP/seccfg partition ops →
reset-to-usable; QCOM birds → leaked firehose/MSM pack → raw dumps → W2b; flagship BBK =
EDL-loader-or-nothing, same as everyone's QCOM.

---

## 5. GOOGLE PIXEL — THE CLEAN DOOR AND THE BUG CLASS

| Fact | Detail | Confidence |
|---|---|---|
| Unlock | `fastboot flashing unlock` — free, instant, **wipes data** (by design). No account, no quota, no clock | HIGH |
| Relock | `fastboot flashing lock` — restores AVB enforcement; with stock images = GREEN state (verified boot clean) | HIGH |
| AVB states | GREEN (locked+stock), **YELLOW** (locked + custom key/root of trust), ORANGE (unlocked), RED (verification fail) | HIGH (AVB 2.0 spec) |
| GrapheneOS-style footprint | Custom OS flashes its **own verified-boot public key to the secure element** (Titan M2 on Pixel 6+; discuss.grapheneos.org: "Installing GrapheneOS flashes the GrapheneOS verified boot public key to the secure element. Each boot, this key is loaded and used to verify the OS") → relocked bootloader = YELLOW-state verified boot with full integrity — a real custom-AVB relock. Reverting to stock requires `fastboot erase avb_custom_key` before relocking | HIGH |
| Recon value | A bird arriving YELLOW/relocked-custom: prior owner was privacy-literate, likely strong passphrase, data likely present, attestation-literate — triage it as a high-effort data bird, not a refurb bird | doctrine |
| CVE-2024-22012 | Pixel 6a **ABL fastboot control-request OOB write**; the overflowed memory held **USB-stack function pointers — overwriting them allowed arbitrary bootloader code execution**; disclosed to Google Nov 2023, patched in the **2024-02 Pixel bulletin**; CVSS 7.8, **no user interaction required** (Black Hat Asia deck, BHAS26-Wade, fetched this wave — primary source) | HIGH |
| CVE-2025-36907 | `draw_surface_image()` heap overflow in ABL, CVSS 7.3 — **requires bootloader ALREADY unlocked + user interaction** (NVD). Correction to W1a §2d's romance: this is a POST-unlock surface, not a locked-bird lane. Its value: proof the ABL attack surface keeps producing; fuzz-target class | HIGH (NVD) |
| Exploitation lane on UNPATCHED arrivals | A 6a (or sibling ABL generation) below 2024-02 patch: boot-code execution **without unlock, without wipe** → dump pre-boot material / instrument the boot chain → W2b. The installed base of stale Pixels is small but real | doctrine on HIGH facts |
| Offline math | Weaver slots live in Titan M2 — **offline credential attack starves without a TEE exploit** (W1a §2g). Pixel = the best-locked data bird despite the easiest boot door | HIGH |
| Dev-bird role | Every chain in the method compiler regresses on Pixel first: unlock→flash→instrument→relock is a closed loop with published images, per-build boot chains, and the cleanest docs. Pixel is the lab's reference frame | doctrine |

---

## 6. TRANSSION (TECNO / itel / Infinix) + MISC BUDGET FLEET

The softest fleet, with real numbers (hosbootloader 2025 table — CONFIDENCE: MEDIUM unless
otherwise tagged):
- **Carlcare walk-in** (Transsion's own service arm): official unlock token, **$0–15,
  within ~1 hr** if policy allows — the cheapest official unlock in the industry.
- **TSM-Tool online**: ~6 credits ≈ **$3** direct unlocks for 2023–24 MTK/SPD models
  (Spark 20C, Camon 20, Hot 30 5G class).
- **Hydra / CM2 box**: ~$10–15 legacy MTK 2016–2021 BROM unlock + FRP in one pass.
- **mtkclient**: $0 on BROM-era SoCs; V6 loader route on newer (W2a).
- **SPD/Unisoc units** (big slice of itel): separate lane — SPD flash tools
  (ResearchDownload class), SPD-specific FRP utilities; three-button mode entry.

Why soft: old BSP levels ship for years, patches lag, bootloaders unlocked-or-sloppy out of
the box, factory-test modes survive, and the glass-plane dead-trick catalogue (W1a §2a) is
CONDITIONAL-to-ALIVE here. **Volume reality:** Transsion-class devices dominate the budget
markets (sub-Saharan Africa ~40%+ share class, LOW on exact figure) — this is the fleet a
DZ-market unlock shop actually sees, hence the lab's training ground AND its volume
business. Doctrine: skills pay their rent here first (cheap birds, BROM reps, glass-bug
verification), then graduate up the vendor ladder.

---

## 7. FRP LANDSCAPE — CONSOLIDATED

**What FRP actually is:** a wizard-state gate AFTER a wipe — the setup wizard demands the
Google account previously synced before it lets the device enroll. It is policy plumbing
in the setup flow, not cryptography; it never held data keys (W1a layer 6). Vendor variants
add their account on top:

| Vendor | FRP = Google + | Notes |
|---|---|---|
| Samsung | Samsung account (S-cloud re-enrollment on post-2019 class) | Reactivation Lock = the pre-2018 ancestor (§1.4) |
| Xiaomi | Mi account bind (HyperOS) | The bootloader-bureaucracy account doubles as re-enrollment wall |
| Huawei | ≤2019: nothing extra (GMS); post-2019: **Huawei ID** replaces Google entirely | Two different planets |
| BBK | OPPO lock / vivo-iQOO cloud account | `reserve1`-class vendor partitions carry unlock keys |
| Transsion | Rarely more than stock Google FRP | Stale builds = bypassable |
| Pixel | Nothing beyond Google | Cleanest |

**2024–25 bypass reality:**
- **SIM-PIN change race: DEAD** on patched (W1a). **TalkBack/wizard intent escapes: DEAD on
  current majors, ALIVE on stale fleet** — Transsion/old-EMUI/old-One-UI patch levels
  (CONDITIONAL per bird; the ≤Aug-2022 Samsung patch class is the documented boundary for
  the tool-assisted family, XDA tags).
- **MTK birds + mtkclient:** `e frp` erases the FRP partition directly (godnessprojects
  mtkclient function docs — verified verb list W2a §3.2); `da seccfg unlock` is a DIFFERENT
  operation (BL-unlock bit surgery, D3-adjacent, wipes metadata/userdata per documented
  flow). DA-auth removal: the `payload` generic-patcher bypasses SLA/DAA/SBC where the chip
  permits (W2a). FRP partition erase = instant wizard-pass on MTK birds where BROM/DA
  access exists. CONFIDENCE: HIGH on verbs, MEDIUM on per-model FRP layout.
- **QCOM/SD birds + EDL:** FRP lives in frp/misc-class partitions per model — `e misc` /
  raw writes via firehose where a signed loader exists (W2a §2.3, edl `e`/`w` verbs).
  Loader-gated exactly like everything EDL.
- **The honest ordering (crown law):** FRP only matters AFTER a wipe decision — and the
  wipe already destroyed the data (FBE keys + KV). **FRP bypass ≠ data recovery, ever.**
  FRP work makes a bird *re-usable/resellable* (reset-to-usable lane); it is never a data
  door. The universal system books every FRP chain under refurb economics, not crown
  economics.

---

## 8. THE CHAIN LIBRARY — skill candidates for the method compiler

Format: name · arrival state → numbered steps · tools · expected evidence · cost/time ·
preconditions (plane, danger class). All chains assume intake triage done (BFU/AFU first —
W1a §5). Data-sacred birds: D0 chains only, ever.

### 8.1 SAMSUNG
**S1 · KG-PRENORMAL WAIT CHAIN** · locked Exynos/SD, KG=PRENORMAL, OEM forbidden, bird is
sacrificial-or-refurb.
1. Download Mode read → record KG STATE/OEM/FRP lines (evidence row).
2. Boot to system with SIM + network; keep on charger; **no reboot** for 168 h.
3. Day-7 check-in → re-read Download Mode → COMPLETED; toggle appears.
4. Enable OEM unlock → Odin unlock (wipe, D2) → VaultKeeper verify → flash freedom.
Tools: hands + Odin. Evidence: before/after Download Mode photos, toggle screenshot.
Cost: $0 / 7 days parked. Preconditions: flash plane; D2 (wipe at step 4), D1 before.
**S2 · COMBINATION FIRMWARE CHAIN** · FRP-locked or DRK-broken refurb bird, combo exists
for model+CSC+Android match.
1. Source combo (samfw-class free / grey $50–150 LOW) — verify model/CSC/version match.
2. Odin flash combo (AP) — **wipe on flash, D2**.
3. Combo's service surface: ADB-enabled build (era-dependent — verify per One UI level),
   FRP-bypass surface, OEM-unlock visibility.
4. Flash stock or TWRP per goal; boot direct to recovery (never OS first).
Evidence: Odin logs, combo build props. Cost: $0–150 / 1–2 h. Preconditions: flash; D2.
**S3 · KG-FINANCED RELEASE CHAIN** · KG=ACTIVE/LOCKED, financed.
1. Read KG lock screen (wallpaper/reminder = policy state evidence).
2. Lock screen → Support → Refresh account status (fetches latest policies — official
   troubleshoot path).
3. Real release = financier-side: Completing (2-day cancel window) → Completed.
4. Verify: KG client deactivates; Download Mode state changes.
Cost: $0 if legit; no software bypass exists (paid KG/RMM unlock = ChimeraTool-class,
$150–400/yr LOW, refurb-only). Preconditions: cloud plane, D1. Not a data chain.
**S4 · EXYNOS ARTIFACT CHAIN (sacrificial twin)** · dead-end Exynos bird, data wanted.
1. Download Mode recon + UART capture if pads live ($3 adapter).
2. ISP/chip-off raw dump (T3 rig) → gatekeeper/spblob/persist blocks.
3. Feed W2b offline credential attack → recovered PIN → boot normally → AFU data.
Preconditions: silicon plane; D0 read (reball risk D4 on the twin only). Cost: rig + hours.

### 8.2 XIAOMI
**X1 · TOKEN-WINDOW CHAIN** · sacrificial HyperOS bird, BL locked, Mi account in hand.
1. Install Xiaomi Community ≥5.3.31 → region Global → log in.
2. Apply for unlocking — **retry loop against the 2000/day quota** (auto-retry at 00:00
   Beijing; lokey0905-class sniper pattern).
3. Permission granted → Dev options → Mi Unlock status → bind account + device.
4. **Park 72 h** of normal use (scheduler owns the clock).
5. Mi Unlock Tool → unlock → wipe (D2) → custom recovery / reset-to-usable.
Evidence: app screenshots, tool logs. Cost: $0 / 72 h + quota luck. Preconditions: flash +
software; D2 at step 5.
**X2 · SD-EDL ARTIFACT CHAIN** · SD Xiaomi, loader known.
1. `adb reboot edl` or button/EDL-cable → 9008.
2. edl.py autodetect → loader match → `printgpt`, `rl dumps --skip=userdata`.
3. Raw artifacts → W2b offline attack.
Preconditions: silicon; D0 (reads only). Cost: $0 / 30–90 min.
**X3 · MTK-BROM CHAIN** · MTK Xiaomi (pre-V6 SoC), BROM live.
1. Hold Vol± → BROM → mtkclient `r`/`rl` dumps → W2b; or `da seccfg unlock` (D3-ish, wipes)
   for BL freedom.
Preconditions: silicon; D0 read path / D2-D3 write path. Cost: $0 / 15–60 min.

### 8.3 HUAWEI
**H1 · POTATONV CHAIN (Kirin 65x/95x)** · 2016–18 Kirin bird.
1. Open bootloader slot / test-point entry per repo docs.
2. PotatoNV NVME write → unlock flag → fastboot unlock (wipe D2).
Cost: $0 / hours. Preconditions: silicon+flash; D2. CONFIDENCE: MEDIUM-HIGH (repo).
**H2 · STALE-FIRMWARE FRP CHAIN (GMS-era)** · old EMUI bird in wizard.
1. Patch-level check → apply W1a §2a stale-fleet catalogue per build.
2. Escaped session → settings → OEM toggle/de-FRP.
Preconditions: glass; D0-D1. Cost: $0 / minutes-hours per bird.
**H3 · SD-HUAWEI TOOL CHAIN (2023+ SD models)** · per XDA 2025 tool list.
1. Model qualifies → tool run → permanent BL unlock (verify per device).
Preconditions: flash; D2. CONFIDENCE: MEDIUM (XDA, single evolving thread).

### 8.4 BBK
**B1 · MTK-BUDGET BROM CHAIN** · realme/OPPO-A/vivo-Y MTK unit.
1. BROM entry → mtkclient dumps (artifact feed) or `e frp` (reset-to-usable) or
   `da seccfg unlock` (BL, wipes).
Cost: $0 / 15–60 min. Preconditions: silicon; D0 or D2-D3.
**B2 · MSM RESCUE/DOWNGRADE CHAIN** · bricked-or-stale QCOM BBK.
1. Source per-model MSM pack (grey) → EDL 9008 → flash stock (rescue) or older build
   (downgrade → re-open old bugs → glass catalogue re-applies).
Preconditions: flash; D2-D4. Cost: $0 (pack hunt) / 30–90 min.
**B3 · DEEP TESTING CHAIN (where open)** · supported OPPO/realme model + region window.
1. Install Deep Testing → request key → key lands in `reserve1` → fastboot unlock (wipe).
Preconditions: flash + cloud; D2. Availability per-model — check before promising.

### 8.5 PIXEL
**P1 · DEV-BIRD REGRESSION CHAIN** · lab Pixel, every method-compiler release.
1. `flashing unlock` (wipe, D2) → flash test images → instrument (Frida class, W1a §4.7)
   → `flashing lock` (GREEN) → repeat.
Evidence: full loop logs = the regression suite. Cost: $0 / 1–2 h per cycle.
**P2 · UNPATCHED-ABL CHAIN (research)** · Pixel 6a-class below 2024-02 patch, sacrificial.
1. Verify patch level (Settings/build prop, D0).
2. CVE-2024-22012-class ABL USB exploit → boot-code execution pre-unlock (no wipe).
3. Instrument/dump pre-boot material → W2b feed.
Preconditions: flash/silicon exploit lane; D0 reads on target, brick-risk D4 sacrificial
only. CONFIDENCE: mechanics HIGH (primary deck), operational repro MEDIUM until trialed.

### 8.6 TRANSSION
**T1 · CARLCARE/TSM OFFICIAL CHAIN** · any current Transsion refurb.
1. IMEI/model check → Carlcare walk-in ($0–15, ~1 hr) or TSM-Tool (~$3) → official token.
2. fastboot unlock (wipe D2) → done.
Cost: $3–15 / 1 hr. Preconditions: flash; D2. CONFIDENCE: MEDIUM (single 2025 table).
**T2 · BROM → DUMP → OFFLINE ATTACK CHAIN** · MTK Transsion, data wanted (the lab's W2b
feeder): BROM → `rl` full dump → gatekeeper/spblob artifacts → W2b offline PIN → boot with
PIN → AFU extraction. Preconditions: silicon; D0 (dump) — the crown-compatible shape.
**T3 · SPD LANE** · itel/Unisoc unit: SPD-mode entry → SPD tools → FRP/flash ops. LOW
confidence on per-model mechanics; treat as its own armory map.

---

## 9. WAIT-CLOCK AUTOMATION — THE SCHEDULER MODULE

The new-era truth: vendors replaced crypto walls with **bureaucracy walls measured in
days**. A human shop cannot babysit a 7-day uptime clock or a 72-hour bind window for
free — an autonomous system does it at $0 marginal cost. This is where LLM autonomy beats
every human shop.

| Clock | Owner | Duration | Reset/abort behavior | Read lane |
|---|---|---|---|---|
| KG PRENORMAL uptime clock | Samsung | 168 h (SIM+net, no reboot) | Reboot resets; no-net = clock never runs | Download Mode state; uptime in Settings |
| KG activation window (financed) | Samsung console | 7 days from first boot | Missed → manual activation via guard.samsungknox.com or factory reset | KG console state; lock-screen Support |
| KG Completing window | Samsung console | 2-day cancel | Then permanent Completed | Console / device check-in |
| Mi bind wait | Xiaomi | 72 h "normal use" | Bind decays (~14-day token class, LOW) → re-bind | Dev options Mi Unlock status |
| Mi application quota | Xiaomi servers | Resets 00:00 Beijing daily (~2000/day) | Miss → next day's window | Community app response |
| (legacy) MIUI wait | Xiaomi | 168 h on old accounts (c.mi.com) | — | Mi Unlock Tool |

**Scheduler design (module spec for the orchestrator):**
1. **PARK states as first-class objects:** a chain that hits a clock transitions to
   `PARKED_<clock>` with: bird id, clock type, start timestamp (uptime-based where
   required), required environmental preconditions (charger, SIM, network), the resume
   chain pointer, and the evidence row capturing the state that started the wait.
2. **Environmental babysitting:** KG uptime clocks die on reboot and battery loss — the
   scheduler holds the bird on bench power, polls uptime via authorized adb where present
   (`Settings` readout otherwise), and treats any reboot as a clock-reset event to refile.
3. **Scheduled re-checks:** calendar-based probes (day-7 Download Mode re-read for KG;
   72-h bind status for Xiaomi; 00:00-Beijing quota sniper with retry loop, lokey0905
   pattern — sync UTC+8, fire at window open, verify, retry next window on quota miss).
4. **Resume:** on clock-expiry evidence (state transition observed — never assumed), the
   parked chain re-arms automatically: S1 step 4 fires, X1 step 5 fires. Every resume
   writes its own evidence row before the destructive step (SILICON-3 habit).
5. **Portfolio effect:** clocks park in parallel — the lab runs 10 birds × mixed clocks at
   zero labor; a shop cannot. Queue discipline: cheapest-clock-first when chains contend
   for the same account resource (Xiaomi 1-device/year quota = the scarce resource).
Failure modes to encode: reboot-reset (KG), quota-exhaustion (Xiaomi), token-decay
(re-bind), network-loss (clock silently stalled — poll for connectivity), false-COMPLETED
(paid-tool forgeries of state — verify against two read lanes).

---

## 10. VENDOR MATRIX

| VENDOR | BL unlock path | Cost / wait | KG/account locks | Silicon lane (W2a) | Glass-trick likelihood | FRP reality | Best chain for the lab |
|---|---|---|---|---|---|---|---|
| Samsung | OEM toggle + Odin (KG-gated) | $0 / 0–7 days | KG ACTIVE/PRENORMAL, Knox fuse (D3), Samsung acct | Exynos: none public; SD: no leaked Samsung loaders; Download Mode signed-only | Low on current; ≤2022-patch birds mid | Google+Samsung, combo-relevant | S1 wait chain; S2 combo for refurbs |
| Xiaomi | Community app + Mi Unlock | $0 / 72 h + quota lottery | Mi account bind; 1 device/yr (2025) | SD: vast loader ecosystem; MTK: mtkclient/V6 | Low-mid (stale MIUI) | Google + Mi account | X1 token chain; X2 EDL feeds |
| Huawei | None official; per-era tools | $4–150 / hours-days (LOW) | Huawei ID post-2019 | Kirin: proprietary test-point lane only; SD-2023+: new tool | Mid on old EMUI | GMS-era Google; then Huawei ID | H1 PotatoNV (old Kirin); H2 stale-FRP |
| BBK | Deep Testing (per-model) / none (vivo) / paid servers | $0–tens / varies | OPPO lock, vivo cloud | MTK: BROM home turf; QCOM: MSM/firehose packs | Mid (stale ColorOS) | Google + vendor acct | B1 BROM chain; B2 MSM rescue |
| Pixel | fastboot — free, instant | $0 / minutes | Google only | (no EDL need); ABL bug class as exploit lane | None worth trying | Google only | P1 regression loop; P2 unpatched-ABL |
| Transsion | Carlcare/TSM official + BROM | $0–15 / 1 hr | Rarely more than Google | BROM/SPD lanes wide open | HIGH (stale fleet) | Google, bypassable | T2 BROM→W2b crown chain; T1 volume |

---

## VENDOR VERDICT — RANKED DIFFICULTY FOR THE UNIVERSAL SYSTEM (2025)

Ranked easiest → hardest for the crown mission (owner-absent data recovery), with the
refurb/reset mission in parentheses where it diverges:

1. **TRANSSION** — every lane open: official tokens for $3–15, BROM for free, glass tricks
   alive, W2b fed daily. The volume business and the training ground in one fleet. (Refurb:
   trivial. Data: easy-to-medium per PIN strength.)
2. **XIAOMI** — bureaucracy heavy but *schedulable*: the quota and the 72-h clock are
   automation food; EDL/MTK lanes feed W2b on QCOM/MTK models. The 1-device/yr quota is
   the only real brake. (Refurb: easy with patience. Data: medium.)
3. **GOOGLE PIXEL** — paradox bird: the easiest unlock in the industry wrapped around the
   hardest offline-credential wall (Weaver in Titan M2). Reset trivial; data requires AFU
   arrival or an ABL/TEE exploit on a stale bird. The dev frame for everything.
4. **SAMSUNG** — the best-mapped state machine, the most schedulable clock (168 h), combo
   lanes for refurbs — but Exynos birds have no silicon feed without a T3 rig, and the Knox
   fuse makes every move a one-way door on data-sacred birds. Sequence discipline or lose.
5. **BBK (OPPO/vivo/realme/iQOO)** — MTK lines are Transsion-soft; QCOM lines are
   loader-or-nothing; vivo global is a wall with no door but paid servers. Inconsistent by
   sub-brand: index by SoC first, brand second.
6. **HUAWEI/HONOR** — the graveyard. Official unlock dead since 2018; Kirin silicon lanes
   proprietary and shrinking; HarmonyOS NEXT leaves the Android doctrine entirely. Only
   stale-EMUI tricks, one old free tool (PotatoNV), one new narrow tool (SD-2023+), and
   silicon. Most arrivals: park the bird or part it out.

The 2025 pattern, stated once: **vendors moved the wall from silicon to paperwork.** The
locks that still fall, fall to schedulers, quota snipers, loader libraries, and offline
math — exactly the four things an LLM-operated lab runs natively and a human shop runs
badly or not at all.

---

## SOURCES — THIS WAVE (fetched/DDG via html.duckduckgo.com, web_search dead)

- Samsung Knox admin docs — Knox Guard status flow (Pending/Activating/Active/Locked/
  Completing/Completed, 7-day activation window, 2-day Completing cancel, Refresh account
  status) docs.samsungknox.com/admin/knox-guard/get-started/knox-guard-status-flow/
- thecustomdroid Prenormal guide (RMM→KG rename, 168 h/SIM/network/no-reboot, KnoxGuard.apk/
  RLC.apk + services.jar cause, corsicanu/BlackMesa123 bypass v3, boot-direct-to-TWRP rule)
- XDA threads 4100957/4766345/3891193 + kg/rmm-prenormal tag corpus (date-rollback tricks,
  OEM=OFF + Prenormal combinations); Reddit r/S22Ultra Download-Mode indicators thread
  (Prenormal/Checking/Completed + RPMB/FRP/OEM lines)
- eu.community.samsung S22 Ultra thread (KG State: Active on retail — financed class)
- xiaomi.eu threads 71323/71752 + r/Xiaomi 1ag4fsh + r/PocoPhones 1afskze (Community app
  flow, 2000/day GMT+8 quota, 3/yr→1/yr Jan 2025, 72 h bind, 365-day CN qualification)
- c.mi.com official guide (168 h/7-day account wait) · ximitime Jan-2025 policy article ·
  github.com/lokey0905/Xiaomi-Bootloader-Unlock-Request-Helper (00:00-Beijing sniper)
- github.com/kitsuned/PotatoNV (NVME nvecommand) · xdaforums 4780724 (SD-SOC Huawei tool)
  · hosbootloader.blogspot 2025 Huawei/vivo/Infinix tables (paid-tool failures, prices)
  · deepwiki wall-of-shame Huawei/vivo chapters · dc-unlocker feature table
- bootloader-unlock-wall-of-shame (zenfyrdev) OPPO README + deepwiki Deep Testing chapter
  (reserve1 partition mechanics) · getdroidtips MSM Download Tool · xdaforums iQOO 3
  (`fastboot bbk unlock`, CN-only history)
- NVD/cve.org CVE-2025-36907 (draw_surface_image ABL heap overflow; post-unlock; user
  interaction; CVSS 7.3) · Black Hat Asia deck BHAS26-Wade "Practical Attacks" (Pixel 6a
  ABL USB-stack function-pointer overwrite → arbitrary bootloader code; Nov 2023
  disclosure) + CVE-2024-22012 record (2024-02 Pixel bulletin patch)
- discuss.grapheneos.org + XDA GrapheneOS thread (avb_custom_key to secure element,
  `fastboot erase avb_custom_key`, yellow-state relock) · avbroot repo (custom-key AVB)
- godnessprojects.github.io mtkclient functions (`e frp`) · deepwiki mtkclient seccfg
  chapter (V2/V3/V4 + signing) · samfw.com combo listings (XDA 4575795) · getdroidtips
  combination-ROM purpose list · amoamare Legacy-Samsung-Reactivation-Lock-Removal (S5
  QSEE/libterrier lineage) · T-Mobile/wer.org Reactivation Lock removal paths
- Prior waves: 01_universal_door_map.md, 03_silicon_plane.md (state machine, FBE trap,
  loader economies, V6 list, danger-class vocabulary).

*Wave W3 complete. These chains are the skill candidates: feed §8 to the method compiler
(W1a §4.6) and §9 to the orchestrator's scheduler spec (02_llm_orchestrator_architecture.md).*
