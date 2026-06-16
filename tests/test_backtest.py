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


def test_equity_curve_length_matches_steps():
    h = _load()
    m = run_backtest(h, token="CAKE")
    expected = len(h["price"]) - 1 - (5 - 1)        # n - 1 - (window - 1)
    assert len(m["equity_curve"]) == expected


def test_final_return_consistent_with_equity_curve():
    m = run_backtest(_load(), token="CAKE")
    assert m["final_return"] == pytest.approx(m["equity_curve"][-1] - 1.0, abs=1e-4)


def test_metric_bounds():
    m = run_backtest(_load(), token="CAKE")
    assert 0.0 <= m["win_rate"] <= 1.0
    assert 0.0 <= m["max_dd"] <= 1.0
    assert m["n_active"] >= m["n_trades"]


def test_higher_fees_reduce_return():
    h = _load()
    lo = run_backtest(h, token="CAKE", fee_bps=1.0)["final_return"]
    hi = run_backtest(h, token="CAKE", fee_bps=200.0)["final_return"]
    assert hi < lo


@pytest.mark.parametrize("ppy", [252, 365])
def test_periods_per_year_scales_sharpe(ppy):
    import numpy as np
    base = run_backtest(_load(), token="CAKE", periods_per_year=365)["sharpe"]
    scaled = run_backtest(_load(), token="CAKE", periods_per_year=ppy)["sharpe"]
    # metrics are rounded to 2 decimals, so allow a rounding-sized tolerance
    assert scaled == pytest.approx(base * np.sqrt(ppy / 365), abs=0.01)


@pytest.mark.parametrize("window", [3, 5, 8])
def test_various_windows_run(window):
    m = run_backtest(_load(), token="CAKE", window=window)
    assert len(m["equity_curve"]) > 0


def test_window_too_large_raises():
    with pytest.raises(ValueError):
        run_backtest(_load(), token="CAKE", window=10_000)


def test_coverage_passthrough_does_not_crash():
    h = dict(_load())
    h["coverage"] = 0.5
    assert run_backtest(h, token="CAKE")["n_active"] >= 0
