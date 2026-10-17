# Loss post-mortem: Charlotte wins

- **Date closed:** 2026-10-17
- **Exit type:** stop_loss
- **Strategy:** favorite_discount (rules v2)
- **Position:** 42.55 × "No" @ 0.940 (cost $40.17)
- **Exit price:** 0.010
- **PnL:** $-39.77
- **Opened:** 2026-10-16T00:22:55+00:00
- **Context at exit:** bid 0.01 / ask 0.02 vs entry 0.940

## What the rules saw at entry
Aggressive book, "No" on Charlotte beating Temple (Fri 10/16 game) at 0.94, about $40 (~8% of equity).
Liquidity was about $5.9k with a 0.01 spread, about a day before kickoff.

## Why it lost
Charlotte won the upset Friday night. The stop could not protect the bet, because the game resolved between
hourly cycles. The more important finding is about *when the book noticed*. The aggr equity sat flat at about
$450 from Friday night through Saturday morning and only took the $39.77 hit at 20:20 UTC Saturday, about 17
hours after the scheduled end. The likely mechanism (not fully verified) is in portfolio.equity
(portfolio.py:107-115) and apply_exits (engine.py:114). Once the game ended, the No book had no bid and no ask.
Equity then **falls back to the entry price** when there is no bid, and the stop needs an ask, so the dead
position stayed valued at 0.94. When a 0.01/0.02 quote reappeared, the stop fired.

## Rule change proposed
Not applied; these are for the owner.
1. **Valuation (code):** after a market's end_date, value a position with no bid at 0, or flag it, rather
   than at entry. Otherwise reported equity hides losses until the market reopens or settles. The four
   aggr NFL ladder positions from 10/1–10/8 that are still open may be in the same state. Their current
   valuation hasn't been checked.
2. **Sizing (rules):** this is the fourth aggr loss of about $27–40 in a week (KXNFLOT ×2, KXTRUMPACT, this one).
   At an ~8% stake and a 0.94 entry, one upset costs about 15 wins. The per-game cap and the KXNFLOT exclusion are still pending.
