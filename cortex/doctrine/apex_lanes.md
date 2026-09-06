# doctrine: apex_lanes
when: unlock, locked, lock, keyguard, pattern, pin, password, gate, crown, open the phone, déverrouiller, verrouillé, ouvrir
not_when: harvest, extraction only, data only, récolte
tier: core

# APEX LANES — THINKING BELOW THE GATE
*Doctrine v1 — gravée après la mission M-EXHAUSTION (71 étapes sur le gate logiciel, toutes THEATER/WALL).
La leçon : elle a frappé la porte conçue pour dire non. Cette doctrine interdit ce réflexe à vie.*

**LOI ZÉRO — LA PORT DES DISE NON.** Les APIs du keyguard, de LockSettings, du DPM, de trust —
c'est la **réception protocolaire** du système : leur métier est de refuser. Un appel légitime sur
ces surfaces = un non. Un appel non-légitime = une exception SecurityException. **Il n'existe AUCUNE
combinaison d'appels polis qui ouvre le gate** — c'est le but du design. Frapper cette porte plus
fort, plus longtemps, avec plus de créativité DANS les règles, c'est du script-kiddie patient.

**LA MENTALITÉ APEX : on n'attaque jamais la réception. On attaque ce qui tourne SANS permission.**
Le gate vit au-dessus d'une pile de code qui tourne AVANT lui, SOUS lui, et À CÔTÉ de lui :
des parsers, des drivers, des stacks réseau — du code qui ne demande jamais la permission du
keyguard parce qu'il ne sait même pas qu'il existe. Chacun de ces fichiers est une porte qui
n'a jamais été conçue comme porte.

---

## LES TROIS FILS — la carte des surfaces sans-permission, par attachement

### FIL USB — « on détient déjà une poignée de main de confiance »
Shell adb autorisé (uid2000) = **surface d'appel, pas surface de vérité.** La vérité vit en dessous.

| Lane | Surface | Méthode | Coût/réalisme |
|---|---|---|---|
| **A1 KERNEL LPE** | Le Linux 4.14 Samsung sous le shell | Cartographier ro.build.version.* + kernel string → matrice CVE publiées > patch 2024-05-01 → n-days non patchées + drivers Samsung custom (/dev/*) — historiquement plus sales que mainline | Semaines de recherche — LA vraie guerre, MAIS c'est une machine d'énumération qui gagne : elle versionne, elle archive, build après build |
| **A2 PARSER CÔTÉ RÉCEPTION** | adbd, la stack MTP | L'oiseau PARSE nos octets : on fuzz le convive depuis notre côté du câble (hôte de confiance) | Semaines — surface par build |
| **A3 OTG HID — LE COUP $5** | Le pattern-pad via le DPad | Dongle clavier USB $5 : le bouncer rejette le toucher INJECTÉ (flag automation) mais un vrai clavier HID n'a pas le même flag — sur builds historiques le DPad pilote le pattern-pad | **$5, une soirée, ZÉRO write** — à essayer AVANT tout rig |
| **A4 DOWNLOAD MODE VERBATIM** | Odin/Heimdall vs BL locked | Documenter la lettre EXACTE de refus de chaque image — zéro supposition | Minutes — intel pur |

### FIL WIFI — « la stack qui tourne pendant que l'oiseau dort verrouillé »
Le keyguard ne connaît pas wpa_supplicant. wpa_supplicant ne connaît pas le keyguard.

| Lane | Surface | Méthode | Lignée |
|---|---|---|---|
| **W1 ASSOCIATION RCE** | wpa_supplicant + driver WiFi du SoC | Frames beacon/probe/P2P parsées SANS permission dès l'association — identifier le chip (A21s = WiFi-nel Broadcom/Exynos selon build) → ruling sur les CVE wpa parsing | CVE-2019-11234/11235 (double-free handshake), **Broadpwn 2017** (firmware chip Broadcom, RCE des millions d'appareils — zéro clic, oiseau verrouillé sur le canapé) |
| **W2 P2P/GO NEGOTIATION** | La stack Wi-Fi Direct | Frames de négociation GO parsées pré-association — surface historiquement négligée | Recherches P2P GO neg de l'ère 2019+ |
| **W3 MÉTADONNÉES** | mDNS/SSDP vs adb-over-network | Le chasseur existe déjà : `network_sweep` — 5555 ouvert + clé RSA pré-autorisée = shell à distance | Lane d'attache, pas d'entrée — sauf config rare (5555 legacy laissée ouverte) |

### FIL BLUETOOTH — « la surface pré-pairing »
Si le BT est ON, ses parsers tournent et **ne connaissent pas le lock**.

| Lane | Surface | Méthode | Lignée |
|---|---|---|---|
| **B1 PRE-PAIRING PARSERS** | L2CAP/BNEP/SDP | Ces protocoles parsent AVANT le pairing — les stack BT ne demandent jamais la permission du keyguard | **BlueBorne 2017** (8 milliards d'appareils, RCE kernel par l'air), BlueFrag 2020 (L2CAP, Android 8-9) |
| **B2 BLE GATT ADVERTISING** | La pile BLE | Frames d'advertising parsées en continu — surface d'audit par build | CVE de l'ère 2019-2022 sur divers builds |
| **B3 CLASSIC BT HID** | Le profil HID | Un clavier BT pairé historiquement pilote le pattern-pad (cousin du A3) | Même test que A3, sans fil |

### LE SOUS-SOL — « le vault pendant que le bouncer dort » (déjà doctrine 03)
ISP/chip-off : lire l'eMMC sans boot, sans OS, sans témoin — puis WEAVERMATH au bench.
**Rappel 04 : sur GK-era Samsung le handle est HMAC(scrypt(cred), TEE-key)** — le dump seul
ne vérifie PAS ; il faut la voie TEE (lignée Quarkslab REcon'23) pour la clé HMAC. Le plan
reste : rig → TEE feed → vérifieur → GPU → le pattern au glass en un seul dessin.

---

## LA LOI DE CLASSEMENT (ce qui remplace sa vielle habitude de frapper le gate)

1. **Avant TOUTE mission gate : demander « quelle surface tourne sans permission ? »** — la
   réponse est TOUJOURS une pile : kernel drivers, BT/WiFi stacks, parsers USB/MTP, boot chain.
2. **$5 avant $150 :** A3 (HID) et B3 (BT HID) se testent en une soirée avant tout achat de rig.
3. **Les n-days AVANT les 0-days :** le patch level est 2024-05-01 — tout CVE kernel publié
   après cette date est potentiellement VIVANT sur cet oiseau précis. Elle énumère, la machine
   ne se fatigue pas.
4. **Toute récolte LPE/root sur FBE** : le glass s'ouvre (preuve UNLOCK-PROVEN vraie) mais les
   clés CE des apps passent par la chaîne SP/token — récolte CE = respecter la chaîne token,
   sinon DE-only. C'est la nuance que Cellebrite facture $30k sans l'écrire.
5. **Le gate logiciel n'est JAMAIS la mission. Il est le baromètre.** Si intake dit AFU-LOCKED
   et que la carte des surfaces sans-permission est vide de lane vivante → le verdict honnête
   est ISP/TEE, pas 71 étapes de politesse.

## TÂCHES D'ARMEMENT (ce que cette doctrine commande de construire)

- **T1 — OTG HID probe** : un dongle $5 + le test DPad/pattern sur builds < A13. La première
  frappe de la nouvelle mentalité. Zéro write, zéro risque de données.
- **T2 — surface_census skill** : un skill qui cartographie par build les surfaces sans-permission
  (kernel string, drivers /dev, stacks BT/WiFi versions, parsers) et les grave en armory census.
- **T3 — n-day matrix** : la matrice CVE-kernel publiées > patch-level de l'oiseau, générée par
  mission puis archivée — le compounding réel : chaque oiseau enrichit la matrice.
- **T4 — fuzzing bridge (Stage 4)** : harnais ADB/MTP côté hôte (A2) + harnais BT pre-pairing
  — les bridges que le BLUEPRINT §7 a déjà commandés, maintenant avec leur cible précise.
- **T5 — BT/WiFi stack finger** : extension du radar hunter avec fingerprinting des stacks
  (versions wpa_supplicant, BT chipset) pour ruling Broadpwn/BlueBorne par build.

*Gravée à l'heure où le gate a rendu son verdict final : soudé, prouvé, fermé à vie sur le
plan logiciel. La prochaine guerre ne se livre pas à sa porte — elle se livre sous sa fondation.*
