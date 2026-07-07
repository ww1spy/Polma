# Polma — rules-driven Polymarket paper/live trading bot

A conservative, rules-driven trading bot for Polymarket. The strategy lives in
a YAML file that gets edited and re-committed as it evolves; the engine, risk
guardrails, and trade journal stay fixed. **Currently paper-trading only** —
real market data, simulated fills, simulated bankroll.

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
python3 -m polma.cycle    # run one trading cycle
python3 -m polma.report   # portfolio + win/loss summary
```

## The learning loop

1. Bot trades on the current rules; every decision is journaled with the
   rules `version` that produced it.
2. Losses generate post-mortem stubs. During review, fill in *why* it lost
   and what rule change (if any) follows.
3. Edit `rules/rules.yaml`, bump `version`, update `updated`, commit.
4. Git history of `rules/` + `journal/` = the full record of what was tried,
   what it cost, and what was learned.

## Going live (later, deliberately)

Live mode requires: the paper phase to prove out the rules, `py-clob-client`
wiring in `polma/executor.py` (`LiveExecutor`), a funded Polygon USDC wallet
whose private key is provided **only** via environment variable (see
`.env.example` — never committed), one-time token allowances for Polymarket's
exchange contracts, and eligibility to trade under Polymarket's terms in your
jurisdiction. The paper→live switch is intentionally not a config flag yet.
