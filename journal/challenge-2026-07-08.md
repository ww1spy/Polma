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
- 03:30 UTC — **Checkpoint 1.** Equity $77.79 (+$2.83): +$0.17 realized
  (BTC-range take-profit), LAD leg marked at 0.82 vs 0.74 entry (Dodgers
  leading). Loop healthy (re-armed twice around a 30-min monitor clamp).
- 03:30 UTC — **Learning #5 (the drought is real):** since the band/exclusion
  fixes, the grind loop has found **zero** qualifying candidates in ~10
  consecutive scans. Overnight UTC is Kalshi's dead zone — nearly nothing
  liquid resolves 02:00–08:00 that isn't crypto (excluded as -EV). An edge
  needs a market to express itself in; time-of-day is a strategy parameter
  we never priced in. Correct daytime expectation: the same loop during US
  afternoon/evening would see sports/econ settlements constantly.
- 03:30 UTC — plan for the back half: LAD settles ~05:15 (+$9.86 if it
  holds → ~$85). Then scan for anything liquid at 0.70–0.85 resolving
  before 07:30 (Asia-session markets?) for a second $30 leg; if that wins
  (~$95), one final small leg only if a clean candidate exists. Floor $56
  stands. Target remains a stretch: two more wins needed with no losses.
- ~05:15 UTC — **LAD LOSES.** Colorado came back after LAD was marked 0.85+.
  Settled -$30.14. Equity $44.99. **Drawdown halt fired (43% from marked
  peak $79.39 > 25%)** — live trading halted, pending owner review.
- 05:20 UTC — **Challenge closed early at the halt.** No loss-chasing:
  overriding our own halt to sprint at a lost target is the exact behavior
  this program exists to prevent.

## Final accounting

| | |
|---|---|
| Start | $74.96 |
| BTC-range accident (take-profit) | +$0.17 |
| Grind loop (validated band) | 0 trades — overnight drought (Learning #5) |
| LAD variance leg | **-$30.14** |
| **End** | **$44.99 (-40%)** |
| Target $100 | Not reached. Never realistic; said so up front. |

- **Learning #6 (the big one): a floor only binds if every position's
  worst case respects it.** We set a $56 floor and then sized a single
  binary position whose total loss landed at $44.82. Max risk should have
  been equity − floor ≈ $19. Authorization is a ceiling, not a target.
  → Now enforced IN CODE: risk.max_notional caps size at equity − floor.
- **Learning #7: unrealized peaks count.** Peak equity $79.39 was a
  mark-to-market high (LAD at 0.85); the drawdown halt measured from it.
  Correct and conservative — but it means variance legs with no
  profit-taking plan donate their peak to the drawdown math. If variance
  legs ever return: pre-committed take-profit.
- **Learning #8: infrastructure is part of risk.** Three container restarts
  killed the trading loop mid-challenge; the send_later scheduler failed
  repeatedly. Positions held through infrastructure gaps were unmanaged for
  up to ~40 min at a time. The hourly Routine was the reliable backstop —
  design for the backstop, treat fast loops as best-effort.

## Post-challenge state
- Rules reverted to validated v4 parameters (as v6); challenge risk limits
  reverted to conservative values. Kept permanently: ask-side band check,
  blanket crypto exclusions, floor-aware sizing cap.
- Live trading remains **HALTED** until the owner reviews this file and the
  LAD post-mortem and explicitly clears it. Paper trading continues on both
  venues.
