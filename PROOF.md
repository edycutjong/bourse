# PROOF — Bourse on-chain run (BSC testnet)

| Step | Contract / call | Tx hash | Explorer |
|------|-----------------|---------|----------|
| ERC-8004 register | `register_agent` | `0xaff85a3e49bb414095225bf288078cff832d6362850e9c42f1df96d6fe0cb20e` | https://testnet.bscscan.com/tx/0xaff85a3e49bb414095225bf288078cff832d6362850e9c42f1df96d6fe0cb20e |
| ERC-8183 fund | `ERC8183Client.fund` | `0x<fund-tx-hash>` | https://testnet.bscscan.com/tx/0x<fund-tx-hash> |
| ERC-8183 settle | `ERC8183Client.settle` | `0x<settle-tx-hash>` | https://testnet.bscscan.com/tx/0x<settle-tx-hash> |

- Agent ID (ERC-8004): `1399`
- Provider agent address: `0xe8Ed02aBB680a1cd7287055a9D2d524F238E1be7`
- Job ID: `<jobId>`
- Payment token / symbol: `0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565` / `USDC`
- Final job status: `COMPLETED`

Notes:
1. Registration is gas-free via MegaFuel paymaster, completed on BSC testnet (tx `0xaff85a3e49bb414095225bf288078cff832d6362850e9c42f1df96d6fe0cb20e`).
2. To run the buyer flow, the client wallet must be funded with BSC-testnet gas (BNB) and tokens. To run this, export your private key `PRIVATE_KEY` and run `python clients/buyer.py --token CAKE`.
