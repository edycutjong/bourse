"""
Bourse ERC-8183 provider (Best Use of BNB AI Agent SDK).

Wraps the divergence engine as a hireable agentic-commerce service. A buyer
negotiates a price, escrows USDC, and receives the signed `bourse.signal.v1`
payload; settlement is optimistic via the BNB AI Agent SDK.

STUB — wire against the verified bnbagent-sdk surface (docs/SPONSOR_DOCS.md):
  from bnbagent.erc8183.server import create_erc8183_app
  app = create_erc8183_app(on_job=run_divergence)
  # routes: /erc8183/negotiate|status|job/{id}; jobs < ERC8183_SERVICE_PRICE -> 402
"""
from __future__ import annotations
import json
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bourse import compute, build_spec, run_backtest
from bourse.ingest import from_fixture

DATA = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures")
FIXTURE = os.path.join(DATA, "demo.json")
BT_FIXTURE = os.path.join(DATA, "backtest_cake.json")


def _real_backtest(token: str) -> dict | None:
    """Compute real Sharpe/maxDD/winRate from the history fixture (not hardcoded).
    Returns None if we have no history for the token, so build_spec omits it
    rather than faking numbers."""
    if not os.path.exists(BT_FIXTURE):
        return None
    with open(BT_FIXTURE) as f:
        history = json.load(f)
    m = run_backtest(history, token=token)
    return {"sharpe": m["sharpe"], "max_dd": m["max_dd"], "win_rate": m["win_rate"]}


def _token_of(job: dict) -> str:
    """Extract the token symbol. Buyers anchor a description like 'CAKE divergence
    signal' on-chain, so take the first word; fall back to an explicit `token` key."""
    raw = job.get("token") or job.get("description") or "CAKE"
    parts = str(raw).split()
    return (parts[0] if parts else "CAKE").upper()


def run_divergence(job: dict) -> dict:
    """on_job handler: read requested token from the job, return the signal spec.
    `job` follows the SDK schema (jobId/description/budget/client/provider/...)."""
    token = _token_of(job)
    # live path: planes = ingest.from_mcp(token); demo path: fixture
    if not os.path.exists(FIXTURE):
        raise RuntimeError("no fixture — run scripts/seed.py")
    try:
        planes = from_fixture(token, FIXTURE)
    except KeyError:
        raise RuntimeError(f"no data for token {token!r}")
    sig = compute(token, planes)
    return build_spec(sig, backtest=_real_backtest(token))


def execute_job(job: dict) -> str:
    """ERC-8183 on_job handler. The SDK calls this for each FUNDED job and expects
    a deliverable *string*; we return the bourse.signal.v1 spec as JSON."""
    return json.dumps(run_divergence(job))


def build_app():  # pragma: no cover - needs bnbagent[server] + WALLET_PASSWORD
    """Build the ERC-8183 provider FastAPI app (verified vs bnbagent 0.3.6).
    Serve with:  uvicorn --factory server.app:build_app --port 8003
    or:          python server/app.py --serve
    Needs env: WALLET_PASSWORD (+ PRIVATE_KEY for a funded wallet), ERC8183_AGENT_URL."""
    from bnbagent.erc8183.server import create_erc8183_app
    return create_erc8183_app(on_job=execute_job)


if __name__ == "__main__":
    if "--serve" in sys.argv:
        import uvicorn
        uvicorn.run(build_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8003")))
    else:
        # offline sanity: print exactly what a buyer would receive for CAKE
        print(json.dumps(run_divergence({"token": "CAKE"}), indent=2))
