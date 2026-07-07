"""Paper portfolio state, persisted to state/portfolio.json (committed to git)."""
import json
import os
from datetime import datetime, timezone

STATE_DIR = os.path.join(os.path.dirname(__file__), "..", "state")


def state_path(mode):
    name = "portfolio_live.json" if mode == "live" else "portfolio.json"
    return os.path.join(STATE_DIR, name)


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def load(starting_bankroll, mode="paper"):
    path = state_path(mode)
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return {
        "created": _now_iso(),
        "mode": mode,
        "starting_bankroll": starting_bankroll,
        "cash": starting_bankroll,
        "peak_equity": starting_bankroll,
        "realized_pnl": 0.0,
        "halted": False,
        "halt_reason": "",
        # market_id -> position
        "positions": {},
        # market_id -> ISO date we last exited it (same-day re-entry cooldown)
        "cooldowns": {},
    }


def save(state):
    os.makedirs(STATE_DIR, exist_ok=True)
    state["updated"] = _now_iso()
    with open(state_path(state.get("mode", "paper")), "w") as f:
        json.dump(state, f, indent=2, sort_keys=True)
        f.write("\n")


def open_position(state, market, outcome_idx, fill):
    state["positions"][market["id"]] = {
        "market_id": market["id"],
        "question": market["question"],
        "slug": market["slug"],
        "token_id": market["token_ids"][outcome_idx],
        "outcome": market["outcomes"][outcome_idx],
        "outcome_idx": outcome_idx,
        "qty": fill["qty"],
        "entry_price": fill["avg_price"],
        "cost": fill["notional"],
        "opened": _now_iso(),
        "strategy": fill["strategy"],
        "rules_version": fill["rules_version"],
    }
    state["cash"] -= fill["notional"]


def close_position(state, market_id, proceeds):
    pos = state["positions"].pop(market_id)
    state["cash"] += proceeds
    pnl = proceeds - pos["cost"]
    state["realized_pnl"] += pnl
    state["cooldowns"][market_id] = datetime.now(timezone.utc).date().isoformat()
    return pos, pnl


def equity(state, marks):
    """Cash plus positions valued at `marks` (market_id -> price per share).

    Falls back to entry price when no mark is available.
    """
    total = state["cash"]
    for mid, pos in state["positions"].items():
        mark = marks.get(mid, pos["entry_price"])
        total += pos["qty"] * mark
    return total
