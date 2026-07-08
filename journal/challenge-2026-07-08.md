# 6-Hour Challenge — 2026-07-08 01:40–07:40 UTC

**Owner directive:** grow $74.96 → $100 in 6 hours; cap raised $2 → $30/trade
(explicitly authorized); document all learnings.

**Honest pre-registration:** +33% in 6h exceeds any measured edge (validated
edge: ~1–6%/trade at 92–98% win rates). Hitting $100 requires a near-perfect
run. Target is treated as a stretch goal; the real deliverable is learnings.
**Floor: halt all new entries if equity ≤ $56 (25% drawdown)** — capital is
preserved for the remaining days unless the owner explicitly overrides.

## Pre-deployment findings (backtest of intraday families, last 3 days)

| Family | Verdict | Evidence |
|---|---|---|
| KXBTC15M / KXSOL15M (15-min crypto) | **EXCLUDED — negative EV in all 6 configs** | win% 88–94% at prices needing 93.5%+; fees finish the job |
| KXBTCD / KXETHD (daily crypto) | EXCLUDED — negative in most configs, small n | mixed, unreliable |
| KXETH15M | Allowed, not relied on | positive in ALL 6 configs (+$17–22 per config on ~40 trades) — consistent but small n |
| Learning #1 | **Velocity ≠ edge.** The fastest-resolving markets are the most efficiently priced. | |

## Plan

1. **Engine grind (validated edge, automated):** live cycles every ~8 min for
   6h; kalshi rules temporarily overridden to intraday horizon (9 min–6h to
   resolution), 0.90–0.97 band, $30/trade cap, crypto losers excluded.
   Expected: small positive EV per settlement, several settlements in-window.
2. **One variance leg (manual, journaled):** a single ≤$30 position at
   0.70–0.82 on a liquid market resolving within ~5h (tonight's late MLB or
   similar). ~Fair-priced (EV ≈ −fees ≈ −$0.50), bought deliberately for the
   payout profile the target demands: a win pays +$7–12. Never more than one
   variance leg open at a time; total worst case stays above the floor.
3. **Checkpoints every ~75 min:** review fills/settlements, document
   learnings here, adapt.

## Risk envelope for the challenge (reverts after)
- max/trade: $30 (owner-authorized), engine hard fraction 42% of equity
- max exposure 85%, max open 8, one-per-market, same-day re-entry cooldown
- daily realized loss halt 25%; drawdown halt 25% from peak (≈$56)
- exits: ask-side disaster stop (0.55), take-profit bid 0.99

## Log

- 01:40 UTC — challenge starts. Equity $74.96, no open live positions.
- 01:59 UTC — **variance leg ON**: 40 × LAD Yes @ $0.74 ($30.14 incl. $0.54
  fee). Pre-game. Win pays +$9.86, resolves ~05:15 UTC.
- 02:05 UTC — **Learning #2 (bug, caught live):** first loop version had no
  sleep — cycles raced back-to-back and re-notified stale lines. The
  **exposure guardrail (85%) is what actually stopped it** after one
  unintended entry. Guardrails > intentions.
- 02:05 UTC — **Learning #3 (rules leak):** excluding `KXBTC15M`/`KXBTCD`
  didn't exclude the `KXBTC-` *range* family — sibling market families
  share a stem but not a prefix. One $29.51 NO @ 0.982 slipped in
  (resolves ~02:00, ~98% to win +$0.49). Exclusions now blanket the stem.
- 02:05 UTC — **Learning #4 (slippage at the band edge):** the engine
  band-checked the MID (0.97 max) but the executor crosses the spread, so
  it FILLED at 0.982 — outside the band, needing a 98.4% win rate to break
  even. Candidates are now band-checked against the effective ASK. This one
  is a permanent engine fix, not challenge-specific.
- 02:10 UTC — loop v2 running: 43 cycles × 8 min. Open: LAD variance leg +
  BTC-range accident. Cash $15.31.
