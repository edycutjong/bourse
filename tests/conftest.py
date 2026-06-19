import os
import sys
from unittest.mock import MagicMock

# Mock dotenv to prevent load_dotenv() from reading the .env file during test collection/execution
sys.modules["dotenv"] = MagicMock()

# Well-known PUBLIC Hardhat/Anvil test account #0 key — NOT a secret, never funded on any real
# network. Used purely as a valid-format fixture so eth_account can parse a key in unit tests.
# (Replaces a real-looking testnet key that used to be committed across the repo.)
TEST_PRIVATE_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

# Clear transient keys from environment
if "CMC_MCP_API_KEY" in os.environ:
    del os.environ["CMC_MCP_API_KEY"]
if "CMC_PRO_API_KEY" in os.environ:
    del os.environ["CMC_PRO_API_KEY"]
