# Polma — rules-driven prediction-market trading bot (Kalshi + Polymarket)

A conservative, rules-driven trading bot for prediction markets. The strategy
lives in a YAML file that gets edited and re-committed as it evolves; the
engine, risk guardrails, and trade journal stay fixed. Two venues behind one
interface (`polma/venues/`): **Kalshi** (CFTC-regulated, the live venue for US
users) and **Polymarket** (paper testbed; live only where eligible).
**Currently paper-trading only** — real market data and order books, simulated
fills (taker fees modeled), simulated bankroll.

## How it works

Each **cycle** (run on a schedule) does, in order:

1. **Settle** — positions in markets that resolved get paid out at $1 or $0.
2. **Mark** — every open position is valued at the live best bid.
3. **Exit** — stop-loss and take-profit rules from `rules/rules.yaml` fire.
4. **Risk check** — drawdown/daily-loss guardrails from `config/risk_limits.yaml`
   can halt all new entries. Guardrails always override strategy rules.
5. **Scan & enter** — markets passing the universe filters and an enabled
   strategy's conditions are entered, most-liquid-first, within sizing limits.
6. **Journal** — every action is appended to `journal/`; losing trades get a
   post-mortem stub in `journal/postmortems/` to be filled in during review.

## Layout

| Path | What it is | Who edits it |
|---|---|---|
| `rules/rules.yaml` | The strategy: universe, entries, exits, sizing | **You, often** |
| `config/risk_limits.yaml` | Hard guardrails that override the rules | Rarely, deliberately |
| `polma/` | The engine (scanner, executor, risk, journal) | Code changes only |
| `state/portfolio.json` | Current paper portfolio (committed = auditable) | The bot |
| `journal/trades.jsonl` | Every enter/exit/settle/block event | The bot |
| `journal/cycles.jsonl` | One summary line per cycle | The bot |
| `journal/postmortems/` | One markdown file per losing trade | Bot creates, you fill in |

## Running

```bash
pip install -r requirements.txt
python3 -m polma.cycle              # one trading cycle (paper, polymarket default)
POLMA_VENUE=kalshi python3 -m polma.cycle      # same, on Kalshi
POLMA_VENUE=kalshi python3 -m polma.report     # portfolio + win/loss summary
POLMA_VENUE=kalshi python3 -m polma.backtest   # replay rules over resolved markets
```

Env switches: `POLMA_VENUE` (`polymarket`|`kalshi`), `POLMA_MODE`
(`paper`|`live`). Each venue+mode pair keeps its own state file under
`state/`; rules support per-venue overrides (`venue_overrides:` in
`rules/rules.yaml`) because the venues' profitable pockets genuinely differ.

The backtester is the fast learning loop: it replays the current rules over
hundreds of already-resolved markets' hourly price history and reports win
rate / ROI, with results archived in `journal/backtests/`. Its caveats are
documented in `polma/backtest.py` — use it to rank rule variants, not to
predict returns.

## Operating the system

**`docs/OPERATIONS.md`** is the run book: how to run all five books from any
machine on a cron (`ops/hourly.sh`), read the weekly revalidation reports,
clear a halt, and what the promotion gates are. It's written so a new
operator can take over cold.

## The learning loop

**Read `docs/LEARNINGS.md` first** — the consolidated distillation of every
market, risk, methodology, engineering, and process lesson to date, each
linked to its primary evidence in `journal/`.


1. Bot trades on the current rules; every decision is journaled with the
   rules `version` that produced it.
2. Losses generate post-mortem stubs. During review, fill in *why* it lost
   and what rule change (if any) follows.
3. Edit `rules/rules.yaml`, bump `version`, update `updated`, commit.
4. Git history of `rules/` + `journal/` = the full record of what was tried,
   what it cost, and what was learned.

## Going live

`LiveExecutor` is wired to the official `polymarket-client` SDK and activates
only when `POLMA_MODE=live` **and** `POLYMARKET_PRIVATE_KEY` is set in the
environment (never in the repo). Live state is tracked separately in
`state/portfolio_live.json`. The owner-side setup checklist and the
validation sequence ($1 test orders before real sizing) are in
**`docs/GOING_LIVE.md`**. Trading live requires eligibility under
Polymarket's terms in your jurisdiction.
