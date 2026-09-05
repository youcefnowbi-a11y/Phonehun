"""
PANOPTICON :: geo_math.py — the physics layer of GPS-less location.

Everything here is honest wave mechanics and plane geometry:

  1. PATH LOSS (the inverse-square law wearing dB clothes)
     Free-space power at distance d, frequency f:
         FSPL(dB) = 20*log10(d_m) + 20*log10(f_MHz) - 27.55
     At 1 m, 2437 MHz (Wi-Fi ch 6): FSPL = 40.2 dB — the classic figure.
     A log-distance model with indoor exponent n:
         RSSI(d) = P_tx - FSPL_1m - 10*n*log10(d)
     inverted:
         d = 10^((P_tx - FSPL_1m - RSSI) / (10*n))
     n = 2.0 is vacuum; indoor building material pushes it to 2.7-3.2.
     Default n = 2.8, P_tx = 20 dBm (typical AP).

  2. WHY THE OLD CENTROID WAS WRONG
     Weighting anchors by (100 + rssi_dbm) weights by the LOGARITHM of
     received power. The physical quantity is POWER: w = 10^(rssi/10)
     (milliwatts). An AP at -40 dBm delivers 10,000x the power of one at
     -80 dBm; a linear-in-dBm weight treats them as 60 vs 20. Trilateration
     goes further: it uses the DISTANCE estimate per anchor, which is what
     RSSI actually encodes.

  3. TRILATERATION (weighted linearized least squares)
     Anchors at (x_i, y_i) with estimated ranges r_i. Linearize by
     subtracting anchor 0:
         A_i = [2(x_i-x_0), 2(y_i-y_0)]
         b_i = r_0^2 - r_i^2 + x_i^2 - x_0^2 + y_i^2 - y_0^2
     Weighted normal equations (A^T W A) p = A^T W b with w_i = 1/r_i^2
     (Fisher information of a range measurement falls as 1/d^2 — near
     anchors speak louder). Solved in closed form via 2x2 Cramer's rule.
     Degeneracy (collinear anchors, tiny determinant) degrades honestly
     to the weighted power centroid instead of inventing a point.

  4. ENU LOCAL FLAT EARTH
     Room-scale problems don't need geodesics: convert anchors to
     East/North meters around a reference latitude, solve in meters,
     convert back. Meters-per-degree from the WGS84 series:
         m_lat(phi) = 111132.92 - 559.82 cos2f + 1.175 cos4f - ...
         m_lon(phi) = 111412.84 cos f - 93.5 cos3f + 0.118 cos5f

  5. TIMING ADVANCE (the network tells you the distance itself)
     GSM:  1 TA = 1 bit period round trip -> d = TA x 553.5 m
     LTE:  1 TA = 16*Ts round trip       -> d = TA x 78.1 m
     These are bounds, not precision fixes — labeled as such.

Pure stdlib. Every function testable arithmetic, no network, no adb.
"""

import math

# --------------------------------------------------------------------------
# Path loss
# --------------------------------------------------------------------------

DEFAULT_P_TX_DBM = 20.0    # typical 2.4 GHz AP EIRP class
DEFAULT_N_INDOOR = 2.8     # indoor log-distance exponent


def fspl_1m(freq_mhz: float) -> float:
    """Free-space path loss at 1 meter, dB. 40.2 dB at 2437 MHz."""
    return 20.0 * math.log10(freq_mhz) - 27.55


def rssi_to_distance(rssi_dbm: float, freq_mhz: float = 2437.0,
                     p_tx_dbm: float = DEFAULT_P_TX_DBM,
                     n: float = DEFAULT_N_INDOOR) -> float:
    """Log-distance model inversion: meters from a single RSSI sample."""
    # M23: un RSSI NaN/inf propageait du garbage silencieux (repli 0.5 m) —
    # entrée non finie refusée bruyamment
    if not isinstance(rssi_dbm, (int, float)) or not math.isfinite(rssi_dbm):
        raise ValueError(f"rssi_dbm non fini: {rssi_dbm!r}")
    head = p_tx_dbm - fspl_1m(freq_mhz) - rssi_dbm
    d = 10.0 ** (head / (10.0 * n))
    return max(0.5, min(d, 500.0))   # physical sanity clamp


# --------------------------------------------------------------------------
# Geodesy — local flat earth
# --------------------------------------------------------------------------

def meters_per_degree(lat_deg: float) -> tuple:
    """WGS84 series: (meters per degree latitude, per degree longitude)."""
    f = math.radians(lat_deg)
    m_lat = (111132.92 - 559.82 * math.cos(2 * f)
             + 1.175 * math.cos(4 * f) - 0.0023 * math.cos(6 * f))
    m_lon = (111412.84 * math.cos(f) - 93.5 * math.cos(3 * f)
             + 0.118 * math.cos(5 * f))
    return m_lat, m_lon


def haversine_m(lat1, lon1, lat2, lon2) -> float:
    """Great-circle distance, meters, R = 6371008.8 m (mean Earth)."""
    r = 6371008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    # M24: l'erreur float peut dépasser 1.0 d'un cheveu près de l'antipode
    # → erreur de domaine asin
    return 2 * r * math.asin(math.sqrt(min(1.0, a)))


def to_enu(anchors, lat0=None, lon0=None):
    """anchors: [{'lat','lon',...}] -> list of (e, n, anchor) around centroid."""
    if lat0 is None:
        lat0 = sum(a["lat"] for a in anchors) / len(anchors)
    if lon0 is None:
        lon0 = sum(a["lon"] for a in anchors) / len(anchors)
    m_lat, m_lon = meters_per_degree(lat0)
    out = []
    for a in anchors:
        e = (a["lon"] - lon0) * m_lon
        n = (a["lat"] - lat0) * m_lat
        out.append((e, n, a))
    return out, lat0, lon0


def from_enu(e: float, n: float, lat0: float, lon0: float) -> tuple:
    m_lat, m_lon = meters_per_degree(lat0)
    return (lat0 + n / m_lat, lon0 + e / m_lon)


# --------------------------------------------------------------------------
# Trilateration
# --------------------------------------------------------------------------

def _solve2(a11, a12, a21, a22, b1, b2):
    """Cramer solve of a 2x2 system; None if singular."""
    det = a11 * a22 - a12 * a21
    if abs(det) < 1e-9:
        return None
    return ((b1 * a22 - b2 * a12) / det,
            (a11 * b2 - a21 * b1) / det)


def power_centroid_enu(points) -> tuple:
    """Weighted centroid with w = 10^(rssi/10) mW — the PHYSICAL weight.
    points: [(e, n, anchor_dict)]"""
    num_e = num_n = den = 0.0
    for e, n, a in points:
        rssi = a["rssi_dbm"]
        # M25: un RSSI non fini fabriquait un centroïde (nan, nan) silencieux
        # (nan <= 0 est faux → le garde den ne voyait rien) — ancre écartée
        if isinstance(rssi, bool) or not isinstance(rssi, (int, float)) \
                or not math.isfinite(rssi):
            continue
        w = 10.0 ** (rssi / 10.0)
        num_e += w * e
        num_n += w * n
        den += w
    if den <= 0:
        return None
    return (num_e / den, num_n / den)


def trilaterate_ls(points):
    """Weighted linearized least-squares position from range circles.

    points: [(e, n, {'rssi_dbm':...})] — ENU meters + anchor RSSI.
    Returns (e, n, rms_residual_m) or None if degenerate.
    """
    if len(points) < 3:
        return None
    e0, n0, a0 = points[0]
    r0 = rssi_to_distance(a0["rssi_dbm"], a0.get("freq_mhz", 2437.0))
    a11 = a12 = a21 = a22 = b1 = b2 = 0.0
    rows = []
    for e, n, a in points[1:]:
        dx, dy = e - e0, n - n0
        r = rssi_to_distance(a["rssi_dbm"], a.get("freq_mhz", 2437.0))
        bi = r0 * r0 - r * r + e * e - e0 * e0 + n * n - n0 * n0
        w = 1.0 / max(r * r, 0.25)
        rows.append((2 * dx, 2 * dy, bi, w))
    for x_, y_, bi, w in rows:
        a11 += w * x_ * x_
        a12 += w * x_ * y_
        a21 += w * y_ * x_
        a22 += w * y_ * y_
        b1 += w * x_ * bi
        b2 += w * y_ * bi
    sol = _solve2(a11, a12, a21, a22, b1, b2)
    if sol is None:
        return None
    e, n = sol
    # RMS residual: how well the solution explains every circle
    sq = 0.0
    for e_i, n_i, a in points:
        r = rssi_to_distance(a["rssi_dbm"], a.get("freq_mhz", 2437.0))
        d = math.hypot(e - e_i, n - n_i)
        sq += (d - r) ** 2
    return (e, n, math.sqrt(sq / len(points)))


def circle_circle(x0, y0, r0, x1, y1, r1):
    """Intersection of two range circles: 0, 1, or 2 (e, n) points."""
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy)
    if d > r0 + r1 or d < abs(r0 - r1) or d == 0:
        return []
    a = (r0 * r0 - r1 * r1 + d * d) / (2 * d)
    h2 = r0 * r0 - a * a
    if h2 < 0:
        return []
    h = math.sqrt(h2)
    xm, ym = x0 + a * dx / d, y0 + a * dy / d
    return [(xm + h * dy / d, ym - h * dx / d),
            (xm - h * dy / d, ym + h * dx / d)]


# --------------------------------------------------------------------------
# The orchestrator: fuse resolved anchors into one honest fix
# --------------------------------------------------------------------------

def fuse_position(resolved_aps, gps_last_known=None):
    """resolved_aps: [{'lat','lon','rssi_dbm','freq_mhz'?}, ...] — anchors with
    KNOWN positions (e.g. WiGLE-resolved BSSIDs) + the RSSI we just heard.

    Returns an estimate dict that degrades HONESTLY:
      >=3 anchors  -> weighted trilateration + power-centroid cross-check
      2 anchors    -> circle-circle intersection (two candidates, nearest
                      centroid wins, ambiguity reported)
      1 anchor     -> range circle around the anchor, no point invented
      0 anchors    -> last-known GPS or nothing
    """
    out = {"method": "none", "anchors_used": len(resolved_aps)}
    # L81: clés manquantes/non numériques explosaient en KeyError profond —
    # valider la surface publique ici, refus propre
    for a in resolved_aps:
        if not isinstance(a, dict):
            out.update(method="invalid-anchor", error="ancre non-dict")
            return out
        for k in ("lat", "lon", "rssi_dbm"):
            v = a.get(k)
            if isinstance(v, bool) or not isinstance(v, (int, float)) \
                    or not math.isfinite(v):
                out.update(method="invalid-anchor",
                           error=f"ancre invalide ({k!r})")
                return out
    if not resolved_aps:
        if gps_last_known:
            out.update(method="gps-last-known", lat=gps_last_known.get("lat"),
                       lon=gps_last_known.get("lon"),
                       note="no RF anchors resolved — last-known GPS only")
        return out

    pts, lat0, lon0 = to_enu(resolved_aps)

    if len(pts) >= 3:
        sol = trilaterate_ls(pts)
        cen = power_centroid_enu(pts)
        if sol is not None:
            e, n, rms = sol
            lat, lon = from_enu(e, n, lat0, lon0)
            out.update(method="rssi-trilateration-wls",
                       lat=round(lat, 6), lon=round(lon, 6),
                       residual_m=round(rms, 1),
                       centroid_cross_check={
                           "lat": round(from_enu(*cen, lat0, lon0)[0], 6),
                           "lon": round(from_enu(*cen, lat0, lon0)[1], 6)}
                       if cen else None,
                       note="ranges from log-distance model (n=2.8, Ptx=20dBm); "
                            "indoor multipath makes residual the honesty meter")
            return out
        if cen is not None:
            lat, lon = from_enu(cen[0], cen[1], lat0, lon0)
            out.update(method="power-centroid-fallback",
                       lat=round(lat, 6), lon=round(lon, 6),
                       note="anchors near-collinear — LS singular, centroid fallback")
            return out
        # M26: 3+ ancres, les deux solveurs inutilisables — l'ancien
        # fall-through atteignait la branche single-anchor et étiquetait
        # faux. Refus honnête, aucun point inventé.
        out.update(method="degenerate-anchors",
                   note="3+ ancres mais LS singulier et centroïde inutilisable — "
                        "aucun fix inventé")
        return out

    if len(pts) == 2:
        (e0, n0, a0), (e1, n1, a1) = pts
        r0 = rssi_to_distance(a0["rssi_dbm"], a0.get("freq_mhz", 2437.0))
        r1 = rssi_to_distance(a1["rssi_dbm"], a1.get("freq_mhz", 2437.0))
        hits = circle_circle(e0, n0, r0, e1, n1, r1)
        if not hits:
            mid_e, mid_n = (e0 + e1) / 2, (n0 + n1) / 2
            lat, lon = from_enu(mid_e, mid_n, lat0, lon0)
            out.update(method="two-anchor-midpoint",
                       lat=round(lat, 6), lon=round(lon, 6),
                       note="range circles do not intersect (model overshoot)")
            return out
        cen = power_centroid_enu(pts) or ((e0 + e1) / 2, (n0 + n1) / 2)
        best = min(hits, key=lambda p: math.hypot(p[0] - cen[0], p[1] - cen[1]))
        lat, lon = from_enu(best[0], best[1], lat0, lon0)
        out.update(method="circle-intersection",
                   lat=round(lat, 6), lon=round(lon, 6),
                   ambiguous=True,
                   note="two intersection candidates exist; power centroid picked one")
        return out

    # exactly one anchor: report the range circle, invent nothing
    a = resolved_aps[0]
    r = rssi_to_distance(a["rssi_dbm"], a.get("freq_mhz", 2437.0))
    out.update(method="single-anchor-range-circle",
               lat=round(a["lat"], 6), lon=round(a["lon"], 6), radius_m=round(r, 1),
               note="one anchor only — the phone is somewhere on this circle")
    return out


# --------------------------------------------------------------------------
# Timing advance (cell network distance bounds)
# --------------------------------------------------------------------------

def timing_advance_meters(radio: str, ta: int):
    """Distance bound from cell timing advance. GSM 553.5 m/TA, LTE 78.1 m/TA."""
    # L81: ta non numérique → TypeError; L83: bornes spec (GSM 0-63,
    # LTE ~0-1282) — un ta=10**6 ne fabrique plus une distance absurde
    if isinstance(ta, bool) or not isinstance(ta, (int, float)) or ta < 0:
        return None
    r = (radio or "").lower()
    if "gsm" in r or r == "2g":
        return round(min(ta, 63) * 553.5, 1)
    if "lte" in r or r == "4g":
        return round(min(ta, 1282) * 78.1, 1)
    return None   # NR TA semantics differ; refuse to guess


# --------------------------------------------------------------------------
# Self-test
# --------------------------------------------------------------------------

def selftest() -> int:
    ok = True

    def check(name, cond):
        nonlocal ok
        print(("PASS " if cond else "FAIL ") + name)
        ok = ok and cond

    check("FSPL(1m, 2437MHz) ~ 40.2 dB", abs(fspl_1m(2437.0) - 40.20) < 0.1)
    # inverse round-trip: rssi at d meters must invert back to d
    for d_true in (1.0, 5.0, 12.0, 30.0):
        f = 5180.0
        n = DEFAULT_N_INDOOR
        ptx = DEFAULT_P_TX_DBM
        rssi = ptx - fspl_1m(f) - 10 * n * math.log10(d_true)
        d_back = rssi_to_distance(rssi, f)
        check(f"round-trip d={d_true} m -> {d_back:.2f}", abs(d_back - d_true) < 1e-6)

    # meters per degree sanity (Paris-ish): ~111.3 km lat, ~73.5 km lon @48.85
    mlat, mlon = meters_per_degree(48.85)
    check("m/deg lat @48.85 ~ 111,200", 111_000 < mlat < 111_400)
    check("m/deg lon @48.85 ~ 73,600", 73_000 < mlon < 74_200)

    # trilateration: synthesize a phone at (10, 20) m from three anchors
    # around origin; read the RSSI the model predicts; solve back.
    truth = (10.0, 20.0)
    pts = []
    for (e, n) in ((0, 0), (30, 5), (8, 35), (40, 30)):
        d = math.hypot(truth[0] - e, truth[1] - n)
        rssi = DEFAULT_P_TX_DBM - fspl_1m(2437.0) - 10 * DEFAULT_N_INDOOR * math.log10(d)
        pts.append((e, n, {"rssi_dbm": rssi, "freq_mhz": 2437.0}))
    sol = trilaterate_ls(pts)
    check("trilateration recovers (10,20)", sol is not None
          and abs(sol[0] - 10.0) < 0.5 and abs(sol[1] - 20.0) < 0.5)
    if sol is not None:   # L82: une régression ne doit pas crasher le selftest
        print(f"     solved: ({sol[0]:.3f}, {sol[1]:.3f}) rms={sol[2]:.4f} m")

    # degenerate: three collinear anchors -> LS must refuse
    coll = [(0, 0, {"rssi_dbm": -50}), (10, 0, {"rssi_dbm": -50}), (20, 0, {"rssi_dbm": -50})]
    check("collinear anchors -> None (honest)", trilaterate_ls(coll) is None)

    # fuse end-to-end: 4 anchors around Paris, truth at +0.0001 deg lat
    lat0, lon0 = 48.8566, 2.3522
    m_lat, m_lon = meters_per_degree(lat0)
    aps = []
    for dlat, dlon in ((0.0008, 0.0008), (-0.0009, 0.0007), (0.0004, -0.0010), (-0.0006, -0.0009)):
        ae = dlon * m_lon            # anchor ENU position
        an = dlat * m_lat
        d = math.hypot(ae - truth[0], an - truth[1])
        rssi = DEFAULT_P_TX_DBM - fspl_1m(2437.0) - 10 * DEFAULT_N_INDOOR * math.log10(d)
        aps.append({"lat": lat0 + dlat, "lon": lon0 + dlon, "rssi_dbm": rssi, "freq_mhz": 2437.0})
    fix = fuse_position(aps)
    ok_fix = fix.get("method") == "rssi-trilateration-wls" and fix.get("lat") is not None
    check(f"fuse end-to-end -> {fix.get('method')}", ok_fix)
    if ok_fix:
        err_m = haversine_m(fix["lat"], fix["lon"], lat0 + truth[1] / m_lat, lon0 + truth[0] / m_lon)
        print(f"     fused fix error: {err_m:.1f} m")
        check("fused fix within 5 m of truth", err_m < 5.0)

    # two-anchor honest ambiguity
    fix2 = fuse_position(aps[:2])
    check("two anchors -> circle-intersection + ambiguous",
          fix2.get("method") == "circle-intersection" and fix2.get("ambiguous") is True)

    # single anchor: no invented point
    fix1 = fuse_position(aps[:1])
    check("one anchor -> range circle, radius present",
          fix1.get("method") == "single-anchor-range-circle" and fix1.get("radius_m"))

    # timing advance
    check("GSM TA=2 -> ~1107 m", timing_advance_meters("gsm", 2) == 1107.0)
    check("LTE TA=10 -> ~781 m", timing_advance_meters("lte", 10) == 781.0)
    check("NR refuses to guess", timing_advance_meters("nr", 5) is None)

    print("GEO_MATH SELFTEST " + ("PASSED" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(selftest())
