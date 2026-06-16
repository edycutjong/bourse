"""
Buyer agent — hires Bourse over ERC-8183 (the demo money-shot).
Real on-chain flow, verified against bnbagent 0.3.6.

Lifecycle: create_job -> register_job -> set_budget -> fund (USDC escrow on BSC) ->
poll until the provider submits -> fetch the signed signal -> settle after the
dispute window (scripts/settle.py).

  export WALLET_PASSWORD=...        # buyer keystore password
  export PRIVATE_KEY=0x...          # funded BSC-testnet key holding the payment token
  export ERC8183_AGENT_URL=http://localhost:8003/erc8183   # provider base URL
  # provider address is auto-discovered from /status (or set BOURSE_PROVIDER_ADDRESS)
  python clients/buyer.py --token CAKE
"""
import argparse
import json
import os
import sys
import time
import urllib.request


def _get(url: str):
    with urllib.request.urlopen(url, timeout=15) as r:
        return json.loads(r.read().decode())


def main(token: str, *, poll_s: int = 10, timeout_s: int = 600):
    from bnbagent.erc8183 import ERC8183Client, JobStatus
    from bnbagent.wallets import EVMWalletProvider

    password = os.environ.get("WALLET_PASSWORD")
    if not password:
        sys.exit("set WALLET_PASSWORD (+ PRIVATE_KEY for a funded buyer wallet).")
    base = os.environ.get("ERC8183_AGENT_URL", "http://localhost:8003/erc8183").rstrip("/")
    provider = os.environ.get("BOURSE_PROVIDER_ADDRESS") or _get(f"{base}/status")["agent_address"]

    wallet = EVMWalletProvider(password=password, private_key=os.environ.get("PRIVATE_KEY"))
    erc8183 = ERC8183Client(wallet, network=os.environ.get("NETWORK", "bsc-testnet"))

    decimals = erc8183.token_decimals()
    budget = int(os.environ.get("ERC8183_SERVICE_PRICE", str(1 * 10 ** decimals)))
    expired_at = int(time.time()) + 172800

    res = erc8183.create_job(provider=provider, expired_at=expired_at,
                             description=f"{token} divergence signal")
    job_id = res["jobId"]
    print(f"created job {job_id}  tx={res.get('transactionHash')}")
    erc8183.register_job(job_id)
    erc8183.set_budget(job_id, budget)
    fres = erc8183.fund(job_id, budget)
    print(f"funded {budget} {erc8183.token_symbol()} (escrowed)  tx={fres.get('transactionHash')}")

    deadline = time.time() + timeout_s
    while time.time() < deadline:
        st = erc8183.get_job_status(job_id)
        print(f"  job {job_id}: {st.name}")
        if st in (JobStatus.SUBMITTED, JobStatus.COMPLETED):
            payload = _get(f"{base}/job/{job_id}/response")
            signal = payload.get("content", payload)
            print("received bourse.signal.v1:\n" + (signal if isinstance(signal, str)
                  else json.dumps(signal, indent=2)))
            print(f"\nnext: settle after the dispute window ->  python scripts/settle.py {job_id}")
            return job_id
        time.sleep(poll_s)
    sys.exit("timed out waiting for the provider to submit")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--token", default="CAKE")
    main(ap.parse_args().token.upper())
