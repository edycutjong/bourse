#!/usr/bin/env python3
import os
import sys
import time
import socket
import subprocess

# Add project root to path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def type_command(cmd: str):
    print("\n\033[1;32m$ " + cmd + "\033[0m", flush=True)
    time.sleep(0.5)

def demo_env() -> dict:
    """Build the child-process environment for the demo.

    Secrets are NEVER hard-coded here: PRIVATE_KEY must come from the environment / .env
    (see .env.example). Only non-sensitive demo defaults are filled in. If no key is set,
    the on-chain settlement beat is skipped with a clear hint rather than signing with a
    committed key.
    """
    env = os.environ.copy()
    env.setdefault("WALLET_PASSWORD", "secret")  # local keystore password, not a chain secret
    env.setdefault("NETWORK", "bsc-testnet")
    if "PRIVATE_KEY" not in env and "AGENT_PRIVATE_KEY" not in env:
        print("\033[1;33m⚠️  PRIVATE_KEY not set — on-chain beats will be skipped. "
              "Add it to .env (see .env.example) to run settlement.\033[0m", flush=True)
    return env

def run_cmd_and_stream(args: list[str], cwd: str = ROOT):
    env = demo_env()
    p = subprocess.Popen(
        args,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        cwd=cwd,
        env=env
    )
    
    # Read output line by line in real-time
    if p.stdout is not None:
        while True:
            line = p.stdout.readline()
            if not line and p.poll() is not None:
                break
            if line:
                print(line, end="", flush=True)
            
    p.wait()
    return p.returncode

def main():
    print("\033[1;36m============================================================\033[0m")
    print("\033[1;36m🎬 Bourse — Terminal Walkthrough Automation\033[0m")
    print("\033[1;36m============================================================\033[0m")
    
    server_proc = None
    server_port = 8003
    
    # 1. Manage server background process
    if not is_port_in_use(server_port):
        print("\n⚙️  Bourse server is not running on port 8003. Starting it now...")
        env = demo_env()
        server_proc = subprocess.Popen(
            [sys.executable, "server/app.py", "--serve"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env
        )
        # Wait for server to start
        print("⏳ Waiting for server to initialize...")
        for _ in range(10):
            time.sleep(1)
            if is_port_in_use(server_port):
                print("✅ Server is active and listening on port 8003!")
                break
        else:
            print("❌ Warning: Timeout waiting for port 8003 to open.")
    else:
        print("\n✅ Bourse server is already running on port 8003.")
        
    try:
        # --- Beat 2: signal.py ---
        os.system("clear")
        print("\033[1;34m--- Beat 2: Running Divergence Signal CLI ---\033[0m")
        cmd_args1 = [sys.executable, "scripts/signal.py", "--token", "CAKE"]
        type_command("python scripts/signal.py --token CAKE")
        run_cmd_and_stream(cmd_args1)
        time.sleep(3)
        
        # --- Beat 3: optimize_weights.py ---
        os.system("clear")
        print("\033[1;34m--- Beat 3: Running Weights Optimizer ---\033[0m")
        cmd_args2 = [sys.executable, "scripts/optimize_weights.py"]
        type_command("python scripts/optimize_weights.py")
        run_cmd_and_stream(cmd_args2)
        time.sleep(3)
        
        # --- Beat 4: clients/buyer.py ---
        os.system("clear")
        print("\033[1;34m--- Beat 4: Running Programmatic Escrow Buyer Agent ---\033[0m")
        cmd_args3 = [sys.executable, "clients/buyer.py", "--token", "CAKE"]
        type_command("python clients/buyer.py --token CAKE")
        run_cmd_and_stream(cmd_args3)
        time.sleep(2)
        
        print("\n\033[1;32m🎉 Walkthrough complete!\033[0m")
        
    finally:
        # Cleanup server if we started it
        if server_proc:
            print("\n🧹 Stopping background server...")
            server_proc.terminate()
            server_proc.wait()
            print("🛑 Server stopped.")

if __name__ == "__main__":
    main()
