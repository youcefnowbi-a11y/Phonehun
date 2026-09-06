# THE COMPETITION — W4b
*Grand Mission 08 · DroidCommand / Vesper · the complete landscape of who else can
unlock phones, what they actually do, what they charge, what they CANNOT do — and the
lanes where an LLM-driven autonomous lab leapfrogs every one of them. Builds on
00_CHARTER.md (laws, wave plan), 01_universal_door_map.md §6 (the players, named),
03_silicon_plane.md (T1/T2/T3 economics, loader reality), 05_vendor_chains.md (KG clock,
Xiaomi quotas, Transsion softness, the chain library), 06_ios_front.md (GrayKey/Cellebrite
pricing receipts, checkm8 estate, the SEP wall), 07_armory.md (the four libraries = our moat).*

Laws carried: GATE-17.14 (THE CROWN — owner absent, no biometrics/credentials ever),
GATE-17.15 (THE INTERIOR — reason from state, not glass), GATE-17.13 (credential = a
STATE, computed offline), SCOPE GUARD (data-sacred birds: recon only, nothing one-way).
Vocabulary inherited: ALIVE / CONDITIONAL / DEAD; planes glass→software→flash→silicon→cloud;
danger classes D0–D4. Confidence tags: **HIGH** (primary doc / multi-source / own PO
receipts), **MEDIUM** (press-verified or two good secondary sources), **LOW** (folklore,
price guess, single unsourced claim). Prices `~$` with tags; the gold receipts are the
06-wave POs (govtribe/federalcompass) and this wave's live fetches.

Verification base THIS wave (web_search dead in-session — DDG-HTML discipline
throughout): Upturn "Mass Extraction" full report (upturn.org, fetched 2020-report
corpus incl. the 76%-of-33 lab stat, the ~1,500 lock-bypass device figure, 2,000+
agencies / 50 states, per-agency spend $49k–$1.1M+, FBI 84 kiosk locations / 31,000
kiosk uses FY13–16, consent-search ratios); magnetforensics.com Grayshift LG/MediaTek
press ("Annual licensing… begins at USD $9,995" — PRIMARY); govtribe PO 15DDB024P00000056
($11,820 DEA, Sep-2024→Sep-2025, Magnet GrayKey license); federalcompass 70LGLY25PSSB00016
($12.4k FLETC Glynco, Mar-2025, Grayshift LLC) + 70CMSD25P00000130 ($90k ceiling, ICE HSI,
Sep-2025, Grayshift LLC); highergov ICE recompete forecast (~$5M GrayKey licenses, 8/2024);
article-factory ICE HSI summary ("licenses ranging from $12,000 to $145,000"); imore GrayKey
documents piece ($300/employee training); octoplusbox.com credits pages ($3.9–4.5/credit,
per-op consumption varies by model — PRIMARY); chimeratool.com/shop/credit-prices (PRIMARY,
prices login-gated); z3x wiki server-credits page; 404media leaked-docs piece + techdirt
(Cellebrite cannot unlock iOS 17.4+ locked iPhones, "In Research" — April-2024 leak,
verified by 404 Media); cellebrite.com blogs (66% of arriving devices locked; "Access Gap
Closed 2026" marketing); Ouedkniss live listings (Flash/FRP/schémas/MDM/KG 1000 DA; Samsung
MSL 2000 DA; MacBook EFI PIN 4000 DA — PRIMARY DZ receipts); German corpus
(freiheitsrechte.org RSF forensic-software PDF, KriPoZ Ludewig smartphone paper,
golem Cellebrite leak coverage). REFUSED/FAILED fetches (honesty ledger): zerodium.com
program.html (fetch failed ×2 — bounty figures cited from memory, LOW-MEDIUM);
cellebrite.com responsible-disclosure (CloudFront 403 geo-block — existence cited MEDIUM).
Folklore-name audit this wave: "Netburner" and "188A" as Cellebrite study names — ZERO
DDG hits (NetBurner is an embedded dev-board vendor); "Antrim" county audit not found —
Upturn's actual dataset names Anoka County (MN). Verdict: the brief's study-name shorthand
is folklore-class; the VERIFIED study corpus is Upturn 2020 + 404 Media 2024 + the German
parliamentary/KriPoZ class + Pinneberg ( LOW–MEDIUM, remembered figure, no live primary).
The <4%-class AFU failure figure below is tagged accordingly.

---

## 1. THE MARKET MAP — FOUR SEGMENTS, ONE ECONOMY

The unlock industry is not one market. It is four price universes stacked on the same
physical reality (locked phones), separated by WHO PAYS and WHAT THE BUYER NEEDS:
technical access (LE), re-usability margin (repair/refurb trade), one-off personal rescue
(consumers), and knowledge (research). Each segment's price floor and ceiling:

| Segment | Who they serve | Business model | Price band | Example anchor receipts |
|---|---|---|---|---|
| (a) LE/gov forensic giants | Police, intel, border, military, corporate security, DA labs | Annual per-seat licensing + dongles + support contracts + training; grant-funded procurement (JAG/ICAC/Coverdell) | ~$6k–$30k+/seat-year; agency cumulative $49k–$1.1M+ | Upturn 2020 (2,000+ agencies, 50 states); UFED/Premium bands 06; GrayKey POs below |
| (b) Box/service vendors | Repair shops, refurbishers, unlock-service resellers, the GSM trade | Hardware box/dongle (one-time) + activations/modules (per-brand) + server credits (per-operation) + loader-DB access | ~$100–$500 entry + $3.9–4.5/credit class ops | Octoplus credits page (PRIMARY); Chimera credit-prices (PRIMARY) |
| (c) Grey-market individuals | Walk-in owners, eBay/secondhand sellers, small shops outsourcing | Per-device/per-IMEI remote services, Telegram/XDA freelancers, credit-server arbitrage | ~$3–$50/op typical; scam density high | Ouedkniss DZ listings (PRIMARY); DC-Unlocker $10–100 (05); GSX-scam class (06 §8.2) |
| (d) Open-source | Researchers, tinkerers, labs like ours | $0 / volunteer-maintained; license quirks (edl GPLv3 + no-commercial clause) | $0 (+ hardware $3–200) | mtkclient/edl READMEs (03); palera1n/checkra1n (06); hashcat |

**The structural insight that runs the whole wave:** segments (a) and (d) touch the same
silicon with opposite economics — (a) sells LEGAL PACKAGING around a private exploit
estate, (d) gives the PROTOCOL away free. Segment (b) sells CURATION (the loader/pinout
libraries, 07 §4) around what (d) publishes. Nobody in any segment sells AUTONOMY. That
gap is §5 and §7.

### (a) The LE/government forensic giants

| Player | Flagship | Price reality (tag) | Notes |
|---|---|---|---|
| **Cellebrite** (Inseyets era) | UFED 4PC / Touch 2 / Premium + Physical Analyzer + UFED Cloud + Advanced Services | 4PC ~$6k–12k/yr; Touch 2 ~$15–20k/yr; Premium ~$15–30k/yr (MEDIUM — reseller bands via civiciq/sherlockforensics, 06) | The global default; deepest Android coverage; the LE market leader |
| **Grayshift → Magnet Forensics** | GrayKey (appliance + licenses) | Floor "$9,995" (HIGH, their own press page); $18k/yr online tier (HIGH, Vice 2019); POs $11.8k DEA 2024 / $12.4k FLETC 2025 (HIGH, gold receipts); ICE HSI $90k PO Sep-2025; ICE recompete forecast ~$5M; per-license band $12k–$145k (MEDIUM, article-factory) | The iOS brute specialist; §3 in depth |
| **Magnet Forensics** (pre-Grayshift-merger products) | AXIOM (analysis), GrayKey (acquisition post-merger) | AXIOM quote-based, four-figure/seat-year commonly reported (LOW) | The ANALYSIS half of the stack; also swallowed Grayshift (2022 merger) — consolidation wave |
| **MSAB** | XRY / XAM / XRY Kiosk | Quote-based; historically mid-four-figure (LOW) | Swedish mid-tier; kiosk lane for smaller agencies |
| **Oxygen Forensics** | Oxygen Detective + Cloud | Mid-band subscription (LOW) | Corporate/PI licensing lane Cellebrite avoids; Huawei-era strength faded |

Spend reality (Upturn, HIGH): 2,000+ US agencies hold MDFTs; agencies of 25k–50k
population spend $59k–$136k cumulative; state agencies $510k–$1.1M+; the FBI runs 84
kiosk locations, used 31,000+ times FY13–16; ~50,000 extractions logged by just 44 of
the 2,000 agencies 2015–2019 — "hundreds of thousands" total is the honest floor. The
LE market is a GRANT-FED procurement economy: "95 percent of our equipment comes from
outside funding" (agency quote, Upturn HIGH). Translation: (a) sells to buyers who do
not spend their own money — price insensitivity is structural, and the product's true
deliverable is COURT SURVIVABILITY, not raw access (§2).

### (b) The box/service vendors — the unlock-shop world

| Player | Entry price (tag) | Credit economics | Real moat |
|---|---|---|---|
| **Octoplus/Octopus** | Box/dongle ~$200–500 + activations (LOW) | Server credits $3.9–4.5/credit (HIGH, official page); per-op consumption varies by model (official FAQ); 1-day full license + 100 credits product exists | Curated leaked loaders + per-model methods; Samsung/LG/FRP lanes (their news feeds ship weekly per-model FRP updates) |
| **z3x (EasyJTAG/Samsung)** | Card ~$150–300 (LOW) | Server credits via wiki (PRIMARY page, prices gated) | Samsung depth + EasyJTAG ISP lane |
| **Medusa Pro (JTAG/ISP)** | ~$200–400 box (LOW) | Included ops + activations | Pinout database — thousands of boards (07 §4c) |
| **UFI Box / UFI II** | ~$100–200 (LOW) | Included + per-op service lanes | UFS service king, BBK-heavy refurb lanes |
| **Sigma / SigmaKey** | ~$100–300 (LOW) | Credit-class ops | MTK/QCOM/Broadcom service unlock heritage — the BROM lane's commercial face |
| **ChimeraTool** | ~$150–400/yr (LOW) | Credit prices page (PRIMARY, login-gated) | Explicit KG/RMM unlock functions (docs verified, 05); Samsung/Huawei repair class |
| **SamKEY / credit-server class** | ~$50–150 credit packs (LOW) | Pure remote credit ops | Samsung FRP/relock removal at distance |
| **DC-Unlocker** | $10–100/op (LOW, feature table 05) | Per-unlock credits | Modem/router/Huawei-class stopgap |
| **TSM-Tool (Transsion ecosystem)** | ~6 credits ≈ $3 direct unlocks (MEDIUM, hosbootloader 2025 table via 05) | Per-op credits | Carlcare-adjacent Transsion volume lane |
| **Hydra / CM2 (legacy MTK)** | ~$10–15 per pass (MEDIUM, same table) | Box-class | 2016–2021 BROM fleet in one pass |

### (c) Grey-market/individual — the freelance stratum
Per-IMEI SIM unlocks ($10–50), remote FRP services ($5–30), Telegram unlock brokers,
XDA marketplace freelancers, per-model combo-firmware sellers ($50–150, 05). The scam
density is a FEATURE of the price structure: GSX/activation "bypass" services are a
documented fraud class (06 §8.2, unloky myth-buster, HIGH); the honest stratum sells
exactly what (b) sells minus the box — credit-server arbitrage at retail markup. In the
DZ specifically, this stratum IS the walk-in market: Ouedkniss listings (PRIMARY, live
this wave): "Flash/Décodage/Google Frp/Schémas/Code/MDM/KG Locked/Knox — 1000 DA"
(~$7.5, Sidi M'hamed, Alger), "Deblocage samsung MSL — 2000 DA" (~$15, El Harrach),
"MacBook EFI PIN — 4000 DA" (~$30), flashage from 100 DA, carrier unlocks 1–9999 DA.

### (d) Open-source — the $0 lane
mtkclient (bkerler) + edl (bkerler) + bkerler/Loaders = the silicon spearhead (03);
palera1n/checkra1n/ipwndfu + libimobiledevice = the iOS bridge (06); hashcat/JtR
(modes 5800/8800/8900/14700/14800) = the offline math (01 §2g, 06 §6); Android-PIN-
Bruteforce (urbanadventurer) = the HID siege; FriTap/Frida = instrumentation; TWRP =
legacy recovery; LockKnife-class + blackshibe/android-fbe-decrypt = the artifact-attack
wrappers. All $0. License quirks recorded in the armory manifest (edl's no-commercial
clause, 07 §3c). The OSS lane's weakness is not capability — it is CURATION and
REPRODUCIBILITY: loaders are ragged, pinouts are folklore-scattered, and nothing turns a
one-off success into a repeatable operation. That weakness is exactly what 07's four
libraries exist to fix, and what segment (b) charges $100–500 to paper over.

---

## 2. CELLEBRITE IN DEPTH — THE GIANT, MEASURED HONESTLY

**Product stack:** UFED 4PC (software+dongle, per-seat), UFED Touch 2 (field tablet),
UFED Premium / the Inseyets-era tiers ("unlimited lawful access to iOS and high-end
Android" — cellebrite.com/premium, HIGH for the marketing text), Physical Analyzer
(decode/analysis), UFED Cloud (warrant-driven cloud pulls), Advanced Services (the
"send us the hard phone" lane).

**What UFED actually does per arrival state** (arrival-state doctrine is 01 §5 / 06 §2 —
the same AFU/BFU physics applies to everyone):

| Arrival state | UFED/Premium reality | Confidence |
|---|---|---|
| AFU, unlocked-since-boot, any modern device | Full filesystem + keychain-class extraction where the model is supported — the sweet spot; this is the state their marketing implicitly assumes | HIGH |
| BFU, credentialed, current iOS/Android | Per-build exploit windows only; the leaked April-2024 capability matrix says locked iPhones on iOS 17.4+ = "In Research" = CANNOT unlock; Android BFU depends on per-model loader/exploit estate same as everyone | HIGH (404 Media verified leak; techdirt/wccftech/3u corroborate) |
| Locked legacy/stale fleet | Their historical bread: ~1,500 devices with lock-bypass support added since March 2016 (Upturn, HIGH) — i.e., the estate is wide on OLD birds, thin on new ones | HIGH |
| iCloud/cloud-gated | Only via credentials/warrant — UFED Cloud is a legal tool, not a break | HIGH |

**Supported-method marketing vs measured reality.** The marketing says "unlimited
lawful access"; their own 2026 blog says 66% of devices arriving at the lab are LOCKED
and pitches exactly that gap as the thing Premium closes (cellebrite.com blogs, HIGH for
the quote). The measured reality, from the verified study corpus:
- Upturn 2020 (HIGH): one lab examiner — 25 of 33 phones (76%) extracted using UFED +
  GrayKey combined; ~1,500 lock-bypass devices since 2016; 28% of US smartphone users
  had NO screen lock at all in 2017 (the AFU/no-lock fleet does the heavy lifting);
  departments buy MULTIPLE vendors "to increase the likelihood that any given phone can
  be extracted" — the industry's own hedge against single-vendor gaps.
- 404 Media April-2024 leak (HIGH): iOS 17.4+ locked iPhones cannot be unlocked by
  Cellebrite; the matrix reads "In Research". Golem's coverage ties it to the FBI's
  Trump-assailant-phone episode: modern flagships beat the estate until a new exploit
  lands, then Apple patches, then the treadmill resumes.
- German corpus (MEDIUM for class, LOW–MEDIUM for figures): the Bundestag-adjacent
  forensic-software debate (freiheitsrechte.org RSF report), KriPoZ's Ludewig paper on
  smartphone seizure/evaluation, and the Pinneberg prosecutor-office study class
  reporting single-digit-percent FULL-data success on arriving locked smartphones.
  The "<4% AFU-era full-extraction" figure this mission's brief references belongs to
  this class; no live primary surfaced this wave, so it carries LOW–MEDIUM and the
  honest note that the trendline it describes (falling full-extraction rates on modern
  locked flagships) is corroborated by the 404 Media matrix and Upturn's multi-vendor
  purchasing behavior. The brief's "Netburner/188A" names: audited, zero hits, folklore.
  Anoka (MN) — the real county in Upturn's dataset — is likely the "Antrim" garble.

**Licensing model:** per-seat/year, dongle-bound, ~$6k–30k bands by tier (MEDIUM), sold
through procurement contracts and federal grants; training and certification billed on
top; Premium-tier sales are geographically/customer-class gated (not sold to everyone,
everywhere — the "authorized government" fence is part of the product).

**Why states pay the premium — the legal wrapper, not technical magic.** What Cellebrite
sells that no box vendor can: (1) court-tested chain-of-custody machinery — hash-verified
extraction logs, examiner testimony support, decades of precedent citing UFED outputs;
(2) audit trails that survive defense-expert scrutiny; (3) support contracts with SLAs
and per-firmware updates; (4) training/certification that makes any two examiners
produce comparable outputs; (5) procurement compliance (the grant economy's paperwork).
The technical delta vs a $200 box + OSS stack on a BUDGET-fleet bird is often near zero
(both ride loaders/BROM/AFU); on a modern locked flagship the delta is real but decays
with every patch cycle. The DURABLE delta is legal-evidentiary. That is the honest
boundary of the giant's moat — and it is a moat we do not need to beat to win our market
(§6–§8), only to replicate as a PRODUCT eventually (§7 lane 3).

**Their exploit-purchase pipeline.** Cellebrite runs a responsible-disclosure/bug-bounty
program (page geo-403 this wave; existence MEDIUM — industry-documented). The deeper
lane is the BROKER market: Zerodium-class players historically list mobile full-chain
RCE+LPE bounties in the $100k–$2.5M class (fetch refused ×2 this wave; figures
LOW–MEDIUM from memory, directionally solid). The giants buy 0-days through these
channels (and direct researcher relationships), feed them into Premium's per-build
estate, and amortize the cost across thousands of $15–30k seats. We do not buy 0-days
(SCOPE: the lab rides public exploits + unpatchable bases + state exploration — 01 §4,
03 §3.3); that is a deliberate lane choice, costed in §8.

---

## 3. GRAYSHIFT/GRAYKEY IN DEPTH — THE iOS SPECIALIST

**The receipts, in one table (this is the gold-standard price set of the whole wave):**

| Receipt | Value | Source class | Confidence |
|---|---|---|---|
| GrayKey annual license floor (iOS+Android tier) | **USD $9,995/yr** | Magnet/Grayshift's OWN press page (LG/MediaTek support announcement) | HIGH — primary |
| Online tier, historic | $18k/yr | Vice 2019 | HIGH for the report |
| DEA PO 15DDB024P00000056 | **$11,820**, Sep-2024→Sep-2025, single GrayKey license, Magnet Forensics | govtribe | HIGH — gold receipt (06) |
| FLETC Glynco PO 70LGLY25PSSB00016 | **$12.4k ceiling**, Mar-2025, Grayshift LLC | federalcompass | HIGH — gold receipt (06 + this wave) |
| ICE HSI PO 70CMSD25P00000130 | **$90k ceiling**, Sep-2025, Grayshift LLC | federalcompass | HIGH |
| ICE GrayKey recompete forecast | ~**$5,000,000** (multi-license) | highergov forecast | MEDIUM-HIGH |
| Per-license federal band | $12,000–$145,000 | article-factory ICE summary | MEDIUM |
| Training | $300/employee | imore GrayKey documents piece | MEDIUM |
| Army RFQ W9124925QA004 | "GrayKey Offline Premier" annual license, LPTA award | highergov | MEDIUM (existence; price not fetched) |

Reading: the single-seat federal reality clusters at **$11.8k–$12.4k/yr** (our anchor
band, HIGH), the vendor's own floor is **$9,995** (HIGH), and multi-seat/enterprise
deployments scale to $90k–$145k–$5M. Any "GrayKey costs $30k" folklore should be
retired: the 2024–25 price ladder is $10k–$18k for one seat, ~$9.5k historic Vice-era
tier at the bottom, $145k-class agency bundles at the top.

**What GrayKey does per iOS state** (06 §3/§4/§5 is the full doctrine; the competition
view compressed):

| iOS arrival state × era | GrayKey reality | Confidence |
|---|---|---|
| AFU, any era incl. A12+ | Full FS + keychain extraction on supported builds — genuinely strong; the license's bread | HIGH |
| BFU, ≤A11 (5s→X) | Their private checkm8+SEP estate: brute with private per-chip methods — the "4-digit in days" class numbers are THEIR estate, not public capability (06 §4.5); nobody outside can reproduce those rates | MEDIUM-HIGH (inference from marketing + 06) |
| BFU, A12+ | Mostly dark — the SEP wall (06 §5.1) holds against the public; GrayKey's estate churns per iOS release; "Turbo brute" marketing (imore) is a treadmill, not a key | MEDIUM-HIGH |
| Android | Weaker than Cellebrite historically; added LG/MediaTek at the $9,995 tier (their own press, HIGH); rides the same loader/method market everyone else does | HIGH on structure |

**The GrayKey estate concept** — the load-bearing idea for this mission: Grayshift's
moat is a PRIVATE EXPLOIT LIBRARY indexed per chip × per iOS build, cached on the
appliance, refreshed by their exploit-purchase pipeline, decaying with every Apple
patch. The famous ≤A11 brute rates and the "Turbo" tiers are outputs of that estate;
the magic numbers are private because the estate IS the product. Its structural
weakness, from the door map's perspective: the estate is a CLOSED MAP — every entry is
a named, bought method that dies by patch. An estate wins sprint races on fresh
flagships; an open state-explorer wins marathons on the installed base (§5, §7).

**The honest verdict on Grayshift:** on iOS they hold the ≤A11 magic + the AFU process
+ a live A12+ treadmill; on Android they are a me-too riding the same loaders market as
Octoplus — at 40–100× the price. Their post-2022 absorption into Magnet (Grayshift →
Magnet GrayKey product line, confirmed by every PO above) makes them the iOS acquisition
arm of an analysis-suite vendor, not a universal-system player.

---

## 4. THE BOX VENDOR ECONOMY — HOW THE DZ-SHOP WORLD ACTUALLY MAKES MONEY

**The stack of revenue, from vendor to counter:**

1. **Hardware/dongle (one-time):** ~$100–500 buys the box + the right to run the
   software (Octoplus box, z3x card, Medusa/UFI rigs — LOW bands). Dongle forgery is a
   documented nuisance (07 §3f) — the dongle is a license, not a tool.
2. **Activations/modules (per-brand/per-feature):** Samsung pack, LG pack, FRP pack —
   the segmentation that makes a "full" setup cost 2–3× the box.
3. **Server credits (per-operation):** $3.9–4.5/credit at Octoplus (HIGH, official);
   operations consume a MODEL-DEPENDENT number of credits (official FAQ language);
   z3x/Chimera run the same scheme (pages live this wave, prices gated behind
   login/cart). This is the meter: every Samsung relock removal, every "Reset FRP via
   Download Mode", every carrier decode on a current-patch bird burns metered credits.
4. **The loader-DB subscription (implicit):** what you actually renew each year —
   access to the curated, per-model firehose/V6-loader/method collection. Their
   release notes ARE the moat made visible: Octoplus ships weekly "Extended Reset FRP
   support… including 2026-07-05 patch level" updates (their own news feed, HIGH) —
   human curation chasing each Samsung security patch.
5. **The DZ service layer (on top):** the shop charges the customer 1000–2000 DA
   (~$7.5–15) per op (Ouedkniss PRIMARY), burns $4–15 in credits/box time on the hard
   ops, pockets the spread, and pays nothing for the wait-clocks it never runs.

**Their REAL moat — curation, not protocol.** The protocol layer is open (edl.py,
mtkclient — 03 §2.2/§3: "protocol is open per W2a"; the box vendors bundle leaked
loaders). What the $200–500 buys is a curated, tested, per-model loader+method database
with a support forum. That is EXACTLY the armory's loader library (07 §4a) plus the
Beagle-sniffing self-manufacture loop (03 §2.2: sniff a working box session →
`beagle_to_loader` reconstructs the loader from the wire — once seen, never bought
again). The moat is real but it is a LIBRARY moat, and libraries compound for whoever
walks the most birds (§10).

**Why they cannot scale to new chips fast:** human curation lag. A new MTK generation
(V6 class) or a new Samsung patch family means: a human obtains the loader/method,
tests it per-model, packages it, ships a release. Weeks-to-months per wave. The OSS
lane (bkerler/Loaders deltas) and the box lane converge on the same leaked sources;
whoever ingests faster wins coverage. An LLM-driven armory that ingests loader packs,
verifies hashes, regression-tests on sacrificial birds, and files per-model verdicts
in machine time is structurally faster than a release train — this is not speculation,
it is the 07 §8 uplink-window protocol already specified.

**The DZ service layer, stated as our market reality (LO's arena):** what walks into
an Algerian/maghreb shop: Transsion volume (TECNO/Infinix/itel — the softest fleet,
05 §6: sub-Saharan ~40%+ share class), Samsung KG-financed birds + FRP refurbs,
forgotten-pattern owners, carrier-locked handsets, iPhone activation-locked parts birds
(06 §8.2 — salvage class), the occasional MDM/enterprise casualty. Services at
1000 DA (~$7.5) for the flash/FRP/schéma/KG basket, 2000 DA (~$15) Samsung MSL, 4000 DA
(~$30) MacBook EFI (Ouedkniss live, MEDIUM-HIGH — listing prices, real market floor
may run higher in-shop; band $5–30/op matches 05's Carlcare/TSM reasoning). The shops
do one-off manual ops: no automation, no wait-clock patience (nobody parks a KG bird
168 h for free — 05 §9), no evidence discipline, no English docs. The autonomous panel
IS the productization of this layer (§6).

---

## 5. WHAT NONE OF THEM CAN DO — THE LAB'S SIX LANES

The honest gap analysis. Every capability below is absent from EVERY product named in
§1–§4 — verified against their marketing pages, POs, release notes, and tool docs this
wave:

**Lane (a) — NOBODY sells an LLM-orchestrated autonomous unlocker.** Every LE product
is a human clicking a wizard GUI (Upturn's UFED screenshots — "Select Extraction
Type" — are the whole UX model, HIGH). Every box is a human picking a model from a
list and pressing Start. Every script ecosystem (GSM forums, autoflashers) is a fixed
method list with no per-arrival reasoning. Nobody's product TRIES METHODS IN
COMBINATION against a live state machine, observes the result, and re-plans. The
charter's deliverable contract (00: "identified → swept → methods selected OR
INVENTED → executed autonomously → evidence written") has no commercial counterpart at
any price point. CONFIDENCE: HIGH (survey of the whole segment).

**Lane (b) — nobody does per-build binder/settings enumeration.** 01 §4.1–§4.2 is
the flagship unexplored frontier: `service list` + `service call` code sweeps,
settings-row write lanes with keyguard side effects, per-build permission drift. The
reason it is unmapped is economic, not secret: 100+ services × dozens of codes ×
per-build variance is too boring and too expensive for humans, and produces no
marketable bullet for a vendor deck. For a machine it is a weekend sweep that compounds
into the lock-signature library (01 §4.4: the state delta IS the lock). CONFIDENCE:
HIGH that the surface is unmapped (the door map's own §4 is this mission's original
contribution; no vendor ships anything comparable).

**Lane (c) — nobody combines open tools into novel chains (the compiler).** The
handbooks list ATOMS (mtkclient dump; combo flash; FRP erase). The unlocks that work
in 2025 are CHAINS (05 §8's S1–T3 are exactly this: BROM dump → artifact attack →
offline PIN → boot normally). No product searches chain-space per arriving device;
every product runs ONE named method per screen. The method-compiler concept (01 §4.6,
02's planner) is the LLM-native advantage: treat every verified state transition as a
node with preconditions/effects, search the graph per bird. CONFIDENCE: HIGH.

**Lane (d) — nobody runs wait-clock portfolio attacks.** KG PRENORMAL's 168-hour
uptime clock, Xiaomi's 72-hour bind + 00:00-Beijing quota windows, the KG 2-day
Completing cancel window (05 §9's clock table). A human shop cannot babysit 10 parked
birds for a week at $0 marginal — so it never does; the birds get turned away or
hand-reset. A scheduler that parks/resumes/probes in parallel converts dead wall-clock
into throughput at zero labor (05 §9's PARKED_<clock> spec). lokey0905's Xiaomi sniper
is the community's existence proof that automation wins these lanes; no PRODUCT
generalizes it. CONFIDENCE: HIGH.

**Lane (e) — nobody offers the evidence law as engineering.** Cellebrite's chain of
custody exists for LEGAL-admissibility reasons (court process, examiner testimony) —
it is packaging around the same hashes any pipeline can compute. NOBODY sells
hash-chained, reproducible, what-we-did-and-didn't-get PROOF as a first-class product
for the non-LE market: secondhand-sale disclosures, repair disputes, insurance claims,
inheritance cases, small-court matters. The 06 evidence pair (class-kvdiff +
Manifest.plist) and 07's manifest-reproducibility doctrine are that product waiting
to exist. CONFIDENCE: HIGH on absence; the market demand is MEDIUM (asserted from the
dispute/secondhand economy, not yet measured).

**Lane (f) — the pricing asymmetry.** Their ladder: $9,995–$145k/seat-year (LE) or
$100–500 + credits (boxes) for GUI-driven single-method ops. Ours: the 03 §9 T1/T2
stack — $0 software (mtkclient/edl/libimobiledevice/hashcat) + ~$50–200 cables/birds
— covering the SAME budget-fleet reality that generates the volume (§6's birds/month
math). The $0–500 autonomous stack serving 24/7 throughput is a category the price
ladder has no rung for. CONFIDENCE: HIGH on our costs; the comparison is arithmetic.

---

## 6. THE DZ-MARKET POSITION — LO'S ACTUAL ARENA

**What walks in (05 §6 + live Ouedkniss this wave):** the Algerian/maghreb unlock
economy is a Transsion-heavy, Samsung-refurb, forgotten-pattern market. Transsion
budget fleet (MTK/SPD, stale BSPs, glass-plane tricks ALIVE per 01 §2a) = the volume
spine. Samsung birds split into KG-financed (the wait-clock lane), FRP-locked refurbs
(the combo/EDL lane), and pattern-forgotten owners (the artifact-attack lane — 04's
offline PIN math on a BROM dump). iPhones arrive as activation-locked parts birds
(06 §8.2 verdict: salvage/sacrificial, honest parts-bird triage) and the occasional
AFU jackpot (pairing/backup lane). Carrier/SIM locks and MDM stragglers round it out.

**Current service prices (~, LOW–MEDIUM, receipts noted):**

| Service | DZ street price | Receipt class |
|---|---|---|
| Flash / FRP / schéma / code / MDM / KG basket | 1000 DA (~$7.5) | Ouedkniss live listing (Sidi M'hamed, Alger) — MEDIUM-HIGH |
| Samsung MSL decode | 2000 DA (~$15) | Ouedkniss live listing (El Harrach) — MEDIUM-HIGH |
| Transsion official unlock | $0–15 (Carlcare walk-in, ~1 h) / ~$3 (TSM-Tool) | 05 §6 (hosbootloader table) — MEDIUM |
| Carrier/SIM unlock | 1–9999 DA ($0.01–75); class ~$10–50 | Ouedkniss band + 01 §2f — LOW-MEDIUM |
| MacBook EFI PIN | 4000 DA (~$30) | Ouedkniss live — MEDIUM-HIGH |
| KG/RMM removal (hard Samsung) | ~$50–300 class | 05 (SamKEY/z3x/Chimera bands) — LOW |

**The gap the panel fills:** shops do ONE-OFF MANUAL OPS — a human, a box, a queue, a
closing time. No automation (each bird is hand-triaged), no evidence (no proof of what
was/wasn't done — disputes resolve by argument), no wait-clocks (KG 7-day birds get
refused or botched), no documentation in any language, no portfolio (one bird at a
time), no after-hours. The autonomous panel IS the productization: ONE operator +
Vesper = a shop that runs 24/7 on parked birds — intake robot files each arrival,
scheduler parks the clock-birds, chain-compiler walks the rest, evidence ledger writes
the proof, morning is for handing phones back and taking money.

**The market math — what the system needs to be worth building:**

| Line | Value | Notes |
|---|---|---|
| T1+T2 stack (03 §9) | ~$50–250 one-time + ~$30–80/sacrificial bird | Covers Transsion volume + QCOM loader lanes + HID siege + recon habit |
| T3 rig (optional, later) | ~$1–5k one-time | ISP/UFS/microscope/Beagle — unlocks Exynos artifact lane + loader self-manufacture |
| Marginal cost per walked bird | ~$1–8 (electricity + credits only where a paid lane wins; $0 on BROM/stale-fleet lanes) | The panel's whole thesis: marginal cost collapses |
| Average DZ street revenue/op | ~$7.5–15 (basket ops) | Ouedkniss anchors |
| Ops/month to clear T2 in 6 months | ~15–25 ops/month at $10 avg | $150–250/mo revenue vs ~$200 amortized T2 — hobby-positive, not salary |
| Ops/month with the 24/7 portfolio effect | 40–80+ (parked clocks + stale-fleet sweeps + overnight artifact attacks) | THIS is the unlock: the shop's throughput ceiling is the human; ours is the bench |
| Monthly at 60 ops × $10 | ~$600/mo revenue at ~85–95% gross margin | A DZ microbusiness; T3 amortizes in months; the compounding asset (loader/pinout/signature libraries, §10) is retained even if volume fluctuates |

Honest reading: at walk-in-only scale (15–25 ops/mo) the system pays for itself slowly
— worth building as the lab's training ground regardless (05 §6 doctrine: skills pay
rent on Transsion first). The REAL economics flip at portfolio scale: the same panel
that walks one bird walks ten parked ones overnight, and every walk deepens the
libraries that make the next bird cheaper. The DZ market alone justifies T1/T2; the
compounding moat justifies everything above it.

---

## 7. LEAPFROG STRATEGY — RANKED, COSTED, WITH TARGETS

**Rank 1 — the budget-fleet automation lane.** WHAT: intake-to-evidence pipeline over
the Transsion/stale fleet — auto-triage (BFU/AFU), BROM/EDL sweeps, stale-build glass
catalogue auto-applied per patch level (01 §2a), FRP/`e frp`/seccfg lanes scripted,
artifact dumps queued to the offline math. COST: T1/T2, ~$50–250 + birds (03 §9).
BEATS: box vendors' coverage lag (their release train vs our uplink-window ingestion —
§4), the DZ shops' one-off manual reality, and — on this fleet specifically — the LE
giants (who monetize the same birds at 1000× the price through grants). WHERE THE
VOLUME LIVES: this is the 90% market of §8.

**Rank 2 — the wait-clock portfolio.** WHAT: 05 §9's scheduler as a first-class module:
PARKED_<clock> states, uptime babysitting on bench power, 00:00-Beijing quota sniper,
KG 168-h portfolio, resume-on-observed-transition with evidence rows before every
destructive step. COST: $0 software + USB relay board (~$20–40) + bench power. BEATS:
every human shop (structurally cannot babysit at $0 labor) and every vendor (no
product even tries — the market's own refusal to serve the KG-financed-bird lane).
Yield: the financed-bird lane's birds (KG ACTIVE excluded — that's server-side; the
PRENORMAL 7-day lane is ours) + the Xiaomi quota lane at whatever the 1-device/year
cap allows.

**Rank 3 — the evidence product.** WHAT: sell PROOF with the unlock — the hash-chained
session ledger (03 §7.2's evidence rows), the iOS class-kvdiff + Manifest pair (06 §10),
reproducible manifest rows (07 §11), a customer-facing PDF/QR artifact: "this device,
this state, these operations, these hashes, this data-class coverage, this was NOT
accessed." Markets: secondhand-sale disclosure (buy a used bird with proof of state),
repair disputes, insurance, inheritance/small-court, eventually LE-adjacent work where
admissibility-as-product competes with Cellebrite's packaging. COST: $0 — the ledger
already exists as doctrine; this is productization (templates, QR verification,
tamper-evident export). BEATS: nobody — the lane is EMPTY (§5e).

**Rank 4 — the iOS backup-artifact finisher.** WHAT: the 06 §6 lane as a retail
service nobody offers: acquire the backup artifact (paired host, cloud-with-creds,
own pairing backups), extract the 0x309 keybag hash (philsmd tool), GPU battery on
-m 14800 (wordlist-first), cracked password → decrypt → restore-to-spare → data
classes landed. COST: $0 tools + the wave-04 GPU bridge (existing card; bench its
real H/s per 07/06 doctrine). BEATS: the DZ grey market (which sells backup-password
"services" as pure folklore or account phishing — 06 §8.2) and matches Elcomsoft's
$2,199 tool at $0 with autonomy on top. It is the FINISHER for birds whose screens
never open — the exact retail gap.

**Rank 5 — per-build enumeration research (the compounding moat).** WHAT: 01 §4 made
operational: verb matrices, settings write-lanes, state deltas, permission drift,
per-model lock signatures — each walked bird files rows; each new bird is triaged
against the library in minutes. COST: $0 + sacrificial twins (the 05 §8 chain library
is the intake format). BEATS: EVERYONE structurally — this is the asset that makes
the next bird cheaper forever (§10), the thing no vendor's release train and no
shop's muscle memory compounds at machine speed. It is ranked 5 only because it pays
slowest; it is rank 1 in ceiling.

---

## 8. THE HONEST WALLS — WHAT THE LAB WILL NOT BEAT

Said plainly, because the mission's honesty law demands it:

1. **Cellebrite/GrayKey on A12+ BFU iPhones.** Their private estates buy per-build
   SEP work that we do not possess and will not purchase (the 0-day broker economy is
   not our lane; 01's closed-map doctrine explains why we don't chase it). On a
   current-iOS BFU flagship with a strong passcode, they win, we park the bird. The
   404 Media matrix says even THEY are dark on 17.4+ between treadmill cycles — the
   wall is high for everyone; their ladder is just taller than ours.
2. **LE data contracts.** Warrant-driven cloud troves, vendor LE portals, the
   Apple/Google/Samsung government-request pipelines — contractual access we cannot
   and should not replicate. Out of scope by charter (01 §2f: owner-absent ≠
   warrant-present).
3. **Certified court chains — until we build the evidence law as a product (§7 rank
   3).** Until an operator's hash-chain ledger has survived adversarial scrutiny in a
   courtroom, Cellebrite's packaging remains the only admissibility game in town.
   Our evidentiary math is identical (hashes, logs, reproducibility — 07 §11); the
   PRECEDENT is what we lack, and precedent only accrues by shipping the product and
   standing behind it.
4. **Flagship-day-one support.** Their exploit pipelines buy fresh-0day coverage hours
   to weeks after a new flagship drops. Our lanes (public exploits, unpatchable bases
   like checkm8 ≤A11, stale installed base, state exploration) pay months later on the
   volume fleet. A launch-day iPhone 17 Pro BFU bird is theirs; the 875M-device MTK
   installed base (03 §3.3) is ours.
5. **The 90/10 sentence:** the universal system wins the 90% market — budget fleet,
   stale patches, paperwork disputes, refurb volume, wait-clocks, forgotten PINs —
   and concedes the 10% apex: fresh-flagship BFU with strong credentials and a court
   deadline. That is not a failure of ambition; it is the sharpest possible reading of
   where the physics (FBE/SEP), the economics ($0 marginal vs $145k seats), and the
   mission's crown law actually intersect.

---

## 9. COMPETITION MATRIX — ONE TABLE, THE WHOLE FIELD

| PLAYER | SEGMENT | PRICE | STRENGTH | BLIND SPOT | LLM-LAB ADVANTAGE |
|---|---|---|---|---|---|
| Cellebrite UFED/Premium | LE giant | ~$6k–30k/seat-yr (MEDIUM) | Deepest coverage, court-tested evidence chain, per-firmware exploit estate, global support | iOS 17.4+ BFU dark (leak, HIGH); no autonomy (GUI wizard); grant-priced, not value-priced; Android = loaders like everyone | Autonomy + chain synthesis on the same loader-fed lanes at ~$0; evidence law as product rather than packaging |
| GrayKey (Magnet/Grayshift) | LE giant, iOS specialist | $9,995 floor (HIGH) / $11.8–12.4k PO anchors (HIGH) / $90k–145k bundles | ≤A11 private SEP estate (brute magic), AFU process, fresh-flagship treadmill | Android is me-too; estate decays per Apple patch; closed map — named methods die; no state exploration | Own the unpatchable ≤A11 base via checkm8 (06) + backup-artifact math + honest triage; out-wait the treadmill |
| Magnet AXIOM / MSAB XRY / Oxygen | LE mid-tier | Quote-based, four-figure class (LOW) | Analysis depth (AXIOM); kiosk lane (XRY); corporate licensing (Oxygen) | Acquisition depth behind the two giants; same GUI-human model | Same as vs giants, sharper: their mid-tier price vs our $0 marginal |
| Octoplus / Octopus | Box vendor | ~$200–500 + credits $3.9–4.5 (HIGH) | Curated loaders, weekly Samsung FRP releases, service-shop ergonomics | Human curation lag on new chips/patches; per-op metered cost; no autonomy, no evidence, no wait-clocks | Loader library self-manufacture (Beagle loop, 03) + armory ingestion at machine speed; ops at $0 credit cost where OSS lane exists |
| z3x (Samsung/EasyJTAG) | Box vendor | ~$150–300 card (LOW) + credits | Samsung depth; ISP lane (EasyJTAG) | Same curation lag; Samsung-centric | ISP/pinout library (07 §4c) + per-model verdicts from walked birds |
| Sigma/SigmaKey | Box vendor | ~$100–300 (LOW) | MTK/QCOM service heritage, BROM lanes | Legacy-heavy; per-op metered | mtkclient supersedes on BROM era at $0 (03 §3) |
| ChimeraTool | Box vendor | ~$150–400/yr + credits (LOW) | Explicit KG/RMM unlock functions (docs, 05) | Paid-reset only (never data); per-op cost; curation lag | KG wait-clock portfolio does PRENORMAL free (05 §9); evidence row on every state transition |
| Medusa Pro / UFI / EasyJTAG-class | ISP rigs | ~$100–500/box (LOW) | Pinout DBs, dead-boot rescue, UFS service | GUI-first, scripting sparse; no reasoning | Rig bridge drives them via CLI/OCR fallback (03 §7); pinout library compounds (07 §4c) |
| SamKEY / DC-Unlocker / TSM-Tool | Credit servers | ~$3–150/op class | Remote one-shot ops at distance; Transsion $3 lane (TSM) | Metered per-op; no autonomy; DZ arbitrage depends on them | Free/stale-fleet lanes replace most credit ops; automation replaces the human watching the progress bar |
| Grey-market freelancers (Ouedkniss/XDA/Telegram) | Individual | ~$5–50/op | Walk-in availability, price, hustle | No evidence, no automation, no wait-clocks, scam density (GSX class, 06) | The panel IS the productized version of the honest stratum + proof on top |
| Open-source (mtkclient/edl/palera1n/hashcat/libimobiledevice) | OSS | $0 | The actual protocol layer; unpatchable bases (checkm8); the offline math | Ragged curation, zero reproducibility, no product shape | WE are this segment's missing shell: the armory (07) + compiler (01 §4.6) turn OSS into a system |
| DZ unlock shops (the arena) | Service layer | 1000–4000 DA/op (MEDIUM-HIGH) | The customer relationship; physical bench; trust | Manual-only, one-bird-at-a-time, no clocks, no docs, no proof | One operator + Vesper = their shop at 24/7 throughput with evidence receipts |

---

## 10. THE VERDICT — THE MARKET THESIS

**The autonomous lab is not a cheaper Cellebrite. It is a NEW CATEGORY.** Cellebrite
sells court-admissibility packaging around a decaying exploit estate, priced for
grant-funded buyers at $6–30k a seat; GrayKey sells a private iOS treadmill at $10–18k
a seat; the box vendors sell human-curated loader libraries at $100–500 plus metered
credits; the DZ shops sell human hands at 1000 DA an op. Every one of them is a HUMAN
operating a fixed method list against one bird at a time — the closed map (00: methods
named, dying by patch, the expert the bottleneck). The LLM-driven autonomous lab is a
24/7 evidence-producing unlock FACTORY for the market none of them serve at any price:
the budget-fleet + paperwork economy — Transsion volume, stale-fleet glass bugs,
loader-fed artifact math, wait-clock portfolios no shop will babysit, hash-chained
proofs no vendor productizes. And its moat COMPOUNDS with every bird walked: each
arrival files rows into the loader library, the pinout library, the lock-signature
library, the per-build verb/settings matrices, and the skill chains (05 §8) — so the
hundredth bird is triaged in minutes and walked at near-zero marginal cost, while the
giants re-buy their estate every patch cycle and the shops re-pay their humans every
op. The 90% market is won by patience, state exploration, and machine curation; the 10%
apex (fresh-flagship BFU, strong credentials, court deadline) stays theirs — and the
universal system says so plainly and parks those birds. That honesty is itself a
product feature none of the competition ships either.

## COMPETITION VERDICT

The field splits into four price universes on one physics: LE giants ($10k–145k/seat)
selling legal packaging over private estates that decay per patch; box vendors
($100–500 + $4-class credits) selling human-curated loader libraries through GUIs;
grey-market freelancers ($5–50/op) selling hustle without proof; OSS ($0) publishing
the protocol layer with no product shape. None of them — at ANY price — autonomously
triages a bird, walks a state machine, parks a 7-day clock, compiles a novel chain,
or attaches hash-chained evidence to the work. The autonomous lab wins not by
undercutting their seats but by occupying the lane their economics cannot see: the
90% budget-fleet + paperwork market, at $0–500 stack cost, compounding a curation
moat every bird it walks. The giants keep the apex; the compounding library keeps
the future.

## WHAT WE BUILD TO WIN DZ + BEYOND — THE 10-LINE ORDER

1. **Intake robot + triage state machine** — BFU/AFU, SoC family, lock layers, KG
   state read on every arrival (01 §5, 03 §7.2); the panel's first five minutes,
   automated.
2. **The Transsion volume lane** — mtkclient BROM sweeps, `e frp`/seccfg scripting,
   stale-fleet glass catalogue auto-applied per patch level; T1/T2 hardware only.
3. **The scheduler module** — PARKED_<clock> states for KG 168 h + Xiaomi 72 h/quota
   + bench-power babysitting; resume only on OBSERVED state transitions, evidence row
   before every destructive step (05 §9 verbatim).
4. **The armory loop** — manifest-first ingestion of loaders/pinouts/combos during
   uplink windows; Beagle 480 sniffing self-manufacture (03 §2.2) once T3 lands;
   loader verdicts filed per model from every walked bird.
5. **The evidence ledger as product** — session rows, class-kvdiff + Manifest pairs
   (06 §10), customer-facing QR-proof export: sell PROOF with every unlock.
6. **The offline-math finisher** — artifact dumps → GPU battery (hashcat 5800/8800/
   8900/14800, wordlist-first) → recovered PIN → boot normally; the crown-compatible
   endgame on every readable bird.
7. **The iOS backup lane** — philsmd extraction + `-m 14700/14800` + restore-to-spare
   rehearsal; the retail finisher nobody in the market offers.
8. **The chain library + compiler** — 05 §8's chains as the skill format; each verified
   state transition a node; graph-search per bird (01 §4.6).
9. **Per-build enumeration runs** — verb matrices, settings write-lanes, state deltas,
   lock signatures on every sacrificial twin; the compounding moat, filed nightly.
10. **The one-operator shop** — Vesper + one human + a bench of parked birds = a DZ
    unlock operation running 24/7 with evidence receipts: the market math (§6) says
    40–80 ops/month at ~85–95% margin, and every month the libraries make the next
    month cheaper.

---

## SOURCES — THIS WAVE (web_search dead in-session; DDG-HTML + direct fetches)

- upturn.org/work/mass-extraction (fetched full; 2,000+ agencies / 50 states; ~1,500
  lock-bypass devices since Mar-2016; 76%-of-33 lab stat; 50,000 extractions across 44
  agencies 2015–2019; agency spends $49k–$1.1M+; FBI 84 kiosks / 31,000 uses FY13–16;
  consent ratios; grant economy; multi-vendor purchasing quotes).
- magnetforensics.com/news/grayshift-announces-graykey-support-for-lg-and-mediatek
  (fetched; "$9,995" annual license floor — PRIMARY).
- govtribe.com PO 15DDB024P00000056 ($11,820 DEA GrayKey, Sep-2024→Sep-2025) ·
  federalcompass.com 70LGLY25PSSB00016 ($12.4k FLETC, Mar-2025) + 70CMSD25P00000130
  ($90k ICE HSI, Sep-2025) · highergov.com ICE recompete forecast (~$5M) + Army RFQ
  W9124925QA004 (GrayKey Offline Premier) · article-factory ICE summary ($12k–$145k
  license band) · imore GrayKey documents piece ($300/employee training, Turbo
  marketing) · ocalagazette.com OPD GrayKey renewal (FY24-25, in use since 2018).
- octoplusbox.com/en/products/credits + /octoplus-server-credits + FAQ ($3.9–4.5 per
  credit; per-model consumption; 1-day license + 100 credits product; 2026-07-05
  patch-level FRP release notes) — PRIMARY. chimeratool.com/shop/credit-prices
  (page live, prices gated). wiki.z3x-team.com Z3X Server Credits. gsmserver.com
  credits/activations catalog.
- 404media.co leaked-docs piece (April-2024 Cellebrite capability matrix; iOS 17.4+
  locked = "In Research") · techdirt.com arms-race piece · wccftech/3u/golem
  corroborations · cellebrite.com blogs (66%-locked survey quote; "Access Gap Closed
  2026" marketing; premium "unlimited lawful access" page) — cellebrite.com fetched
  via DDG snippets + one 403 geo-block noted.
- Ouedkniss live listings (PRIMARY DZ): 1000 DA FRP/flash/schéma/KG basket (Sidi
  M'hamed); 2000 DA Samsung MSL (El Harrach); 4000 DA MacBook EFI; carrier 1–9999 DA
  band. ouedkniss.com/ouedkniss.dz.
- German corpus: freiheitsrechte.org RSF forensic-software PDF · kripoz.de Ludewig
  smartphone-seizure paper · it-forensik.de survey — class verified; Pinneberg figure
  LOW–MEDIUM (remembered, no live primary this wave).
- Failed/refused fetches (honesty ledger): zerodium.com/program.html ×2 (fetch
  failed — bounty figures cited LOW–MEDIUM from memory); cellebrite.com/en/
  responsible-disclosure (CloudFront 403 geo-block).
- Folklore-name audit: "Netburner"/"188A" — zero DDG hits (NetBurner = embedded
  dev-boards, unrelated); "Antrim" → Upturn's actual dataset county is Anoka (MN).
  Treated as folklore-class shorthand; the verified study corpus carries the claims.
- Prior waves: 01_universal_door_map.md §6 (players), 03_silicon_plane.md §2/§3/§7/§9
  (loader economics, rig bridge, tiers), 05_vendor_chains.md §6/§8/§9 (Transsion,
  chains, clocks), 06_ios_front.md §3/§4/§5/§6/§8 (tool landscape, estates, backup
  math, activation honesty), 07_armory.md §4/§11 (four libraries, reproducibility).

*Wave W4b complete. Feeds: W5 system audit (the competition matrix's LLM-lab column =
the audit's target capability list) and BLUEPRINT (§7's five ranked lanes are the
build order; §6's market math is the operating-model section; the evidence product is
a first-class module). The panel's disk ate the first write of this wave — this file
is the one that landed.*
