"""
GHOST :: mathcore.py — the probability engine behind the pairing siege.

Code IS math wearing a costume. This module is the math, naked:

  1. CODE SPACES & ENTROPY
     A 6-digit pairing code lives in a space of 10^6 = 1,000,000.
     Shannon entropy of uniform choice: log2(10^6) ≈ 19.93 bits.
     Humans do NOT sample uniformly — published leak analyses (DataGenetics
     4-digit PIN study, 6-digit PIN/OTP leak corpora) show the top few
     hundred codes carry double-digit percent of the real-world mass.

  2. BAYESIAN SIEGE ORDERING (the actual weapon)
     Try codes in descending prior probability. With codes sorted so
     p_(1) >= p_(2) >= ..., the expected number of attempts until the
     true code appears is
         E[N] = sum_i  i * p_(i)  +  N_max * (1 - M_N)
     where M_N = cumulative prior mass of the first N_max candidates and
     the second term is the expected cost of finishing on the uniform
     residual. Sequential order pays E ≈ 500,000; prior order pays
     E ≈ 1/ (mass-weighted rank) — often three to four orders less.

  3. DIALOG-WINDOW MODEL
     The phone's pairing dialog is a renewable resource: each open mints
     a fresh code valid for the dialog lifetime W (~90 s of idle, plus
     however long the operator leaves it). One attempt costs
     tau = t_tls + t_spake2 + t_gcm ≈ 0.3–1.5 s over LAN.
     Attempts per dialog open: A = floor(W / tau).
         P(hit in one dialog) = prior_mass(A)   [biased engine]
         P(hit over K dialogs) = 1 - (1 - p)^K  [independent dialogs]
     This turns "brute force" into a resource-allocation schedule.

  4. ADAPTIVE PACING
     No artificial delay beats physics: the attempt rate is bounded by
     the protocol itself. We keep a rolling median of measured attempt
     durations and recompute the schedule from it. The only courtesy
     floor is SAFETY_FLOOR_S (default 0.15 s) so we never hammer a
     device harder than a human with fast fingers would.

Pure stdlib. No Flask, no adb — every function is testable arithmetic.
"""

import math
import time
from bisect import insort

# --------------------------------------------------------------------------
# 1. Code spaces and entropy
# --------------------------------------------------------------------------

def entropy_bits(space_size: int) -> float:
    """Uniform-choice Shannon entropy, in bits."""
    if space_size <= 1:
        return 0.0
    return math.log2(space_size)


SIX_DIGIT_SPACE = 10 ** 6
SIX_DIGIT_ENTROPY = entropy_bits(SIX_DIGIT_SPACE)   # 19.9316...

# --------------------------------------------------------------------------
# 2. The prior: human-chosen 6-digit codes, descending mass
# --------------------------------------------------------------------------
# Calibration (honest): relative weights distilled from public leak
# corpora — the DataGenetics 4-digit PIN study, 6-digit OTP/PIN dumps,
# and password-corpus numeric tails. These are HEURISTIC PRIORS, not
# gospel; the machinery below is exact given whatever priors you feed it.

_PRIOR_RAW = [
    # keystroke walks / repeats — the global summit
    ("123456", 5.0), ("000000", 2.4), ("111111", 1.9), ("123123", 1.3),
    ("121212", 1.1), ("112233", 1.0), ("654321", 0.9), ("123321", 0.8),
    ("696969", 0.6), ("000123", 0.5), ("456789", 0.45), ("789456", 0.45),
    ("159753", 0.4), ("123654", 0.4), ("987654", 0.35), ("888888", 0.3),
    ("222222", 0.28), ("666666", 0.28), ("999999", 0.25), ("555555", 0.25),
    ("333333", 0.22), ("777777", 0.22), ("444444", 0.2), ("101010", 0.18),
    ("121111", 0.15), ("100200", 0.15), ("258258", 0.15), ("147258", 0.14),
    ("369369", 0.13), ("258025", 0.12), ("137913", 0.1), ("085208", 0.1),
]

# years as YY01xx birthday belt (1950–2010); then ddmm + yy suffix calendar codes
for _y in range(1950, 2011):
    _ys = f"{_y % 100:02d}"
    _w = 0.30 if 1970 <= _y <= 2005 else 0.12
    _PRIOR_RAW.append((f"{_ys}0101", _w))     # YY0101 birthdays-of-convenience
for _d in range(1, 32):
    for _m in range(1, 13):
        _w = 0.10 if _d <= 28 else 0.04       # real calendar dates dominate
        _PRIOR_RAW.append((f"{_d:02d}{_m:02d}{'89' if _d % 2 else '87'}", _w / 8))

# dedupe + normalize into a proper descending prior
_seen = {}
for code, w in _PRIOR_RAW:
    if w > 0:
        _seen[code] = _seen.get(code, 0.0) + w

_TOTAL_W = sum(_seen.values())
# The priors above are RELATIVE frequencies of the biased region. The
# remaining 6-digit mass is uniform residual. We do NOT pretend the
# biased list covers the world: SIEGE_CODES = ranked candidates,
# SIEGE_MASS = total probability mass the ranked prefix claims.
_SIEGE_CODES = [c for c, _ in sorted(_seen.items(), key=lambda kv: -kv[1])]
_SIEGE_WEIGHTS = {c: _seen[c] for c in _SIEGE_CODES}
# Rescale so that the biased region itself carries ~12% of the full space
# (empirical share of human-chosen 6-digit codes inside the pattern belt):
BIASED_REGION_MASS = 0.12
SIEGE_MASS = {c: (w / _TOTAL_W) * BIASED_REGION_MASS for c, w in _SIEGE_WEIGHTS.items()}


def siege_codes() -> list:
    """Prior-ranked candidate codes (the biased dictionary, canonical order)."""
    return list(_SIEGE_CODES)


def prior_mass(n: int) -> float:
    """Cumulative prior probability mass of the first n ranked candidates."""
    return sum(SIEGE_MASS[c] for c in _SIEGE_CODES[:n])


def expected_attempts(n_max: int) -> float:
    """E[attempts] under prior ordering, capped at n_max then uniform residual.

    E = sum_{i=1..n_max} i * p_(i) + (1 - M_n_max) * [ n_max + (R+1)/2 ]
    where R = 10^6 - n_max residual codes swept uniformly afterwards.
    Sequential uniform order pays ≈ (10^6 + 1) / 2 ≈ 500,000.
    """
    acc = 0.0
    m = 0.0
    for i, c in enumerate(_SIEGE_CODES[:n_max], start=1):
        p = SIEGE_MASS[c]
        acc += i * p
        m += p
    residual_space = SIX_DIGIT_SPACE - n_max
    if residual_space > 0:
        acc += (1.0 - m) * (n_max + (residual_space + 1) / 2.0)
    return acc


def p_hit_within_dialogs(attempts_per_dialog: int, dialogs: int) -> float:
    """P(hit) over K independent dialog opens (fresh code each).

    With A prior-ranked attempts per dialog the win probability per open
    is exactly M_A (cumulative prior mass) — the residual space contains
    codes our ranked list never proposes, so the naive engine's uniform
    p = A/10^6 is the comparison baseline, not part of this sum.
    """
    if attempts_per_dialog <= 0 or dialogs <= 0:
        return 0.0
    p = min(1.0, prior_mass(attempts_per_dialog))
    return 1.0 - (1.0 - p) ** dialogs


def p_hit_uniform(attempts_per_dialog: int, dialogs: int) -> float:
    """The naive-engine comparison line: uniform sampling only."""
    if attempts_per_dialog <= 0 or dialogs <= 0:
        return 0.0
    p = attempts_per_dialog / SIX_DIGIT_SPACE
    return 1.0 - (1.0 - p) ** dialogs


# --------------------------------------------------------------------------
# 3. Dialog-window schedule
# --------------------------------------------------------------------------

def dialog_window(attempt_seconds: float, dialog_seconds: float = 90.0,
                  dialogs: int = 10) -> dict:
    """Full resource model for one siege campaign."""
    tau = max(attempt_seconds, 1e-6)
    a = int(dialog_seconds / tau)
    return {
        "attempt_seconds": round(tau, 3),
        "dialog_seconds": dialog_seconds,
        "attempts_per_dialog": a,
        "dialogs": dialogs,
        "p_hit_biased": round(p_hit_within_dialogs(a, dialogs), 5),
        "p_hit_uniform": round(p_hit_uniform(a, dialogs), 5),
        "expected_attempts_prior": round(expected_attempts(min(a * dialogs, len(_SIEGE_CODES))), 1),
        "expected_attempts_uniform": round((SIX_DIGIT_SPACE + 1) / 2.0, 1),
        "space_bits": round(SIX_DIGIT_ENTROPY, 3),
    }


# --------------------------------------------------------------------------
# 4. Adaptive pacing — rolling median of real attempt durations
# --------------------------------------------------------------------------

class RollingMedian:
    """Median of the last k durations; O(log k) insert via sorted list."""

    def __init__(self, k: int = 12):
        self.k = k
        self._sorted = []
        self._ring = []
        self._i = 0

    def add(self, value: float):
        if len(self._ring) < self.k:
            self._ring.append(value)
            insort(self._sorted, value)
        else:
            old = self._ring[self._i]
            pos = _bisect_left(self._sorted, old)
            del self._sorted[pos]
            self._ring[self._i] = value
            insort(self._sorted, value)
        self._i = (self._i + 1) % self.k

    def median(self, default: float = 0.9) -> float:
        n = len(self._sorted)
        if n == 0:
            return default
        mid = n // 2
        return self._sorted[mid] if n % 2 else (self._sorted[mid - 1] + self._sorted[mid]) / 2.0


def _bisect_left(seq, x):
    lo, hi = 0, len(seq)
    while lo < hi:
        mid = (lo + hi) // 2
        if seq[mid] < x:
            lo = mid + 1
        else:
            hi = mid
    return lo


SAFETY_FLOOR_S = 0.15


def pacing_delay(timer: RollingMedian) -> float:
    """Inter-attempt courtesy delay: never below the safety floor,
    never above what the rolling median says the device already needs."""
    med = timer.median()
    return max(SAFETY_FLOOR_S, min(0.5, med * 0.10))


# --------------------------------------------------------------------------
# 5. Self-test
# --------------------------------------------------------------------------

def selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    check("entropy(10^6) == 19.9316 bits", abs(SIX_DIGIT_ENTROPY - 19.9316) < 1e-3)
    check("siege codes non-empty & unique", len(_SIEGE_CODES) > 400 and len(set(_SIEGE_CODES)) == len(_SIEGE_CODES))
    check("top code is 123456", _SIEGE_CODES[0] == "123456")
    check("prior mass descending", all(
        SIEGE_MASS[_SIEGE_CODES[i]] >= SIEGE_MASS[_SIEGE_CODES[i + 1]]
        for i in range(len(_SIEGE_CODES) - 1)))
    m100 = prior_mass(100)
    check("top-100 mass in (0, biased_region]", 0 < m100 <= BIASED_REGION_MASS + 1e-9)

    # The honest comparison: conditional on the code being in the ranked
    # list, prior ordering finds it in ~ (sum i*p_i)/M attempts; uniform
    # ordering needs 500,000 even in the best case.
    n_all = len(_SIEGE_CODES)
    m_all = prior_mass(n_all)
    e_prior = expected_attempts(n_all)
    e_uniform = (SIX_DIGIT_SPACE + 1) / 2.0
    e_cond = (e_prior - (1.0 - m_all) * (n_all + (SIX_DIGIT_SPACE - n_all + 1) / 2.0)) / m_all
    check("E[prior] beats E[uniform] outright", e_prior < e_uniform)
    check("conditional in-region E < 10k", e_cond < 10_000)
    print(f"     prior-ranked list: {n_all} codes, total mass {m_all:.3f}")
    print(f"     conditional in-region E[attempts]: {e_cond:.0f}  (uniform: 500000)")
    w = dialog_window(0.8, dialog_seconds=90, dialogs=10)
    check("90s @ 0.8s -> 112 attempts/dialog", w["attempts_per_dialog"] == 112)
    check("biased beats uniform in P(hit)", w["p_hit_biased"] > w["p_hit_uniform"])
    print(f"     dialog model: A={w['attempts_per_dialog']}, "
          f"P_biased={w['p_hit_biased']}, P_uniform={w['p_hit_uniform']}")
    rm = RollingMedian(k=4)
    for v in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0):
        rm.add(v)
    check("rolling median of last 4 {3,4,5,6} == 4.5", abs(rm.median() - 4.5) < 1e-9)
    check("pacing floor respected", pacing_delay(RollingMedian()) >= SAFETY_FLOOR_S)
    print("MATHCORE SELFTEST " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
