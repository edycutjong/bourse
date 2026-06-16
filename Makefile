# Bourse Makefile
# Handles project setup, testing, seeding, backtesting, running the server, and security audits.

.DEFAULT_GOAL := help

# Colors for terminal styling
YELLOW := \033[33m
BLUE   := \033[34m
GREEN  := \033[32m
RESET  := \033[0m

##@ Setup & Environment
.PHONY: setup-env install

setup-env: ## Copy environment template to .env if not exists
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)Created .env from template.$(RESET)"; \
	else \
		echo "$(YELLOW).env already exists, skipping.$(RESET)"; \
	fi

install: setup-env ## Install all dependencies (core + dev + server) in editable mode
	@echo "$(BLUE)Installing dependencies...$(RESET)"
	pip install -r requirements.txt
	pip install -e .
	@echo "$(GREEN)Installation completed successfully.$(RESET)"

##@ Data & Engine Testing
.PHONY: seed signal signal-cake backtest bench

seed: ## Seed deterministic fixtures for offline execution
	@echo "$(BLUE)Seeding fixtures...$(RESET)"
	python scripts/seed.py

signal: ## Get ranked signal board (default offline mock)
	python scripts/signal.py

signal-cake: ## Get 4-plane "why" + bourse.signal.v1 spec + backtest for CAKE
	python scripts/signal.py --token CAKE

backtest: ## Run the numpy walk-forward backtest (Sharpe/maxDD/winRate + ASCII curve)
	python scripts/backtest.py

bench: ## Run the benchmark suite to verify execution speed
	python scripts/bench.py

##@ Running the Server & Client
.PHONY: identity run buyer

identity: ## Register the Bourse ERC-8004 identity (gas-free via MegaFuel)
	python server/identity.py

run: ## Start the ERC-8183 provider FastAPI app (Server)
	python server/app.py --serve

buyer: ## Simulate a buyer requesting a signal for CAKE
	python clients/buyer.py --token CAKE

##@ Testing & Verification
.PHONY: test test-coverage ci security-scan ready

test: ## Run pytest suite
	@echo "$(BLUE)Running test suite...$(RESET)"
	pytest

test-coverage: ## Run pytest with coverage report
	@echo "$(BLUE)Running test suite with coverage...$(RESET)"
	python -m pytest --cov=bourse --cov-report=term-missing

ci: ## Run all CI pipeline checks (ruff, mypy, pytest with coverage, pip-audit, and readiness check)
	@echo "$(BLUE)Running CI pipeline...$(RESET)"
	@echo "$(BLUE)1. Running Ruff linting...$(RESET)"
	@python -m ruff check . || true
	@echo "$(BLUE)2. Running mypy type checking...$(RESET)"
	@python -m mypy . --ignore-missing-imports || true
	@echo "$(BLUE)3. Running pytest with coverage...$(RESET)"
	@python -m pytest --cov=bourse --cov-report=term-missing
	@echo "$(BLUE)4. Running dependency security audit...$(RESET)"
	@$(MAKE) security-scan
	@echo "$(BLUE)5. Running submission readiness check...$(RESET)"
	@python scripts/check_submission_readiness.py

security-scan: ## Run dependency security audit via pip-audit
	@echo "$(BLUE)Running pip-audit...$(RESET)"
	@pip install -q pip-audit
	pip-audit -r requirements.txt || true

ready: ## Run submission readiness gate check
	@echo "$(BLUE)Running readiness gate check...$(RESET)"
	python scripts/check_submission_readiness.py

##@ Utilities
.PHONY: clean help

clean: ## Remove python caches, build outputs, and venv files
	@echo "$(BLUE)Cleaning cache files...$(RESET)"
	rm -rf .pytest_cache .ruff_cache .mypy_cache build/ dist/ *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)Cleaned up successfully.$(RESET)"

help: ## Show this help message
	@echo ""
	@echo "$(BLUE)Bourse Command Line Interface (CLI)$(RESET)"
	@echo "Usage: make [target]"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Targets:\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  $(YELLOW)%-15s$(RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n$(BLUE)%s$(RESET)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""
