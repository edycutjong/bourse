"""Core engine tests: zscore, divergence, regime matrix, thresholds, spec."""
import json
import os
import subprocess
import sys
import pytest
from bourse import compute, build_spec, classify_regime, to_yaml, Planes, zscore

FIX = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "demo.json")


def _load():
    if not os.path.exists(FIX):
        subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "..", "scripts", "seed.py")], check=True)
    with open(FIX) as f:
        return json.load(f)


def _planes(fear_greed=50.0, whale=(0, 0, 0), **kw):
    base = dict(narrative_heat=[1, 1, 1], social_volume=[1, 1, 1],
                whale_net_flow=list(whale), funding_rate=[0, 0, 0],
                open_interest=[100, 100, 100], fear_greed=fear_greed)
    base.update(kw)
    return Planes(**base)


# ---- zscore --------------------------------------------------------------- #
def test_zscore_degenerate():
    assert zscore([]) == 0.0
    assert zscore([5]) == 0.0
    assert zscore([5, 5, 5]) == 0.0


def test_zscore_sign_and_symmetry():
    assert zscore([1, 2, 3, 4, 5]) > 0          # latest above mean
    assert zscore([5, 4, 3, 2, 1]) < 0          # latest below mean
    assert zscore([1, 2, 3, 4, 5]) == pytest.approx(-zscore([5, 4, 3, 2, 1]))


def test_zscore_value():
    import numpy as np
    s = [1, 2, 3, 4, 5]
    assert zscore(s) == pytest.approx((s[-1] - np.mean(s)) / np.std(s))


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


# ---- divergence bounds & confidence -------------------------------------- #
@pytest.mark.parametrize("token", ["CAKE", "XYZL", "ABCN"])
def test_divergence_within_bounds(token):
    sig = compute(token, Planes(**_load()[token]))
    assert -100.0 <= sig.divergence <= 100.0
    assert 0.0 <= sig.confidence <= 1.0


def test_cake_divergence_clips_to_100():
    assert compute("CAKE", Planes(**_load()["CAKE"])).divergence == 100.0


def test_confidence_zero_when_no_divergence():
    assert compute("ABCN", Planes(**_load()["ABCN"])).confidence == 0.0


# ---- fade threshold ------------------------------------------------------- #
def test_higher_threshold_suppresses_signal():
    d = _load()["CAKE"]
    assert compute("CAKE", Planes(**d)).direction == "short"
    assert compute("CAKE", Planes(**d), fade_threshold=200).direction == "none"


def test_lower_threshold_can_fire_signal():
    # ABCN is flat (~0 divergence); even a tiny threshold keeps it no-trade,
    # but a clearly-divergent token fires at the default and stays firing lower.
    d = _load()["XYZL"]
    assert compute("XYZL", Planes(**d), fade_threshold=10).direction == "long"


# ---- regime matrix -------------------------------------------------------- #
def test_regime_distribution():
    assert classify_regime(_planes(fear_greed=80), 1.0, 0.0) == "distribution"


def test_regime_accumulation():
    p = _planes(fear_greed=20, whale=(0, 1, 5))     # whales buying -> flow z > 0.5
    assert classify_regime(p, 0.0, 0.0) == "accumulation"


def test_regime_risk_on():
    assert classify_regime(_planes(fear_greed=65), 0.0, 0.5) == "risk-on"


def test_regime_risk_off():
    assert classify_regime(_planes(fear_greed=30), 0.0, 0.0) == "risk-off"


def test_regime_chop():
    assert classify_regime(_planes(fear_greed=50), 0.0, 0.0) == "chop"


@pytest.mark.parametrize("token,regime", [
    ("CAKE", "distribution"), ("XYZL", "accumulation"), ("ABCN", "chop")])
def test_fixture_regimes(token, regime):
    assert compute(token, Planes(**_load()[token])).regime == regime


# ---- crowd / smart decomposition ----------------------------------------- #
def test_crowd_and_smart_opposite_on_smoking_gun():
    sig = compute("CAKE", Planes(**_load()["CAKE"]))
    assert sig.crowd > 0 and sig.smart < 0


def test_reasons_are_strings():
    sig = compute("CAKE", Planes(**_load()["CAKE"]))
    assert sig.reasons and all(isinstance(r, str) for r in sig.reasons)
