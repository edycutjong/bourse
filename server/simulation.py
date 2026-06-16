import os
import time
import threading
from fastapi import APIRouter

router = APIRouter(prefix="/api")

# Global simulation state
class SimulationState:
    def __init__(self):
        self.status = "idle"
        self.logs = []
        self.job_id = None
        self.tx_fund = None
        self._lock = threading.Lock()

    def get_snapshot(self) -> dict:
        """Safely extract state for JSON serialization without race conditions."""
        with self._lock:
            return {
                "status": self.status,
                "logs": list(self.logs),
                "job_id": self.job_id,
                "tx_fund": self.tx_fund
            }

    def reset(self):
        with self._lock:
            self.status = "idle"
            self.logs = []
            self.job_id = None
            self.tx_fund = None

    def add_log(self, msg: str):
        with self._lock:
            self.logs.append(msg)

    def set_status(self, status: str):
        with self._lock:
            self.status = status

    def set_job_details(self, job_id: int, tx_fund: str):
        with self._lock:
            self.job_id = job_id
            self.tx_fund = tx_fund

state = SimulationState()

def run_simulation_thread(password: str, private_key: str, provider_address: str, network: str):
    state.set_status("running")
    state.add_log("🚀 Launching Buyer Agent on-chain simulator...")
    try:
        from bnbagent.wallets import EVMWalletProvider
        from bnbagent.erc8183 import ERC8183Client, JobStatus
        
        state.add_log("1. Initializing Web3 wallet provider...")
        wallet = EVMWalletProvider(password=password, private_key=private_key)
        client = ERC8183Client(wallet, network=network)
        
        state.add_log(f"   Buyer address derived: {wallet.address}")
        
        # Check balance
        bal = client.token_balance()
        state.add_log(f"   Current payment token balance: {bal / 1e18:.4f} {client.token_symbol()}")
        
        if bal < 1000000000000000000:
            state.add_log("⚠️ Balance below 1.0 U. Calling faucet contract...")
            faucet_address = "0x86e9197cc0f76e4e4aaa7082180945196bbab5d3"
            faucet_abi = [
                {"inputs":[],"name":"requestTokens","outputs":[],"stateMutability":"nonpayable","type":"function"}
            ]
            faucet = client.w3.eth.contract(
                address=client.w3.to_checksum_address(faucet_address),
                abi=faucet_abi
            )
            
            tx = faucet.functions.requestTokens().build_transaction({
                'from': wallet.address,
                'gas': 200000,
                'gasPrice': client.w3.eth.gas_price,
                'nonce': client.w3.eth.get_transaction_count(wallet.address),
            })
            
            signed = client.w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = client.w3.eth.send_raw_transaction(signed.raw_transaction)
            state.add_log(f"   Faucet request tx broadcasted: {tx_hash.hex()}")
            
            state.add_log("   Waiting for confirmation...")
            client.w3.eth.wait_for_transaction_receipt(tx_hash)
            bal_after = client.token_balance()
            state.add_log(f"   Success! Faucet funded wallet. New balance: {bal_after / 1e18:.4f} {client.token_symbol()}")
            
        # Create Job
        state.add_log("2. Creating signal request job on-chain...")
        budget = int(os.environ.get("ERC8183_SERVICE_PRICE", "1000000000000000000"))
        expired_at = int(time.time()) + 172800
        res = client.create_job(provider=provider_address, expired_at=expired_at, description="CAKE divergence signal")
        job_id = res["jobId"]
        state.add_log(f"   Job created on-chain. Job ID: {job_id}")
        
        # Register Job
        state.add_log("3. Registering Job ID on router...")
        client.register_job(job_id)
        
        # Set Budget
        state.add_log("4. Setting job budget...")
        client.set_budget(job_id, budget)
        
        # Fund (Escrow)
        state.add_log("5. Escrowing payment (funding the job)...")
        fres = client.fund(job_id, budget)
        tx_fund = fres.get("transactionHash", "")
        state.add_log(f"   Job funded successfully! Escrow tx: {tx_fund}")
        state.set_job_details(job_id, tx_fund)
        
        # Wait for provider App to process
        state.add_log("6. Waiting for Bourse provider agent to submit signal...")
        for i in range(15):
            time.sleep(2)
            st = client.get_job_status(job_id)
            state.add_log(f"   Job status: {st.name}")
            if st in (JobStatus.SUBMITTED, JobStatus.COMPLETED):
                state.add_log("✨ Success! Bourse provider agent submitted the divergence signal on-chain.")
                state.add_log(f"   Next step: settle job {job_id} after the 24-hour dispute window has elapsed.")
                state.set_status("completed")
                return
                
        state.set_status("failed")
        state.add_log("❌ Timeout waiting for Bourse provider to submit the signal.")
        
    except Exception as e:
        err_msg = str(e)
        if private_key and private_key in err_msg:
            err_msg = err_msg.replace(private_key, "[REDACTED_KEY]")
        if password and password in err_msg:
            err_msg = err_msg.replace(password, "[REDACTED_PASSWORD]")
            
        state.set_status("failed")
        state.add_log(f"💥 Simulation failed: {err_msg}")

@router.post("/simulate-buyer")
def trigger_simulation():
    with state._lock:
        if state.status == "running":
            return {"status": "already_running"}
        state.status = "running"
        state.logs = []
        state.job_id = None
        state.tx_fund = None
    
    password = os.environ.get("WALLET_PASSWORD", "secret")
    private_key = os.environ.get("PRIVATE_KEY")
    provider = os.environ.get("BOURSE_PROVIDER_ADDRESS") or "0x318A19d41De4eD4365765A542a9FAe5fBD78D4Ae"
    network = os.environ.get("NETWORK", "bsc-testnet")
    
    if not private_key:
        state.set_status("failed")
        return {"status": "error", "message": "PRIVATE_KEY environment variable is not configured."}
        
    # Spawn thread
    t = threading.Thread(target=run_simulation_thread, args=(password, private_key, provider, network))
    t.daemon = True
    t.start()
    
    return {"status": "started"}

@router.get("/simulate-buyer/status")
def get_simulation_status():
    return state.get_snapshot()

@router.get("/info")
def get_info():
    from bnbagent.wallets import EVMWalletProvider
    from bnbagent.erc8183 import ERC8183Client
    
    password = os.environ.get("WALLET_PASSWORD", "secret")
    private_key = os.environ.get("PRIVATE_KEY")
    network_name = os.environ.get("NETWORK", "bsc-testnet")
    provider = os.environ.get("BOURSE_PROVIDER_ADDRESS") or "0x318A19d41De4eD4365765A542a9FAe5fBD78D4Ae"
    
    try:
        wallet = EVMWalletProvider(password=password, private_key=private_key)
        client = ERC8183Client(wallet, network=network_name)
        balance = client.token_balance()
        symbol = client.token_symbol()
        decimals = client.token_decimals()
    except Exception:
        balance = 0
        symbol = "U"
        decimals = 18
        
    return {
        "agent_address": provider,
        "agent_id": "1401",
        "network": network_name,
        "payment_token": "0xc70B8741B8B07A6d61E54fd4B20f22Fa648E5565",
        "symbol": symbol,
        "balance": f"{balance / (10 ** decimals):.4f}",
    }


@router.post("/settle/{job_id}")
def trigger_settle(job_id: int):
    # Run settle logic
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
    from scripts.settle import main as settle_main
    try:
        res = settle_main(job_id)
        return {"status": "success", "tx": res.get("transactionHash")}
    except Exception as e:
        return {"status": "error", "message": str(e)}

