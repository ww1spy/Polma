#!/usr/bin/env bash
# Hourly operating loop — runs all five books, commits and pushes state.
# See docs/OPERATIONS.md §3. Safe to run from cron on any machine:
#   5 * * * * cd $HOME/Polma && ./ops/hourly.sh >> cron.log 2>&1
# Live cycle only places orders if KALSHI_* credentials are present AND
# POLMA_MODE=live is set below; everything else is paper and needs no keys.
set -uo pipefail
cd "$(dirname "$0")/.."

BRANCH=$(git rev-parse --abbrev-ref HEAD)
git pull --rebase origin "$BRANCH" || { echo "pull failed — aborting to avoid state divergence"; exit 1; }

run() { echo "== $* =="; "$@" || echo "!! book failed (continuing): $*"; }

run env POLMA_VENUE=kalshi python3 -m polma.cycle
run env POLMA_VENUE=polymarket python3 -m polma.cycle
run env POLMA_VENUE=kalshi POLMA_PROFILE=aggr \
    POLMA_RULES=rules/rules-aggressive.yaml \
    POLMA_LIMITS=config/risk_limits_aggressive.yaml python3 -m polma.cycle
run env POLMA_VENUE=kalshi POLMA_PROFILE=eth15 \
    POLMA_RULES=rules/rules-eth15.yaml \
    POLMA_LIMITS=config/risk_limits_aggressive.yaml python3 -m polma.cycle

# LIVE last, clean profile env (engine hard-refuses profile+live anyway).
if [ -n "${KALSHI_API_KEY_ID:-}" ]; then
    run env -u POLMA_PROFILE -u POLMA_RULES -u POLMA_LIMITS \
        POLMA_VENUE=kalshi POLMA_MODE=live python3 -m polma.cycle
else
    echo "== live cycle skipped (no KALSHI_API_KEY_ID in environment) =="
fi

git add state journal
git diff --cached --quiet && { echo "no state changes"; exit 0; }
git commit -m "Cycles: all books"
for wait in 2 4 8 16 0; do
    git push -u origin "$BRANCH" && exit 0
    [ "$wait" = 0 ] && break
    echo "push failed, retrying in ${wait}s"; sleep "$wait"
done
echo "push failed after retries — state is committed locally; next run will push"
exit 1
