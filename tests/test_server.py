"""ERC-8183 on_job wiring tests. These exercise the provider's job->spec path
WITHOUT the bnbagent SDK (only build_app() touches the SDK / network)."""
import importlib.util
import json
import os
import subprocess
import sys
import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")


def _load_app():
    fix = os.path.join(ROOT, "data", "fixtures", "demo.json")
    if not os.path.exists(fix):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "seed.py")], check=True)
    spec = importlib.util.spec_from_file_location(
        "bourse_server_app", os.path.join(ROOT, "server", "app.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


app = _load_app()


def test_token_parsing_from_description():
    # buyers anchor "CAKE divergence signal" on-chain -> server must extract the symbol
    assert app._token_of({"description": "CAKE divergence signal"}) == "CAKE"
    assert app._token_of({"token": "xyzl"}) == "XYZL"
    assert app._token_of({}) == "CAKE"


def test_execute_job_returns_json_spec_string():
    out = app.execute_job({"description": "CAKE divergence signal"})
    assert isinstance(out, str)               # SDK requires a string deliverable
    spec = json.loads(out)
    assert spec["schema"] == "bourse.signal.v1"
    assert spec["token"] == "CAKE" and spec["direction"] == "short"
    assert set(spec["backtest"]) >= {"sharpe", "max_dd", "win_rate"}


def test_unknown_token_raises():
    with pytest.raises(RuntimeError):
        app.run_divergence({"token": "NOPE"})
