"""Kalshi venue: CFTC-regulated US exchange. Public data needs no auth.

Kalshi quirks the rest of the code shouldn't know about:
- Markets are reached via /events (the flat /markets listing is dominated by
  auto-generated multivariate parlays, which we exclude).
- Order books contain BIDS only: a YES ask is derived as 1 - best NO bid.
- Prices arrive as dollar strings ("0.9400"); sizes are fractional contracts.
- Taker fees: ceil_to_cent(0.07 * price * (1-price)) per contract.
- "token_id" here is "TICKER:yes" / "TICKER:no".
"""
import base64
import math
import time
from datetime import datetime, timezone

from ..http import get_json

BASE = "https://api.elections.kalshi.com/trade-api/v2"
TAKER_FEE_COEF = 0.07


def load_private_key_env():
    """Read the RSA key from the environment.

    Sources, in order: KALSHI_PRIVATE_KEY (optionally continued in
    KALSHI_PRIVATE_KEY_2, _3, ... for env-var UIs with a length limit —
    chunks are concatenated in numeric order; _1 may start the chain
    instead), or a file at KALSHI_PRIVATE_KEY_PATH.

    Tolerates the ways env-var UIs mangle values: flattened/escaped
    newlines, surrounding quotes, or the whole file base64-encoded
    (including base64 split across the numbered chunks).
    Returns the PEM string or None.
    """
    import os

    def clean(s):
        return (s or "").strip().strip("'\"")

    parts = [clean(os.environ.get("KALSHI_PRIVATE_KEY"))
             or clean(os.environ.get("KALSHI_PRIVATE_KEY_1"))]
    i = 2
    while True:
        nxt = clean(os.environ.get(f"KALSHI_PRIVATE_KEY_{i}"))
        if not nxt:
            break
        parts.append(nxt)
        i += 1
    pem = "".join(parts)

    path = os.environ.get("KALSHI_PRIVATE_KEY_PATH")
    if not pem and path:
        with open(path) as f:
            pem = f.read()
    if not pem:
        return None
    if "\\n" in pem and "-----" in pem:
        pem = pem.replace("\\n", "\n")
    if "-----" not in pem:
        try:
            decoded = base64.b64decode(pem).decode()
            if "-----" in decoded:
                pem = decoded
        except Exception:
            pass
    if "-----" not in pem:
        return None
    return _rewrap_pem(pem)


def diagnose_pem(pem):
    """Structural diagnostics for an unparseable PEM. Returns ONLY safe
    metadata (lengths, character classes) — never key material."""
    import re

    info = {}
    m = re.search(r"-----BEGIN ([^-]+)-----(.*?)-----END ([^-]+)-----", pem or "", re.S)
    if not m:
        info["envelope"] = "no BEGIN/END envelope found"
        info["total_chars"] = len(pem or "")
        return info
    body = re.sub(r"\s+", "", m.group(2))
    info["label"] = m.group(1).strip()
    info["body_chars"] = len(body)
    info["body_len_mod4"] = len(body) % 4
    info["reference"] = "a 2048-bit PKCS#1 RSA key body is ~1592-1624 chars"
    bad = sorted(set(re.findall(r"[^A-Za-z0-9+/=]", body)))
    info["non_base64_chars"] = bad
    try:
        raw = base64.b64decode(body, validate=True)
        info["base64_decodes"] = True
        info["der_bytes"] = len(raw)
        info["der_starts_with_sequence"] = raw[:1] == b"\x30"
    except Exception as e:
        info["base64_decodes"] = False
        info["decode_error"] = type(e).__name__
    return info


def _rewrap_pem(pem):
    """Rebuild PEM structure when newlines were flattened to spaces.

    "-----BEGIN RSA PRIVATE KEY----- MIIEpA... -----END RSA PRIVATE KEY-----"
    becomes a properly line-broken PEM. Already-valid PEMs pass through
    reconstructed identically.
    """
    import re

    m = re.search(r"-----BEGIN ([^-]+)-----(.*?)-----END ([^-]+)-----", pem, re.S)
    if not m:
        return pem
    label, body = m.group(1).strip(), m.group(2)
    body = re.sub(r"\s+", "", body)
    lines = [body[i:i + 64] for i in range(0, len(body), 64)]
    return f"-----BEGIN {label}-----\n" + "\n".join(lines) + f"\n-----END {label}-----\n"


def auth_headers(key_id, private_key_pem, method, path):
    """Signed headers for authenticated calls (see docs.kalshi.com api_keys).

    Signs "<ts_ms><METHOD><path-without-query>" with RSA-PSS/SHA-256.
    `path` must include the /trade-api/v2 prefix.
    """
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding

    ts = str(int(time.time() * 1000))
    key = serialization.load_pem_private_key(private_key_pem.encode(), password=None)
    sig = key.sign(
        f"{ts}{method.upper()}{path}".encode(),
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.DIGEST_LENGTH),
        hashes.SHA256(),
    )
    return {
        "KALSHI-ACCESS-KEY": key_id,
        "KALSHI-ACCESS-TIMESTAMP": ts,
        "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode(),
    }


def _f(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_time(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def taker_fee(price, qty):
    """Kalshi fee schedule: fees round up to the next cent per order."""
    fee = TAKER_FEE_COEF * price * (1.0 - price) * qty
    return math.ceil(fee * 100) / 100.0


def normalize(m, event_title=""):
    yes_bid = _f(m.get("yes_bid_dollars"), None)
    yes_ask = _f(m.get("yes_ask_dollars"), None)
    if yes_bid and yes_ask:
        yes_price = round((yes_bid + yes_ask) / 2, 4)
        spread = round(yes_ask - yes_bid, 4)
    else:
        yes_price = _f(m.get("last_price_dollars"))
        spread = 1.0
    result = m.get("result") or ""
    closed = m.get("status") in ("settled", "finalized", "closed")
    if result == "yes":
        prices = [1.0, 0.0]
    elif result == "no":
        prices = [0.0, 1.0]
    else:
        prices = [yes_price, round(1.0 - yes_price, 4)]
    title = m.get("title", "")
    sub = m.get("yes_sub_title") or ""
    question = f"{event_title or title}" + (f" — {sub}" if sub and sub not in title else "")
    ticker = m["ticker"]
    return {
        "id": ticker,
        "question": question,
        "slug": ticker.lower(),
        "event_ticker": m.get("event_ticker", ""),
        "end_date": _parse_time(m.get("expected_expiration_time") or m.get("close_time")),
        "open_time": _parse_time(m.get("open_time")),
        # open interest (contracts, ~$1 notional each) is the best available
        # depth proxy — Kalshi's liquidity_dollars field is often 0.
        "liquidity": _f(m.get("open_interest_fp")),
        "volume_24h": _f(m.get("volume_24h_fp")),
        "volume_total": _f(m.get("volume_fp")),
        "outcomes": ["Yes", "No"],
        "prices": prices,
        "token_ids": [f"{ticker}:yes", f"{ticker}:no"],
        "spread": spread,
        "best_bid": yes_bid,
        "best_ask": yes_ask,
        "min_order_size": 1.0,
        "tick": 0.01,
        "active": m.get("status") == "active",
        "closed": closed,
        "order_book": m.get("market_type") == "binary",
        "result": result,
    }


def _is_junk(market, event_ticker=""):
    et = market.get("event_ticker") or event_ticker
    return et.startswith("KXMV") or market.get("mve_collection_ticker") or \
        market.get("is_provisional")


class KalshiVenue:
    name = "kalshi"

    def open_markets(self, max_markets=300, min_close_hours=6, max_close_days=30,
                     max_pages=4, **_):
        """Open markets closing within the given window, busiest first.

        The close-time window is essential: without it the listing is
        dominated by same-day in-play markets and far-future longshots.
        """
        now = int(time.time())
        out, cursor = [], None
        for _ in range(max_pages):
            params = {
                "limit": 1000,
                "status": "open",
                "min_close_ts": now + int(min_close_hours * 3600),
                "max_close_ts": now + int(max_close_days * 86400),
            }
            if cursor:
                params["cursor"] = cursor
            data = get_json(f"{BASE}/markets", params=params)
            for raw in data.get("markets", []):
                if _is_junk(raw):
                    continue
                m = normalize(raw)
                if m["order_book"] and m["active"]:
                    out.append(m)
            cursor = data.get("cursor")
            if not cursor:
                break
        out.sort(key=lambda m: m["volume_24h"], reverse=True)
        return out[:max_markets]

    def market(self, market_id):
        data = get_json(f"{BASE}/markets/{market_id}")
        return normalize(data.get("market", data))

    def book(self, token_id):
        ticker, side = token_id.rsplit(":", 1)
        data = get_json(f"{BASE}/markets/{ticker}/orderbook")
        raw = data.get("orderbook_fp") or {}
        yes = [(_f(p), _f(c)) for p, c in (raw.get("yes_dollars") or [])]
        no = [(_f(p), _f(c)) for p, c in (raw.get("no_dollars") or [])]
        own, other = (yes, no) if side == "yes" else (no, yes)
        bids = sorted(own, key=lambda l: l[0], reverse=True)
        asks = sorted(((round(1.0 - p, 4), c) for p, c in other), key=lambda l: l[0])
        return {"bids": bids, "asks": asks}

    def taker_fee(self, price, qty):
        return taker_fee(price, qty)

    # ---- history for backtesting ----
    def candles(self, market, period_minutes=60):
        """Hourly (bid, ask) closes: [(ts, yes_bid, yes_ask), ...]."""
        series = (market["event_ticker"] or market["id"]).split("-")[0]
        end = market["end_date"] or datetime.now(timezone.utc)
        end_ts = int(end.timestamp()) + 86400
        start_ts = end_ts - 32 * 86400
        if market["open_time"]:
            start_ts = max(start_ts, int(market["open_time"].timestamp()) - 3600)
        data = get_json(
            f"{BASE}/series/{series}/markets/{market['id']}/candlesticks",
            params={"start_ts": start_ts, "end_ts": min(end_ts, int(time.time())),
                    "period_interval": period_minutes},
        )
        out = []
        for c in data.get("candlesticks", []):
            bid = _f((c.get("yes_bid") or {}).get("close_dollars"), None)
            ask = _f((c.get("yes_ask") or {}).get("close_dollars"), None)
            if bid is not None and ask is not None:
                out.append((c["end_period_ts"], bid, ask))
        return out

    def settled_markets(self, n, min_volume=5000, days_back=30, max_series=40):
        """Recently settled, clean-resolution markets from actively-traded series.

        The raw settled feed is ~99.9% auto-generated parlays (thousands
        settle per hour), so instead we take the busiest currently-active
        series and pull each one's settled history.
        """
        open_ms = self.open_markets(max_markets=1500, min_close_hours=0,
                                    max_close_days=45, max_pages=2)
        series, seen = [], set()
        for m in open_ms:  # already sorted busiest-first
            s = (m["event_ticker"] or m["id"]).split("-")[0]
            if s not in seen:
                seen.add(s)
                series.append(s)
            if len(series) >= max_series:
                break

        # Cap each series' contribution so one prolific family (e.g. golf
        # finish props, hundreds settled per week) can't dominate the sample.
        per_series_cap = max(10, (n * 2) // max(len(series), 1))
        out = []
        now = int(time.time())
        for s in series:
            got = []
            data = get_json(f"{BASE}/markets",
                            params={"limit": 1000, "status": "settled",
                                    "series_ticker": s,
                                    "min_close_ts": now - days_back * 86400})
            for raw in data.get("markets", []):
                if _is_junk(raw):
                    continue
                m = normalize(raw)
                if m["result"] in ("yes", "no") and m["volume_total"] >= min_volume:
                    got.append(m)
            got.sort(key=lambda m: m["volume_total"], reverse=True)
            out.extend(got[:per_series_cap])
        epoch = datetime.min.replace(tzinfo=timezone.utc)
        out.sort(key=lambda m: m["end_date"] or epoch, reverse=True)
        return out[:n]
