"""Portfolio and journal summary: python3 -m polma.report"""
import json
import os

from . import portfolio, risk
from .journal import JOURNAL_DIR


def main():
    limits = risk.load_limits()
    state = portfolio.load(limits["starting_bankroll_usd"])

    print(f"=== Polma portfolio ({state['mode']}) ===")
    print(f"cash:          ${state['cash']:.2f}")
    print(f"realized PnL:  ${state['realized_pnl']:+.2f}")
    print(f"peak equity:   ${state['peak_equity']:.2f}")
    print(f"halted:        {state['halted']}")
    print(f"\nopen positions ({len(state['positions'])}):")
    for pos in state["positions"].values():
        print(
            f"  {pos['qty']:>8.2f} × {pos['outcome']:<12} @ {pos['entry_price']:.3f} "
            f"(${pos['cost']:.2f})  {pos['question'][:70]}"
        )

    trades_path = os.path.join(JOURNAL_DIR, "trades.jsonl")
    if os.path.exists(trades_path):
        wins = losses = 0
        with open(trades_path) as f:
            for line in f:
                rec = json.loads(line)
                if rec.get("type") in ("EXIT", "SETTLE"):
                    if rec["pnl"] >= 0:
                        wins += 1
                    else:
                        losses += 1
        closed = wins + losses
        if closed:
            print(f"\nclosed trades: {closed}  (wins {wins} / losses {losses}, "
                  f"win rate {wins / closed:.0%})")


if __name__ == "__main__":
    main()
