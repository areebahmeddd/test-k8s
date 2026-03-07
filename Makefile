.PHONY: up down quality test coverage migrate upgrade downgrade

# ============================================
# Development
# ============================================

up:
	@echo "Starting server..."
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

down:
	@echo "Stopping server..."
	- pkill -f "uvicorn app.main:app" || true

# ============================================
# Code Quality
# ============================================

quality:
	@echo "Running pre-commit checks..."
	uv run pre-commit run --all-files

# ============================================
# Testing
# ============================================

test:
	@echo "Running tests..."
	uv run pytest -v --cov=app --cov-report=term-missing

coverage:
	@echo "Running tests with full coverage report..."
	uv run pytest -v --cov=app --cov-report=term-missing --cov-report=html
	@echo "HTML report generated at htmlcov/index.html"

# ============================================
# Database Migrations
# ============================================

migrate:
	@echo "Creating new migration..."
	uv run alembic revision --autogenerate -m "$(msg)"

upgrade:
	@echo "Upgrading database to latest revision..."
	uv run alembic upgrade head

downgrade:
	@echo "Downgrading database by one revision..."
	uv run alembic downgrade -1
