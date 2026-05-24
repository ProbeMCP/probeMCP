#!/usr/bin/env bash
set -euo pipefail

mode="${1:-full}"

uv run ruff check .
uv run mypy src
uv run pytest

if [[ "${mode}" == "full" ]]; then
  uv run ruff check . --select S --ignore S101,S105,S106
  uvx pip-audit --progress-spinner off
  uv build
fi
