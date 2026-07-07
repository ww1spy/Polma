"""The trading cycle: settle → mark → exit → scan → enter, under risk guardrails."""
import os
from datetime import datetime, timezone

import yaml

from . import clob, gamma, journal, portfolio, risk
from .executor import PaperExecutor

RULES_PATH = os.path.join(os.path.dirname(__file__), "..", "rules", "rules.yaml")


def load_rules():
    with open(RULES_PATH) as f:
        return yaml.safe_load(f)


def _today():
    return datetime.now(timezone.utc).date().isoformat()


def settle_resolved(state, actions):
    """Settle positions whose market has closed (shares pay $1 or $0)."""
    for mid in list(state["positions"]):
        pos = state["positions"][mid]
        try:
            market = gamma.fetch_market(mid)
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
        rec = journal.log_event(
            "SETTLE", market_id=mid, question=pos_closed["question"],
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


def mark_positions(state, actions):
    """Best-bid marks for every open position (conservative valuation)."""
    marks = {}
    for mid, pos in state["positions"].items():
        try:
            book = clob.get_book(pos["token_id"])
            bid = clob.best_bid(book)
            if bid is not None:
                marks[mid] = bid
        except Exception as e:
            actions.append(f"WARN no book for {mid}: {e}")
    return marks


def apply_exits(state, rules, marks, executor, actions):
    exits = rules["exits"]
    for mid in list(state["positions"]):
        pos = state["positions"][mid]
        bid = marks.get(mid)
        if bid is None:
            continue
        kind = None
        if bid <= pos["entry_price"] - exits["stop_loss_points"]:
            kind = "stop_loss"
        elif bid >= exits["take_profit_bid"]:
            kind = "take_profit"
        if kind is None:
            continue
        fill = executor.sell(pos["token_id"], pos["qty"])
        if fill is None:
            actions.append(f"WARN wanted to exit {mid} ({kind}) but book is empty")
            continue
        pos_closed, pnl = portfolio.close_position(state, mid, fill["notional"])
        journal.log_event(
            "EXIT", exit_kind=kind, market_id=mid, question=pos_closed["question"],
            outcome=pos_closed["outcome"], qty=fill["qty"],
            entry_price=pos_closed["entry_price"], exit_price=fill["avg_price"],
            proceeds=fill["notional"], pnl=round(pnl, 2),
            strategy=pos_closed["strategy"], rules_version=pos_closed["rules_version"],
        )
        actions.append(f"EXIT ({kind}) {pos_closed['question'][:60]} → ${pnl:+.2f}")
        if pnl < 0:
            pm = journal.write_postmortem(
                pos_closed, pnl, kind, fill["avg_price"],
                f"best bid {bid:.3f} vs entry {pos_closed['entry_price']:.3f}",
            )
            actions.append(f"POSTMORTEM written: {pm}")
        marks.pop(mid, None)


def in_universe(market, uni):
    if market["liquidity"] < uni["min_liquidity_usd"]:
        return False
    if market["volume_24h"] < uni["min_volume_24h_usd"]:
        return False
    hours = gamma.hours_to_resolution(market)
    if hours is None or hours < uni["min_hours_to_resolution"]:
        return False
    if hours > uni["max_days_to_resolution"] * 24:
        return False
    q = market["question"].lower()
    if any(kw.lower() in q for kw in uni.get("exclude_question_keywords") or []):
        return False
    return True


def find_candidates(rules, state, max_markets=300):
    """Scan the universe and return [(market, outcome_idx, strategy_name), ...]."""
    markets = gamma.fetch_open_markets(max_markets=max_markets)
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
                if strat["min_price"] <= price <= strat["max_price"]:
                    candidates.append((market, idx, strat["name"]))
                    break  # at most one outcome per market
            break  # first enabled strategy that fires wins
    # Most liquid first — easiest to enter and exit.
    candidates.sort(key=lambda c: c[0]["liquidity"], reverse=True)
    return candidates


def apply_entries(state, rules, limits, marks, candidates, executor, actions):
    rules_version = rules.get("version", "?")
    entered = 0
    today_loss = journal.today_realized_loss()
    for market, idx, strat_name in candidates:
        if entered >= rules["sizing"]["max_new_positions_per_cycle"]:
            break
        eq = portfolio.equity(state, marks)
        notional = risk.max_notional(limits, rules, eq)
        blocks = risk.entry_blocks(limits, state, eq, notional, today_loss)
        if notional > state["cash"]:
            blocks.append("insufficient cash")
        if blocks:
            journal.log_event(
                "BLOCK", market_id=market["id"], question=market["question"],
                reasons=blocks, rules_version=rules_version,
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
            "ENTER", market_id=market["id"], question=market["question"],
            outcome=market["outcomes"][idx], strategy=strat_name,
            qty=fill["qty"], price=fill["avg_price"], notional=fill["notional"],
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


def run_cycle():
    rules = load_rules()
    limits = risk.load_limits()
    state = portfolio.load(limits["starting_bankroll_usd"])
    executor = PaperExecutor()  # live mode is a deliberate, later, explicit switch
    actions = []

    settle_resolved(state, actions)
    marks = mark_positions(state, actions)
    apply_exits(state, rules, marks, executor, actions)

    eq = portfolio.equity(state, marks)
    drawdown = risk.check_drawdown_halt(limits, state, eq)
    if state["halted"]:
        journal.log_event("HALT", reason=state["halt_reason"], equity=round(eq, 2))
        actions.append(f"HALTED: {state['halt_reason']}")
    else:
        candidates = find_candidates(rules, state)
        actions.append(f"scan: {len(candidates)} candidate(s) passed the rules")
        apply_entries(state, rules, limits, marks, candidates, executor, actions)

    eq = portfolio.equity(state, marks)
    summary = {
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
