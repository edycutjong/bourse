#!/usr/bin/env python3
"""
Run the Bourse backtest over a token's history fixture and print metrics +
a compact ASCII equity curve. Deterministic — same fixture in, same numbers out.

  python scripts/seed.py          # writes data/fixtures/backtest_cake.json
  python scripts/backtest.py      # -> sharpe / max_dd / win_rate / equity curve
  python scripts/backtest.py --json   # machine-readable metrics
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bourse import run_backtest

DEFAULT_FIX = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "backtest_cake.json")


def _spark(curve):
    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(curve), max(curve)
    rng = (hi - lo) or 1.0
    return "".join(blocks[min(7, int((x - lo) / rng * 7))] for x in curve)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", default=DEFAULT_FIX)
    ap.add_argument("--token", default="CAKE")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    if not os.path.exists(a.fixture):
        sys.exit(f"no fixture at {a.fixture} -- run: python scripts/seed.py")
    with open(a.fixture) as f:
        history = json.load(f)
    m = run_backtest(history, token=a.token)
    if a.json:
        print(json.dumps(m, indent=2))
        return
    print(f"Bourse backtest -- {a.token} ({len(history['price'])} days)\n")
    print(f"  Sharpe (ann.) : {m['sharpe']}")
    print(f"  max drawdown  : {m['max_dd'] * 100:.1f}%")
    print(f"  win rate      : {m['win_rate'] * 100:.1f}%")
    print(f"  trades        : {m['n_trades']}  (active steps {m['n_active']})")
    print(f"  total return  : {m['final_return'] * 100:+.1f}%")
    print(f"  equity        : {_spark(m['equity_curve'])}")


if __name__ == "__main__":
    main()
