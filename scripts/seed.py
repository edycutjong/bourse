#!/usr/bin/env python3
"""
Deterministic demo fixtures (SEED_DATA.md). Writes data/fixtures/demo.json with:
  - CAKE  : engineered "smoking gun" -> SHORT/FADE, distribution
  - XYZL  : inverse -> LONG, accumulation
  - ABCN  : neutral -> no-trade
Identical output every run. `--live` is handled by ingest.from_mcp, not here.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bourse import compute, Planes

FIX = {
    # crowd euphoric (narrative+social rising), whales leaving, funding crowded-long, greed
    "CAKE": {
        "narrative_heat": [1, 1, 2, 4, 9],
        "social_volume":  [2, 2, 3, 6, 11],
        "whale_net_flow": [5, 4, 2, -3, -9],
        "funding_rate":   [0.01, 0.01, 0.03, 0.06, 0.12],
        "open_interest":  [100, 102, 110, 125, 140],
        "fear_greed":     78,
        "coverage":       1.0,
    },
    # crowd fearful, whales accumulating -> LONG
    "XYZL": {
        "narrative_heat": [9, 7, 5, 3, 1],
        "social_volume":  [11, 8, 5, 3, 2],
        "whale_net_flow": [-4, -2, 1, 5, 10],
        "funding_rate":   [0.05, 0.02, -0.01, -0.03, -0.05],
        "open_interest":  [140, 130, 120, 110, 105],
        "fear_greed":     18,
        "coverage":       1.0,
    },
    # everything flat -> no trade
    "ABCN": {
        "narrative_heat": [5, 5, 5, 5, 5],
        "social_volume":  [5, 5, 5, 5, 5],
        "whale_net_flow": [0, 1, 0, -1, 0],
        "funding_rate":   [0.01, 0.01, 0.01, 0.01, 0.01],
        "open_interest":  [100, 100, 101, 100, 100],
        "fear_greed":     50,
        "coverage":       1.0,
    },
}


# Synthetic-but-realistic backtest fixture. Seeded RNG => byte-for-byte reproducible.
# 5x12d phases: markup1 -> distribution1 -> chop -> recovery/markup2 -> distribution2,
# with crypto-like daily noise so the Sharpe is believable (not a noise-free ~11).
# This is an ILLUSTRATIVE single-asset cycle; real depth comes from CMC history once
# scripts/probe_cmc_history.py confirms which planes expose REST history (BUILD_PLAN Day 1).
BT_SEED = 9
BT_PRICE_NOISE = 0.025


def _seg(a, b, n):
    return np.linspace(a, b, n)


def backtest_history():
    """CAKE pump/distribution/recovery cycle Bourse trades: SHORT the euphoric tops
    (price falling) and LONG the capitulation bottom (price recovering). Deterministic
    via fixed seed -> the demo's Sharpe/maxDD/winRate reproduce exactly."""
    rng = np.random.default_rng(BT_SEED)
    trend     = np.concatenate([_seg(100,124,12), _seg(125,101,12), _seg(101,104,12), _seg(102,123,12), _seg(124,107,12)])
    narrative = np.concatenate([_seg(1,3,12),     _seg(4,9,12),     _seg(5,5,12),     _seg(3,2,12),     _seg(4,9,12)])
    social    = np.concatenate([_seg(2,4,12),     _seg(6,11,12),    _seg(6,6,12),     _seg(4,3,12),     _seg(6,11,12)])
    whale     = np.concatenate([_seg(4,2,12),     _seg(-1,-8,12),   _seg(0,0,12),     _seg(2,9,12),     _seg(-1,-8,12)])
    funding   = np.concatenate([_seg(0.01,0.03,12), _seg(0.04,0.11,12), _seg(0.01,0.01,12), _seg(-0.01,-0.04,12), _seg(0.04,0.11,12)])
    oi        = np.concatenate([_seg(100,118,12), _seg(122,142,12), _seg(120,120,12), _seg(118,138,12), _seg(122,140,12)])
    fg        = np.concatenate([_seg(45,62,12),   _seg(74,84,12),   _seg(50,50,12),   _seg(32,20,12),   _seg(74,84,12)])
    n = trend.size

    def noisy(a, rel):
        return [round(float(x), 4) for x in a + rng.normal(0, rel * (np.abs(a).mean() or 1), n)]

    price = [round(float(x), 4) for x in trend * (1 + rng.normal(0, BT_PRICE_NOISE, n))]
    return {
        "price":          price,
        "narrative_heat": noisy(narrative, 0.18),
        "social_volume":  noisy(social, 0.18),
        "whale_net_flow": noisy(whale, 0.25),
        "funding_rate":   noisy(funding, 0.20),
        "open_interest":  noisy(oi, 0.10),
        "fear_greed":     [round(float(x), 4) for x in np.clip(fg + rng.normal(0, 4, n), 0, 100)],
        "coverage":       1.0,
    }


def main():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    out = os.path.join(root, "data", "fixtures", "demo.json")
    with open(out, "w") as f:
        json.dump(FIX, f, indent=2)
    print(f"wrote {out} ({len(FIX)} tokens)")

    # backtest history (consumed by bourse.run_backtest + scripts/backtest.py)
    bt_out = os.path.join(root, "data", "fixtures", "backtest_cake.json")
    bt = backtest_history()
    with open(bt_out, "w") as f:
        json.dump(bt, f, indent=2)
    print(f"wrote {bt_out} ({len(bt['price'])} days)")

    # Render the static landing board from the same fixtures via the engine,
    # so landing/index.html's fetch('signals.json') resolves (matches the footer).
    board = []
    for token, planes in FIX.items():
        sig = compute(token, Planes(**planes))
        board.append({
            "token": sig.token,
            "divergence": sig.divergence,
            "regime": sig.regime,
            "direction": sig.direction,
            "confidence": sig.confidence,
        })
    board.sort(key=lambda r: abs(r["divergence"]), reverse=True)
    board_out = os.path.join(root, "landing", "signals.json")
    with open(board_out, "w") as f:
        json.dump(board, f, indent=2)
    print(f"wrote {board_out} ({len(board)} rows)")


if __name__ == "__main__":
    main()
