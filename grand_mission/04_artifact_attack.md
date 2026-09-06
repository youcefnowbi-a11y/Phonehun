# THE CREDENTIAL ARTIFACT ATTACK — W2b
*Grand Mission 04 · DroidCommand / Vesper · deepens W1a §2g into full doctrine.
Laws carried: GATE-17.13 (credential = state), GATE-17.14 (THE CROWN), GATE-17.15 (THE INTERIOR).
Bird of record: SM-A217F (Exynos 850, Android 12, pattern lock, 3 fingerprints, BL locked,
shell-only access — recon proven in `_research/brain.log` 2026-09-06).*

Verification basis: AOSP docs (Gatekeeper/Weaver pages), Quarkslab "Android Data Encryption
in depth" (REcon'23 — includes working PoCs on Samsung A22-class TEEGRIS devices, the
bird's silicon sibling), repo-primary code audit of `tools_clone/LockKnife-main` (bruteforce.rs,
gesture.rs read line-by-line), hashcat example-hashes + hashidentifier confirmations,
plus `_research/brain.log` on-bird evidence. Confidence flags per row; LOW/MEDIUM = memory
or single-source, HIGH = primary code/doc in hand or on-bird proof.

---

## 1. THE ARTIFACT INVENTORY

**Master table — every credential artifact, its format, its crypto role, its privilege bar.**

| Artifact | Path (A12-era) | Format / contents | Crypto role (WHY it locks) | Read requires |
|---|---|---|---|---|
| locksettings DB | `/data/system/locksettings.db` (+`-journal`) | SQLite. `credential` table (user, type, owner, alias, version, blob); legacy `locksettings` key-value rows (`sphandle` etc.); `sparePasswords` table (managed-profile spare credential, work-challenge era) — CONFIDENCE: MEDIUM on exact columns, HIGH on password_type + SP-handle presence | THE TRIAGE ARTIFACT: `password_type` (pattern vs PIN vs password int per build) + SP handle pointers. Contains no recoverable secret itself; it sizes the candidate space and names the protectors | root (proven: shell sees 20480B metadata only, `cat` denied — brain.log 02:09:30) |
| SP protector blob | `/data/system/users/0/spblob/` (CE twin, bird-proven denied) and `/data/system_de/0/spblob/` (DE twin, Quarkslab-confirmed path) | SyntheticPasswordManager blobs: `<handle>` SP wrapper (dual-AES-GCM), `<handle>.weaver` (slot pointer: slot# + version), `<handle>.sp` metadata. Version-tagged headers, parse-don't-assume | THE KEY WRAPPER: SP is the random master secret that derives CE keys; the blob is SP sealed under (a) TEE Keymaster SID-bound key, (b) credential-derived key. Unwrap chain = the lock | root, or recovery BFU (DE twin only) |
| GK password handles | `/data/misc/gatekeeper/` per-user dirs (older variants: `/data/system/gatekeeper.*.key` — CONFIDENCE: MEDIUM) | GateKeeper handle blob: version byte + secure_user_id + 16B salt + scrypt params + HMAC-SHA256 of stretched credential, keyed by a TEE-internal secret | THE VERIFIER: enroll = HMAC(scrypt(credential, salt), TEE_KEY). The handle is a *proof*, not the key — but with the TEE key it is the offline oracle | root, or recovery BFU (dir is DE-resident) |
| Weaver slot table | Pixel-class only — Titan M flash / RPMB, NOT `/data`. On-device pointer: `<handle>.weaver` in spblob dir | Slot n → { key(16B), value(16B), throttle state } | THE THROTTLE VAULT: weaverKey = SHA512("weaver_key" ∥ token); chip returns value only on key match, throttles on miss | chip read (Titan M exploit class) — file pointer alone yields nothing |
| Legacy pattern | `/data/system/gesture.key` (≤ Android 5.x) | 20-byte SHA1 of dot-index byte string | Raw unsalted hash — instant offline crack, whole 389k space | any flash read |
| Legacy PIN/password | `/data/system/password.key` (≤ Android 5.x; Samsung SHA1-MD5 lineage → hashcat 5800) | SHA1-style lockscreen hash | Pre-TEE verifier, no stretch | any flash read |
| FDE footer | `crypto footer` on FDE-era (5.x–7.x) userdata | PBKDF2-stretched disk key verifier + encrypted master key | hashcat 8800/8900 target; TEE-independent | any flash read |
| Keystore blobs | `/data/misc/keystore/` (app keys, DE/CE per key) | Keymaster-wrapped key blobs — ciphertext, keys never leave TEE | NOT attackable offline: blobs are AES-wrapped by hardware-held keys; this is the wall, not the door | root reads ciphertext — worthless without TEE |
| TEE secure storage | TEEGRIS `tzar.img` root FS / RPMB (Samsung); Trusty fs / RPMB (QCOM) | GK HMAC keys, Keymaster keys, SID state | THE ROOT OF THE LOCK — key material lives here, never on `/data` | TEE exploit only |

**Samsung A12-era variant stack (the bird's exact stack):**
- TEEGRIS (Samsung's TrustZone OS) runs the GK TA — with a **custom KDF in the TEEGRIS
  crypto driver**, not the AOSP Trusty HMAC (Quarkslab/keybuster finding, CONFIDENCE: HIGH
  — research in hand). Consequence: the lab's GK verifier needs a Samsung variant, not
  the AOSP one.
- No Weaver (no Titan M on Exynos 850) → throttling is GK-internal in TEEGRIS →
  fallback path only, per W1a layer 4.
- No Knox Vault (discrete SE ships S21+ class) — the bird has plain TEEGRIS on-die.
- FBE with `fileencryption` ice/a variants (W1a A1C note) — per-file keys, DE + CE trees.

**Schema notes for the parser (section 4 feeds on this):**
- `password_type` ints drift per build (PIN/pattern/password/passcode-6, A14+) — decode via
  per-version catalog, never hardcode. The KEY output: it picks the candidate generator.
- `sparePasswords` rows exist on managed-profile-era builds — a second verifier target
  with often-weaker policy (CONFIDENCE: MEDIUM).
- The 20480B file the bird exposes is the system-user db; 3 enrolled fingerprints live in a
  different artifact entirely (biometric templates under `/data/vendor/` + GK biometrics-
  SID) — and per layer 2 they never unwrap keys; crown-irrelevant except as keyguard
  convenience state.

---

## 2. THE CRYPTO INSIDE

**Enrollment (what happens when the owner sets a PIN):**
```
stretched = scrypt(credential, salt, N, r, p)          # params+salt stored in the handle (DE file)
pwd_blob  = stretched ∥ prehashedValue                 # prehashed flag per credential class
handle    = { version, secure_user_id, salt, scrypt_params,
              HMAC_TEE_KEY(pwd_blob) }                  # TEE_KEY never leaves the TEE
```
The blob is the VERIFIER, not the key. Verifying a candidate = recompute scrypt + HMAC
inside the TEE. The TEE also enforces the throttle (fail-count → timeout escalation),
which is why on-device guessing is dead (W1a §2g) — and why a COPIED blob has no throttle.

**SP derivation chain (what the credential actually buys):**
```
token        = scrypt(credential, salt, params)                 # same stretched token
GK path:    applicationId = token ∥ prehashedValue
Weaver path: key = SHA512("weaver_key" ∥ token) → chip slot read → secret
             applicationId = token ∥ SHA256(weaverSecret)
SP unwrap:   intermediate = AES-GCM-Dec(SPBlob, TEE_KEYMASTER_KEY, auth=SID token)
             syntheticPassword = AES-GCM-Dec(intermediate,
                                  key = SHA512("application_id" ∥ applicationId))
CE keys:     SP → Keymint-wrapped per-file key derivation → fscrypt CE master keys
```
(AOSP + Quarkslab, both in hand. The AES-GCM tag IS the oracle: wrong credential → tag
mismatch → silent reject. No timing side-channel, no partial plaintext.)

**Why off-device cracking bypasses throttling entirely:** the throttle lives in the TEE
verifier's fail-counter — on-device calls. A copied handle has no TEE attached; the lab's
verifier calls scrypt+HMAC as fast as silicon allows. The attacker trades TEE-throttling
for scrypt-cost — the ONLY remaining speed limit is the KDF work factor (this is the whole
economic engine of sections 6 and 8).

**What success gives:** credential recovered → boot the phone NORMALLY → first-unlock
mounts CE → full AFU session → data (plus every auth-bound key the OS then unwraps itself).
The system does the decryption for us; we never touch FBE math post-recovery. This is the
crown-compliant finish: the credential is a state we COMPUTE, then the SYSTEM consumes it.

**The TEE-key problem — the honest wall in the chain:**
- GK HMAC verification requires the TEE's secret key → a raw copied handle is NOT
  independently verifiable off-device. Quarkslab's PoCs solved it by patching the TEEGRIS
  GK TA (accept-any → auth token) and leaking the Keymaster first-decrypt intermediate via
  Frida on `SyntheticPasswordCrypto.decryptBlob` — then brute-forcing offline against the
  *credential-derived inner wrap only*. That intermediate leak is the difference between
  a dead artifact and a live one. On-device root + hook, or a TEE exploit, stands between
  the lab and the inner-oracle. CONFIDENCE: HIGH (working PoC, Samsung A22 class).

**Pattern-space vs PIN-space math (scrypt N in the 2^14–2^15 class, parse per-blob;
CONFIDENCE: MEDIUM on exact defaults, HIGH on method):**

| Credential | Space | CPU box (~1k/s) | Single GPU (~10k/s optimistic) | 4-GPU rig (~40k/s) |
|---|---|---|---|---|
| 4-digit PIN | 10^4 | ~10 s | ~1 s | <1 s |
| Pattern 3×3 (legal, jumps) | 389,112 | ~6.5 min | ~39 s | ~10 s |
| Pattern 3×3 (naive 9!) | 362,880 | ~6 min | ~36 s | ~9 s |
| 6-digit PIN | 10^6 | ~17 min | ~100 s | ~25 s |
| 8-digit PIN | 10^8 | ~28 h | ~2.8 h | ~42 min |
| 4×4 pattern (16!) | 2.09×10^13 | ~243 days | ~24 days | ~6 days |
| 8-char alnum | 2.18×10^14 | ~6.9 yr | ~251 days | ~63 days |
| 12-char random | 5.4×10^23 | dead | dead | dead |

Reading: no key stretching SAVES a small space — scrypt multiplies the cost per guess,
it cannot rescue a 10^4 or 389k space. The bird's pattern is minutes of math. The wall is
only real at alnum-class credentials. Wordlists first (birthdays, repeats, years) collapse
PIN spaces by orders of magnitude — intel before brute, always.

---

## 3. THE TOOLING LANDSCAPE

**Boxed crackers — what exists, what it actually covers:**

| Tool / mode | Covers | Why it does NOT cover GK-era | State |
|---|---|---|---|
| hashcat **-m 5800** (Samsung Android PIN) | Legacy Samsung SHA1/MD5 lockscreen hash (pre-2014 fleet) | No scrypt, no HMAC, no SP | Maintained, active. CONFIDENCE: HIGH |
| hashcat **-m 8800** (Android FDE, Samsung) | FDE footer: PBKDF2-HMAC-SHA256 disk-key verifier (5.x–7.x) | FDE-era KDF; no SP, no GK | Maintained. HIGH |
| hashcat **-m 8900** (Android FDE generic) | FDE footer variants (PBKDF2 lineage) | Same era boundary | Maintained. HIGH |
| JtR jumbo `fde` format | Same FDE footers, CPU-side | Same | Maintained. HIGH |
| JtR jumbo `androidbackup` | ADB-backup AED PBKDF2 | Backups, not locks | Maintained. MEDIUM-HIGH |
| Raw SHA1 (any cracker) | `gesture.key` ≤5.x | Legacy-only | Trivial. HIGH |

**Different family — on-device oracle (throttle-respecting, NOT offline):**
- **Android-PIN-Bruteforce** (urbanadventurer; ~1.2k stars; era: Kali NetHunter HID, OTG
  keyboard emulation, stop/resume around the backoff schedule; archive snapshot 2021-03).
  It types PINs at the glass and waits out throttling — days-to-weeks per 4-digit PIN.
  The SBC 2024 paper (Nunes & Schneider) refined it: brightness-based unlock detection,
  66% of 18 devices in ≤2 weeks. Role in this doctrine: fallback siege for SHORT pins on
  stale fleet when artifact read fails; NEVER the primary for the lab. CONFIDENCE: HIGH.

**Bespoke verifier class — the actual GK-era landscape (surveyed):**

| Repo | What it is | GK-era reality | Maintenance | Confidence |
|---|---|---|---|---|
| `LockKnife` (ImKKingshuk; cloned at `tools_clone/LockKnife-main`; v1.1.0 2026-04-20, GPL-3.0, Python+Rust) | Unified Android forensic toolkit; `crack pin/password/gesture` subcommands, Rust core (rayon) | **ZERO.** Code audit (bruteforce.rs, gesture.rs): raw SHA1/SHA256/SHA512 over candidate strings; gesture = SHA1 DFS with a correct 3×3 jump table — i.e., legacy `gesture.key`/`password.key` math only. No scrypt, no GK HMAC, no SP parse. Claims in README about "modern credential storage" = device-side extraction helpers, not verifiers | Active (rapid release cadence, CI, fuzz targets) | **HIGH — source in hand** |
| Quarkslab REcon'23 PoC code + `titanm/nosclient` | The working GK/Weaver offline brute (Samsung A22 TEEGRIS + Pixel Titan M). Published brute pseudocode is the verifier blueprint | Real, but each run needs a per-device TEE exploit/root+hook chain to feed the Keymaster intermediate / chip key | Research-grade, per-device, expert-only | **HIGH** |
| `blackshibe/android-fbe-decrypt` | Honest failed-attempt notes: "extract device keys, brute separately" | Documentation of the wall, not a tool | Dormant | MEDIUM |
| `MissMyTime/spblob-rescue` | Offline spblob handle-switcher for broken-FBE rescue (switches active protector to backup key) | Parses spblob structure — useful parser knowledge, no cracker | Niche/active-ish | MEDIUM-HIGH |
| `shakevsky/keybuster` (+ writeup) | TEEGRIS crypto-driver reverse engineering | The Samsung TEE KDF map — feed for a TEEGRIS GK verifier | Research | HIGH (existence) |
| `gatekeeper-bruteforce`-class name-only repos | Various small scripts claiming GK brute | None verified to implement the HMAC/scrypt chain correctly; treat as folklore until code-audited | Scattergun | LOW |

**The honest verdict:** NO boxed, maintained GK-era SP+Weaver module exists publicly. The
Veracrypt-style convenience never happened for Android's SP chain because the verifier's
TEE key makes naive porting impossible — every real implementation is an exploit-fed,
per-device bespoke. **This is a BUILD item, not a BUY item.** The lab's build starts from
Quarkslab's published math + LockKnife's parser scaffolding + its own TEEGRIS KDF variant.

---

## 4. THE BESPOKE VERIFIER SPEC

**Codename: WEAVERMATH-1. Engineering spec, S/M/L per component.**

**Inputs:**
- Artifact set (per §1): locksettings.db, spblob dir (DE twin first), GK handles, weaver
  pointer if present, plus the leaked Keymaster intermediate (the TEE feed — acquisition
  problem, §5/§6) or TEE-exploit material per device class.
- Metadata: `password_type` → selects generator. Auto-detect is frontier (a), §10; v1
  takes it as a flag and falls back to all-generators when unknown.

**Verifiers per artifact class:**
| Class | Verify | Needs | Effort |
|---|---|---|---|
| Legacy gesture.key | SHA1(candidate_bytes) == hash | Nothing | **S** (exists in LockKnife — correct jump table, reuse) |
| Legacy password.key / 5800 | mode-5800 math | Nothing | **S** (call hashcat) |
| FDE footer | 8800/8900 math | Nothing | **S** (call hashcat/JtR) |
| GK handle (Trusty HMAC) | HMAC_TEE_KEY(scrypt(cand)) == stored — TEE key REQUIRED | TEE key leak / emu | **M** |
| GK handle (TEEGRIS custom KDF) | keybuster-documented KDF variant | TEE key leak + KDF port | **M-L** |
| SP inner wrap (the workhorse) | AES-GCM-Dec(intermediate, SHA512("application_id" ∥ token∥prehash)) — tag match = HIT | Keymaster intermediate (root-hook or TEE exploit feed) | **M** |
| Weaver slot | SHA512("weaver_key" ∥ token) == leaked chip key | Titan-M-class chip read | **S** (given the key) |

**Candidate generators:**
- Pattern enumerator: 3×3 adjacency (jump table: midpoints 2/4/6/8 + diagonals through
  5), 4–9 dots, no revisit → exact 389,112 ordering, breadth-first by human likelihood
  (length ≥4, corners-first priors). Effort **S**.
- PIN spaces: 4/6/8/10-digit, ascending, wordlist-priority queue (dates, repeats,
  keypad-shapes: 2580, L-shapes) before sequential. Effort **S**.
- Password: rockyou-class dicts + mangling (best64 rules) + corpus-derived priors (§10c).
  Effort **M**.

**Runner (hashcat-style):** CPU thread pool (scrypt is memory-hard — GPU-hostile; huge-
page scrypt, ~32–64MB/guess at AOSP-ish params, core-count scaling), OpenCL backend for
legacy/hash-light classes, checkpoint/resume (state file per 10^4 candidates), live rate
+ ETA + coverage reporting, kill-switch on hit. Effort **M**.

**Output law (per credential):**
```
PIN: 1234
PASSWORD: <string>
PATTERN: 1-2-5-8-9   →   [1] [2] [3]
                        [4] [5] [6]
                        [7] [8] [9]
```
**On-device verification protocol (GATE-17.13, the 2-attempt law):** the recovered
credential is entered at the glass a MAXIMUM of twice. One clean hit → evidence frame
(screen capture of unlocked home) → ledger. Two misses → verifier bug, artifacts
re-audited, NO third attempt (throttle/wipe risk). Success proof = the phone itself
mounting CE, not our math.

**Dev effort ledger:** parser+catalog M (the long pole — §10d version drift), generators S,
verifiers M (TEE feed is the variable), runner M, output S. **Total: 3–6 focused dev-weeks
to first working chain on a TEE-fed sacrificial bird.**

---

## 5. ARTIFACT ACQUISITION — THE PRECONDITION CHAIN

**The critical CE/DE resolution (the nuance the map flagged — resolved per component):**
- `/data/misc/gatekeeper/` and `/data/system_de/0/spblob/` are **DE** (direct-boot readable).
- `/data/system/locksettings.db` and `/data/system/users/0/spblob/` sit in the **CE** tree.
- Consequence: **the verifier material (GK handle + salt + scrypt params + SP DE blob) is
  largely DE-resident** — a recovery boot WITHOUT the credential can still feed the offline
  attack. The CE trap (W1a §2c) locks the DATA, not the credential artifacts. This is the
  single most important acquisition fact in the wave. (Quarkslab's chain starts from
  DE-protected files; bird log confirms only the CE twin's permission wall — both true.)
- BUT the artifacts are still *files on an FBE volume*: from a RAW image (no live OS),
  DE files are per-file-encrypted with DE keys → carving gives ciphertext. Raw readout
  without the DE key chain yields nothing readable (W1a §2e row 6). The silicon feed must
  therefore include key extraction (pre-boot dump class) or be a live/recovery read.

**Acquisition ladder (per method: preconditions / state / yield):**

| Method | Preconditions | Data-at-rest state | Yield for the attack |
|---|---|---|---|
| Shell (uid 2000) | Authorized ADB (bird: proven path) | AFU on bird | **Metadata only** — 20480B size, timestamps, denial walls. PROVEN DEAD on-bird |
| Root (`su`) on running system | Exploit or engineering build | DE+CE live-mounted | Full artifact copy (all classes) + Keymaster intermediate via Frida hook — the COMPLETE feed. Bird: no su — blocked |
| Custom recovery (TWRP-class) | Unlocked BL | BFU: DE tree readable, CE sealed | GK handles + spblob DE twin + params = verifier feed WITHOUT the credential. Bird: BL locked, Odin refuses unsigned — blocked |
| EDL 9008 + firehose | QCOM SoC + signed per-model loader | Raw partitions | Raw ciphertext — needs DE key chain added. **Exynos has no public EDL** — bird blocked (W1a §3 note) |
| mtkclient / BROM | MTK SoC, pre-auth window | Raw R/W + dump | Same — not the bird's SoC |
| ISP / chip-off raw image | Test points, reader | Raw NAND/UFS | Ciphertext only under FBE; pairs with per-device key extraction research. Bird: last-lane physical feed |
| Pre-boot key dump (CVE-2025-20435 class) | Vulnerable SoC (MTK ~875M-fleet class) | Keys dumped before Android loads | The full silicon feed: keys + artifacts → offline brute → ~45s-class full decrypt (CMF Phone 1 demo). **No Exynos public equivalent — bird blocked** |
| Samsung Download Mode + combination firmware | KG-state permitting + per-model combo | Combo flash usually wipes | Root-ish shell on SAME /data only if no wipe — rare; grey-market per-model. CONDITIONAL |

**Bird-of-record truth (A21s):** every acquisition lane is shut — BL locked, no root, no
public Exynos EDL/pre-boot dump, FBE per-file keys unextractable from raw image. The
artifact attack on THIS bird is acquisition-blocked, not math-blocked. Live lanes: AFU
arrival + authorized shell (exfil without the credential entirely), or a future TEEGRIS/
Exynos research break, or paid silicon service with key extraction. This matches W1a §3.

---

## 6. THE ATTACK FLOW

**Pipeline (intake → evidence):**
```
1 INTAKE      device ID + arrival state (BFU/AFU — W1a 4.8) + acquisition lane pick (§5)
2 EXTRACT     artifact copy (per lane) + hash everything (ledger opens)
3 PARSE       locksettings.db → password_type + handles; spblob parse; GK handle parse
              → verifier class chosen per artifact (§4 table)
4 SIZE        candidate space computed exactly; wordlist-priority queue built
5 DISPATCH    rig (CPU threads / GPU where the class allows); checkpointed; rate logged
6 CREDENTIAL  hit → output law (PIN:/PASSWORD:/PATTERN diagram)
7 VERIFY      on-device, ≤2 attempts (GATE-17.13); proof frame captured
8 UNLOCK     normal boot → CE mounts → the SYSTEM does the decryption
9 LEDGER     artifact hashes + candidate count + rate + elapsed + credential + proof frame
```

**Timing expectations per lock class (feed assumed complete):** pattern = minutes on CPU
(the bird's class — IF the feed existed); 4/6-digit = seconds-to-minutes GPU; 8-digit =
hours-days; alnum ≥8 = honest wall — go AFU/exploit/silicon instead. Strong passwords are
not beaten by rigs; they are beaten by feeds.

**Failure modes — the mission-critical truth table (TEE-independence of verification):**

| Artifact class | Off-device verifiable WITHOUT TEE exploit? | Why |
|---|---|---|
| gesture.key / password.key / 5800 / 8800 / 8900 | **YES** | Verifier math is fully in the artifact/footer |
| GK handle (copied) | **NO** | HMAC key is TEE-internal; a copy cannot self-verify |
| SP inner wrap | **CONDITIONAL** | Needs the Keymaster-decrypted intermediate (live root hook or TEE exploit) — then fully offline |
| Weaver slot | **NO** | Secret never leaves the chip; verify requires chip read (Titan-M-exploit class) |

Corrupt/truncated blob → parser rejects before rig burn (never brute a bad oracle).
Version drift → unknown handle version → catalog lookup → if unmapped, STOP and map it
(§10d) rather than emit silent false-negatives. The one unforgivable lab error is
burning rig-days against a misparsed scrypt param — params come from the blob, always.

---

## 7. iOS EQUIVALENT — BRIDGE TO WAVE 06

Passcode blob = PBKDF2 stretched, verified by the SEP (Secure Enclave); throttling inside
SEP hardware, same doctrine shape as GK. A12+ (SEP with PKe/fused key hierarchy): off-device
brute is DEAD — the blob verifies against a per-device key that never leaves the SEP.
≤A11: checkm8 bootrom exploit (uncurable) → custom ramdisk with patched SEP interaction →
on-ramdisk brute respecting/patching the counter (palera1n / Chimera lineage tooling state
carried by wave 06). Activation lock = separate cloud-plane gate, never a data key.
Android doctrine translation: Apple closed the same door earlier — TEE-independence (§6
table) is the whole story on both platforms. Wave 06 owns the depth.

---

## 8. ECONOMICS

**Rig costs (used market, 2025, CONFIDENCE: LOW — prices float):**

| Rig | Cost | Class | Role |
|---|---|---|---|
| Existing CPU box | $0 (sunk) | ~1k/s scrypt-ish | Pattern + 4-digit + wordlist PIN |
| Single used RTX 3060/4060 | ~$200–300 | legacy-hash classes, PIN at 10k/s-class | Entry GPU |
| Single used RTX 3090 (24GB) | ~$700–900 | high-memory KDF classes | The workhorse |
| 4×3090 rig + PSU/frame | ~$2,500–4,000 | ~40k/s-class on friendly params | The lab ceiling |

**Per-credential-class cost model (electricity ~$0.15/kWh, rig amortized over 2 yr):**

| Class | Time (4-GPU) | Cost/bird | Verdict |
|---|---|---|---|
| Pattern | <1 min | cents | Always attack |
| 4/6-digit PIN | seconds–minutes | cents–$1 | Always attack |
| 8-digit PIN | ~40 min | ~$1–5 | Attack |
| 4×4 pattern | ~6 days | tens of $ | Attack if case value high |
| 8-char alnum | ~60+ days | hundreds–thousands $ | Wall — don't price it, refuse the lane |

**Pricing an unlock (lab model):** cost = rig-hours(credential class) + acquisition cost
(lane from §5: shell $0 / root-exploit research / recovery $0 when BL-unlocked / ISP-chip
$50–300 outsourced / pre-boot-dump exploit: research capital). Pattern+root-shell bird =
minutes and dollars; pattern+ISP-silicon bird = hardware + days; alnum anything = the
honest no-sale. **Decision rule: attack math when the feed is complete and the space is
small; go silicon when the feed is missing; go home when the space is alnum-large.**

---

## 9. LAWS CARRIED

- **GATE-17.13 — credential-is-state.** The offline attack is MATH, not guessing: a
  deterministic enumeration of a finite, fully-defined space against a mechanical oracle.
  "Guessing as a plan" = typing at the glass hoping; this doctrine never does that. Every
  attempt is logged, counted, and reproducible.
- **The 2-attempt on-device law.** The rig may burn 10^8 candidates; the GLASS gets at
  most two. Verification is a ceremony, not a search.
- **GATE-17.14 — THE CROWN.** The recovered credential is used BY THE SYSTEM, owner
  absent, owner's body never a key or a fallback. Biometrics on the bird (3 fingerprints)
  are crown-irrelevant convenience state — never part of any chain.
- **GATE-17.15 — THE INTERIOR.** Artifact parse reasons from state (files, schema rows,
  handle versions), never from glass folklore.
- **Evidence ledger.** Per case: artifact SHA-256s, acquisition lane + timestamps,
  password_type, candidate-space size, candidates tried, rate, elapsed, recovered
  credential (per output law), on-device proof frame, operator notes. The unlock is only
  as real as its ledger.

---

## 10. OPEN FRONTIERS — WHAT NOBODY HAS BUILT

| # | Frontier | State | Why it matters |
|---|---|---|---|
| a | **Pattern-vs-PIN auto-detect** from locksettings metadata (type ints + handle lengths + prehash flag correlation) | Nobody ships it; schema drift makes it a catalog problem | Kills the biggest wasteful default (wrong generator = 10^4 space burned on pattern rigs or vice versa) |
| b | **Distributed cracking across panel + cloud GPU** — Vesper dispatches rig shards, merges checkpoints | No public Android-credential-aware scheduler exists | Turns 4-GPU lab ceiling into elastic rent; case-queue economics |
| c | **LLM-guided candidate ordering** — owner-context priors (birthdays, names, dates, keypad habits) mined from the HARVESTED CORPUS the lab already holds (SMS/contacts/media EXIF) | Research-class; LockKnife markets an ML password predictor (unaudited, LOW) | Order-of-magnitude convergence on PIN classes. **Doctrine position: fully inside GATE-17.13** — ordering a deterministic enumeration is still math; the corpus is already lawfully in lab custody; no oracle at the glass is touched |
| d | **Artifact-format version drift catalog** per Android release (locksettings schema, handle versions, spblob layout, TEEGRIS KDF variants) | Scattered across research repos; nobody maintains the matrix | The parser's long pole; without it every new bird is a reverse-engineering detour |
| e | **TEE-independent verifiability table per vendor** — which vendors' GK blobs verify off-device cleanly (Trusty vs TEEGRIS vs QSEE variants; Knox Vault vs on-die) | Never tabulated publicly | §6's truth table is the skeleton; the industry table would be the crown jewel — it prices every unlock before the rig spins |

---

## ARTIFACT ATTACK VERDICT

The honest capability line, 2025:

- **Wins outright:** every legacy class (gesture.key, password.key/5800, FDE 8800/8900) —
  instant on any flash read; every small-space credential (pattern 389k, 4/6-digit PIN)
  where the verifier feed is complete — minutes of math, twice at the glass, done.
- **Wins with conditions:** GK-era chains on devices where acquisition + one TEE-feed
  (root hook or TEE exploit) exist — Quarkslab proved the class on Samsung silicon; the
  lab must BUILD the verifier (no boxed module exists; LockKnife's marketing ≠ its math).
- **Loses honestly:** alphanumeric ≥8-class passwords (rig-time wall, not a doctrine
  failure — the answer is feeds: AFU arrival, exploit chains, pre-boot dumps); TEE-locked
  artifacts without an exploit feed (GK handle copies can't self-verify — the blob is a
  proof, not a key); Weaver-class chips without Titan-M-grade reads.
- **The bird (A21s):** math-ready (pattern = minutes) but acquisition-blocked on every
  lane (BL locked, no root, no Exynos EDL/pre-boot public path). Its unlock lives in
  arrival state (AFU + authorized shell), research (TEEGRIS/Exynos break), or paid
  silicon — not in the rig.

**Bottom line: this finisher wins wherever artifacts can be READ and the verifier's
TEE-independence holds; on the lab's own bird both gates are shut in 2025 — acquisition,
not mathematics, is the wall. The rig beats the glass every time it is fed.**
