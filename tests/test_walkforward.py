"""Walk-forward optimizer tests: the OOS contract (no leakage, IS >= OOS), weight-restore,
determinism, multi-token pooling, and the engine W global staying pristine."""
import json
import os
import subprocess
import sys

import pytest

import bourse.engine as engine
from bourse import run_backtest
from bourse.walkforward import (DEFAULT_STEPS, optimize_multi, use_weights,
                                walk_forward)

ROOT = os.path.join(os.path.dirname(__file__), "..")
FIXDIR = os.path.join(ROOT, "data", "fixtures")
TOKENS = ("cake", "bnb", "eth")

# Coarse grid (3^4 = 81 combos) keeps the suite fast; the optimizer logic is independent of
# grid resolution. The production default (DEFAULT_STEPS, 1,296 combos) is asserted separately.
SMALL = (0.0, 0.5, 1.0)


def _load(token):
    path = os.path.join(FIXDIR, f"backtest_{token}.json")
    if not os.path.exists(path):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "seed.py")], check=True)
    with open(path) as f:
        return json.load(f)


def _histories():
    return {t.upper(): _load(t) for t in TOKENS}


def test_use_weights_restores_global():
    before = dict(engine.W)
    with use_weights({"narrative": 0.1, "social": 0.1, "whale_flow": 0.1, "funding_oi": 0.1}):
        assert engine.W["narrative"] == 0.1
    assert engine.W == before                         # restored exactly, even the values


def test_use_weights_restores_on_exception():
    before = dict(engine.W)
    with pytest.raises(ValueError):
        with use_weights({"narrative": 0.0, "social": 0.0, "whale_flow": 0.0, "funding_oi": 0.0}):
            raise ValueError("boom")
    assert engine.W == before


def test_walk_forward_schema_and_oos_keys():
    r = walk_forward(_load("cake"), token="CAKE", steps=SMALL)
    for k in ("token", "in_sample_sharpe", "oos_sharpe", "n_folds", "oos_n", "folds"):
        assert k in r
    assert r["n_folds"] >= 1
    assert r["oos_n"] > 0
    assert len(r["folds"]) == r["n_folds"]


def test_in_sample_is_the_grid_maximum():
    """The in-sample number is the grid MAX on the full history, i.e. an inflated ceiling:
    no individual fold's train-fit weights can score higher when replayed on the whole
    history. (Out-of-sample is data-dependent and may land above or below it — which is
    exactly why the in-sample figure must never be reported as the edge.)"""
    for token in ("CAKE", "BNB", "ETH"):
        h = _load(token.lower())
        r = walk_forward(h, token=token, steps=SMALL)
        for f in r["folds"]:
            with use_weights(f["weights"]):
                full = run_backtest(h, token=token)["sharpe"]
            assert full <= r["in_sample_sharpe"] + 1e-9


def test_does_not_mutate_engine_weights():
    before = dict(engine.W)
    walk_forward(_load("cake"), token="CAKE", steps=SMALL)
    assert engine.W == before


def test_deterministic():
    a = walk_forward(_load("eth"), token="ETH", steps=SMALL)
    b = walk_forward(_load("eth"), token="ETH", steps=SMALL)
    assert a["oos_sharpe"] == b["oos_sharpe"]
    assert a["in_sample_sharpe"] == b["in_sample_sharpe"]


def test_run_backtest_unchanged_after_refactor():
    """The public backtest output must be identical to the pre-refactor contract."""
    m = run_backtest(_load("cake"), token="CAKE")
    assert m["sharpe"] == 1.74
    assert m["n_trades"] == 15
    assert len(m["equity_curve"]) == 55


def test_optimize_multi_pools_oos():
    res = optimize_multi(_histories(), steps=SMALL)
    assert set(res["tokens"]) == {"CAKE", "BNB", "ETH"}
    # pooled OOS step count is the sum of per-token OOS steps
    assert res["oos_n"] == sum(res["per_token"][t]["oos_n"] for t in res["tokens"])


def test_folds_are_forward_and_non_overlapping():
    """Each test window must start exactly where it was trained up to — no peeking ahead,
    no overlap between train and its own test."""
    r = walk_forward(_load("bnb"), token="BNB", steps=SMALL)
    for f in r["folds"]:
        tr0, tr1 = f["train"]
        te0, te1 = f["test"]
        assert tr1 == te0          # test begins at the train cutoff (forward)
        assert te0 < te1
        assert tr0 < tr1


def test_steps_constant_is_1296_combos():
    assert len(DEFAULT_STEPS) ** 4 == 1296


def test_sharpe_ratio_degenerate_cases():
    from bourse.backtest import sharpe_ratio
    assert sharpe_ratio([]) == 0.0          # empty series
    assert sharpe_ratio([0.0, 0.0]) == 0.0  # zero variance


def test_short_history_skips_undersized_folds():
    """A history barely long enough for one backtest can't be split into real folds — every
    candidate fold is too small, so walk_forward skips them and reports an empty OOS."""
    n = 7  # window(5) + 2, the minimum run_backtest accepts
    keys = ("price", "narrative_heat", "social_volume", "whale_net_flow",
            "funding_rate", "open_interest", "fear_greed")
    hist = {k: [1.0 + i for i in range(n)] for k in keys}
    hist["coverage"] = 1.0
    r = walk_forward(hist, token="X", n_folds=4, steps=SMALL)
    assert r["n_folds"] == 0
    assert r["oos_n"] == 0
    assert r["oos_sharpe"] == 0.0
