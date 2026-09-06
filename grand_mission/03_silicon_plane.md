# THE SILICON PLANE — W2a
*Grand Mission 03 · DroidCommand / Vesper · the hardware-rig doctrine for the universal
unlock system. Builds on 01_universal_door_map.md §2d (bootloader/flash) and §2e
(silicon) — this wave expands those rows into full operating doctrine: rigs, entry modes,
tool reality, per-chip feasibility, economics, acquisition tiers, and the exact
interface where LLM decisions stop and operator hands begin.*

Laws carried: GATE-17.14 (THE CROWN — owner absent, no biometrics, no credentials ever),
GATE-17.15 (THE INTERIOR — reason from state, not glass), GATE-17.13 (credential = a
STATE we compute, never guess at the glass), SCOPE GUARD (flash/destructive ops on
sacrificial birds only; LO's personal bird is data-sacred).

Verdict vocabulary (inherited from the door map): **ALIVE** (works on current builds or
needs only cheap hardware), **CONDITIONAL** (per-model / per-build / per-arrival-state),
**DEAD** (patched era, kept for lineage). Confidence flags: **CONFIDENCE: HIGH**
(multi-source + primary doc), **MEDIUM** (press-verified or single good source),
**LOW** (folklore / vendor-unpublished / price guess). Prices always `~$` with LOW
unless a vendor publishes.

Verification base: live fetches this wave — mtkclient README + README-USAGE (bkerler,
master), edl README (bkerler, master, incl. the Sahara-V3 fork fixes), Donjon CVE-2025-
20435 press family (Forbes/Yahoo Tech, Quokka, CCN, Gate.com, AndroidHeadlines), plus
the predecessor unit's salvaged verified facts (V6 chip list, edl-repo master branch,
CVE reality) and repo evidence (`_research/extracted_A217F` corpus — the lab bird).

---

## 1. WHY SILICON AT ALL — THE HONEST LADDER

The universal system sweeps planes in strict escalation order. Each plane seals, and
when it seals you do not wish at it — you drop one plane lower. The ladder, honestly:

| Rung | Plane | Opens | Seals when | Fall-through |
|---|---|---|---|---|
| 0 | Glass (UI tricks, HID siege) | Stale-fleet sessions, short PINs | Patched build + strong credential | → rung 1 |
| 1 | ADB / shell (uid 2000) | AFU data exfil, state surgery on no-lock devices | Debugging unauthorized, or BFU + credential | → rung 2 |
| 2 | Bootloader / flash (fastboot, Odin, tokens) | Flash plane, reset-to-usable, combo-firmware surfaces | Locked BL + vendor unlock forbidden (KG ACTIVE, carrier builds, HyperOS quotas) | → rung 3 |
| 3 | **Silicon (this wave)** | Boot control below the OS, raw flash R/W, pre-boot key extraction | Per-SoC: patched bootroms, signed-loader walls, RPMB-bound keys — the LAST plane before rung 4 | → rung 4 |
| 4 | Offline math (artifact attack, W2b) | The credential itself, computed off-device | No artifact read achieved → rung 3 is the only way to feed it | (fed BY rung 3) |

The honest sentence: rungs 0–2 never open a current, patched, BFU, credentialed phone
(door-map summary #1). Rung 4 is the crown-compatible finisher but it starves without
rung 3 feeding it artifacts. **Silicon is the feeding plane.**

Silicon carries exactly two roles, and conflating them is the classic world's most
common confusion (door-map §2c FBE-CE trap):

| Role | What it means | Concretely (2025) | What it does NOT give |
|---|---|---|---|
| **(a) BOOT CONTROL** | Force the SoC to boot/accept unsigned code below Android | EDL firehose, MTK BROM payload, Download Mode signed flash, JTAG halt | It does NOT decrypt CE data — FBE keys are credential-wrapped (door-map layer 3/4). Boot control ≠ data |
| **(b) ARTIFACT / KEY EXTRACTION** | Read raw storage or TEE key material out of the device | eMMC/UFS raw dump → gatekeeper/spblob/locksettings offline attack (W2b); pre-boot key dump (CVE-2025-20435 class) → root keys → offline PIN brute → full decrypt | On AFU arrivals it is redundant (cheaper software paths exist); its whole value is the BFU bird |

Door-map plane wiring: role (a) extends §2d rows (EDL/BROM/Odin) — it is the flash plane
entered without vendor permission. Role (b) is §2g's feeding precondition ("artifact
READ requires one of: root/recovery, EDL/BROM dump, ISP/reader raw image, pre-boot key
dump") — this wave is the doctrine for the last three of those four feeds, plus the
state-triage (BFU/AFU, §4.8) that decides whether silicon is even needed.

**The decision rule for the rig:** if arrival triage says AFU + authorized shell →
silicon is unnecessary (software exfil). If BFU + credential + current TEE → silicon is
the ONLY remaining plane, and only roles (b)+(a) chained toward W2b can win. If the bird
is boot-dead (no OS to lock) → silicon is the ONLY plane, full stop.

---

## 2. QUALCOMM EDL / 9008 — THE FLASH LANE BELOW FASTBOOT

### 2.1 Mode entry — how a SoC falls into EDL

Qualcomm PBL (primary bootloader) drops to EDL (Emergency Download, a.k.a. Qualcomm
HS-USB QDLoader 9008 mode, USB VID 05c6 PID 9008) whenever it cannot find/validate a
bootloader, or when told to. Entry vectors, cheapest first:

| Vector | How | Works when | Cost |
|---|---|---|---|
| `adb reboot edl` | Shell command | Authorized ADB exists (or any fastboot `oem edl`) | $0 |
| Button combo | Vol-Up + Vol-Dn (both) + plug USB, or Vol-Dn + Power held; per-model variants | Combo not remapped by OEM | $0 |
| Boot-failure auto-EDL | Corrupt/absent XBL/SBL → PBL falls to 9008 automatically | Bird already semi-bricked | $0 |
| EDL / "9908" cable | Cable wired with D+ shorted to GND; force-reboot (Vol-Up+Power >20s or battery pull) → PBL reads garbage on D+ and falls to EDL | XBL not fully broken; works on eMMC and UFS boards | ~$5–15 (LOW) or self-made from a sacrificial cable |
| eMMC DAT0 short | Battery out, short DAT0 to GND, plug battery in, remove short | eMMC devices; forces read failure → EDL | $0 (tweezers) |
| UFS CLK short | Short the UFS clock line at boot — some boards expose dedicated test points for this | UFS devices; fiddly, per-board TP hunt | tweezers + hours |
| Boot-config resistors | Some boards strap boot order (e.g., force SD-card boot) | Per-model; documented on service schematics | $0 if schematic known |

Recovered-from-`0x900E` note (verified, edl README): a semi-bricked bird sitting at USB
PID 0x900E (QDLOAD variant) is recoverable to 9008 via the EDL-cable + force-reboot
trick; the edl toolchain also speaks `--serial`/`--portname COMx` and even a TCP server
mode (`edl server --memory=ufs --tcpport=1340`) — rig-bridge friendly (§7).

### 2.2 Firehose programmer reality — the signed-loader wall

Sahara (the EDL protocol) will only RUN a programmer you supply — the firehose loader
(FHPRG / MBN / ELF "prog_emmc_firehose_****.mbn") — and the SoC verifies it against the
OEM's signing keys burned in QFPROM fuses. The wall, stated plainly:

| Fact | Detail | Status |
|---|---|---|
| Loaders are per-model-signed | Signed for OEM_ID + MODEL_ID + (on secure boot) PK_HASH of that exact device family; a Xiaomi loader won't run on an OPPO of the same SoC | Structural — verified by toolchain design (edl autodetect keys off MSMID + PKHASH) |
| Official loaders | Live inside OEM service packs / MSM Download Tool distributions; never published voluntarily | ALIVE but closed |
| Leaked loaders | The box ecosystem's bread and butter — bkerler/Loaders submodule ships a public stash; grey forums trade per-model packs | ALIVE, ragged coverage |
| Authenticated EDL | Newer Qualcomm chains (e.g. SDM660 Xiaomi era onward) demand a challenge-response auth on top of the signed loader; edl's own Issues list: "Secure loader with SDM660 on Xiaomi not yet supported (EDL authentification)" | CONDITIONAL — per-model hard wall for OSS tooling |
| VIP Programming | Vendor-exclusive firehose verbs — not supported by OSS | Dead end for the lab |
| Making your own loader | `fhloaderparse` ingests your loader collection into the autodetect DB; a Total Phase Beagle 480 USB analyzer can SNIFF a working box-tool session and `beagle_to_loader` reconstructs the loader from the wire | ALIVE — the loader-acquisition loop the armory (W4a) automates |

Autodetect mechanics (verified from edl master README): Sahara V1/V2 read MSM_ID /
OEM_ID / MODEL_ID / PK_HASH and match `msmid_pkhash[8 bytes].bin` filenames in the
Loaders tree; V3 devices stopped answering the old commands, so the current fork reads
`cmd=0x0A` CHIP_ID_V3_READ and reconstructs a V1/V2-compatible HW_ID for lookup —
tested on OPPO/OnePlus SM8350/8450/8550 and Xiaomi SD models. Translation: bird in EDL
→ tool reads identity → DB match → loader sent → firehose alive. That identity-to-loader
match IS the rig's first decision point (§7).

### 2.3 What firehose gives you once alive

| Capability | edl.py verb (verified) | Forensic value |
|---|---|---|
| Partition table | `printgpt` (per-LUN on UFS) | Layout map — feeds artifact-location homework |
| Raw partition read | `r boot_a boot.img`, multi-partition `r boot_a,boot_b …`, sector reads `rs` | THE artifact feed: persist, misc, EFS, userdata blocks — raw copies, lock state intact |
| Full flash dump | `rf flash.bin` / per-LUN `rf lun0.bin --memory=ufs --lun=0`, or `rl dumps --skip=userdata --genxml` | Complete image for offline W2b work (userdata skipped to save time when artifacts live elsewhere) |
| Crypto footer | `footer footer.bin` | FDE-era key material location (legacy fleet only) |
| Partition write | `w`, `wl`, `wf`, erase `e misc` | Boot surgery, FRP-era misc wipes — DESTRUCTIVE (§10 laws) |
| Memory peek/poke | `peek`, `poke`, `peekhex`, `pokeqword` (EL3 loaders only) | RAM surgery on advanced loaders — research lane |
| Fuse reads | `secureboot` (secure-boot fuses), `qfp` (QFPROM), `pbl` (primary BL dump, EL3) | Hardware state recon: secure-boot on/off, anti-rollback counters — pre-flight BEFORE any flash decision |
| OEM unlock bit | `modules oemunlock enable` (where partition "config" exists) | Fastboot-unlock precondition seeding — with wipe consequences, one-way-door ledger applies |
| QFIL emulation | `edl qfil rawprogram0.xml patch0.xml image_dir` | Replicates the official flasher for scripted full flashes |
| Diag lane | separate `qc_diag` tool: NV reads/backups, EFS dumps | IMEI/NV/lock-state raw material |

### 2.4 Tools and lineage

| Tool | License / cost | Notes |
|---|---|---|
| **edl.py (bkerler/edl)** | GPLv3, free; explicit "no commercial use without permit" | The OSS spearhead: Sahara+Firehose+Diag client, loader DB scheme, LiveDVD, Windows PowerShell installer. Our rig's EDL engine |
| **bkerler/Loaders** | submodule of the above | Public loader stash; the armory grows this per model |
| **QFIL / QPST suite** (Qualcomm's own) | free download | GUI flasher, same signed-loader dependency; QPST includes COM-port automation hooks — partially scriptable (§7) |
| **MSM Download Tool packs** (BBK/OEM service packs) | free-floating, leaked | Rescue flashers that carry their own loaders — CONDITIONAL per model |
| **Box ecosystems** (Octoplus, Sigma, z3x, Easy-JTAG/Octopus, UFI) | ~$100–500 + activations/credits (LOW) | Their moat = bundled leaked loader libraries, not the protocol (protocol is open) |

### 2.5 Per-vendor EDL reality (2025)

| Vendor | EDL door state | Notes |
|---|---|---|
| Xiaomi / Redmi / POCO (SD models) | CONDITIONAL | Vast leaked-loader ecosystem per model; newer models = authenticated EDL (edl Issues admit unsupported walls) — box tools often still hold the auth'd loaders |
| OPPO / vivo / realme / iQOO (QCOM units) | CONDITIONAL | MSM rescue packs + `*#808#`-class engineer modes; V3 identity supported by current edl fork |
| OnePlus | CONDITIONAL (historically the friendliest) | edl tested list includes 3T→9/Nord family (some read-only); MSM packs double as unbrick+downgrade lanes → old-bug reopening chains |
| Google Pixel | CONDITIONAL, research-class | Not an EDL-unlock lane (fastboot unlock is free anyway); Pixel ABL fastboot bug class (CVE-2024-22012, CVE-2025-36907) is the live attack surface |
| Samsung (Snapdragon variants) | CONDITIONAL | SD-based Samsungs DO sit on the 9008 lane — but Samsung service loaders are not publicly leaked per-model in the OSS ecosystem; box vendors claim Samsung-SD lanes (LOW). Samsung (Exynos) — see §4: no EDL at all |

### 2.6 Cost of entry

EDL is the cheapest silicon lane: $0 in tools (edl.py + QFIL free), ~$5–15 for an EDL
cable (or self-made), tweezers for test points, plus the real currency — loader
availability per exact model. **No public loader = no public EDL.** The lab's job is
loader curation, not tool buying.

---

## 3. MEDIATEK BROM — THE PRE-AUTH BOOT ROM DOOR

### 3.1 The chain, and where the doors are

| Stage | What it is | Attack surface |
|---|---|---|
| BROM (boot ROM, mask ROM in the SoC) | First code the chip runs; speaks USB via a fixed handler; historically shipped with exploitable bugs because it cannot be patched in the field | Pre-auth memory R/W via exploits — the mtkclient family |
| Preloader (provision/boot partition 1st stage) | Verifies and loads the DA (download agent); enforces SLA/DAA | Load your OWN patched preloader (mtkclient `--loader`), or exploit handoff |
| DA (Download Agent) | The tool that does the actual flash protocol; OEM-signed normally (DAA) | Bypass via payload; or use leaked/unsigned stock DAs per era |
| SLA / DAA / SBC | Serial-link-auth (SLA), DA-auth (DAA), secure-boot-challenge (SBC) — the post-2021 walls | mtkclient `payload` (generic_patcher_payload) bypasses where chips allow |

### 3.2 mtkclient capability by era

Verified against live README/USAGE docs (bkerler, master):

| Era / SoC class | Door state | What works | What doesn't |
|---|---|---|---|
| Legacy (pre-~2021, MT65xx/67xx/68xx pre-V6) | ALIVE | Full BROM exploit suite: `kamakiri` (xyzz, USB ctrl handler), `amonet` (gcpu), `hashimoto` (cqdma), `linecode`/`heapbait` (chimera/R0rt1z2/Shomy); dumpbrom, brute for unknown BROMs | — |
| **V6 / patched-bootrom era: MT6781, MT6789, MT6855, MT6886, MT6895, MT6983, MT8985** (salvaged fact, verified verbatim in current README) | CONDITIONAL | Bootrom exploits dead — **BROM is patched; you must use `--loader` with a proper loader from `Loaders/V6`**, entering via PRELOADER mode (no buttons held, just connect; some devices deactivate preloader — reactivate with `adb reboot edl`) | No BROM R/W; you are now loader-hunting like the Qualcomm EDL world — same grey-market economics |
| SLA/DAA/SBC-fused newer chips | CONDITIONAL | `python mtk.py payload` (generic_patcher_payload) bypasses SLA/DAA/SBC where the chip permits; then SP Flash Tool on UART | Where fuses hard-require signed DA and no bypass exists → door sealed |
| Newest flagships (Dimensity 9-class recent) | DEAD (OSS lane) for pre-auth R/W | — | See CVE-2025-20435 below — the exploit lane replaced the generic lane |

Capabilities once you're in (all verified verbs): `r`/`w`/`rl`/`rf`/`ro`/`wo`/`e`/
`es` (partition + raw flash R/W, full dumps), `printgpt`, `fs` (mount flash as
filesystem!), `da peek/poke` (memory), **`da rpmb r`** (RPMB read — xflash only; write
broken), **`da generatekeys`** (rpmb1-3 key generation/display), `da efuse` (fuse
reads), `da seccfg unlock/lock` (bootloader unlock bit surgery — DESTRUCTIVE, wipes
metadata/userdata/md_udc first per documented flow), `payload --metamode FASTBOOT`
(boot to meta modes via payload), `stage`/`plstage` stage2 with `keys --mode sej,dxcc`
(key extraction per SoC generation), `crash` (deliberately crash DA to fall back to
BROM), `dumpbrom`/`dumppreloader`, `brute` (unknown-BROM enumeration — feed results
upstream), GUI (`mtk_gui.py`), multi-command scripts (`script`/`multi`), `devices
--filter` DB. Root flow documented tested Android 9–12 (boot/vbmeta dump → Magisk
patch → `da vbmeta 3` → write boot — on birds where BL-unlock is allowed).

**What mtkclient CANNOT do (the honest list):**
- Newest locked chains: V6+ with no obtainable V6 loader, and any SoC whose SLA/DAA/SBC
  is hard-fused with no payload bypass → no pre-auth access at all.
- Keys that never leave RPMB/fuses on devices where RPMB provisioning keys aren't
  extractable: `da rpmb r` is xflash-only; `generatekeys` depends on SoC generation;
  where the Weaver secret lives in RPMB keyed to a fused secret the tool can't derive,
  the offline artifact attack (W2b) starves — the door-map §2g Weaver note, restated as
  silicon reality.
- Nothing about CE keys: mtkclient reads FLASH, FBE still needs the credential chain —
  mtkclient is a feeder, not a decryptor.

### 3.3 CVE-2025-20435 — the 2025 headline door (real coverage)

| Claim | Value | Confidence |
|---|---|---|
| Existence / researcher | Ledger Donjon (hardware security team) — flaw in **MediaTek's secure-boot chain** | HIGH (press-corroborated: Forbes/Yahoo Tech, Quokka, CCN, Gate.com, AndroidHeadlines; plus advisory record) |
| Mechanism | Attacker with **physical access + USB** extracts the **root cryptographic keys protecting Android's encryption before the OS loads**; then offline PIN brute; full decrypt | HIGH (consistent across all outlets) |
| Demo result | CMF Phone 1 (Nothing, **Dimensity 7300**) fully decrypted in **~45s** ("60-second hack" headline family) | MEDIUM-HIGH (press-verified demo, primary technical paper not fetched this wave) |
| Fleet exposure | ~**875M devices / 1 in 4 Android** — press estimate built on MediaTek share + affected-silicon class | MEDIUM (press math; treat as class-size, not chip list) |
| Affected silicon enumeration | Press ties the flaw to **MediaTek SoCs using Trustonic's TEE** (one outlet, beebom, misnumbers it CVE-2026-20435 — press sloppiness; the number is 2025-20435). Exact SoC list NOT enumerated in press | LOW-MEDIUM — the per-chip list is exactly what the armory must assemble from the Donjon writeup/patch tracking |
| Patch state | MediaTek issued fixes to OEMs; distribution through vendors — fixes rolling through **2026** (door map: OEM fixes Jan 2026) | MEDIUM (press-consistent) |
| Why it matters | It converts a BFU credentialed bird into a **key-holder** without ever meeting the keyguard: dump keys pre-boot → offline scrypt on the PIN (W2b table: 6-digit = minutes-hours) → boot normally with recovered PIN → full AFU | Doctrine — the crown-compatible chain |

Lab translation: exploit code is not public retail (nobody sells it); this is a
research-integration lane — track Donjon disclosures, affected-chip list, and patch
levels per bird. The installed base lags YEARS (budget MTK fleet ships 2022-2023 SoCs
today), so the lane stays hot long after patches exist. CONFIDENCE on operational
reproducibility: MEDIUM until primary technical disclosure is ingested.

### 3.4 Operator skill floor (MediaTek lane)

Comfortable with Python/pip, USB drivers (stock MTK port + UsbDk on Windows — verified
install path, or the codefl0w Windows installer), reading GPTs, and knowing which era
the SoC belongs to. BROM-era birds: nearly push-button (hold Vol±, connect). V6-era:
loader hunting + preloader-mode patience. Skill hours to first success: ~2–10 h on a
legacy sacrificial MTK bird; ~20+ h to be useful on V6 models.

---

## 4. SAMSUNG SPECIFIC — TWO SILICON FAMILIES UNDER ONE BRAND

### 4.1 The Exynos vs Snapdragon door split

Same marketing name ≠ same doors (door-map §3 doctrine, silicon index key):

| Variant family | Flash lane | Pre-auth silicon lane | Artifact feed |
|---|---|---|---|
| Snapdragon Samsungs (US models mostly) | Odin AND the Qualcomm 9008 lane structurally | CONDITIONAL: needs Samsung-signed firehose loaders — not in the OSS ecosystem; box vendors claim SD-Samsung lanes (LOW) | Where a loader leaks → full raw dump like any QCOM bird |
| Exynos Samsungs (global, incl. our A21s class) | **Download Mode (Odin) ONLY** | No public EDL/firehose equivalent; no BROM (Exynos boot chain is Samsung's own USB download protocol) | ISP/chip-off raw read (FBE-sealed for CE; DE/persist visible) or post-unlock root — no software pre-auth feed on a locked bird |

### 4.2 Download Mode — gates, entries, and what it gives when locked

| Gate | Mechanism | Locked-bird reality |
|---|---|---|
| Entry | Powered-off combo: Vol-Dn + plug USB (A21s class; Vol-Dn+Vol-Up variants per generation) — the lock LIVES in Android, this lives BELOW it | Entry is free — always reachable, battery permitting |
| VaultKeeper | Boot-side guardian: after `oem unlock` flag set, verifies before permitting flash operations | On a locked/OEM-unlock-forbidden bird, flash of unsigned anything = refused |
| KG / Knox Guard state | ACTIVE / PRENORMAL / COMPLETED state machine; RMM "Prenormal" 7-day online window then COMPLETED (verified door map) | Readable in Download Mode warning screens — free hardware-state recon (§4.10 lineage) |
| OEM unlock toggle | Developer-options bit that must be ON before unlocking; absent/forbidden on carrier builds | If forbidden at Android level, the toggle never appears — Odin can't unlock what the state machine forbids |
| eFuse (Knox) | Trips PERMANENTLY on unlock/tamper — Knox-wrapped data paths die (Secure Folder/vault keys) | One-way door — see §10 ledger; on a data-sacred bird this is the reason unlocking is forbidden as a plan |

What Download Mode gives on a locked bird, honestly: **signed-image flash only** —
stock firmware of the right model, re-partition class operations — plus state readout
(KG/lock status screens). No unsigned boot, no raw partition read, no key material.
Its real 2025 value for the lab: (1) stock reflash/rescue, (2) combination-firmware
chains (per-model grey-market engineering builds signed by Samsung — historically
enabled ADB-from-locked and factory-reset-without-signin classes; modern One UI combos
hardened but still central to Samsung chains — CONDITIONAL per model), (3) the KG-state
readout itself feeding the door-map precondition tables.

### 4.3 The repo bird — A217F / Exynos 850 reality (verified repo evidence)

SM-A217F, Exynos 850, Android 12, BL locked, OEM unlock forbidden, no authorized ADB,
no EDL firehose path, no mtkclient (obviously — not MTK). Panel doctrine already
settled: Odin-only when allowed, and the bird is **data-sacred** (SCOPE GUARD) — no
flash, no unlock attempt, nothing one-way. What silicon CAN lawfully do on THIS bird:
Download Mode entry (pure read: KG/warning screens = state recon, no flash performed),
UART log capture if pads are populated (§5 recon lane), and all the software-plane
corpus work already in motion (`_research/extracted_A217F`). The A21s is the standing
reminder that Exynos-class birds wait for either an owner-present moment (never —
GATE-17.14), a sacrificial twin (then §2–§6 apply fully), or a chain through the glass
plane's stale-firmware surface. Sacrificial Exynos twins of A21s class are cheap
(~$30–60 used, LOW) — the lab's first T2/T3 purchases should include one.

---

## 5. JTAG / UART — THE OLD NERVES, HALF-DEAD

### 5.1 Where JTAG still lives

| Fleet | JTAG state | Notes |
|---|---|---|
| Legacy (pre-~2016) | ALIVE | Full halt/dump pre-boot; TAP accessible via populated pads; Riff/Medusa pinout libraries cover thousands of boards |
| Budget fleet (Transsion/itel/TECNO class, old BSPs) | CONDITIONAL | Boards often leave JTAG un-disabled because nobody bothered; per-board pad hunt ~hours |
| Engineering samples / dev boards | ALIVE | By design — the dev-fleet twins are the research instrument |
| 2019+ flagships | DEAD-to-CONDITIONAL | Production fuses blow JTAG_DISABLE; cores behind TrustZone locked out; pads unpopulated/lasered; per-model heroic work only |

Death causes enumerated: eFuses (JTAG disable burned at manufacture), TrustZone
(secure world cores unreachable even when TAP works), pad removal (unpopulated
footprints, X-rays required to find them), per-SoC lockout after secure-boot.

### 5.2 What JTAG gives where it lives

Halt the CPU before/instead of Android boot → read RAM live (AFU birds: keyring/CE
key material resident — the door-map §2e JTAG row), dump memory regions, single-step
the early boot chain. It is the only classical lane that reads RAM rather than flash —
which is why its death on flagships mattered. Tools: J-Link (~$500, Segger; clones
~$50 LOW), Lauterbach Trace32 (enterprise, $$$), OpenOCD (free, config files per
SoC), Riff Box / Medusa Pro (JTAG+ISP combo boxes, ~$100–300 LOW).

### 5.3 UART — alive as recon, forever

UART is not JTAG: it's a debug console, and budget/legacy boards ship it populated and
verbose. What it leaks: preloader/bootloader logs (partition layout, boot mode
decisions, **lock state hints**, secure-boot checks, dump of early-boot errors), and
on some builds a console with limited command surface. Cost: a $3 USB-TTL adapter +
pinout hunt (2 test pads, per-board). For the rig: UART capture is a §7 pre-flight
RECON step on every sacrificial bird — zero risk, pure readout, feeds the evidence
ledger before any mode-entry is attempted. 2019+ flagships: UART mostly gone or
gated; budget fleet: usually there. CONFIDENCE on "always" claims: per-board, LOW.

---

## 6. CHIP-OFF / ISP — THE UFS TRUTH

### 6.1 The core doctrine (door-map §2e, expanded)

**Chip-off died as a DATA readout and lives as an ARTIFACT readout.** FBE means CE
keys are credential-wrapped and never on flash in the clear; desoldering storage
gives you ciphertext. BUT the lock artifacts that W2b attacks —
`/data/system/spblob/`, `/data/misc/gatekeeper/`, locksettings, persist/misc/EFS
blocks, DE-visible blobs — are FILES ON FLASH, and a raw image contains them. The
silicon rig's chip-off job is not "read the data," it is **"mine the crown's raw
material."**

| Route | eMMC | UFS | Verdict |
|---|---|---|---|
| Desolder + reader | eMMC readers cheap (~$10–40, LOW); BGA153 reball feasible | UFS is a SCSI-like protocol IC with per-device provisioning — needs UFS-capable readers/boxes; LGA/HS-BGA footprints; one-shot removal risk | eMMC: ALIVE for legacy+artifact; UFS: BRUTAL logistics |
| Reball/reflow | Hot-air + stencil, moderate skill | Same plus often underfilled/populated both sides — board-kill risk high | T3-lab work, sacrificial birds only |
| ISP (in-system, chip stays soldered) | Clip/probe TP points on eMMC DAT/CMD/CLK lines while board is powered — Medusa/EasyJTAG/UFI class | TP-based on UFS boards where vendor left points; write-protect handling needed | The 2025 workhorse of the service-rig world |

### 6.2 ISP / box-rig reality

| Tool class | Role | Price (~, LOW) | Rig-bridge reality (§7) |
|---|---|---|---|
| Medusa Pro / Medusa Pro II (Medusa team) | JTAG+eMMC ISP, partition surgery, unbrick | ~$200–400 | GUI-first; scripting limited |
| EasyJTAG Plus (Z3X family) / Octopus | eMMC/UFS ISP, Samsung-heavy support | ~$200–500 + activations | GUI + some CLI |
| UFI Box / UFI II | UFS service king, BBK-heavy, refurbish lanes | ~$100–200 | GUI-first, dongle'd |
| UFSxx-class readers (e.g., UFS-xx/Pro programmers) | direct UFS chip read/write off-board | ~$100–300 | Companion software; CLI sparse |
| Riff Box (legacy) | JTAG-era, historical coverage | ~$100 (aging) | Mostly superseded by Medusa lineage |

What ISP actually fixes/feeds on 2025 birds: restore dead-boot devices (rewrite
boot/preloader/persist), targeted partition ops (persist wipes, FRP-era misc blocks),
and — the crown lane — raw partition dumps feeding W2b when no USB lane exists (the
Exynos-A21s-class case, on a sacrificial twin). Write-protect: eMMC write ops need
WP handling (DAT0/CLK tricks per adapter docs, CONFIDENCE LOW per-board); UFS ISP
lives or dies on the per-board TP map — pinout databases (Medusa/EasyJTAG/forums)
are the armory's second loader-DB-class asset.

### 6.3 Commercial lab reality

Who does chip-off today: forensic outfits on legacy/unencrypted targets and repair
shops for data recovery on dead-but-unencrypted boards. On modern FBE birds the
commercial forensic world sells AFU extraction + exploit chains, NOT chip-off decrypt
(Cellebrite's own marketing reality). Prices: reball/rework ~$50–300/device (LOW),
chip-off forensic service ~$300–1000+ (LOW), success rates on modern-FBE DATA
recovery: near-zero — ARTIFACT recovery: good if the chip survives the lift
(CONFIDENCE LOW, no public rates). The lab should treat chip-off as a LAST resort
after EDL/BROM/ISP-USB lanes fail, and only on sacrificial birds.

---

## 7. THE RIG BRIDGE — HOW THE LLM DRIVES THE SILICON

### 7.1 Architecture

```
 [VESPER CORE]  ---- rig bridge (this section) ---->  [PHYSICAL RIG]
   planner/verifier                                    cables, clips, TP probes,
   evidence ledger                                     boxes, soldering bench
        |                                                       |
        v                                                       v
  adapter layer:  edl.py / mtk.py subprocess   |   QFIL/QPST COM automation
                  GUI-class boxes via OCR+input-injection or vendor CLI
                  USB relay board (button combos robotized, T3 option)
  state machine:  DETECT -> IDENTIFY -> MATCH -> AUTH -> READ -> HASH -> LEDGER
```

| Layer | Implementation | Notes |
|---|---|---|
| **CLI adapters (first-class)** | `edl` (subprocess, `--debugmode` logs parsed), `mtk`/`stage2` (same), `qc_diag` | Both are Python CLIs with structured-enough output; exit codes + log.txt are the LLM's sense data |
| **QFIL/QPST** | QPST COM port + QFIL CLI-ish automation; the edl tool already emulates QFIL XML flows (`edl qfil rawprogram0.xml patch0.xml image_dir`) — prefer edl emulation over GUI | Scriptable without OCR |
| **GUI-class boxes (Medusa/UFI/EasyJTAG)** | Two lanes: (a) vendor scripting/CLI where present, (b) OCR (panel screen readout) + input injection for the rest | OCR+injection is a FALLBACK, never the primary; every GUI step is still hash-verified through the filesystem after the fact |
| **Mode-entry robot (T3 option)** | USB relay board (~$20–40, LOW) wired to power/volume pads or an OTG HID for combos | Battery disconnects, test-point shorts, clip seating stay HUMAN — see 7.3 |
| **Transport** | USB via UsbDk (9008) / stock MTK port + UsbDk (BROM); `--serial`/`--portname` COM fallback; TCP server mode for remote-box bench | Fresh pwsh per command, no state carries — the bridge re-establishes context from the ledger, never memory |

### 7.2 The rig state machine (every session walks this)

| # | State | Actor | Verified how | Failure handling |
|---|---|---|---|---|
| 0 | INTAKE: BFU/AFU, battery %, model, SoC, lock layers (door-map §5 preconditions) | LLM (via ADB/Uart/Download-Mode screens where possible) + operator eyes | dumpsys/trust/Download-Mode readout, USB PID enumeration | If AFU+authorized shell → exit rig, software plane |
| 1 | MODE-ENTRY VERIFY | tool + operator hands (buttons) | USB PID = 0x9008 (QCOM) / MTK BROM VID:PID from config/usb_ids.py / Download Mode screen | 0x900E→9008 recovery drill (edl cable); preloader deactivated → `adb reboot edl` quirk (MTK) |
| 2 | CHIP ID | edl Sahara read (V3 `0x0A` path incl. MSM/OEM/MODEL/PKHASH) / mtk `printgpt`+identity | parsed HW_ID line e.g. `0028c0e10051a012` | no ID → wiring/driver tier check, never loader-guess |
| 3 | LOADER-MATCH | LLM against the loader DB (`msmid_pkhash.bin` scheme; mtk `Loaders/V6`) | loader accepted → firehose/DA alive | no match → ACQUISITION task (armory W4a), session parks, bird unplugged |
| 4 | AUTHENTICATE | loader/toolchain (auth'd EDL walls surface HERE) | tool reports auth stage | auth wall = stop; box-vendor escalation is a human decision (spend $) |
| 5 | RECON READ (non-destructive first) | `printgpt`, `secureboot`/`qfp` fuse reads, `da efuse` | GPT + fuse snapshot into ledger | fuse state contradiction → re-identify, possible mis-model |
| 6 | ARTIFACT READ (evidence-before-flash, §10) | `r persist`, `rl dumps --skip=userdata`, `rf` on sacrificial-only, `footer` | per-partition SHA256 into evidence ledger | read errors → LUN/partition map review, never re-flash as a "fix" pre-read |
| 7 | HASH VERIFY | LLM | re-read spot sectors, compare hashes; log.txt archived | mismatch → re-read; persistent → storage health flag |
| 8 | NEXT / DONE | planner (chain into W2b or a flash op if LAWFUL) | session ends with ledger entry, bird state recorded | every terminal state (incl. aborts) gets an evidence row |

Evidence capture per step (mandatory rows): timestamp, bird serial, USB VID:PID,
tool + version, exact command line, parsed identity fields, partition table hash,
per-artifact SHA256, log.txt path, screen capture (Download-Mode/GUI tiers), operator
name, and a one-way-door delta (§10.5) — before any write, the counters/fuses/KG state
that a write would change.

### 7.3 The human-hands floor — where the LLM stops

The bridge's contract with the bench, stated exactly:

| Task | Owner | Why |
|---|---|---|
| Pad prep, soldering, reballing, clip/TP seating, microscope work | **OPERATOR** | Physical dexterity, thermal judgment — not an API |
| Battery disconnects, button combos (until relay rig exists), cable seating | OPERATOR | Hands; robotized later at T3 |
| All decisions: model ID, loader choice, which partition to read, whether a write is lawful, when to abort | **LLM** | The operating core (charter) |
| Every command invocation that has a CLI | **LLM** via adapter | edl.py / mtk.py / qc_diag / QFIL-emulation are first-class |
| GUI-only steps of box tools | LLM via OCR+injection, operator supervises | Fallback lane; results filesystem-verified after |
| Destructive ops (flash/erase) | LLM decides, **operator countersigns** via the panel | SCOPE GUARD enforcement point — the bridge refuses writes to data-sacred birds outright |
| Donor-board harvesting, hot-air work, board rework | OPERATOR | T3 craft |

The interface sentence: **the LLM owns everything after a verified USB/COM endpoint
exists; the operator owns everything needed to make that endpoint exist.** The relay
board narrows the human's share over time, but solder never becomes an API.

### 7.4 Failure-recovery economics (per sacrificial bird)

Each session has a burn budget: a botched BROM/V6 write or a failed reball can kill a
$30–80 bird (LOW). Doctrine: birds are spent in order of cheapness; every write is
preceded by the artifact dump (§10) so a killed bird has already paid its evidence
rent; donor boards are bought as spares for the top-3 models the lab actually sees.
Abort rules: two consecutive read failures at the same stage → park and escalate to
operator eyes; any fuse-state ambiguity → no write, ever.

---

## 8. ECONOMICS TABLE — THE HONEST MONEY

Lab starting condition: one Windows panel, one Exynos A21s-class bird (data-sacred,
recon-only), sacrificial birds incoming. Costs approximate, CONFIDENCE: LOW unless a
vendor publishes. "Success" = achieving the method's stated yield (boot control /
artifact read / key extraction), NOT "full data" — FBE still gates DATA (see W2b).

| Method | HW ~$ (conf) | Skill hrs to first success | Per-bird time | Success: budget fleet | Success: 2024-25 flagship | DATA survives? | ARTIFACTS readable? | ROI rank (this lab) |
|---|---|---|---|---|---|---|---|---|
| UART recon | $3 TTL adapter | 1–3 | 10–30 min | HIGH | low (gone) | YES | n/a (recon only) | **1** — cheapest intel per dollar, zero risk |
| MTK BROM (mtkclient, legacy SoCs) | $0 + cables | 2–10 | 15–60 min | HIGH | n/a (not MTK) | YES (raw read; CE sealed) | YES — full dump | **2** — the volume lane on incoming budget birds |
| MTK V6 loader route | $0 + loader hunt | 20+ | 30–90 min | MEDIUM (loader-gated) | n/a | YES | YES where loader exists | 4 |
| QC EDL w/ leaked loader | $0–15 | 5–15 | 30–90 min | MEDIUM (per-model loaders) | MEDIUM (auth'd EDL walls) | YES | YES — full raw dump | **3** — covers the QCOM half of the fleet |
| EDL 0x900E recovery drills | $5–15 cable | 2–5 | 15–45 min | MEDIUM | MEDIUM | YES | (enabler) | 5 — unbrick insurance |
| Download Mode (Samsung, signed flash) | $0 | 1–2 | 20–60 min | HIGH (entry) — but signed-only | HIGH (entry) | YES if not wiping | NO (no raw read) | 6 — rescue/state-recon lane |
| Combination firmware (Samsung) | ~$50–150/file (LOW) | 5–10 | 30–60 min | CONDITIONAL per model | CONDITIONAL | NO (wipe on flash) | indirect (ADB surface) | 7 — only when a Samsung chain needs it |
| JTAG (where alive) | $100–500 box | 10–30 | 1–4 h | LOW-MEDIUM (legacy) | very low | YES | RAM keys on AFU legacy | 8 |
| ISP (box rig, chip on board) | $200–500 box | 20–50 | 1–6 h | MEDIUM | MEDIUM | YES | YES — the Exynos-class artifact feed | 9 — T3 purchase, Exynos twins first |
| Chip-off eMMC | $100–400 (reader+rework) | 30–80 | 4–10 h | MEDIUM (legacy) | low | usually (legacy) | YES on legacy | 10 |
| Chip-off UFS | $300–1k+ | 50–100+ | 6–20 h | LOW | LOW | often killed | YES if chip survives | 11 — last resort |
| CVE-2025-20435-class key dump | exploit dev/track | very high | ~45 s once it works | (unpatched MTK class) | (unpatched base for years) | YES | KEYS THEMSELVES | N/A yet — research lane, highest ceiling |
| Commercial boxes (Octoplus/Sigma/UFI) | $100–500 + credits | 10–30 | varies | per their loader moat | per model | YES | YES where they have loaders | optional shortcut — the moat is loaders, which the armory curates anyway |

Reading of the table: the lab's first hundred dollars buy the two lanes that match the
actual incoming fleet (budget MTK + budget QCOM), plus the recon habit (UART) that
makes every later decision smarter. Flagships are a CONDITIONAL story everywhere —
that is the era, not a purchasing error.

---

## 9. ACQUISITION PLAN — THREE TIERS

### T1 — Software-only, ~$0 (start immediately)

| Item | Cost | Unlocks (door-map row) |
|---|---|---|
| edl.py (bkerler/edl, GPLv3) + bkerler/Loaders submodule | $0 | EDL lane on loader-covered birds (§2d) |
| mtkclient (bkerler) + UsbDk + stock MTK driver, or codefl0w installer | $0 | BROM/V6 lanes (§2d/§3) |
| QPST/QFIL suite (Qualcomm, free) | $0 | Official-lane flashes, COM automation |
| Android-PIN-Bruteforce, hashcat/JtR, scrcpy | $0 | HID siege + W2b offline math |
| Samsung USB driver + Odin (free) | $0 | Download Mode recon + signed rescue on lawful birds |
| DDG-HTML discovery discipline (web_search dead in-session) | $0 | Loader/pinout/combo hunting methodology |

Maps to door-map feasibility: glass stale-fleet tricks, ADB-authorized exfil,
EDL/BROM where loaders already leak. Feeds W2b directly.

### T2 — EDL/MTK starter, ~$50–200 (first sacrificial birds)

| Item | ~$ (LOW) | Why |
|---|---|---|
| Cable kit: USB-C/A data-quality, EDL cable (D+/GND short) ×2 | 15–30 | 9008/900E drills (§2.1) |
| USB-TTL adapter (CP2102 class) + dupont/jumper wires | 3–8 | UART recon lane |
| Test-point kit: fine tweezers, kapton, multimeter, magnetic probes | 25–40 | TP shorts, DAT0/CLK tricks |
| OTG HID rubber-ducky-class board (for the glass siege) | 10–25 | door-map HID row |
| One sacrificial MTK bird (Transsion class, legacy SoC) | 30–80 | First BROM reps — the skill floor is paid on this bird |
| One sacrificial QCOM bird with known leaked loader (Xiaomi/OnePlus class) | 30–80 | First EDL reps |

Maps to: §2/§3 full practice, artifact-first dumps feeding W2b, HID siege. This tier is
where the rig state machine (§7) gets its first hundred hours.

### T3 — Full lab, ~$1–5k (the silicon bench proper)

| Item | ~$ (LOW) | Why |
|---|---|---|
| ISP box rig: EasyJTAG Plus or Medusa Pro II + UFI Box | 300–900 | §6 ISP lanes, Samsung/BBK-heavy |
| UFS programmer/reader (UFSxx class) | 100–300 | UFS off-board work |
| Hot-air rework station (Quick 861DW class) + soldering iron + stencils | 250–450 | Reball/reflow, TP prep |
| Stereo microscope (7–45x class) | 150–400 | Pad work |
| JTAG probe (J-Link or clone) + OpenOCD configs | 50–500 | §5 lanes on legacy/dev boards |
| USB logic analyzer (Beagle 480 used, or cheaper clone) | 100–400 | loader SNIFFING → `beagle_to_loader` — the loader-acquisition loop (§2.2) |
| USB relay board rig for mode-entry robotizing | 20–40 | §7.3 — shrink the human's share |
| Donor boards ×3 (top models the lab actually sees) + sacrificial Exynos A21s twin | 90–250 | §4.3 — the Exynos artifact lane finally opens |
| ESD bench kit (mat, wrist strap, flux, wick, solder paste) | 50–100 | craft floor |

Maps to: ISP/chip-off artifact feeds on birds no USB lane covers (the Exynos case),
boot-dead rescues, and loader self-manufacture from sniffed box sessions — the lane
that makes the lab independent of loader grey-markets.

**Airgap note (panel DNS-dead episodes):** every install above rides into the lab on
operator-supplied USB media — hashes recorded in the ledger, installers run offline,
driver packs (UsbDk, QPST, MTK port) staged in the armory before sessions. The rig
bridge NEVER fetches during a session; loader/pinout/combo acquisitions happen as
separate armory (W4a) tasks on operator-uplink episodes only. A DNS-dead panel is
expected, not exceptional.

---

## 10. SILICON-PLANE LAWS

1. **SILICON-1 SCOPE GUARD (from charter, non-negotiable):** flash/erase/reball/
   any destructive op happens on **sacrificial birds only**. LO's personal bird
   (A217F) is data-sacred: recon reads (Download Mode screens, UART logs, USB PID
   enumeration) permitted; nothing one-way, ever. The rig bridge enforces this as a
   hardware-level bird registry — data-sacred serials are write-blocked at the adapter.
2. **SILICON-2 BATTERY FLOOR:** no Download Mode / EDL / BROM write session begins
   below **30% battery** (or bench power). A mid-write power drop is the classic
   self-inflicted brick; EDL/BROM reads can proceed lower, writes never.
3. **SILICON-3 EVIDENCE-BEFORE-FLASH:** before ANY write that could destroy or
   mutate them, dump the artifacts (persist, misc, EFS, gatekeeper-adjacent blocks,
   GPT, fuses) and hash them into the ledger. A bird may die AFTER paying evidence
   rent; never before.
4. **SILICON-4 ARTIFACT-FIRST DOCTRINE:** the goal of every silicon session is
   artifact/keys capture feeding W2b — not "unlocking the screen." Boot control is a
   means (access to storage, custom boot for instrumentation); the finisher is the
   offline credential attack or pre-boot key extraction.
5. **SILICON-5 ONE-WAY-DOOR LEDGER:** every flash, erase, seccfg flip, KG-state
   change, unlock token, combo flash, and eFuse trip is recorded BEFORE crossing
   (what counters/fuses/KG state exist now) and after (what changed). Knox fuses and
   KG transitions do not un-trip. If it cannot be undone, it must have been logged
   first, on a sacrificial bird, with operator countersign.
6. **SILICON-6 CHAIN OF CUSTODY:** every session ends with a complete evidence row
   per §7.2 — including aborts and failures. A failed session that is logged is
   lab capital; an unlogged success is not admissible to the map.
7. **SILICON-7 HUMAN-HANDS FLOOR:** solder, rework, clip seating, and (pre-relay)
   button work are operator-owned; the LLM owns all decisions and all CLI execution
   after a verified endpoint exists. Destructive writes carry operator
   countersignature via the panel.
8. **SILICON-8 LEAVE-BETTER RULE:** no bird leaves the bench in a worse state than
   it arrived unless it is registered sacrificial AND its evidence rent is paid
   (SILICON-3) AND the ledger says so.

---

## SILICON VERDICT

What silicon realistically adds in 2025, stated without romance:

1. **Silicon is the only remaining plane for a BFU, credentialed, patched bird** —
   and even then only via two shapes: raw artifact readout (EDL/BROM/ISP dump → W2b
   offline credential attack) or pre-boot key extraction (CVE-2025-20435 class →
   offline PIN brute → full decrypt). There is no third shape; there is no solder
   iron that decrypts FBE.
2. **The silicon economy inverted.** The classical currency was microsoldering skill;
   the 2025 currency is **loader and exploit availability per exact model**. edl.py
   and mtkclient are free; loaders leak or they don't; BROMs are patched or they
   aren't. The lab's moat is the loader/pinout/loader-sniffing armory, not tools.
3. **The lanes that matter for the incoming fleet (budget, MTK-heavy, stale patches)
   are nearly free** — BROM exploits on pre-2021 SoCs, V6 loaders where obtainable,
   leaked QC firehoses, $15 of cables. JTAG is legacy archaeology; chip-off is a
   last-resort artifact miner; ISP is the Samsung/BBK service-bench workhorse.
4. **CVE-2025-20435 is the proof of concept for the crown law's silicon endgame**:
   keys out before the OS ever runs, credential computed offline, phone opened
   normally — no keyguard ever engaged, no wipe, no fuse tripped. Its unpatched
   installed base (years of budget-MTK shipping) makes it the highest-ceiling lane
   of the era. CONFIDENCE on class mechanics: HIGH; on our operational reproduction:
   MEDIUM until the primary disclosure is ingested and trialed on a sacrificial bird.
5. **What silicon cannot do, ever, by design:** it cannot read CE data without the
   credential chain (FBE), it cannot untrip a Knox fuse, it cannot beat an auth'd
   EDL wall without the right signed loader, it cannot make a 12-char random
   PIN tractable (W2b's math is the ceiling), and it cannot help a bird whose keys
   live in RPMB/fuses that no exploit reaches. Silicon feeds the finisher; it is not
   the finisher. The universal system's boot order stands: **state triage first,
   software planes second, silicon third, offline math last — and the ledger
   watching every one-way door the whole way down.**

---

## SOURCES — THIS WAVE

- mtkclient (bkerler) README + README-USAGE, master — fetched this wave: V6 chip list
  (MT6781/6789/6855/6886/6895/6983/8985) + preloader-mode requirement; exploit credits
  (kamakiri/xyzz; amonet; hashimoto; linecode/heapbait/chimera/R0rt1z2/Shomy); payload
  SLA/DAA/SBC bypass; stage2 sej/dxcc keys; rpmb read (xflash) / write broken;
  generatekeys; seccfg; efuse; crash; brute; GUI/script/multi; Windows UsbDk path;
  codefl0w installer; LiveDVD V6. https://github.com/bkerler/mtkclient
- edl (bkerler) README, master — fetched this wave: GPLv3 + non-commercial clause;
  Sahara V3 CHIP_ID_V3_READ (0x0A) autodetect fix; loader DB scheme (msmid_pkhash),
  fhloaderparse, beagle_to_loader sniffing loop; 9008/0x900E; EDL cable; DAT0/CLK/
  boot-resistor recovery drills; peek/poke/qfp/secureboot/pbl (EL3); modules
  oemunlock; qfil emulation; qc_diag; tested-device list. https://github.com/bkerler/edl
- CVE-2025-20435 press family (fetched/DDG-corroborated this wave): Forbes/Yahoo Tech
  (daveywinder) "875M / 60-second" coverage; Quokka; CCN; Gate.com; AndroidHeadlines
  (CMF Phone 1, ~45s); beebom (Trustonic-TEE attribution; note their CVE misnumber).
  Primary Donjon technical disclosure NOT yet fetched — flagged MEDIUM/LOW above.
- Door map 01_universal_door_map.md §2d/§2e/§2g/§3 (this repo) — taxonomy, FBE-CE
  trap, Weaver/RPMB wall, vendor tables, the A21s Exynos reality.
- 00_CHARTER.md — crown laws, SCOPE GUARD, wave plan (W2a → this file; W2b next).
- Repo evidence: `_research/extracted_A217F` corpus — the lab bird's standing state.

*Wave W2a complete. Next per plan: W2b artifact attack (GateKeeper/Weaver/SP blobs,
cracker landscape, GPU economics) — this file is its feeder doctrine.*
