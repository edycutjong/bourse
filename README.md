# Bourse — the exchange for strategy intelligence

> A retail trader apes a KOL-pumped token at the top — while the whales who funded those KOLs quietly sell into his bid. **Bourse is the signal that screams *fade, don't follow* — and sells it to any agent by the cent.**

Bourse is a **CoinMarketCap Agent Hub Skill** that fuses four data planes —
derivatives positioning, on-chain whale flow, social/narrative heat, and market
regime — into a single **Divergence score** and emits a **backtestable strategy
spec**. The same engine is wrapped as a **hireable on-chain service (ERC-8183)**
so other agents pay (x402/USDC) to consume the live signal.

**Tracks/prizes (one codebase):** Track 2 — Strategy Skills · Best Use of Agent Hub · Best Use of BNB AI Agent SDK. *(Track 1 / TWAK intentionally out of scope — that's a live-PnL lottery.)*

## Status
- ✅ Core engine + spec generator + deterministic fixtures + **walk-forward backtest** + tests (**12 passing**, target ≥100)
- ✅ Static landing board (`scripts/seed.py` → `landing/signals.json`)
- ✅ ERC-8183 provider + buyer + ERC-8004 identity wired against **`bnbagent` 0.3.6** (real API, smoke-tested — provider app builds with all routes)
- ⏳ CMC MCP live wiring (after Day-1 data probe) · live on-chain run → `PROOF.md` tx hashes (needs a funded BSC testnet wallet) · demo video

## Quickstart
```bash
pip install -r requirements.txt
cp .env.example .env          # add CMC keys + BSC testnet key
python scripts/seed.py        # write deterministic demo fixtures + landing board
python scripts/backtest.py    # walk-forward backtest -> Sharpe/maxDD/winRate (reproducible)
pytest -q                     # 12 passing
# GO/NO-GO data gate (needs CMC_PRO_API_KEY):
python scripts/probe_cmc_history.py --symbol CAKE
```

## The core flow
`4 CMC planes → divergence + regime → bourse.signal.v1 spec → served via ERC-8183`

```
$ python -c "import json;from bourse import *;d=json.load(open('data/fixtures/demo.json'));\
h=json.load(open('data/fixtures/backtest_cake.json'));bt=run_backtest(h,token='CAKE');\
print(to_yaml(build_spec(compute('CAKE',Planes(**d['CAKE'])),backtest={k:bt[k] for k in('sharpe','max_dd','win_rate')})))"
# -> SHORT/FADE, regime=distribution, divergence=+100, 4-plane reasons, + COMPUTED backtest (Sharpe 1.74 / maxDD 15% / win 59%)
```

## Layout
```
skill/bourse/SKILL.md   # Track-2 deliverable (CMC Agent Skills format)
bourse/engine.py        # divergence + regime (z-scores, rules) — pure, tested
bourse/spec.py          # bourse.signal.v1 generator
bourse/ingest.py        # CMC MCP (live) + REST (history) — wire after probe
bourse/backtest.py      # walk-forward backtest -> Sharpe/maxDD/winRate (numpy, tested)
server/app.py           # ERC-8183 provider: create_erc8183_app(on_job=execute_job)
server/identity.py      # ERC-8004 identity registration (gas-free via MegaFuel)
clients/buyer.py        # ERC8183Client buyer: create_job -> fund -> settle
scripts/probe_cmc_history.py  # Day-1 GO/NO-GO data gate
scripts/backtest.py     # run backtest + ASCII equity curve
scripts/settle.py       # permissionless ERC8183Client.settle(jobId)
scripts/seed.py         # deterministic fixtures + landing board
```

## Why ONLY this stack
See `../SPONSOR_DEFENSE.md` — CMC (5 MCP tools, 4 planes) + BNB AI Agent SDK
(ERC-8004 identity + ERC-8183 commerce + X402Signer). Take CMC out → 4 vendors;
take the SDK out → rebuild escrow/identity/payments/disputes from scratch.

## Honest limitations
On-chain flow is aggregated (distribution pressure, not seller identity); optimistic
ERC-8183 settlement leans on a whitelisted-voter quorum. The backtest currently runs
on a **reproducible synthetic CAKE cycle** (seeded — Sharpe 1.74 / maxDD 15% / win 59%);
it is computed by `bourse.run_backtest`, not hardcoded. Real depth comes from CMC
historical data once `scripts/probe_cmc_history.py` confirms which planes expose REST
history (Day 1) — the harness is data-source agnostic, so only the input swaps.
