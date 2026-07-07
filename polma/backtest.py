"""Backtest the current rules against recently-resolved markets.

    python3 -m polma.backtest [--markets 400]

This is the fast learning loop: instead of waiting days for paper positions
to resolve, replay the entry/exit rules over historical hourly prices of
markets that already resolved, and see what the rules WOULD have done.

Honest caveats (read before trusting the numbers):
- Prices are hourly midpoints; intra-hour spikes are invisible, so real
  stop-loss behavior is somewhat worse than simulated.
- Historical spreads/depth are unknown: we charge 0.5c slippage on entries
  and 1c on stop exits instead, and cannot apply the max_spread rule.
- Liquidity/volume filters use the market's final snapshot, not its value
  at entry time.
Results are directional, for comparing rule variants — not a P&L promise.
"""
import argparse
import json
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from . import gamma
from .engine import load_rules
from .http import get_json
from .journal import JOURNAL_DIR

CLOB_URL = "https://clob.polymarket.com"
ENTRY_SLIPPAGE = 0.005
STOP_SLIPPAGE = 0.01
STAKE = 10.0  # fixed per-trade stake so results are comparable


def fetch_resolved_markets(n):
    """Recently-ended, order-book, binary markets with a clean 0/1 resolution."""
    out, offset = [], 0
    while len(out) < n and offset < n * 6:
        rows = get_json(
            f"{gamma.GAMMA_URL}/markets",
            params={"closed": "true", "limit": 100, "offset": offset,
                    "order": "endDate", "ascending": "false"},
        )
        if not rows:
            break
        offset += 100
        for raw in rows:
            m = gamma.normalize(raw)
            if not (m["order_book"] and len(m["outcomes"]) == 2 and m["token_ids"]):
                continue
            if not m["prices"] or set(round(p) for p in m["prices"]) != {0, 1}:
                continue  # skip 50/50 or unresolved-looking payouts
            m["volume_total"] = float(raw.get("volumeNum") or 0)
            if m["volume_total"] < 20000:
                continue
            out.append(m)
    return out[:n]


def fetch_history(token_id):
    data = get_json(f"{CLOB_URL}/prices-history",
                    params={"market": token_id, "interval": "1m", "fidelity": 60})
    return [(pt["t"], float(pt["p"])) for pt in data.get("history", [])]


def simulate_market(market, rules):
    """Replay strategy rules on one resolved market. Returns a trade or None."""
    strat = next((s for s in rules["strategies"] if s.get("enabled")), None)
    if strat is None:
        return None
    uni = rules["universe"]
    hist0 = fetch_history(market["token_ids"][0])
    if len(hist0) < 3:
        return None
    resolution_ts = hist0[-1][0]

    # Both sides of a binary market from one history (side1 = 1 - side0).
    best = None
    for side in (0, 1):
        for ts, p0 in hist0:
            price = p0 if side == 0 else round(1.0 - p0, 4)
            hours_left = (resolution_ts - ts) / 3600.0
            if hours_left < uni["min_hours_to_resolution"]:
                break
            if hours_left > uni["max_days_to_resolution"] * 24:
                continue
            if strat["min_price"] <= price <= strat["max_price"]:
                if best is None or ts < best[0]:
                    best = (ts, side, price)
                break
    if best is None:
        return None

    entry_ts, side, raw_price = best
    entry = min(raw_price + ENTRY_SLIPPAGE, 0.999)
    payout = round(market["prices"][side])
    exits = rules["exits"]

    # Variant A: rules as written (stop loss / take profit active).
    exit_kind, exit_price = "settle", float(payout)
    for ts, p0 in hist0:
        if ts <= entry_ts:
            continue
        price = p0 if side == 0 else round(1.0 - p0, 4)
        if price <= entry - exits["stop_loss_points"]:
            exit_kind, exit_price = "stop_loss", max(price - STOP_SLIPPAGE, 0.001)
            break
        if price >= exits["take_profit_bid"]:
            exit_kind, exit_price = "take_profit", price
            break

    qty = STAKE / entry
    return {
        "question": market["question"],
        "outcome": market["outcomes"][side],
        "entry": round(entry, 4),
        "hours_before_resolution": round((resolution_ts - entry_ts) / 3600, 1),
        "exit_kind": exit_kind,
        "exit_price": round(exit_price, 4),
        "pnl": round(qty * exit_price - STAKE, 2),
        "pnl_no_stop": round(qty * payout - STAKE, 2),  # Variant B: hold to settle
        "volume_total": market["volume_total"],
    }


def summarize(trades):
    def stats(pnls):
        wins = sum(1 for p in pnls if p >= 0)
        return {
            "trades": len(pnls),
            "win_rate": round(wins / len(pnls), 3) if pnls else None,
            "total_pnl": round(sum(pnls), 2),
            "avg_pnl": round(sum(pnls) / len(pnls), 3) if pnls else None,
            "return_on_stakes": round(sum(pnls) / (STAKE * len(pnls)), 4) if pnls else None,
        }

    by_kind = {}
    for t in trades:
        by_kind.setdefault(t["exit_kind"], []).append(t["pnl"])
    return {
        "with_stop_loss": stats([t["pnl"] for t in trades]),
        "hold_to_settle_no_stop": stats([t["pnl_no_stop"] for t in trades]),
        "by_exit_kind": {k: stats(v) for k, v in sorted(by_kind.items())},
        "worst_losses": sorted(trades, key=lambda t: t["pnl"])[:5],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--markets", type=int, default=400)
    args = ap.parse_args()

    rules = load_rules()
    markets = fetch_resolved_markets(args.markets)
    print(f"backtesting rules v{rules.get('version')} on {len(markets)} resolved markets…")

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda m: simulate_market(m, rules), markets))
    trades = [t for t in results if t]

    summary = summarize(trades)
    report = {
        "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rules_version": rules.get("version"),
        "markets_scanned": len(markets),
        "summary": summary,
    }
    os.makedirs(os.path.join(JOURNAL_DIR, "backtests"), exist_ok=True)
    fname = f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H%M')}-v{rules.get('version')}.json"
    with open(os.path.join(JOURNAL_DIR, "backtests", fname), "w") as f:
        json.dump({**report, "trades": trades}, f, indent=2)

    print(json.dumps(report, indent=2))
    print(f"full trade list → journal/backtests/{fname}")


if __name__ == "__main__":
    main()
