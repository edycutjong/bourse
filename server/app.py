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
import re
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bourse import compute, build_spec, run_backtest
from bourse.ingest import from_fixture, from_mcp

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
    token = (parts[0] if parts else "CAKE").upper()
    
    # Strip non-alphanumeric chars to prevent payload injection and clamp size
    token = re.sub(r"[^A-Z0-9]", "", token)
    return token[:20] if token else "CAKE"


def run_divergence(job: dict) -> dict:
    """on_job handler: read requested token from the job, return the signal spec.
    `job` follows the SDK schema (jobId/description/budget/client/provider/...)."""
    token = _token_of(job)
    
    # If CMC_MCP_API_KEY is configured in the environment, query the live CoinMarketCap MCP service.
    # Otherwise, fall back to the local seeded fixture file.
    mcp_api_key = os.environ.get("CMC_MCP_API_KEY")
    if mcp_api_key:
        try:
            planes = from_mcp(token)
        except Exception as e:
            # Fallback to fixture if live API fails
            if not os.path.exists(FIXTURE):
                raise RuntimeError(f"Live MCP query failed: {e}. Additionally, no fixture file found.")
            try:
                planes = from_fixture(token, FIXTURE)
            except KeyError:
                raise RuntimeError(f"Live MCP query failed: {e}. Additionally, no fixture data for token {token!r}.")
    else:
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
    from fastapi.responses import HTMLResponse
    from fastapi.staticfiles import StaticFiles
    from server.simulation import router as sim_router
    
    app = create_erc8183_app(on_job=execute_job)
    
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include simulation endpoints
    app.include_router(sim_router)
    
    # Mount docs directory so all icon, image, and style assets resolve
    app.mount("/docs", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "..", "docs")), name="docs")
    
    # Serve index.html at root /
    @app.get("/", response_class=HTMLResponse)
    def get_index():
        index_path = os.path.join(os.path.dirname(__file__), "..", "landing", "index.html")
        if os.path.exists(index_path):
            with open(index_path) as f:
                return HTMLResponse(content=f.read(), status_code=200)
        return HTMLResponse(content="<h1>Bourse Server</h1>", status_code=200)
        
    # Serve signals.json dynamically so the board loads live data
    @app.get("/signals.json")
    def get_signals_json():
        mcp_api_key = os.environ.get("CMC_MCP_API_KEY")
        fix_path = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "demo.json")
        if not os.path.exists(fix_path):
            return []
        with open(fix_path) as f:
            tokens_data = json.load(f)
            
        res = []
        for token in tokens_data.keys():
            try:
                if mcp_api_key:
                    try:
                        planes = from_mcp(token)
                    except Exception:
                        planes = from_fixture(token, fix_path)
                else:
                    planes = from_fixture(token, fix_path)
                
                s = compute(token, planes)
                res.append({
                    "token": s.token,
                    "divergence": float(s.divergence),
                    "regime": s.regime,
                    "direction": s.direction,
                    "confidence": float(s.confidence),
                    "reasons": s.reasons,
                    "derivatives_pct": s.derivatives_pct,
                    "whale_pct": s.whale_pct,
                    "sentiment_pct": s.sentiment_pct,
                    "technical_pct": s.technical_pct
                })
            except Exception:
                pass
        return res
        
    @app.get("/api/backtest/{token}")
    def get_backtest(token: str):
        token_upper = token.upper()
        fix_path = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "backtest_cake.json")
        if not os.path.exists(fix_path):
            return {"error": "Backtest fixture not found"}
        with open(fix_path) as f:
            history = json.load(f)
        try:
            m = run_backtest(history, token=token_upper)
            return m
        except Exception as e:
            return {"error": str(e)}
        
    return app


if __name__ == "__main__":
    if "--serve" in sys.argv:
        import uvicorn
        uvicorn.run(build_app(), host="0.0.0.0", port=int(os.environ.get("PORT", "8003")))
    else:
        # offline sanity: print exactly what a buyer would receive for CAKE
        print(json.dumps(run_divergence({"token": "CAKE"}), indent=2))

