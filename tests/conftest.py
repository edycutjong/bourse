import os
import sys
from unittest.mock import MagicMock

# Mock dotenv to prevent load_dotenv() from reading the .env file during test collection/execution
sys.modules["dotenv"] = MagicMock()

# Clear transient keys from environment
if "CMC_MCP_API_KEY" in os.environ:
    del os.environ["CMC_MCP_API_KEY"]
if "CMC_PRO_API_KEY" in os.environ:
    del os.environ["CMC_PRO_API_KEY"]
