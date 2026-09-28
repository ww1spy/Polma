"""Weekly rolling re-validation of Kalshi family edges.

    python3 -m polma.revalidate [--fast-only] [--families A,B,C] [--days N]

Re-runs the family study over the available settled history (~60 days, the
API's retention window) for every LIVE include-list family and every
WATCHLIST family, plus the fast (15-min) families on 1-minute candles.
Writes a dated report to journal/revalidations/. It NEVER edits rules.

Each family is simulated two ways:
  - TAKER: what the engine does today — cross the spread at the ask, pay the
    taker fee.
  - MAKER: rest a limit bid one tick inside the spread instead; count it
    filled ONLY if a later trade printed at least one tick THROUGH our price
    (a trade through our level guarantees our order filled first — queue
    position can't save it), and cancel if unfilled by the entry cutoff.
    Maker fee is 0 on series with fee_type "quadratic" and 0.0175·P·(1−P)
    on "quadratic_with_maker_fees" series. Unfilled orders are opportunity
    cost, and fills that happen only because price fell toward us carry
    their adverse selection into the result (outcome = actual settlement).

Verdict policy (rev. 2026-09-28, owner-approved; see docs/LEARNINGS.md S1):
  - Statistics: ROI = sum(pnl)/sum(stake), standard error clustered by
    entry day (polma/stats.py).
  - PROMOTE-CANDIDATE: n >= 100 AND both halves > 0 AND the one-sided lower
    confidence bound at alpha = 0.10/k > 0, where k = number of families
    screened this run (Bonferroni). Promotion still needs a human.
  - LIVE family: DEMOTE if ROI < 0 or both halves < 0 (conservative, as
    before); REVIEW if one half < 0; flagged UNPROVEN if its uncorrected
    90% lower bound is <= 0 (informational — families promoted before the
    gates existed are grandfathered until they fail).
  - Fast paper families: DEMOTE/REVIEW pause/keep the paper experiment;
    controls are informational.
"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import stats
from .engine import load_rules
from .http import get_json
from .journal import JOURNAL_DIR
from .venues.kalshi import BASE, normalize, taker_fee, _is_junk

WATCHLIST = ["KXMLBGAME", "KXWTI", "KXFIBAGAME", "KXWNBAGAME", "KXRT",
             "KXTRUMPSAY", "KXWT20MATCH"]
DAYS = 60
STAKE = 10.0
MIN_N_PROMOTE = 100
FAMILY_ALPHA = 0.10
TICK = 0.01
MAKER_FEE_COEF = 0.0175

FAST_FAMILIES = [("KXETH15M", "paper"), ("KXBTC15M", "control")]
FAST_DAYS = 7
FAST_RULES = os.path.join(os.path.dirname(__file__), "..", "rules",
                          "rules-eth15.yaml")


def live_series_from_rules():
    rules = load_rules("kalshi")
    prefixes = rules["universe"].get("include_ticker_prefixes") or []
    return [p.rstrip("-") for p in prefixes], rules


def fee_type(series):
    try:
        d = get_json(f"{BASE}/series/{series}")
        return (d.get("series") or d).get("fee_type") or "quadratic"
    except Exception:
        return "unknown"


def maker_fee(price, qty, ftype):
    if ftype == "quadratic":
        return 0.0
    coef = MAKER_FEE_COEF if ftype == "quadratic_with_maker_fees" else 0.07
    fee = coef * price * (1.0 - price) * qty
    return -(-fee * 100 // 1) / 100.0  # ceil to the cent


def settled(series, days=DAYS, min_volume=1000):
    now = int(time.time())
    out, cursor = [], None
    for _ in range(5):
        params = {"limit": 1000, "status": "settled", "series_ticker": series,
                  "min_close_ts": now - days * 86400}
        if cursor:
            params["cursor"] = cursor
        d = get_json(f"{BASE}/markets", params=params)
        for r in d.get("markets", []):
            if _is_junk(r):
                continue
            m = normalize(r)
            if m["result"] in ("yes", "no") and m["volume_total"] >= min_volume and m["end_date"]:
                out.append(m)
        cursor = d.get("cursor")
        if not cursor:
            break
    return out


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fetch_candles(series, m, lookback_s, period):
    """[(ts, yes_bid, yes_ask, trade_low, trade_high)] — trade fields may be
    None for candles with no prints."""
    now = int(time.time())
    e = int(m["end_date"].timestamp())
    try:
        d = get_json(f"{BASE}/series/{series}/markets/{m['id']}/candlesticks",
                     params={"start_ts": e - lookback_s, "end_ts": min(e + 3600, now),
                             "period_interval": period})
    except Exception:
        return []
    out = []
    for c in d.get("candlesticks", []):
        b = _f((c.get("yes_bid") or {}).get("close_dollars"))
        a = _f((c.get("yes_ask") or {}).get("close_dollars"))
        if b is None or a is None:
            continue
        p = c.get("price") or {}
        out.append((c["end_period_ts"], b, a, _f(p.get("low_dollars")),
                    _f(p.get("high_dollars"))))
    return out


def _side_quotes(b, a, side):
    """(bid, ask) for the side we'd buy: YES directly, NO via 1 - YES."""
    if side == 0:
        return b, a
    return round(1 - a, 4), round(1 - b, 4)


def simulate(m, cs, rules, min_h, max_h, ftype):
    """→ {"taker": row|None, "maker": row|None, "maker_placed": bool}."""
    strat = rules["strategies"][0]
    exits = rules["exits"]
    lo, hi = strat["min_price"], strat["max_price"]
    out = {"taker": None, "maker": None, "maker_placed": False}
    if len(cs) < 3:
        return out
    rts = int(m["end_date"].timestamp())
    signal = None
    for i, (ts, b, a, _, _) in enumerate(cs):
        hl = (rts - ts) / 3600
        if hl < min_h:
            break
        if hl > max_h:
            continue
        if (a - b) > strat["max_spread"]:
            continue
        for side in (0, 1):
            sb, sa = _side_quotes(b, a, side)
            if lo <= sa <= hi:
                signal = (i, side, sb, sa)
                break
        if signal:
            break
    if not signal:
        return out
    i0, side, sb, sa = signal
    payout = round(m["prices"][side])

    def run_exits(start_idx, ep, qty):
        exit_p, fee_out = float(payout), 0.0
        for ts, b, a, _, _ in cs[start_idx + 1:]:
            ob, oa = _side_quotes(b, a, side)
            if oa <= ep - exits["stop_loss_points"]:
                exit_p = max(ob, 0.001)
                fee_out = taker_fee(exit_p, qty)
                break
            if ob >= exits["take_profit_bid"]:
                exit_p = ob
                fee_out = taker_fee(exit_p, qty)
                break
        return qty * exit_p - fee_out

    # TAKER: buy at the ask on the signal candle.
    qty = STAKE / sa
    cost = STAKE + taker_fee(sa, qty)
    out["taker"] = {"ts": cs[i0][0], "stake": STAKE,
                    "pnl": run_exits(i0, sa, qty) - cost}

    # MAKER: rest one tick above the side's bid (join the bid if the spread
    # is one tick). Filled only if a later print trades THROUGH our price.
    p = round(sb + TICK, 2) if sb + TICK < sa - 1e-9 else round(sb, 2)
    if not (lo - TICK <= p <= hi) or p <= 0:
        return out
    out["maker_placed"] = True
    for j in range(i0 + 1, len(cs)):
        ts, b, a, tlo, thi = cs[j]
        if (rts - ts) / 3600 < min_h:
            break  # entry cutoff: cancel
        if side == 0:
            filled = tlo is not None and tlo <= p - TICK + 1e-9
        else:
            filled = thi is not None and thi >= (1 - p) + TICK - 1e-9
        if filled:
            qty = STAKE / p
            cost = STAKE + maker_fee(p, qty, ftype)
            out["maker"] = {"ts": ts, "stake": STAKE,
                            "pnl": run_exits(j, p, qty) - cost}
            break
    return out


def _fmt(st, zc, halves):
    lo_b, _ = stats.bounds(st, zc)
    h1, h2 = halves
    lb = f"{lo_b:+.2%}" if lo_b is not None else "–"
    return f"{st['n']} | {st['roi']:+.2%} | ±{(st['se'] or 0):.2%} | {lb} | {h1:+.2%} | {h2:+.2%}"


def _halves(rows):
    rows = sorted(rows, key=lambda r: r["ts"])
    h = len(rows) // 2
    roi = lambda rs: sum(r["pnl"] for r in rs) / sum(r["stake"] for r in rs) if rs else 0.0
    return roi(rows[:h]), roi(rows[h:])


def study(fam, rules, days, min_vol, lookback_s, period, min_h, max_h):
    ms = settled(fam, days=days, min_volume=min_vol)
    ftype = fee_type(fam)
    with ThreadPoolExecutor(max_workers=4) as pool:
        cs_list = list(pool.map(lambda m: fetch_candles(fam, m, lookback_s, period), ms))
    sims = [simulate(m, cs, rules, min_h, max_h, ftype) for m, cs in zip(ms, cs_list)]
    taker = [s["taker"] for s in sims if s["taker"]]
    maker = [s["maker"] for s in sims if s["maker"]]
    placed = sum(1 for s in sims if s["maker_placed"])
    return taker, maker, placed, ftype


def main():
    args = sys.argv[1:]
    fast_only = "--fast-only" in args
    days = int(args[args.index("--days") + 1]) if "--days" in args else DAYS
    live, rules = live_series_from_rules()
    if "--families" in args:
        families = args[args.index("--families") + 1].split(",")
    else:
        families = [] if fast_only else sorted(set(live) | set(WATCHLIST))
    k = max(len(families), 1)
    zc = stats.z_for(FAMILY_ALPHA / k)
    today = datetime.now(timezone.utc).date().isoformat()
    lines = [f"# Weekly family re-validation — {today}", "",
             f"Rolling {days}-day study, rules v{rules.get('version')} semantics, "
             f"fees included. Stake ${STAKE:.0f}/trade. SE clustered by entry day; "
             f"LB = one-sided lower bound at alpha {FAMILY_ALPHA}/{k} "
             f"(z={zc:.2f}, Bonferroni over {k} families).", "",
             "| family | status | exec | n | ROI | SE | LB | half1 | half2 | fill% | verdict |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]
    flags = []
    for fam in families:
        taker, maker, placed, ftype = study(fam, rules, days, 1000, 4 * 86400, 60, 2, 72)
        status = "LIVE" if fam in live else "watch"
        for label, rows in (("taker", taker), (f"maker({ftype})", maker)):
            if len(rows) < 10:
                lines.append(f"| {fam} | {status} | {label} | {len(rows)} | – | – | – | – | – | – | insufficient data |")
                continue
            st = stats.roi_stats(rows)
            h1, h2 = _halves(rows)
            lo_c, _ = stats.bounds(st, zc)
            lo_90, _ = stats.bounds(st, stats.Z90)
            fill = f"{len(maker) / placed:.0%}" if label.startswith("maker") and placed else "–"
            if status == "LIVE" and label == "taker":
                if st["roi"] < 0 or (h1 < 0 and h2 < 0):
                    verdict = "**DEMOTE**"
                elif h1 < 0 or h2 < 0:
                    verdict = "REVIEW"
                elif lo_90 is None or lo_90 <= 0:
                    verdict = "healthy but UNPROVEN (90% LB ≤ 0)"
                else:
                    verdict = "healthy (proven)"
            elif (st["n"] >= MIN_N_PROMOTE and h1 > 0 and h2 > 0
                  and lo_c is not None and lo_c > 0):
                verdict = "**PROMOTE-CANDIDATE**" + (" (maker only)" if label != "taker" else "")
            elif st["roi"] > 0 and h1 > 0 and h2 > 0:
                verdict = "positive, not significant"
            else:
                verdict = "no edge"
            if "DEMOTE" in verdict or "REVIEW" in verdict or "PROMOTE" in verdict:
                flags.append(f"{fam} [{label}]: {verdict.strip('*')}")
            lines.append(f"| {fam} | {status} | {label} | {_fmt(st, zc, (h1, h2))} | {fill} | {verdict} |")

    fast_rules = load_rules("kalshi", path=FAST_RULES)
    min_h = fast_rules["universe"]["min_hours_to_resolution"]
    max_h = fast_rules["universe"]["max_days_to_resolution"] * 24
    kf = len(FAST_FAMILIES)
    zf = stats.z_for(FAMILY_ALPHA / kf)
    lines += ["", f"## Fast families — 1-min candles, rolling {FAST_DAYS}-day window, "
                  f"rules-eth15 v{fast_rules.get('version')} semantics", "",
              "| family | role | exec | n | ROI | SE | LB | half1 | half2 | fill% | verdict |",
              "|---|---|---|---|---|---|---|---|---|---|---|"]
    for fam, role in FAST_FAMILIES:
        taker, maker, placed, ftype = study(
            fam, fast_rules, FAST_DAYS, fast_rules["universe"]["min_volume_24h_usd"],
            20 * 60, 1, min_h, max_h)
        for label, rows in (("taker", taker), (f"maker({ftype})", maker)):
            if len(rows) < 30:
                lines.append(f"| {fam} | {role} | {label} | {len(rows)} | – | – | – | – | – | – | insufficient data |")
                continue
            st = stats.roi_stats(rows)
            h1, h2 = _halves(rows)
            lo_c, _ = stats.bounds(st, zf)
            fill = f"{len(maker) / placed:.0%}" if label.startswith("maker") and placed else "–"
            if role == "control":
                verdict = ("control positive — edge may be regime-wide"
                           if h1 > 0 and h2 > 0 else "control ≤ 0 (expected)")
            elif st["roi"] < 0 or (h1 < 0 and h2 < 0):
                # A paper book exists to measure; only stop it when it is
                # SIGNIFICANTLY negative, not on a noise-level point estimate.
                _, hi_90 = stats.bounds(st, stats.Z90)
                if label != "taker":
                    verdict = "no edge"
                elif hi_90 is not None and hi_90 < 0:
                    verdict = "**DEMOTE**"
                else:
                    verdict = "negative, not significant (keep measuring)"
            elif h1 < 0 or h2 < 0:
                verdict = "REVIEW" if label == "taker" else "mixed"
            elif lo_c is not None and lo_c > 0:
                verdict = "healthy (significant)"
            else:
                verdict = "healthy, not significant"
            if role != "control" and label == "taker" and verdict in ("**DEMOTE**", "REVIEW"):
                flags.append(f"{fam}: {verdict.strip('*')}")
            lines.append(f"| {fam} | {role} | {label} | {_fmt(st, zf, (h1, h2))} | {fill} | {verdict} |")

    lines += ["", "## Policy (rev. 2026-09-28)",
              f"- PROMOTE-CANDIDATE needs n ≥ {MIN_N_PROMOTE}, both halves > 0, and the "
              "Bonferroni-corrected lower bound > 0. Promotion still needs a human.",
              "- LIVE DEMOTE (ROI < 0 or both halves < 0) is conservative and may be "
              "applied by the weekly session. UNPROVEN is informational.",
              "- Maker rows are research: live execution is taker until a maker paper "
              "book confirms fills at live fidelity.",
              "- LB is also capped by the ROI after one more full-stake loss (tail guard: "
              "a family with no losses in-sample has a meaningless sample SE).",
              "- Fast-family DEMOTE (90% upper bound < 0) / REVIEW flags apply to the eth15 "
              "PAPER book; the control row is informational.",
              "- This script never edits rules itself."]
    out_dir = os.path.join(JOURNAL_DIR, "revalidations")
    os.makedirs(out_dir, exist_ok=True)
    suffix = "-fast-only" if fast_only else ("-custom" if "--families" in args else "")
    path = os.path.join(out_dir, f"{today}{suffix}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nreport → {os.path.relpath(path, os.path.join(JOURNAL_DIR, '..'))}")
    print("FLAGS:", "; ".join(flags) if flags else "none")


if __name__ == "__main__":
    main()
