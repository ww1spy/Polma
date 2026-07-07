"""Order execution. PaperExecutor simulates fills against the real live book.

LiveExecutor places real orders via the official `polymarket-client` SDK.
It activates only when POLMA_MODE=live and POLYMARKET_PRIVATE_KEY is set,
and must be validated with $1-sized orders before real sizing.
"""
import os

from . import clob


class PaperExecutor:
    """Simulates immediate-or-cancel fills by walking the live order book."""

    def buy(self, token_id, notional):
        """Spend up to `notional` USD walking the asks. Returns fill or None."""
        book = clob.get_book(token_id)
        return self._walk(book["asks"], notional_budget=notional)

    def sell(self, token_id, qty):
        """Sell up to `qty` shares walking the bids. Returns fill or None."""
        book = clob.get_book(token_id)
        return self._walk(book["bids"], qty_budget=qty)

    @staticmethod
    def _walk(levels, notional_budget=None, qty_budget=None):
        filled_qty = 0.0
        filled_notional = 0.0
        for price, size in levels:
            if notional_budget is not None:
                remaining = notional_budget - filled_notional
                take = min(size, remaining / price)
            else:
                take = min(size, qty_budget - filled_qty)
            if take <= 1e-9:
                break
            filled_qty += take
            filled_notional += take * price
        if filled_qty <= 0:
            return None
        return {
            "qty": round(filled_qty, 2),
            "notional": round(filled_notional, 2),
            "avg_price": round(filled_notional / filled_qty, 4),
        }


class LiveExecutor:
    """Real orders through the official Polymarket SDK (requirements-live.txt).

    Marketable FAK (fill-and-kill) orders with a 2% max-spend buffer on buys.
    The engine's interface is sync; each call opens an authenticated client.
    """

    MAX_SPEND_BUFFER = 1.02

    def __init__(self):
        self.key = os.environ.get("POLYMARKET_PRIVATE_KEY")
        self.wallet = os.environ.get("POLYMARKET_WALLET_ADDRESS") or None
        if not self.key:
            raise RuntimeError(
                "POLMA_MODE=live but POLYMARKET_PRIVATE_KEY is not set. "
                "See docs/GOING_LIVE.md."
            )

    def _run(self, op):
        import asyncio

        from polymarket import AsyncSecureClient

        async def go():
            async with await AsyncSecureClient.create(
                private_key=self.key, wallet=self.wallet
            ) as client:
                return await op(client)

        return asyncio.run(go())

    def buy(self, token_id, notional):
        async def op(client):
            return await client.place_market_order(
                token_id=token_id,
                side="BUY",
                amount=f"{notional:.2f}",
                max_spend=f"{notional * self.MAX_SPEND_BUFFER:.2f}",
                order_type="FAK",
            )

        return self._to_fill(self._run(op), fallback_notional=notional)

    def sell(self, token_id, qty):
        async def op(client):
            return await client.place_market_order(
                token_id=token_id,
                side="SELL",
                amount=f"{qty:.2f}",
                order_type="FAK",
            )

        return self._to_fill(self._run(op), fallback_qty=qty)

    @staticmethod
    def _to_fill(response, fallback_notional=None, fallback_qty=None):
        """Normalize an SDK order response to the engine's fill dict."""
        if response is None or not getattr(response, "ok", False):
            raise RuntimeError(f"live order rejected: {response!r}")
        data = {}
        for attr in ("model_dump", "dict"):
            if hasattr(response, attr):
                data = getattr(response, attr)()
                break
        qty = float(data.get("size_matched") or data.get("filled_size")
                    or fallback_qty or 0)
        notional = float(data.get("amount_matched") or fallback_notional or 0)
        if qty <= 0 and notional <= 0:
            return None
        if qty <= 0 or notional <= 0:
            # Partial info from the API — record what we know; reconcile from
            # the account's positions during the next cycle.
            qty = qty or notional
            notional = notional or qty
        return {
            "qty": round(qty, 2),
            "notional": round(notional, 2),
            "avg_price": round(notional / qty, 4) if qty else None,
            "raw": data,
        }
