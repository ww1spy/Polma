# 4-week hypothesis study — 2026-07-08 (owner-requested)

~50 market families, up to 250 settled markets each, stratified across 28
days. All sims: real ask entries, fees, ask-side disaster stop. Baseline
config: 0.90–0.97 band, 2–72h pre-resolution, spread ≤ 2¢.

## Headline: the pooled favorite "edge" on Kalshi is NEGATIVE
All families pooled: n=4,272, win 89.4%, **ROI −4.10%**. The strategy only
works inside the right families. Commodities dailies (gold −10.5%, silver
−14.5%, copper −15.9%, Brent −6.8%) and the weather-city group (~25 cities,
pooled −2.1%) are systematic losers at high volume.

## H4 + the honest test: naive family selection DOES NOT TRANSFER
Selecting families that were profitable in half-1 (n≥15, ROI>+1%) and
holding them in half-2: **OOS ROI −2.68%** vs −2.91% all-family baseline —
no meaningful skill. Six half-1 "winning" weather cities imploded in
half-2 (−6% to −14%). **Learning #9: with 90%+ win rates, losses are rare
events; family ROI on a few dozen trades is mostly noise, and picking
winners from ~50 candidates is a multiple-comparisons trap.**

What survives BOTH halves positive with n≥30 AND a plausible mechanism:

| Family | n | win% | ROI | halves | mechanism |
|---|---|---|---|---|---|
| KXRT (Rotten Tomatoes) | 39 | 100% | +5.5% | +4.8/+6.1 | critic aggregation is predictable pre-certification |
| KXWT20MATCH (cricket) | 44 | 97.7% | +3.8% | +1.4/+6.3 | thin retail sports, favorite-longshot bias |
| KXMLBGAME (pre-game) | 59 | 96.6% | +2.2% | +2.2/+2.3 | classic favorite-longshot bias |
| KXWTI (WTI daily) | 212 | 94.8% | +1.9% | +0.3/+3.6 | unclear — siblings all negative; TREAT AS PROVISIONAL |
| KXTRUMPSAY | 68 | 95.6% | +1.7% | +0.1/+3.2 | retail lottery flow on YES longshots |
| KXFIBAGAME | 78 | 94.9% | +0.4% | +0.7/+0.1 | sports, marginal |
| (KXHIGHLAX, KXHIGHPHIL) | ~95 ea | 98% | +3.0–3.5% | both + | weather cities: group is −EV and city-picking failed OOS — testing continues in aggr book only |

## H5 bands (pooled): higher bands lose less (−6.5% → −2.8% from 0.85 to
0.96+), but no band rescues bad family selection.

## H6 time-of-day: quality is flat across UTC buckets (−3.6/−4.9/−3.8).
Overnight is scarce, not toxic.

## H8 take-profit: tp@0.98 beats 0.99 and hold (−3.88% vs −4.10%/−3.91%)
and cuts average hold by 3h (16.8h vs 19.8h) → adopted (faster recycling,
no cost).

## H9 spread: ≤1¢ entries modestly better (−4.08% vs −4.84%) → keep 2¢ cap.

## H10 weather dailies: pooled −2.11% (n=1,990) → excluded from base rules.

## H12 ETH15M (4 weeks, controls): ETH +1.68% (n=379; weekly +3.0/+0.9/
+4.0/−1.5), BTC +0.34% (mixed). Edge real-ish but modest; stays paper-only.

## Actions taken (rules v8)
1. Base kalshi universe RESTRICTED to the mechanism-backed shortlist
   (include-list): KXMLBGAME, KXRT, KXTRUMPSAY, KXWTI, KXWT20MATCH,
   KXFIBAGAME. Fewer candidates, positive expectancy — previously the base
   config was likely −EV on unrestricted families.
2. take_profit_bid 0.99 → 0.98 (H8).
3. Aggr paper book keeps the BROAD universe deliberately — it is now the
   discovery book measuring family drift, including the weather-city
   question, at zero real-money cost.
4. Next: run the same honest 4-week family study on Polymarket (its +2.2%
   validation predates this methodology and deserves the same skepticism).
