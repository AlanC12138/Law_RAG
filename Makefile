# Law RAG — Common Commands
# Run `make help` to see all available commands.

.PHONY: help start stop restart build logs logs-backend reset status

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

start: ## Start all services (in the background)
	docker compose up -d

stop: ## Stop all services
	docker compose down

restart: ## Restart all services
	docker compose restart

build: ## Rebuild images and start (use this after code changes)
	docker compose up -d --build

logs: ## Stream live logs from all services  (Ctrl-C to exit)
	docker compose logs -f

logs-backend: ## Stream backend logs only
	docker compose logs -f backend

status: ## Show running containers and their health
	docker compose ps

reset: ## ⚠️  Stop everything and wipe ALL data, then restart fresh
	docker compose down -v
	docker compose up -d --build

.DEFAULT_GOAL := help
