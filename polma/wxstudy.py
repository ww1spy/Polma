"""Settlement-lag study for Kalshi daily-high temperature markets (KXHIGH*).

    python3 -m polma.wxstudy [--days 30] [--margin 1.0] [--series KXHIGHNY,...]

Mechanism (LEARNINGS S6): a day's maximum can only go UP. Once an official
station has already observed a temperature above a market's threshold, the
outcome is decided hours before the market closes at local midnight:
  - "greater than X"  → YES is locked once the observed max ≥ X+1
  - "between A-B"     → NO  is locked once the observed max ≥ B+1
  - "less than X"     → NO  is locked once the observed max ≥ X
This is a decided fact, not a forecast (the July LA loss was a forecast).

Data: hourly/special METARs from the Iowa Environmental Mesonet ASOS archive
(free, public; the same observations NWS uses) for each market's settlement
station; Kalshi hourly candles for the quotes. The climate day runs midnight
to midnight LOCAL STANDARD time. `margin` (°F) is extra cushion on the METAR
value to absorb rounding/conversion differences vs the official daily max.

For each locked market we "buy" the locked side at the ask on the first
hourly candle ≥ LAG_MIN after the locking observation, pay the taker fee, and
hold to settlement. A locked trade that settles the other way is a DATA
MISMATCH — the risk this study exists to measure.
"""
import csv
import io
import math
import os
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from . import stats
from .http import get_json
from .journal import JOURNAL_DIR

BASE = "https://api.elections.kalshi.com/trade-api/v2"
IEM = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"

# series -> (IEM station id, UTC offset of local STANDARD time)
STATIONS = {
    "KXHIGHNY": ("NYC", -5), "KXHIGHCHI": ("MDW", -6), "KXHIGHMIA": ("MIA", -5),
    "KXHIGHAUS": ("AUS", -6), "KXHIGHLAX": ("LAX", -8), "KXHIGHDEN": ("DEN", -7),
    "KXHIGHPHIL": ("PHL", -5), "KXHIGHTATL": ("ATL", -5), "KXHIGHTDAL": ("DFW", -6),
    "KXHIGHTSEA": ("SEA", -8), "KXHIGHTPHX": ("PHX", -7), "KXHIGHTSFO": ("SFO", -8),
    "KXHIGHTMIN": ("MSP", -6), "KXHIGHTBOS": ("BOS", -5), "KXHIGHTDC": ("DCA", -5),
}
STAKE = 10.0
LAG_MIN = 10          # observation publication lag before we could act
MAX_ASK = 0.99        # above this, fees eat everything
TAKER_COEF = 0.07


def taker_fee(p, qty):
    return math.ceil(TAKER_COEF * p * (1 - p) * qty * 100) / 100.0


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def settled_markets(series, days):
    now = int(time.time())
    out, cursor = [], None
    for _ in range(10):
        params = {"limit": 1000, "status": "settled", "series_ticker": series,
                  "min_close_ts": now - days * 86400}
        if cursor:
            params["cursor"] = cursor
        d = get_json(f"{BASE}/markets", params=params)
        for m in d.get("markets", []):
            if m.get("result") in ("yes", "no"):
                out.append(m)
        cursor = d.get("cursor")
        if not cursor:
            break
    return out


def climate_date(m):
    """Event date from the ticker, e.g. KXHIGHNY-26SEP27-T72 → 2026-09-27."""
    code = m["event_ticker"].split("-")[1]
    return datetime.strptime(code, "%y%b%d").date()


def observations(station, start, end):
    """[(utc_ts, tmpf)] for routine + special METARs."""
    params = {"station": station, "data": "tmpf", "tz": "Etc/UTC",
              "format": "onlycomma", "latlon": "no", "missing": "M",
              "trace": "T", "direct": "no", "report_type": [3, 4],
              "year1": start.year, "month1": start.month, "day1": start.day,
              "year2": end.year, "month2": end.month, "day2": end.day}
    import requests
    # IEM throttles bursts from shared IPs (same class as the Kalshi 429s):
    # one station at a time, back off and retry.
    for wait in (5, 15, 30, 60, 120, None):
        r = requests.get(IEM, params=params, timeout=120,
                         headers={"User-Agent": "polma-research/1.0"})
        if r.status_code not in (429, 503) or wait is None:
            break
        time.sleep(wait)
    r.raise_for_status()
    out = []
    for row in csv.DictReader(io.StringIO(r.text)):
        t = _f(row.get("tmpf"))
        if t is None:
            continue
        ts = datetime.strptime(row["valid"], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        out.append((ts.timestamp(), t))
    return sorted(out)


def lock_threshold(m):
    """(side, observed-max °F that locks it) or None if no lock is possible."""
    st, fl, cap = m.get("strike_type"), _f(m.get("floor_strike")), _f(m.get("cap_strike"))
    if st == "greater" and fl is not None:
        return 0, fl + 1
    if st == "between" and cap is not None:
        return 1, cap + 1
    if st == "less" and cap is not None:
        return 1, cap
    return None


def lock_time(m, obs, offset_h, margin):
    lk = lock_threshold(m)
    if not lk:
        return None
    side, thresh = lk
    d = climate_date(m)
    start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc) - timedelta(hours=offset_h)
    t0, t1 = start.timestamp(), (start + timedelta(days=1)).timestamp()
    run = -1e9
    for ts, t in obs:
        if ts < t0:
            continue
        if ts >= t1:
            break
        run = max(run, t)
        if run >= thresh + margin:
            return side, ts, run
    return None


def candles(series, ticker, start_ts, end_ts):
    try:
        d = get_json(f"{BASE}/series/{series}/markets/{ticker}/candlesticks",
                     params={"start_ts": int(start_ts), "end_ts": int(end_ts),
                             "period_interval": 60})
    except Exception:
        return []
    out = []
    for c in d.get("candlesticks", []):
        b = _f((c.get("yes_bid") or {}).get("close_dollars"))
        a = _f((c.get("yes_ask") or {}).get("close_dollars"))
        if b is not None and a is not None:
            out.append((c["end_period_ts"], b, a))
    return out


def study_series(series, days, margin):
    station, off = STATIONS[series]
    ms = settled_markets(series, days)
    if not ms:
        return []
    dates = [climate_date(m) for m in ms]
    obs = observations(station, min(dates) - timedelta(days=1), max(dates) + timedelta(days=2))
    todo = []
    for m in ms:
        lk = lock_time(m, obs, off, margin)
        if lk:
            todo.append((m, lk))
    close_ts = lambda m: datetime.fromisoformat(m["close_time"].replace("Z", "+00:00")).timestamp()
    with ThreadPoolExecutor(max_workers=4) as pool:
        cs_list = list(pool.map(
            lambda x: candles(series, x[0]["ticker"], x[1][1], close_ts(x[0])), todo))
    rows = []
    for (m, (side, lts, seen)), cs in zip(todo, cs_list):
        if lts >= close_ts(m):
            continue
        entry = next((c for c in cs if c[0] >= lts + LAG_MIN * 60), None)
        if not entry:
            continue
        ts, b, a = entry
        ask = a if side == 0 else round(1 - b, 4)
        won = (m["result"] == "yes") == (side == 0)
        row = {"series": series, "ticker": m["ticker"], "side": "YES" if side == 0 else "NO",
               "lock_ts": lts, "entry_ts": ts, "ask": ask, "seen_max": seen,
               "won": won, "hours_to_close": (close_ts(m) - ts) / 3600,
               "volume": _f(m.get("volume_fp") or m.get("volume")) or 0}
        if 0 < ask <= MAX_ASK:
            qty = STAKE / ask
            cost = STAKE + taker_fee(ask, qty)
            row.update(ts=ts, stake=cost, pnl=(qty if won else 0.0) - cost)
        rows.append(row)
    return rows


def main():
    args = sys.argv[1:]
    days = int(args[args.index("--days") + 1]) if "--days" in args else 30
    margin = float(args[args.index("--margin") + 1]) if "--margin" in args else 1.0
    series = (args[args.index("--series") + 1].split(",") if "--series" in args
              else list(STATIONS))
    all_rows = []
    for s in series:
        try:
            rows = study_series(s, days, margin)
        except Exception as e:
            print(f"{s}: failed ({e})", file=sys.stderr)
            continue
        all_rows += rows
        print(f"{s}: {len(rows)} locked markets", file=sys.stderr)

    today = datetime.now(timezone.utc).date().isoformat()
    lines = [f"# Temperature settlement-lag study — {today}", "",
             f"{days} days, margin {margin}°F on the METAR max, entry at the first hourly "
             f"candle ≥{LAG_MIN} min after the locking observation, taker fee, "
             f"${STAKE:.0f} stake, hold to settlement. Trades only when ask ≤ {MAX_ASK}.", "",
             "| series | locked | tradable (ask≤0.99) | mismatches | avg ask | n | ROI | SE | LB90 | net $ |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    by = defaultdict(list)
    for r in all_rows:
        by[r["series"]].append(r)
    for s in list(by) + ["ALL"]:
        rs = all_rows if s == "ALL" else by[s]
        tr = [r for r in rs if "pnl" in r]
        mism = sum(1 for r in rs if not r["won"])
        if tr:
            st = stats.roi_stats(tr)
            lo, _ = stats.bounds(st, stats.Z90)
            avg = sum(r["ask"] for r in tr) / len(tr)
            lines.append(f"| {s} | {len(rs)} | {len(tr)} | {mism} | {avg:.3f} | {st['n']} | "
                         f"{st['roi']:+.2%} | ±{(st['se'] or 0):.2%} | "
                         f"{'–' if lo is None else f'{lo:+.2%}'} | "
                         f"${sum(r['pnl'] for r in tr):+.2f} |")
        else:
            lines.append(f"| {s} | {len(rs)} | 0 | {mism} | – | 0 | – | – | – | – |")
    buckets = defaultdict(int)
    for r in all_rows:
        buckets[min(math.floor(r["ask"] * 100) / 100, 1.0)] += 1
    lines += ["", "Ask for the locked side at entry (count of locked markets):", "",
              "| ask | count |", "|---|---|"]
    for k in sorted(buckets):
        lines.append(f"| {k:.2f} | {buckets[k]} |")
    mis = [r for r in all_rows if not r["won"]]
    if mis:
        lines += ["", "Mismatches (locked by METAR but settled the other way):", ""]
        for r in mis:
            lines.append(f"- {r['ticker']} {r['side']} seen max {r['seen_max']:.1f}°F, ask {r['ask']:.2f}")
    out_dir = os.path.join(JOURNAL_DIR, "backtests")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, f"wx-settlement-lag-{today}.md")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"report → {path}")


if __name__ == "__main__":
    main()
