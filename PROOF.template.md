# PROOF — Bourse on-chain run (BSC testnet)

> Copy to `PROOF.md` and replace the placeholders with REAL tx hashes from a live run
> (`server/identity.py` → `clients/buyer.py` → `scripts/settle.py`). The submission
> readiness gate looks for a `0x…64hex` hash in `PROOF.md`.

| Step | Contract / call | Tx hash | Explorer |
|------|-----------------|---------|----------|
| ERC-8004 register | `register_agent` | `0x<register-tx-hash>` | https://testnet.bscscan.com/tx/0x<register-tx-hash> |
| ERC-8183 fund | `ERC8183Client.fund` | `0x<fund-tx-hash>` | https://testnet.bscscan.com/tx/0x<fund-tx-hash> |
| ERC-8183 settle | `ERC8183Client.settle` | `0x<settle-tx-hash>` | https://testnet.bscscan.com/tx/0x<settle-tx-hash> |

- Agent ID (ERC-8004): `<agentId>`
- Provider agent address: `0x<provider-address>`
- Job ID: `<jobId>`
- Payment token / symbol: `<currency>` / `<symbol>`
- Final job status: `COMPLETED`

Notes: registration is gas-free via MegaFuel; fund escrows the payment token; settle is
permissionless after the dispute window.
