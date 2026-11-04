# Loss post-mortem: Chennai Open: Robin Montgomery vs Jeline Vandromme

- **Date closed:** 2026-11-04
- **Exit type:** settled against us
- **Strategy:** favorite_discount (rules v14)
- **Position:** 11.56 × "Jeline Vandromme" @ 0.880 (cost $10.17)
- **Exit price:** 0.000
- **PnL:** $-10.17
- **Opened:** 2026-11-04T12:20:36+00:00
- **Context at exit:** market resolved to the other outcome

## What the rules saw at entry
Polymarket base book, favorite_discount v14. Bought Vandromme at 0.88 on 11/04 12:20 (spread
0.01, liquidity ~$291k). The market's end_date was 11/11 — a week-long window — but the match
itself was being played that hour: it settled against us at the very next cycle (13:21).
A pre-/in-match tennis price of 0.88 is a ~12% upset chance, and the stated end_date did not
reflect how soon the event would resolve.

## Why it lost
Upset: Montgomery won. No stop could act — entry and settlement were one cycle apart.

This is the tennis/head-to-head pattern already flagged (see the ten earlier WTA/ATP
postmortems, July-October). Polymarket head-to-head match markets ("X vs Y", "<Event> Open:")
for this book: 92W +$88.36 / 17L -$162.01, net -$73.65 — more than the whole book's net
(-$71.77 across 248W/30L). Excluding them alone would roughly zero the book's losses.

## Rule change proposed
Not applied (owner decision; the carried-over "Polymarket tennis" options):
1. Exclude single-match head-to-head markets (tennis, esports, cricket) from the Polymarket
   book, or
2. Require price >= 0.93 for them (most losses entered at 0.85-0.92), or
3. Use time-to-match rather than market end_date for the hours-to-resolution filter.
