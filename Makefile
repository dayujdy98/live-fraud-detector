.PHONY: help setup setup-dev clean lint typecheck test test-coverage train train-basic train-optimized docker_build docker_push all pre-commit install-hooks load-test security-scan

# Variables
IMAGE_NAME ?= fraud-detection-api
AWS_REGION ?= us-east-1
ECR_REGISTRY ?= $(shell aws ecr describe-repositories --region $(AWS_REGION) --query 'repositories[?repositoryName==`$(IMAGE_NAME)`].repositoryUri' --output text 2>/dev/null)
PYTHON ?= python3
PIP ?= pip3
VENV_NAME ?= venv
VENV_ACTIVATE = $(VENV_NAME)/bin/activate

# Default target
all: lint typecheck test

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

$(VENV_NAME)/bin/activate: requirements-dev.txt
	$(PYTHON) -m venv $(VENV_NAME)
	. $(VENV_ACTIVATE) && $(PIP) install --upgrade pip
	. $(VENV_ACTIVATE) && $(PIP) install -r requirements-dev.txt
	touch $(VENV_ACTIVATE)

setup: $(VENV_ACTIVATE) ## Set up production environment
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

setup-dev: $(VENV_ACTIVATE) ## Set up development environment with all dev dependencies
	@echo "Development environment ready. Activate with: source $(VENV_ACTIVATE)"

install-hooks: setup-dev ## Install pre-commit hooks
	. $(VENV_ACTIVATE) && pre-commit install

clean: ## Remove build artifacts and cache files
	rm -rf $(VENV_NAME)
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf build/ dist/ .coverage htmlcov/ .pytest_cache/ .mypy_cache/

lint: ## Run code formatting and linting
	$(PYTHON) -m black --check src/ tests/
	$(PYTHON) -m isort --check-only src/ tests/
	$(PYTHON) -m flake8 src/ tests/

lint-fix: ## Auto-fix code formatting issues
	$(PYTHON) -m black src/ tests/
	$(PYTHON) -m isort src/ tests/

typecheck: ## Run static type checking
	$(PYTHON) -m mypy src/ --ignore-missing-imports

test: ## Run unit tests
	$(PYTHON) -m pytest tests/ -v

test-coverage: ## Run tests with coverage reporting
	$(PYTHON) -m pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

pre-commit: lint typecheck test ## Run all quality checks (lint, typecheck, test)

train: ## Run optimized model training
	$(PYTHON) src/training/optimized_training.py

train-basic: ## Run basic training workflow
	$(PYTHON) src/flows/train_flow.py

train-optimized: ## Run optimized training with hyperparameter tuning
	$(PYTHON) src/training/optimized_training.py

docker_build: ## Build Docker image
	docker build -t $(IMAGE_NAME) -f src/deployment/Dockerfile .

docker_push: ## Push Docker image to ECR
	@if [ -z "$(ECR_REGISTRY)" ]; then \
		echo "Error: ECR repository URI not found. Please create the ECR repository first."; \
		echo "Run: aws ecr create-repository --repository-name $(IMAGE_NAME) --region $(AWS_REGION)"; \
		exit 1; \
	fi
	@echo "Pushing to ECR: $(ECR_REGISTRY)"
	aws ecr get-login-password --region $(AWS_REGION) | docker login --username AWS --password-stdin $(ECR_REGISTRY)
	docker tag $(IMAGE_NAME):latest $(ECR_REGISTRY):latest
	docker push $(ECR_REGISTRY):latest

# Load Testing
load-test-smoke: ## Run quick smoke test (30 seconds)
	@echo "Running load test smoke test..."
	./tests/load/run-load-tests.sh smoke

load-test-quick: ## Run quick load test (5 minutes)
	@echo "Running quick load test..."
	./tests/load/run-load-tests.sh quick

load-test: ## Run comprehensive load test (targeting 10K+ TPS)
	@echo "Running comprehensive load test..."
	./tests/load/run-load-tests.sh

# Security Scanning
security-scan-quick: ## Run quick security scan (Python + Dependencies)
	@echo "Running quick security scan..."
	./security/security-scan.sh quick

security-scan-deps: ## Scan dependencies only
	@echo "Scanning dependencies..."
	./security/security-scan.sh deps

security-scan: ## Run comprehensive security scan
	@echo "Running comprehensive security scan..."
	./security/security-scan.sh

# Combined Quality Assurance
qa: lint typecheck test security-scan-quick ## Run complete quality assurance suite

qa-full: lint typecheck test security-scan load-test-quick ## Run full QA including load testing
