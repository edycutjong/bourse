"""
Backtest harness — walk a token's history forward, re-compute the Bourse signal at
each step from the trailing window, take the implied position (short = fade,
long = accumulate, none = flat), and realize next-step PnL. Returns
{sharpe, max_dd, win_rate, n_trades, n_active, final_return, equity_curve}.

Pure + deterministic (numpy only): fixed history in -> fixed metrics out, so the
demo reproduces exactly. The Day-1 CMC probe only decides *where* `history` comes
from (REST historical endpoints vs forward-collected fixtures); the logic here is
data-source agnostic, so it never needs to change once the probe lands.

`history` schema (every series equal length N, oldest..latest):
  {price, narrative_heat, social_volume, whale_net_flow, funding_rate,
   open_interest, fear_greed, coverage?}
Note `fear_greed` is a per-step SERIES here (the engine takes a scalar per step).
"""
from __future__ import annotations
import numpy as np
from .engine import Planes, compute

# series the engine consumes as rolling windows (fear_greed is sampled per step)
_WINDOW_SERIES = ("narrative_heat", "social_volume", "whale_net_flow",
                  "funding_rate", "open_interest")


def _position(direction: str) -> int:
    return {"long": 1, "short": -1, "none": 0}.get(direction, 0)


def run_backtest(history: dict, *, token: str = "TOKEN", window: int = 5,
                 fee_bps: float = 10.0, periods_per_year: int = 365) -> dict:
    price = np.asarray(history["price"], dtype=float)
    n = price.size
    if n < window + 2:
        raise ValueError(f"history too short: need >= {window + 2} points, got {n}")
    for k in (*_WINDOW_SERIES, "fear_greed"):
        if len(history[k]) != n:
            raise ValueError(f"series '{k}' has length {len(history[k])}, expected {n}")
    coverage = float(history.get("coverage", 1.0))

    rets: list[float] = []
    prev_pos = 0
    wins = active = trades = 0
    for t in range(window - 1, n - 1):
        lo = t - window + 1
        planes = Planes(
            narrative_heat=history["narrative_heat"][lo:t + 1],
            social_volume=history["social_volume"][lo:t + 1],
            whale_net_flow=history["whale_net_flow"][lo:t + 1],
            funding_rate=history["funding_rate"][lo:t + 1],
            open_interest=history["open_interest"][lo:t + 1],
            fear_greed=float(history["fear_greed"][t]),
            coverage=coverage,
        )
        pos = _position(compute(token, planes).direction)
        nxt = price[t + 1] / price[t] - 1.0
        r = pos * nxt
        if pos != prev_pos:                       # turnover -> fee on |delta position|
            r -= (fee_bps / 1e4) * abs(pos - prev_pos)
            if pos != 0:
                trades += 1                       # count entering a new nonzero position
        if pos != 0:
            active += 1
            if pos * nxt > 0:
                wins += 1
        rets.append(r)
        prev_pos = pos

    r = np.asarray(rets, dtype=float)
    equity = np.cumprod(1.0 + r)
    sd = r.std()
    sharpe = float(r.mean() / sd * np.sqrt(periods_per_year)) if sd > 0 else 0.0
    peak = np.maximum.accumulate(equity)
    max_dd = float((1.0 - equity / peak).max()) if equity.size else 0.0
    win_rate = wins / active if active else 0.0
    return {
        "sharpe": round(sharpe, 2),
        "max_dd": round(max_dd, 4),
        "win_rate": round(win_rate, 4),
        "n_trades": trades,
        "n_active": active,
        "final_return": round(float(equity[-1] - 1.0), 4) if equity.size else 0.0,
        "equity_curve": [round(float(x), 5) for x in equity],
    }
