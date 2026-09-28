"""Resting-limit-order (maker) execution — PAPER ONLY, Kalshi only.

Why: every live/paper book so far crossed the spread and paid taker fees,
and in every book the win rate landed below its break-even win rate
(journal/scorecard.md, 2026-09-28). On a favorite with ~5c of upside, the
half-spread + taker fee is a large slice of the edge. A resting bid one
tick inside the spread earns the spread instead of paying it, and on
fee_type "quadratic" series makers pay no fee at all.

Fill model (conservative, exact to the public tape): an order resting at
price p is filled ONLY by volume that printed THROUGH p after we placed it
(YES bid: prints at yes_price <= p - 1 tick; NO bid: prints at
yes_price >= 1 - p + 1 tick). A print through our level means every bid at
our price — including ours, wherever it sat in the queue — was consumed.
Prints exactly at p are ignored (we can't know our queue position), so the
paper book understates fills rather than overstating them. Adverse
selection is fully captured: the fills we get are the ones where price
moved toward us.

State: resting orders live in state["orders"] (market_id -> order), with
their notional reserved from cash so exposure/equity accounting stays
honest. Orders expire at the entry cutoff (min hours before resolution) or
after ORDER_TTL_HOURS, whichever is first.
"""
import math
import time
from datetime import datetime, timezone

from . import journal, portfolio

TICK = 0.01
ORDER_TTL_HOURS = 24


def _series(market_id_or_event):
    return str(market_id_or_event).split("-")[0]


def place(state, market, idx, strat, notional, rules, venue, actions):
    """Rest a bid for outcome `idx`. Returns True if an order was placed."""
    book = venue.book(market["token_ids"][idx])
    if not book["bids"] or not book["asks"]:
        return False  # one-sided book: no honest reference price
    bid, ask = book["bids"][0][0], book["asks"][0][0]
    price = round(bid + TICK, 2) if bid + TICK < ask - 1e-9 else round(bid, 2)
    if not (strat["min_price"] - TICK <= price <= strat["max_price"]) or price <= 0:
        return False
    qty = math.floor(notional / price)
    if qty < 1:
        return False
    now = time.time()
    end_ts = market["end_date"].timestamp() if market["end_date"] else now + 86400
    cutoff = end_ts - rules["universe"]["min_hours_to_resolution"] * 3600
    expires = min(cutoff, now + ORDER_TTL_HOURS * 3600)
    if expires <= now:
        return False
    reserved = round(qty * price, 2)
    state.setdefault("orders", {})[market["id"]] = {
        "market_id": market["id"], "event_ticker": market.get("event_ticker") or "",
        "question": market["question"], "slug": market["slug"],
        "token_ids": market["token_ids"], "outcomes": market["outcomes"],
        "outcome_idx": idx, "price": price, "qty": qty, "reserved": reserved,
        "placed_ts": now, "expires_ts": expires, "strategy": strat["name"],
        "rules_version": rules.get("version", "?"),
        "end_date": market["end_date"].isoformat() if market["end_date"] else None,
        "book_at_place": {"bid": bid, "ask": ask},
    }
    state["cash"] -= reserved
    journal.log_event(
        "ORDER_PLACE", venue=venue.name, profile=state.get("profile"),
        mode=state.get("mode", "paper"), market_id=market["id"],
        question=market["question"], outcome=market["outcomes"][idx],
        price=price, qty=qty, bid=bid, ask=ask, strategy=strat["name"],
        expires=datetime.fromtimestamp(expires, timezone.utc).isoformat(timespec="seconds"),
        rules_version=rules.get("version", "?"),
    )
    actions.append(f"ORDER {market['question'][:55]} [{market['outcomes'][idx]}] "
                   f"{qty} @ {price:.2f} (bid {bid:.2f} / ask {ask:.2f})")
    return True


def _through_volume(order, prints):
    p = order["price"]
    if order["outcome_idx"] == 0:
        return sum(c for ts, yp, c in prints
                   if ts >= order["placed_ts"] and yp is not None and yp <= p - TICK + 1e-9)
    thresh = 1.0 - p + TICK
    return sum(c for ts, yp, c in prints
               if ts >= order["placed_ts"] and yp is not None and yp >= thresh - 1e-9)


def sweep(state, venue, actions):
    """Fill or expire every resting order from the public trade tape."""
    now = time.time()
    for mid in list(state.get("orders") or {}):
        order = state["orders"][mid]
        try:
            prints = venue.trades(mid, order["placed_ts"])
        except Exception as e:
            actions.append(f"WARN no trades for {mid}: {e}")
            continue
        filled = min(order["qty"], math.floor(_through_volume(order, prints)))
        expired = now >= order["expires_ts"]
        if filled < 1 and not expired:
            continue
        state["orders"].pop(mid)
        state["cash"] += order["reserved"]  # release; position cost re-debits below
        if filled < 1:
            journal.log_event("ORDER_CANCEL", venue=venue.name, profile=state.get("profile"),
                              mode=state.get("mode", "paper"), market_id=mid,
                              question=order["question"], price=order["price"],
                              qty=order["qty"], reason="expired unfilled")
            actions.append(f"CANCEL (unfilled) {order['question'][:60]}")
            continue
        fee = venue.maker_fee(order["price"], filled,
                              _series(order["event_ticker"] or mid))
        notional = round(filled * order["price"] + fee, 2)
        market = {
            "id": mid, "event_ticker": order["event_ticker"],
            "question": order["question"], "slug": order["slug"],
            "token_ids": order["token_ids"], "outcomes": order["outcomes"],
        }
        fill = {"qty": filled, "avg_price": order["price"], "notional": notional,
                "fee": fee, "strategy": order["strategy"],
                "rules_version": order["rules_version"]}
        portfolio.open_position(state, market, order["outcome_idx"], fill)
        journal.log_event(
            "ENTER", venue=venue.name, profile=state.get("profile"),
            mode=state.get("mode", "paper"), market_id=mid, question=order["question"],
            outcome=order["outcomes"][order["outcome_idx"]], strategy=order["strategy"],
            qty=filled, price=order["price"], notional=notional, fee=fee,
            execution="maker", ordered_qty=order["qty"],
            rest_hours=round((now - order["placed_ts"]) / 3600, 2),
            end_date=order["end_date"], rules_version=order["rules_version"],
        )
        actions.append(f"FILL (maker) {order['question'][:55]} {filled}/{order['qty']} "
                       f"@ {order['price']:.2f} fee ${fee:.2f}")
