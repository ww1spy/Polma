"""Per-book scorecard — is anything actually working?

    python3 -m polma.scorecard

Reads journal/trades.jsonl and state/*.json and writes journal/scorecard.md:
per book, lifetime and last-30-days trade counts, win rate vs the break-even
win rate implied by the actual average win and loss, net P&L, fees paid,
and how long the book has been idle. Run weekly (ops/weekly.sh) so "no
progress" is visible in one table instead of buried in hourly one-liners.
"""
import glob
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .journal import JOURNAL_DIR

STATE_DIR = os.path.join(JOURNAL_DIR, "..", "state")


def _ts(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _book(r):
    return (r.get("venue") or "?", r.get("mode") or "paper", r.get("profile") or "base")


def _summ(events, since=None):
    ev = [e for e in events if since is None or _ts(e["ts"]) >= since]
    entries = [e for e in ev if e["type"] == "ENTER"]
    reversed_ = {(e["market_id"], e["reversed_ts"]) for e in ev if e["type"] == "SETTLE_REVERSED"}
    closes = [e for e in ev if e["type"] in ("EXIT", "SETTLE") and e.get("pnl") is not None
              and (e.get("market_id"), e["ts"]) not in reversed_]
    wins = [e["pnl"] for e in closes if e["pnl"] > 0]
    losses = [e["pnl"] for e in closes if e["pnl"] <= 0]
    fees = sum(e.get("fee") or 0 for e in ev if e["type"] in ("ENTER", "EXIT"))
    aw = sum(wins) / len(wins) if wins else 0.0
    al = sum(losses) / len(losses) if losses else 0.0
    be = abs(al) / (aw + abs(al)) if (aw + abs(al)) > 0 else None
    return {
        "entries": len(entries), "closes": len(closes),
        "win_rate": len(wins) / len(closes) if closes else None,
        "breakeven": be, "avg_win": aw, "avg_loss": al,
        "net": sum(e["pnl"] for e in closes), "fees": fees,
        "last_entry": max((e["ts"] for e in entries), default=None),
    }


def _pct(x):
    return "–" if x is None else f"{x:.0%}"


def build(now=None):
    now = now or datetime.now(timezone.utc)
    by = defaultdict(list)
    with open(os.path.join(JOURNAL_DIR, "trades.jsonl")) as f:
        for line in f:
            try:
                r = json.loads(line)
            except ValueError:
                continue
            by[_book(r)].append(r)
    states = {}
    for p in glob.glob(os.path.join(STATE_DIR, "portfolio*.json")):
        with open(p) as f:
            s = json.load(f)
        states[(s.get("venue") or "polymarket", s.get("mode") or "paper",
                s.get("profile") or "base")] = s

    lines = [f"# Scorecard — {now.date().isoformat()}", "",
             "Win% vs BE% is the whole story for favorite-buying: BE% is the win rate "
             "needed to break even given this book's actual average win and loss.", "",
             "| book | window | entries | closes | win% | BE% | avg win | avg loss | net | fees | idle | status |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for key in sorted(set(by) | set(states)):
        if key[0] == "?":
            continue
        ev = by.get(key, [])
        st = states.get(key)
        status = "–"
        if st:
            status = "HALTED" if st.get("halted") else "active"
            if st.get("epochs"):
                status += f", epoch {len(st['epochs']) + 1}"
        for label, since in (("lifetime", None), ("30d", now - timedelta(days=30))):
            s = _summ(ev, since)
            idle = (f"{(now - _ts(s['last_entry'])).days}d" if s["last_entry"] else "never")
            lines.append(
                f"| {'/'.join(key)} | {label} | {s['entries']} | {s['closes']} | "
                f"{_pct(s['win_rate'])} | {_pct(s['breakeven'])} | ${s['avg_win']:.2f} | "
                f"${s['avg_loss']:.2f} | ${s['net']:+.2f} | ${s['fees']:.2f} | "
                f"{idle if label == 'lifetime' else ''} | {status if label == 'lifetime' else ''} |")
    return "\n".join(lines) + "\n"


def main():
    text = build()
    path = os.path.join(JOURNAL_DIR, "scorecard.md")
    with open(path, "w") as f:
        f.write(text)
    print(text)


if __name__ == "__main__":
    main()
