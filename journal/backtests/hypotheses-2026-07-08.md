# Hypothesis backtests — 2026-07-08 (owner-requested)

## H1: in-play sports favorites — **REJECTED**
Band 0.90–0.97, hold-to-settle, ask-side disaster stop, real ask entries,
fees included. 444 settled sports markets (MLB/WNBA/World Cup/UFC, 21 days),
1-minute candles, entries bucketed by time-to-resolution:

| Entry bucket | n | win% | ROI | stops fired |
|---|---|---|---|---|
| 10–45 min (late in-play) | 283 | 86.9% | **-4.6%** | 37 |
| 45min–2h (in-play) | 222 | 73.9% | **-14.1%** | 58 |
| 2–4h (early/pre) | 61 | 70.5% | **-15.8%** | 18 |
| 4–12h (pre-game) | 23 | **95.7%** | **+2.9%** | 1 |

Breakeven at these prices ≈ 94%. Verdict: the edge exists ONLY pre-game.
In-play "favorites" systematically underprice comeback risk. The old
"no in-play" rule was correct — but now for a measured reason, not a
stop-loss artifact. Aggressive profile reverted to 2h minimum.

## H3: ETH15M anomaly — **CONFIRMED (this regime)**
7 days, entries 3–12 min pre-settle, fees included, BTC/SOL as controls:

| Family | band 0.90–0.97 | band 0.93–0.98 |
|---|---|---|
| **KXETH15M** | **n=456, 95.4%, +2.34%** | n=408, 97.3%, +1.65% |
| KXBTC15M (control) | n=471, 93.0%, -0.21% | n=417, 94.5%, -1.00% |
| KXSOL15M (control) | n=466, 92.3%, -1.26% | n=418, 95.0%, -0.88% |

Same ordering in both bands; ~900 cumulative ETH trades positive across
all tests to date. Caveat: one week, one (calm) crypto regime — a vol
regime change could erase it. New paper profile "eth15" runs it at live
fidelity; revisit weekly.

## H2: sizing velocity — **QUANTIFIED**
Monte Carlo, 20k paths × 60 sequential trades drawn from the 45-trade
empirical v4 kalshi distribution (96% win, mean +1.1%/$):

| Sizing | halt line | median | p10 | p90 | P(halt) | avg maxDD |
|---|---|---|---|---|---|---|
| 2.5% | 15% | +2.0% | -3.5% | +6.2% | ~0% | 3.7% |
| 5% | 15% | +3.7% | -7.9% | +12.8% | 5.8% | 7.3% |
| 8% | 30% | +6.0% | -12.0% | +21.4% | 1.2% | 11.7% |
| 12% | 30% | +8.3% | -20.6% | +32.9% | 9.7% | 17.0% |

Reading: growth scales roughly linearly with sizing; tail pain scales
faster. 5% needs a wider halt than 15% or it self-halts on noise. The
8%/30% cell is the interesting one — but the empirical sample (n=45, ONE
loss) underrepresents tails, so treat all rows as optimistic. Promotion
path: if the aggr paper book's realized loss rate over ≥50 settled trades
stays ≤5%, 5% sizing with a 25% halt is a defensible live upgrade.
