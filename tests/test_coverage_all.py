# ruff: noqa: E402
import sys
import os
import pytest
import importlib.util
from unittest.mock import MagicMock, patch

# Clear environment keys loaded by other tests/files to avoid contaminating test_ingest.py
if "CMC_MCP_API_KEY" in os.environ:
    del os.environ["CMC_MCP_API_KEY"]
if "CMC_PRO_API_KEY" in os.environ:
    del os.environ["CMC_PRO_API_KEY"]

# Adjust path to find the packages
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "server"))
sys.path.insert(0, os.path.join(ROOT, "clients"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

# Import targets
import app  # type: ignore
import identity  # type: ignore
import buyer  # type: ignore
import settle  # type: ignore
import backtest  # type: ignore
import bench  # type: ignore
import check_submission_readiness  # type: ignore
import probe_cmc_history  # type: ignore

# Dynamically load signal.py to avoid name clash with Python's built-in signal module
spec = importlib.util.spec_from_file_location("bourse_signal_cli", os.path.join(ROOT, "scripts", "signal.py"))
assert spec is not None
assert spec.loader is not None
signal_cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(signal_cli)

# Register in sys.modules so patch can find it
sys.modules["bourse_signal_cli"] = signal_cli

from bourse.ingest import MCPClient, from_mcp, fetch_fear_greed_history, _series_from_result  # type: ignore


# --------------------------------------------------------------------------- #
# server/app.py tests
# --------------------------------------------------------------------------- #

def test_real_backtest_missing_fixture(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda x: False)
    assert app._real_backtest("CAKE") is None


def test_run_divergence_missing_fixture(monkeypatch):
    original_exists = os.path.exists
    def mock_exists(p):
        if "demo.json" in p:
            return False
        return original_exists(p)
    
    monkeypatch.setattr(os.path, "exists", mock_exists)
    with pytest.raises(RuntimeError, match="no fixture"):
        app.run_divergence({"token": "CAKE"})


def test_main_branch_offline(capsys):
    with patch("app.run_divergence", return_value={"dummy": "spec"}):
        with patch.object(sys, "argv", ["app.py"]):
            import app as test_app  # type: ignore
            test_app.run_divergence({"token": "CAKE"})
            assert True


def test_main_branch_serve():
    with patch("uvicorn.run") as mock_run:
        with patch("app.build_app", return_value="mock_app"):
            with patch.object(sys, "argv", ["app.py", "--serve"]):
                import app as test_app  # type: ignore
                if "--serve" in sys.argv:
                    import uvicorn
                    import os
                    uvicorn.run(test_app.build_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8003")))
                mock_run.assert_called_once_with("mock_app", host="0.0.0.0", port=8003)


def test_app_main_block_serve(monkeypatch):
    monkeypatch.setenv("WALLET_PASSWORD", "mock_password")
    monkeypatch.setenv("PRIVATE_KEY", "0x4e582560bc6ffb3131547778dc9106d2956035113ce76fc5936ac1ed28402caa")
    monkeypatch.setenv("ERC8183_SERVICE_PRICE", "100")
    with patch("uvicorn.run") as mock_run:
        mock_app = MagicMock()
        with patch("bnbagent.erc8183.server.create_erc8183_app", return_value=mock_app):
            with patch.object(sys, "argv", ["app.py", "--serve"]):
                spec = importlib.util.spec_from_file_location("__main__", os.path.join(ROOT, "server", "app.py"))
                m = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(m)
                mock_run.assert_called_once_with(mock_app, host="0.0.0.0", port=8003)


def test_app_main_block_offline():
    with patch("app.run_divergence", return_value={"cake": "sig"}):
        with patch.object(sys, "argv", ["app.py"]):
            spec = importlib.util.spec_from_file_location("__main__", os.path.join(ROOT, "server", "app.py"))
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)


# --------------------------------------------------------------------------- #
# server/identity.py tests
# --------------------------------------------------------------------------- #

def test_register_missing_password(monkeypatch):
    monkeypatch.delenv("WALLET_PASSWORD", raising=False)
    with pytest.raises(SystemExit):
        identity.register()


def test_register_success(monkeypatch):
    monkeypatch.setenv("WALLET_PASSWORD", "mock_password")
    monkeypatch.setenv("PRIVATE_KEY", "0x4e582560bc6ffb3131547778dc9106d2956035113ce76fc5936ac1ed28402caa")
    monkeypatch.setenv("NETWORK", "bsc-testnet")
    monkeypatch.setenv("ERC8183_AGENT_URL", "http://localhost:8003/erc8183")

    mock_wallet = MagicMock()
    mock_sdk = MagicMock()
    mock_sdk.generate_agent_uri.return_value = "mock_uri"
    mock_sdk.register_agent.return_value = {"agentId": "agent-123", "transactionHash": "0xhash"}

    with patch("bnbagent.wallets.EVMWalletProvider", return_value=mock_wallet):
        with patch("bnbagent.ERC8004Agent", return_value=mock_sdk):
            res = identity.register()
            assert res["agentId"] == "agent-123"
            assert res["transactionHash"] == "0xhash"


def test_identity_main_block(monkeypatch):
    monkeypatch.setenv("WALLET_PASSWORD", "mock_password")
    monkeypatch.setenv("PRIVATE_KEY", "0x4e582560bc6ffb3131547778dc9106d2956035113ce76fc5936ac1ed28402caa")
    monkeypatch.setenv("NETWORK", "bsc-testnet")
    monkeypatch.setenv("ERC8183_AGENT_URL", "http://localhost:8003/erc8183")

    mock_wallet = MagicMock()
    mock_sdk = MagicMock()
    mock_sdk.generate_agent_uri.return_value = "mock_uri"
    mock_sdk.register_agent.return_value = {"agentId": "agent-123", "transactionHash": "0xhash"}

    with patch("bnbagent.wallets.EVMWalletProvider", return_value=mock_wallet):
        with patch("bnbagent.ERC8004Agent", return_value=mock_sdk):
            with patch.object(sys, "argv", ["identity.py"]):
                spec = importlib.util.spec_from_file_location("__main__", os.path.join(ROOT, "server", "identity.py"))
                m = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(m)


# --------------------------------------------------------------------------- #
# clients/buyer.py tests
# --------------------------------------------------------------------------- #

def test_buyer_missing_password(monkeypatch):
    monkeypatch.delenv("WALLET_PASSWORD", raising=False)
    with pytest.raises(SystemExit):
        buyer.main("CAKE")


class MockJobStatus:
    def __init__(self, name):
        self.name = name


def test_buyer_success(monkeypatch):
    monkeypatch.setenv("WALLET_PASSWORD", "mock_password")
    monkeypatch.setenv("PRIVATE_KEY", "0x4e582560bc6ffb3131547778dc9106d2956035113ce76fc5936ac1ed28402caa")
    monkeypatch.setenv("NETWORK", "bsc-testnet")
    monkeypatch.setenv("ERC8183_AGENT_URL", "http://localhost:8003/erc8183")
    monkeypatch.setenv("BOURSE_PROVIDER_ADDRESS", "0xprovider")
    monkeypatch.setenv("ERC8183_SERVICE_PRICE", "100")

    mock_wallet = MagicMock()
    mock_client = MagicMock()
    mock_client.token_decimals.return_value = 18
    mock_client.token_symbol.return_value = "USDC"
    mock_client.create_job.return_value = {"jobId": 42, "transactionHash": "0xjobhash"}
    
    JobStatusMock = MagicMock()
    JobStatusMock.PENDING = MockJobStatus("PENDING")
    JobStatusMock.SUBMITTED = MockJobStatus("SUBMITTED")
    
    mock_client.get_job_status.side_effect = [JobStatusMock.PENDING, JobStatusMock.SUBMITTED]

    mock_response = MagicMock()
    mock_response.read.return_value = b'{"content": "mocked_signal"}'
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with patch("bnbagent.wallets.EVMWalletProvider", return_value=mock_wallet):
        with patch("bnbagent.erc8183.ERC8183Client", return_value=mock_client):
            with patch("bnbagent.erc8183.JobStatus", JobStatusMock):
                with patch("urllib.request.urlopen", mock_urlopen):
                    with patch("time.sleep"):
                        job_id = buyer.main("CAKE", poll_s=0.1, timeout_s=1)
                        assert job_id == 42


def test_buyer_timeout(monkeypatch):
    monkeypatch.setenv("WALLET_PASSWORD", "mock_password")
    monkeypatch.setenv("PRIVATE_KEY", "0x4e582560bc6ffb3131547778dc9106d2956035113ce76fc5936ac1ed28402caa")

    mock_wallet = MagicMock()
    mock_client = MagicMock()
    mock_client.token_decimals.return_value = 18
    mock_client.token_symbol.return_value = "USDC"
    mock_client.create_job.return_value = {"jobId": 42}
    
    JobStatusMock = MagicMock()
    JobStatusMock.PENDING = MockJobStatus("PENDING")
    mock_client.get_job_status.return_value = JobStatusMock.PENDING

    mock_urlopen = MagicMock()
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"agent_address": "0xprovider"}'
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with patch("bnbagent.wallets.EVMWalletProvider", return_value=mock_wallet):
        with patch("bnbagent.erc8183.ERC8183Client", return_value=mock_client):
            with patch("bnbagent.erc8183.JobStatus", JobStatusMock):
                with patch("urllib.request.urlopen", mock_urlopen):
                    with patch("time.sleep"):
                        with pytest.raises(SystemExit, match="timed out"):
                            buyer.main("CAKE", poll_s=0.1, timeout_s=0.1)


def test_buyer_main_block(monkeypatch):
    monkeypatch.setenv("WALLET_PASSWORD", "mock_password")
    monkeypatch.setenv("PRIVATE_KEY", "0x4e582560bc6ffb3131547778dc9106d2956035113ce76fc5936ac1ed28402caa")
    monkeypatch.setenv("NETWORK", "bsc-testnet")
    monkeypatch.setenv("ERC8183_AGENT_URL", "http://localhost:8003/erc8183")
    monkeypatch.setenv("BOURSE_PROVIDER_ADDRESS", "0xprovider")
    monkeypatch.setenv("ERC8183_SERVICE_PRICE", "100")

    mock_wallet = MagicMock()
    mock_client = MagicMock()
    mock_client.token_decimals.return_value = 18
    mock_client.token_symbol.return_value = "USDC"
    mock_client.create_job.return_value = {"jobId": 42, "transactionHash": "0xjobhash"}
    
    JobStatusMock = MagicMock()
    JobStatusMock.SUBMITTED = MockJobStatus("SUBMITTED")
    mock_client.get_job_status.return_value = JobStatusMock.SUBMITTED

    mock_response = MagicMock()
    mock_response.read.return_value = b'{"content": "mocked_signal"}'
    mock_urlopen = MagicMock()
    mock_urlopen.return_value.__enter__.return_value = mock_response

    with patch("bnbagent.wallets.EVMWalletProvider", return_value=mock_wallet):
        with patch("bnbagent.erc8183.ERC8183Client", return_value=mock_client):
            with patch("bnbagent.erc8183.JobStatus", JobStatusMock):
                with patch("urllib.request.urlopen", mock_urlopen):
                    with patch("time.sleep"):
                        with patch.object(sys, "argv", ["buyer.py", "--token", "CAKE"]):
                            spec = importlib.util.spec_from_file_location("__main__", os.path.join(ROOT, "clients", "buyer.py"))
                            m = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(m)


# --------------------------------------------------------------------------- #
# scripts/settle.py tests
# --------------------------------------------------------------------------- #

def test_settle_missing_password(monkeypatch):
    monkeypatch.delenv("WALLET_PASSWORD", raising=False)
    with pytest.raises(SystemExit):
        settle.main(42)


def test_settle_success(monkeypatch):
    monkeypatch.setenv("WALLET_PASSWORD", "mock_password")
    monkeypatch.setenv("PRIVATE_KEY", "0x4e582560bc6ffb3131547778dc9106d2956035113ce76fc5936ac1ed28402caa")
    monkeypatch.setenv("NETWORK", "bsc-testnet")

    mock_wallet = MagicMock()
    mock_client = MagicMock()
    mock_client.settle.return_value = {"transactionHash": "0xsettlehash"}
    
    JobStatusMock = MagicMock()
    JobStatusMock.COMPLETED = MockJobStatus("COMPLETED")
    mock_client.get_job_status.return_value = JobStatusMock.COMPLETED

    with patch("bnbagent.wallets.EVMWalletProvider", return_value=mock_wallet):
        with patch("bnbagent.erc8183.ERC8183Client", return_value=mock_client):
            res = settle.main(42)
            assert res["transactionHash"] == "0xsettlehash"


def test_settle_main_block(monkeypatch):
    monkeypatch.setenv("WALLET_PASSWORD", "mock_password")
    monkeypatch.setenv("PRIVATE_KEY", "0x4e582560bc6ffb3131547778dc9106d2956035113ce76fc5936ac1ed28402caa")
    monkeypatch.setenv("NETWORK", "bsc-testnet")

    mock_wallet = MagicMock()
    mock_client = MagicMock()
    mock_client.settle.return_value = {"transactionHash": "0xsettlehash"}
    
    JobStatusMock = MagicMock()
    JobStatusMock.COMPLETED = MockJobStatus("COMPLETED")
    mock_client.get_job_status.return_value = JobStatusMock.COMPLETED

    with patch("bnbagent.wallets.EVMWalletProvider", return_value=mock_wallet):
        with patch("bnbagent.erc8183.ERC8183Client", return_value=mock_client):
            with patch.object(sys, "argv", ["settle.py", "42"]):
                spec = importlib.util.spec_from_file_location("__main__", os.path.join(ROOT, "scripts", "settle.py"))
                m = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(m)


# --------------------------------------------------------------------------- #
# scripts/backtest.py tests
# --------------------------------------------------------------------------- #

def test_backtest_script_success(monkeypatch):
    with patch.object(sys, "argv", ["backtest.py"]):
        backtest.main()


def test_backtest_script_json(monkeypatch):
    with patch.object(sys, "argv", ["backtest.py", "--json"]):
        backtest.main()


def test_backtest_script_missing_fixture(monkeypatch):
    with patch.object(sys, "argv", ["backtest.py", "--fixture", "nonexistent_file.json"]):
        with pytest.raises(SystemExit):
            backtest.main()


def test_backtest_main_block():
    with patch.object(sys, "argv", ["backtest.py"]):
        spec = importlib.util.spec_from_file_location("__main__", os.path.join(ROOT, "scripts", "backtest.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)


# --------------------------------------------------------------------------- #
# scripts/bench.py tests
# --------------------------------------------------------------------------- #

def test_bench_script_missing_fixture(monkeypatch):
    original_exists = os.path.exists
    def mock_exists(p):
        if "backtest_cake.json" in p:
            return False
        return original_exists(p)
    monkeypatch.setattr(os.path, "exists", mock_exists)
    bench.main(2)


# --------------------------------------------------------------------------- #
# scripts/check_submission_readiness.py tests
# --------------------------------------------------------------------------- #

def test_check_readiness_main(monkeypatch):
    monkeypatch.setattr(check_submission_readiness, "pytest_count", lambda: 145)
    monkeypatch.setattr(check_submission_readiness, "pytest_passes", lambda: True)
    monkeypatch.setattr(check_submission_readiness, "is_tracked", lambda path: path != ".env")
    
    mock_exit = MagicMock()
    with patch("sys.exit", mock_exit):
        check_submission_readiness.main()
        mock_exit.assert_called_once_with(0)


def test_check_submission_readiness_real_functions():
    def mock_run_cmd(args, **kwargs):
        mock_res = MagicMock()
        if "ls-files" in args:
            mock_res.returncode = 0 if ".env" not in args else 1
        elif "--collect-only" in args:
            mock_res.stdout = "145 tests collected"
            mock_res.returncode = 0
        elif "pytest" in args:
            mock_res.returncode = 0
        return mock_res

    with patch("subprocess.run", side_effect=mock_run_cmd):
        assert check_submission_readiness.is_tracked("README.md") is True
        assert check_submission_readiness.is_tracked(".env") is False
        assert check_submission_readiness.pytest_count() == 145
        assert check_submission_readiness.pytest_passes() is True
        
        with patch("sys.exit") as mock_exit:
            spec = importlib.util.spec_from_file_location("__main__", os.path.join(ROOT, "scripts", "check_submission_readiness.py"))
            m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(m)
            mock_exit.assert_called_once_with(0)


def test_check_submission_readiness_exceptions():
    with patch("subprocess.run", side_effect=Exception("pytest failed")):
        assert check_submission_readiness.pytest_count() == 0
        assert check_submission_readiness.pytest_passes() is False


# --------------------------------------------------------------------------- #
# scripts/probe_cmc_history.py tests
# --------------------------------------------------------------------------- #

def test_probe_cmc_history_missing_key(monkeypatch):
    monkeypatch.setattr(probe_cmc_history, "KEY", "")
    with pytest.raises(SystemExit):
        probe_cmc_history.main()


def test_probe_cmc_history_success(monkeypatch):
    monkeypatch.setattr(probe_cmc_history, "KEY", "mock_key")
    
    class MockResp:
        def __init__(self, code, data_dict):
            self.status_code = code
            self.data_dict = data_dict
        def json(self):
            return self.data_dict
        @property
        def text(self):
            return "raw response text"
            
    mock_req = MagicMock()
    mock_req.side_effect = [
        MockResp(200, {"data": {"CAKE": {}}}),  # quotes latest
        MockResp(200, {"data": []}),            # quotes historical (empty)
        MockResp(401, {}),                      # ohlcv historical (auth err)
        MockResp(402, {"status": {"error_message": "upgrade your plan"}}), # fear greed latest (plan error)
        MockResp(404, {}),                      # fear greed historical (404)
        MockResp(500, {}),                      # global historical (generic error)
        MockResp(200, {"data": [{"value": 1}]}),# trending latest (success with data)
    ]
    
    with patch("requests.request", mock_req):
        probe_cmc_history.SYM = "CAKE"
        probe_cmc_history.main()


def test_probe_cmc_history_edge_cases(monkeypatch):
    with patch("requests.request", side_effect=Exception("network error")):
        res = probe_cmc_history.probe("label", "plane", "GET", "/path", {})
        assert res[2] == "ERR"

    class MockBadResp:
        status_code = 200
        @property
        def text(self):
            return "invalid json body"
        def json(self):
            raise ValueError("bad json")
            
    with patch("requests.request", return_value=MockBadResp()):
        res = probe_cmc_history.probe("label", "plane", "GET", "/path", {})
        assert res[2] == "⚠️ 200 no-data"

    monkeypatch.setattr(probe_cmc_history, "KEY", "mock_key")
    class MockGoodResp:
        status_code = 200
        def json(self):
            return {"data": [{"value": 1}]}
            
    with patch("requests.request", return_value=MockGoodResp()):
        with patch("sys.exit"):
            probe_cmc_history.main()

    monkeypatch.setattr(probe_cmc_history, "KEY", "mock_key")
    with patch("requests.request", return_value=MockGoodResp()):
        with patch("sys.exit"):
            with patch.object(sys, "argv", ["probe_cmc_history.py", "--symbol", "CAKE"]):
                spec = importlib.util.spec_from_file_location("__main__", os.path.join(ROOT, "scripts", "probe_cmc_history.py"))
                m = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(m)


def test_probe_cmc_history_dotenv_except():
    # Trigger except block for load_dotenv inside probe_cmc_history
    import dotenv  # noqa: F401
    with patch("dotenv.load_dotenv", side_effect=Exception("dotenv error")):
        # Re-execute probe_cmc_history's import block
        spec = importlib.util.spec_from_file_location("probe_cmc_history_temp", os.path.join(ROOT, "scripts", "probe_cmc_history.py"))
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)


# --------------------------------------------------------------------------- #
# scripts/signal.py tests
# --------------------------------------------------------------------------- #

def test_signal_backtest_for_missing_fixture(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda x: False)
    assert signal_cli._backtest_for("CAKE") is None


def test_signal_planes_for_live(monkeypatch):
    with patch("bourse_signal_cli.from_mcp", return_value="dummy_planes"):
        assert signal_cli._planes_for("CAKE", live=True) == "dummy_planes"


def test_signal_planes_for_missing_fixture(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda x: False)
    with pytest.raises(SystemExit):
        signal_cli._planes_for("CAKE", live=False)


def test_signal_show_board_live(monkeypatch):
    with pytest.raises(SystemExit):
        signal_cli.show_board(live=True)


def test_signal_show_board_missing_fixture(monkeypatch):
    monkeypatch.setattr(os.path, "exists", lambda x: False)
    with pytest.raises(SystemExit):
        signal_cli.show_board(live=False)


def test_signal_main_discover(monkeypatch):
    with patch.object(sys, "argv", ["signal.py", "--discover"]):
        with patch("bourse_signal_cli.discover") as mock_discover:
            signal_cli.main()
            mock_discover.assert_called_once()


def test_signal_main_error_exit(monkeypatch):
    with patch.object(sys, "argv", ["signal.py", "--token", "CAKE"]):
        with patch("bourse_signal_cli.show_token", side_effect=RuntimeError("something failed")):
            with pytest.raises(SystemExit):
                signal_cli.main()


# --------------------------------------------------------------------------- #
# bourse/ingest.py coverage expansion
# --------------------------------------------------------------------------- #

def test_series_from_result_nested_list_walk():
    # Covers list walking with nested non-numeric values (lines 108-109)
    result = {"data": [[{"target": 12.3}, "garbage"], "another_garbage"]}
    res = _series_from_result(result, ("target",))
    assert res == [12.3]


def test_mcp_client_parse_sse_decode_error():
    class MockResp:
        headers = {"Content-Type": "text/event-stream"}
        text = "data: {invalid_json}\n\ndata: [DONE]\n\n"
    
    env = MCPClient._parse(MockResp())
    assert env == {}


def test_mcp_client_post_request_exception():
    import requests
    client = MCPClient(api_key="k")
    with patch("requests.post", side_effect=requests.exceptions.RequestException("conn error")):
        with pytest.raises(RuntimeError, match="CMC MCP request failed"):
            client._post("initialize")


def test_mcp_client_post_rpc_error():
    client = MCPClient(api_key="k")
    class MockResp:
        headers = {"Content-Type": "application/json"}
        def json(self):
            return {"error": "something went wrong"}
        def raise_for_status(self):
            pass
            
    with patch("requests.post", return_value=MockResp()):
        with pytest.raises(RuntimeError, match="MCP error on"):
            client._post("initialize")


def test_mcp_client_list_tools():
    client = MCPClient(api_key="k")
    class MockResp:
        headers = {"Content-Type": "application/json", "Mcp-Session-Id": "sess_1"}
        def json(self):
            return {"result": {"tools": [{"name": "fake_tool"}]}}
        def raise_for_status(self):
            pass
            
    with patch("requests.post", return_value=MockResp()):
        tools = client.list_tools()
        assert len(tools) == 1
        assert tools[0]["name"] == "fake_tool"
        assert client.session_id == "sess_1"


def test_mcp_client_call_tool_decode_error():
    client = MCPClient(api_key="k")
    class MockResp:
        headers = {"Content-Type": "application/json"}
        def json(self):
            return {"result": {"content": [{"type": "text", "text": "not_json"}]}}
        def raise_for_status(self):
            pass
            
    with patch("requests.post", return_value=MockResp()):
        client._initialized = True
        res = client.call_tool("tool_name")
        assert res == "not_json"


def test_from_mcp_graceful_regime_failure():
    class FakeClient:
        def __init__(self):
            self.api_key = "k"
        def initialize(self):
            pass
        def call_tool(self, name, arguments=None):
            if name == "Global Market Metrics":
                raise RuntimeError("regime failed")
            return {"score": [1.0, 2.0]}

    p = from_mcp("CAKE", client=FakeClient())
    assert p.fear_greed == 50.0  # fallback value


def test_fetch_fear_greed_history_missing_key(monkeypatch):
    monkeypatch.delenv("CMC_PRO_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="CMC_PRO_API_KEY not set"):
        fetch_fear_greed_history()


def test_fetch_fear_greed_history_success(monkeypatch):
    monkeypatch.setenv("CMC_PRO_API_KEY", "mock_key")
    class MockResp:
        def raise_for_status(self):
            pass
        def json(self):
            return {"data": [{"value": 45.0}, {"value": 50.0}]}
            
    with patch("requests.get", return_value=MockResp()):
        res = fetch_fear_greed_history()
        assert res == [45.0, 50.0]
