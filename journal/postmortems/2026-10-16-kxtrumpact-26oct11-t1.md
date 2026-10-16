# Loss post-mortem: Will there be at least 1 presidential actions in the week of Oct 11, 2026? — At least 1

- **Date closed:** 2026-10-16
- **Exit type:** stop_loss
- **Strategy:** favorite_discount (rules v2)
- **Position:** 43.01 × "Yes" @ 0.930 (cost $40.20)
- **Exit price:** 0.324
- **PnL:** $-26.94
- **Opened:** 2026-10-15T17:20:07+00:00
- **Context at exit:** bid 0.33 / ask 0.38 vs entry 0.930

## What the rules saw at entry
Aggressive book, "Yes, at least 1 presidential action in the week of Oct 11" at 0.93, about a $40 stake
(roughly 8% of equity). Liquidity was about $3.0k with a 0.01 spread, about 2.9 days before resolution (10/18 14:00 UTC).

## Why it lost
Treat this as unverified. On Friday the market repriced from 0.93 to a bid of 0.33 / ask of 0.38, so the
crowd now expects no qualifying "presidential action" this week. That points to a narrow resolution source
(it counts specific documented actions, not news-level activity) and none had posted by late week. The rules
read "at least 1" as near-certain without checking what counts. I did not look up the contract's
resolution terms, so this cause is a hypothesis. The stop sold at 0.324 with two days still to go.

## Rule change proposed
Not applied; this is the owner's call. KXTRUMPACT has not been through revalidation. Candidate: keep
count-threshold "government action" families (KXTRUMPACT) out of rules-aggressive until a backtest shows
an edge. This is another loss from a full ~8% stake at a 0.93 entry: one stop costs about 10 typical wins.
