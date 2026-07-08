"""
ERC-8004 identity registration (gas-free on BSC testnet via MegaFuel paymaster).
Real flow, verified against bnbagent 0.3.6.

Run once to mint an on-chain agentId and advertise Bourse's /erc8183 endpoint so
buyers can discover the service:

  export WALLET_PASSWORD=...      # encrypts the keystore at ~/.bnbagent/wallets/
  export PRIVATE_KEY=0x...        # throwaway BSC-testnet key (optional: auto-generates if absent)
  export ERC8183_AGENT_URL=http://localhost:8003/erc8183
  python server/identity.py
"""
import os
import sys


def register() -> dict:
    from bnbagent import ERC8004Agent, AgentEndpoint, EVMWalletProvider

    password = os.environ.get("WALLET_PASSWORD")
    if not password:
        sys.exit("set WALLET_PASSWORD (encrypts the keystore). "
                 "PRIVATE_KEY/AGENT_PRIVATE_KEY optional — auto-generates a wallet if absent.")
    wallet = EVMWalletProvider(
        password=password,
        private_key=os.environ.get("PRIVATE_KEY") or os.environ.get("AGENT_PRIVATE_KEY"),
    )
    sdk = ERC8004Agent(wallet_provider=wallet,
                       network=os.environ.get("NETWORK", "bsc-testnet"))

    base = os.environ.get("ERC8183_AGENT_URL", "http://localhost:8003/erc8183").rstrip("/")
    agent_uri = sdk.generate_agent_uri(
        name="bourse",
        description="Crowd-vs-smart-money divergence signal — hireable via ERC-8183.",
        endpoints=[AgentEndpoint(name="ERC-8183", endpoint=f"{base}/status", version="1.2.0")],
    )
    result = sdk.register_agent(agent_uri=agent_uri)
    print(f"registered Bourse: agentId={result.get('agentId')} "
          f"tx={result.get('transactionHash')}")
    return result


if __name__ == "__main__":
    register()
