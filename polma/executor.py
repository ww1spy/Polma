"""Order execution. PaperExecutor simulates fills against the real live book.

LiveExecutor is a deliberate stub: it gets wired to py-clob-client (signed
orders, real USDC) only after the paper phase proves the rules out.
"""
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
    def buy(self, token_id, notional):
        raise NotImplementedError(
            "Live trading is not wired up yet. It requires py-clob-client, a funded "
            "Polygon wallet (POLYMARKET_PRIVATE_KEY), and explicit sign-off after the "
            "paper phase."
        )

    sell = buy
