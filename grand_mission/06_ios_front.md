# THE iOS FRONT — W3b
*Grand Mission 06 · DroidCommand / Vesper · the complete Apple-device unlock/extraction
doctrine for an autonomous LLM-driven lab. Builds on 01_universal_door_map.md §1 (taxonomy
layers, the DATA/BOOT/CLOUD split) and §2f (cloud) — this wave is the Apple half of that map:
SEP, arrival states, the tool landscape, the checkm8 lane, the backup-artifact finisher,
pairing economics, activation-lock verdicts, and the bridge contract that drives it all.*

Laws carried: GATE-17.14 (THE CROWN — owner absent; the owner's body/credentials are never
a key, never a plan, never a fallback), GATE-17.15 (THE INTERIOR — reason from state, not
glass), GATE-17.13 (credential = STATE, computed not guessed at the glass), SCOPE GUARD
(LO's personal bird data-sacred; destructive work on sacrificial birds only).
Vocabulary inherited: ALIVE / CONDITIONAL / DEAD; planes glass→software→flash→silicon→cloud.
Danger classes inherited from 05: D0 pure read · D1 reversible · D2 wipe/destructive ·
D3 one-way · D4 brick-risk. Prices `~$` with CONFIDENCE tags; verification this wave:
live DDG-HTML + primary fetches (libimobiledevice.org, checkra.in, palera1n GitHub,
theapplewiki.com, elcomsoft.com + resellers, Apple Support, govtribe POs, Vice/imore press).
One named-claim audit included: the "Sarah Jamison A10 fuzzer" note — verdict inside §4.5.

---

## 1. THE APPLE LOCK STACK — WHAT ACTUALLY LOCKS AN iPHONE

Same reading order as the Android map: a locked iPhone is not "locked", it is eight
state machines, and the doors differ per layer. The iOS twist: ONE layer (the SEP) is the
kernel of difficulty for almost everything else.

| # | Lock layer | What it really is | Gates DATA? | Gates BOOT? | Gates CLOUD? | Verdict/notes |
|---|---|---|---|---|---|---|
| 1 | Passcode (PIN/password) | SpringBoard UI → keybag-unwrap request to the Secure Enclave: passcode + PASSCODE_SALT (effaceable storage) run through PBKDF2 inside/with the SEP; candidate key must unwrap the system keybag | Indirect — it WRAPS the per-file class keys | No | No | The UI face of #3. Guessing at the glass is the least-leveraged attack on iOS in existence (throttle ladder in §5) |
| 2 | Face ID / Touch ID | Biometric → SEP-verified token → unlocks session; never unwraps keys alone | No (convenience of #1) | No | No | Dead after reboot until first credential entry. Biometrics are a FINGERPRINT OF THE OWNER — crown-forbidden as a plan, useless as a fallback |
| 3 | Data Protection (per-file classes) | Every file carries a protection class; class keys live in the system keybag; keybag keys are SEP-wrapped + passcode-wrapped | YES — this is the real wall | No | No | Classes below. AFU vs BFU is a property of THIS layer |
| 4 | Secure Enclave (SEP) | Dedicated coprocessor (A7+, iPhone 5s era 2013 onward), own secure boot chain, own fuses/UID key, holds the keybag unwrap logic and the passcode throttle counter | YES — the kernel of difficulty | No (it guards secrets, not boot) | No | Never publicly broken on ANY iPhone chip (§4.5, §5.1). This single fact shapes the entire iOS front |
| 5 | Boot chain / SecureROM (bootrom) | Burned-in ROM → iBoot → kernel, each stage signature-checked; bootrom is the only truly unpatchable stage | No (does not encrypt) — but gates unsigned boot | YES — the boot/flash gate | No | A5–A11 bootrom: checkm8 (CVE-2019-8900, §4). A12+ bootrom: hardened — no public exploit, lane DEAD |
| 6 | Activation lock (cloud) | Server-side ownership check at activation; Find My tied | No — disk keys stay with the SEP regardless | No | YES | Gates REACTIVATION post-wipe, not the running disk (§8). FOLKLORE says "bypass tool exists"; reality says server-side + verified ownership only |
| 7 | Carrier/SIM lock (NCK) | Baseband NV lock bits — subsidy lock | No | No | No | Data-irrelevant, same verdict as Android map layer 8. Cheap commercial unlocks exist; never the data door |
| 8 | MDM / supervised / DEP | Policy state machine (profiles, supervision, enrollment) | Partial: can block every plane, can also REMOVE a lock on stale builds (§8.3) | Partial | YES (server-side enrollment) | Different animal from activation lock — has a legitimate bypass code path (MDM Activation Lock bypass code, §8.3) |

**Reading order for an arriving iPhone:** layers 3+4 are the data wall; 5 is the boot wall
(checkm8-able era only); 6 is the reactivation wall; 1 is only the UI face of 3+4; 7 never
mattered to the mission; 8 is a wall that occasionally contains a door.

### 1.1 Data Protection classes — the AFU/BFU engine

| Class (NSFileProtection…) | Key available | Meaning for extraction |
|---|---|---|
| Complete | Only while device is unlocked AND passcode entered at least once since boot (BFU = sealed) | The strong class: Messages SQL, Health, keychain ThisDeviceOnly, most modern app data. BFU → unreadable even with full boot control |
| CompleteUnlessOpen | While file is open (background downloads while locked) | Edge class, rarely the target |
| CompleteUntilFirstUserAuthentication (a.k.a. AFU class) | After first unlock since boot, until next reboot | The commercial extractors' favorite: once unlocked-since-boot, keys stay in userspace. Mail caches, much app data |
| None | Always | Camera roll DCIM (camera must fire at the lock screen), system files, some app caches |

**AFU (After First Unlock)** = device has been unlocked at least once since last reboot:
UntilFirstAuth + None keys live in RAM. **BFU (Before First Unlock)** = rebooted, locked,
never unlocked: only None-class readable. This is the same AFU/BFU doctrine as the Android
map §1 layer 3 — with the difference that iOS's verifier (SEP) never exposes an
offline-crackable artifact (the §5 asymmetry).

### 1.2 SEP architecture and the A11/A12 split (the checkm8-era fault line)

- **A7–A11 (iPhone 5s → iPhone 8/8+/X, 2013–2017):** SEP present since A7, but the
  APPLICATION PROCESSOR's bootrom is checkm8-able (CVE-2019-8900, axi0mX, Sept 2019;
  confirmed by theapplewiki + Zimperium: A5–A11, S1P–S3, T2 included). Bootrom is burned
  into silicon → unpatchable forever on this fleet. The SEP is a SEPARATE coprocessor with
  its own boot chain and is NOT compromised by checkm8 (Zimperium: "SEP not directly
  compromised"; theapplewiki, Reddit r/jailbreak_ concordance). CONFIDENCE: HIGH.
- **A12+ (iPhone XS/XR 2018 → current):** bootrom exploit surface closed (heap-overflow
  hardening axi0mX himself described as "fixed in A12"); SEP additionally hardened. No
  public bootrom exploit has EVER existed for A12+. CONFIDENCE: HIGH.
- **T2 Macs:** share the checkm8 lineage (theapplewiki device list) — forensic curiosity,
  not a phone lane. Not this wave's scope.

**Which layer gates what — the iOS/Android asymmetry in one line:** Android's credential
verifier artifacts (GateKeeper blobs, SP blob) live on FLASH and are (per-SOC) readable →
offline artifact attack exists (map §2g). iOS's keybag is double-wrapped — passcode-derived
key AND SEP-internal UID key — and the SEP never exposes the blob to any readable bus. The
verifier itself is the vault. Consequence: **on iOS the offline attack target is NOT the
passcode blob — it is the BACKUP artifact (§6), which Apple deliberately made a plain
PBKDF2 offline-verifiable format.** That reframes the whole front.

---

## 2. ARRIVAL-STATE TAXONOMY (iOS INTAKE)

Intake classifies BEFORE any door is chosen (same doctrine as map §5). Four canonical
arrival states plus the jackpot:

| State | What it is | What extraction realistically yields | Cost |
|---|---|---|---|
| (a) **AFU unlocked-since-boot** | Device unlocked at least once since reboot; may be sitting at lock screen NOW, but keys are resident | The cheap win: pairing/prompted backup (full logical), media, app backup data, UntilFirstAuth + None classes; with a jailbreak at hand: full filesystem image + keychain decrypt | Minutes–hours |
| (b) **BFU powered-off locked** | Rebooted/never-unlocked-since-boot; keys sealed in SEP | Only None-class: media/DCIM (if paired), crash logs, syslog, device info. Full data = passcode (→ §4/§5/§6 lanes only). Haronest wall in the business | Hours–never |
| (c) **BFU + passcode known by NOBODY** | The crown case: owner absent forever | ≤A11: checkm8 conditional lane (§4). A12+: the wall (§5) — backup-artifact lane (§6) and cloud-lane (§2f exception) are the only doors. This state is WHY this document exists | See §11 |
| (d) **Disabled/erased** | 10 wrong attempts (if Erase Data enabled) or remote wipe | Post-erase: data cryptographically gone (keys destroyed by SEP) → activation lock question only (§8). "Disabled" (not erased): still keybag-sealed BFU — same as (c) with a timer | Erased = DEAD |

Plus the fifth, non-canonical jackpot:

| State | What it is | Yield |
|---|---|---|
| (e) **Pairing jackpot** | A previously-paired bird lands on the panel (we hold its lockdown record), device is BFU or AFU-locked screen | No passcode prompt needed: media, crash, syslog, diagnostics; on AFU: full logical backup (backup agent runs in userspace with resident keys). Elcomsoft sells exactly this ("accessing locked devices via lockdown records" — elcomsoft.com product pages, CONFIDENCE: HIGH). See §7 |

Intake capture per state (the LLM's first five minutes): `idevice_id -l` → `ideviceinfo`
(ProductType, ProductVersion, ActivationState, BuildVersion, ChipID via MobileGestalt) →
`idevicepair validate` → screen-state photo (glass ORACLE only, per GATE-17.15). From
ProductVersion+ChipID the entire map (§4/§5/§11) is deterministic — that is the intake
state machine the panel walks.

---

## 3. THE EXTRACTION TOOLS LANDSCAPE — THE HONEST 2025 REALITY

What each tool ACTUALLY does, per arrival state and hardware era. License reality and
prices with CONFIDENCE tags. The pattern to internalize: LE closed-source boxes hold
private per-chip SEP exploit estates; the open world holds checkm8 (≤A11) + pairing +
backup math; consumer GUIs hold nothing the panel should trust.

| Tool | Class / license | What it does on AFU | On BFU | Era gates | Price reality |
|---|---|---|---|---|---|
| **GrayKey (Grayshift → Magnet Forensics)** | LE-only box + subscription; closed source | Full FS + keychain extraction on supported builds (vendor marketing: "accesses more data than any other extraction technology" — magnetforensics.com) | The famous capability: brute-forces passcodes on locked/BFU iPhones via private SEP exploits, per-chip/per-iOS windows; "Turbo" brute marketing (imore). Apple patches walk it back release by release — a treadmill, not a key | iOS support lags/leads by SEP-exploit estate, not bootrom | Subscription: online tier historically $18k/yr (Vice 2019); recent single-license federal POs $11.8k (DEA 2024) / $12.4k (FLETC 2025) — govtribe. CONFIDENCE: HIGH on orders, MEDIUM on list floors |
| **Cellebrite UFED 4PC / Touch 2 / Premium (Inseyets)** | LE + enterprise (corporate/PI licensing varies by jurisdiction); dongle(s) | Logical + advanced extraction, decodes | Premium tier = the unlock estate: "unlimited lawful access to iOS and high-end Android" (cellebrite.com/premium) — same private-exploit treadmill as GrayKey | Same: support matrix churns per iOS | UFED 4PC ~$6k–12k/yr; Touch 2 $15–20k/yr; Premium/Inseyets $15–30k/yr (civiciq.com, sherlockforensics.com reseller analyses). CONFIDENCE: MEDIUM (two independent secondary sources, no primary price sheet) |
| **Magnet AXIOM** | Analysis suite, quote-based licensing | Parses/decodes extractions (backups, GrayKey/UFED dumps) | Not an extraction tool per se — the ANALYSIS half of the Magnet stack | — | Vendor-quote; four-figure per seat-year commonly reported. CONFIDENCE: LOW |
| **Elcomsoft iOS Forensic Toolkit (EIFT)** | Commercial, sold to LE + corporate forensic buyers (contract terms); CLI-driven since 8.0 (Sept 2022 press release: "forensically sound checkm8 extraction… command-line driven") | Agent-based FS extraction + keychain on jailbroken/ramdisk-booted birds | checkm8 ramdisk extraction on ≤A11 (5s→X: partial FS + keychain on BFU/locked/disabled — SUMURI reseller copy, CONFIDENCE: HIGH); pairing-record path on locked birds (§7); passcode unlock advertised with per-chip limits (A10/A11 caveats, §4.3) | checkm8 era ≤A11 for the deep paths; newer chips = logical-only | **$2,199 published reseller price** (arsdigitalforensics.com listing, CONFIDENCE: HIGH for that listing; renewal/licensing terms quote-based) |
| **Elcomsoft Phone Breaker / DPF tools** | Commercial, purchasable | Backup password attacks, iCloud with credentials | The OFFLINE lane (§6): 0x29/0x2A/0x309 backup formats, GPU-accelerated PBKDF2 | Any iOS with an encrypted backup artifact — era-proof | ~$1–2k/yr band per module (reseller band). CONFIDENCE: LOW-MEDIUM |
| **libimobiledevice / usbmuxd stack** | FOSS (LGPL/GPL), free forever, current 1.4.0 (Oct 2025) | ideviceinfo/idevicebackup2 full logical, media via ifuse, syslog, crash reports, diagnostics | All lockdown services reachable WITHOUT passcode when paired (§7); on unpaired+locked: device info only | Supports "first to latest iOS device" (primary claim) — era-proof | $0. CONFIDENCE: HIGH (primary source fetched) |
| **palera1n / checkra1n (checkm8 lineage)** | FOSS/free, checkra1n semi-closed (macOS GUI + Linux CLI), palera1n open | Jailbreak on ≤A11 (post-exploit AFU = Filza/keychain dumps, §5.2) | checkm8 bootrom pwn → custom ramdisk (§4.4) on BFU ≤A11 | A8–A11 + T2, iOS 15.0+ (palera1n GitHub); checkra1n covers older iOS. Hardware ceiling: A11 iPhones end at iOS 16.7.x; iOS 17/18 reachability exists only via A10-class iPads (iPad 7th gen line runs iPadOS 17/18; Reddit beta threads). CONFIDENCE: HIGH on matrix, MEDIUM on exact iPadOS ceilings | $0 |
| **ipwndfu (axi0mX)** | FOSS research PoC | The raw exploit primitive the others build on | DFU pwn →SecureROM payload; parents of every checkm8 tool above | ≤A11 + T2 | $0 |
| **i4tools / 3uTools class** | Consumer GUI, free, Shenzhen ecosystem | Backup/restore/flash helpers with a pretty face | Nothing forensic-grade; unsigned telemetry risk; NEVER near evidentiary birds (scope-guard: sacrificial only, if ever) | — | $0 (but you pay in unknown network calls). CONFIDENCE: LOW on safety, HIGH on existence |

Landscape verdict: **the only crown-compatible, license-clean, bridgeable lanes are
libimobiledevice (pairing/backup/diagnostics), checkm8-class (≤A11 boot control), and
Elcomsoft-class offline math (backup artifacts). GrayKey/Cellebrite are $12–30k/yr LE
contracts with dongles — the panel does not bridge them (§9); it out-waits their treadmill
by owning the unpatchable base (checkm8) and the artifact math.**

---

## 4. THE CHECKM8/CHECKRA1N LANE (≤A11)

### 4.1 What checkm8 actually is
SecureROM (bootrom) USB heap overflow, CVE-2019-8900, discovered/released by axi0mX
(ipwndfu, Sept 2019). Affects A5–A11, S1P–S3, S5L8747, T2 (theapplewiki). Bootrom is
manufacturing-time ROM → **unpatchable, permanent for the life of the fleet** (tin-z
starterpack, techacrobat: "jailbreakable forever"). Gives: unsigned code execution at the
iBoot level → custom ramdisk boot, custom kernel, pwned DFU persisting across the session.
CONFIDENCE: HIGH everywhere.

### 4.2 What checkm8 does NOT do — the precise truth (this section is load-bearing)
**checkm8 does NOT break the SEP. On ANY chip. Not A10, not A11.** The SEP is a separate
coprocessor with its own boot chain, own fuses, own root of trust; checkm8 pwns the AP's
ROM, which hands you the FILESYSTEM PLANE (boot control), never the keybag unwrap
(verification of every claim: Zimperium analysis "SEP not directly compromised";
r/jailbreak_ thread: "rate limiting is enforced on the Secure Enclave itself, which is
not vulnerable to checkm8"; theapplewiki). CONFIDENCE: HIGH — triple-sourced.

Consequences, stated plainly:
- **"SEP-frozen passcode brute" — mostly folklore.** A pwned ramdisk CAN run a passcode
  brute agent, but every guess still walks into the SEP for verification, and the SEP owns
  the throttle counter (persisted, not reset by re-pwn or reboot). On A7+ this is a SIEGE
  at glass-equivalent rates, not a break. The real-world ≤A11 numbers people quote come
  from GrayKey-class private SEP work (§4.5), not from checkm8. CONFIDENCE: HIGH.
- **checkra1n A10/A11 limitation (verified from checkra1n's own FAQ, checkra.in):**
  "A11 devices on iOS 14.0 and above require removing the passcode and enabling 'Skip A11
  BPR check' in the options. This is not recommended." The BPR (Boot Progress Register)
  check ties passcode-signed state to boot; skipping it to jailbreak forces PASSCODE
  REMOVAL — and removing the passcode destroys the passcode-wrapped class keys on the
  device (Complete-class data dies). CONFIDENCE: HIGH (primary).
- **Therefore A11-on-iOS-14+ jailbreak = filesystem access to None/AFU-class files only.**
  On an AFU-since-boot bird, that is still most of the interesting extraction surface
  (UntilFirstAuth data); on a BFU bird it is the None-class subset. This is exactly why
  §11 rates "BFU ≤A11" as CONDITIONAL, not ALIVE.

### 4.3 The forensic use of a checkm8'd bird (verified pattern)
Elcomsoft's own engineering blog ("Using and Troubleshooting the checkm8 exploit", 2023-10)
+ EIFT 8.0 press release document the pattern the whole industry uses: pure checkm8 alone
is not enough → tool boots a **custom ramdisk with an on-device extraction agent** over the
pwned boot chain → agent reads the filesystem (classes it can reach, per §4.2) and the
keychain (keychain items decryptable under the keys the agent holds; ThisDeviceOnly/
SEP-wrapped items stay sealed without passcode). Passcode unlock is advertised with
per-generation limits and A10/A11 caveats. CONFIDENCE: HIGH on the pattern, MEDIUM on
exact per-chip unlock support claims (vendor copy, not independently reproduced).

### 4.4 What a pwned DFU session gives the panel, concretely
- Custom ramdisk with SSH/agent (idevicerestore primary docs: "custom firmware files
  (requires bootrom exploit)" — the panel's own ramdisk-builder path on ≤A11).
- Filesystem image of reachable classes (D0 read-only discipline, sacrificial bird first).
- Keychain subset; app container pulls; FFS snapshot for diffing (evidence law §10).
- Passcode-brute siege only as a LOW-priority timer job (D1: throttle counter grows —
  never on the data-sacred bird, crown law: computed credential, not glass-guessed).

### 4.5 The "A10/A11 SEP bypass" research claims — verified status
- **"Sarah Jamison A10 Fusion fuzzer" notes:** DDG search this wave returns ZERO results
  for the name+topic. No talk, no paper, no repo found. **Verdict: folklore/misattribution
  until a primary surfaces. CONFIDENCE: HIGH on the absence (searched), LOW on any
  underlying claim.** Do not build doctrine on it.
- The real 2021–2023 SEP-research landscape (what actually existed): Siguza's SEP-oriented
  reverse-engineering writing (public education, no SEP break); the checkm8/T2 explosion
  (AP-plane, never SEP); academic fault-injection/glitching work on discrete secure
  elements (no iPhone SEP extraction reproduced publicly). **No public SEP exploit for
  ANY iPhone chip exists as of this wave. CONFIDENCE: HIGH.**
- GrayKey's claimed locked-iPhone brute (imore "Turbo brute force" headline; Vice
  pricing pieces) is the market's evidence for a PRIVATE per-chip SEP estate — inference,
  CONFIDENCE: LOW-MEDIUM. It is a treadmill: Apple ships SEP/iOS fixes, Grayshift
  re-arms. The panel neither owns nor depends on that treadmill.

### 4.6 Why A12+ killed this lane
Bootrom exploit surface hardened at A12 (checkm8 lineage does not reach it — theapplewiki
device matrix ends at A11; Zimperium: "up to and including iPhone X"); SEP hardened in
parallel. No public bootrom exploit has ever existed for A12+. The lane is DEAD on A12+ —
not "hard", DEAD (for the public world). CONFIDENCE: HIGH.

### 4.7 The secondhand sacrificial-bird market
checkm8-able fleet (iPhone 8 / 8+ / X top of the line, 7/6s/SE1 below): clean used units
~$40–120 depending on storage/cosmetics (eBay/Swappa market reality; Alibaba 2026 used
price-guide band corroborates the low tier). iCloud-locked "for parts" units float in the
$10–30 range (postage-adjacent). For the LAB: a clean iPhone 8/X + Lightning rig = the
training ground where every iOS skill gets rehearsed before it touches a real bird.
Price CONFIDENCE: LOW (marketplace-skim, no fixed price sheet).

---

## 5. BFU REALITY ON A12+ — THE HONEST WALL

### 5.1 The wall itself
Passcode → PBKDF2 → candidate KEK → SEP unwraps/compares against the system keybag stored
in effaceable storage. The keybag is wrapped with BOTH the passcode-derived key AND
SEP-internal key material; the SEP never exposes the wrapped blob over any bus the panel
can read without an SEP exploit. **There is no off-device verifiable passcode artifact on
iOS — the exact inverse of the Android map §2g.** CONFIDENCE: HIGH (this asymmetry is the
consensus of every source in this wave: Elcomsoft docs/throttle reality, Zimperium, r/jailbreak_).

On-device brute throttling (SEP-enforced): wrong attempts → escalating delays; after a
handful of failures the ladder climbs from minutes to the famous 1-hour-per-try ceiling;
10 wrong attempts with "Erase Data" enabled (OFF by default, Apple-documented) → wipe.
No reboot, re-pwn, or ramdisk resets the SEP's persisted counter. The panel's law: **no
guessing at the glass — iOS throttles are a harder siege than Android's** (map 2a HID
siege rates are unreachable here). GATE-17.13's iOS form: compute artifacts, never type.

### 5.2 The 2024–25 research lanes, honestly rated
| Lane | Status | Verdict |
|---|---|---|
| (a) "SEP is fed passcodes — side channels/glitching" | Academic fault-injection on discrete secure elements exists; NO published iPhone-SEP key extraction; vendor-private estates (inference). No independent replication | THEORETICAL. Watch, don't plan. CONFIDENCE: LOW |
| (b) Jailbroken AFU extraction | Real and current: on ≤A11, palera1n (iOS 15–17-era, A8–A11 + A10-class iPads on 17/18); on A12+ iOS ≤16.x, Dopamine-class arm64e jailbreaks; TrollStore-class perma-signed apps on 14.0–16.6.x/17.0 windows | ALIVE but CONDITIONAL (bird must be jailbroken/exploitable AND unlocked-since-boot for the data classes that matter). Filza/keychain dumps then trivial. CONFIDENCE: MEDIUM-HIGH |
| (c) Backup password attack | The offline-attackable artifact — iOS's deliberate weakness. Full §6 | ALIVE — the iOS finisher |
| (d) iCloud extraction via credentials | Crown exception per map §2f: IF the operator owns/controls the account, cloud backups + synced data are reachable (Elcomsoft-class with account password + 2FA handling). NOT a no-credential door — the panel never treats it as a default. Note: Advanced Data Protection (E2E iCloud encryption, global since Jan 2023; Apple withdrew it in the UK Feb 2025 rather than backdoor — press-verified) makes even Apple unable to serve most iCloud key material with ADP on | CONDITIONAL — account-gated, not bird-gated |
| (e) Pairing-record survival | Verified: a live lockdown record keeps a battery of no-passcode services (§7 full table) — the "some data without passcode" classes are None + (AFU) UntilFirstAuth | ALIVE — arrival-state economics, not an exploit |

Big-lane verdict for A12+ BFU: **near-dead except the backup-artifact lane and the
pairing/cloud conditionals.** The wall holds. Doctrine says so plainly because every
"iPhone unlock service" ad on the grey market is selling either (c) backup math,
(d) account access, or a lie.

---

## 6. THE OFFLINE ARTIFACT ATTACK (iOS analog of W2b) — THE FINISHER LANE

The one artifact Apple made offline-verifiable: **the encrypted iTunes/Finder backup.**
The backup password never touches the SEP. It unwraps the backup keybag with plain
PBKDF2 — a format built so ANY computer can verify guesses. This is the iOS counterpart
of Android's SP-blob attack (map 2g / wave 04), and on iOS it is the ONLY off-device
credential math there is.

### 6.1 Backup format history and hash extraction

| Era | Keybag type | KDF | Attack speed |
|---|---|---|---|
| iOS ≤ 9 | 0x29 | PBKDF2-SHA1, ~10,000 iterations (hashcat forum-documented: "iterations are 10000") | Trivial: hashcat **-m 14700** (iTunes backup < 10.0) |
| iOS 10.0–10.1 | 0x2A | 10M iterations BUT SHA-256→SHA-1 transition mid-derivation | The famous Elcomsoft 2016 discovery: ~2,500× faster attack. Dead era, still-worth-knowing era |
| iOS 10.2+ → current | **0x309** | **PBKDF2-SHA256, 10,000,000+ iterations** (elitedigitalforensics: "iOS 10.2+: 10,000,000+ iterations"; philsmd's itunes_backup2hashcat emits exactly this) | hashcat **-m 14800** (iTunes backup 10.x). This is today's artifact |

Hash extraction: philsmd/itunes_backup2hashcat (Perl, parses Manifest.plist BackupKeyBag:
WPKY salt/ITER attributes → `$itunes_backup$*10*…` hashcat line; CONFIDENCE: HIGH —
primary repo fetched via DDG round). 0xNemo Python port exists; John the Ripper jumbo
consumes the same keybag math (hashextractor documents both hashcat and JtR paths;
CONFIDENCE: MEDIUM on exact JtR format name). Elcomsoft Phone Breaker and every boxed
tool need ONLY the Manifest.plist (hashcat forum: "Cellebrite, Elcomsoft… need only the
manifest.plist to run an attack"). CONFIDENCE: HIGH.

### 6.2 GPU economics for the 10M-iteration class
Per-guess cost: 10M PBKDF2-SHA256 iterations ≈ tens of millions of SHA-256 compressions
per candidate — a deliberately slow KDF. Order-of-magnitude bench: a single modern GPU
lands in the **~100–500 H/s class on -m 14800** (hardware/overhead-dependent;
CONFIDENCE: LOW — no fixed vendor bench; the panel should bench its own card at armory
time and let the registry carry the number). The math structure, which is certain:

| Candidate space | Size | At 100 H/s | At 500 H/s |
|---|---|---|---|
| 4-digit PIN | 10^4 | ~1.7 min | ~20 s |
| 6-digit PIN | 10^6 | ~2.8 h | ~33 min |
| 8-digit PIN | 10^8 | ~11.6 days | ~2.3 days |
| 8-char alphanumeric (62^8) | 2.18×10^14 | ~69,000 years | ~13,800 years |
| Human-chosen 10-char passphrase w/ wordlist | ~10^9–10^11 first | wordlist-first collapses it | wordlist-first |

Doctrine mirror of map §2g: digits die, wordlists bleed, random-strong survives. The
panel's wordlist battery (rockyou-class + context-derived from the bird's other data)
runs BEFORE brute masks — same as Android lane. CONFIDENCE: HIGH on topology.

### 6.3 What success yields — the crown-compatible finisher
Cracked backup password → decrypt the backup → **restore to a DIFFERENT device** with the
backup password (Apple's own restore flow requires exactly: the backup files + the backup
password; no device passcode involved). The artifact plus its password is a self-contained
data capsule independent of the bird's lock state, SEP, and activation state. If the
panel holds a backup from any source (paired host, cloud account, seized disk,
formerly-owned machine), the backup is the finisher for a bird the panel cannot boot.
CONFIDENCE: HIGH.

### 6.4 The keychain dependency chain (backup → keychain)
Encrypted backups (password set) include the keychain subset that syncs to backups;
**ThisDeviceOnly items are excluded by design** (SEP-tied; Apple's documented restore
behavior — they never migrate to new devices). So the chain reads: backup password →
backup keybag → keychain items (non-ThisDeviceOnly: most app/site passwords that sync) →
further account access → possibly the iCloud lane (§5.2d). Each hop is another arrival
state the panel inherits. The backup password is therefore the highest-leverage secret
on the entire iOS board after the device passcode itself — and unlike the device
passcode, it is computable offline. CONFIDENCE: HIGH.

### 6.5 Acquisition paths for the backup artifact (where backups come from)
1. Any host the bird previously synced with: `Manifest.plist` lives in the backup folder
   (Windows: `%APPDATA%\Apple Computer/MobileSync/Backup/<UDID>/`; macOS:
   `~/Library/Application Support/MobileSync/Backup/<UDID>/`). D0 read.
2. The panel's own pairing-record backups (§7): idevicebackup2 from an AFU paired bird.
3. Cloud lane with credentials (crown exception, §5.2d).
4. A RAM disk image of the bird's own disk (AFU-jailbroken ≤A11, §4.3/5.2b) — the
   backup agent's files include the same format artifacts.

---

## 7. PAIRING + TRUST LANE — THE RECORD IS A KEY

### 7.1 What a pairing record is
Lockdown plist (host side): DeviceCertificate, DevicePrivateKey? (no — device-side cert +
host keypair), HostID, SystemBUID, RootCertificate, and the EscrowBag — the blobs that
make the host a TRUSTED computer. Trusted-computer status **survives reboots and normal
iOS updates; it dies on device restore/wipe and on user-initiated un-pair/Reset Location
& Privacy.** CONFIDENCE: MEDIUM-HIGH (libimobiledevice-documented lifecycle + forensic
literature). USB Restricted Mode (iOS 11.4.1+): data-port lockdown after ~1h locked
(Elcomsoft/LanCologne product docs confirm the recovery/DFU escape hatch remains) —
pairing BEFORE the hour, or an already-paired port, is the operational counter.

### 7.2 The services a pairing record buys (no passcode, no unlock tap)
| libimobiledevice tool | Service | Works on BFU locked? | Yield |
|---|---|---|---|
| `ideviceinfo` / `idevice_id` | lockdown/MobileGestalt | YES | Full device identity: ProductType, iOS, ChipID, ECID, serial, IMEI-in-scenarios, ActivationState — the intake oracle (§2) |
| `idevicesyslog` | syslog relay | YES | Live system log — state recon, app activity hints |
| `idevicecrashreport` | crash log mover | YES | Crash/diagnostics history |
| `idevicediagnostics` (mobilegestalt, ioregistry, restart, shutdown, sleep) | diagnostics | YES | IORegistry state, battery, and RESTART/SHUTDOWN verbs (D1: state change, gate them) |
| `ifuse` / AFC (media) | afc file access | YES — media is None-class (camera fires at lock screen) | DCIM/media tree, downloads |
| `idevicebackup2` | mobilebackup | YES-ish: backup agent starts, but file CLASSES gate what lands in the backup — on BFU expect a thin backup; on AFU-locked-screen expect the FULL logical backup (this is the jackpot: app data + settings, keychain subset only if backup is ENCRYPTED with a known/none-cracked password) | The §6 artifact generator |
| `ideviceinstaller`, `ideviceimagemounter`, `idevicepair`, `ideviceactivation`, `idevicerestore`, `iproxy` | installer/debug/devimg/pairing/activation/restore/tunnel | mixed; installer needs unlocked session typically | Full panel-side control surface (see §9) |

(Elcomsoft product pages market exactly this shape: "accessing locked devices via
lockdown records… media files, crash/diagnostics logs, stored files of multiple apps."
CONFIDENCE: HIGH on the class list; MEDIUM on per-service BFU/AFU nuances — the panel
verifies per iOS build, per §9's verification harness.)

### 7.3 The pairing-record law (a new law for the ledger)
**PAIRING-1: never lose a pairing record — it is a key.** Every bird that ever pairs
with the panel host gets its lockdown plist snapshotted into the evidence ledger with the
UDID, chip, iOS, and pairing date. On Windows the panel keeps `%ProgramData%\Apple\Lockdown\`
and the per-user `Lockdown` trees under inventory (D0, versioned). Restoring old records
onto a fresh panel host = re-arming the jackpot state on a bird's NEXT arrival.
**PAIRING-2: pre-pair at intake when possible** — a bird that arrives unlocked (AFU) and
owner-less still allows "Trust" flows for services; harvest everything while the state
lasts (D0/D1 discipline, one-way doors logged).

---

## 8. ACTIVATION LOCK — THE CLOUD WALL

### 8.1 What it gates
Server-side ownership check during ACTIVATION (post-wipe/setup). It gates REACTIVATION —
it does not encrypt the disk, does not hold the passcode, does not affect an
already-activated device's lock screen. A BFU, activated, Find-My-flagged bird can still
be paired/backed up per §7 — activation lock only matters when the bird is wiped/erased
or reactivated. CONFIDENCE: HIGH (Apple Support 108934 + Apple Community: "Activation
Lock is a server-side security mechanism").

### 8.2 Bypass reality 2025
- No local bypass exists on current builds. The check happens against Apple's servers;
  the only legitimate satisfaction paths are the owner's Apple ID credentials or Apple
  Support with verified-ownership proof (Apple Support pages; MacObserver walkthrough).
- **GSX "factory unlock" folklore: SCAM CLASS.** Grey-market "GSX erase/he3 unlock"
  services are phishing/stolen-credential/dns-trick operations per the unloky myth-buster
  and Apple Community consensus. The famous "he3/activation-ticket" lore from the
  checkm8 era does not survive contact with the server-side reality. CONFIDENCE: HIGH
  that no legitimate third-party local bypass exists; MEDIUM on individual service
  operators' methods (they are, uniformly, either scams or fraud — the panel never
  touches them).
- **Honest verdict, stated plainly: a BFU + activation-locked bird with no owner and no
  credentials is a PARTS BIRD.** Its data may still be technically alive on the NAND
  (encrypted), but every door to it is closed: no reactivation, no pairing (wipe killed
  it), no backup (fresh setup wipes the old backup relationship), no cloud (unknown
  account). Strip it for the training fleet or the silicon bench (sacrificial duty),
  and let the ledger say "parts".

### 8.3 MDM lock vs activation lock — the distinction that actually pays
- **MDM Activation Lock bypass code:** MDM deployments generate an escrowed bypass code
  that clears the lock WITHOUT Apple ID (SimpleMDM documentation). LEGITIMATE for
  fleet-owned hardware: a supervised corporate bird with the code on file unlocks
  cleanly. The panel's MDM intake branch asks: is this a fleet bird with a code path?
- **MDM profile removal on stale iOS:** grey-market "MDM bypass" tricks live in the
  setup-wizard/activation-escape family (the old DNS/server tricks + profile-removal
  bugs on unpatched builds). CONDITIONAL on stale build levels; current builds with
  Automated Device Enrollment close them year by year. CONFIDENCE: MEDIUM-HIGH on
  existence, LOW on any specific current chain (verify per build, never buy folklore).
- Doctrine: MDM-locked ≠ activation-locked. Intake separates them (settings state read
  when session reachable; activation screen readout otherwise). An MDM lock is a wall
  with doors in it; activation lock is the finished wall.

---

## 9. THE iOS BRIDGE — HOW THE PANEL DRIVES IT ALL

The orchestrator contract (wave 02 §3: registry entries with `interface: cli|rig|…` and
adapter functions) fits the iOS front like a glove, because the good tools are CLI-native.

### 9.1 Bridge adapters (first-class, license-clean)
| Adapter | Tool(s) | Interface | Panel verbs |
|---|---|---|---|
| `bridges.libimobiledevice` | idevice_id, ideviceinfo, idevicepair, idevicebackup2, idevicecrashreport, idevicediagnostics, idevicesyslog, ifuse, ideviceinstaller, ideviceactivation, iproxy, idevicerestore | cli, USB (usbmuxd) | intake recon, pairing validate/pair, logical backup, crash pull, syslog stream, diagnostics, media mount, activation-state read, tethered restore. Windows note (primary, libimobiledevice.org): usbmuxd is not fully supported on Windows — the rig runs Apple Mobile Device Support (from the iTunes bundle) for the mux daemon. Version pinning per armory law (current: libimobiledevice 1.4.0 / libplist 2.7.0 / usbmuxd 1.1.1 stack) |
| `bridges.checkm8` | palera1n (primary, open, CLI) · checkra1n (Linux CLI headless) · ipwndfu (research) | cli + rig (DFU entry robot) | pwn DFU, boot ramdisk (palera1n CLI / custom via idevicerestore+libirecovery), agent deploy, FS image. Era gate enforced at registry level: ProductType ≤A11 or refuse |
| `bridges.gpu.ios_backup` | hashcat -m 14700/14800 + philsmd extractor (pinned) + Phone Breaker-class (licensed seat if procured) | cli, GPU rig (shares wave-04 hashcat bridge) | Manifest.plist → `$itunes_backup$` → wordlist/mask battery → recovered password → backup decrypt/restore |
| `bridges.rig.relay` | The DFU/button robot — SAME USB relay board as the Android Download-Mode rig (wave 03 §7.3: ~$20–40 board, CONFIDENCE: LOW on price) driving power/volume/side-button lines per model profile | rig serial | The DFU timing dance below |

**GrayKey/Cellebrite are NOT bridgeable** — LE-only contracts, dongles, human-GUI
workflows; they are the competition to out-wait (wave 08), never adapters in our
registry. Doctrine line: the universal system's iOS front = **libimobiledevice +
checkm8-class + Elcomsoft-class offline math + pairing records.**

### 9.2 The DFU entry robot (one rig, two worlds)
The DFU entry sequence is a timing dance — historically THE human bottleneck of the
checkm8 lane. The panel robotizes it:
- **Model profile:** per-ProductType JSON: ordered steps of {hold-set (side/vol+/vol−),
  duration ms, release-set, wait-for USB PID}. Example family (iPhone 8/X-class): quick
  Vol+ tap, Vol− tap, hold Side ~10s until screen black, then Side+Vol− 5s, release
  Side, hold Vol− ~10s more. CONFIDENCE: MEDIUM (canonical dance, verify per model at
  armory time; timings drift per generation).
- **Detection:** DFU enumerated as Apple USB PID 0x1227 (recovery/iBSS 0x1281 class) —
  read by libirecovery/usbmuxd; the bridge treats PID as the success oracle, retries
  with timing jitter on miss (the robot's loop, wave 03's mode-entry-verify discipline).
  CONFIDENCE: MEDIUM on PIDs (libirecovery-documented class; verify against live birds).
- **The relay board is shared** with the Android front: same GPIO/relay USB board, same
  driver contract, different model-profile library. One rig, two worlds — the
  economics that make a $30 board the lab's best dollars-per-door ratio.

### 9.3 Bridge priority order (what gets built first, and why)
1. libimobiledevice bridge (intake + pairing + backups on EVERY bird that ever arrives —
   the cheapest data the lab will ever collect).
2. Pairing-record store (PAIRING-1/2 laws) — an evening's work, pays forever.
3. DFU relay profile library for the sacrificial fleet (training ground).
4. checkm8 bridge (palera1n/ramdisk) on sacrificial birds only until skill-proven.
5. GPU backup lane (14700/14800) pinned into the wave-04 hashcat bridge.
6. MDM/activation intake branch (question router, not a bypass engine).
Every adapter lands with: registry entry, verification test (a known-good bird per
era), danger class (D0–D4), and evidence-ledger hooks (§10).

---

## 10. LAWS CARRIED (iOS EDITION)

- **CROWN (GATE-17.14):** the owner's body is never a key. On iOS this bites hardest at
  Face ID/Touch ID (§1 #2): owner biometrics are crown-forbidden plans, and post-reboot
  they are technically dead anyway. No owner credentials ever: the iCloud lane (§5.2d)
  opens ONLY with operator-owned accounts — a different mission door, logged separately.
- **THE ARTIFACT LAW (iOS form):** the SEP is the boss — but the BACKUP is the artifact
  we can compute. When the silicon wall is absolute, the panel pivots to the format
  Apple made offline-verifiable (§6) instead of pretending the wall is soft.
- **THE GLASS LAW (iOS-hardened):** no guessing at the glass. iOS throttling (SEP-owned,
  persisted, escalating to 1h-per-try and disable/erase) is a harder siege than
  Android's; the panel brutes ARTIFACTS (backup passwords on GPUs) and never lock
  screens. GATE-17.13's iOS translation.
- **EVIDENCE LAW:** extraction proof = class-kvdiff + backup manifest — every extraction
  writes (a) the per-protection-class key/value diff of what was reachable vs not
  (the class ledger: None/AFU/Complete percentages), (b) the backup Manifest.plist/Manifest.db
  (file list + per-file metadata blob incl. protection class + the BackupKeyBag the
  artifact attack runs on). Together they make an extraction reproducible and honest
  about what it did NOT get — the iOS evidence pair.
- **SCOPE GUARD (iOS form):** sacrificial birds (the §4.7 fleet) for anything
  destructive or one-way: ramdisk experiments, DFU drills, relay-timing development,
  passcode-counter experiments. LO's personal bird and any data-sacred arrival: D0
  reads and pairing only; every D1+ step requires the danger-class gate.
- **PAIRING-1/2:** never lose pairing records; pre-pair at intake when the state allows.
- **ACTIVATION HONESTY:** a BFU + activation-locked bird is a parts bird — say it in
  the intake report, don't burn weeks pretending otherwise (§8.2).

---

## 11. iOS VERDICT — THE HONEST CAPABILITY LINE

The table the whole wave builds toward. Arrival state × hardware era, one verdict each:

| Arrival state × era | Verdict | The door that works (or the sentence that doesn't) |
|---|---|---|
| AFU + paired (or pairable) — ANY era incl. A12+ | **STRONG (ALIVE)** | Full logical backup + media + crash/syslog via pairing; ramdisk/agent paths on ≤A11; on jailbroken A12+≤16.x: Filza/keychain class. The quiet 80% — same as Android map §5 point 2 |
| AFU, unpaired, passcode-known-by-nobody, ≤A11 | **CONDITIONAL→STRONG** | checkm8: pwn DFU, boot agent/ramdisk, image reachable classes; passcode siege only as timer job |
| AFU, unpaired, nobody, A12+ | **CONDITIONAL** | Depends on jailbreak/exploit window per iOS build (Dopamine/TrollStore class); else None-class-only + hope for a backup artifact elsewhere (§6.5) |
| BFU locked-since-boot, ≤A11 | **CONDITIONAL (checkm8)** | Ramdisk + agent: None + (if previously-unlocked-once data sealed post-reboot — treat as BFU) limited classes; A11-on-14+ BPR wrinkle (§4.2) makes it passcode-removal destructive → sacrificial-or-consent only; keychain subset; NOT a passcode break |
| BFU locked-since-boot, A12+ | **NEAR-DEAD** | The §5 wall: SEP unbroken publicly, no offline artifact, throttle siege forbidden by doctrine. Doors: backup artifact from elsewhere (§6), cloud-with-credentials (exception), MDM code path if fleet bird. Otherwise: WAIT — for an AFU state, a future exploit, or a sourced backup |
| Disabled (not erased), any era | **CONDITIONAL** | = BFU + a timer. Same lanes as BFU rows; erase-at-10 risk makes glass siege doubly forbidden |
| Erased/wiped + activation-locked | **DEAD — PARTS BIRD** | §8.2 verbatim. Salvage: sacrificial fleet, silicon bench, secondhand market value only |
| Wiped, NOT activation-locked (owner-less) | **CONDITIONAL** | Reactivates as a fresh bird — useless for old data (keys destroyed), useful as a training bird |
| MDM-locked (fleet, no activation lock) | **CONDITIONAL** | Bypass code path (§8.3) if procurable; stale-build profile-removal chains verify-then-use; current builds = usually a wall |
| iCloud-gated data, account unknown | **DEAD (crown)** | Not a door for the panel — the account is the owner's credential-space; operator-owned accounts are the only cloud lane |

**The bridge priority order for the lab** (§9.3 restated as the verdict): libimobiledevice
→ pairing store → DFU relay library → checkm8 (sacrificial) → GPU backup lane → MDM/activation
intake branch. GrayKey/Cellebrite-class remain human/LE instruments — admired, mapped,
not bridged.

**The strategic sentence:** Apple's iOS is the one ecosystem where the wall is real —
so the universal system's iOS front wins by SHAPE, not force: it owns the unpatchable
base (checkm8 ≤A11 forever), the cheapest intake in the business (pairing records), and
the only offline-mathematical artifact (the 0x309 backup) — and it classifies every
other bird honestly, in minutes, without pretending.

### WHAT THE LAB BUILDS FIRST (the 10-line order)
1. libimobiledevice bridge on the Windows rig (usbmuxd via Apple Mobile Device Support) — intake recon on any bird, day one.
2. The pairing-record store: lockdown snapshots, UDID-indexed, versioned — the keys we never lose (PAIRING-1).
3. Intake state machine: ChipID + ProductVersion + ActivationState + pairing status → verdict row of §11, auto-selected.
4. One sacrificial iPhone 8/X (~$40–120, LOW) + Lightning cables + USB relay board (shared with the Android rig).
5. The DFU entry robot: per-model timing profiles, PID-oracle detection, jitter-retry loop.
6. palera1n CLI pinned in the armory; ramdisk boot drills on the sacrificial bird until boring.
7. philsmd's itunes_backup2hashcat + hashcat -m 14700/14800 pinned behind the wave-04 GPU bridge; bench the panel's card, store the real H/s in the registry.
8. Backup-restore rehearsal: cracked-password backup → restore to the spare bird → verify data classes landed (the finisher proof).
9. MDM-vs-activation intake branch with the bypass-code question router (§8.3).
10. Evidence ledger hooks: class-kvdiff + Manifest.plist capture wired into every adapter from the first day — extraction proof is part of the extraction, not a report written after.

---

## SOURCES — REAL TOOLS, PRICES, AND CLAIMS CHECKED THIS WAVE
Primary/product: libimobiledevice.org (full release/tool matrix, Windows usbmuxd note,
idevicerestore bootrom-exploit line) · checkra.in FAQ (A11 BPR/passcode note) ·
github.com/palera1n/palera1n + theapplewiki.com/Palera1n (A8–A11/T2, iOS 15+, rootless/
rootful, lineage) · theapplewiki.com/Checkm8_Exploit (CVE-2019-8900, device matrix) ·
elcomsoft.com / us.elcomsoft.com (EIFT product + 8.0 press release, checkm8 ramdisk
extraction) · support.apple.com/en-us/108934 (activation lock) · cellebrite.com/premium
+ premium-advanced-access ("unlimited lawful access") · magnetforensics.com/products/
magnet-graykey. Reseller/price: arsdigitalforensics.com (EIFT $2,199 listing) ·
govtribe.com POs 15DDB024P00000056 ($11,820 DEA, 2024) + 15DDM122P00000041 ($12,410
FLETC, 2025) · civiciq.com + sherlockforensics.com (UFED/Premium price bands) ·
vice.com (GrayKey $18k/yr online tier) · imore.com (Turbo brute marketing). Research/
attack: zimperium.com checkm8 analysis (SEP not compromised) · philsmd/itunes_backup2hashcat
(14700/14800 + keybag parse) · hashcat.net forum thread-6047 (0x29 10k iterations, tools
need only Manifest.plist) · elitedigitalforensics.com (iOS 10.2+ 10M iterations) ·
leminlimez gist "deep dive into the iOS backup/restore system". Community/verification:
Reddit r/jailbreak_ hhijgy (SEP throttling, checkm8-vs-SEP) + palera1n beta threads ·
simplemdm.com (MDM bypass code) · unloky.com (GSX scam reality) · jailbreakly.com +
idevicecentral.com (tool matrices) · ebay/swappa/alibaba marketplace skim (sacrificial
fleet pricing). Claim audit: "Sarah Jamison A10 fuzzer" — zero DDG results this wave;
treated as folklore, CONFIDENCE: HIGH on absence.
