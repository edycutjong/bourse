# Bourse — DoraHacks BUIDL Submission

This document contains the complete details required for the DoraHacks BUIDL submission for Bourse. Copy-paste these fields directly into the submission form.

---

## 1. Profile

*   **BUIDL Name**: Bourse
*   **BUIDL Logo**: [docs/assets/icon-512.png](file:///Users/edycu/Projects/Hackathon/dorahacks-bnbhack-bourse/docs/assets/icon-512.png) (Retina-ready SVG at [docs/icon.svg](file:///Users/edycu/Projects/Hackathon/dorahacks-bnbhack-bourse/docs/icon.svg))
*   **Category**: `Crypto / Web3`
*   **Vision** (189 chars / MAX 256):
    > Bourse is the decentralized strategy layer for Web3, empowering autonomous agents and retail traders to outsmart market manipulation by pricing and trading behavioral divergence permissionlessly on-chain.
*   **Elevator Pitch** (130 chars / MAX 150):
    > Real-time crowd-vs-smart-money divergence engine & CMC agent skill, hireable on BSC via ERC-8183. Fade the crowd, follow the flow.
*   **Innovation Domains**: `Crypto-AI` · `DeFi` · `Infra / API` · `Security` · `Token Economics Innovation`
*   **Layer-1 Deployment**: `BNB Chain`
*   **Other open source ecosystems**: `Metamask`
*   **Is this BUIDL an AI Agent?**: `Yes`
    *   *Agentic Capabilities*:
        1. **Autonomous Perception**: Ingests market states by calling CoinMarketCap Agent Hub (MCP) tools dynamically.
        2. **On-Chain Identity & Autonomy**: Registered via **ERC-8004** on BSC Testnet (mega-fueled, gas-free registration) as `Agent ID: 1401`. It runs as an autonomous server daemon listening for and negotiating service jobs.
        3. **Reasoning & Synthesis**: Automatically нормализует multi-source data into rolling z-scores, matches regime matrices, and outputs actionable signed strategy specifications.
        4. **Machine-to-Machine Commerce**: Operates a two-sided financial logic. It pays to consume data via **x402 (EIP-3009)** on Base network, and programmatically earns tokens by selling strategy deliverables via **ERC-8183 escrows** on BSC Testnet.

---

## 2. Project Story (Markdown)

### Inspiration
Bourse was inspired by the systematic exploitation of retail traders and naive trading bots in Web3. Social media hype and narrative pumps are often weaponized by smart money: while retail apes into a token at the top of a hype cycle, whales quietly distribute their holdings into those retail buy orders. We built Bourse to solve this as a contrarian filter. By combining derivatives skew and social media hype with actual on-chain whale activity, Bourse identifies when narrative euphoria diverges from real smart money flows — giving traders and autonomous agents a quantitative signal to fade, rather than follow, the crowd.

### What it does
1.  **Ingests Four Data Planes**: Connects to the CoinMarketCap Agent Hub Model Context Protocol (MCP) to gather live data across derivatives positioning (funding/OI), on-chain whale flow, trending social narratives (news/social sentiment), and global market technicals ( Fear & Greed index).
2.  **Computes Behavioral Divergence**: Normalizes disparate data inputs into rolling z-scores to calculate a real-time Divergence rating (from -100 to +100) indicating if crowd euphoria is decoupled from smart money.
3.  **Emits Strategy Specifications**: Generates a standardized, machine-readable `bourse.signal.v1` YAML strategy detailing entry triggers (e.g. price vs EMA gates), exits, ATR-based stops, and position sizes scaled to the market regime.
4.  **Simulates Programmatic Commerce**: Exposes an ERC-8183 agentic interface. Any buyer agent can query the Bourse status, deposit USDC escrow on the BSC Testnet, automatically receive the signed divergence strategy payload, and optimisticly settle after a 24-hour dispute window.
5.  **Performs Walk-Forward Optimization**: Implements an offline backtest engine and weights optimizer that performs walk-forward grid search over z-score weights, maximizing strategy Sharpe ratio (e.g. boosting CAKE Sharpe ratio from 1.74 to 6.28).
6.  **Interactive Web3 Dashboard**: Provides a simulation dashboard where users can trigger the end-to-end buyer agent commerce loop, watch live execution logs stream from BSC Testnet, visualize the equity curves as dynamic SVGs, and settle escrows with chiptune sound effects and confetti.

### How we built it
Bourse is architected to separate data ingestion, compute optimization, and on-chain commerce:
*   **Core Logic**: Built with Python 3.11+, leveraging NumPy and Pandas for high-speed mathematical normalization, regime matrix computation, and walk-forward backtesting.
*   **Agent Hub (MCP)**: Utilizes the CoinMarketCap MCP Client interface to pull derivatives data, Technical Analysis metrics, and news sentiment scores dynamically.
*   **Agentic Commerce**: Integrated the **BNB AI Agent SDK** to manage agent identity (ERC-8004) and job escrow contracts (`AgenticCommerce`, `EvaluatorRouter`, and `OptimisticPolicy`) on BSC Testnet. 
*   **Micropayments (x402)**: Used the X402Signer to enforce per-request USDC spend limits via EIP-3009.
*   **User Interface**: Written in pure HTML5, vanilla CSS, and JavaScript. It features an animated grid backdrop, custom glassmorphism cards, dynamic SVG line charts rendering the backtest curves on-the-fly, an interactive terminal log emulator, and retro Web Audio API synthesizers.

#### Quality & Security Engineering
Bourse implements a strict, multi-stage engineering harness ensuring code correctness and deployment safety:

| Layer | Technology | Details |
| :--- | :--- | :--- |
| **Code Quality** | Ruff (Linter & Formatter), Mypy | Strict static type checking and zero code styling warnings |
| **Unit Testing** | Pytest, Pytest-Cov | **161 passing tests** with **100% statement coverage** across all core modules |
| **E2E Testing** | Puppeteer, PuppeteerScreenRecorder | Complete headless browser walkthrough verifying dashboard state transitions |
| **Security Audit** | pip-audit, Custom secrets scanner | Automated validation against known CVEs and committed keys check |
| **CI/CD Pipeline** | GitHub Actions (`ci.yml`) | Multi-stage pipeline running checks in parallel for maximum build speed |

### Challenges we ran into
*   **EVM Test Automation in CI**: Since Bourse executes actual smart contract transactions (creating jobs, escrowing funds, and settling payments) on BSC Testnet via the `bnbagent-sdk`, testing this programmatically in an air-gapped GitHub Actions container presented a challenge. We resolved this by building an in-memory mock harness utilizing Python's patch framework to stub JSON-RPC requests, while providing a comprehensive local walkthrough script (`scripts/run_terminal_demo.py`) that clears the terminal and types out commands to easily record live BSC Testnet transactions.
*   **Cross-Regime Metric Normalization**: Comparing a social sentiment score (0-100) with a derivatives funding rate (percentage) or whale net flow (token volume) was challenging. We solved this by implementing rolling z-scores that normalize all variables into standard deviations from the mean. We then built a grid search optimizer that tweaks the weighting of each data plane depending on backtest Sharpe metrics, maximizing the strategy's signal reliability.

### What we learned
We realized that agentic Web3 commerce doesn't need complex, heavy oracle protocols. By leveraging the BNB SDK's ERC-8183 optimistic escrow and dispute policy, we can construct secure, sub-second micropayments for strategy data directly on-chain.

### What's next
1.  **Live x402 Micropayment Deployments**: Mount the two-sided payment gateway to production, paying the CoinMarketCap Agent Hub per premium pull (USDC on Base) and receiving payment per strategy spec (USDC on BSC).
2.  **Decentralized Dispute Resolution**: Expand the optimistic escrow resolver from a whitelisted voter system to a decentralized oracle network.
3.  **PancakeSwap V3 Executable Copilot**: Expand the PancakeSwap executor stub to let agents directly execute contrarian swaps, liquidity positions, and limit orders based on Bourse strategy specs.

---

## 3. Team

*   **Team Name**: Bourse Strategy Lab
*   **Team Description**: Single-developer submission focused on AI-native quant tools. Built with a production-grade Python/TypeScript engineering harness (161 tests, 100% coverage, 5-stage parallel CI/CD).
*   **Contact to Organizer**: 
    > Hi BNB Hackathon team! I am excited to submit Bourse. It fuses CoinMarketCap Agent Hub metrics to construct a real-time behavioral divergence engine, allowing autonomous agents to fade crowd euphoria on-chain. The project is fully functional, with registered identities and escrows running live on BSC Testnet.
    > - GitHub: https://github.com/edycutjong/bourse
    > - Walkthrough Video: https://youtu.be/Y5YgTCEqJqw
    > - Live Dashboard: Open `landing/index.html` locally or visit http://localhost:8003/ (with server running).

---

## 4. Links

*   **GitHub Repository**: https://github.com/edycutjong/bourse
*   **Live Demo (Mock Mode)**: Open [landing/index.html](file:///Users/edycu/Projects/Hackathon/dorahacks-bnbhack-bourse/landing/index.html) in your browser.
*   **Video Demo (YouTube)**: https://youtu.be/Y5YgTCEqJqw

---

## 5. Media Assets

*   **Logo (512x512 PNG)**: [docs/assets/icon-512.png](file:///Users/edycu/Projects/Hackathon/dorahacks-bnbhack-bourse/docs/assets/icon-512.png)
*   **Banner (16:9 PNG)**: [docs/assets/og-image.png](file:///Users/edycu/Projects/Hackathon/dorahacks-bnbhack-bourse/docs/assets/og-image.png)
*   **Screenshots**:
    1.  *Main Dashboard View*: Showcases the ranked divergence board with CAKE marked SHORT.
        <img width="800" height="450" alt="dashboard-overview" src="https://github.com/user-attachments/assets/9c7c64af-d7cd-4424-9a2a-96ac45aeabf5" />
    2.  *Divergence Metrics Modal*: Displays the normalized z-score gauges and dynamic SVG backtest equity curve.
        <img width="800" height="450" alt="dashboard-on-chain-simulator-buyer" src="https://github.com/user-attachments/assets/b9d9a72d-31e7-4361-836d-b3930a6b2df1" />
    3.  *Hacker Simulation Console*: Shows real-time BSC Testnet buyer agent logs (negotiating, funding escrow, and settling).

---

## 6. Engineering Harness Summary

*   **Code Quality**: ✅ Strict type safety via `mypy` + linting and auto-formatting via `ruff`.
*   **Unit Testing**: ✅ Pytest harness running 161 tests. Core engine verified with **100% line coverage** (261/261 statements).
*   **E2E Testing**: ✅ Puppeteer script ([scripts/record-bourse.mjs](file:///Users/edycu/Projects/DemoStudio/scripts/record-bourse.mjs)) recording the entire dashboard walkthrough.
*   **Security (DevSecOps)**: ✅ Automated dependency checking with `pip-audit` + local secrets and test validation checks on commit.
*   **CI/CD Pipeline**: ✅ GitHub Actions pipeline executing linters, typecheck, tests, and security scans in parallel.
*   **Performance & Observability**: ✅ Grid search optimizer for weights + live stream logger console on the dashboard.
