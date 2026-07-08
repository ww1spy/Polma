"""The trading cycle: settle → mark → exit → scan → enter, under risk guardrails.

Venue-agnostic: everything market-specific lives behind polma.venues.
Select with POLMA_VENUE=polymarket|kalshi (default polymarket) and
POLMA_MODE=paper|live (default paper).
"""
import os
from datetime import datetime, timezone

import yaml

from . import journal, portfolio, risk
from .executor import KalshiLiveExecutor, PaperExecutor, PolymarketLiveExecutor
from .venues import get_venue

RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules", "rules.yaml")


def load_rules(venue_name=None, path=None):
    path = path or os.environ.get("POLMA_RULES") or RULES_PATH
    with open(path) as f:
        rules = yaml.safe_load(f)
    # Venue-specific overrides: venues differ in market scale, fee structure,
    # and which pockets are profitable (see journal/backtests/).
    ov = (rules.get("venue_overrides") or {}).get(venue_name) or {}
    rules["universe"] = {**rules["universe"], **(ov.get("universe") or {})}
    rules["exits"] = {**rules["exits"], **(ov.get("exits") or {})}
    rules["sizing"] = {**rules["sizing"], **(ov.get("sizing") or {})}
    strat_ov = ov.get("strategy") or {}
    rules["strategies"] = [{**s, **strat_ov} for s in rules["strategies"]]
    return rules


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def _hours_to_resolution(market, now=None):
    now = now or datetime.now(timezone.utc)
    if not market["end_date"]:
        return None
    return (market["end_date"] - now).total_seconds() / 3600.0


def settle_resolved(state, actions, venue):
    """Settle positions whose market has closed (shares pay $1 or $0)."""
    for mid in list(state["positions"]):
        pos = state["positions"][mid]
        try:
            market = venue.market(mid)
        except Exception as e:
            actions.append(f"WARN could not refresh market {mid}: {e}")
            continue
        if not market["closed"]:
            continue
        payout_per_share = (
            market["prices"][pos["outcome_idx"]] if market["prices"] else 0.0
        )
        proceeds = round(pos["qty"] * payout_per_share, 2)
        pos_closed, pnl = portfolio.close_position(state, mid, proceeds)
        journal.log_event(
            "SETTLE", venue=venue.name, profile=state.get("profile"), mode=state.get("mode", "paper"), market_id=mid, question=pos_closed["question"],
            outcome=pos_closed["outcome"], qty=pos_closed["qty"],
            entry_price=pos_closed["entry_price"], payout=payout_per_share,
            proceeds=proceeds, pnl=round(pnl, 2), strategy=pos_closed["strategy"],
            rules_version=pos_closed["rules_version"],
        )
        actions.append(f"SETTLE {pos_closed['question'][:60]} → ${pnl:+.2f}")
        if pnl < 0:
            pm = journal.write_postmortem(
                pos_closed, pnl, "settled against us", payout_per_share,
                "market resolved to the other outcome",
            )
            actions.append(f"POSTMORTEM written: {pm}")


def mark_positions(state, actions, venue):
    """Best bid/ask for every open position (bid = conservative valuation)."""
    marks = {}
    for mid, pos in state["positions"].items():
        try:
            book = venue.book(pos["token_id"])
            marks[mid] = {
                "bid": book["bids"][0][0] if book["bids"] else None,
                "ask": book["asks"][0][0] if book["asks"] else None,
            }
        except Exception as e:
            actions.append(f"WARN no book for {mid}: {e}")
    return marks


def apply_exits(state, rules, marks, executor, actions, venue):
    exits = rules["exits"]
    for mid in list(state["positions"]):
        pos = state["positions"][mid]
        mark = marks.get(mid) or {}
        bid, ask = mark.get("bid"), mark.get("ask")
        kind = None
        # Stop triggers on the ASK: a lone collapsed bid in a thin book is
        # noise, but a collapsed ask means the market has truly repriced.
        # (Backtests: bid-triggered stops phantom-fired constantly on Kalshi.)
        if ask is not None and ask <= pos["entry_price"] - exits["stop_loss_points"]:
            kind = "stop_loss"
        elif bid is not None and bid >= exits["take_profit_bid"]:
            kind = "take_profit"
        if kind is None:
            continue
        fill = executor.sell(pos["token_id"], pos["qty"])
        if fill is None:
            actions.append(f"WARN wanted to exit {mid} ({kind}) but book is empty")
            continue
        pos_closed, pnl = portfolio.close_position(state, mid, fill["notional"])
        journal.log_event(
            "EXIT", venue=venue.name, profile=state.get("profile"), mode=state.get("mode", "paper"), exit_kind=kind, market_id=mid,
            question=pos_closed["question"], outcome=pos_closed["outcome"],
            qty=fill["qty"], entry_price=pos_closed["entry_price"],
            exit_price=fill["avg_price"], proceeds=fill["notional"],
            fee=fill.get("fee", 0), pnl=round(pnl, 2),
            strategy=pos_closed["strategy"], rules_version=pos_closed["rules_version"],
        )
        actions.append(f"EXIT ({kind}) {pos_closed['question'][:60]} → ${pnl:+.2f}")
        if pnl < 0:
            pm = journal.write_postmortem(
                pos_closed, pnl, kind, fill["avg_price"],
                f"bid {bid} / ask {ask} vs entry {pos_closed['entry_price']:.3f}",
            )
            actions.append(f"POSTMORTEM written: {pm}")
        marks.pop(mid, None)


def in_universe(market, uni):
    if market["liquidity"] < uni["min_liquidity_usd"]:
        return False
    if market["volume_24h"] < uni["min_volume_24h_usd"]:
        return False
    hours = _hours_to_resolution(market)
    if hours is None or hours < uni["min_hours_to_resolution"]:
        return False
    if hours > uni["max_days_to_resolution"] * 24:
        return False
    q = market["question"].lower()
    if any(kw.lower() in q for kw in uni.get("exclude_question_keywords") or []):
        return False
    tick = str(market.get("event_ticker") or market["id"])
    if any(tick.startswith(p) for p in uni.get("exclude_ticker_prefixes") or []):
        return False
    return True


def find_candidates(rules, state, venue, max_markets=300):
    """Scan the universe and return [(market, outcome_idx, strategy_name), ...]."""
    uni = rules["universe"]
    markets = venue.open_markets(
        max_markets=max_markets,
        min_close_hours=uni["min_hours_to_resolution"],
        max_close_days=uni["max_days_to_resolution"],
    )
    today = _today()
    candidates = []
    for market in markets:
        if market["id"] in state["positions"]:
            continue
        if state["cooldowns"].get(market["id"]) == today:
            continue  # don't re-enter a market we exited today
        if not in_universe(market, rules["universe"]):
            continue
        for strat in rules["strategies"]:
            if not strat.get("enabled"):
                continue
            if market["spread"] > strat["max_spread"]:
                continue
            for idx, price in enumerate(market["prices"]):
                # Band-check what we'd actually PAY (the ask for this side),
                # not the mid — crossing the spread at the band edge otherwise
                # buys above max_price (live lesson: mid 0.97 filled at 0.982).
                ask = market["best_ask"] if idx == 0 else (
                    round(1.0 - market["best_bid"], 4)
                    if market["best_bid"] is not None else None)
                entry_price = ask if ask is not None else price
                if strat["min_price"] <= entry_price <= strat["max_price"]:
                    candidates.append((market, idx, strat["name"]))
                    break  # at most one outcome per market
            break  # first enabled strategy that fires wins
    # Most liquid first — easiest to enter and exit.
    candidates.sort(key=lambda c: c[0]["liquidity"], reverse=True)
    return candidates


def apply_entries(state, rules, limits, marks, candidates, executor, actions, venue):
    rules_version = rules.get("version", "?")
    entered = 0
    today_loss = journal.today_realized_loss(venue=venue.name,
                                             mode=state.get("mode", "paper"),
                                             profile=state.get("profile"))
    for market, idx, strat_name in candidates:
        if entered >= rules["sizing"]["max_new_positions_per_cycle"]:
            break
        eq = portfolio.equity(state, marks)
        notional = risk.max_notional(limits, rules, eq,
                                     peak_equity=state.get("peak_equity"))
        blocks = risk.entry_blocks(limits, state, eq, notional, today_loss)
        if notional > state["cash"]:
            blocks.append("insufficient cash")
        if blocks:
            journal.log_event(
                "BLOCK", venue=venue.name, profile=state.get("profile"), mode=state.get("mode", "paper"), market_id=market["id"],
                question=market["question"], reasons=blocks, rules_version=rules_version,
            )
            actions.append(f"BLOCK {market['question'][:60]}: {'; '.join(blocks)}")
            break  # risk blocks apply portfolio-wide; no point trying more
        fill = executor.buy(market["token_ids"][idx], notional)
        if fill is None:
            continue
        if market["min_order_size"] and fill["qty"] < market["min_order_size"]:
            continue  # too small to be a real order on this market
        fill["strategy"] = strat_name
        fill["rules_version"] = rules_version
        portfolio.open_position(state, market, idx, fill)
        journal.log_event(
            "ENTER", venue=venue.name, profile=state.get("profile"), mode=state.get("mode", "paper"), market_id=market["id"],
            question=market["question"], outcome=market["outcomes"][idx],
            strategy=strat_name, qty=fill["qty"], price=fill["avg_price"],
            notional=fill["notional"], fee=fill.get("fee", 0),
            liquidity=market["liquidity"], spread=market["spread"],
            end_date=market["end_date"].isoformat() if market["end_date"] else None,
            rules_version=rules_version,
        )
        actions.append(
            f"ENTER {market['question'][:60]} [{market['outcomes'][idx]}] "
            f"{fill['qty']} @ {fill['avg_price']:.3f} (${fill['notional']:.2f})"
        )
        entered += 1
    return entered


def make_executor(mode, venue):
    if mode != "live":
        return PaperExecutor(venue)
    if venue.name == "kalshi":
        return KalshiLiveExecutor()
    return PolymarketLiveExecutor()


def run_cycle():
    # Live mode requires BOTH the env switch and credentials — a paper run can
    # never accidentally place a real order.
    mode = os.environ.get("POLMA_MODE", "paper").lower()
    profile = os.environ.get("POLMA_PROFILE") or None
    if profile and mode == "live":
        raise RuntimeError("experimental profiles are PAPER-ONLY; unset "
                           "POLMA_PROFILE for live runs")
    venue = get_venue(os.environ.get("POLMA_VENUE", "polymarket"))
    rules = load_rules(venue.name)
    limits = risk.load_limits()
    state = portfolio.load(limits["starting_bankroll_usd"], mode=mode,
                           venue=venue.name, profile=profile)
    executor = make_executor(mode, venue)
    actions = [f"venue: {venue.name}, mode: {mode}"]

    # A brand-new LIVE portfolio starts from the real account balance, not
    # the paper bankroll constant.
    if (mode == "live" and venue.name == "kalshi"
            and not state["positions"] and not state.get("live_balance_synced")):
        from .venues.kalshi import fetch_balance
        balance = fetch_balance()
        if balance is None:
            raise RuntimeError("live mode: could not read Kalshi balance to "
                               "initialize the portfolio — refusing to trade blind")
        state.update(cash=balance, starting_bankroll=balance,
                     peak_equity=balance, live_balance_synced=True)
        actions.append(f"live portfolio initialized from account balance")

    settle_resolved(state, actions, venue)
    marks = mark_positions(state, actions, venue)
    apply_exits(state, rules, marks, executor, actions, venue)

    eq = portfolio.equity(state, marks)
    drawdown = risk.check_drawdown_halt(limits, state, eq)
    if state["halted"]:
        journal.log_event("HALT", venue=venue.name, profile=state.get("profile"), mode=state.get("mode", "paper"), reason=state["halt_reason"],
                          equity=round(eq, 2))
        actions.append(f"HALTED: {state['halt_reason']}")
    else:
        candidates = find_candidates(rules, state, venue)
        actions.append(f"scan: {len(candidates)} candidate(s) passed the rules")
        apply_entries(state, rules, limits, marks, candidates, executor, actions, venue)

    eq = portfolio.equity(state, marks)
    summary = {
        "venue": venue.name,
        "mode": mode,
        "profile": profile,
        "equity": round(eq, 2),
        "cash": round(state["cash"], 2),
        "open_positions": len(state["positions"]),
        "realized_pnl_total": round(state["realized_pnl"], 2),
        "drawdown_from_peak": round(drawdown, 4),
        "rules_version": rules.get("version"),
        "halted": state["halted"],
        "actions": actions,
    }
    journal.log_cycle(summary)
    portfolio.save(state)
    return summary
