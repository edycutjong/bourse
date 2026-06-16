import os
from web3 import Web3
from dotenv import load_dotenv

# Load env variables from .env file
load_dotenv()

def main():
    rpc_url = "https://data-seed-prebsc-2-s2.binance.org:8545"
    w3 = Web3(Web3.HTTPProvider(rpc_url))
    
    private_key = os.environ.get("PRIVATE_KEY")
    if not private_key:
        print("PRIVATE_KEY env var not found!")
        return

    account = w3.eth.account.from_key(private_key)
    address = account.address
    print(f"Using address: {address}")
    
    faucet_address = "0x86e9197cc0f76e4e4aaa7082180945196bbab5d3"
    faucet_abi = [
        {"inputs":[],"name":"requestTokens","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"internalType":"address","name":"_address","type":"address"}],"name":"allowedToWithdraw","outputs":[{"internalType":"bool","name":"","type":"bool"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"tokenInstance","outputs":[{"internalType":"contract ERC20","name":"","type":"address"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"tokenAmount","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"waitTime","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"}
    ]
    
    faucet_contract = w3.eth.contract(address=Web3.to_checksum_address(faucet_address), abi=faucet_abi)
    
    # Check token instance
    token_inst = faucet_contract.functions.tokenInstance().call()
    print(f"Faucet token instance: {token_inst}")
    
    # Check if allowed to withdraw
    allowed = faucet_contract.functions.allowedToWithdraw(address).call()
    print(f"Allowed to withdraw: {allowed}")
    
    # Check token amount
    amount = faucet_contract.functions.tokenAmount().call()
    print(f"Token amount per request: {amount}")
    
    # Check wait time
    wait = faucet_contract.functions.waitTime().call()
    print(f"Wait time (seconds): {wait}")

    # Check token balance before
    token_abi = [
        {"inputs":[{"internalType":"address","name":"account","type":"address"}],"name":"balanceOf","outputs":[{"internalType":"uint256","name":"","type":"uint256"}],"stateMutability":"view","type":"function"},
        {"inputs":[],"name":"symbol","outputs":[{"internalType":"string","name":"","type":"string"}],"stateMutability":"view","type":"function"}
    ]
    token_contract = w3.eth.contract(address=Web3.to_checksum_address(token_inst), abi=token_abi)
    balance_before = token_contract.functions.balanceOf(address).call()
    symbol = token_contract.functions.symbol().call()
    print(f"Balance before: {balance_before} {symbol}")
    
    if not allowed:
        print("Faucet says address is not allowed to withdraw at this moment. Maybe too soon since last claim?")
        return

    # Call requestTokens
    print("Calling requestTokens() to get faucet tokens...")
    tx = faucet_contract.functions.requestTokens().build_transaction({
        'from': address,
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(address),
    })
    
    signed_tx = w3.eth.account.sign_transaction(tx, private_key)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print(f"Transaction sent! Hash: {tx_hash.hex()}")
    
    print("Waiting for transaction confirmation...")
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    print(f"Transaction confirmed in block {receipt['blockNumber']} with status {receipt['status']}")
    
    balance_after = token_contract.functions.balanceOf(address).call()
    print(f"Balance after: {balance_after} {symbol}")

if __name__ == "__main__":
    main()
