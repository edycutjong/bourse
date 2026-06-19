"""
Walk-forward weight optimization — the honest version of a single in-sample grid search.

Picking the best of 1,296 weight combos on one fixture and reporting *that* Sharpe is
overfitting: with that many tries a high Sharpe shows up by luck, even on random data.
Walk-forward instead FITS the weights on a train window and SCORES them on the next, unseen
test window, so the reported number is out-of-sample — the only kind a trader or an agent
should pay for.

For each token:
  - slide an expanding train / forward test split across its history (`n_folds` folds);
  - on each TRAIN range, grid-search the 4 plane weights to maximize train Sharpe;
  - apply those frozen weights to the following TEST range and keep only the test returns;
  - pool every fold's test returns into one out-of-sample Sharpe.

`optimize_multi` runs this across several tokens and pools the out-of-sample returns, so the
headline number reflects generalization, not one lucky fixture. Pure + deterministic (same
fixtures in -> same numbers out), matching bourse.backtest.
"""
from __future__ import annotations
import itertools
from contextlib import contextmanager
from typing import Iterator

import numpy as np

import bourse.engine as engine
from .backtest import _simulate, _validate, sharpe_ratio

# grid resolution per plane weight (same 6^4 = 1,296 combos the old optimizer searched)
DEFAULT_STEPS = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
_KEYS = ("narrative", "social", "whale_flow", "funding_oi")


@contextmanager
def use_weights(w: dict):
    """Temporarily install plane weights `w` into the engine, restoring the prior set after.

    The engine reads a module-level `W` (config, not learned); a context manager makes
    trying a combo safe and reentrant instead of permanently mutating global state.
    """
    saved = dict(engine.W)
    try:
        engine.W.update(w)
        yield
    finally:
        engine.W.clear()
        engine.W.update(saved)


def _grid(steps) -> Iterator[dict]:
    for combo in itertools.product(steps, repeat=len(_KEYS)):
        yield dict(zip(_KEYS, combo))


def _returns(history, price, token, window, fee_bps, t0, t1):
    rets, *_ = _simulate(history, price, token=token, window=window,
                         fee_bps=fee_bps, t0=t0, t1=t1)
    return rets


def _best_weights(history, price, token, window, fee_bps, t0, t1, steps, ppy):
    """Grid-search the weights that maximize Sharpe over decision steps [t0, t1)."""
    best_w, best_s = None, -np.inf
    for w in _grid(steps):
        with use_weights(w):
            s = sharpe_ratio(_returns(history, price, token, window, fee_bps, t0, t1), ppy)
        if s > best_s:
            best_s, best_w = s, w
    return best_w, best_s


def walk_forward(history: dict, *, token: str = "TOKEN", window: int = 5,
                 fee_bps: float = 10.0, n_folds: int = 4, steps=DEFAULT_STEPS,
                 periods_per_year: int = 365) -> dict:
    """Expanding-window walk-forward optimization for one token.

    Returns the pooled out-of-sample Sharpe alongside the (overfit) in-sample Sharpe from
    grid-searching the whole history, so the gap between them is explicit.
    """
    price, n = _validate(history, window)
    start, stop = window - 1, n - 1          # decision steps live in [start, stop)
    edges = np.linspace(start, stop, n_folds + 1).round().astype(int)

    folds: list[dict] = []
    oos_rets: list[float] = []
    for i in range(1, len(edges) - 1):
        tr0, tr1 = start, int(edges[i])               # expanding train window
        te0, te1 = int(edges[i]), int(edges[i + 1])   # next, unseen test window
        if tr1 - tr0 < 2 or te1 - te0 < 1:
            continue
        best_w, train_s = _best_weights(
            history, price, token, window, fee_bps, tr0, tr1, steps, periods_per_year)
        with use_weights(best_w):                      # freeze train-fit weights, score OOS
            test_rets = _returns(history, price, token, window, fee_bps, te0, te1)
        oos_rets.extend(test_rets)
        folds.append({
            "train": [tr0, tr1], "test": [te0, te1], "weights": best_w,
            "train_sharpe": round(train_s, 2),
            "test_sharpe": round(sharpe_ratio(test_rets, periods_per_year), 2),
        })

    # the overfit number, for contrast: best in-sample grid search on the WHOLE history
    _, in_sample = _best_weights(
        history, price, token, window, fee_bps, start, stop, steps, periods_per_year)
    return {
        "token": token,
        "in_sample_sharpe": round(in_sample, 2),
        "oos_sharpe": round(sharpe_ratio(oos_rets, periods_per_year), 2),
        "n_folds": len(folds),
        "oos_n": len(oos_rets),
        "folds": folds,
        "oos_returns": oos_rets,
    }


def optimize_multi(histories: dict, *, window: int = 5, fee_bps: float = 10.0,
                   n_folds: int = 4, steps=DEFAULT_STEPS,
                   periods_per_year: int = 365) -> dict:
    """Run walk_forward across several tokens and pool the out-of-sample returns.

    `histories` maps token -> history dict (the bourse.backtest schema).
    """
    per_token: dict[str, dict] = {}
    pooled_oos: list[float] = []
    in_sample_sharpes: list[float] = []
    for token, history in histories.items():
        r = walk_forward(history, token=token, window=window, fee_bps=fee_bps,
                         n_folds=n_folds, steps=steps, periods_per_year=periods_per_year)
        per_token[token] = r
        pooled_oos.extend(r["oos_returns"])
        in_sample_sharpes.append(r["in_sample_sharpe"])
    return {
        "tokens": list(histories.keys()),
        "per_token": per_token,
        "pooled_oos_sharpe": round(sharpe_ratio(pooled_oos, periods_per_year), 2),
        "mean_in_sample_sharpe": (
            round(float(np.mean(in_sample_sharpes)), 2) if in_sample_sharpes else 0.0),
        "oos_n": len(pooled_oos),
    }
