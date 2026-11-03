# Loss post-mortem: Memphis wins

- **Date closed:** 2026-11-03
- **Exit type:** stop_loss
- **Strategy:** favorite_discount (rules v2)
- **Position:** 40.34 × "No" @ 0.910 (cost $36.95)
- **Exit price:** 0.230
- **PnL:** $-28.18
- **Opened:** 2026-11-02T00:20:33+00:00
- **Context at exit:** bid 0.23 / ask 0.25 vs entry 0.910

## What the rules saw at entry
Aggressive paper book (rules-aggressive v2, ~8% stake). Bought "Memphis wins" **No** at 0.91
on 11/02 00:20 (spread 0.01) — i.e. Memphis a ~9% underdog — for $36.95. Listed liquidity
was only ~$5.1k, and the game resolved ~27h later. First trade ever in KXNCAAMBGAME (college
basketball) for this book: no family history behind it.

## Why it lost
Thesis wrong: the underdog led / won. By the 02:20 cycle on 11/03 (game in progress or
just ended) the No was 0.23/0.25 and the stop sold at 0.23. In-game price swings in a
single basketball game routinely move 0.9 → 0.2 within an hour; the hourly stop is a
coin-flip on where in that swing it samples.

A ~9% outcome is the price of the bet; at 8% sizing one such hit (-$28.18) erases ~50 of
this book's typical ~$0.55 wins. Aggressive book after this: 300W +$550.02 / 32L -$766.58,
net -$216.56. Losses are dominated by single-game and player-prop markets.

## Rule change proposed
Not applied (owner decision; same as the 10/27 EFL Cup postmortem):
1. Exclude single-game / player-prop families from the aggressive book, or require a
   minimum family track record before trading a new game family (this was its first).
2. Cut the aggressive stake toward 2%, and/or add a minimum-liquidity floor (here ~$5k).
