# Loss post-mortem: Will Trump say "Marijuana / Weed / Cannabis" before Jul 27, 2026?

- **Date closed:** 2026-07-26
- **Exit type:** settled against us
- **Strategy:** favorite_discount (rules v12)
- **Position:** 5.0 × "No" @ 0.970 (cost $4.86)
- **Exit price:** 0.000
- **PnL:** $-4.86
- **Opened:** 2026-07-24T15:05:38+00:00
- **Context at exit:** market resolved to the other outcome

## What the rules saw at entry
A KXTRUMPSAY favorite: NO at 0.970 ask with ~2.5 days to resolution,
inside the 0.90–0.97 band, spread within 0.02, family on the live
include-list (KXTRUMPSAY revalidated healthy at +3.88% ROI on 2026-07-20,
n=127, both halves positive). Entry was rules-clean.

## Why it lost
The thesis (Trump unlikely to say "marijuana/weed/cannabis" in a ~2.5-day
window) was priced at 97% and resolved against us — he said one of the
trigger words before Jul 27. Nothing about the fill, family, or band was
anomalous; a 0.97 favorite loses ~1 time in 33 if fairly priced, and this
family's measured edge comes from winning slightly MORE often than priced,
not from never losing. First live loss in 9 settled trades since v12
(8W-1L), which is consistent with the family's 98% measured win rate.
The shadow book took the same loss at $15 scale (−$15.04).

## Rule change proposed
No change — acceptable variance. Watch item only: topic-specific
mention markets (drugs, controversial subjects) may be systematically
juicier for YES than the family average; if TRUMPSAY losses cluster in
topical words at the next weekly revalidation, consider a per-topic look
before trusting the pooled family ROI.
