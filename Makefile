# Engineering Intelligence System (EIS) - Common Tasks
# Run: make <target>

.PHONY: help build up down logs test lint format clean install

# Colors for output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(BLUE)Engineering Intelligence System - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# Dependency Management
install: ## Install base dependencies
	pip install -r requirements.txt

install-dev: ## Install development dependencies
	pip install -r requirements-dev.txt

compile-requirements: ## Compile requirements.txt from requirements.in
	pip install pip-tools
	./compile-requirements.sh

compile-requirements-upgrade: ## Upgrade and recompile all dependencies
	pip install pip-tools
	./compile-requirements.sh --upgrade

# Docker Commands
build: ## Build Docker image
	docker-compose build

build-dev: ## Build development Docker image
	docker-compose build dev

up: ## Start services (development)
	docker-compose up -d

down: ## Stop all services
	docker-compose down

restart: ## Restart all services
	docker-compose restart

logs: ## View application logs
	docker-compose logs -f eis

logs-qdrant: ## View Qdrant logs
	docker-compose logs -f qdrant

logs-all: ## View all logs
	docker-compose logs -f

shell: ## Start development shell
	docker-compose exec eis bash

dev-shell: ## Start development container shell
	docker-compose run --rm dev bash

# Testing
test: ## Run tests inside Docker
	docker-compose exec eis pytest

test-coverage: ## Run tests with coverage report
	docker-compose exec eis pytest --cov=.

test-verbose: ## Run tests with verbose output
	docker-compose exec eis pytest -vv

# Code Quality
lint: ## Run linters (ruff, mypy)
	docker-compose exec eis ruff check .
	docker-compose exec eis mypy .

format: ## Format code with black and isort
	docker-compose exec eis black .
	docker-compose exec eis isort .

format-check: ## Check code formatting without changes
	docker-compose exec eis black --check .
	docker-compose exec eis isort --check-only .

# Development
dev-up: ## Start development environment
	docker-compose up -d qdrant eis

dev-logs: ## Show development logs
	docker-compose logs -f eis qdrant

migrate-db: ## Run database migrations (if applicable)
	docker-compose exec eis python -m alembic upgrade head

# Cleanup
clean: ## Remove stopped containers and dangling images
	docker-compose down
	docker system prune -f

clean-volumes: ## Remove containers and volumes
	docker-compose down -v
	docker system prune -f

clean-all: ## Complete cleanup (containers, volumes, images)
	docker-compose down -v
	docker rmi $$(docker images -q eis:*)

# Production
build-prod: ## Build production image
	docker build -f Dockerfile -t eis:latest .
	docker build -f Dockerfile -t eis:$$(date +%Y%m%d) .

push-prod: ## Push production image to registry
	docker tag eis:latest $${REGISTRY}/eis:latest
	docker push $${REGISTRY}/eis:latest

# Health & Status
health: ## Check service health
	@echo "$(BLUE)Service Status:$(NC)"
	@docker-compose ps
	@echo ""
	@echo "$(BLUE)Checking Qdrant health...$(NC)"
	@curl -s http://localhost:6333/health | python -m json.tool || echo "Qdrant not available"
	@echo ""
	@echo "$(BLUE)Checking EIS health...$(NC)"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "EIS not available"

ps: ## Show running services
	docker-compose ps

# Utilities
env-setup: ## Create .env file from template
	cp .env.example .env
	@echo "$(GREEN)✓ .env created$(NC)"
	@echo "$(YELLOW)Please edit .env with your configuration$(NC)"

docs: ## Open documentation
	@echo "$(BLUE)Documentation:$(NC)"
	@echo "  - Main: README.md"
	@echo "  - Architecture: ARCHITECTURE.md"
	@echo "  - Ingestion: INGESTION.md"
	@echo "  - Quick Start: INGESTION_QUICKSTART.md"
	@echo "  - Docker: DOCKER.md (this file)"

.DEFAULT_GOAL := help
