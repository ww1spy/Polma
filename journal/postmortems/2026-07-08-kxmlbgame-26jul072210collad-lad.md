# Loss post-mortem: Colorado vs Los Angeles D Winner?

- **Date closed:** 2026-07-08 (settled ~05:15 UTC)
- **Exit type:** settled against us
- **Strategy:** variance_leg (rules v5, 6h challenge)
- **Position:** 40.0 × "Yes" (LAD) @ 0.740 (cost $30.14 incl. $0.54 fee)
- **Exit price:** 0.000
- **PnL:** -$30.14
- **Opened:** 2026-07-08T01:39:49+00:00, pre-game
- **Context at exit:** market resolved to the other outcome

## What the rules saw at entry
Deliberate, pre-registered variance leg — NOT a strategy-band trade. LAD
0.73/0.74 pre-game, $500k book, 1¢ spread, resolving in-window. Bought for
the payout profile the $100 target demanded (+$9.86 on a win), accepting
~fair pricing (EV ≈ -fees).

## Why it lost
The 26% event happened. Baseball is high-variance; LAD led late (market
marked 0.85+, our peak equity $79.39) and Colorado came back. Nothing about
the entry was mispriced; this is what buying a 0.74 favorite means 1 time
in 4.

## What actually went WRONG (distinct from the loss itself)
1. **Sizing violated our own floor.** Pre-registration set a $56 halt floor,
   then sized a single position whose worst case ($74.96 − $30.14 = $44.82)
   crashed through it. A floor only binds if every position's worst case
   respects it: max risk should have been equity − floor ≈ $19, not $30.
   Authorization ($30) is a ceiling, not a target.
2. **No profit-taking plan for a variance leg.** At the 0.85+ mark the leg
   was ~+$4.4 unrealized with the payout profile mostly captured. "Hold to
   settle" is right for 0.93-band favorites (the edge IS the last cents);
   it's questionable for a fair-priced 0.74 coin. Backtest a "variance legs
   take profit at entry+0.12" rule before ever using one again.

## Rule change proposed
- Hard risk-layer rule: per-position worst-case loss ≤ (equity − drawdown
  floor) — code, not judgment.
- Variance legs (if ever used again): pre-committed take-profit level.
- The drawdown halt fired exactly as designed. Keep it sacred: no
  same-session overrides to chase losses.
