# ruff: noqa: E402
import sys
import os
from unittest.mock import MagicMock, patch

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from scripts import check_submission_readiness
from scripts import run_terminal_demo



# --------------------------------------------------------------------------- #
# scripts/check_submission_readiness.py additional coverage
# --------------------------------------------------------------------------- #

def test_update_readme_test_count_additional():
    # 1. Test collected <= 0
    check_submission_readiness.update_readme_test_count(0)
    
    # 2. Test README not existing
    with patch("os.path.exists", return_value=False):
        check_submission_readiness.update_readme_test_count(10)
        
    # 3. Test update succeeds
    mock_file_content = "pytest-5_passing\npytest (5 tests)"
    class MockFileObj:
        def __init__(self):
            self.written = ""
        def read(self):
            return mock_file_content
        def write(self, data):
            self.written = data
        def __enter__(self):
            return self
        def __exit__(self, *exc):
            pass
            
    mock_file = MockFileObj()
    original_open = open
    def mock_open(file, mode="r", *args, **kwargs):
        if "README.md" in str(file):
            return mock_file
        return original_open(file, mode, *args, **kwargs)
        
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open):
            check_submission_readiness.update_readme_test_count(10)
            
    assert "pytest-10_passing" in mock_file.written
    assert "pytest (10 tests)" in mock_file.written


# --------------------------------------------------------------------------- #
# scripts/run_terminal_demo.py tests
# --------------------------------------------------------------------------- #

def test_run_terminal_demo_dotenv_import_error():
    import builtins
    orig_import = builtins.__import__
    def mock_import(name, *args, **kwargs):
        if name == "dotenv":
            raise ImportError("mocked import error")
        return orig_import(name, *args, **kwargs)
        
    had_dotenv = "dotenv" in sys.modules
    old_dotenv = sys.modules.get("dotenv")
    if had_dotenv:
        del sys.modules["dotenv"]
        
    with patch("builtins.__import__", mock_import):
        import runpy
        # Run module setup to cover try-except block
        runpy.run_path("scripts/run_terminal_demo.py", run_name="not_main")
        
    if had_dotenv:
        sys.modules["dotenv"] = old_dotenv


def test_run_terminal_demo_is_port_in_use():
    mock_socket = MagicMock()
    mock_socket.__enter__.return_value = mock_socket
    # Port in use (0)
    mock_socket.connect_ex.return_value = 0
    with patch("socket.socket", return_value=mock_socket):
        assert run_terminal_demo.is_port_in_use(8003) is True
        
    # Port not in use (non-zero)
    mock_socket.connect_ex.return_value = 111
    with patch("socket.socket", return_value=mock_socket):
        assert run_terminal_demo.is_port_in_use(8003) is False


def test_run_terminal_demo_type_command():
    with patch("time.sleep") as mock_sleep:
        run_terminal_demo.type_command("echo test")
        mock_sleep.assert_called_once_with(0.5)


def test_run_terminal_demo_run_cmd_and_stream(monkeypatch):
    monkeypatch.delenv("WALLET_PASSWORD", raising=False)
    monkeypatch.delenv("PRIVATE_KEY", raising=False)
    monkeypatch.delenv("NETWORK", raising=False)
    
    mock_proc = MagicMock()
    mock_proc.poll.return_value = 0
    mock_proc.stdout.readline.side_effect = ["line1\n", ""]
    mock_proc.wait.return_value = 0
    mock_proc.returncode = 0
    
    with patch("subprocess.Popen", return_value=mock_proc) as mock_popen:
        code = run_terminal_demo.run_cmd_and_stream(["some", "cmd"])
        assert code == 0
        mock_popen.assert_called_once()
        called_env = mock_popen.call_args[1]["env"]
        assert called_env["WALLET_PASSWORD"] == "secret"
        # PRIVATE_KEY is never hard-coded: absent from env -> absent from the child env
        assert "PRIVATE_KEY" not in called_env
        assert called_env["NETWORK"] == "bsc-testnet"
        
    # Test with existing env vars + stdout is None
    monkeypatch.setenv("WALLET_PASSWORD", "custom_pass")
    monkeypatch.setenv("PRIVATE_KEY", "custom_key")
    monkeypatch.setenv("NETWORK", "custom_net")
    
    mock_proc2 = MagicMock()
    mock_proc2.poll.return_value = 0
    mock_proc2.stdout = None
    mock_proc2.wait.return_value = 1
    mock_proc2.returncode = 1
    
    with patch("subprocess.Popen", return_value=mock_proc2) as mock_popen2:
        code = run_terminal_demo.run_cmd_and_stream(["some", "cmd"])
        assert code == 1
        called_env2 = mock_popen2.call_args[1]["env"]
        assert called_env2["WALLET_PASSWORD"] == "custom_pass"
        assert called_env2["PRIVATE_KEY"] == "custom_key"
        assert called_env2["NETWORK"] == "custom_net"


def test_run_terminal_demo_main_starts_server_success(monkeypatch):
    monkeypatch.delenv("WALLET_PASSWORD", raising=False)
    monkeypatch.delenv("PRIVATE_KEY", raising=False)
    monkeypatch.delenv("NETWORK", raising=False)

    is_port_in_use_mock = MagicMock(side_effect=[False, False, True])
    monkeypatch.setattr(run_terminal_demo, "is_port_in_use", is_port_in_use_mock)
    
    mock_server_proc = MagicMock()
    mock_popen = MagicMock(return_value=mock_server_proc)
    monkeypatch.setattr(run_terminal_demo.subprocess, "Popen", mock_popen)
    
    mock_run_stream = MagicMock(return_value=0)
    monkeypatch.setattr(run_terminal_demo, "run_cmd_and_stream", mock_run_stream)
    
    mock_sleep = MagicMock()
    monkeypatch.setattr(run_terminal_demo.time, "sleep", mock_sleep)
    
    mock_system = MagicMock()
    monkeypatch.setattr(run_terminal_demo.os, "system", mock_system)
    
    run_terminal_demo.main()
    
    mock_popen.assert_called_once()
    called_env = mock_popen.call_args[1]["env"]
    assert called_env["WALLET_PASSWORD"] == "secret"
    # PRIVATE_KEY is never hard-coded: absent from env -> absent from the child env
    assert "PRIVATE_KEY" not in called_env
    assert called_env["NETWORK"] == "bsc-testnet"

    assert mock_run_stream.call_count == 3
    mock_server_proc.terminate.assert_called_once()
    mock_server_proc.wait.assert_called_once()


def test_run_terminal_demo_main_starts_server_timeout(monkeypatch):
    is_port_in_use_mock = MagicMock(return_value=False)
    monkeypatch.setattr(run_terminal_demo, "is_port_in_use", is_port_in_use_mock)
    
    mock_server_proc = MagicMock()
    mock_popen = MagicMock(return_value=mock_server_proc)
    monkeypatch.setattr(run_terminal_demo.subprocess, "Popen", mock_popen)
    
    mock_run_stream = MagicMock(return_value=0)
    monkeypatch.setattr(run_terminal_demo, "run_cmd_and_stream", mock_run_stream)
    
    mock_sleep = MagicMock()
    monkeypatch.setattr(run_terminal_demo.time, "sleep", mock_sleep)
    
    mock_system = MagicMock()
    monkeypatch.setattr(run_terminal_demo.os, "system", mock_system)
    
    run_terminal_demo.main()
    
    mock_server_proc.terminate.assert_called_once()


def test_run_terminal_demo_main_server_already_running(monkeypatch):
    is_port_in_use_mock = MagicMock(return_value=True)
    monkeypatch.setattr(run_terminal_demo, "is_port_in_use", is_port_in_use_mock)
    
    mock_popen = MagicMock()
    monkeypatch.setattr(run_terminal_demo.subprocess, "Popen", mock_popen)
    
    mock_run_stream = MagicMock(return_value=0)
    monkeypatch.setattr(run_terminal_demo, "run_cmd_and_stream", mock_run_stream)
    
    mock_sleep = MagicMock()
    monkeypatch.setattr(run_terminal_demo.time, "sleep", mock_sleep)
    
    mock_system = MagicMock()
    monkeypatch.setattr(run_terminal_demo.os, "system", mock_system)
    
    run_terminal_demo.main()
    
    mock_popen.assert_not_called()


def test_run_terminal_demo_main_block(monkeypatch):
    # Mock socket.socket connect_ex to return 0 (port in use, so it doesn't start the server)
    mock_socket = MagicMock()
    mock_socket.__enter__.return_value = mock_socket
    mock_socket.connect_ex.return_value = 0
    
    # Mock Popen to return a fresh mock process each time
    def mock_popen_func(*args, **kwargs):
        p = MagicMock()
        p.poll.return_value = 0
        p.stdout.readline.side_effect = ["line1\n", ""]
        p.wait.return_value = 0
        p.returncode = 0
        return p
    
    with patch("socket.socket", return_value=mock_socket), \
         patch("subprocess.Popen", side_effect=mock_popen_func) as mock_popen, \
         patch("time.sleep") as mock_sleep, \
         patch("os.system") as mock_system:
         
        import runpy
        runpy.run_path("scripts/run_terminal_demo.py", run_name="__main__")
        
        # Verify that Popen was called (for signal.py, optimize_weights.py, buyer.py)
        assert mock_popen.call_count == 3
        # Verify time.sleep was called
        assert mock_sleep.call_count > 0
        # Verify os.system was called
        assert mock_system.call_count > 0

