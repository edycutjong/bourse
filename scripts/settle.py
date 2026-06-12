#!/usr/bin/env python3
"""
Permissionless settle: apply the policy verdict to a submitted job once its dispute
window has elapsed. `router.settle` is permissionless — anyone can finalise.
Real flow, verified against bnbagent 0.3.6 (ERC8183Client.settle -> COMPLETED).

  export WALLET_PASSWORD=...    # any keystore; settle is permissionless
  export PRIVATE_KEY=0x...
  python scripts/settle.py <jobId>
"""
import os
import sys


def main(job_id: int) -> dict:
    from bnbagent.erc8183 import ERC8183Client
    from bnbagent.wallets import EVMWalletProvider

    password = os.environ.get("WALLET_PASSWORD")
    if not password:
        sys.exit("set WALLET_PASSWORD (+ PRIVATE_KEY).")
    wallet = EVMWalletProvider(password=password, private_key=os.environ.get("PRIVATE_KEY"))
    erc8183 = ERC8183Client(wallet, network=os.environ.get("NETWORK", "bsc-testnet"))

    res = erc8183.settle(int(job_id))
    print(f"settled job {job_id}  tx={res.get('transactionHash')}  "
          f"-> {erc8183.get_job_status(int(job_id)).name}")
    return res


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: settle.py <jobId>")
    main(sys.argv[1])
