"""Polymarket venue: thin wrapper over the gamma + clob modules."""
from .. import clob, gamma


class PolymarketVenue:
    name = "polymarket"

    def open_markets(self, max_markets=300, **_):
        return gamma.fetch_open_markets(max_markets=max_markets)

    def market(self, market_id):
        return gamma.fetch_market(market_id)

    def book(self, token_id):
        return clob.get_book(token_id)

    def taker_fee(self, price, qty):
        return 0.0  # Polymarket charges no trading fees on the CLOB today
