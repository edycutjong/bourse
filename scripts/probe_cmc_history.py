#!/usr/bin/env python3
"""
GO/NO-GO data gate (BUILD_PLAN Day 1).

Answers the one question that decides Bourse's backtest design:
  "Which CMC data planes expose HISTORICAL data on my API tier?"

Usage:
  export CMC_PRO_API_KEY=...        # from pro.coinmarketcap.com
  python scripts/probe_cmc_history.py [--symbol CAKE]

It probes latest + historical endpoints across the planes Bourse fuses and
prints a verdict table. No external deps beyond `requests` + `python-dotenv`.

Reading the result:
  ✅ latest + historical  -> full backtest for that plane
  ⚠️ latest only          -> forward-collect into data/fixtures/ from today
  ❌ blocked (plan/auth)   -> price-led backtest; treat plane as live-only signal
"""
import os
import sys
import argparse
import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

BASE = "https://pro-api.coinmarketcap.com"
KEY = os.getenv("CMC_PRO_API_KEY", "")
HEADERS = {"X-CMC_PRO_API_KEY": KEY, "Accept": "application/json"}

# (label, plane, method, path, params)  — historical endpoints are the ones that matter
PROBES = [
    ("quotes latest",        "price",       "GET", "/v1/cryptocurrency/quotes/latest",            {"symbol": "{sym}"}),
    ("quotes HISTORICAL",    "price",       "GET", "/v2/cryptocurrency/quotes/historical",        {"symbol": "{sym}", "count": 10, "interval": "daily"}),
    ("ohlcv HISTORICAL",     "price",       "GET", "/v1/cryptocurrency/ohlcv/historical",         {"symbol": "{sym}", "count": 10, "interval": "daily"}),
    ("fear&greed latest",    "regime",      "GET", "/v3/fear-and-greed/latest",                   {}),
    ("fear&greed HISTORICAL","regime",      "GET", "/v3/fear-and-greed/historical",               {"limit": 10}),
    ("global HISTORICAL",    "regime",      "GET", "/v1/global-metrics/quotes/historical",        {"count": 10, "interval": "daily"}),
    # Derivatives / on-chain / social historical paths are less standardized in the public REST docs.
    # Probe the latest variants; if these 404, those planes are MCP-live-only -> forward-collect.
    ("trending (narratives?)","social",     "GET", "/v1/cryptocurrency/trending/latest",          {}),
]


def probe(label, plane, method, path, params):
    p = {k: (str(v).replace("{sym}", SYM) if isinstance(v, str) else v) for k, v in params.items()}
    try:
        r = requests.request(method, BASE + path, headers=HEADERS, params=p, timeout=20)
    except Exception as e:
        return (label, plane, "ERR", str(e)[:60])
    code = r.status_code
    try:
        body = r.json()
        status = body.get("status", {})
        err = status.get("error_message")
        has_data = bool(body.get("data"))
    except Exception:
        err, has_data = r.text[:60], False
    if code == 200 and has_data:
        verdict = "✅ OK (data)"
    elif code == 200:
        verdict = "⚠️ 200 no-data"
    elif code in (401, 403):
        verdict = "❌ auth"
    elif code in (402, 1006) or (err and "plan" in err.lower()):
        verdict = "❌ plan/tier"
    elif code == 404:
        verdict = "❌ 404"
    else:
        verdict = f"❌ {code}"
    return (label, plane, verdict, (err or "")[:50])


def main():
    if not KEY:
        sys.exit("CMC_PRO_API_KEY not set. export it or put it in .env")
    print(f"Probing CMC Pro REST for symbol={SYM}\n")
    rows = [probe(*p) for p in PROBES]
    w = max(len(r[0]) for r in rows)
    print(f"{'endpoint':<{w}}  {'plane':<7}  verdict           note")
    print("-" * (w + 45))
    for label, plane, verdict, note in rows:
        print(f"{label:<{w}}  {plane:<7}  {verdict:<16}  {note}")
    hist_ok = [r for r in rows if "HISTORICAL" in r[0] and r[2].startswith("✅")]
    print("\nVERDICT:")
    if hist_ok:
        print(f"  Backtest can use {len(hist_ok)} historical plane(s): "
              + ", ".join(r[0] for r in hist_ok))
    else:
        print("  No historical planes on this tier -> START FORWARD-COLLECTING TODAY")
        print("  (run scripts/seed.py on a cron to accumulate a real window by Jun 21)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="CAKE")
    SYM = ap.parse_args().symbol
    main()
