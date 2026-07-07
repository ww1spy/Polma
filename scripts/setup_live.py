"""One-time live-trading onboarding. Run AFTER the env vars are set:

    pip install -r requirements-live.txt
    python3 scripts/setup_live.py

Verifies credentials, runs Polymarket's idempotent trading-approvals setup,
and prints the account state. Places NO orders.
"""
import asyncio
import os
import sys


async def main():
    key = os.environ.get("POLYMARKET_PRIVATE_KEY")
    if not key:
        sys.exit("POLYMARKET_PRIVATE_KEY is not set — see docs/GOING_LIVE.md")
    wallet = os.environ.get("POLYMARKET_WALLET_ADDRESS") or None

    from polymarket import AsyncSecureClient

    async with await AsyncSecureClient.create(private_key=key, wallet=wallet) as client:
        print("authenticated OK")
        print("running setup_trading_approvals() (idempotent)…")
        await client.setup_trading_approvals()
        print("approvals in place — account can trade")


if __name__ == "__main__":
    asyncio.run(main())
