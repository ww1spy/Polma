"""Order execution.

PaperExecutor simulates fills against the venue's real live book, including
taker fees. Live executors place real orders and are gated behind
POLMA_MODE=live plus venue credentials in the environment; both must be
validated with minimum-size orders before real sizing (docs/GOING_LIVE.md).
"""
import os
import uuid


class PaperExecutor:
    """Simulates immediate-or-cancel fills by walking the live order book."""

    def __init__(self, venue):
        self.venue = venue

    def buy(self, token_id, notional):
        """Spend up to `notional` USD (fees included) walking the asks."""
        book = self.venue.book(token_id)
        fill = self._walk(book["asks"], notional_budget=notional)
        if fill:
            fee = self.venue.taker_fee(fill["avg_price"], fill["qty"])
            fill["fee"] = fee
            fill["notional"] = round(fill["notional"] + fee, 2)
        return fill

    def sell(self, token_id, qty):
        """Sell up to `qty` shares walking the bids; proceeds are net of fees."""
        book = self.venue.book(token_id)
        fill = self._walk(book["bids"], qty_budget=qty)
        if fill:
            fee = self.venue.taker_fee(fill["avg_price"], fill["qty"])
            fill["fee"] = fee
            fill["notional"] = round(fill["notional"] - fee, 2)
        return fill

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


class KalshiLiveExecutor:
    """Real Kalshi orders via the V2 order API (marketable limit IOC).

    V2 semantics (docs.kalshi.com api-reference/orders/create-order-v2):
    everything is expressed on the YES leg — side is "bid"/"ask", prices are
    dollar strings. Buying NO == ask on YES at (1 - no_price); selling NO ==
    bid on YES. Fills come back as fill_count / average_fill_price /
    average_fee_paid (per contract).
    """

    ORDER_HOSTS = ("https://external-api.kalshi.com",
                   "https://api.elections.kalshi.com")
    ORDERS_PATH = "/trade-api/v2/portfolio/events/orders"

    def __init__(self):
        from .venues import kalshi

        self.kalshi = kalshi
        self.key_id = os.environ.get("KALSHI_API_KEY_ID")
        self.pem = kalshi.load_private_key_env()
        if not (self.key_id and self.pem):
            raise RuntimeError(
                "POLMA_MODE=live on kalshi needs KALSHI_API_KEY_ID and "
                "KALSHI_PRIVATE_KEY (or KALSHI_PRIVATE_KEY_PATH). See docs/GOING_LIVE.md."
            )

    def _post(self, path, payload):
        from .http import SESSION

        last_err = None
        for host in self.ORDER_HOSTS:
            headers = self.kalshi.auth_headers(self.key_id, self.pem, "POST", path)
            resp = SESSION.post(f"{host}{path}", json=payload,
                                headers=headers, timeout=20)
            if resp.status_code in (404, 410):
                last_err = resp  # endpoint not on this host — try the next
                continue
            resp.raise_for_status()
            return resp.json()
        last_err.raise_for_status()

    def _order(self, token_id, action, count, limit_price):
        """Place an IOC limit order. count = whole contracts; limit_price is
        in the TOKEN's own price space (no-tokens use NO prices)."""
        ticker, leg = token_id.rsplit(":", 1)
        if leg == "yes":
            side = "bid" if action == "buy" else "ask"
            yes_price = limit_price
        else:
            side = "ask" if action == "buy" else "bid"
            yes_price = 1.0 - limit_price
        yes_price = min(max(round(yes_price, 4), 0.01), 0.99)
        payload = {
            "ticker": ticker,
            "client_order_id": str(uuid.uuid4()),
            "side": side,
            "count": f"{count:.2f}",
            "price": f"{yes_price:.4f}",
            "time_in_force": "immediate_or_cancel",
            "self_trade_prevention_type": "taker_at_cross",
        }
        if action == "sell":
            payload["reduce_only"] = True  # never flip an exit into a short
        data = self._post(self.ORDERS_PATH, payload)
        order = data.get("order", data)
        fill = float(order.get("fill_count") or 0)
        if fill <= 0:
            return None
        avg_yes = float(order.get("average_fill_price") or yes_price)
        fee = round(float(order.get("average_fee_paid") or 0) * fill, 4)
        avg_tok = avg_yes if leg == "yes" else round(1.0 - avg_yes, 4)
        cost = fill * avg_tok
        notional = cost + fee if action == "buy" else cost - fee
        return {"qty": fill, "notional": round(notional, 2),
                "avg_price": round(avg_tok, 4), "fee": round(fee, 2), "raw": order}

    def buy(self, token_id, notional):
        book_ask = self._best_price(token_id, "asks")
        if book_ask is None:
            return None
        count = int(notional // book_ask)
        if count < 1:
            return None
        # cross the spread by a cent to fill IOC
        return self._order(token_id, "buy", count, min(book_ask + 0.01, 0.99))

    def sell(self, token_id, qty):
        book_bid = self._best_price(token_id, "bids")
        if book_bid is None:
            return None
        return self._order(token_id, "sell", int(qty), max(book_bid - 0.01, 0.01))

    def _best_price(self, token_id, side):
        from .venues.kalshi import KalshiVenue

        levels = KalshiVenue().book(token_id)[side]
        return levels[0][0] if levels else None


class PolymarketLiveExecutor:
    """Real orders through the official Polymarket SDK (requirements-live.txt)."""

    MAX_SPEND_BUFFER = 1.02

    def __init__(self):
        self.key = os.environ.get("POLYMARKET_PRIVATE_KEY")
        self.wallet = os.environ.get("POLYMARKET_WALLET_ADDRESS") or None
        if not self.key:
            raise RuntimeError(
                "POLMA_MODE=live on polymarket but POLYMARKET_PRIVATE_KEY is not set. "
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
