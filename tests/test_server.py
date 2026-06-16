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


def test_real_backtest_valid_token():
    res = app._real_backtest("CAKE")
    assert res is not None
    assert set(res.keys()) == {"sharpe", "max_dd", "win_rate"}
    assert res["sharpe"] > 0


def test_real_backtest_invalid_token():
    res = app._real_backtest("NOPE")
    assert res is not None
    assert "sharpe" in res


def test_execute_job_token_casing():
    # description contains lowercase 'cake divergence signal'
    out = app.execute_job({"description": "cake divergence signal"})
    spec = json.loads(out)
    assert spec["token"] == "CAKE"
    assert spec["direction"] == "short"


def test_build_app_returns_fastapi_app(monkeypatch):
    # Mock create_erc8183_app to return a dummy string or FastAPI instance
    monkeypatch.setattr("bnbagent.erc8183.server.create_erc8183_app", lambda on_job: "dummy_app")
    assert app.build_app() == "dummy_app"

