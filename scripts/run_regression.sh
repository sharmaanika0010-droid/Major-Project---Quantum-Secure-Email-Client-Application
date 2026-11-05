#!/usr/bin/env bash
# QuMail - full regression run (SCRUM-68), Linux/macOS/CI. Run from the project root.
set -u
mkdir -p reports
OUT="reports/regression_$(date +%F).txt"
{
  echo "QuMail regression - $(date)"; python3 --version; git rev-parse --short HEAD; echo
  echo "=== 1. Static analysis ==="; python3 -m ruff check src tests; python3 -m bandit -c bandit.yaml -r src -q; echo
  echo "=== 2. Unit tests (default, perf excluded) ==="; python3 -m pytest -q -p no:cacheprovider; echo
  echo "=== 3. Integration (real KM simulator) ==="; python3 -m pytest -q -p no:cacheprovider -m integration; echo
  echo "=== 4. Performance ==="; python3 -m pytest -q -p no:cacheprovider -m perf
} 2>&1 | tee "$OUT"
echo "Report: $OUT"
