"""
Bourse divergence + regime engine (core IP).

Pure, deterministic, rule-based — no ML, no network. Takes normalized per-plane
series for a token and returns a Divergence score, a Regime label, and confidence.
Legible by design: a judge can read exactly why a signal fired.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence
import numpy as np

# plane weights (config, not learned). crowd = social/narrative; smart = flow+derivs.
W = {"narrative": 0.6, "social": 0.4, "whale_flow": 0.6, "funding_oi": 0.4}


def zscore(series: Sequence[float]) -> float:
    """z-score of the latest point vs the rolling window. 0 if degenerate."""
    a = np.asarray(series, dtype=float)
    a = a[np.isfinite(a)]  # Purge NaNs and Infs to prevent poisoned signal propagation
    if a.size < 2:
        return 0.0
    sd = a.std()
    if sd == 0:
        return 0.0
    return float((a[-1] - a.mean()) / sd)


@dataclass
class Planes:
    """Each field is a recent window (oldest..latest) for one token."""
    narrative_heat: Sequence[float]      # Trending Narratives
    social_volume: Sequence[float]       # social/news volume
    whale_net_flow: Sequence[float]      # On-Chain Metrics (net whale flow; + = inflow)
    funding_rate: Sequence[float]        # Derivatives Data (funding)
    open_interest: Sequence[float]       # Derivatives Data (OI)
    fear_greed: float                    # Global Metrics F&G (0..100)
    coverage: float = 1.0                # 0..1 fraction of planes with real data


@dataclass
class Signal:
    token: str
    divergence: float                    # -100..+100  (+ = crowd hot, smart money leaving)
    regime: str                          # risk-on|risk-off|accumulation|distribution|chop
    direction: str                       # short|long|none
    confidence: float                    # 0..1
    crowd: float = 0.0
    smart: float = 0.0
    reasons: list[str] = field(default_factory=list)
    derivatives_pct: int = 50
    whale_pct: int = 50
    sentiment_pct: int = 50
    technical_pct: int = 50


def _clip100(x: float) -> float:
    return max(-100.0, min(100.0, x))


def compute(token: str, p: Planes, *, fade_threshold: float = 40.0) -> Signal:
    crowd = W["narrative"] * zscore(p.narrative_heat) + W["social"] * zscore(p.social_volume)
    # smart money: positive whale flow = accumulation (bullish); overcrowded long funding = bearish
    funding_skew = zscore(p.funding_rate)
    oi_delta = zscore(p.open_interest)
    smart = W["whale_flow"] * zscore(p.whale_net_flow) - W["funding_oi"] * funding_skew

    divergence = _clip100((crowd - smart) * 33.3)   # scale z-diff into -100..100-ish

    reasons = []
    if crowd > 0.5:
        reasons.append(f"crowd hot (z={crowd:+.2f}: narrative+social)")
    if zscore(p.whale_net_flow) < -0.5:
        reasons.append("whales net-outflow (distribution)")
    if funding_skew > 0.5:
        reasons.append(f"funding overcrowded-long (z={funding_skew:+.2f})")
    if oi_delta > 0.5:
        reasons.append("rising OI")

    regime = classify_regime(p, funding_skew, oi_delta)

    direction = "none"
    if divergence >= fade_threshold:
        direction = "short"      # crowd euphoric, smart money leaving -> fade
    elif divergence <= -fade_threshold:
        direction = "long"       # crowd fearful, smart money accumulating

    confidence = min(1.0, abs(divergence) / 100.0 * p.coverage + 0.0)

    # Compute individual plane normalized percentages (0..100)
    avg_deriv_z = (funding_skew + oi_delta) / 2.0
    derivatives_pct = int(max(0.0, min(100.0, 50.0 + avg_deriv_z * 20.0)))

    whale_z = zscore(p.whale_net_flow)
    whale_pct = int(max(0.0, min(100.0, 50.0 + whale_z * 20.0)))

    sentiment_z = (zscore(p.narrative_heat) + zscore(p.social_volume)) / 2.0
    sentiment_pct = int(max(0.0, min(100.0, 50.0 + sentiment_z * 20.0)))

    technical_pct = int(max(0.0, min(100.0, p.fear_greed)))

    return Signal(
        token=token,
        divergence=round(divergence, 1),
        regime=regime,
        direction=direction,
        confidence=round(confidence, 2),
        crowd=round(crowd, 2),
        smart=round(smart, 2),
        reasons=reasons,
        derivatives_pct=derivatives_pct,
        whale_pct=whale_pct,
        sentiment_pct=sentiment_pct,
        technical_pct=technical_pct
    )


def classify_regime(p: Planes, funding_skew: float, oi_delta: float) -> str:
    fg = p.fear_greed
    flow = zscore(p.whale_net_flow)
    if fg >= 75 and funding_skew > 0.5:
        return "distribution"          # greed + crowded longs
    if fg <= 25 and flow > 0.5:
        return "accumulation"          # fear + whales buying
    if fg >= 60 and oi_delta > 0:
        return "risk-on"
    if fg <= 35:
        return "risk-off"
    return "chop"
