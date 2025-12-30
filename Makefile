# Medico24 Backend - Development Commands

.PHONY: help install dev test lint format clean docker-build docker-up docker-down migrate migrate-create precommit

help:
	@echo "Available commands:"
	@echo "  make install        - Install dependencies"
	@echo "  make dev            - Run development server"
	@echo "  make test           - Run tests"
	@echo "  make lint           - Run linters"
	@echo "  make format         - Format code"
	@echo "  make precommit      - Run pre-commit hooks on all files"
	@echo "  make precommit-install - Install pre-commit hooks"
	@echo "  make clean          - Clean cache and build files"
	@echo "  make docker-build   - Build Docker images"
	@echo "  make docker-up      - Start Docker containers"
	@echo "  make docker-down    - Stop Docker containers"
	@echo "  make migrate        - Run database migrations"
	@echo "  make migrate-create - Create new migration"

install:
	pip install uv
	uv pip install -e ".[dev]"

dev:
	uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

test:
	pytest -v --cov=app --cov-report=term-missing --cov-report=html

lint:
	@echo "Running Ruff linter..."
	ruff check app tests
	@echo "Running mypy type checker..."
	mypy app
	@echo "Running bandit security scanner..."
	bandit -r app -c pyproject.toml
	@echo "Running pydocstyle..."
	pydocstyle app

format:
	@echo "Sorting imports with isort..."
	isort app tests scripts alembic
	@echo "Formatting with Black..."
	black app tests scripts alembic
	@echo "Auto-fixing with Ruff..."
	ruff check --fix app tests scripts alembic

precommit:
	@echo "Running all pre-commit hooks..."
	pre-commit run --all-files

precommit-install:
	@echo "Installing pre-commit hooks..."
	pre-commit install
	pre-commit install --hook-type commit-msg
	@echo "Pre-commit hooks installed successfully!"

precommit-update:
	@echo "Updating pre-commit hooks..."
	pre-commit autoupdate

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name "htmlcov" -exec rm -rf {} +
	find . -type f -name ".coverage" -delete
	find . -type f -name "*.pyc" -delete

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

migrate:
	alembic upgrade head

migrate-create:
	@read -p "Enter migration name: " name; \
	alembic revision --autogenerate -m "$$name"

migrate-downgrade:
	alembic downgrade -1

db-shell:
	psql $(DATABASE_URL)
