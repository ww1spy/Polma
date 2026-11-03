# Loss post-mortem: US-Iran ceasefire continues through the midterms?

- **Date closed:** 2026-11-03
- **Exit type:** stop_loss
- **Strategy:** favorite_discount (rules v14)
- **Position:** 11.01 × "Yes" @ 0.940 (cost $10.35)
- **Exit price:** 0.051
- **PnL:** $-9.79
- **Opened:** 2026-10-29T03:20:16+00:00
- **Context at exit:** bid 0.051 / ask 0.079 vs entry 0.940

## What the rules saw at entry
Polymarket base book, favorite_discount v14. Bought Yes at 0.94 on 2026-10-29 03:20
(spread 0.01, liquidity ~$83k, ~6 days to the 2026-11-04 end date). The entry had been
BLOCKed repeatedly from 10/27 by the 8-position cap and filled as soon as a slot opened.
This was the latest rung of a long series: the book has traded "US/Israel x Iran ceasefire
continues through <date>" markets since July, almost all take-profits at ~0.98.

## Why it lost
Thesis wrong: by the 01:20 cycle on 11/03 the Yes was 0.051/0.079 — the market now prices
the ceasefire as having ended (or near-certain to end) before the midterms. The 0.55-point
disaster stop (trigger ~0.39) fired only at this cycle, so the exit was ~0.05: effectively a
full-stake loss. The collapse happened between hourly cycles; the stop cannot help with a
jump of this size.

Payoff shape of the series: Polymarket ceasefire markets record 16W +$8.56 / 2L -$15.84,
net -$7.28 — each win earns ~$0.50, each loss costs ~$8-10. That is the textbook
favorite-longshot tail: the "streak" of daily renewals is the same underlying risk
re-bought every few days.

Polymarket base-book record after this loss: see journal; net was -$59.85 before the BTC
loss on 10/30 and is now lower by a further ~$20 across those two.

## Rule change proposed
Not applied (owner decision):
1. Treat rolling "X continues through <date>" geopolitical series as one family with a
   lifetime/rolling loss budget, or exclude them: their realized payoff here is negative.
2. Same proposal as the 10/30 BTC postmortem: one open position per underlying event.
