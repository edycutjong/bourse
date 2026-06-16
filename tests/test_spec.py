"""bourse.signal.v1 spec-generator invariants."""
import datetime as dt

import pytest
import yaml

from bourse import Signal, build_spec, to_yaml
from bourse.spec import REGIME_SCALAR


def _sig(direction="short", regime="distribution", divergence=100.0):
    return Signal(token="CAKE", divergence=divergence, regime=regime,
                  direction=direction, confidence=1.0, crowd=1.8, smart=-1.7,
                  reasons=["crowd hot", "whales net-outflow"])


def test_schema_and_core_fields():
    spec = build_spec(_sig())
    assert spec["schema"] == "bourse.signal.v1"
    assert spec["token"] == "CAKE"
    assert spec["regime"] == "distribution"
    assert spec["divergence"] == 100.0
    assert spec["reasons"]


def test_generated_at_is_iso_utc():
    spec = build_spec(_sig())
    parsed = dt.datetime.fromisoformat(spec["generated_at"])
    assert parsed.tzinfo is not None                       # tz-aware
    assert parsed.utcoffset() == dt.timedelta(0)           # UTC


def test_short_body_shape():
    spec = build_spec(_sig("short"))
    assert spec["direction"] == "short"
    assert "funding > p90" in spec["entry"]["trigger"]
    assert spec["invalidation"] == "on-chain whale flow flips net-inflow"
    assert spec["stop"] == {"type": "atr", "mult": 1.5}
    assert spec["exit"]["time_stop_h"] == 48


def test_long_body_shape():
    spec = build_spec(_sig("long", regime="accumulation", divergence=-90))
    assert spec["direction"] == "long"
    assert "whale_flow > p75" in spec["entry"]["trigger"]
    assert spec["invalidation"] == "on-chain whale flow flips net-outflow"


def test_long_and_short_differ():
    short = build_spec(_sig("short"))
    long = build_spec(_sig("long", regime="accumulation", divergence=-90))
    assert short["entry"]["trigger"] != long["entry"]["trigger"]
    assert short["invalidation"] != long["invalidation"]


def test_none_direction_is_no_trade():
    spec = build_spec(_sig("none", regime="chop", divergence=5))
    assert spec["direction"] == "none"
    assert "note" in spec
    for k in ("entry", "exit", "stop", "sizing", "invalidation"):
        assert k not in spec


@pytest.mark.parametrize("regime,scalar", list(REGIME_SCALAR.items()))
def test_regime_scalar_mapping(regime, scalar):
    direction = "long" if regime == "accumulation" else "short"
    spec = build_spec(_sig(direction, regime=regime, divergence=80))
    assert spec["sizing"]["regime_scalar"] == scalar


def test_unknown_regime_scalar_defaults():
    spec = build_spec(_sig("short", regime="mystery", divergence=80))
    assert spec["sizing"]["regime_scalar"] == 0.5


def test_sizing_pct_portfolio_present():
    spec = build_spec(_sig("short"))
    assert spec["sizing"]["pct_portfolio"] == 3


def test_default_sources():
    spec = build_spec(_sig())
    assert spec["sources"] == ["DerivativesData", "OnChainMetrics",
                               "TrendingNarratives", "GlobalMetrics"]


def test_custom_sources_override():
    spec = build_spec(_sig(), sources=["X", "Y"])
    assert spec["sources"] == ["X", "Y"]


def test_backtest_passthrough_when_present():
    bt = {"sharpe": 1.9, "max_dd": 0.11, "win_rate": 0.58}
    assert build_spec(_sig(), backtest=bt)["backtest"] == bt


def test_backtest_omitted_when_absent():
    assert "backtest" not in build_spec(_sig())


def test_to_yaml_roundtrips_core_fields():
    spec = build_spec(_sig(), backtest={"sharpe": 1.9})
    loaded = yaml.safe_load(to_yaml(spec))
    assert loaded["schema"] == "bourse.signal.v1"
    assert loaded["direction"] == "short"
    assert loaded["divergence"] == 100.0
    assert loaded["backtest"]["sharpe"] == 1.9


def test_to_yaml_preserves_key_order():
    text = to_yaml(build_spec(_sig()))
    assert text.splitlines()[0].startswith("schema:")     # sort_keys=False
