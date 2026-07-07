"""Venue abstraction: every venue exposes the same interface to the engine.

    open_markets(max_markets) -> [normalized market dicts]
    market(market_id)         -> normalized market dict (for settlement checks)
    book(token_id)            -> {"bids": [(price, size)...], "asks": [...]}, best first
    taker_fee(price, qty)     -> fee in dollars for a marketable order
    name                      -> venue slug used in state files and journal

Normalized market dict fields: id, question, outcomes, prices, token_ids,
liquidity, volume_24h, spread, end_date, min_order_size, closed.
"""


def get_venue(name):
    name = (name or "polymarket").lower()
    if name == "polymarket":
        from .polymarket import PolymarketVenue
        return PolymarketVenue()
    if name == "kalshi":
        from .kalshi import KalshiVenue
        return KalshiVenue()
    raise ValueError(f"unknown venue: {name!r} (expected 'polymarket' or 'kalshi')")
