"""Core engine tests. Target: grow this file + commerce tests to >=100 total."""
import json
import os
import subprocess
import sys
import pytest
from bourse import compute, build_spec, to_yaml, Planes, zscore

FIX = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "demo.json")


def _load():
    if not os.path.exists(FIX):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "scripts", "seed.py")], check=True)
    with open(FIX) as f:
        return json.load(f)


def test_zscore_degenerate():
    assert zscore([]) == 0.0
    assert zscore([5, 5, 5]) == 0.0


def test_smoking_gun_is_short_distribution():
    d = _load()["CAKE"]
    sig = compute("CAKE", Planes(**d))
    assert sig.direction == "short"
    assert sig.regime == "distribution"
    assert sig.divergence >= 40
    assert sig.crowd > 0 and sig.smart < 0
    assert any("whale" in r for r in sig.reasons)


def test_inverse_is_long_accumulation():
    d = _load()["XYZL"]
    sig = compute("XYZL", Planes(**d))
    assert sig.direction == "long"
    assert sig.regime == "accumulation"
    assert sig.divergence <= -40


def test_neutral_is_no_trade():
    d = _load()["ABCN"]
    sig = compute("ABCN", Planes(**d))
    assert sig.direction == "none"
    assert abs(sig.divergence) < 40


def test_spec_schema_and_yaml():
    d = _load()["CAKE"]
    sig = compute("CAKE", Planes(**d))
    spec = build_spec(sig, backtest={"sharpe": 1.9, "max_dd": 0.11, "win_rate": 0.58})
    assert spec["schema"] == "bourse.signal.v1"
    assert spec["direction"] == "short"
    assert spec["sources"]
    assert "schema: bourse.signal.v1" in to_yaml(spec)


def test_confidence_scales_with_coverage():
    d = dict(_load()["CAKE"])
    d["coverage"] = 0.5
    low = compute("CAKE", Planes(**d))
    d["coverage"] = 1.0
    high = compute("CAKE", Planes(**d))
    assert high.confidence >= low.confidence
