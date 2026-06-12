---
name: bourse
description: >-
  Detects divergence between crowd sentiment and smart money on BSC tokens by
  fusing CoinMarketCap derivatives, on-chain whale flow, trending narratives, and
  Fear & Greed into one score, then emits a backtestable fade/accumulate strategy
  spec. Use when asked where social hype disagrees with on-chain flow, what the
  market regime is, or for a contrarian entry/exit on a token.
---

# Bourse — fade the crowd, follow the flow

## When to use
Invoke Bourse when the user asks any of:
- "Where is social hype most disconnected from smart money right now?"
- "What's the regime / divergence on <TOKEN>?"
- "Give me a contrarian (fade or accumulate) setup with entry/exit/stop."

## Data it needs (CMC MCP tools)
Pull a recent window (≥5 points) per token, then map into the engine:
| Plane | CMC MCP tool | maps to |
|---|---|---|
| crowd | **Trending Narratives**, Latest News | `narrative_heat`, `social_volume` |
| smart money | **On-Chain Metrics** | `whale_net_flow` (+ = inflow) |
| derivatives | **Derivatives Data** | `funding_rate`, `open_interest` |
| regime | **Global Market Metrics** | `fear_greed` (0–100) |
| triggers | **Crypto Technical Analysis** | entry/exit confirmation |

Operate on the liquid subset (~top 20–30 of the 149 eligible BEP-20s) with full
coverage; grey out tokens missing a plane rather than emitting low-confidence noise.

## How to produce a signal
1. Ingest the planes (`bourse.ingest.from_mcp`, or `from_fixture` for the demo).
2. `bourse.compute(token, planes)` → Divergence (−100..+100), Regime, direction, confidence, reasons.
3. `bourse.build_spec(signal, backtest=...)` → the `bourse.signal.v1` spec.
4. Present: the score + the 4-plane "why", then the YAML spec, then the backtest stats.

## Interpreting Divergence
- **≥ +40** crowd euphoric + smart money leaving → **SHORT / FADE**
- **≤ −40** crowd fearful + smart money accumulating → **LONG / ACCUMULATE**
- between → **no trade** (don't force a signal)

## Output contract (`bourse.signal.v1`)
Always return the structured spec (direction, entry, exit, ATR stop, regime-scaled
sizing, invalidation, sources, backtest) — never a vague "looks bullish."

## Honest limits
On-chain flow is aggregated (distribution *pressure*, not the seller's identity).
Backtest depth depends on CMC historical availability — state which planes are
historical vs live-only in the answer.
