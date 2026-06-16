# Security Policy

## Supported Versions

We actively support and patch security vulnerabilities in the following versions of Bourse:

| Version | Supported |
| ------- | --------- |
| v1.0.x  | ✅ Yes    |
| < v1.0  | ❌ No     |

## Reporting a Vulnerability

We take the security of Bourse, our smart contracts, and agentic commerce workflows seriously. If you find a security vulnerability, please do **not** open a public issue. Instead, report it privately to our team.

### How to Report

Please send an email to **security@bourse.intelligence** (or the project maintainer's email listed in the repository settings) with the following details:
1. **Description**: A clear description of the vulnerability.
2. **Steps to Reproduce**: A detailed description of the steps (or proof-of-concept script) needed to reproduce the issue.
3. **Impact**: An evaluation of the potential impact (e.g., wallet key exposure, budget drain, contract state manipulation).

### Response Process

1. **Acknowledgment**: You will receive an acknowledgment of your report within 48 hours.
2. **Evaluation**: Our security team will validate the vulnerability and determine its severity.
3. **Fix & Release**: We will work on a patch and release a secure update as soon as possible.
4. **Coordination**: We will coordinate with you on public disclosure timing and attribution (if requested).

## Web3 & Agent Security Best Practices

As an agentic trading system operating on EVM networks (BSC & Base), please follow these critical guidelines during development and deployment:

* **Private Key Management**: Never commit private keys, keystores, or password variables in your `.env` files to source control. Ensure `.env` is always listed in your `.gitignore`.
* **Budget Tracking**: Always configure a strict `SessionBudgetTracker` with the BNB AI Agent SDK to limit the maximum USDC/Base or USDC/BSC amount a running agent instance is authorized to spend per session.
* **Testnet First**: Always test agentic-commerce capabilities and job escrows on testnets (e.g., BSC Testnet) before deploying to mainnets.
