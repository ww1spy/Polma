# Going live: what YOU need to set up

The bot is code-complete for live trading but deliberately cannot go live
until you provide credentials. Here is your part (~30 minutes), then the
validation sequence we run together.

## Your checklist

1. **Eligibility.** Polymarket's terms geo-restrict trading in some
   jurisdictions (including the US). Confirm you can trade under their
   terms from where you are. This one is entirely on you — the bot can't
   and won't check it, and we don't work around it.

2. **Create a dedicated Polymarket account** at polymarket.com — email
   signup is easiest. Strongly recommended: a *fresh* account used only by
   the bot, so its key never guards anything else you own.

3. **Fund it small.** Deposit what live *testing* needs, not the full
   bankroll — $50–$200. Card and crypto deposits both work. Scale up only
   after the bot has proven itself with real fills.

4. **Export the wallet's private key.** In the Polymarket app: profile →
   Settings → Export private key. Also copy your **wallet address** (shown
   on your profile / deposit page).

5. **Put both into the Claude Code environment settings** (the environment
   this repo runs in → environment variables):
   - `POLYMARKET_PRIVATE_KEY` — the exported key
   - `POLYMARKET_WALLET_ADDRESS` — your Polymarket wallet address

   **Never** paste the key into chat, commit it, or put it in a file in
   this repo. Env vars only. Anyone with this key controls the funds —
   that includes any tooling running in this environment, which is another
   reason the account should hold only the bot's bankroll.

## Then the validation sequence (I run this, with you watching)

1. `pip install -r requirements-live.txt`
2. `python3 scripts/setup_live.py` — authenticates and runs Polymarket's
   idempotent `setup_trading_approvals()`. No orders placed.
3. One **$1 manual buy** and one **$1 sell** via the live executor, outside
   the engine, to validate order plumbing and fill parsing end to end.
4. First live engine cycle with `POLMA_MODE=live` and sizing caps floored
   (`max_notional_per_trade_usd: 2`).
5. Only after 1–4 are clean: raise sizing to the real conservative limits
   and schedule the live Routine.

Live state is tracked separately in `state/portfolio_live.json`; paper
trading keeps running in parallel as the strategy testbed. Before the first
live cycle, set `starting_bankroll_usd` in `config/risk_limits.yaml` to the
amount actually deposited.
