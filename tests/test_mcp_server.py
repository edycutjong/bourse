"""Unit tests for scripts/mcp_server.py."""
import json
import os
import pytest
import io
from unittest.mock import MagicMock, patch

# Adjust path to find the scripts
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
import sys
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import mcp_server  # type: ignore

def test_log():
    stderr = io.StringIO()
    with patch("sys.stderr", stderr):
        mcp_server.log("hello")
    assert "[bourse-mcp] hello\n" in stderr.getvalue()

def test_send_response():
    stdout = io.StringIO()
    with patch("sys.stdout", stdout):
        mcp_server.send_response({"foo": "bar"})
    assert json.loads(stdout.getvalue().strip()) == {"foo": "bar"}

def test_spark():
    curve = [1.0, 2.0, 3.0]
    res = mcp_server._spark(curve)
    assert len(res) == 3

def test_handle_get_divergence_board_live():
    res = mcp_server.handle_get_divergence_board({"live": True})
    assert "Live board view is not supported" in res

def test_handle_get_divergence_board_missing_fixture(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    res = mcp_server.handle_get_divergence_board({"live": False})
    assert "no fixtures" in res

def test_handle_get_divergence_board_success(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True if "demo.json" in p else False)
    mock_open = MagicMock(return_value=io.StringIO('{"CAKE": {}, "XYZL": {}}'))
    with patch("builtins.open", mock_open):
        with patch("mcp_server.from_fixture", return_value="planes"):
            with patch("mcp_server.compute") as mock_compute:
                mock_compute.side_effect = [
                    MagicMock(token="CAKE", divergence=10.0, regime="chop", direction="none", confidence=0.5),
                    MagicMock(token="XYZL", divergence=-50.0, regime="distribution", direction="short", confidence=0.8)
                ]
                res = mcp_server.handle_get_divergence_board({"live": False})
                assert "CAKE" in res
                assert "XYZL" in res

def test_handle_get_divergence_board_exception(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True if "demo.json" in p else False)
    mock_open = MagicMock(return_value=io.StringIO('{"CAKE": {}}'))
    with patch("builtins.open", mock_open):
        with patch("mcp_server.from_fixture", side_effect=ValueError("load error")):
            res = mcp_server.handle_get_divergence_board({"live": False})
            assert "TOKEN" in res

def test_handle_get_token_signal_missing_token():
    res = mcp_server.handle_get_token_signal({})
    assert "token argument is required" in res

def test_handle_get_token_signal_live_success():
    with patch("mcp_server.from_mcp", return_value="live_planes"):
        with patch("mcp_server.compute", return_value=MagicMock(token="CAKE", divergence=10.0, regime="chop", direction="none", confidence=0.5, crowd=0.1, smart=0.2, reasons=[])):
            res = mcp_server.handle_get_token_signal({"token": "CAKE", "live": True})
            assert "CAKE" in res
            assert "CMC MCP (live)" in res

def test_handle_get_token_signal_live_fail():
    with patch("mcp_server.from_mcp", side_effect=RuntimeError("mcp failed")):
        res = mcp_server.handle_get_token_signal({"token": "CAKE", "live": True})
        assert "Error loading planes" in res

def test_handle_get_token_signal_fixture_missing_fixture(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    res = mcp_server.handle_get_token_signal({"token": "CAKE", "live": False})
    assert "no fixtures" in res

def test_handle_get_token_signal_fixture_key_error(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True if "demo.json" in p else False)
    with patch("mcp_server.from_fixture", side_effect=KeyError("key missing")):
        res = mcp_server.handle_get_token_signal({"token": "CAKE", "live": False})
        assert "no fixture data for token" in res

def test_handle_get_token_signal_with_backtest(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    mock_open = MagicMock(return_value=io.StringIO('{"price": [1, 2]}'))
    with patch("builtins.open", mock_open):
        with patch("mcp_server.from_fixture", return_value="planes"):
            with patch("mcp_server.compute", return_value=MagicMock(token="CAKE", divergence=10.0, regime="chop", direction="none", confidence=0.5, crowd=0.1, smart=0.2, reasons=[])):
                with patch("mcp_server.run_backtest", return_value={"sharpe": 1.5, "max_dd": 0.1, "win_rate": 0.6}):
                    res = mcp_server.handle_get_token_signal({"token": "CAKE", "live": False})
                    assert "CAKE" in res
                    assert "sharpe" in res

def test_handle_get_token_signal_backtest_error(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    mock_open = MagicMock(return_value=io.StringIO('{"price": [1, 2]}'))
    with patch("builtins.open", mock_open):
        with patch("mcp_server.from_fixture", return_value="planes"):
            with patch("mcp_server.compute", return_value=MagicMock(token="CAKE", divergence=10.0, regime="chop", direction="none", confidence=0.5, crowd=0.1, smart=0.2, reasons=[])):
                with patch("mcp_server.run_backtest", side_effect=ValueError("backtest failed")):
                    res = mcp_server.handle_get_token_signal({"token": "CAKE", "live": False})
                    assert "CAKE" in res

def test_handle_run_backtest_missing_token():
    res = mcp_server.handle_run_backtest({})
    assert "token argument is required" in res

def test_handle_run_backtest_missing_fixture(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    res = mcp_server.handle_run_backtest({"token": "CAKE"})
    assert "backtest fixture not found" in res

def test_handle_run_backtest_success(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    mock_open = MagicMock(return_value=io.StringIO('{"price": [1, 2]}'))
    with patch("builtins.open", mock_open):
        with patch("mcp_server.run_backtest", return_value={"sharpe": 1.5, "max_dd": 0.1, "win_rate": 0.6, "n_trades": 5, "n_active": 10, "final_return": 0.2, "equity_curve": [1.0, 1.2]}):
            res = mcp_server.handle_run_backtest({"token": "CAKE"})
            assert "Sharpe (ann.)" in res

def test_handle_run_backtest_fail(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda p: True)
    mock_open = MagicMock(return_value=io.StringIO('{"price": [1, 2]}'))
    with patch("builtins.open", mock_open):
        with patch("mcp_server.run_backtest", side_effect=ValueError("backtest failed")):
            res = mcp_server.handle_run_backtest({"token": "CAKE"})
            assert "Error running backtest" in res

def test_main_loop_initialize():
    stdin = io.StringIO('{"jsonrpc": "2.0", "method": "initialize", "params": {}, "id": 1}\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        mcp_server.main_loop()
    res = json.loads(stdout.getvalue().strip())
    assert res["id"] == 1
    assert "protocolVersion" in res["result"]

def test_main_loop_initialized():
    stdin = io.StringIO('{"jsonrpc": "2.0", "method": "notifications/initialized"}\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        mcp_server.main_loop()
    assert stdout.getvalue() == ""

def test_main_loop_tools_list():
    stdin = io.StringIO('{"jsonrpc": "2.0", "method": "tools/list", "id": 2}\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        mcp_server.main_loop()
    res = json.loads(stdout.getvalue().strip())
    assert res["id"] == 2
    assert len(res["result"]["tools"]) == 3

def test_main_loop_tools_call_board():
    stdin = io.StringIO('{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_divergence_board", "arguments": {}}, "id": 3}\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout), patch("mcp_server.handle_get_divergence_board", return_value="board_output"):
        mcp_server.main_loop()
    res = json.loads(stdout.getvalue().strip())
    assert res["id"] == 3
    assert res["result"]["content"][0]["text"] == "board_output"

def test_main_loop_tools_call_token():
    stdin = io.StringIO('{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "get_token_signal", "arguments": {"token": "CAKE"}}, "id": 4}\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout), patch("mcp_server.handle_get_token_signal", return_value="token_output"):
        mcp_server.main_loop()
    res = json.loads(stdout.getvalue().strip())
    assert res["id"] == 4
    assert res["result"]["content"][0]["text"] == "token_output"

def test_main_loop_tools_call_backtest():
    stdin = io.StringIO('{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "run_backtest", "arguments": {"token": "CAKE"}}, "id": 5}\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout), patch("mcp_server.handle_run_backtest", return_value="backtest_output"):
        mcp_server.main_loop()
    res = json.loads(stdout.getvalue().strip())
    assert res["id"] == 5
    assert res["result"]["content"][0]["text"] == "backtest_output"

def test_main_loop_tools_call_unknown():
    stdin = io.StringIO('{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "unknown_tool", "arguments": {}}, "id": 6}\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        mcp_server.main_loop()
    res = json.loads(stdout.getvalue().strip())
    assert "Unknown tool" in res["result"]["content"][0]["text"]

def test_main_loop_unknown_method():
    stdin = io.StringIO('{"jsonrpc": "2.0", "method": "unknown_method", "id": 7}\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        mcp_server.main_loop()
    res = json.loads(stdout.getvalue().strip())
    assert res["error"]["code"] == -32601

def test_main_loop_invalid_json():
    stdin = io.StringIO('invalid_json\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        mcp_server.main_loop()
    res = json.loads(stdout.getvalue().strip())
    assert res["error"]["code"] == -32700

def test_main_loop_empty_line():
    stdin = io.StringIO('\n{"jsonrpc": "2.0", "method": "tools/list", "id": 8}\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout):
        mcp_server.main_loop()
    res = json.loads(stdout.getvalue().strip())
    assert res["id"] == 8

def test_main_loop_exception():
    stdin = io.StringIO('{"jsonrpc": "2.0", "method": "tools/list", "id": 9}\n')
    stdout = io.StringIO()
    with patch("sys.stdin", stdin), patch("sys.stdout", stdout), patch("mcp_server.send_response", side_effect=Exception("stdout error")):
        mcp_server.main_loop()
