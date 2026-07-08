"""Hard risk guardrails. These sit ABOVE the strategy rules and always win."""
import os

import yaml

LIMITS_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "risk_limits.yaml")


def load_limits():
    with open(LIMITS_PATH) as f:
        return yaml.safe_load(f)


def max_notional(limits, rules, eq, peak_equity=None):
    """Per-trade notional: the strategy's ask, capped by the hard limit and
    by POLMA_MAX_NOTIONAL_USD when set (used to floor sizing during live
    validation, e.g. =2 for the first real-money cycles).

    Also capped so a TOTAL loss of the position cannot single-handedly
    breach the drawdown-halt floor (LAD post-mortem, 2026-07-08: a floor
    only binds if every position's worst case respects it)."""
    want = min(
        rules["sizing"]["bankroll_fraction_per_trade"] * eq,
        rules["sizing"]["max_notional_per_trade_usd"],
    )
    hard_cap = limits["max_bankroll_fraction_per_trade"] * eq
    env_cap = float(os.environ.get("POLMA_MAX_NOTIONAL_USD", "inf"))
    floor_cap = float("inf")
    if peak_equity:
        floor = peak_equity * (1.0 - limits["max_drawdown_halt_fraction"])
        floor_cap = max(eq - floor, 0.0)
    return min(want, hard_cap, env_cap, floor_cap)


def entry_blocks(limits, state, eq, notional, today_realized_loss):
    """Return a list of reasons this entry must be refused (empty = allowed)."""
    blocks = []
    if state.get("halted"):
        blocks.append(f"portfolio halted: {state.get('halt_reason', 'unknown')}")
    if len(state["positions"]) >= limits["max_open_positions"]:
        blocks.append(f"max open positions ({limits['max_open_positions']}) reached")
    deployed = eq - state["cash"]
    if eq > 0 and (deployed + notional) / eq > limits["max_exposure_fraction"]:
        blocks.append(
            f"would exceed max exposure {limits['max_exposure_fraction']:.0%} of equity"
        )
    if today_realized_loss >= limits["max_daily_realized_loss_fraction"] * eq:
        blocks.append("daily realized loss limit hit; no new entries today")
    return blocks


def check_drawdown_halt(limits, state, eq):
    """Update peak equity; halt the portfolio if drawdown breaches the limit."""
    if eq > state["peak_equity"]:
        state["peak_equity"] = eq
    dd = 1.0 - eq / state["peak_equity"] if state["peak_equity"] > 0 else 0.0
    if dd >= limits["max_drawdown_halt_fraction"] and not state["halted"]:
        state["halted"] = True
        state["halt_reason"] = (
            f"drawdown {dd:.1%} from peak ${state['peak_equity']:.2f} breached "
            f"{limits['max_drawdown_halt_fraction']:.0%} halt threshold — "
            "human review required (set halted=false in state/portfolio.json to resume)"
        )
    return dd
