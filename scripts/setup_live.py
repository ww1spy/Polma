"""One-time live-trading onboarding check. Run AFTER the env vars are set:

    pip install -r requirements-live.txt
    python3 scripts/setup_live.py [kalshi|polymarket]

Verifies credentials work (and on Polymarket, runs the idempotent
trading-approvals setup). Places NO orders.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def check_kalshi():
    import json

    from polma.http import SESSION
    from polma.venues.kalshi import auth_headers, diagnose_pem, load_private_key_env

    key_id = os.environ.get("KALSHI_API_KEY_ID")
    pem = load_private_key_env()
    if not (key_id and pem):
        sys.exit("KALSHI_API_KEY_ID / KALSHI_PRIVATE_KEY not set (or the key isn't "
                 "valid PEM) — see docs/GOING_LIVE.md")

    from cryptography.hazmat.primitives import serialization

    try:
        serialization.load_pem_private_key(pem.encode(), password=None)
    except Exception as e:
        print(f"private key failed to parse: {type(e).__name__}")
        print("safe structural diagnostics (no key material):")
        print(json.dumps(diagnose_pem(pem), indent=2))
        sys.exit(1)

    path = "/trade-api/v2/portfolio/balance"
    resp = SESSION.get(
        f"https://api.elections.kalshi.com{path}",
        headers=auth_headers(key_id, pem, "GET", path),
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    print("kalshi authentication OK")
    print(f"balance: {data}")


def check_polymarket():
    import asyncio

    key = os.environ.get("POLYMARKET_PRIVATE_KEY")
    if not key:
        sys.exit("POLYMARKET_PRIVATE_KEY not set — see docs/GOING_LIVE.md")
    wallet = os.environ.get("POLYMARKET_WALLET_ADDRESS") or None

    from polymarket import AsyncSecureClient

    async def go():
        async with await AsyncSecureClient.create(private_key=key, wallet=wallet) as c:
            print("polymarket authentication OK")
            print("running setup_trading_approvals() (idempotent)…")
            await c.setup_trading_approvals()
            print("approvals in place — account can trade")

    asyncio.run(go())


if __name__ == "__main__":
    venue = (sys.argv[1] if len(sys.argv) > 1 else "kalshi").lower()
    check_kalshi() if venue == "kalshi" else check_polymarket()
