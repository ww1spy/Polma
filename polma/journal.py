"""Trade journal: every decision that moves money gets a permanent record.

- journal/trades.jsonl   — machine-readable event log (ENTER/EXIT/SETTLE/BLOCK/HALT)
- journal/cycles.jsonl   — one summary line per trading cycle
- journal/postmortems/   — a markdown post-mortem stub for every losing trade,
                           to be filled in during rule reviews
"""
import json
import os
import re
from datetime import datetime, timezone

JOURNAL_DIR = os.path.join(os.path.dirname(__file__), "..", "journal")


def _now():
    return datetime.now(timezone.utc)


def _append(filename, record):
    os.makedirs(JOURNAL_DIR, exist_ok=True)
    record = {"ts": _now().isoformat(timespec="seconds"), **record}
    with open(os.path.join(JOURNAL_DIR, filename), "a") as f:
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def log_event(event_type, **fields):
    return _append("trades.jsonl", {"type": event_type, **fields})


def log_cycle(summary):
    return _append("cycles.jsonl", summary)


def today_realized_loss(venue=None, mode=None, profile=None):
    """Sum of today's realized losses (UTC) from the trade log, filtered to
    one venue+mode book — a live loss must not freeze the paper books and
    vice versa. Records predating the mode field count toward every book
    of their venue (conservative)."""
    path = os.path.join(JOURNAL_DIR, "trades.jsonl")
    if not os.path.exists(path):
        return 0.0
    today = _now().date().isoformat()
    loss = 0.0
    with open(path) as f:
        for line in f:
            try:
                rec = json.loads(line)
            except ValueError:
                continue
            if not (rec.get("ts", "").startswith(today) and rec.get("pnl", 0) < 0):
                continue
            if venue and rec.get("venue", venue) != venue:
                continue
            if mode and rec.get("mode") and rec["mode"] != mode:
                continue
            if rec.get("profile") != profile:
                continue
            loss += -rec["pnl"]
    return loss


def write_postmortem(pos, pnl, exit_kind, exit_price, context):
    """Create a post-mortem stub for a losing trade. Returns the file path."""
    pm_dir = os.path.join(JOURNAL_DIR, "postmortems")
    os.makedirs(pm_dir, exist_ok=True)
    date = _now().date().isoformat()
    slug = re.sub(r"[^a-z0-9]+", "-", pos["slug"].lower())[:60].strip("-") or pos["market_id"]
    path = os.path.join(pm_dir, f"{date}-{slug}.md")
    body = f"""# Loss post-mortem: {pos['question']}

- **Date closed:** {date}
- **Exit type:** {exit_kind}
- **Strategy:** {pos['strategy']} (rules v{pos['rules_version']})
- **Position:** {pos['qty']} × "{pos['outcome']}" @ {pos['entry_price']:.3f} (cost ${pos['cost']:.2f})
- **Exit price:** {exit_price:.3f}
- **PnL:** ${pnl:.2f}
- **Opened:** {pos['opened']}
- **Context at exit:** {context}

## What the rules saw at entry
<!-- Fill in during review: liquidity, spread, price, hours to resolution -->

## Why it lost
<!-- Was the thesis wrong, the timing wrong, or the rule too loose? -->

## Rule change proposed
<!-- Concrete edit to rules/rules.yaml, or "no change — acceptable variance" -->
"""
    with open(path, "w") as f:
        f.write(body)
    return os.path.relpath(path, os.path.join(JOURNAL_DIR, ".."))
