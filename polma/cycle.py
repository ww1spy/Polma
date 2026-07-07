"""Run one trading cycle: python3 -m polma.cycle"""
import json

from .engine import run_cycle


def main():
    summary = run_cycle()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
