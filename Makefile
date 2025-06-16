# Makefile for Anonymous Questions Bot Testing
# Provides convenient commands for different testing scenarios

.PHONY: help test test-quick test-full test-unit test-integration test-handlers test-models test-utils test-middleware
.PHONY: test-security test-ci test-deploy test-pre-commit
.PHONY: coverage coverage-html coverage-report lint clean install-dev install-test
.PHONY: setup-test-env check-deps run-bot debug-bot

# Default target
.DEFAULT_GOAL := help

# Colors for output
RED=\033[0;31m
GREEN=\033[0;32m
YELLOW=\033[0;33m
BLUE=\033[0;34m
PURPLE=\033[0;35m
CYAN=\033[0;36m
NC=\033[0m # No Color

# Python and project settings
PYTHON=python3
PIP=pip3
PROJECT_NAME=anonymous-questions-bot
VENV_DIR=venv

help: ## Show this help message
	@echo "$(CYAN)Anonymous Questions Bot - Testing Automation$(NC)"
	@echo "=================================================="
	@echo ""
	@echo "$(GREEN)Quick Start:$(NC)"
	@echo "  make install-test    # Install test dependencies"
	@echo "  make test-quick      # Run fast unit tests"
	@echo "  make test-full       # Run all tests with coverage"
	@echo "  make test-deploy     # Run deployment tests"
	@echo ""
	@echo "$(GREEN)Available Commands:$(NC)"
	@awk 'BEGIN {FS = ":.*##"} /^[a-zA-Z_-]+:.*##/ { printf "  $(CYAN)%-18s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(GREEN)Test Categories:$(NC)"
	@echo "  $(YELLOW)Unit Tests$(NC)      - Fast, isolated tests"
	@echo "  $(YELLOW)Integration$(NC)     - Database and component tests"  
	@echo "  $(YELLOW)Security$(NC)        - Security validation tests"
	@echo "  $(YELLOW)Handlers$(NC)        - Bot handler tests"
	@echo "  $(YELLOW)Models$(NC)          - Data model tests"
	@echo "  $(YELLOW)Utils$(NC)           - Utility function tests"
	@echo "  $(YELLOW)Middleware$(NC)      - Middleware tests"

# Installation targets
install-dev: ## Install development dependencies
	@echo "$(YELLOW)Installing development dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-asyncio pytest-cov flake8 mypy black isort
	@echo "$(GREEN)✅ Development dependencies installed$(NC)"

install-test: ## Install test dependencies only
	@echo "$(YELLOW)Installing test dependencies...$(NC)"
	$(PIP) install pytest pytest-asyncio pytest-cov
	@echo "$(GREEN)✅ Test dependencies installed$(NC)"

check-deps: ## Check if required dependencies are installed
	@echo "$(YELLOW)Checking dependencies...$(NC)"
	@$(PYTHON) -c "import pytest; print('✅ pytest:', pytest.__version__)" 2>/dev/null || (echo "❌ pytest not found" && exit 1)
	@$(PYTHON) -c "import pytest_asyncio; print('✅ pytest-asyncio installed')" 2>/dev/null || (echo "❌ pytest-asyncio not found" && exit 1)
	@$(PYTHON) -c "import pytest_cov; print('✅ pytest-cov installed')" 2>/dev/null || (echo "❌ pytest-cov not found" && exit 1)
	@echo "$(GREEN)✅ All required dependencies found$(NC)"

# Main test targets
test: test-quick ## Alias for test-quick

test-quick: check-deps ## Run fast unit tests (recommended for development)
	@echo "$(BLUE)🚀 Running Quick Unit Tests$(NC)"
	$(PYTHON) run_tests.py quick

test-full: check-deps ## Run complete test suite with coverage
	@echo "$(BLUE)🔬 Running Full Test Suite$(NC)"
	$(PYTHON) run_tests.py full

test-unit: check-deps ## Run unit tests only
	@echo "$(BLUE)🧪 Running Unit Tests$(NC)"
	$(PYTHON) -m pytest -v -m "unit" --tb=short Tests/

test-integration: check-deps ## Run integration and database tests
	@echo "$(BLUE)🔗 Running Integration Tests$(NC)"
	$(PYTHON) run_tests.py integration

test-handlers: check-deps ## Run handler tests only
	@echo "$(BLUE)🎮 Running Handler Tests$(NC)"
	$(PYTHON) run_tests.py handlers

test-models: check-deps ## Run model tests only
	@echo "$(BLUE)📊 Running Model Tests$(NC)"
	$(PYTHON) run_tests.py models

test-utils: check-deps ## Run utility tests only
	@echo "$(BLUE)🛠 Running Utility Tests$(NC)"
	$(PYTHON) run_tests.py utils

test-middleware: check-deps ## Run middleware tests only
	@echo "$(BLUE)⚙️ Running Middleware Tests$(NC)"
	$(PYTHON) run_tests.py middleware

test-security: check-deps ## Run security-focused tests
	@echo "$(BLUE)🔒 Running Security Tests$(NC)"
	$(PYTHON) run_tests.py security

# CI/CD targets
test-ci: check-deps ## Run tests optimized for CI/CD pipeline
	@echo "$(BLUE)🤖 Running CI Tests$(NC)"
	$(PYTHON) run_tests.py ci

test-pre-commit: check-deps ## Run pre-commit checks (lint + quick tests)
	@echo "$(BLUE)✨ Running Pre-Commit Checks$(NC)"
	$(PYTHON) run_tests.py pre-commit

test-deploy: check-deps ## Run comprehensive deployment tests
	@echo "$(BLUE)🚀 Running Deployment Tests$(NC)"
	$(PYTHON) run_tests.py deploy

# Coverage targets
coverage: test-full ## Generate coverage report (same as test-full)

coverage-html: check-deps ## Generate HTML coverage report
	@echo "$(YELLOW)Generating HTML coverage report...$(NC)"
	$(PYTHON) -m pytest --cov=. --cov-report=html:Tests/coverage_html Tests/
	@echo "$(GREEN)✅ HTML coverage report generated$(NC)"
	@echo "Open: Tests/coverage_html/index.html"

coverage-report: ## Show coverage report location
	$(PYTHON) run_tests.py --coverage

# Code quality targets
lint: ## Run code linting with flake8
	@echo "$(YELLOW)Running code linting...$(NC)"
	@which flake8 >/dev/null 2>&1 || (echo "$(RED)❌ flake8 not found. Install with: pip install flake8$(NC)" && exit 1)
	flake8 --max-line-length=120 --ignore=E501,W503,E203 --exclude=venv,env,__pycache__,.git,Tests/coverage_html .
	@echo "$(GREEN)✅ Linting passed$(NC)"

format: ## Format code with black (if available)
	@echo "$(YELLOW)Formatting code...$(NC)"
	@which black >/dev/null 2>&1 && black . || echo "$(YELLOW)⚠️  black not available, skipping formatting$(NC)"
	@which isort >/dev/null 2>&1 && isort . || echo "$(YELLOW)⚠️  isort not available, skipping import sorting$(NC)"

type-check: ## Run type checking with mypy (if available)
	@echo "$(YELLOW)Running type checks...$(NC)"
	@which mypy >/dev/null 2>&1 && mypy . --ignore-missing-imports || echo "$(YELLOW)⚠️  mypy not available, skipping type checking$(NC)"

# Cleanup targets
clean: ## Clean test cache, coverage files, and Python cache
	@echo "$(YELLOW)Cleaning test artifacts...$(NC)"
	$(PYTHON) run_tests.py --clean
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

clean-all: clean ## Clean everything including bytecode
	@echo "$(YELLOW)Deep cleaning...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage*" -delete
	rm -rf .pytest_cache .mypy_cache .tox dist build *.egg-info
	@echo "$(GREEN)✅ Deep cleanup completed$(NC)"

# Bot execution targets
run-bot: check-deps ## Run the bot (for manual testing)
	@echo "$(BLUE)🤖 Starting bot...$(NC)"
	$(PYTHON) main.py

debug-bot: check-deps ## Run bot with debug logging
	@echo "$(BLUE)🐛 Starting bot in debug mode...$(NC)"
	LOG_LEVEL=DEBUG $(PYTHON) main.py

config-check: ## Check bot configuration
	@echo "$(YELLOW)Checking bot configuration...$(NC)"
	$(PYTHON) check_config.py

# Development workflows
dev-setup: install-dev ## Complete development setup
	@echo "$(GREEN)🎉 Development environment ready!$(NC)"
	@echo ""
	@echo "$(CYAN)Next steps:$(NC)"
	@echo "  1. Copy .env.example to .env and fill in your values"
	@echo "  2. Run 'make test-quick' to verify setup"
	@echo "  3. Run 'make run-bot' to start the bot"

dev-test: test-quick lint ## Quick development test (unit tests + lint)

pre-push: test-full lint type-check ## Run before pushing to repository
	@echo "$(GREEN)🚀 Ready to push!$(NC)"

release-test: test-deploy ## Run comprehensive tests before release
	@echo "$(GREEN)🎉 Ready for release!$(NC)"

# Information targets
info: ## Show project information
	@echo "$(CYAN)Project Information$(NC)"
	@echo "==================="
	@echo "Name: $(PROJECT_NAME)"
	@echo "Python: $(shell $(PYTHON) --version)"
	@echo "Pytest: $(shell $(PYTHON) -c 'import pytest; print(pytest.__version__)' 2>/dev/null || echo 'Not installed')"
	@echo "Working Directory: $(shell pwd)"
	@echo "Tests Directory: $(shell pwd)/Tests"

test-status: ## Show current test status and coverage
	@echo "$(CYAN)Test Status$(NC)"
	@echo "============"
	@[ -f Tests/coverage_html/index.html ] && echo "✅ Coverage report available" || echo "❌ No coverage report found"
	@[ -f .coverage ] && echo "✅ Coverage data exists" || echo "❌ No coverage data"
	@[ -d .pytest_cache ] && echo "✅ Pytest cache exists" || echo "❌ No pytest cache"
	@echo ""
	@echo "Run 'make test-full' to generate complete coverage report"

# Help for specific test types
help-marks: ## Show available pytest marks
	@echo "$(CYAN)Available Test Marks$(NC)"
	@echo "===================="
	@echo "$(YELLOW)unit$(NC)        - Fast unit tests"
	@echo "$(YELLOW)integration$(NC) - Integration tests with database"
	@echo "$(YELLOW)database$(NC)    - Tests requiring database"
	@echo "$(YELLOW)handlers$(NC)    - Bot handler tests"
	@echo "$(YELLOW)models$(NC)      - Data model tests"
	@echo "$(YELLOW)utils$(NC)       - Utility function tests"
	@echo "$(YELLOW)security$(NC)    - Security validation tests"
	@echo ""
	@echo "Run specific marks with: pytest -m 'mark_name'"

	# Deployment targets
deploy-check: ## Check deployment readiness
	@echo "$(YELLOW)Checking deployment readiness...$(NC)"
	$(PYTHON) deployment_check.py
	@echo "$(GREEN)✅ Deployment check completed$(NC)"

deploy-setup: ## Setup production environment
	@echo "$(YELLOW)Setting up production environment...$(NC)"
	$(PIP) install -r requirements.txt
	$(PYTHON) reset_database.py
	@echo "$(GREEN)✅ Production setup completed$(NC)"

deploy-test: ## Run minimal tests before deployment
	@echo "$(YELLOW)Running deployment tests...$(NC)"
	$(PYTHON) -m pytest -v -m "not database" --tb=short Tests/
	@echo "$(GREEN)✅ Deployment tests passed$(NC)"

deploy-clean: ## Clean unnecessary files for deployment
	@echo "$(YELLOW)Cleaning for deployment...$(NC)"
	rm -f .env.test
	rm -f utils/helpers.py
	rm -rf services/
	rm -f test_diagnostics.py
	rm -f setup_tests.py
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)✅ Cleanup completed$(NC)"

deploy: deploy-clean deploy-check deploy-test ## Full deployment preparation
	@echo "$(GREEN)🚀 Ready for deployment!$(NC)"

# Service management (for systemd)
service-install: ## Install systemd service
	@echo "$(YELLOW)Installing systemd service...$(NC)"
	sudo cp anon-questions-bot.service /etc/systemd/system/
	sudo systemctl daemon-reload
	sudo systemctl enable anon-questions-bot
	@echo "$(GREEN)✅ Service installed$(NC)"

service-start: ## Start bot service
	@echo "$(YELLOW)Starting bot service...$(NC)"
	sudo systemctl start anon-questions-bot
	@echo "$(GREEN)✅ Service started$(NC)"

service-stop: ## Stop bot service
	@echo "$(YELLOW)Stopping bot service...$(NC)"
	sudo systemctl stop anon-questions-bot
	@echo "$(GREEN)✅ Service stopped$(NC)"

service-restart: ## Restart bot service
	@echo "$(YELLOW)Restarting bot service...$(NC)"
	sudo systemctl restart anon-questions-bot
	@echo "$(GREEN)✅ Service restarted$(NC)"

service-status: ## Check bot service status
	@echo "$(YELLOW)Bot service status:$(NC)"
	sudo systemctl status anon-questions-bot

service-logs: ## View bot service logs
	@echo "$(YELLOW)Bot service logs:$(NC)"
	sudo journalctl -u anon-questions-bot -f

# Database management
db-backup: ## Backup database
	@echo "$(YELLOW)Creating database backup...$(NC)"
	pg_dump -U $(DB_USER) -h $(DB_HOST) -p $(DB_PORT) $(DB_NAME) > backup_$(shell date +%Y%m%d_%H%M%S).sql
	@echo "$(GREEN)✅ Database backup created$(NC)"

db-restore: ## Restore database from backup
	@echo "$(YELLOW)Restoring database...$(NC)"
	@read -p "Enter backup file name: " backup_file; \
	psql -U $(DB_USER) -h $(DB_HOST) -p $(DB_PORT) $(DB_NAME) < $$backup_file
	@echo "$(GREEN)✅ Database restored$(NC)"

# Production helpers
prod-logs: ## Tail production logs
	tail -f logs/bot.log logs/admin.log logs/question.log

prod-check: ## Check production bot health
	@echo "$(YELLOW)Checking bot health...$(NC)"
	@ps aux | grep -v grep | grep "python main.py" > /dev/null && echo "$(GREEN)✅ Bot is running$(NC)" || echo "$(RED)❌ Bot is not running$(NC)"
	@echo "$(YELLOW)Database connection:$(NC)"
	$(PYTHON) -c "import asyncio; from models.database import check_db_connection; print('✅ Connected' if asyncio.run(check_db_connection()) else '❌ Not connected')"

prod-update: ## Update bot code (git pull + restart)
	@echo "$(YELLOW)Updating bot code...$(NC)"
	git pull
	$(PIP) install -r requirements.txt
	sudo systemctl restart anon-questions-bot
	@echo "$(GREEN)✅ Bot updated and restarted$(NC)"