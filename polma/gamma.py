"""Read-only client for Polymarket's public Gamma API (market metadata)."""
import json
from datetime import datetime, timezone

import requests

GAMMA_URL = "https://gamma-api.polymarket.com"
TIMEOUT = 20


def _parse_json_field(raw):
    """Gamma encodes list fields as JSON strings, e.g. '["Yes", "No"]'."""
    if raw is None:
        return []
    if isinstance(raw, list):
        return raw
    try:
        return json.loads(raw)
    except (ValueError, TypeError):
        return []


def _parse_end_date(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def normalize(m):
    """Flatten a raw Gamma market record into the fields the engine uses."""
    outcomes = _parse_json_field(m.get("outcomes"))
    prices = [float(p) for p in _parse_json_field(m.get("outcomePrices"))]
    token_ids = _parse_json_field(m.get("clobTokenIds"))
    return {
        "id": str(m.get("id")),
        "question": m.get("question", ""),
        "slug": m.get("slug", ""),
        "condition_id": m.get("conditionId", ""),
        "end_date": _parse_end_date(m.get("endDate")),
        "liquidity": float(m.get("liquidityNum") or m.get("liquidity") or 0),
        "volume_24h": float(m.get("volume24hr") or 0),
        "outcomes": outcomes,
        "prices": prices,
        "token_ids": token_ids,
        "spread": float(m.get("spread") or 1.0),
        "best_bid": float(m["bestBid"]) if m.get("bestBid") is not None else None,
        "best_ask": float(m["bestAsk"]) if m.get("bestAsk") is not None else None,
        "min_order_size": float(m.get("orderMinSize") or 0),
        "tick": float(m.get("orderPriceMinTickSize") or 0.01),
        "active": bool(m.get("active")),
        "closed": bool(m.get("closed")),
        "order_book": bool(m.get("enableOrderBook")),
    }


def fetch_open_markets(max_markets=300):
    """Open, order-book-enabled markets, highest 24h volume first."""
    out = []
    offset = 0
    while len(out) < max_markets:
        batch = min(100, max_markets - len(out))
        resp = requests.get(
            f"{GAMMA_URL}/markets",
            params={
                "closed": "false",
                "active": "true",
                "limit": batch,
                "offset": offset,
                "order": "volume24hr",
                "ascending": "false",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        rows = resp.json()
        if not rows:
            break
        for raw in rows:
            m = normalize(raw)
            if m["order_book"] and m["active"] and not m["closed"] and m["token_ids"]:
                out.append(m)
        offset += batch
    return out


def fetch_market(market_id):
    """Fetch a single market by Gamma id (used to settle held positions)."""
    resp = requests.get(f"{GAMMA_URL}/markets/{market_id}", timeout=TIMEOUT)
    resp.raise_for_status()
    return normalize(resp.json())


def hours_to_resolution(market, now=None):
    now = now or datetime.now(timezone.utc)
    if not market["end_date"]:
        return None
    return (market["end_date"] - now).total_seconds() / 3600.0
