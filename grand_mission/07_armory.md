# THE ARMORY — W4a
*Grand Mission 07 · DroidCommand / Vesper · the complete tool-acquisition, pinning,
provisioning and library doctrine that makes self-arming SAFE and UNIVERSAL. Builds on
00_CHARTER.md (laws), 01_universal_door_map.md (planes/feasibility/tools named),
03_silicon_plane.md (T1/T2/T3 tiers, loader economics, §2.2 sniffing loop), 05_vendor_chains.md
(combo firmware, unlock bureaucracy), 06_ios_front.md (libimobiledevice bridge, DFU robot).*

Laws carried: GATE-17.14 (THE CROWN), GATE-17.15 (THE INTERIOR), GATE-17.13 (credential =
state), SCOPE GUARD (data-sacred birds), **GATE-17.8 (SELF-ARMING — the cortex installs
tools without asking; this wave is its safety contract)**, **GATE-18.1 (UNTRUSTED CONTENT —
the cortex processes attacker-influenceable input; the armory is its enforcement point)**.
Vocabulary inherited: ALIVE/CONDITIONAL/DEAD; planes glass→software→flash→silicon→cloud;
danger classes D0 read · D1 reversible · D2 destructive · D3 one-way · D4 brick-risk.
Confidence tags: **HIGH** (multi-source/primary), **MEDIUM** (single good source),
**LOW** (folklore/price guess). Prices `~$` LOW unless vendor-publishes. Verification base:
prior waves' live fetches (edl/mtkclient READMEs, Knox docs, libimobiledevice.org, checkra1n/
palera1n repos, samfw/XDA corpus) — web_search dead in-session, DDG-HTML discipline assumed.

---

## 1. THE ARMORY THESIS — WHY SELF-ARMING WITHOUT AN ARMORY IS A LIABILITY

The charter gave the cortex GATE-17.8: it installs what it needs, without asking. That law
is what makes the system universal — a cortex that waits for the operator to hand it every
binary is a cortex that stops at the edge of its installer. But the same law, unwritten
further, is the panel's largest attack surface. The sentence that motivates this entire
wave:

**An LLM that will run anything it downloads is an LLM that can be fed anything — and
the panel is the machine doing the feeding.**

Connect this to GATE-18.1 (untrusted content): the cortex already reasons daily over
attacker-influenceable input — lockscreen states, web-scraped pinout forums, combo-firmware
filenames, loader DBs assembled from grey channels. 18.1 exists because content is a
weapon-delivery lane. Now observe that GATE-17.8 arms that lane: the cortex's response to
"tool missing" is to FETCH. A poisoned loader filename in a forum corpus, a typosquatted
GitHub repo, a combo file that is 60% real firmware and 40% dropper — each of these targets
the moment of acquisition. The intersection of 17.8 and 18.1 is where the armory lives:
**the armory is the enforcement point that converts "what runs is what was verified" from
doctrine to machinery.**

The threat model, stated concretely (all lanes observed in the wild, CONFIDENCE: MEDIUM on
prevalence, HIGH on mechanism):

| Attack lane | Vector | Why a naive self-armer falls |
|---|---|---|
| Typosquat repos | `bkerler/edl` vs `bkerIer/edl`, `mtkcIient` | Cortex fetching by name from search results at 3am |
| Poisoned loader packs | Firehose .mbn with appended payload; "loader packs" are the grey market's favorite dropper wrapper | Loaders are EXPECTED to be weird binaries — perfect camouflage |
| Combo firmware trojans | Grey-market Samsung combos are the #1 malware vector in this tool class (see §4b) | Combos come from unofficial sources BY DESIGN |
| Installer bundling | "Free Odin download" sites ship with adware/extras; fake QPST mirrors | The tool name is public knowledge, the canonical URL is not |
| pip dependency confusion | Upstream package name not claimed on PyPI → attacker claims it | `pip install` in a hurry with no pin |
| Update hijack | Tool phones home to a dead/moved domain; someone re-registers it | An armory that auto-updates is a standing offer |
| Driver-pack malware | Third-party "MTK driver pack" zips | Driver hunting is exactly when the operator is desperate |

**The manifest-first law:** no binary, script, driver, loader, firmware image, or
dependency enters execution scope on the panel unless a manifest row for it already exists
— name, version, hash, source, license, danger-plane — written and verified BEFORE the
fetch. The manifest is not paperwork after the fact; it is the gate. Self-arming survives
contact with 18.1 only because the arming step and the trusting step are separated by a
verification the cortex cannot skip. Everything below is the machinery of that sentence.

---

## 2. THE MANIFEST — THE ARMORY'S CORE OBJECT

### 2.1 Schema (armory.json, versioned, hash-chained per revision)

```json
{
  "manifest_version": "2",
  "row": {
    "name": "mtkclient",                     // canonical tool name (lowercase, no spaces)
    "version": "1.6.1",                       // EXACT version — pins forbid "latest"
    "sha256": "<64-hex>",                     // of the acquired artifact (archive or wheel)
    "sha256_inner": ["<...>"],                // per-file hashes after unpack (entry-points)
    "source_url": "https://github.com/bkerler/mtkclient/archive/refs/tags/1.6.1.zip",
    "source_type": "git-tag",                 // git-tag | winget | pip | usb-drop | url | box-sniff
    "license": "MIT-class (verify per repo)", // GPLv3 noted for edl (non-commercial clause)
    "danger_plane": "silicon",                // glass|software|flash|silicon|offline|cloud|panel
    "danger_class": "D0-D4",                  // what the TOOL itself can do, worst case
    "panel_exec": true,                       // does this EVER execute on the panel itself?
    "entry_points": ["mtk", "stage2", "mtk_gui"],  // verified-present executables
    "install_method": "venv+pip pinned",      // see §3 channel doctrine
    "dependencies_pinned": {"pyusb": "1.2.1", "pyserial": "3.5"},
    "verified_date": "2026-01-15",
    "verified_by": "armory-task-0142",
    "provenance": "bkerler upstream tag, DDG->GitHub direct",
    "airgap_staged": true,                    // present on the offline panel copy
    "notes": "V6 loader route; preloader-mode entry; see 03_silicon_plane.md §3"
  }
}
```

Fields that carry the law: `sha256` (the refusal key), `panel_exec` (the 18.1 key — false
means the artifact may only ever touch a flash TARGET, never the panel), `version` (the
anti-drift key), `provenance` (the ledger key). A row with a missing or placeholder sha256
is a row that does not exist — the API treats it as ACQUISITION-NEEDED, not as available.

### 2.2 The install flow (every acquisition, no exceptions)

| # | Stage | What happens | Failure handling |
|---|---|---|---|
| 0 | MANIFEST ROW FIRST | A row with real sha256 is authored/updated — BEFORE any fetch. Hash comes from upstream release page or a second independent mirror; for USB drops it comes with the drop (see §3e) | No hash obtainable → no acquisition, park it |
| 1 | FETCH or USB-DROP | Channel-native download (git tag archive, winget, pip, https, or operator media) into `armory/intake/` — NEVER into PATH, never into a run location | TLS fail/mirror mismatch → try second mirror; still fail → park |
| 2 | HASH VERIFY | SHA-256 of the artifact vs the row; for archives, unpack to a temp and verify `sha256_inner` for every entry_point | MISMATCH = quarantine + provenance investigation; the artifact NEVER proceeds |
| 3 | QUARANTINE UNPACK | Unpack/install into `armory/quarantine/<name>-<version>/` — a directory with no execute privileges for the panel user until stage 5; pip installs into a dedicated venv, not system python | Unpack bombs (zip-slip paths, symlinks escaping) → reject row entirely |
| 4 | ENTRY-POINT PROBE | Non-executing probes only: file exists, is the right PE/ELF/script class, magic bytes sane, declared deps resolvable, `--help` in a sandboxed throwaway context where the tool class permits | Probe crashes machine → quarantine holds; no retry loop |
| 5 | REGISTRY ENTRY | Promote from quarantine to `armory/tools/<name>/<version>/` (versioned dir — multiple versions coexist); write the registry row linking manifest ↔ install path ↔ entry_points; stamp `verified_date` | — |
| 6 | LEDGER ROW | Provenance row: who/what fetched, from where, when, why (the requesting task/mission id), hash, verdict | — |

The refusal law, in its full form: **NO unsigned or unverified binary ever executes on the
panel.** Not "probably fine" — hash-verified or it does not run. This is the gate that
makes GATE-18.1 real rather than aspirational: 18.1 says treat content as hostile; the
armory is the mechanism that decides, before execution, whether content is the content we
chose. The probe stage exists because a correct hash on a hostile upstream is still a
hostile binary — pinning verifies identity, not intent; `panel_exec=false` and quarantine
probes limit what intent can do to us. (CONFIDENCE: HIGH that this is the standard
supply-chain control shape; MEDIUM that our probe stage catches novel malice — it is a
floor, not a ceiling.)

---

## 3. ACQUISITION CHANNELS — PER-CHANNEL DOCTRINE

### 3a. winget (Windows packages)
Good for: panel-side utilities that need to EXIST on Windows and are Microsoft-catalogued —
7zip, Python runtime, VS Code-class editors, notepad++ for manifest editing, git itself,
vim-class tools. Integrity chain: winget manifests carry their own sha256 + signature
checks against the package catalog; the armory re-verifies the installed binary's hash and
writes it into OUR manifest anyway (trust winget for delivery; trust our row for identity).
Failure modes: catalog version drift (winget hands you 1.7 when the row says 1.6.1 → the
armory pins `winget install --version`), MSIX signature weirdness on offline panels
(some packages want a store check → prefer portable/zips from winget where offered,
CONFIDENCE: MEDIUM on which packages misbehave offline), and the classic: winget NOT
installed / broken on a DNS-dead panel — winget needs its source list updated or it sulks.
Airgap note: winget downloads happen only during uplink windows; on the airgapped panel,
install from the cached `.nupkg`/installer in `armory/intake` via hash-verified local
install (the channel is the fetch lane, not the install lane — installs are always local).

### 3b. pip (Python)
Good for: the actual weapon class — mtkclient, edl, frida-tools, hashcat wrappers,
capstone/keystone for research, pwntools-class chains. The sub-dependency pinning problem:
pip resolves dependency trees at install time; an unpinned `pip install mtkclient` is a
lottery ticket over transitive deps (pyusb, pycryptodome, colorama, fusepy…). Doctrine:
(a) every pip install goes into a dedicated armory venv (NEVER system python — the panel's
python is infrastructure, not a workshop), (b) `pip install --require-hashes` with a fully
locked requirements file generated at first verified install (`pip freeze` + hash export),
(c) the locked file is itself a manifest artifact — hash-chained into the row. Failure
modes: dependency confusion (mitigated by hashes + exact pins), yanked releases (pin by
exact version, never >=), and build-from-source wheels needing compilers (prefer wheels;
note them in `install_method`). CONFIDENCE: HIGH — this is standard `--require-hashes`
practice, not invention.

### 3c. git clone (repos)
Good for: the research toolchain that lives on GitHub and moves fast — bkerler/edl,
bkerler/mtkclient, bkerler/Loaders (submodule!), axi0mX/ipwndfu, palera1n, kitsuned/PotatoNV,
corsicanu/BlackMesa123 KG-RMM bypass zips, amoamare Legacy-Samsung-Reactivation-Lock-Removal,
lokey0905/Xiaomi-Bootloader-Unlock-Request-Helper, blackshibe/android-fbe-decrypt,
urbanadventurer/Android-PIN-Bruteforce, tools_clone/LockKnife already in repo. The pinning
doctrine: clone by TAG or COMMIT, not branch — record the commit sha256-adjacent (git
object hash) in the row, then hash the produced tree (`git archive` → tar → sha256) so the
row pins the CONTENT not just the pointer. The sub-dependency problem compounds here:
repos carry submodules (edl→Loaders — the loader stash IS a submodule) and requirements
files; each submodule gets its own row (loaders are a LIBRARY, §4a, with their own
per-loader hashes). Failure modes: repo moves/deleted (pin = we keep our own copy; the
armory is the archive of record), force-pushed history (tag pins dodge it), typosquats
(§1 — mitigated by provenance notes naming the canonical account), and the license reality:
edl is GPLv3 WITH the maintainer's no-commercial-use-without-permit clause (verified
README, 03_silicon_plane.md §2.4) — the row records it; the lab is non-commercial
forensics on owned/sacrificial birds, and the row is where that reasoning lives.

### 3d. Direct download (URLs)
Good for: vendor-published tooling with stable official URLs — QPST/QFIL (Qualcomm
package), Samsung USB driver, Odin (3.13/3.14 class zips — NOTE: Odin has no official
site; it lives on XDA threads and mirrors — CONFIDENCE: MEDIUM on any specific mirror
being clean; treat every Odin zip as grey-market-grade: hash from the XDA post + second
mirror cross-check + `panel_exec` true but network-isolated execution), UsbDk, Apple
Mobile Device Support (inside iTunes/AppleDevices installers — the DLLs are what usbmuxd
wants), Frija/SamFw-class firmware tools. TLS+hash discipline: fetch over https only,
verify sha256 from a SECOND source than the download page (the page that serves the binary
is the attacker-controllable one), refuse redirects to unknown hosts, record the final
resolved URL in provenance. Failure modes: link-rot (expected — the armory's cached
artifact is the recovery), silent version swaps at the same URL (hash catches it; this is
why rows pin content), and fake "official" download portals for tools with no official
home (Odin, MSM packs — those are grey channels, see §4b discipline).

### 3e. USB drop (operator-supplied media — the airgap lane)
Good for: EVERYTHING on a DNS-dead panel. The rig bridge never fetches during a session
(03_silicon_plane.md §9 airgap note); the panel itself may be uplink-less for weeks.
Protocol — the signed manifest handoff: (1) the operator runs acquisitions on an
internet-facing machine (or brings files from wherever the internet lives this week);
(2) the drop is a directory `drop-YYYYMMDD/` containing artifacts PLUS
`drop-manifest.json`: per-file {name, sha256, size, source_url, fetched_date, fetcher},
signed/hashed against a pre-shared rolling key or simply verified by the panel against
rows already present in the armory (the panel KNOWS what it asked for — the pending
acquisition queue IS the expected-contents list); (3) the panel processes drops through
the SAME stage 2–6 flow as network fetches — hash verify, quarantine, probe, registry,
ledger — a USB drop is not a trust bypass, it is a transport. Failure modes: operator
fetches the wrong thing (the pending-queue cross-check catches it), stale drops (version
drift — see §8 reconciliation), media-borne malware (the drop directory is scanned with
 Defender BEFORE unpack — exclusions in §7 do NOT cover the intake lane; CONFIDENCE:
MEDIUM that Defender scanning of intake is fully reliable, LOW that anything is — it is a
speed bump on a road already gated by hashes).

### 3f. Hardware deliveries (boxes/adapters/birds — physical)
Good for: the T2/T3 purchases (03_silicon_plane.md §9) and birds themselves. The integrity
chain here is NOT cryptographic — it is the LEDGER (§6): purchase record, seller, price,
arrival date, serials photographed, first-power-up state captured before any use.
Failure modes: refurb-sold-as-new boxes (Medusa/UFI clones and dongle forgery are real in
this market — CONFIDENCE: MEDIUM, community-reported), grey-imported birds with unknown
history (the intake row records arrival state = BFU/AFU per door-map §5), and hardware
that arrives already flashed with something weird (first boot on an ISOLATED bench, never
on the panel's USB, until the intake row exists — the same quarantine instinct, physical
edition).

---

## 4. THE TOOL LIBRARIES — THE FOUR COLLECTIONS

The manifest holds tools; the LIBRARIES hold the per-model knowledge assets that make
tools useful. Four collections, each with schema, growth loop, and quality control.

### 4a. THE LOADER LIBRARY (firehose + BROM/V6 programmers)
The single most valuable asset class the lab owns (03_silicon_plane.md verdict: "the lab's
moat is the loader/pinout armory, not tools"). Contents: (1) Qualcomm firehose loaders
(FHPRG/MBN/ELF `prog_emmc_firehose_*.mbn`), named per the edl autodetect scheme:
`msmid_pkhash[8-bytes].bin` — Sahara V1/V2 match MSM_ID+OEM_ID+MODEL_ID+PK_HASH; V3
devices need the `cmd=0x0A` CHIP_ID_V3_READ reconstruction path (verified edl README);
(2) MediaTek V6-era loaders (`Loaders/V6` per mtkclient README — required for MT6781,
MT6789, MT6855, MT6886, MT6895, MT6983, MT8985, the patched-BROM class) entered via
PRELOADER mode; (3) generic DAs for the pre-V6 BROM fleet where mtkclient exploits make
loaders unnecessary (kamakiri/amonet/hashimoto/linecode/heapbait lineage).
Seed: the bkerler/Loaders submodule (public stash, ragged per-model coverage — HIGH).
Growth loop — three lanes: (i) grey-market per-model packs (same discipline as combos,
below); (ii) **the Beagle-sniffing self-manufacture loop** (W2a §2.2, the independence
lane): a Total Phase Beagle 480 USB analyzer captures a working box-tool EDL session →
`beagle_to_loader` reconstructs the loader from the wire → the lab NEVER depends on a
grey seller for any loader it has once seen on a bench (this is the loop that converts a
$300 box purchase into a permanent manifest asset — CONFIDENCE: HIGH, the tooling is in
the edl repo); (iii) `fhloaderparse` ingests any loader collection into the autodetect DB
(HIGH, README-verified). Quality control: every loader row carries per-loader sha256,
the exact device identity it matched (msmid+pkhash string), the session it first worked
in (evidence ledger link), and a worked/failed verdict history — a loader that "matches"
but 404s in Sahara gets demoted, not deleted. Loader rows are NEVER panel_exec (they
execute on the PHONE's SoC, not the panel — but note the §1 poisoned-loader lane: hash
verification still applies because the panel TRANSMITS them).

### 4b. THE COMBO/ENGINEERING FIRMWARE LIBRARY (Samsung combination builds)
Reality first: combos are signed-by-Samsung engineering builds that historically expose
service surfaces (ADB-from-locked era, FRP-bypass surfaces, DRK repair, OEM-unlock
visibility, downgrade testing — 05_vendor_chains.md §1.5). Sourcing reality: freely listed
for many models on samfw.com-class firmware sites (free); curated/newest-Android combos
are grey-seller territory at ~$50–150 (LOW on prices); combos for the LATEST One UI
levels are genuinely hard to find (XDA-verified); modern combos are hardened (ADB in
combos restricted). Per-model availability is the whole game: model + CSC + Android/One-UI
version must MATCH the target or the flash is worthless-to-harmful. Hash discipline —
this is the #1 malware vector of this entire tool class (grey-market files, wrapper
sites, expired-mirror redirects): every combo row gets sha256 from the listing/second
mirror cross-check, the file is scanned (intake lane, not the exclusion lane), and — the
law that follows — **combo firmware NEVER executes on the panel** (`panel_exec=false`,
hard): combos are FLASH TARGETS only, and they flash only after model/CSC/version match
verification and only on sacrificial/refurb birds (D2 wipe-on-flash, 05 §1.5). Growth
loop: samfw-class listings sweep during uplink windows; XDA per-model threads; the
acquisition queue is driven by the top-N Samsung models the lab actually sees (§6 scope
integration). QC: a combo row without a verified target-model match is a stub, not an
asset; worked-once combos get evidence-ledger links like loaders.

### 4c. THE PINOUT LIBRARY (JTAG/ISP/UART test-point maps per board)
The second loader-DB-class asset (03 §6.2: "pinout databases are the armory's second
core asset"). Sources: Medusa Pro / EasyJTAG / Riff legacy pinout databases (thousands of
boards, box-vendor maintained — buying the box buys the DB access), forum corpora
(GSM-legend forums, lay-by repair threads), and the lab's own UART-pad finds ($3 CP2102
USB-TTL + two test pads per board, 03 §5.3). Schema — per-board JSON:
{board_id, device_model_variant (SM-A217F ≠ A21 US — SoC-first indexing per 01 §3),
connector_or_pads: {jtag: {tck,tdi,tdo,tms,trst,rtck: pad coords/photo}, uart: {tx,rx,gnd},
isp: {clk,cmd,dat0..7, vcc/vccq, wp}}, voltage, entry_procedure, source_refs [],
provenance_tag, confidence_tag, worked_sessions []}. Community-provenance confidence
tags: C-CERT (box-vendor DB / official schematic), C-COMM (multi-thread forum concordance),
C-SINGLE (one forum post — treat as unverified hypothesis), C-LAB (our own probe find —
highest trust, evidence-linked). Growth loop: every bench session that finds a pinout
writes it; forum sweeps during uplink windows harvest per-model; buying a box (T3)
unlocks its whole DB. QC: a pinout row without a confidence tag does not exist; C-SINGLE
rows require operator-hands verification before any destructive use (SILICON-7 lineage).

### 4d. THE EXPLOIT/PAYLOAD LIBRARY (checkm8-class, CVE research chains)
Contents: (1) bootrom-era permanent exploits — checkm8 (CVE-2019-8900, axi0mX ipwndfu,
A5–A11+T2, unpatchable for fleet life — 06_ios_front.md §4) with its toolchain descendents
(checkra1n, palera1n); (2) CVE research chains with versioned disclosure tracking: the
Pixel ABL family (CVE-2024-22012 USB function-pointer overwrite, patched 2024-02;
CVE-2025-36907 post-unlock heap overflow — fuzz-target class, not a locked-bird lane,
corrected in 05 §5), the MediaTek secure-boot chain (CVE-2025-20435, Donjon: pre-boot key
extraction via USB, ~45s full decrypt demo on CMF Phone 1 / Dimensity 7300, fixes rolling
through 2026, primary technical disclosure still to ingest — MEDIUM per 03 §3.3), the
fuzzy_fastboot/FuzzUSB lineage as the fuzzing harness class; (3) payload primitives —
mtkclient's generic_patcher_payload (SLA/DAA/SBC bypass), stage2 sej/dxcc key extraction
(03 §3.2). Schema: per-exploit {cve_or_name, class (bootrom/TEE/kernel/fastboot),
affected_matrix: {chip, patch_floor, patch_deadline}, public_code_state (repo/none/paper),
repro_provenance, dependency rows (ipwndfu needs libusb etc.), danger_class, crown_compatible
verdict, LAST-VERIFIED date}. Versioned disclosure tracking is the growth loop's core: the
library MAINTAINS the patch-coverage matrix (which chip+patch-level combos are still
open) — this is what converts "an exploit existed once" into "this arriving bird is
vulnerable NOW"; the installed base lags patch distribution by YEARS (03 §3.3: budget-MTK
ships 2022-23 SoCs today), so disclosure-tracking is the library's compounding asset.
QC: exploit rows without an affected-matrix are folklore; rows carry CONFIDENCE tags and
the disclosure-status flag (paper-only vs public-code vs lab-reproduced).

---

## 5. THE FIRMWARE FETCHER — STOCK ROM ACQUISITION DOCTRINE

The lawful baseline layer: the system must be able to obtain STOCK firmware for rescue
flashes, downgrade chains (B2: downgrade → re-open old bugs), AVB-verification baselines,
and dev-bird regression loops — all without ever touching grey channels for stock images.

| Vendor | Official lane | Tooling / method | Verdict |
|---|---|---|---|
| Samsung | FUS/Odin servers via Frija / SamFw class downloaders (firmware is free; the tools authenticate to Samsung's firmware server per-model) | Frija (model+CSC input → encrypted package), SamFw.fr; the armory wraps whatever current tool works — these tools die and get replaced often (CONFIDENCE: MEDIUM on any specific tool's 2026 health) | ALIVE; per-model+CSC exactness required |
| Xiaomi | mi.com official archive — fastboot ROMs (`.tgz` with images) and recovery ROMs (`.zip`), published per-device with version history | URL patterns are community-documented; hash verification from the listing page + a second mirror | ALIVE; the friendliest official archive of the majors (HIGH) |
| Google | developers.google.com factory images — per-device, per-build, WITH sha256 checksums published | direct URL fetch; Google publishes the hash — the integrity chain is first-party | ALIVE; the GOLD STANDARD the armory points to (HIGH) |
| Transsion | scattered: Carlcare service centers, per-model firmware threads, no unified portal; TSM-Tool ecosystem carries some | armory sweep via DDG-HTML during uplink; per-model rows with community hashes | CONDITIONAL; the softest fleet is the least-archived (MEDIUM) |
| Apple | Apple IPSW签名 servers — ipsw.me / theiphonewiki list per-device latest-signed URLs; Apple signs only the CURRENT window | `idevicerestore` (libimobiledevice suite) fetches/uses IPSWs; official URLs are first-party | ALIVE (HIGH); the panel's Apple flash lane |
| BBK | MSM Download Tool packs carry their own firmware; official per-model archives largely don't exist for global units | grey-market lane for packs — §4b discipline applies; Deep-Testing-key birds don't need it | CONDITIONAL (MEDIUM) |
| Huawei | post-2018: no public firmware lane of note | downgrade zips float in forums; LOW confidence fleet-wide | DEAD-ish (LOW) |

Firmware verification BEFORE flash — the law: every stock image is verified before it
touches a bird. (a) archive sha256 vs the manifest row (fetcher writes it at download
time); (b) AVB checks — for Android 8+/AVB2.0 devices, the panel runs `avbtool
verify_image` (or the edl/mtk-side equivalent checks) against vbmeta before flash;
an image failing AVB in pre-flash verify is a CORRUPTED or TAMPERED artifact, and the
flash aborts (this also catches truncated downloads — the most common silent failure);
(c) per-file hashes inside fastboot/MSM packages where the OEM ships them (Google does;
others mostly don't — LOW-MEDIUM). Model-to-firmware mapping discipline: the armory keeps
a mapping table row per MODEL VARIANT (SM-A217F ≠ SM-A217M — SoC-first indexing, 01 §3
doctrine, the A21s Exynos/SD split is the standing example), holding: variant → CSC →
latest stock → known-good downgrade floors (what still boots) → combo availability pointer
(§4b) → loader pointer (§4a) → pinout pointer (§4c). A flash plan that can't name its
mapping row is not a plan. Offline caching strategy: the panel keeps a firmware cache
`armory/firmware/<vendor>/<model>/<version>/` holding (1) the LATEST stock for every
data-sacred bird in the registry (rescue insurance — a data-sacred bird's firmware is the
only thing we may ever flash it, and only with operator countersign), (2) the latest
stock for the top-N incoming sacrificial models, (3) at least one known-good downgrade
floor per supported Samsung/QCOM model (the B2 chain's ammunition). The cache is the
airgapped panel's flash ammunition — an uplink window's sync job (§8) refreshes it in
priority order: data-sacred first, top-N models second, research floors third.

---

## 6. THE HARDWARE INVENTORY LEDGER

Every physical asset gets a ledger row — the physical twin of the manifest. File:
`armory/hardware_ledger.json`. Schema per asset:
{hw_id (HW-### sequential), class (box | cable | adapter | relay | tool | bird | board |
bench-kit), model, serial/photo-ref, purchase_date, seller+price (provenance — §3f),
current_state: in-service | spare | sacrificial | donor | dead, location (bench-drawer
coordinates — honest: labs lose hardware), notes}. Birds get the extended row: arrival
state (BFU/AFU per door-map §5 — THE first triage fact), SoC family, BL state, KG/account
state where readable, evidence-ledger link (SILICON-6), and — the load-bearing field —
**data_sacred: true/false**, the registry-level write-block.

The scope-guard integration (SILICON-1, 03 §10): the bird registry IS the enforcement
list — the rig bridge adapters (edl/mtk subprocess wrappers) consult it before every write
class operation; a data-sacred serial is write-blocked AT THE ADAPTER, not at the policy
layer — the adapter refuses to construct the write command, full stop, regardless of what
a mission plan believes. LO's personal bird (SM-A217F, Exynos 850, per repo evidence)
is the permanent first row: data-sacred, recon-only (Download Mode screens, UART capture
if pads live, USB PID enumeration — nothing one-way, ever). Sacrificial birds are spent in
order of cheapness (03 §7.4 burn-budget doctrine); donor boards are indexed by which
top-N model they serve. The relay boards (T3 USB-relay mode-entry rig) and the Beagle 480
sniffer get their own rows — sniffers especially: the Beagle is the loader factory's
machine tool and gets treated as such. Current T2/T3 wants (03 §9, feeds the FIRST
MANIFEST below): EDL cable ×2, CP2102 TTL, test-point kit, OTG HID board, sacrificial
MTK+QCOM birds, then T3's EasyJTAG Plus/Medusa Pro II, UFI Box, UFS programmer,
hot-air station, microscope, J-Link, Beagle 480, USB relay board, donor boards ×3,
ESD kit — each will be a ledger row the day it arrives.

---

## 7. THE RIG PROVISIONING — WINDOWS DRIVER DISCIPLINE

The panel is Windows 11; the silicon plane speaks USB through drivers, and drivers are
where Windows fights back.

**The driver map (what talks to what):**

| Rig function | Driver | Notes / conflict class |
|---|---|---|
| Qualcomm 9008 EDL | **UsbDk** (preferred by edl/mtkclient on Windows) or the stock Qualcomm QDLoader package | libusb-based; fights with QPST's own driver over the same VID:PID 05c6:9008 |
| QPST/QFIL | Qualcomm's package (its own QDLoader/QSUSB variants) | The edl tool can EMULATE QFIL XML flows (`edl qfil rawprogram0.xml patch0.xml`) — prefer emulation, avoid running QFIL's GUI stack at all (03 §7.1) |
| MTK BROM/Preloader | Stock MediaTek VCOM/preloader port driver + UsbDk as the libusb lane | mtkclient README documents the UsbDk Windows path and the codefl0w installer (HIGH) |
| Apple usbmuxd lane | **Apple Mobile Device Support** (the usbmuxd service + AppleUsbDevice DLLs) | libimobiledevice's Windows usbmuxd rides on AMDS or the open usbmuxd build; 06 §3 bridge — keep ONE muxd, not two fighting |
| Samsung Download Mode | Samsung USB driver (standard Odin package) | Well-behaved; rarely conflicts |
| Generic serial (UART TTL, relay boards) | CP210x / CH340 / FTDI class COM drivers | COM-port assignment drift is the annoyance; pin port names per adapter in the registry |

**The driver-conflict reality (documented annoyance, CONFIDENCE: HIGH that it happens,
MEDIUM on which exact pairs on a given build):** multiple phone stacks want the same
USB device class or COM ports — QPST's QDLoader vs UsbDk over 9008 is the classic; two
usbmuxd instances (Apple's AMDS + a standalone) split lockdown clients; VCOM drivers
fight over preloader PIDs across mtkclient sessions. The isolation scheme, in order of
preference: (1) **temporal isolation** — one mode per session, the rig state machine's
fresh-pwsh-per-command discipline (03 §7.1) extended to drivers: never run QPST and
edl-UsbDk against 9008 in the same boot session; (2) **per-tool VMs** — a Hyper-V or
VMware instance per conflicting stack (the QPST VM, the Apple AMDS VM), USB-passthrough
for the device, each VM with its own driver monoculture — this is the clean lane when
conflicts get persistent, at the cost of USB latency (fine for EDL, annoying for
high-speed sniffing — the Beagle stays on bare metal); (3) **the driver-signing dance**
— test-signing mode + signature enforcement off for unsigned box drivers (some box-tool
drivers ship unsigned; DANGER: disabling signature enforcement panel-wide weakens the
whole machine — rule: test-signing is a VM-only state, NEVER the panel's boot config).
Windows remembers the choices: pnputl export of the working driver set is part of the
armory's staged snapshots so a rebuilt panel restores the exact driver state, not a
guess.

**Windows Defender exclusions — the false-positive storm, documented reality:**
EDL/MTK/bre box tooling trips Defender constantly — pyinstaller-packed CLI agents,
firehose loader .mbn files that look like raw exploit payloads to heuristics, combo
firmware, Magisk-patched boot images, hashcat binaries (packed/cryptographic tools are
a classic AV flag), friTap/Frida gadget DLLs (injection tooling = malware signature
class). CONFIDENCE: HIGH that flags occur (this tool class is AV-flagged industry-wide),
MEDIUM on specific products. The discipline — the exclusion perimeter is NARROW and
AUDITED: exclusions cover ONLY `armory/tools/` and `armory/firmware/` (paths, not
extensions), NEVER the intake lane (`armory/intake` is ALWAYS scanned — that is where
grey-market files first land, §3e), never `Downloads`, never the whole disk. The
exclusion list is itself a manifest artifact — hash-chained, reviewed at every sync
window (an exclusion that grew silently is a finding, not a convenience). The panel's
real-time protection stays ON everywhere else; this is a forensics lab, the panel being
patient-zero is the §1 nightmare.

**The staging checklist before any rig session** (pre-flight, blocking):
1. Registry sweep: every tool the mission plan names resolves to a manifest row (§10
   request_tool all-green — NO ACQUISITION-NEEDED outstanding for mission tools).
2. Loader/pinout/combo pointers resolved for the target model(s) — or the session is
   scoped recon-only and says so.
3. Driver state verified: expected driver present, expected COM/USB class enumerated,
   conflicting stacks shut down (temporal isolation honored).
4. Bird registry consulted: target serial's data_sacred flag read by the ADAPTER, not
   the plan (§6); sacrificial-bird burn budget acknowledged.
5. Battery floor ≥30% for write sessions (SILICON-2); bench power for parked clocks.
6. Firmware cache hit: the exact rescue image for the bird's model-variant row is on
   disk and AVB-verified — BEFORE any write class op (evidence-before-flash, SILICON-3's
   sibling: rescue-before-risk).
7. Evidence ledger session opened; one-way-door counters photographed where applicable.
8. Airgap check: if DNS is dead, confirm nothing in the plan wants the network —
   missions never fetch (§9 law 5).

---

## 8. THE AIRGAP PROTOCOL — THE DNS-DEAD PANEL IS NORMAL

The premise inversion: this panel spends weeks DNS-dead (documented episodes). An
architecture that treats offline as failure will offline-fail; the armory treats OFFLINE
as the DEFAULT STATE and uplink as the special event. **Offline-first design:** the
cortex's mission capability must be fully resident — every tool, loader, pinout, driver,
firmware image, and research corpus the mission could need is pre-staged BEFORE the bird
arrives. The test of the design is the §7 checklist: a green pre-flight on a DNS-dead
panel. Anything that would fetch mid-mission is a design bug, and the fix is always
"stage it during uplink," never "fetch it now" (law 5 below).

**The uplink window** — operator brings internet (hotspot, or the panel moves, or a
USB-tethered phone): the armory runs its sync protocol. What gets synced, in priority
order (bandwidth-and-attention-constrained; the order is the doctrine):

| Pri | Class | What | Why first |
|---|---|---|---|
| 1 | Security/intel | CVE feeds, patch-coverage matrix deltas for the exploit library, new disclosures (Donjon-class) | The compounding asset (§4d) — and the threat picture for the panel itself |
| 2 | Manifest & tool updates | New pinned versions of core tools (edl/mtkclient/libimobiledevice), where the change log matters; NEVER auto-applied — queued as armory tasks (law 7) | Keeps the moat sharp without breaking law discipline |
| 3 | Loaders | New bkerler/Loaders upstream deltas + grey-pack acquisitions + any pending loader requests from parked sessions (ACQUISITION tasks from rig state-machine step 3) | The #1 mission-unblocking asset |
| 4 | Firmware cache refresh | Data-sacred rescue images, top-N model latest stock, downgrade floors (§5 order) | The flash ammunition |
| 5 | Pinouts & combos | New pinout harvests, per-model combo acquisitions for models actually seen | The bench-unlocking assets |
| 6 | Research corpus | DDG-HTML sweeps queued during offline (queries batched), forum deltas, docs | Feeds cortex reasoning; lowest urgency |

**Version-drift reconciliation** (when the panel rejoins): the armory diffs its manifest
revision against the upstream manifest (the internet-side copy the operator maintains) and
against the world (upstream release pages). Drift cases and verdicts: upstream moved and
we didn't → a QUEUED update task (deliberate, re-verified, law 7 — never auto-applied);
we moved and upstream didn't (local patch) → row flagged `local-fork`, documented; upstream
MOVED AND CHANGED LICENSE/CLAUSE (edl's non-commercial note, a license flip, a yanked
release) → the row is flagged for operator review before the tool's next use — license
state is a security property of the row, not decoration; a drop arrives with files whose
hashes match NOTHING pending → quarantined as unsolicited, provenance investigation before
any promotion (§3e). The reconciliation output is a drift report LO reads — the armory's
honesty document — plus the new airgap-staging list: whatever the window brought gets
pre-positioned for the next offline stretch, and the loop closes.

---

## 9. SELF-ARMING LAWS v2 — GATE-17.8 UPGRADED FOR THE UNIVERSAL ERA

The original GATE-17.8 (the cortex installs tools without asking) is RETAINED in full —
it is what makes the system universal — and CONSTRAINED by seven sub-laws. Together
this is the v2 contract:

1. **MANIFEST-FIRST ALWAYS.** No acquisition of any executable/flashable artifact begins
   without a manifest row (with hash) existing first. The row precedes the fetch; the
   fetch precedes nothing. (§2)
2. **HASH-REFUSAL WITHOUT EXCEPTION.** A binary that fails its hash never executes on
   the panel — no "it's probably the mirror's fault, run it anyway," no operator-override
   shortcut, no emergency lane. The refusal is the gate that makes GATE-18.1 real. (§2.2)
3. **QUARANTINE BEFORE ENTRY-POINT PROBE.** Everything new lands in quarantine with no
   execute privilege; probes are static/structural; promotion is a registry event with a
   ledger row. The panel never runs what it has not installed through the gate. (§2.2)
4. **NO GREY-MARKET FIRMWARE EXECUTES ON THE PANEL — flash targets only.** Combos,
   leaked MSM packs, grey loaders execute on BIRDS, never on the panel (`panel_exec=false`
   is structural in the row), and they flash only after AVB verification (§5) and only on
   lawful (sacrificial/refurb) targets. The panel is not a test bench — it is the brain;
   brains don't taste strange firmware. (§4b)
5. **THE ARMORY GROWS ONLY VIA ARMORY TASKS — NEVER MID-MISSION.** Missions fetch
   NOTHING. A mission that discovers a missing asset files an ACQUISITION task, parks the
   bird (03 §7.2 step 3), and the armory fulfills it during the next uplink window or
   USB drop. This is the airgap law expressed as an arming rule — it makes missions
   deterministic and the DNS-dead panel a non-event. (§8)
6. **EVERY ACQUISITION LEAVES A LEDGER ROW (provenance law).** What, from where, fetched
   by whom/what, when, why (task/mission id), hash, verdict. An asset without provenance
   is not an asset — it is an intruder with a file name. (§2.2, §3f)
7. **VERSION-PIN DISCIPLINE — THE ARMORY NEVER AUTO-UPDATES.** No tool self-updates, no
   `latest` tags, no unattended upgrade tasks. Updates are DELIBERATE armory tasks:
   new row, new hash, re-verification through the full §2.2 flow, drift-documented (§8
   reconciliation). An armory that auto-updates is a standing supply-chain offer (§1
   update-hijack lane) and a reproducibility failure (§11) in one.

The v2 sentence: self-arming is a RIGHT the cortex earned by accepting that arming is a
CEREMONY — the manifest row, the hash, the quarantine, the ledger row. Speed comes from
pre-staging (§10 stage_for_mission), never from skipping the ceremony.

---

## 10. THE ARMORY API — THE MODULE INTERFACE THE CORTEX CALLS

The armory is a module with a narrow, explicit interface — the cortex talks to tools
through it, never around it.

| Call | Signature | Returns / semantics |
|---|---|---|
| `list_armory` | `list_armory(status: <all\|installed\|staged\|pending\|quarantined>, plane: <danger_plane filter>, class: <tool\|loader\|combo\|pinout\|exploit\|firmware>)` | Manifest rows with install state; the cortex's situational view of what exists |
| `request_tool` | `request_tool(name, version?, context?)` | If installed+staged: {entry_points, install_path, version, danger_class, data_sacred_notes}. If not: **ACQUISITION-NEEDED** verdict + pending-task id. ACQUISITION-NEEDED is a MISSION-PARKING event, not a mid-mission fetch — the cortex plans around it, never through it |
| `stage_for_mission` | `stage_for_mission(objective: mission_plan)` | The auto-staging sweep: reads the plan's model-variant rows (§5 mapping), resolves every tool/loader/pinout/combo/firmware pointer the plan names, pre-stages from cache to the mission's staging directory, verifies all green, returns the §7 pre-flight checklist as a pass/fail report. A red report means the mission doesn't start — the panel doesn't do hope-based staging |
| `sync_armory` | `sync_armory(window: uplink-session)` | Runs the §8 protocol: priority-ordered sync, drift reconciliation report, new airgap-staging list. Uplink windows are events, sync is the event handler |
| Registry integration | (automatic) | Every tool the staging sweep pre-stages writes a registry row linking manifest ↔ install path ↔ entry_points ↔ the mission id that staged it — every execution on the panel is attributable to a manifest row, and every manifest row to a provenance trail. This is the audit spine: what ran, when, from which row, fetched from where, for which mission |

API-level enforcement (not politeness): the rig-bridge adapters resolve entry points ONLY
through the registry — a binary outside `armory/tools/<name>/<version>/` is not
addressable by a mission plan, period. The API is the single door between the cortex's
intent and the panel's execution surface; GATE-18.1 is enforced at exactly one choke
point because there is exactly one choke point.

---

## 11. WHAT THE ARMORY BUYS — AND WHAT IT COSTS

**Reproducibility:** any mission is re-runnable from the manifest — the same pinned
tools, the same loaders, the same firmware images, same hashes. A result that cannot be
reproduced from manifest rows is a result that didn't happen (SILICON-6's admissibility
logic, extended to the whole pipeline). Version pins turn "it worked once" into "it works
again on demand."

**Survivability:** the DNS-dead panel is a non-event. Offline-first staging (§8) plus the
firmware cache (§5) plus the loader/pinout libraries (§4) means the cortex's capability
is resident, not rented from the network. Uplink windows are growth events, never
life-support.

**Security:** GATE-18.1 gets an enforcement point instead of a wish. The cortex that
reasons over hostile content daily does so on a panel where everything executing is
hash-verified, version-pinned, quarantine-proven, and provenance-ledgered — the §1 attack
lanes all die at stage 2 of the install flow. The unarmored self-armer is one poisoned
loader pack away from being the story; the armored one is the machine that verifies the
poisoned pack and files it as a finding.

**Speed:** pre-staging kills the mid-mission fetch failure — the class of session-kill
where a bird is plugged in, hands are on the bench, and the tool wants the network that
isn't there. `stage_for_mission` moves every failure to BEFORE the bird arrives, when
fixing it costs a queued task instead of a parked session and an operator standing
around. The §7 checklist is a speed feature pretending to be bureaucracy.

**The honest cost — the discipline tax on LO:** every new tool wants a manifest row
FIRST. No more "just grab this zip real quick" — the quick grab is now a two-stage
ceremony (row, then fetch) with a hash hunt when the upstream doesn't publish one.
Updates don't happen by themselves; they're deliberate tasks with re-verification. The
exclusion list gets audited. Drops get processed, not dumped. This tax is real, it's
payable in operator attention, and it is the entire price of having a self-arming cortex
that isn't a supply-chain liability. The armory's honest promise: the tax is boring,
steady, and small; the thing it prevents is catastrophic and total. Pay the boring tax.

---

## ARMORY VERDICT

1. **The armory is not a tool shed — it is the panel's immune system.** GATE-17.8
   (self-arming) and GATE-18.1 (untrusted content) intersect at exactly one point: the
   moment something new runs. The armory owns that moment. Without it, the universal
   system's greatest strength (autonomous acquisition) is its greatest vulnerability
   (autonomous compromise); with it, the cortex can arm itself from the greyest channels
   in the industry — grey-market loaders, combo firmware, forum pinouts, leaked MSM
   packs — without ever letting those channels execute on the brain.
2. **The four libraries are the moat.** Tools are free and everyone has them (edl,
   mtkclient, libimobiledevice — all $0, all named in prior waves). The loader library
   (msmid_pkhash-named firehoses, V6 loaders, the Beagle-sniffing self-manufacture loop),
   the pinout library (per-board JTAG/ISP/UART maps with provenance confidence tags), the
   combo library (per-model Samsung engineering builds with hash discipline for the #1
   malware vector in this class), and the exploit library (checkm8-class permanents plus
   CVE-2025-20435-class patch-coverage tracking) are what the lab actually compounds.
   Box vendors sell exactly this — at $100–500 plus credits (LOW) with dongles — and the
   OSS lane plus the sniffing loop replicates their moat at $0.
3. **Airgap-first is a design, not a workaround.** The DNS-dead episodes made it true
   here before we made it doctrine: missions never fetch, uplink windows grow the
   armory, the panel's capability is resident. Priority-ordered sync (intel → manifest →
   loaders → firmware → pinouts → research) plus drift reconciliation makes the offline
   panel the NORMAL machine and the connected one the special case.
4. **The enforcement is structural, not behavioral.** Hash-refusal without exception,
   quarantine-before-probe, `panel_exec=false` on everything grey, adapter-level
   write-blocking on data-sacred serials, registry-only execution addressing — the laws
   live in machinery (the install flow, the API, the adapters), so the cortex cannot
   violate them by being in a hurry. Discipline that depends on the LLM remembering is
   discipline that fails at 3am; discipline that lives in the gate does not.
5. **The verdict in one sentence:** the armory is what lets this lab keep both of its
   defining properties at once — a cortex that arms itself instantly (GATE-17.8
   unimpaired) and a panel that is the most hardened node in the whole rig — and the
   only price is the discipline tax, paid in manifest rows, which is the cheapest
   insurance in this entire grand mission.

## FIRST MANIFEST — the concrete initial manifest contents for this lab's panel

1. **edl (bkerler/edl)** — GPLv3 (non-commercial clause noted), git-tag pin, entry: `edl`,
   plane silicon, panel_exec true, deps pinned via locked venv (PyUSB/pyserial/pycryptodome);
   provenance: github.com/bkerler/edl direct.
2. **bkerler/Loaders submodule** — loader library seed, plane silicon, panel_exec false
   (flash targets only), per-loader sha256 indexed in the loader library as grown.
3. **mtkclient (bkerler)** — git-tag pin, entry: `mtk`/`stage2`/`mtk_gui`, plane silicon,
   deps pinned (keystone-engine/capstone noted), `Loaders/V6` folder linked to loader lib.
4. **QPST/QFIL suite (Qualcomm)** — direct-download official package, plane silicon,
   panel_exec true but preferably replaced by edl's qfil emulation at runtime; driver
   isolation per §7.
5. **UsbDk** — winget/direct, plane panel-infrastructure, the 9008/BROM libusb lane.
6. **Samsung USB driver + Odin (3.13/3.14-class)** — Odin via XDA-mirror + second-source
   hash (grey-grade verification, network-isolated execution), Download Mode recon/rescue.
7. **libimobiledevice suite (1.4.0 era) + Apple Mobile Device Support (usbmuxd lane)** —
   git-tag/libinstaller pin, entries: `idevice_id`/`ideviceinfo`/`idevicebackup2`/
   `idevicepair`/`idevicerestore`, plane silicon/software, the whole iOS bridge (06 §3).
8. **checkm8 toolchain: ipwndfu (axi0mX) + palera1n** — exploit library, git-commit pins,
   panel_exec true (ramdisk build) but flash targets are the phones; ≤A11 matrix row.
9. **Offline-math stack: hashcat (+JtR jumbo)** — direct/winget pinned, plane offline,
   modes 5800/8800/8900 + bespoke SP verifiers (LockKnife, blackshibe/android-fbe-decrypt
   refs) as git-cloned research rows feeding W2b.
10. **Bench stack + T1/T2 hardware rows**: scrcpy, Android-PIN-Bruteforce
    (urbanadventurer), Frida + friTap (instrumentation, §4.7), pyusb/pyserial venv
    baseline — PLUS the T2 hardware ledger rows (EDL cable ×2, CP2102 TTL, test-point
    kit, OTG HID board, sacrificial MTK + QCOM birds) and T3 wants queued (EasyJTAG
    Plus/Medusa Pro II, UFI Box, UFS programmer, hot-air station, microscope, J-Link,
    Beagle 480 sniffer — the loader factory, USB relay rig, donor boards ×3, ESD kit)
    per 03_silicon_plane.md §9, each pending a manifest/ledger row the day it lands.

*Wave W4a complete. Feeds: W4b (the competition — what the boxes sell vs what this
armory replicates), W5 system audit (registry integration is the audit spine), and
BLUEPRINT (the armory module + its API go into the architecture as first-class citizens).*
