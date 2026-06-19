# PROOF — Bourse on-chain run (BSC testnet)

> [!IMPORTANT]
> **Status:** ✅ **Settled — full lifecycle complete.** The buyer job ran register → fund → submit → **settle** on BSC Testnet. The 24-hour dispute window elapsed on 2026-06-17 04:52:48 UTC and the escrow was finalized via permissionless `router.settle` (tx in the table below). Final job status: **`COMPLETED`**.

| Step | Contract / call | Tx hash | Explorer |
|------|-----------------|---------|----------|
| ERC-8004 register | `register_agent` | `0x849e44f9e11207730f99b2392fea4a0b01311f9489d044412be7d51acbee5a0e` | https://testnet.bscscan.com/tx/0x849e44f9e11207730f99b2392fea4a0b01311f9489d044412be7d51acbee5a0e |
| ERC-8183 fund | `ERC8183Client.fund` | `0x929534e45b19a3d6e52e2ee0384bf4888302aebbbf875a556171b0710b9fbb97` | https://testnet.bscscan.com/tx/0x929534e45b19a3d6e52e2ee0384bf4888302aebbbf875a556171b0710b9fbb97 |
| ERC-8183 settle | `ERC8183Client.settle` | `0xa738ad287d26e6605e720d67a14008a8eba73fd6fa9457db0312d59c89093f16` | https://testnet.bscscan.com/tx/0xa738ad287d26e6605e720d67a14008a8eba73fd6fa9457db0312d59c89093f16 |

- Agent ID (ERC-8004): `1401`
- Provider agent address: `0x318A19d41De4eD4365765A542a9FAe5fBD78D4Ae`
- Job ID: `174`
- Payment token / symbol: `0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565` / `U`
- Final job status: `COMPLETED` (settled on-chain via permissionless `router.settle` after the 24-hour dispute window elapsed; tx `0xa738ad287d26e6605e720d67a14008a8eba73fd6fa9457db0312d59c89093f16`)

Notes:
1. Registration is gas-free via MegaFuel paymaster, completed on BSC testnet (tx `0x849e44f9e11207730f99b2392fea4a0b01311f9489d044412be7d51acbee5a0e`).
2. The buyer job was funded and negotiated on BSC Testnet with Mock "U" (United Stables) tokens (tx `0x929534e45b19a3d6e52e2ee0384bf4888302aebbbf875a556171b0710b9fbb97`), escrowing 1.0 U token.
3. The provider agent processed the job and submitted the signed divergence signal back to the commerce contract.
4. The escrow settlement was triggered permissionlessly via `python scripts/settle.py 174` once the dispute window (24 hours on the preset testnet policy contract) had expired, moving the job to `COMPLETED` (tx `0xa738ad287d26e6605e720d67a14008a8eba73fd6fa9457db0312d59c89093f16`).
