# Loss post-mortem: Full Game: Over 33.5 points scored

- **Date closed:** 2026-10-18
- **Exit type:** stop_loss
- **Strategy:** favorite_discount (rules v2)
- **Position:** 38.44 × "Yes" @ 0.940 (cost $36.29)
- **Exit price:** 0.320
- **PnL:** $-24.58
- **Opened:** 2026-10-17T00:20:46+00:00
- **Context at exit:** bid 0.32 / ask 0.36 vs entry 0.940

## What the rules saw at entry
Aggressive book, "Over 33.5 total points" Yes at 0.94 on Louisiana Tech at ULM, about $36 (~8% of equity).
Liquidity was about $8.3k with a 0.01 spread, entered about a day before kickoff.

## Why it lost
The game was low-scoring in-play, the over repriced to about 0.34, and the stop sold at 0.32 for −$24.58.
A total of 33.5 for a college game is not a near-certainty the way 0.94 implies; scoring variance is large.
This is a second-day college football loss for the aggressive book (Charlotte −$39.77 yesterday).

## Rule change proposed
Not applied; this is the owner's call. The aggressive book's full journal record (all aggr SETTLE/EXIT rows,
including any before past resets) is 236 wins (+$436.45) and 30 losses (−$701.90), so net −$265.45.
Wins average about +$1.85, and losses average about −$23. With a ~8% stake at 0.90–0.95 entries, the edge needed to break even
is not there. Candidates: cut the aggr stake back toward the base 2%, exclude game-total and player-prop families
(KXNCAAFTOTAL, KXNFLOT, KXNFLTD), and the per-game cap. I can't change sizing myself.
