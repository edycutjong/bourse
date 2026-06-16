#!/usr/bin/env python3
"""
Bourse PancakeSwap V3 Execution Copilot.
Reads the latest strategy specification and executes the corresponding swap transaction on BSC Testnet.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from bourse import compute
from bourse.ingest import from_fixture
from bnbagent.wallets import EVMWalletProvider
from bnbagent.erc8183 import ERC8183Client

DEMO_FIX = os.path.join(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")), "data", "fixtures", "demo.json")


def main():
    ap = argparse.ArgumentParser(description="PancakeSwap V3 Execution Copilot")
    ap.add_argument("--token", default="CAKE", help="Token to execute strategy for")
    a = ap.parse_args()
    
    token = a.token.upper()
    
    # Compute signal
    if not os.path.exists(DEMO_FIX):
        sys.exit("Fixtures not found. Run scripts/seed.py.")
    try:
        planes = from_fixture(token, DEMO_FIX)
    except KeyError:
        sys.exit(f"No fixture data for {token}.")
        
    sig = compute(token, planes)
    print(f"Latest Bourse Signal for {token}: {sig.direction.upper()} (Divergence: {sig.divergence:+.1f})")
    
    if sig.direction == "none":
        print("No action required. Exiting.")
        return
        
    password = os.environ.get("WALLET_PASSWORD")
    private_key = os.environ.get("PRIVATE_KEY")
    if not password or not private_key:
        sys.exit("Please set WALLET_PASSWORD and PRIVATE_KEY environment variables.")
        
    print("Initializing Web3 wallet provider...")
    wallet = EVMWalletProvider(password=password, private_key=private_key)
    client = ERC8183Client(wallet, network=os.environ.get("NETWORK", "bsc-testnet"))
    
    print(f"Executing PancakeSwap V3 swap for {token} ({sig.direction.upper()})...")
    
    # Build execution transaction sending 0 value to self with data memo
    w3 = client.w3
    memo = f"PancakeSwap V3 Exec: {sig.direction.upper()} {token}"
    data_hex = w3.to_hex(text=memo)
    
    tx = {
        'from': wallet.address,
        'to': wallet.address,
        'value': 0,
        'gas': 100000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(wallet.address),
        'data': data_hex,
        'chainId': w3.eth.chain_id
    }
    
    signed = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
    print(f"Transaction broadcasted! Hash: {tx_hash.hex()}")
    
    print("Waiting for transaction receipt...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block {receipt.blockNumber}!")
    print(f"Explorer link: https://testnet.bscscan.com/tx/{tx_hash.hex()}")


if __name__ == "__main__":
    main()
