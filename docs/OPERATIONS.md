# Operations manual (handoff)

This is the run book for operating Polma **without the original operator**.
It assumes you can run Python on any machine (laptop, server, or a phone via
Termux) and have push access to this repo. Companion docs:

- `docs/GOING_LIVE.md` — Kalshi account, API keys, credential env vars.
- `docs/LEARNINGS.md` — every lesson behind every rule; read before changing anything.
- `README.md` — repo layout and what each directory is for.

---

## 1. What runs, and why

One engine (`polma/`), five independent **books**. Each book is a
(venue, mode, profile) triple with its own state file in `state/` and its own
tagged rows in `journal/trades.jsonl` / `journal/cycles.jsonl`. The engine's
cycle is: settle resolved markets → mark positions → apply exits → scan for
candidates → apply entries, all under the hard limits in `config/`.

| book | purpose | state file |
|---|---|---|
| kalshi **live** | real money, include-list families only, 2.5% sizing | `portfolio_kalshi_live.json` |
| kalshi paper | shadow of the live rules at $500 paper | `portfolio_kalshi.json` |
| polymarket paper | keeps the second venue's rules honest for a future US launch | `portfolio.json` |
| aggr paper | broad-universe discovery at a wider risk envelope | `portfolio_kalshi_aggr.json` |
| eth15 paper | single-family fast-favorite experiment (H3) | `portfolio_kalshi_eth15.json` |

Paper books exist to generate evidence; the live book only ever trades what
paper + backtests have already validated twice (see §7 promotion gates).

## 2. Setup on a new machine

```bash
git clone https://github.com/ww1spy/Polma && cd Polma
pip install -r requirements.txt        # requests, PyYAML; live also needs: pip install cryptography
```

For the **live book only**, set the Kalshi credentials
(`KALSHI_API_KEY_ID`, `KALSHI_PRIVATE_KEY` or chunked
`KALSHI_PRIVATE_KEY_1..N`, or `KALSHI_PRIVATE_KEY_PATH`) — full walkthrough
including phone/Termux in `docs/GOING_LIVE.md`. Paper books need no
credentials at all; Kalshi's market-data endpoints are public.

**Never** commit a key, paste one into a chat/issue, or print one in logs.
`python3 -c "from polma.venues.kalshi import diagnose_pem; diagnose_pem()"`
prints only safe structural metadata when debugging a mangled key.

## 3. The hourly operating loop

Run every book once per hour, then commit and push state + journal (git is
the system's memory — an unpushed state file dies with the machine). The
whole loop is `ops/hourly.sh`: it pulls, runs the four paper books, runs the
live book last with a clean profile environment (skipped automatically if no
Kalshi credentials are set), then commits and pushes with retry. One failing
book doesn't stop the others.

Cron (any Linux/macOS box, or Termux with `pkg install cronie termux-services`):

```
5 * * * * cd $HOME/Polma && ./ops/hourly.sh >> cron.log 2>&1
```

Why hourly: the live families (RT, Trump-mention, WT20) move on hour-plus
timescales, and hold-to-resolution means exits rarely need speed. The stop
is disaster-only (0.55 points). Running more often mostly adds fee-paying
churn; less often risks missing the entry band. Revisit only if sizing grows
(an exits-only fast loop is sketched in LEARNINGS E-notes).

Check on things anytime with:

```bash
POLMA_VENUE=kalshi POLMA_MODE=live python3 -m polma.report
```

**Missed hours are fine.** Nothing decays badly: entries are opportunistic,
exits settle on their own. After downtime just resume the loop.

**Deposits/withdrawals (live book):** the engine detects a brand-new live
book and initializes from the real balance, but a deposit into an existing
book must be synced by hand: add the deposit amount to BOTH `cash` and
`peak_equity` in `state/portfolio_kalshi_live.json` (equal baseline shift —
otherwise the deposit reads as "profit" and inflates the drawdown floor),
then commit with a note.

## 4. Weekly revalidation

```bash
python3 -m polma.revalidate            # full: slow families + fast (eth15) section
python3 -m polma.revalidate --fast-only  # just the 1-min-candle eth15 section (~2 min)
```

Runs every live include-list family and the watchlist over the full ~60-day
API retention window (and the eth15 family + BTC control over 7 days of
1-minute candles), with half-period consistency, and writes
`journal/revalidations/YYYY-MM-DD.md`. Read the **verdict** column:

- **DEMOTE** (live family went negative): pre-authorized — remove its prefix
  from `include_ticker_prefixes` in `rules/rules.yaml` (kalshi
  venue_overrides), bump the rules `version`, note why in the yaml comment,
  commit. Then **audit open positions**: any position in a demoted family
  should be exited at the next reasonable bid (lesson: the LA-temp position
  that lingered after weather was excluded).
- **REVIEW** (one negative half): no rule change; watch next week. Two
  consecutive REVIEWs → treat as DEMOTE.
- **PROMOTE-CANDIDATE** (watchlist family, n≥30, both halves positive):
  **requires human judgment** — you must articulate a mechanism (WHY the
  edge exists) before adding it to the live list. No mechanism, no promotion.
- Fast-section flags apply to the eth15 **paper** book: DEMOTE = stop
  running that book; the BTC control row is informational (if the control
  turns positive too, the "edge" is market regime, not family skill).

The script never edits rules itself. Demotions are the only rule change
pre-authorized to happen without a human reviewing anything beyond the report.

## 5. Halts and how to clear them

Three automatic brakes, all in `config/risk_limits.yaml`:

1. **Per-trade / exposure / position caps** — silent skips, no action needed.
2. **Daily realized-loss limit** (5%) — blocks new entries until UTC
   midnight; exits keep working. Self-clears. A one-day owner exception is a
   **waiver**: set `"daily_loss_waiver": "YYYY-MM-DD"` (today, UTC) in the
   book's state file and journal why. It expires at midnight and never
   weakens the rule itself.
3. **Drawdown halt** (15% below peak equity) — sets `"halted": true` in the
   state file and stops ALL new entries until a human clears it.

To clear a drawdown halt (owner or successor only):

1. Read the journal for the losing trades (`journal/trades.jsonl`, the
   auto-generated stubs in `journal/postmortems/`).
2. Write/complete the post-mortem: what rule allowed the loss, what changes.
3. Only then edit the state file: `"halted": false, "halt_reason": ""`. If
   the loss is accepted as the new baseline, also lower `peak_equity` to the
   current equity (this resets the 15% floor; leaving the old peak keeps the
   halt hair-triggered).
4. Commit state + post-mortem together.

Never clear a halt from an automated/scheduled run. That defeats its purpose.

## 6. Who may change what

| artifact | scheduled runs | human operator |
|---|---|---|
| `state/`, `journal/` | write freely | write freely |
| `rules/*.yaml` | **never** (exception: pre-authorized demotions in the weekly session) | yes, with a version bump + comment |
| `config/risk_limits*.yaml` | **never** | rarely, deliberately, never mid-drawdown |
| sizing fractions, caps | **never raise** | only via §7 gates |
| credentials | never touch | env vars only |

## 7. Promotion gates (the only sanctioned ways to get more aggressive)

- **Family → live list**: survives two independent evaluation periods
  (e.g. the June study AND the May out-of-sample rerun) with positive ROI in
  both halves of each, plus a stated mechanism. One good period is noise —
  that's how MLB/WTI/FIBA got in and then demoted.
- **Sizing 2.5% → 5%** (with drawdown halt loosened 15% → 25%): requires
  **≥50 settled live trades at ≤5% loss rate**. Count them from
  `journal/trades.jsonl` (venue=kalshi, mode=live, SETTLE events). Human
  applies the change to `rules/rules.yaml` sizing + `config/risk_limits.yaml`.
- **eth15 → live**: not gated yet. It would need its own faster loop
  (15-min markets can't be traded well on an hourly cron) and a fill-quality
  review of the paper book first. Treat as research until then.

Demotions and halts need no permission. Promotions always do. When in doubt,
the conservative direction is always pre-authorized.

## 8. Journal discipline

- Every settled loss gets a post-mortem (auto-stubbed in
  `journal/postmortems/`, finish it by hand): what happened, which rule
  allowed it, what changes (possibly nothing — variance is real).
- Every rule version bump: one line in the yaml comment citing evidence
  (a backtest file, a post-mortem, a revalidation report).
- Backtests live in `journal/backtests/` with their methodology caveats —
  read `hypotheses-4wk-2026-07-08.md` and `oos-may-2026-07-08.md` before
  trusting any number in them.

## 9. Safety invariants (do not relax)

- Live orders only from an environment where the account owner has
  authorized real-money trading. Paper is the default everywhere
  (`POLMA_MODE=live` must be explicit; profiles are hard-blocked from live).
- The engine refuses to start a live book blind (no balance = no trading).
- Band checks and stops evaluate against the effective **ask** (thin books
  make mid a lie); keep it that way.
- New include-prefixes must end at a real token boundary (`KXRT-` not
  `KXRT`) — both prefix-leak incidents (RTX5090 GPUs, WTIW weekly) came from
  this, and both cost real money.
- When the include-list tightens, audit ALL open positions the same day.

## 10. State at handoff (2026-07-09)

- Live book: $103.04, 0 open positions, 2.5% sizing, v11 rules
  (include-list: `KXRT-`, `KXTRUMPSAY`, `KXWT20MATCH`; two strategies —
  the 0.90-0.97 favorite band plus the KXRT-only 0.97-0.995 last-mile).
- Honest read of the edge (LEARNINGS, bottom line): the *pooled* Kalshi
  favorite strategy is negative; only RT/Trump-mention survived two
  independent periods, WT20 is provisional, eth15 is paper-only but healthy
  on the latest 7-day revalidation (+0.9% ROI vs BTC control −0.2%).
  Forward paper/live performance is the remaining out-of-sample test —
  expect slow weeks; that is the strategy working, not failing.
- Known gaps: no cross-family correlation guard (M9 — the per-event and
  per-family guards exist); eth15 needs its own fast loop before any live
  consideration; Polymarket live path (`PolymarketLiveExecutor`) is written
  but has never placed a real order.
