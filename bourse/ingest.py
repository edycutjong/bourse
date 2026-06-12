"""
CMC Agent Hub ingestor — pulls the 4 planes into `engine.Planes`.

Two backends:
  - MCP (live, for the Skill)  -> https://mcp.coinmarketcap.com/mcp, X-CMC-MCP-API-KEY
  - REST (history, for backtest) -> https://pro-api.coinmarketcap.com, X-CMC_PRO_API_KEY

This is a STUB with the verified tool/endpoint names wired as TODOs. Implement
after the Day-1 probe tells you which historical planes exist.
"""
from __future__ import annotations
import os
import json
from .engine import Planes

CMC_MCP_URL = "https://mcp.coinmarketcap.com/mcp"
CMC_REST = "https://pro-api.coinmarketcap.com"

# Verified CMC MCP tools Bourse uses (see docs/SPONSOR_DOCS.md):
MCP_TOOLS = [
    "Derivatives Data",        # funding / OI / liquidations
    "On-Chain Metrics",        # whale vs retail net flow
    "Trending Narratives",     # narrative / social heat
    "Crypto Technical Analysis",
    "Global Market Metrics",   # Fear & Greed, dominance
]


def from_fixture(token: str, path: str) -> Planes:
    """Load a deterministic fixture (used by demo + tests + offline backtest)."""
    with open(path) as f:
        d = json.load(f)[token]
    return Planes(**d)


def from_mcp(token: str) -> Planes:  # pragma: no cover - needs live key
    """TODO: call the CMC MCP tools above and map into Planes.
    Use an MCP client with header X-CMC-MCP-API-KEY=os.environ['CMC_MCP_API_KEY'].
    Map: Trending Narratives->narrative_heat, On-Chain Metrics->whale_net_flow,
         Derivatives Data->funding_rate/open_interest, Global Metrics->fear_greed."""
    raise NotImplementedError("wire MCP after Day-1 probe; use from_fixture for now")
