# Structural-edge study — 2026-07-09

Question: beyond family selection, are there *structural* edges (fee/spread
mechanics, settlement timing) the current rules leave on the table?
Analysis only — no rules changed. Script: session scratchpad
`structure_study.py` (reuses `polma.revalidate` machinery; fees included;
$10 stakes; half-period consistency shown).

## A. "Last-mile" band: taker entries at 0.97–0.995 (spread ≤ 0.02)

Currently the band stops at 0.97, so the engine never touches these.
Slow families, hourly candles, 60d, 2–72h pre-settle window:

| family | n | win% | ROI | h1 | h2 | read |
|---|---|---|---|---|---|---|
| KXRT | 119 | **100%** | **+1.86%** | +1.96% | +1.77% | **real — see mechanism** |
| KXMLBGAME | 19 | 100% | +2.09% | +1.95% | +2.22% | same shape, n too small |
| KXTRUMPSAY | 140 | 98% | +0.40% | +1.24% | −0.45% | no |
| KXWT20MATCH | 45 | 96% | −2.05% | −6.63% | +2.34% | no — cricket flips late |
| KXWTI | 420 | 97% | −0.50% | −0.90% | −0.10% | no — price moves to the wire |
| KXETH15M (1-min, 7d, 3–14min window) | 488 | 98% | +0.18% | +1.00% | −0.64% | no |

**Mechanism (why RT and only RT):** a Rotten Tomatoes threshold market's
outcome is often *publicly determined* hours before Kalshi settles it — the
score is posted and essentially frozen, but the market lingers at 0.97–0.99
awaiting settlement. Buying there is collecting a settlement-lag premium on
a decided fact, which is why the win rate is 100/119 with both halves
positive. Families that can still flip late (cricket, WTI, Trump-mention)
show no such edge — this is NOT a generic band extension, it's
family-specific. MLB post-game-final markets plausibly share the mechanism
(n=19, insufficient).

Caveats: one 60-day period (halves consistent, but no second independent
period — same evidence tier that got MLB/WTI demoted after May OOS);
at live size (~$2.6/trade ≈ 2–3 contracts) the ceil-to-cent fee costs
~0.3–0.5% extra vs these $10-stake numbers; payoff per trade is cents.

## B. Maker-entry approximation (post at ask−1¢, fill only if a later ask
close crosses down to the post; no taker fee on entry)

| family | n(filled) | ROI | vs taker baseline |
|---|---|---|---|
| KXTRUMPSAY | 130 | +2.84% | +2.63% — comparable |
| KXRT | 74 | +2.60% | +2.05% — comparable, half the fills |
| KXWT20MATCH | 42 | +3.48% | +3.79% — comparable |
| KXWTI | 389 | −2.04% | worse |
| **KXETH15M (1-min)** | 188 | **−8.58%** | **catastrophic** |

**Read:** in fast markets a resting bid fills mainly when the world moves
against you — textbook adverse selection (ETH: −8.6%, and only 37% of
candidates fill at all). In slow retail families maker ≈ taker on ROI with
half the fill rate and real operational complexity (resting-order state,
cancel/replace in an unattended cron). Not worth implementing now; the fill
model here is also crude (hourly closes). Revisit only if taker fees ever
become the binding constraint.

## C. Side-findings

- **ETH15M decay warning:** baseline band re-run on the freshest 7 days:
  +0.37% overall but **h2 = −0.32%** (this morning's fast-only revalidation
  already showed the edge thinning: +0.92% vs +2.3% original). The one
  "steady churn" candidate is fading with the regime. Do not promote;
  Monday's revalidator (which now covers it) is the checkpoint.
- Watchlist (from 2026-07-08 report): MLB/WTI/FIBA/WNBA all
  breakeven-to-negative — no promotion candidates pending.

## Proposals (owner decision required — rules changes)

1. **RT last-mile strategy** (add 0.97–0.995 entries for `KXRT-` only,
   spread ≤ 0.02, hold to settle): mechanism is crisp, halves consistent,
   100% win in sample. Conservative path: add to the base kalshi PAPER book
   now, live after forward confirmation. Aggressive path: straight to live
   at current 2.5% sizing (worst case per trade is bounded and small).
2. **Do NOT extend the band generically** — the same trade loses money in
   WT20/WTI/ETH15M.
3. Maker execution: shelved with evidence, not opinion.
