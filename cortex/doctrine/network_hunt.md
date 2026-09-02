# doctrine: network_hunt
title: Hunt pairing doors and strike with evidence
when: sweep, hunt, pairing, network, wifi, lan, hunter, target, strike, engage
not_when: offline, airplane
tier: core

## THE CHAIN

1. `hunter_status` FIRST — she may already be armed and holding targets.
   Never double-strike a door she is besieging.
2. `network_sweep` — classified targets come back with vectors attached.
   Read the classification; trust it over guessing.
3. One target at a time: `engage_target` with exact ip + port.
   Parallel sieges double-count lockout timers and blind you both.
4. If she was armed (`hunter_arm`), new pairing dialogs are auto-struck —
   your job becomes reading `hunter_status` events, not manual sweeping.
5. Evidence discipline: every strike event lands in the hunter log.
   Report IPs, ports, classification, and the exact event text —
   not "I found something".

## STANDING RULES
- An EMPTY sweep is a truthful answer. Report "no doors", never invent.
- A target that refused engagement stays refused — the siege knows the
  lockout timers; do not hammer it by hand.
- `hunter_standdown` when the operator says stand down or the mission
  ends. Leave no watcher behind unless he asked for one.
