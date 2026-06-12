#!/usr/bin/env python3
"""Reproducible benchmark: signal-compute latency p50/p95 over N runs."""
import json
import os
import sys
import time
import argparse
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bourse import compute, Planes

FIX = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "demo.json")


def main(n: int):
    d = json.load(open(FIX))["CAKE"]
    ts = []
    for _ in range(n):
        t = time.perf_counter()
        compute("CAKE", Planes(**d))
        ts.append((time.perf_counter() - t) * 1e3)
    ts.sort()
    p = lambda q: ts[min(len(ts) - 1, int(q * len(ts)))]
    print(f"compute() over {n} runs (ms): "
          f"p50={p(.5):.3f} p95={p(.95):.3f} mean={sum(ts)/len(ts):.3f} "
          f"min={ts[0]:.3f} max={ts[-1]:.3f}")
    # TODO: also emit backtest Sharpe/maxDD/winRate once backtest.py lands


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", type=int, default=1000)
    main(ap.parse_args().n)
