# Makefile for Customer Support Multi-Agent System

.PHONY: help build up down logs shell migrate seed test clean

# Default target
help:
	@echo "Customer Support Multi-Agent System"
	@echo ""
	@echo "Available commands:"
	@echo "  make build       - Build Docker images"
	@echo "  make up          - Start all services"
	@echo "  make down        - Stop all services"
	@echo "  make logs        - View logs"
	@echo "  make shell       - Open Django shell"
	@echo "  make migrate     - Run database migrations"
	@echo "  make seed        - Seed database with sample data"
	@echo "  make test        - Run tests"
	@echo "  make clean       - Remove containers and volumes"
	@echo ""

# Build Docker images
build:
	docker compose build

# Start all services
up:
	docker compose up -d

# Start with logs
up-logs:
	docker compose up

# Stop all services
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# View specific service logs
logs-web:
	docker compose logs -f web

logs-celery:
	docker compose logs -f celery_worker

# Open Django shell
shell:
	docker compose exec web python manage.py shell

# Open bash shell
bash:
	docker compose exec web bash

# Run migrations
migrate:
	docker compose exec web python manage.py makemigrations
	docker compose exec web python manage.py migrate

# Seed database
seed:
	docker compose exec web python manage.py seed_data

# Seed without knowledge base (no OpenAI key needed)
seed-no-kb:
	docker compose exec web python manage.py seed_data --skip-kb

# Run tests
test:
	docker compose exec web python manage.py test

# Create superuser
superuser:
	docker compose exec web python manage.py createsuperuser

# Clean up
clean:
	docker compose down -v --remove-orphans
	docker system prune -f

# Full setup (build, start, migrate, seed)
setup: build up
	@echo "Waiting for database to be ready..."
	@sleep 10
	$(MAKE) migrate
	@echo "Database migrated. To seed data, run: make seed"

# Development setup without seeding (for manual testing)
dev: build up
	@echo "Waiting for database to be ready..."
	@sleep 10
	$(MAKE) migrate
	@echo "Ready! Run 'make seed' to populate test data."

# Check service status
status:
	docker compose ps

# Restart services
restart:
	docker compose restart

# View database
db-shell:
	docker compose exec db psql -U postgres -d customer_support

# Redis CLI
redis-cli:
	docker compose exec redis redis-cli

