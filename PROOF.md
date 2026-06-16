# PROOF — Bourse on-chain run (BSC testnet)

> [!IMPORTANT]
> **Status:** Escrow currently locked in the 24-hour dispute window (a core security feature of our ERC-8183 Agentic Commerce implementation). See BscScan link below for proof of lock. Settlement will be triggered automatically via `python scripts/settle.py 174` at **2026-06-17 04:52:48 UTC**.

| Step | Contract / call | Tx hash | Explorer |
|------|-----------------|---------|----------|
| ERC-8004 register | `register_agent` | `0x849e44f9e11207730f99b2392fea4a0b01311f9489d044412be7d51acbee5a0e` | https://testnet.bscscan.com/tx/0x849e44f9e11207730f99b2392fea4a0b01311f9489d044412be7d51acbee5a0e |
| ERC-8183 fund | `ERC8183Client.fund` | `0x929534e45b19a3d6e52e2ee0384bf4888302aebbbf875a556171b0710b9fbb97` | https://testnet.bscscan.com/tx/0x929534e45b19a3d6e52e2ee0384bf4888302aebbbf875a556171b0710b9fbb97 |
| ERC-8183 settle | `ERC8183Client.settle` | `Pending (Dispute Lock)` | Locked in 24h dispute window until **2026-06-17 04:52:48 UTC** (run `python scripts/settle.py 174` after expiry) |

- Agent ID (ERC-8004): `1401`
- Provider agent address: `0x318A19d41De4eD4365765A542a9FAe5fBD78D4Ae`
- Job ID: `174`
- Payment token / symbol: `0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565` / `U`
- Final job status: `SUBMITTED` (Pending 24-hour dispute window settlement expiring **2026-06-17 04:52:48 UTC**)

Notes:
1. Registration is gas-free via MegaFuel paymaster, completed on BSC testnet (tx `0x849e44f9e11207730f99b2392fea4a0b01311f9489d044412be7d51acbee5a0e`).
2. The buyer job was funded and negotiated on BSC Testnet with Mock "U" (United Stables) tokens (tx `0x929534e45b19a3d6e52e2ee0384bf4888302aebbbf875a556171b0710b9fbb97`), escrowing 1.0 U token.
3. The provider agent processed the job and submitted the signed divergence signal back to the commerce contract.
4. The escrow settlement transaction can be triggered permissionlessly by anyone once the dispute window (24 hours on the preset testnet policy contract) has expired: `python scripts/settle.py 174`.
