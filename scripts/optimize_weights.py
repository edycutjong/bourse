#!/usr/bin/env python3
"""
Bourse weights optimizer script.
Performs grid search over the 4-plane z-score weights to maximize backtest Sharpe ratio.
"""
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bourse import run_backtest
import bourse.engine


STEPS = [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    bt_fix = os.path.join(root, "data", "fixtures", "backtest_cake.json")
    if not os.path.exists(bt_fix):
        sys.exit("No backtest fixture found. Run scripts/seed.py first.")
        
    with open(bt_fix) as f:
        history = json.load(f)
        
    print("Running Bourse weights optimizer...")
    print("Initial weights:", bourse.engine.W)
    
    initial_res = run_backtest(history, token="CAKE")
    print(f"Initial Sharpe Ratio: {initial_res['sharpe']}")
    
    best_sharpe = -999.0
    best_w = None
    
    # Grid search step
    steps = STEPS
    
    for w_narrative in steps:
        for w_social in steps:
            for w_whale in steps:
                for w_funding in steps:
                    # Update engine weights
                    w = {
                        "narrative": w_narrative,
                        "social": w_social,
                        "whale_flow": w_whale,
                        "funding_oi": w_funding
                    }
                    bourse.engine.W.update(w)
                    try:
                        res = run_backtest(history, token="CAKE")
                        sharpe = res["sharpe"]
                        if sharpe > best_sharpe:
                            best_sharpe = sharpe
                            best_w = w.copy()
                    except Exception:
                        pass
                        
    print("\nOptimization completed successfully!")
    print("Optimal weights found:")
    for k, val in best_w.items():
        print(f"  w_{k}: {val:.1f}")
    print(f"Optimal Sharpe Ratio: {best_sharpe:.2f}")


if __name__ == "__main__":
    main()
