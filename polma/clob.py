"""Read-only client for Polymarket's CLOB API (live order books)."""
import requests

CLOB_URL = "https://clob.polymarket.com"
TIMEOUT = 20


def get_book(token_id):
    """Return {'bids': [(price, size), ...], 'asks': [...]}, best price first.

    The raw API returns levels with the BEST price at the END of each list;
    we sort explicitly so callers never depend on that quirk.
    """
    resp = requests.get(f"{CLOB_URL}/book", params={"token_id": token_id}, timeout=TIMEOUT)
    resp.raise_for_status()
    raw = resp.json()
    bids = sorted(
        ((float(l["price"]), float(l["size"])) for l in raw.get("bids", [])),
        key=lambda l: l[0], reverse=True,
    )
    asks = sorted(
        ((float(l["price"]), float(l["size"])) for l in raw.get("asks", [])),
        key=lambda l: l[0],
    )
    return {"bids": bids, "asks": asks}


def best_bid(book):
    return book["bids"][0][0] if book["bids"] else None


def best_ask(book):
    return book["asks"][0][0] if book["asks"] else None
