"""
CoinMarketCap Agent Hub ingestor — pulls the four divergence planes into
`engine.Planes`.

Three backends, all real:
  - fixture : deterministic JSON (demo + tests + offline backtest)
  - MCP     : live, for the Skill / standalone --live CLI
              -> https://mcp.coinmarketcap.com/mcp, header X-CMC-MCP-API-KEY
  - REST    : history, for forward-collection + backtest seeding
              -> https://pro-api.coinmarketcap.com, header X-CMC_PRO_API_KEY

Design note — *graceful degradation*. A plane whose CMC tool errors or returns
nothing is dropped and `coverage` is lowered, so the engine greys it out instead
of emitting low-confidence noise (this is exactly the contract SKILL.md promises).
`from_mcp` therefore never crashes on a single-plane miss; it raises only when no
API key is configured or every plane fails.

Canonical live path: inside Claude Code with the CMC MCP attached, the agent
calls the tools per SKILL.md and feeds them to `compute`. `MCPClient` below is the
*standalone* path — for the `--live` CLI and for non-Claude agents that want to
call CMC directly. Use `MCPClient(...).list_tools()` (CLI `--discover`) to inspect
the live tool schemas before relying on the mapping.
"""
from __future__ import annotations

import json
import os
from typing import Any, Iterable

from .engine import Planes

CMC_MCP_URL = os.environ.get("CMC_MCP_URL", "https://mcp.coinmarketcap.com/mcp")
CMC_REST = os.environ.get("CMC_REST_URL", "https://pro-api.coinmarketcap.com")

# CMC MCP tools Bourse fuses, with the Planes field each populates.
# (Tool names are verbatim from the CMC Agent Hub — see docs/SPONSOR_DOCS.md.)
PLANE_TOOLS: dict[str, dict[str, Any]] = {
    "narrative_heat": {"tool": "Trending Narratives",
                       "keys": ("score", "heat", "rank", "mentions", "social_score")},
    "social_volume":  {"tool": "Latest News",
                       "keys": ("volume", "count", "mentions", "social_volume")},
    "whale_net_flow": {"tool": "On-Chain Metrics",
                       "keys": ("whale_net_flow", "net_flow", "netflow", "inflow")},
    "funding_rate":   {"tool": "Derivatives Data",
                       "keys": ("funding_rate", "funding", "fundingRate")},
    "open_interest":  {"tool": "Derivatives Data",
                       "keys": ("open_interest", "oi", "openInterest")},
}
WINDOW_FIELDS = tuple(PLANE_TOOLS.keys())


# --------------------------------------------------------------------------- #
# fixture (offline / deterministic)                                           #
# --------------------------------------------------------------------------- #
def from_fixture(token: str, path: str) -> Planes:
    """Load a deterministic fixture (used by demo + tests + offline backtest)."""
    with open(path) as f:
        d = json.load(f)[token]
    return Planes(**d)


# --------------------------------------------------------------------------- #
# helpers                                                                      #
# --------------------------------------------------------------------------- #
def _coerce_floats(value: Any) -> list[float]:
    """Pull a numeric series out of an arbitrary JSON value. Returns [] if none."""
    out: list[float] = []
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return [float(value)]
    if isinstance(value, str):
        try:
            return [float(value)]
        except ValueError:
            return []
    if isinstance(value, dict):
        value = value.values()
    if isinstance(value, Iterable):
        for item in value:
            out.extend(_coerce_floats(item))
    return out


def _series_from_result(result: Any, keys: tuple[str, ...]) -> list[float]:
    """Best-effort extraction of a numeric window from a CMC tool result.

    Walks the (possibly nested) result, preferring values under any of `keys`;
    falls back to the longest bare numeric list found. Defensive by design: an
    unexpected shape yields [] (-> plane dropped, coverage lowered) rather than
    an exception.
    """
    keyed: list[float] = []
    bare: list[float] = []

    def walk(node: Any) -> None:
        nonlocal keyed, bare
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(k, str) and k.lower() in {x.lower() for x in keys}:
                    keyed.extend(_coerce_floats(v))
                else:
                    walk(v)
        elif isinstance(node, list):
            nums = _coerce_floats(node)
            if len(nums) == len(node) and nums:        # a flat numeric list
                if len(nums) > len(bare):
                    bare = nums
            else:
                for item in node:
                    walk(item)

    walk(result)
    return keyed or bare


# --------------------------------------------------------------------------- #
# MCP client (live, Streamable HTTP / JSON-RPC 2.0)                            #
# --------------------------------------------------------------------------- #
class MCPClient:
    """Minimal Streamable-HTTP MCP client for the CMC Agent Hub.

    Implements just the surface Bourse needs: `initialize`, `list_tools`,
    `call_tool`. Handles both JSON and SSE (`text/event-stream`) responses and
    carries the `Mcp-Session-Id` the server hands back on initialize.
    """

    PROTOCOL_VERSION = "2025-06-18"

    def __init__(self, url: str | None = None, api_key: str | None = None,
                 timeout: int = 30):
        self.url = url or CMC_MCP_URL
        self.api_key = api_key or os.environ.get("CMC_MCP_API_KEY", "")
        self.timeout = timeout
        self.session_id: str | None = None
        self._rpc_id = 0
        self._initialized = False

    def _headers(self) -> dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "X-CMC-MCP-API-KEY": self.api_key,
        }
        if self.session_id:
            h["Mcp-Session-Id"] = self.session_id
        return h

    @staticmethod
    def _parse(resp: Any) -> dict:
        """Return the JSON-RPC envelope from a JSON or SSE response."""
        ctype = resp.headers.get("Content-Type", "")
        if "text/event-stream" in ctype:
            for line in resp.text.splitlines():
                line = line.strip()
                if line.startswith("data:"):
                    chunk = line[5:].strip()
                    if chunk and chunk != "[DONE]":
                        try:
                            return json.loads(chunk)
                        except json.JSONDecodeError:
                            continue
            return {}
        return resp.json()

    def _post(self, method: str, params: dict | None = None,
              *, notify: bool = False) -> dict:
        import requests

        body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            body["params"] = params
        if not notify:
            self._rpc_id += 1
            body["id"] = self._rpc_id
        try:
            resp = requests.post(self.url, headers=self._headers(),
                                 data=json.dumps(body), timeout=self.timeout)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"CMC MCP request failed ({method}): {e}") from e
        sid = resp.headers.get("Mcp-Session-Id")
        if sid:
            self.session_id = sid
        resp.raise_for_status()
        if notify:
            return {}
        env = self._parse(resp)
        if "error" in env:
            raise RuntimeError(f"MCP error on {method}: {env['error']}")
        return env.get("result", {})

    def initialize(self) -> "MCPClient":
        if self._initialized:
            return self
        if not self.api_key:
            raise RuntimeError(
                "CMC_MCP_API_KEY not set — get one at pro.coinmarketcap.com/login")
        self._post("initialize", {
            "protocolVersion": self.PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "bourse", "version": "0.1.0"},
        })
        self._post("notifications/initialized", {}, notify=True)
        self._initialized = True
        return self

    def list_tools(self) -> list[dict]:
        self.initialize()
        return self._post("tools/list").get("tools", [])

    def call_tool(self, name: str, arguments: dict | None = None) -> Any:
        """Call a tool; return its parsed structured/text content."""
        self.initialize()
        result = self._post("tools/call",
                            {"name": name, "arguments": arguments or {}})
        # Prefer structured content; else parse the text content blocks as JSON.
        if "structuredContent" in result:
            return result["structuredContent"]
        parsed: list[Any] = []
        for block in result.get("content", []):
            if block.get("type") == "text":
                text = block.get("text", "")
                try:
                    parsed.append(json.loads(text))
                except json.JSONDecodeError:
                    parsed.append(text)
        return parsed[0] if len(parsed) == 1 else (parsed or result)


# --------------------------------------------------------------------------- #
# live ingestion                                                               #
# --------------------------------------------------------------------------- #
def from_mcp(token: str, *, client: MCPClient | None = None) -> Planes:
    """Pull the four planes for `token` live from the CMC MCP and map into Planes.

    Each plane degrades independently: on error/empty it is left at a flat
    sentinel and `coverage` drops, so the engine greys it out. Raises only if no
    key is set or *every* plane fails.
    """
    client = client or MCPClient()
    client.initialize()

    fields: dict[str, list[float]] = {}
    present = 0
    cache: dict[str, Any] = {}
    for field, spec in PLANE_TOOLS.items():
        tool = spec["tool"]
        try:
            if tool not in cache:
                cache[tool] = client.call_tool(tool, {"symbol": token})
            series = _series_from_result(cache[tool], spec["keys"])
        except Exception:
            series = []
        if series:
            fields[field] = series
            present += 1
        else:
            fields[field] = [0.0, 0.0]            # flat -> z-score 0, no signal

    # Fear & Greed is a single scalar from Global Market Metrics.
    fear_greed = 50.0
    try:
        fg = _series_from_result(
            client.call_tool("Global Market Metrics", {}),
            ("fear_greed", "value", "fear_and_greed"))
        if fg:
            fear_greed = float(fg[-1])
            present += 1
    except Exception:
        pass

    if present == 0:
        raise RuntimeError(
            f"CMC MCP returned no usable planes for {token!r} — check the key/tier "
            "or run `--discover` to inspect live tool schemas")

    coverage = round(present / (len(PLANE_TOOLS) + 1), 3)  # +1 for the regime plane
    return Planes(
        narrative_heat=fields["narrative_heat"],
        social_volume=fields["social_volume"],
        whale_net_flow=fields["whale_net_flow"],
        funding_rate=fields["funding_rate"],
        open_interest=fields["open_interest"],
        fear_greed=fear_greed,
        coverage=coverage,
    )


# --------------------------------------------------------------------------- #
# REST history (forward-collection / backtest seeding)                         #
# --------------------------------------------------------------------------- #
def fetch_fear_greed_history(limit: int = 30) -> list[float]:
    """CMC Pro REST: Fear & Greed history (well-documented, stable endpoint)."""
    import requests

    key = os.environ.get("CMC_PRO_API_KEY", "")
    if not key:
        raise RuntimeError("CMC_PRO_API_KEY not set")
    r = requests.get(f"{CMC_REST}/v3/fear-and-greed/historical",
                     headers={"X-CMC_PRO_API_KEY": key, "Accept": "application/json"},
                     params={"limit": limit}, timeout=20)
    r.raise_for_status()
    data = r.json().get("data", [])
    return [float(d["value"]) for d in data if "value" in d]
