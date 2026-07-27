# Calibration-forecast study — "beat the price with settlement history" (2026-07-28)

Owner asked for sophisticated forecasting from how recent/previous markets
settled. The honest version: estimate P(settle YES | family, price bucket,
time-to-resolution) empirically from 60 days of settled markets
(beta-binomial shrinkage: family cell → pooled cell → raw mid), and trade
either side wherever the calibrated probability beats the quoted price by
more than fees + margin.

**Pre-registered design:** TRAIN = settlements May 28–Jul 12 (10,388
price observations), TEST = Jul 13–27 (2,728). Nine families (RT,
TRUMPSAY, WT20, MLB, WNBA, FIBA, WTI, NY/CHI temps), horizons 24/12/6/2/1h
from hourly candles, margin grid chosen on TRAIN only. Fees included.

## Result: the market out-forecasts the model out-of-sample

| metric | TRAIN | TEST |
|---|---|---|
| Brier, market mid | 0.1838 | **0.1761** |
| Brier, calibrated | **0.1801** | 0.1777 |
| trading sim (margin 0.04, chosen on TRAIN) | +32.0% ROI (n=1,899) | **−11.0% ROI (n=490)** |

A +32% in-sample ROI collapsed to −11% out-of-sample, and on TEST the raw
market price was better calibrated than our empirical curve. The
in-sample "miscalibration pockets" were noise in the cells — with 9
families × 5 horizons × 20 buckets, some cells always look mispriced in
any finite window, and the margin filter selects exactly those. Per-family
TEST slices that look positive (temp ladders +50–80%) are n=9 — noise.

## Conclusion

At hourly granularity and with 60 days of history, Kalshi prices are
better-calibrated forecasts than any per-cell empirical correction we can
fit — the aggregate market already does the "sophisticated forecasting."
Our live edges remain the narrow, mechanism-backed kind (settlement lag on
published facts; family-specific favorite discounts confirmed over two
independent periods), not a general model-vs-market advantage. No paper
book wired on this evidence; a forecast book would be forward-testing a
model that already failed its first out-of-sample exam.

Third time the pre-registered wall has saved us (lead-lag momentum
+7%→−23%, MLB promote-candidate +both-halves→−2.4% next week, this).

Script: session scratchpad `calibration_study.py`. Caveats: hourly candle
mids; 5c buckets; one split point; shrinkage strengths (40/20) not tuned —
deliberately, since tuning them on TEST would be the same trap.
