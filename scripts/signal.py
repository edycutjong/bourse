#!/usr/bin/env python3
"""
Bourse signal CLI — run the Skill end-to-end from the terminal.

  python scripts/signal.py                  # ranked divergence board (all fixture tokens)
  python scripts/signal.py --token CAKE     # one token: 4-plane "why" + bourse.signal.v1 + backtest
  python scripts/signal.py --token CAKE --live   # pull planes live from the CMC MCP
  python scripts/signal.py --discover       # list the live CMC MCP tools (needs CMC_MCP_API_KEY)
  python scripts/signal.py --token CAKE --json   # machine-readable spec

Fixture mode is deterministic and offline (reproduces the demo exactly). `--live`
routes through `bourse.ingest.from_mcp`; planes that the MCP can't supply are
greyed out via the engine's coverage gate rather than faked.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bourse import Planes, build_spec, compute, run_backtest, to_yaml
from bourse.ingest import from_fixture, from_mcp

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DEMO_FIX = os.path.join(ROOT, "data", "fixtures", "demo.json")
BT_FIX = os.path.join(ROOT, "data", "fixtures", "backtest_cake.json")

ARROW = {"short": "▼ SHORT/FADE", "long": "▲ LONG/ACCUM", "none": "— no-trade"}


def _backtest_for(token: str) -> dict | None:
    if not os.path.exists(BT_FIX):
        return None
    with open(BT_FIX) as f:
        history = json.load(f)
    m = run_backtest(history, token=token)
    return {"sharpe": m["sharpe"], "max_dd": m["max_dd"], "win_rate": m["win_rate"]}


def _planes_for(token: str, live: bool) -> Planes:
    if live:
        return from_mcp(token)
    if not os.path.exists(DEMO_FIX):
        sys.exit("no fixtures — run: python scripts/seed.py")
    try:
        return from_fixture(token, DEMO_FIX)
    except KeyError:
        sys.exit(f"no fixture data for {token!r} (have: see data/fixtures/demo.json)")


def show_board(live: bool) -> None:
    if live:
        sys.exit("--live needs a --token (the board is the offline fixture set)")
    if not os.path.exists(DEMO_FIX):
        sys.exit("no fixtures — run: python scripts/seed.py")
    with open(DEMO_FIX) as f:
        tokens = json.load(f).keys()
    rows = [compute(t, _planes_for(t, live=False)) for t in tokens]
    rows.sort(key=lambda s: abs(s.divergence), reverse=True)
    print(f"{'TOKEN':<7}{'DIV':>7}  {'REGIME':<14}{'SIGNAL':<14}CONF")
    print("-" * 52)
    for s in rows:
        print(f"{s.token:<7}{s.divergence:>+7.1f}  {s.regime:<14}"
              f"{ARROW.get(s.direction, s.direction):<14}{s.confidence*100:>3.0f}%")
    print("\nrun `--token <SYM>` for the full why + spec + backtest")


def show_token(token: str, live: bool, as_json: bool) -> None:
    sig = compute(token, _planes_for(token, live))
    spec = build_spec(sig, backtest=_backtest_for(token))
    if as_json:
        print(json.dumps(spec, indent=2))
        return
    src = "CMC MCP (live)" if live else "fixture"
    print(f"Bourse — {token}  [{src}]\n")
    print(f"  divergence : {sig.divergence:+.1f}   regime: {sig.regime}   "
          f"signal: {ARROW.get(sig.direction, sig.direction)}")
    print(f"  confidence : {sig.confidence*100:.0f}%   (crowd {sig.crowd:+.2f} / "
          f"smart {sig.smart:+.2f})")
    print("  why        : " + (" · ".join(sig.reasons) or "no plane crossed threshold"))
    print("\n--- bourse.signal.v1 ---")
    print(to_yaml(spec))


def discover() -> None:
    from bourse.ingest import MCPClient

    tools = MCPClient().list_tools()
    print(f"CMC MCP exposes {len(tools)} tools:\n")
    for t in tools:
        print(f"  - {t.get('name')}: {t.get('description', '')[:80]}")


def main() -> None:
    ap = argparse.ArgumentParser(description="Bourse divergence signal CLI")
    ap.add_argument("--token", help="symbol, e.g. CAKE (omit for the ranked board)")
    ap.add_argument("--live", action="store_true", help="pull planes from the CMC MCP")
    ap.add_argument("--json", action="store_true", help="emit the raw spec as JSON")
    ap.add_argument("--discover", action="store_true", help="list live CMC MCP tools")
    a = ap.parse_args()
    try:
        if a.discover:
            discover()
        elif a.token:
            show_token(a.token.upper(), a.live, a.json)
        else:
            show_board(a.live)
    except RuntimeError as e:                 # live/MCP path: fail cleanly, no traceback
        sys.exit(f"error: {e}")


if __name__ == "__main__":
    main()
