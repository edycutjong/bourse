"""Ingestor tests: fixture loading, series extraction, MCP client parsing,
and graceful coverage degradation on the live path (no network)."""
import json
import os

import pytest

from bourse import Planes, compute
from bourse.ingest import (
    MCPClient,
    _coerce_floats,
    _series_from_result,
    from_fixture,
    from_mcp,
)

FIX = os.path.join(os.path.dirname(__file__), "..", "data", "fixtures", "demo.json")


# ---- fixtures ------------------------------------------------------------- #
@pytest.mark.parametrize("token", ["CAKE", "XYZL", "ABCN"])
def test_from_fixture_returns_planes(token):
    p = from_fixture(token, FIX)
    assert isinstance(p, Planes)
    assert len(p.narrative_heat) >= 2


def test_from_fixture_unknown_token_raises():
    with pytest.raises(KeyError):
        from_fixture("DOESNOTEXIST", FIX)


# ---- _coerce_floats ------------------------------------------------------- #
def test_coerce_scalar_numbers():
    assert _coerce_floats(5) == [5.0]
    assert _coerce_floats(2.5) == [2.5]


def test_coerce_numeric_string():
    assert _coerce_floats("3.14") == [3.14]


def test_coerce_rejects_bool_and_text():
    assert _coerce_floats(True) == []
    assert _coerce_floats("hello") == []


def test_coerce_nested_list_and_dict():
    assert _coerce_floats([1, 2, [3, 4]]) == [1.0, 2.0, 3.0, 4.0]
    assert _coerce_floats({"a": 1, "b": 2}) == [1.0, 2.0]


# ---- _series_from_result -------------------------------------------------- #
def test_series_prefers_keyed_values():
    res = {"funding_rate": [0.01, 0.02, 0.03], "noise": [9, 9]}
    assert _series_from_result(res, ("funding_rate",)) == [0.01, 0.02, 0.03]


def test_series_keyed_is_case_insensitive():
    assert _series_from_result({"FundingRate": [1, 2]}, ("fundingrate",)) == [1.0, 2.0]


def test_series_nested_keyed():
    res = {"data": {"metrics": {"open_interest": [100, 110, 140]}}}
    assert _series_from_result(res, ("open_interest",)) == [100.0, 110.0, 140.0]


def test_series_falls_back_to_longest_numeric_list():
    res = {"data": {"points": [1, 2, 3, 4], "two": [9, 9]}}
    assert _series_from_result(res, ("nomatch",)) == [1.0, 2.0, 3.0, 4.0]


def test_series_empty_when_nothing_numeric():
    assert _series_from_result({"label": "text"}, ("x",)) == []


# ---- MCPClient (no network) ---------------------------------------------- #
def test_headers_carry_key_and_session():
    c = MCPClient(api_key="abc")
    c.session_id = "sess-1"
    h = c._headers()
    assert h["X-CMC-MCP-API-KEY"] == "abc"
    assert h["Mcp-Session-Id"] == "sess-1"
    assert "application/json" in h["Accept"]


class _Resp:
    def __init__(self, ctype, text):
        self.headers = {"Content-Type": ctype}
        self.text = text

    def json(self):
        return json.loads(self.text)


def test_parse_plain_json():
    env = MCPClient._parse(_Resp("application/json", '{"result": {"ok": 1}}'))
    assert env["result"]["ok"] == 1


def test_parse_sse_stream():
    sse = "event: message\ndata: {\"result\": {\"ok\": 2}}\n\n"
    env = MCPClient._parse(_Resp("text/event-stream", sse))
    assert env["result"]["ok"] == 2


def test_initialize_requires_key():
    with pytest.raises(RuntimeError):
        MCPClient(api_key="").initialize()


def test_call_tool_parses_text_content(monkeypatch):
    c = MCPClient(api_key="k")
    c._initialized = True
    monkeypatch.setattr(c, "_post", lambda *a, **k: {
        "content": [{"type": "text", "text": '{"funding_rate": [1, 2, 3]}'}]})
    assert c.call_tool("Derivatives Data") == {"funding_rate": [1, 2, 3]}


def test_call_tool_prefers_structured_content(monkeypatch):
    c = MCPClient(api_key="k")
    c._initialized = True
    monkeypatch.setattr(c, "_post", lambda *a, **k: {"structuredContent": {"x": 1}})
    assert c.call_tool("Whatever") == {"x": 1}


# ---- from_mcp (injected fake client) ------------------------------------- #
class _FakeClient:
    def __init__(self, table, fail=()):
        self.table, self.fail = table, set(fail)

    def initialize(self):
        return self

    def call_tool(self, name, arguments=None):
        if name in self.fail:
            raise RuntimeError("boom")
        return self.table.get(name, {})


_FULL = {
    "Trending Narratives": {"score": [1, 2, 3, 4, 5]},
    "Latest News": {"volume": [2, 2, 3, 6, 11]},
    "On-Chain Metrics": {"net_flow": [5, 4, 2, -3, -9]},
    "Derivatives Data": {"funding_rate": [0.01, 0.03, 0.06],
                         "open_interest": [100, 110, 140]},
    "Global Market Metrics": {"fear_greed": 78},
}


def test_from_mcp_full_coverage():
    p = from_mcp("CAKE", client=_FakeClient(_FULL))
    assert p.coverage == 1.0
    assert p.fear_greed == 78
    assert list(p.whale_net_flow) == [5, 4, 2, -3, -9]
    compute("CAKE", p)               # must not raise on live planes


def test_from_mcp_degrades_on_missing_plane():
    p = from_mcp("CAKE", client=_FakeClient(_FULL, fail=["Derivatives Data"]))
    assert p.coverage < 1.0
    assert list(p.funding_rate) == [0.0, 0.0]      # greyed-out sentinel


def test_from_mcp_raises_when_all_planes_empty():
    with pytest.raises(RuntimeError):
        from_mcp("CAKE", client=_FakeClient({}))
