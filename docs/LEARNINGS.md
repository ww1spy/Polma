# Polma — Everything We've Learned

Consolidated from the trade journal, backtest reports, post-mortems, and
the build itself (2026-07-07 → 2026-07-08). Each item links to primary
evidence in this repo. This document is the distillation; the journal is
the proof.

---

## I. Market & strategy learnings

**M1. The "favorite discount" edge is real but NARROW — it lives in
specific market families, not in prices.**
Pooled across ~50 Kalshi families and 4,272 backtested trades, buying
0.90–0.97 favorites is **negative** (-4.1% ROI). The same trade inside
mechanism-backed families (MLB pre-game, Rotten Tomatoes, Trump-mention
NO-side, WTI, women's T20) is +1.7% to +5.5%. Family selection IS the
strategy; the price band is just the costume.
*Evidence: journal/backtests/hypotheses-4wk-2026-07-08.md*

**M2a. Even mechanism-backed family-picking must survive a SECOND
independent period.** The owner-requested May portfolio test (v9 rules,
$500, full engine semantics) lost 13.4% and tripped the halt: WTI
(−$44.91) and MLB (−$30.92) failed out-of-sample despite passing the
Jun–Jul study; only Rotten Tomatoes (+$8.64) and Trump-mention (+$0.42)
survived both periods. A 91% win rate coexisted with a −13% month —
favorites' rare losses arrive CLUSTERED, not i.i.d. Live now trades only
double-validated families (v10); everything else is measured in paper.
*Evidence: journal/backtests/oos-may-2026-07-08.md*

**M2. Naive family-picking does not transfer out-of-sample.**
Families selected for being profitable in weeks 1–2 returned **-2.68%**
in weeks 3–4 — indistinguishable from the -2.91% pick-nothing baseline.
Six "winning" weather cities imploded out-of-sample. Only families with
BOTH half-period consistency AND a nameable mechanism went into the live
include-list. At 90%+ win rates, losses are rare events, so ROI estimates
on <50 trades are mostly noise — and picking winners from 50 candidates
is a multiple-comparisons trap.
*Evidence: same file, "honest test" section*

**M3. Velocity ≠ edge.** The fastest-resolving markets (15-min crypto
strikes) are the most efficiently priced; favorites there lose in nearly
every configuration once fees are counted. The exception (M4) proves the
rule. *Evidence: journal/challenge-2026-07-08.md, Learning #1*

**M4. The ETH15M anomaly.** The one crypto family persistently positive:
+1.68% over 4 weeks (n=379, positive 3 of 4 weeks) while BTC/SOL controls
sit at/below zero in identical configs. Modest, regime-dependent,
paper-only until it survives more regimes.
*Evidence: hypotheses-4wk file, H12; hypotheses-2026-07-08.md, H3*

**M5. In-play sports favorites LOSE.** 444 settled games: entries during
play run 71–87% win rates against a ~94% breakeven (-5% to -16% ROI);
only pre-game entries (4–12h out) are +EV (+2.9% at 95.7%). Markets
underprice comeback risk mid-game. The old "no in-play" rule was right,
but for the wrong reason — it was blamed on stop-loss whipsaw.
*Evidence: journal/backtests/hypotheses-2026-07-08.md, H1*

**M6. Tight stop-losses destroy value on favorites; disaster stops must
trigger off the ASK.** Stops at 0.10/0.25 points lost money in EVERY
backtest configuration (favorites dip on noise and recover). And on thin
books the BID collapses spuriously — bid-triggered stops phantom-fired in
130/266 backtest trades. Current design: 0.55-point disaster stop,
ask-triggered, take-profit at 0.98 (H8: same ROI as 0.99, ~3h faster
capital recycling). *Evidence: v2 grid + hypotheses files*

**M7. Fees are a first-class strategy input.** Kalshi taker fees
(≈0.07·P·(1−P) per contract) consume roughly a third of the gross edge at
0.93 entries. Polymarket currently charges zero. Any strategy comparison
that ignores fees is fiction. *Evidence: fee modeling in polma/backtest.py*

**M8. Time-of-day changes opportunity COUNT, not quality.** Overnight UTC
is a candidate desert (Learning #5 of the challenge) but entry quality is
flat across UTC buckets (H6). Cadence and patience solve this; strategy
changes don't.

**M9. Correlated positions are an unpriced risk.** The books repeatedly
held multiple positions on one event (France–Morocco cluster; the
challenge's FDV family). No correlation guard exists yet in code — it's
the top known gap. *Flagged in rules notes since v2.*

---

## II. Risk & sizing learnings

**R1. A floor only binds if every position's worst case respects it.**
The challenge set a $56 floor, then sized one $30 binary position whose
total loss landed at $44.82. Sizing authorization is a CEILING, not a
target. Now enforced in code: `risk.max_notional` caps every position at
(equity − drawdown floor). *Evidence: LAD post-mortem; challenge Learning #6*

**R2. Guardrails beat intentions — keep them layered and sacred.** The
exposure cap stopped a runaway loop bug; the drawdown halt stopped
loss-chasing after the LAD loss; the daily-loss limit correctly blocked
resumed trading. Every one of them fired before a human could have. Halts
get cleared by explicit owner review, never by the bot; one-day exceptions
are implemented as self-expiring, journaled waivers, not rule edits.
*Evidence: challenge close-out; HALT_CLEARED + GUARDRAIL_WAIVER journal events*

**R3. Sizing scales growth linearly and tail-pain super-linearly.** Monte
Carlo on the empirical distribution: 8% sizing ≈ 3× the median growth of
2.5%, with p10 of -12%; 12% tips into 10% halt probability. And the halt
line must scale with sizing (5% sizing self-halts on noise at a 15% line).
Promotion criterion on record: ≥50 live/paper settled trades at ≤5% loss
rate unlocks 5% sizing with a 25% halt.
*Evidence: hypotheses-2026-07-08.md, H2*

**R4. Unrealized peaks count toward drawdown.** Mark-to-market highs (LAD
at 0.85) set the peak the halt measures from. Correct and conservative —
but it means naked variance positions donate their high-water mark. If
variance legs ever return: pre-committed take-profit.

**R5. Books must be accounting-isolated.** The live LAD loss initially
froze the PAPER books via a shared daily-loss counter. Every journal event
now carries venue+mode+profile, and every limit check filters to its own
book. *Evidence: per-book daily-loss commit*

---

## III. Backtesting & methodology learnings

**B1. Backtest before deploying, every time.** The pre-challenge backtest
flipped v1 rules from -7% to +9% before a dollar moved; the intraday
backtest killed the crypto-scalping plan that "felt" right; the H1 test
killed in-play before the paper book could bleed on it. Minutes of
backtesting repeatedly beat days of live discovery.

**B2. Distrust your own positive results — attack them.** The "+3.5%
validated Kalshi edge" from a 300-market sample largely dissolved under
the 4-week, all-family, out-of-sample methodology. Backtests need:
stratified sampling across time, controls (BTC/SOL for ETH), half-period
consistency, and out-of-sample family selection tests. Selection bias is
the default state of trading research, not an edge case.

**B3. Match live filters to measured filters.** The live book was
rejecting in-band trades in validated families because its liquidity
threshold ($10k OI) was stricter than the backtest's inclusion filter
($2k volume). If the backtest measured it, the live config should trade
it — and vice versa. *Evidence: v9 commit*

**B4. Backtest at the venue's actual fidelity.** Kalshi candles carry
real bid AND ask — entries simulated at ask, exits at bid, fees exact.
Polymarket history is a single mid-ish series requiring slippage guesses.
Fidelity differences change conclusions; know which one you're getting.

**B5. Simulated fills must walk the real book.** Band-checking the MID
while filling at the ASK bought a 0.982 entry that "passed" a 0.97 band —
needing a 98.4% win rate to break even. Candidates are now band-checked
against the effective ask. *Evidence: challenge Learning #4 (permanent
engine fix)*

---

## IV. Engineering & infrastructure learnings

**E1. Ticker prefixes leak — in BOTH directions.** Excluding `KXBTC15M`
didn't exclude the `KXBTC-` range family (challenge); including `KXRT`
(Rotten Tomatoes) accidentally included `KXRTX5090` GPU markets (v9).
Family selectors need deliberate stem/dash discipline and a funnel check
after every change.

**E2. Infrastructure is part of risk.** Container restarts killed trading
loops mid-challenge; positions went unmanaged for ~40-minute stretches;
the fast in-session loop dies every ~30 minutes to a monitor clamp. The
hourly scheduled Routine is the only cadence that has proven reliable —
design around the reliable backstop and treat fast loops as best-effort.
(Corollary: the right cadence upgrade is a cheap exits-only fast loop,
not a faster full-scan loop.)

**E3. Headless/spawned sessions are constrained by design.** They start
with EMPTY workspaces (must clone by exact repo name), have READ-ONLY git,
and cannot authorize real-money orders — the safety layer requires owner
authorization verifiable in the session doing the trading. Architecture:
live trading runs in the owner-authorized session (woken hourly);
headless sessions do read-only checks. *Evidence: docs/GOING_LIVE.md*

**E4. Env-var UIs mangle secrets.** Single-line fields, length caps,
flattened newlines. The Kalshi RSA key survives as base64 chunks across
numbered variables reassembled by a tolerant loader (handles escaped \n,
flattened spaces, quotes, base64, chunking). Diagnose with structural
metadata (lengths, character classes), never key material.

**E5. APIs move — verify against live docs, then against the live API.**
Polymarket had migrated collateral, contracts, SDK, and (fatally for our
first order) the order endpoint (HTTP 410 → V2 with different semantics:
YES-leg bid/ask, dollar strings, new fill schema). The $1 round-trip test
exists precisely to catch this class of failure; it did.

**E6. The cheapest reliability wins compound.** Retrying HTTP session;
`reduce_only` on every exit order (an exit can never flip into a short);
live portfolios initialize from the real account balance and refuse to
trade blind; profile experiments are paper-only by hard engine guard;
every book has its own state file.

---

## V. Process learnings

**P1. Rules as data + journal as audit trail works.** Nine rule versions
in two days, each traceable: every trade records the rules version that
produced it, every loss gets a post-mortem, every rule change cites its
backtest. The git history of rules/ + journal/ is the complete record of
what was tried, what it cost, and why it changed.

**P2. Losses are tuition — but only if the post-mortem distinguishes
"bad luck" from "bad process."** The LAD loss was 26% variance (fine)
wrapped in a sizing error (not fine). The lesson that got encoded in code
was the sizing rule, not "don't bet on baseball."

**P3. Aggressive experiments belong in isolated paper books.** The
base/aggr/eth15 profile system runs riskier hypotheses with real market
data and zero real-money exposure, while the live book stays on the
evidence. The aggressive book's drifting marks (-3.7% in its first day on
the broad universe) are already re-confirming the include-list decision.

**P4. Honest expectations, pre-registered.** The 6h challenge was
pre-registered as a stretch goal with a floor; the daily live forecast
(+$0.15–0.30 with a ~20% chance of a red day) was published before the
day. Being measurably wrong is itself data — but only if the prediction
was written down first.

---

## Current state (as of 2026-07-08, rules v9)

- **Live (Kalshi):** ~$45, 1-contract positions, six-family include-list,
  all guardrails at conservative values. Expected pace: cents/day until
  the 50-trade promotion gate or a larger deposit.
- **Paper:** base books on both venues; aggr book (broad universe, 8%
  sizing) and eth15 book as controlled experiments.
- **Top open questions:** Polymarket universe needs the same 4-week
  family methodology; correlation guard unbuilt; WTI mechanism
  unexplained (provisional); ETH15M regime-dependence.
