#!/usr/bin/env python3
"""
Bourse WALK-FORWARD weight optimizer.

Honest replacement for the old single-fixture grid search. The old script grid-searched
1,296 weight combos on one CAKE fixture and reported the best *in-sample* Sharpe — that is
overfitting: with that many tries a high Sharpe appears by luck. This version fits the
weights on a train window and scores them OUT-OF-SAMPLE on the next, unseen window, across
every token fixture, and prints both numbers so the gap is visible.

  python scripts/seed.py             # writes data/fixtures/backtest_<token>.json
  python scripts/optimize_weights.py # -> per-token + pooled out-of-sample Sharpe
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bourse.walkforward import optimize_multi


def load_histories(root: str) -> dict:
    histories = {}
    pattern = os.path.join(root, "data", "fixtures", "backtest_*.json")
    for path in sorted(glob.glob(pattern)):
        token = os.path.basename(path)[len("backtest_"):-len(".json")].upper()
        with open(path) as f:
            histories[token] = json.load(f)
    return histories


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    histories = load_histories(root)
    if not histories:
        sys.exit("No backtest fixtures found. Run: python scripts/seed.py")

    print("Running Bourse WALK-FORWARD optimizer (out-of-sample)...")
    print(f"Tokens: {', '.join(histories)}")
    print("Method: grid-search weights on each train window, score on the NEXT unseen window.\n")

    res = optimize_multi(histories)

    print(f"{'token':<8}{'in-sample':>12}{'out-of-sample':>16}{'folds':>8}")
    print("-" * 44)
    for token, r in res["per_token"].items():
        print(f"{token:<8}{r['in_sample_sharpe']:>12.2f}{r['oos_sharpe']:>16.2f}{r['n_folds']:>8}")
    print("-" * 44)

    print(f"\nMean in-sample Sharpe  (overfit: grid search on full data) : {res['mean_in_sample_sharpe']:.2f}")
    print(f"Pooled OUT-OF-SAMPLE Sharpe (honest: unseen windows only)  : {res['pooled_oos_sharpe']:.2f}")
    print(f"  over {res['oos_n']} out-of-sample steps across {len(res['tokens'])} tokens")
    print("\nThe out-of-sample number is the one a trader or agent should price on.")


if __name__ == "__main__":
    main()
