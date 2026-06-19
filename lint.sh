#!/usr/bin/env bash
# Run all linters and the type checker. Exits non-zero if any check fails.
set -euo pipefail

cd "$(dirname "$0")"

echo "== ruff check =="
ruff check .

echo "== ruff format --check =="
ruff format --check .

echo "== mypy =="
mypy drone_alarm.py alarm.py

echo "All checks passed."
