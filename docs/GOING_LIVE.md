# Going live on Kalshi: what YOU need to set up

Kalshi is the live venue: CFTC-regulated, legal for US citizens, web-based
(no iPhone needed), and API-friendly. The bot is code-complete for it but
cannot go live until you provide API credentials. Your part takes ~30
minutes, most of it waiting on KYC.

## Your checklist

1. **Create a Kalshi account** at kalshi.com — standard web signup with
   KYC (SSN, ID verification, US persons welcome). Note: a few states
   restrict specific market types (e.g. sports contracts); Kalshi's UI
   enforces this per your residence automatically.

2. **Deposit small.** Fund what live *testing* needs — $50–$200 via bank
   transfer or debit. Scale up only after the bot has proven itself with
   real fills.

3. **Create an API key.** Log in → https://kalshi.com/account/profile →
   "API Keys" → "Create New API Key". You get:
   - a **Key ID**, and
   - an **RSA private key** (PEM file) shown **once** — download it
     immediately; Kalshi does not store it and cannot recover it.

4. **Put the credentials into the Claude Code environment settings** (the
   environment this repo runs in → environment variables):
   - `KALSHI_API_KEY_ID` — the Key ID
   - `KALSHI_PRIVATE_KEY` — the full PEM contents (multi-line), **or**
     `KALSHI_PRIVATE_KEY_PATH` — a path to the PEM file if you mount it

   **Never** paste the key into chat, commit it, or put it in this repo.
   Anyone with it can trade (though Kalshi API keys cannot withdraw funds
   — withdrawals stay behind your login).

## Then the validation sequence (run together, in order)

1. `pip install -r requirements-live.txt`
2. `python3 scripts/setup_live.py` — verifies signed authentication and
   prints the account balance. Places NO orders.
3. One **1-contract buy** and **1-contract sell** via the live executor,
   outside the engine, to validate order plumbing and fill parsing end to
   end (order-field names must be confirmed against the real API).
4. First live engine cycle: `POLMA_VENUE=kalshi POLMA_MODE=live` with
   sizing floored (`max_notional_per_trade_usd: 2`).
5. Only after 1–4 are clean: set `starting_bankroll_usd` in
   `config/risk_limits.yaml` to the real deposit, raise sizing to the
   normal conservative limits, and schedule the live Routine.

Live state is tracked separately in `state/portfolio_kalshi_live.json`;
paper trading keeps running in parallel on both venues as the strategy
testbed.

## Polymarket (non-US path, parked)

The Polymarket executor remains wired (`polymarket-client` SDK,
`POLYMARKET_PRIVATE_KEY` / `POLYMARKET_WALLET_ADDRESS`). US persons can't
use the main exchange; Polymarket US is iOS-only as of July 2026. If that
changes, the validation sequence mirrors the one above.
