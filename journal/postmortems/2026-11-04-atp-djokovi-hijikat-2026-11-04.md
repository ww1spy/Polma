# Loss post-mortem: Rolex Paris Masters: Novak Djokovic vs Rinky Hijikata

- **Date closed:** 2026-11-04
- **Exit type:** settled against us
- **Strategy:** favorite_discount (rules v14)
- **Position:** 10.51 × "Novak Djokovic" @ 0.950 (cost $9.98)
- **Exit price:** 0.000
- **PnL:** $-9.98
- **Opened:** 2026-11-04T15:20:37+00:00
- **Context at exit:** market resolved to the other outcome

## What the rules saw at entry
Polymarket base book, favorite_discount v14. Bought Djokovic at 0.95 on 11/04 15:20 for $9.98
(~5% upset priced). Like the Chennai loss earlier today, the match was played within hours of
entry and settled at the 18:19 cycle; no stop could act.

## Why it lost
Upset: Hijikata beat Djokovic. A 5% tail at a 0.95 entry.

Second head-to-head tennis loss today (see 2026-11-04-wta-montgom-vandrom). Polymarket
head-to-head match markets for this book now: 92W +$88.36 / 18L -$171.99,
net -83.63. This loss was entered at 0.95, so a >=0.93 price floor alone would not have
blocked it.

## Rule change proposed
Not applied (owner decision): exclude single-match head-to-head markets from the Polymarket
book. A price floor is not sufficient (this entry was 0.95).
