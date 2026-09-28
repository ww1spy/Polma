"""Honest edge statistics for family studies.

Why this exists: at 90%+ win rates a per-trade ROI has a standard deviation
of ~23%, so a 50-trade family's ROI estimate carries a ~±3.5% standard
error — the same size as the edges being hunted. Screening ~9 families a
week on point estimates promoted noise, which the next weeks then demoted
(MLB, WTI, RT, TRUMPSAY all went that way). Every verdict now comes with a
confidence bound, and promotion requires the bound — corrected for how
many families were screened — to clear zero.

Standard errors are CLUSTERED by entry day: favorites' losses arrive
clustered (LEARNINGS M2a), so treating trades as independent overstates
confidence.
"""
import math
from collections import defaultdict
from datetime import datetime, timezone
from statistics import NormalDist

Z90 = NormalDist().inv_cdf(0.90)  # one-sided 90%


def z_for(alpha):
    return NormalDist().inv_cdf(1.0 - alpha)


def roi_stats(rows):
    """rows: [{"ts": epoch_s, "pnl": $, "stake": $}] → dict with roi, se, n.

    ROI is the ratio estimator sum(pnl)/sum(stake); its standard error uses
    day-level clusters (delta method, small-sample G/(G-1) correction).
    """
    n = len(rows)
    if n == 0:
        return {"n": 0, "roi": None, "se": None, "days": 0}
    stake = sum(r["stake"] for r in rows)
    pnl = sum(r["pnl"] for r in rows)
    roi = pnl / stake
    clusters = defaultdict(float)
    for r in rows:
        day = datetime.fromtimestamp(r["ts"], timezone.utc).date()
        clusters[day] += r["pnl"] - roi * r["stake"]
    g = len(clusters)
    # Tail guard: a favorite family with few/no losses in-sample has a tiny
    # sample SE that says nothing about the -100% loss it hasn't seen yet.
    # The ROI after ONE more full-stake loss is a floor on any lower bound.
    roi_plus_loss = (pnl - stake / n) / (stake + stake / n)
    if g < 2:
        return {"n": n, "roi": roi, "se": None, "days": g, "roi_plus_loss": roi_plus_loss}
    var = (g / (g - 1)) * sum(e * e for e in clusters.values()) / stake ** 2
    return {"n": n, "roi": roi, "se": math.sqrt(var), "days": g,
            "roi_plus_loss": roi_plus_loss}


def bounds(st, z):
    """(lower, upper). Lower is also capped by the one-more-loss tail guard."""
    if st["se"] is None:
        return None, None
    lo = st["roi"] - z * st["se"]
    if st.get("roi_plus_loss") is not None:
        lo = min(lo, st["roi_plus_loss"])
    return lo, st["roi"] + z * st["se"]
