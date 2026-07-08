"""Weekly rolling re-validation of Kalshi family edges.

    python3 -m polma.revalidate

Re-runs the family study over the full available settled history (~60 days,
the API's retention window) for every LIVE include-list family and every
WATCHLIST family, with half-period consistency. Writes a dated report to
journal/revalidations/ and prints verdicts. It NEVER edits rules itself —
demotion/promotion policy (docs/LEARNINGS.md M2a):
  - DEMOTE (flag) a live family if full-period ROI < 0 OR both halves < 0.
  - REVIEW (flag) a live family if either half < 0.
  - PROMOTE-CANDIDATE (flag) a watchlist family only if n >= 30 AND both
    halves positive AND a mechanism is on record — promotion still needs
    a human (or in-session review) to apply.
"""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from .engine import load_rules
from .http import get_json
from .journal import JOURNAL_DIR
from .venues.kalshi import BASE, normalize, taker_fee, _is_junk

WATCHLIST = ["KXMLBGAME", "KXWTI", "KXFIBAGAME", "KXWNBAGAME", "KXRT",
             "KXTRUMPSAY", "KXWT20MATCH"]
DAYS = 60
STAKE = 10.0


def live_series_from_rules():
    rules = load_rules("kalshi")
    prefixes = rules["universe"].get("include_ticker_prefixes") or []
    return [p.rstrip("-") for p in prefixes], rules


def settled(series):
    now = int(time.time())
    out, cursor = [], None
    for _ in range(3):
        params = {"limit": 1000, "status": "settled", "series_ticker": series,
                  "min_close_ts": now - DAYS * 86400}
        if cursor:
            params["cursor"] = cursor
        d = get_json(f"{BASE}/markets", params=params)
        for r in d.get("markets", []):
            if _is_junk(r):
                continue
            m = normalize(r)
            if m["result"] in ("yes", "no") and m["volume_total"] >= 1000 and m["end_date"]:
                out.append(m)
        cursor = d.get("cursor")
        if not cursor:
            break
    return out


def candles(job):
    s, m = job
    now = int(time.time())
    e = int(m["end_date"].timestamp())
    try:
        d = get_json(f"{BASE}/series/{s}/markets/{m['id']}/candlesticks",
                     params={"start_ts": e - 4*86400, "end_ts": min(e + 3600, now),
                             "period_interval": 60})
    except Exception:
        return m["id"], []
    return m["id"], [(c["end_period_ts"], float(c["yes_bid"]["close_dollars"]),
                      float(c["yes_ask"]["close_dollars"]))
                     for c in d.get("candlesticks", [])
                     if c.get("yes_bid", {}).get("close_dollars") is not None
                     and c.get("yes_ask", {}).get("close_dollars") is not None]


def sim(m, cs, rules):
    strat = rules["strategies"][0]
    exits = rules["exits"]
    lo, hi = strat["min_price"], strat["max_price"]
    if len(cs) < 3:
        return None
    rts = cs[-1][0]
    entry = None
    for ts, b, a in cs:
        hl = (rts - ts) / 3600
        if hl < 2:
            break
        if hl > 72:
            continue
        for side in (0, 1):
            ask = a if side == 0 else round(1 - b, 4)
            if (a - b) <= strat["max_spread"] and lo <= ask <= hi:
                entry = (ts, side, ask)
                break
        if entry:
            break
    if not entry:
        return None
    ets, side, ep = entry
    qty = STAKE / ep
    fee_in = taker_fee(ep, qty)
    payout = round(m["prices"][side])
    exit_p, fee_out = float(payout), 0.0
    for ts, b, a in cs:
        if ts <= ets:
            continue
        oa = a if side == 0 else round(1 - b, 4)
        ob = b if side == 0 else round(1 - a, 4)
        if oa <= ep - exits["stop_loss_points"]:
            exit_p = max(ob, 0.001)
            fee_out = taker_fee(exit_p, qty)
            break
        if ob >= exits["take_profit_bid"]:
            exit_p = ob
            fee_out = taker_fee(exit_p, qty)
            break
    return {"ts": ets, "pnl": qty*exit_p - fee_out - (STAKE + fee_in)}


def main():
    live, rules = live_series_from_rules()
    families = sorted(set(live) | set(WATCHLIST))
    today = datetime.now(timezone.utc).date().isoformat()
    lines = [f"# Weekly family re-validation — {today}",
             "",
             f"Rolling {DAYS}-day study, current rules "
             f"(v{rules.get('version')}) semantics, fees included.",
             "",
             "| family | status | n | win% | ROI | half1 | half2 | verdict |",
             "|---|---|---|---|---|---|---|---|"]
    flags = []
    for fam in families:
        ms = settled(fam)
        with ThreadPoolExecutor(max_workers=8) as pool:
            cmap = dict(pool.map(candles, ((fam, m) for m in ms)))
        rows = [r for m in ms if (r := sim(m, cmap.get(m["id"], []), rules))]
        status = "LIVE" if fam in live else "watch"
        if len(rows) < 10:
            lines.append(f"| {fam} | {status} | {len(rows)} | – | – | – | – | insufficient data |")
            continue
        rows.sort(key=lambda r: r["ts"])
        half = len(rows) // 2
        roi = lambda rs: sum(r["pnl"] for r in rs) / (STAKE * len(rs))
        r_all, r1, r2 = roi(rows), roi(rows[:half]), roi(rows[half:])
        win = sum(1 for r in rows if r["pnl"] > 0) / len(rows)
        if fam in live:
            if r_all < 0 or (r1 < 0 and r2 < 0):
                verdict = "**DEMOTE**"
            elif r1 < 0 or r2 < 0:
                verdict = "REVIEW"
            else:
                verdict = "healthy"
        else:
            verdict = ("PROMOTE-CANDIDATE" if len(rows) >= 30 and r1 > 0 and r2 > 0
                       else "keep watching")
        if verdict not in ("healthy", "keep watching"):
            flags.append(f"{fam}: {verdict}")
        lines.append(f"| {fam} | {status} | {len(rows)} | {win:.0%} | {r_all:+.2%} "
                     f"| {r1:+.2%} | {r2:+.2%} | {verdict} |")
    lines += ["", "## Policy",
              "- DEMOTE flags: remove from the live include-list (conservative "
              "direction — may be applied by the weekly session).",
              "- PROMOTE-CANDIDATE flags: require mechanism + human/in-session "
              "review before entering the live list.",
              "- This script never edits rules itself."]
    out_dir = os.path.join(JOURNAL_DIR, "revalidations")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"{today}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"\nreport → {os.path.relpath(path, os.path.join(JOURNAL_DIR, '..'))}")
    print("FLAGS:", "; ".join(flags) if flags else "none")


if __name__ == "__main__":
    main()
