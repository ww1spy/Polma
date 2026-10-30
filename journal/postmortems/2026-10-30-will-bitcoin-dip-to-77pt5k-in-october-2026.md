# Loss post-mortem: Will Bitcoin dip to $77,500 in October?

- **Date closed:** 2026-10-30
- **Exit type:** settled against us
- **Strategy:** favorite_discount (rules v14)
- **Position:** 11.37 × "No" @ 0.910 (cost $10.34)
- **Exit price:** 0.000
- **PnL:** $-10.34
- **Opened:** 2026-10-28T22:20:10+00:00
- **Context at exit:** market resolved to the other outcome

## What the rules saw at entry
Bought No at 0.910 (inside the 0.85-0.96 band), spread 0.01, liquidity ~$101k, ~78h to the
2026-11-01 resolution. Entry was delayed two cycles by the 8-position cap (BLOCKs at 20:20 and
21:20 on 10/28). The same book also held "dip to $75,000 in October" No from 10/29 02:20
(took profit +$0.28 on 10/29 14:40) — two rungs of the same BTC ladder.

## Why it lost
Thesis wrong: BTC touched $77,500 before month-end, so the market resolved Yes. This is a
"touch" market — one wick anywhere in the window resolves it — and at 0.91 the market itself
priced ~9% odds; this is the tail it was paying for. Book equity drifted from $519.66 (10/29
19:20) to $511.80 (23:19) as the No marked down, but the 0.55-point disaster stop (trigger ~0.36
on the ask) never fired before resolution: the touch happened between hourly cycles.

Follow-on worth noting: in the same cycle as this settle, the engine bought "dip to $70,000 in
October" No at 0.938 ($10.17). The next rung down is now the book's BTC exposure, entered
right after the rung above it was breached.

Polymarket base-book record to date: 237W +$195.83 / 28L -$255.68, net -$59.85.

## Rule change proposed
Not applied (owner decision):
1. Same-underlying cap: at most one open rung per price-ladder family (BTC dip/reach markets),
   and skip entries on a ladder in the cycle immediately after a sibling rung settled against us.
2. Otherwise no change — a single 9%-tail outcome at 2% sizing is within variance, though the
   book's net record is negative (-$59.85) and dominated by a few full-stake losses.
