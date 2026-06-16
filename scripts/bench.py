#!/usr/bin/env python3
"""Reproducible benchmark: signal-compute latency p50/p95 + backtest quality."""
import json
import os
import sys
import time
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bourse import compute, Planes, run_backtest

ROOT = os.path.join(os.path.dirname(__file__), "..")
FIX = os.path.join(ROOT, "data", "fixtures", "demo.json")
BT_FIX = os.path.join(ROOT, "data", "fixtures", "backtest_cake.json")


def main(n: int):
    d = json.load(open(FIX))["CAKE"]
    ts = []
    for _ in range(n):
        t = time.perf_counter()
        compute("CAKE", Planes(**d))
        ts.append((time.perf_counter() - t) * 1e3)
    ts.sort()

    def pct(q):
        return ts[min(len(ts) - 1, int(q * len(ts)))]

    print(f"compute() over {n} runs (ms): "
          f"p50={pct(.5):.3f} p95={pct(.95):.3f} mean={sum(ts)/len(ts):.3f} "
          f"min={ts[0]:.3f} max={ts[-1]:.3f}")

    if os.path.exists(BT_FIX):
        m = run_backtest(json.load(open(BT_FIX)), token="CAKE")
        print(f"backtest CAKE ({len(m['equity_curve'])} steps): "
              f"sharpe={m['sharpe']} maxDD={m['max_dd']*100:.1f}% "
              f"win={m['win_rate']*100:.1f}% return={m['final_return']*100:+.1f}%")
    else:
        print("backtest: no fixture — run `python scripts/seed.py`")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=1000)
    main(ap.parse_args().n)
