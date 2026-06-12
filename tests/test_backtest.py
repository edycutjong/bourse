"""Backtest harness tests: schema, believable ranges, determinism, guards."""
import json
import os
import subprocess
import sys
import pytest
from bourse import run_backtest

ROOT = os.path.join(os.path.dirname(__file__), "..")
FIX = os.path.join(ROOT, "data", "fixtures", "backtest_cake.json")


def _load():
    if not os.path.exists(FIX):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "seed.py")], check=True)
    with open(FIX) as f:
        return json.load(f)


def test_metrics_schema_and_ranges():
    m = run_backtest(_load(), token="CAKE")
    for k in ("sharpe", "max_dd", "win_rate", "n_trades", "n_active",
              "final_return", "equity_curve"):
        assert k in m
    assert 0.0 < m["sharpe"] < 6.0          # believable, not a noise-free ~11 blowup
    assert 0.0 <= m["max_dd"] <= 0.5
    assert 0.4 <= m["win_rate"] <= 0.8
    assert m["n_trades"] > 0
    assert len(m["equity_curve"]) > 0


def test_deterministic():
    h = _load()
    assert run_backtest(h, token="CAKE") == run_backtest(h, token="CAKE")


def test_profitable_on_demo_cycle():
    assert run_backtest(_load(), token="CAKE")["final_return"] > 0


def test_short_history_raises():
    tiny = {k: [1.0, 2.0, 3.0] for k in
            ("price", "narrative_heat", "social_volume", "whale_net_flow",
             "funding_rate", "open_interest", "fear_greed")}
    with pytest.raises(ValueError):
        run_backtest(tiny)


def test_length_mismatch_raises():
    h = dict(_load())
    h["price"] = h["price"][:-1]            # one short -> inconsistent series
    with pytest.raises(ValueError):
        run_backtest(h, token="CAKE")


def test_flat_market_no_trades():
    n = 20
    flat = {k: [1.0] * n for k in
            ("narrative_heat", "social_volume", "whale_net_flow",
             "funding_rate", "open_interest")}
    flat["price"] = [100.0] * n
    flat["fear_greed"] = [50.0] * n
    m = run_backtest(flat, token="FLAT")
    assert m["n_trades"] == 0
    assert m["sharpe"] == 0.0
    assert m["max_dd"] == 0.0
