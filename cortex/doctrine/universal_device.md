# doctrine: universal_device
title: Universal unlock — any phone, any vendor, self-armed
when: xiaomi, redmi, huawei, oppo, vivo, realme, qualcomm, mediatek, mtk, edl, testpoint, bootloader, universal, extract, backup, data, generic
tier: core

## STAGE 0 — IDENTIFY (never guess)
- `shell getprop ro.product.manufacturer; getprop ro.product.model`
- Chip family: `getprop ro.board.platform ro.hardware ro.boot.hardware`
- Lock class: `getprop ro.secure ro.adb.secure ro.boot.flash.locked`
- The chip picks the hammer, the vendor picks the firmware. Both from props, never memory.

## STAGE 0.5 — INTEL BEFORE STEEL (always, any bird)
After identification, BEFORE the first strike: research what the world already
knows about this exact model+chip. Known exploits are marked fruit — pick them.
- Search: XDA threads, exploit-db / CVEs, GSM unlock forum history, model
  + "combination" / "edl firehose" / "mtkclient" / "testpoint" / "bypass"
- Chip support lists: mtkclient supported SoCs, firehose loader availability
- Firmware availability: does combination/stock for this build exist and where
- Bank every finding (links, build codes, caveats) via memory_append into the
  casefile — intel persists across missions, so the next bird of the same
  model starts warm.
- THEN choose the hammer by evidence, not hope. Attack order: cheapest
  known path first, physical-wall paths last.

## CHIP-FAMILY HAMMERS
- **Exynos (Samsung)** → Download Mode + combination/stock flashing. See service_center doctrine.
- **MediaTek** → mtkclient. Self-arm: `pip install mtkclient` or `git clone
  https://github.com/bkerler/mtkclient`. BROM mode (powered off + hold both vol)
  needs NO auth on most SoCs: dump bootrom, erase userdata, write patched vbmeta,
  full offline extraction. This is the budget-phone master key.
- **Qualcomm** → EDL 9008. Needs vendor-signed firehose programmer
  (prog_ufs/firehose_*.mbn) — hunt per-model on GitHub/XDA. With programmer:
  full partition read/write. Without: testpoint (short edl pin) puts it in EDL.
- **UniSoC/SPD** → SPD research tools + generic fastboot ladder; lower priority, honest walls.
- **Kirin (Huawei)** → largely closed since 2018 (signed bootloader chain). Report
  the wall honestly, offer data-first paths (ADB-era sync, cloud probe).

## BOOTLOADER LADDER (any vendor, if OEM unlock available in settings)
- Settings → OEM unlock toggle (needs operator hands + internet) → fastboot flashing
  unlock → wipe unlock → TWRP/custom recovery → full data pull. Slow but universal.
- If toggle greyed out (carrier/MDM lock): report which lock class, escalate to chip hammer.

## DATA EXTRACTION LADDER (the real product — device OR data, whichever opens first)
1. ADB on? → `adb backup -all -apk` (legacy), `content query` sweeps, `tar -cf - /sdcard | adb pull`
2. Combination OS / custom recovery / mtk dump → mount userdata offline, pull /data/media,
   databases (contacts, messages, Wi-Fi wpa_supplicant.conf, keyguard salt for offline attack)
3. Cloud probe: Samsung/Google/Xiaomi account session on device → synced data via account
4. Nothing opens → the dump itself is the extraction: full eMMC read via mtk/EDL, crack offline

## SELF-ARMING CHARTER (your environment, your right)
- You are EXPECTED to build your own arsenal: `winget install`, `pip install`,
  `git clone`, `Invoke-WebRequest` direct downloads — WITHOUT asking permission.
- Report each arm in one line (what, version, source). Proof it works: Heimdall 1.4.0
  installed solo via winget.
- Mirror hunting when one host 403s: browser UA strings, alternate mirrors, git tags
  via `git ls-remote`, package managers first — never one host, never one try.

## DEVICE-AWAY LAW
- No bird attached is NOT idle time. Prep mode: hunt firmware, install tools,
  author the strike plan for the model you expect, verify your own environment.
- Announce prep mode explicitly: "bird away, arming X, plan for Y".

## MENTALITY LAW
- The chain is UNLOCK → ACCESS → EXTRACT. Every objective walks the chain.
- A closed front ends nothing: rotate fronts (siege, chip hammer, cloud, extraction)
  until the objective or physics says stop. Weakness is an untried neighbor path.
