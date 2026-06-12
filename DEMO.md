# DEMO — Bourse (exact steps + expected output)

## Setup
```bash
pip install -r requirements.txt
cp .env.example .env   # fill CMC_PRO_API_KEY / CMC_MCP_API_KEY / AGENT_PRIVATE_KEY
python scripts/seed.py
```

## Beat 1 — the hook (0:00–0:20)
"This trader bought the top while whales sold into him. Bourse would've told him to fade."
Show the CAKE row on the landing board (red, SHORT).

## Beat 2 — the Skill answers live (0:20–1:10)
In Claude Code with the CMC MCP attached, ask:
> "Bourse, where is social hype most disconnected from smart money right now?"

Expected: a ranked divergence table; CAKE flagged **SHORT/FADE**, regime **distribution**,
divergence **+100**, with the 4-plane "why":
```
crowd hot (z=+1.84) · whales net-outflow · funding overcrowded-long (z=+1.79) · rising OI
```
Then the `bourse.signal.v1` YAML spec (entry/exit/ATR stop/sizing/invalidation/sources).

Reproduce offline (no network):
```bash
python -c "import json;from bourse import *;d=json.load(open('data/fixtures/demo.json'));\
h=json.load(open('data/fixtures/backtest_cake.json'));bt=run_backtest(h,token='CAKE');\
print(to_yaml(build_spec(compute('CAKE',Planes(**d['CAKE'])),backtest={k:bt[k] for k in('sharpe','max_dd','win_rate')})))"
```

## Beat 3 — backtest + authenticity (1:10–1:50)
```bash
python scripts/backtest.py        # -> Sharpe 1.74 / maxDD 15.3% / win 59% + ASCII equity curve
```
The numbers are **computed** by `bourse.run_backtest` (walk-forward over the history
fixture), not hardcoded — re-run it and they reproduce exactly. The series is a seeded,
illustrative CAKE cycle; once the Day-1 CMC probe confirms historical planes, the same
harness runs on real CMC data (only the input swaps).

## Beat 4 — the money shot: hire Bourse on-chain (1:50–2:40)
Prereqs: `pip install "bnbagent[server]"` and `.env` with `WALLET_PASSWORD` + a funded
BSC-testnet `PRIVATE_KEY` (holds the payment token).
```bash
python server/identity.py              # ERC-8004: mint agentId (gas-free via MegaFuel) -> tx
python server/app.py --serve &         # ERC-8183 provider at :8003/erc8183
python clients/buyer.py --token CAKE   # create_job -> fund (BSC tx, escrow) -> receive signal
python scripts/settle.py <jobId>       # ERC8183Client.settle after dispute window (BSC tx)
```
Expected: ERC-8004 registration tx + ERC-8183 fund tx + settle tx on BSC testnet
(record the explorer links in `PROOF.md`).

## Beat 5 — close (2:40–3:00)
"Any agent can hire a strategy brain by the cent." Thank-you.

## Expected test state
```bash
pytest -q     # 12 passing now; ≥100 by submission
```
