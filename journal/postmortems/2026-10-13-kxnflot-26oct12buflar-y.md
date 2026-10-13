# Loss post-mortem: Buffalo vs Los Angeles R goes to overtime? — Game goes to overtime

- **Date closed:** 2026-10-13
- **Exit type:** stop_loss
- **Strategy:** favorite_discount (rules v2)
- **Position:** 42.11 × "No" @ 0.950 (cost $40.15)
- **Exit price:** 0.260
- **PnL:** $-29.77
- **Opened:** 2026-10-12T00:20:24+00:00
- **Context at exit:** bid 0.25 / ask 0.26 vs entry 0.950

## What the rules saw at entry
"No overtime" at 0.95 on Bills @ Rams (MNF), entered about 24 hours before kickoff, aggressive book,
about $40 stake (about 8% of equity). This was one of **five** aggressive-book positions on the same game
(overtime No, Kyren Williams 70+ receiving yards No, Bills by more than 13.5 No, Allen 3+ TD No, Shakir 1st TD No),
about $200 combined. Each one was a separate Kalshi event, so the per-event correlation guard
allowed all five.

## Why it lost
The game was close late, the overtime market reprised to about 0.75, and the stop fired
at 0.26. Even if this game never reaches overtime, the problem is structural: a
close game moves several of these legs against us at once. The same hour, the
aggressive book fell $50.49 (from $516.56 to $466.07): −$29.77 realized here, +$3.68 from the
Bills-by-13.5 take-profit, and the rest from marking the open positions to market. The Allen
and Shakir legs had already closed in profit.

## Rule change proposed
This is the clearest example so far of the **per-game cap** that is still waiting on the
owner (one game = one exposure bucket, for example ≤ 1 position or ≤ 2× single-stake
per game across event types). I have not applied it. It needs a change to the engine's
correlation guard, plus owner approval for the aggressive rules/limits files.
