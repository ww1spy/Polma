# Loss post-mortem: Will Trump say "Ceasefire" before Oct 12, 2026?

- **Date closed:** 2026-10-11
- **Exit type:** settled against us
- **Strategy:** favorite_discount_maker (rules v1)
- **Position:** 11 × "No" @ 0.900 (cost $9.90)
- **Exit price:** 0.000
- **PnL:** $-9.90
- **Opened:** 2026-10-09T19:21:23+00:00
- **Context at exit:** market resolved to the other outcome

## What the rules saw at entry
A resting maker bid on "No" at 0.90 in a KXTRUMPSAY "mention" market, opened about
2.5 days before resolution. A print traded through 0.90 and filled the bid.

## Why it lost
The thesis was wrong. "Ceasefire" was a live news topic that week; the Polymarket
book held several ceasefire bets at the same time. A No at 0.90 on a word Trump is
actively being asked about is underpriced risk, not a favorite. A maker fill on
a mention market is also adversely selected: the bid fills when someone with
fresher information (a scheduled speech, a press gaggle) sells into it.

## Rule change proposed
Candidate for review, not applied: exclude `KXTRUMPSAY` from the maker book, or
at least exclude words tied to the week's headlines. The maker engine placed
another KXTRUMPSAY No order in the same cycle. One loss is not a sample, so this
is for the owner to decide. rules/*.yaml is not edited here.
