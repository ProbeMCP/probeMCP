.PHONY: build check coverage format lint test typecheck

check: lint typecheck test

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

test:
	uv run pytest

coverage:
	uv run pytest --cov=probemcp --cov-report=term-missing

build:
	uv build
