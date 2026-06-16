"""
Strategy-spec generator: turns a Signal into the backtestable `bourse.signal.v1`
spec (the Track-2 deliverable artifact). Deterministic given a Signal + backtest.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Any
import yaml
from .engine import Signal

REGIME_SCALAR = {"risk-on": 1.0, "accumulation": 0.8, "chop": 0.3,
                 "risk-off": 0.4, "distribution": 0.5}


def build_spec(sig: Signal, backtest: dict | None = None,
               sources: list[str] | None = None) -> dict:
    body: dict[str, Any]
    if sig.direction == "none":
        body = {"direction": "none", "note": "divergence below threshold — no trade"}
    else:
        long = sig.direction == "long"
        body = {
            "direction": sig.direction,
            "entry": {"trigger": ("price < ema(20) AND funding > p90" if not long
                                  else "price > ema(20) AND whale_flow > p75")},
            "exit": {"take_profit": "abs(divergence) < 20", "time_stop_h": 48},
            "stop": {"type": "atr", "mult": 1.5},
            "sizing": {"pct_portfolio": 3, "regime_scalar": REGIME_SCALAR.get(sig.regime, 0.5)},
            "invalidation": ("on-chain whale flow flips net-inflow" if not long
                             else "on-chain whale flow flips net-outflow"),
        }
    spec = {
        "schema": "bourse.signal.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "token": sig.token,
        "regime": sig.regime,
        "divergence": sig.divergence,
        "confidence": sig.confidence,
        "reasons": sig.reasons,
        **body,
        "sources": sources or ["DerivativesData", "OnChainMetrics",
                               "TrendingNarratives", "GlobalMetrics"],
    }
    if backtest:
        spec["backtest"] = backtest
    return spec


def to_yaml(spec: dict) -> str:
    return yaml.safe_dump(spec, sort_keys=False, default_flow_style=False)
