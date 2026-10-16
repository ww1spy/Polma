# Loss post-mortem: Seattle vs Denver goes to overtime? — Game goes to overtime

- **Date closed:** 2026-10-16
- **Exit type:** settled against us
- **Strategy:** favorite_discount (rules v2)
- **Position:** 42.55 × "No" @ 0.940 (cost $40.17)
- **Exit price:** 0.000
- **PnL:** $-40.17
- **Opened:** 2026-10-15T00:20:43+00:00
- **Context at exit:** market resolved to the other outcome

## What the rules saw at entry
Aggressive book, "No overtime" at 0.94 on Seattle @ Denver (TNF), about $40 stake (about 8% of equity),
entered about 24 hours before kickoff. One of four same-game positions (overtime No, Humphrey
1+ TD No, Engram 1st TD No, first-half tie No), about $160 combined.

## Why it lost
The game went to overtime. NFL overtime happens in roughly 5–7% of games, so 0.94 was
about fair, with no real edge. The swing from "close late" to "OT" happened between
hourly cycles, so the stop never triggered and the bet went to $0 (−$40.17).
This is the second NFL overtime-No loss in four days (BUF@LAR stop-loss −$29.77 on 10/13).
The other three legs on this game closed in profit (+$1.15, +$3.68, +$1.96 = +$6.79),
so the game netted −$33.38.

## Rule change proposed
Not applied; this is the owner's call. Two candidates:
1. Exclude `KXNFLOT` (overtime markets) from the aggressive book. At about 0.94 the price matches the
   base rate, so there is no discount to harvest. Two losses in four days total −$69.94, against
   about +$4 for a typical win.
2. The per-game exposure cap already pending (one game = one bucket).
