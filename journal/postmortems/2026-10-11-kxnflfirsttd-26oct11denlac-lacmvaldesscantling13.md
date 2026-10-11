# Loss post-mortem: Marquez Valdes-Scantling: 1st Touchdown

- **Date closed:** 2026-10-11
- **Exit type:** take_profit
- **Strategy:** favorite_discount (rules v2)
- **Position:** 40.45 × "No" @ 0.973 (cost $39.44)
- **Exit price:** 0.961
- **PnL:** $-0.69
- **Opened:** 2026-10-10T20:20:27+00:00
- **Context at exit:** bid 0.99 / ask None vs entry 0.973

## What the rules saw at entry
"No" on a first-touchdown scorer at 0.973 (aggressive book, about $39 stake), roughly
a day before kickoff.

## Why it lost
This is an execution problem, not a thesis problem: the No would very likely have
settled at $1. Take-profit fires when the top-of-book bid is at or above `take_profit_bid`
(engine.py:116). The bid showed 0.99, but it was thin and the ask side was empty,
so the sell walked the book to an average of 0.961, below the 0.973 entry.
With entry this close to the take-profit level, any depth walk turns a "profit"
exit into a loss.

## Rule change proposed
Not applied; this is for the owner to decide. Two options:
1. Give `favorite_discount` in rules-aggressive a hold-to-settle take-profit for
   entries at 0.97 or above, the same pattern `rt_last_mile` already uses.
2. In code, skip a take-profit when the estimated fill (from depth) is below
   entry. That is an engine change and needs approval before it is made.
The loss is small ($0.69), but the pattern repeats on every high-priced entry.
