"""End-to-end CLI tests for scripts/signal.py (subprocess, offline fixture mode)."""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(__file__), "..")
CLI = os.path.join(ROOT, "scripts", "signal.py")


def _run(*args):
    return subprocess.run([sys.executable, CLI, *args],
                          cwd=ROOT, capture_output=True, text=True, timeout=60)


@pytest.fixture(autouse=True, scope="module")
def _seed():
    if not os.path.exists(os.path.join(ROOT, "data", "fixtures", "demo.json")):
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "seed.py")],
                       check=True)


def test_board_lists_all_tokens():
    r = _run()
    assert r.returncode == 0
    for tok in ("CAKE", "XYZL", "ABCN"):
        assert tok in r.stdout
    assert "SHORT/FADE" in r.stdout


def test_token_view_shows_why_and_spec():
    r = _run("--token", "CAKE")
    assert r.returncode == 0
    assert "bourse.signal.v1" in r.stdout
    assert "divergence" in r.stdout
    assert "whales net-outflow" in r.stdout


def test_token_json_is_valid_spec():
    r = _run("--token", "XYZL", "--json")
    assert r.returncode == 0
    spec = json.loads(r.stdout)
    assert spec["schema"] == "bourse.signal.v1"
    assert spec["direction"] == "long"
    assert set(spec["backtest"]) >= {"sharpe", "max_dd", "win_rate"}


def test_unknown_token_exits_nonzero():
    r = _run("--token", "NOPE")
    assert r.returncode != 0


def test_live_board_combo_rejected():
    r = _run("--live")              # no --token
    assert r.returncode != 0


def test_discover_fails_without_key():
    r = _run("--discover")
    assert r.returncode != 0
    assert "CMC_MCP_API_KEY not set" in r.stderr


def test_discover_in_process(monkeypatch, capsys):
    import importlib.util
    spec = importlib.util.spec_from_file_location("bourse_signal_cli", CLI)
    cli_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli_mod)

    class DummyClient:
        def list_tools(self):
            return [{"name": "fake_tool", "description": "fake desc"}]

    monkeypatch.setattr("bourse.ingest.MCPClient", DummyClient)
    cli_mod.discover()
    captured = capsys.readouterr()
    assert "fake_tool" in captured.out


def test_invalid_argument_exits_nonzero():
    r = _run("--bogus-argument-xyz")
    assert r.returncode != 0


def test_seed_runs_successfully():
    script = os.path.join(ROOT, "scripts", "seed.py")
    r = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0


def test_bench_runs_successfully():
    script = os.path.join(ROOT, "scripts", "bench.py")
    r = subprocess.run([sys.executable, script, "-n", "5"], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert r.returncode == 0
    assert "compute()" in r.stdout


def test_settle_missing_job_id():
    script = os.path.join(ROOT, "scripts", "settle.py")
    r = subprocess.run([sys.executable, script], cwd=ROOT, capture_output=True, text=True, timeout=30)
    assert r.returncode != 0

