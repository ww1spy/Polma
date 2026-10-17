# Loss post-mortem: Wuhan Tennis Open: Iga Swiatek vs Maja Chwalinska

- **Date closed:** 2026-10-17
- **Exit type:** stop_loss
- **Strategy:** favorite_discount (rules v14)
- **Position:** 11.93 × "Iga Swiatek" @ 0.850 (cost $10.14)
- **Exit price:** 0.170
- **PnL:** $-8.11
- **Opened:** 2026-10-17T10:20:30+00:00
- **Context at exit:** bid 0.14 / ask 0.18 vs entry 0.850

## What the rules saw at entry
Swiatek at 0.85 vs Chwalinska (Wuhan, WTA 1000), standard ~2% stake ($10.14), deep book (~$147k liquidity,
0.01 spread), entered at 10:20 UTC. 0.85 is near the low end of the favorite band.

## Why it lost
Swiatek was losing within three hours of entry, so the stop sold at 0.17 for −$8.11. Unlike the Alcaraz
loss, the stop did fire before settlement, but in-play tennis moves so fast that it only saved about $2 against
a full loss. A 0.85 favorite is priced to lose about 15% of the time, so the price itself was not wrong.

## Rule change proposed
Not applied; this is the owner's call. A rough keyword tally of Polymarket head-to-head settles and exits
since 9/28 (it may include a few non-tennis "X vs Y" markets) shows 61 wins (+$62.06) and 9 losses (−$88.89),
so net −$26.83. Wins average about +$1, and losses average about −$10. The options offered on 10/13 still stand
(exclude tennis, add a price bound, or run the 60-day backtest). Note that only a minimum entry price, for example
at least 0.90, would have blocked this 0.85 entry. A maximum would not have.
