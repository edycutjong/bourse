#!/usr/bin/env python3
"""
Bourse stdio MCP server wrapper.
Allows Claude Desktop (and other MCP clients) to interact with Bourse's 
divergence signal and backtesting engine over a stdio JSON-RPC connection.
"""
import sys
import os
import json
import traceback
from dotenv import load_dotenv

# Ensure bourse package can be imported
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

# Load environment variables from absolute path
dotenv_path = os.path.join(ROOT, ".env")
load_dotenv(dotenv_path=dotenv_path)

from bourse import Planes, build_spec, compute, run_backtest, to_yaml
from bourse.ingest import from_fixture, from_mcp

DEMO_FIX = os.path.join(ROOT, "data", "fixtures", "demo.json")
BT_FIX = os.path.join(ROOT, "data", "fixtures", "backtest_cake.json")

def log(msg: str):
    """Log helper writing to stderr so we don't pollute stdout JSON-RPC stream."""
    sys.stderr.write(f"[bourse-mcp] {msg}\n")
    sys.stderr.flush()

def send_response(response: dict):
    """Send JSON-RPC response over stdout."""
    out = json.dumps(response)
    sys.stdout.write(out + "\n")
    sys.stdout.flush()

def _spark(curve):
    """ASCII Sparkline for backtest equity visualization."""
    blocks = "▁▂▃▄▅▆▇█"
    lo, hi = min(curve), max(curve)
    rng = (hi - lo) or 1.0
    return "".join(blocks[min(7, int((x - lo) / rng * 7))] for x in curve)

def handle_get_divergence_board(arguments):
    live = arguments.get("live", False)
    if live:
        return "Live board view is not supported directly without token symbols. Please specify a specific token and run live, or check the fixture board."

    if not os.path.exists(DEMO_FIX):
        return "no fixtures — please run 'python scripts/seed.py' first."

    with open(DEMO_FIX) as f:
        tokens = json.load(f).keys()

    rows = []
    for t in tokens:
        try:
            p = from_fixture(t, DEMO_FIX)
            rows.append(compute(t, p))
        except Exception as e:
            log(f"Error computing board token {t}: {e}")

    rows.sort(key=lambda s: abs(s.divergence), reverse=True)

    ARROW = {"short": "▼ SHORT/FADE", "long": "▲ LONG/ACCUM", "none": "— no-trade"}

    lines = []
    lines.append(f"{'TOKEN':<7}{'DIV':>7}  {'REGIME':<14}{'SIGNAL':<14}CONF")
    lines.append("-" * 52)
    for s in rows:
        lines.append(f"{s.token:<7}{s.divergence:>+7.1f}  {s.regime:<14}"
                     f"{ARROW.get(s.direction, s.direction):<14}{s.confidence*100:>3.0f}%")
    lines.append("\nRun `get_token_signal` on a specific token for details.")
    return "\n".join(lines)

def handle_get_token_signal(arguments):
    token = arguments.get("token", "").upper()
    live = arguments.get("live", False)
    if not token:
        return "Error: token argument is required."

    try:
        if live:
            p = from_mcp(token)
        else:
            if not os.path.exists(DEMO_FIX):
                return "no fixtures — please run 'python scripts/seed.py' first."
            p = from_fixture(token, DEMO_FIX)
    except KeyError:
        return f"Error: no fixture data for token {token!r}. Available fixture tokens are: CAKE, XYZL, ABCN."
    except Exception as e:
        return f"Error loading planes for {token}: {str(e)}"

    sig = compute(token, p)

    backtest_data = None
    if os.path.exists(BT_FIX):
        try:
            with open(BT_FIX) as f:
                history = json.load(f)
            m = run_backtest(history, token=token)
            backtest_data = {"sharpe": m["sharpe"], "max_dd": m["max_dd"], "win_rate": m["win_rate"]}
        except Exception as e:
            log(f"Backtest error for {token}: {e}")

    spec = build_spec(sig, backtest=backtest_data)

    src = "CMC MCP (live)" if live else "fixture"
    ARROW = {"short": "▼ SHORT/FADE", "long": "▲ LONG/ACCUM", "none": "— no-trade"}

    lines = []
    lines.append(f"Bourse — {token}  [{src}]\n")
    lines.append(f"  divergence : {sig.divergence:+.1f}   regime: {sig.regime}   "
                 f"signal: {ARROW.get(sig.direction, sig.direction)}")
    lines.append(f"  confidence : {sig.confidence*100:.0f}%   (crowd {sig.crowd:+.2f} / "
                 f"smart {sig.smart:+.2f})")
    lines.append("  why        : " + (" · ".join(sig.reasons) or "no plane crossed threshold"))
    lines.append("\n--- bourse.signal.v1 ---")
    lines.append(to_yaml(spec))
    return "\n".join(lines)

def handle_run_backtest(arguments):
    token = arguments.get("token", "").upper()
    if not token:
        return "Error: token argument is required."

    if not os.path.exists(BT_FIX):
        return "Error: backtest fixture not found."

    try:
        with open(BT_FIX) as f:
            history = json.load(f)
        m = run_backtest(history, token=token)
    except Exception as e:
        return f"Error running backtest for {token}: {str(e)}"

    lines = []
    lines.append(f"Bourse backtest -- {token} ({len(history['price'])} days)\n")
    lines.append(f"  Sharpe (ann.) : {m['sharpe']:.2f}" if isinstance(m['sharpe'], float) else f"  Sharpe (ann.) : {m['sharpe']}")
    lines.append(f"  max drawdown  : {m['max_dd'] * 100:.1f}%")
    lines.append(f"  win rate      : {m['win_rate'] * 100:.1f}%")
    lines.append(f"  trades        : {m['n_trades']}  (active steps {m['n_active']})")
    lines.append(f"  total return  : {m['final_return'] * 100:+.1f}%")
    lines.append(f"  equity        : {_spark(m['equity_curve'])}")
    return "\n".join(lines)

def main_loop():
    log("Bourse MCP server starting...")
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break
            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                log(f"Invalid JSON received: {e}")
                send_response({
                    "jsonrpc": "2.0",
                    "error": {"code": -32700, "message": "Parse error"},
                    "id": None
                })
                continue

            method = request.get("method")
            msg_id = request.get("id")

            if method == "initialize":
                send_response({
                    "jsonrpc": "2.0",
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {
                            "tools": {}
                        },
                        "serverInfo": {
                            "name": "bourse-mcp",
                            "version": "0.1.0"
                        }
                    },
                    "id": msg_id
                })
            elif method == "notifications/initialized":
                pass
            elif method == "tools/list":
                send_response({
                    "jsonrpc": "2.0",
                    "result": {
                        "tools": [
                            {
                                "name": "get_divergence_board",
                                "description": "Get the ranked divergence board for all tracked tokens, showing divergence signals, regime, and confidence.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "live": {
                                            "type": "boolean",
                                            "description": "Whether to fetch live data from CoinMarketCap MCP (requires API key in environment) or use deterministic fixture data.",
                                            "default": False
                                        }
                                    }
                                }
                            },
                            {
                                "name": "get_token_signal",
                                "description": "Get detailed crowd-vs-smart-money divergence signal, why it fired, the bourse.signal.v1 spec, and backtest stats for a specific token (e.g. CAKE).",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "token": {
                                            "type": "string",
                                            "description": "The token symbol to analyze (e.g., CAKE)"
                                        },
                                        "live": {
                                            "type": "boolean",
                                            "description": "Whether to fetch live data from CoinMarketCap MCP (requires API key in environment) or use deterministic fixture data.",
                                            "default": False
                                        }
                                    },
                                    "required": ["token"]
                                }
                            },
                            {
                                "name": "run_backtest",
                                "description": "Run the historical backtest for a specific token and return Sharpe ratio, max drawdown, and win rate.",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "token": {
                                            "type": "string",
                                            "description": "The token symbol to backtest (e.g., CAKE)"
                                        }
                                    },
                                    "required": ["token"]
                                }
                            }
                        ]
                    },
                    "id": msg_id
                })
            elif method == "tools/call":
                params = request.get("params", {})
                name = params.get("name")
                arguments = params.get("arguments", {})

                if name == "get_divergence_board":
                    output = handle_get_divergence_board(arguments)
                elif name == "get_token_signal":
                    output = handle_get_token_signal(arguments)
                elif name == "run_backtest":
                    output = handle_run_backtest(arguments)
                else:
                    output = f"Unknown tool: {name}"

                send_response({
                    "jsonrpc": "2.0",
                    "result": {
                        "content": [
                            {
                                "type": "text",
                                "text": output
                            }
                        ]
                    },
                    "id": msg_id
                })
            elif msg_id is not None:
                send_response({
                    "jsonrpc": "2.0",
                    "error": {"code": -32601, "message": f"Method not found: {method}"},
                    "id": msg_id
                })
        except Exception as e:
            log(f"Exception in loop: {traceback.format_exc()}")

if __name__ == "__main__":
    # Make script executable via chmod if needed
    main_loop()
