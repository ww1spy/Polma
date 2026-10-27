# Loss post-mortem: Arsenal wins

- **Date closed:** 2026-10-27
- **Exit type:** settled against us
- **Strategy:** favorite_discount (rules v2)
- **Position:** 40.26 × "Yes" @ 0.900 (cost $36.50)
- **Exit price:** 0.000
- **PnL:** $-36.50
- **Opened:** 2026-10-26T20:20:48+00:00
- **Context at exit:** market resolved to the other outcome

## What the rules saw at entry
Aggressive paper book (about 8% of equity, ~$36.50). It bought Arsenal to win this EFL Cup tie at 0.90 on 10/26 at 20:20 UTC, about 26 hours before the market's end date (10/27 23:00 UTC). The spread was 0.01 and liquidity about $6.8k, so the market looked deep and settled.

## Why it lost
The favourite didn't win. The match was played between hourly cycles: at the 21:20 cycle the whole book was only $3.62 lower, and by 22:20 the market had settled at 0. The stop (which checks the ask once an hour) never had a chance to act, the same hourly-gap weakness behind earlier losses. One thing I couldn't verify: whether this market settles on the 90-minute result. If so, a draw that Arsenal won later in extra time or on penalties would still pay No, and a 0.90 price would have underpriced that risk.

The aggressive book's all-time record is now 275 wins (+$506.45) and 31 losses (−$738.40), net −$231.95. One loss at this stake wipes out about 18 average wins.

## Rule change proposed
Not applied; this is the owner's call. This is the same pattern as the pending aggressive-book proposals: either cut the stake toward 2% or exclude game families that resolve inside one hour. A cup-specific option is to exclude KXEFLCUPGAME, or knockout ties in general, if the market settles on the 90-minute result. Elsewhere in soccer, KXUCLGAME is 8 wins and 0 losses for +$19.17 in this book.
