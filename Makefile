.PHONY: build check format lint test typecheck

check: lint typecheck test

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy src

test:
	uv run pytest

build:
	uv build
