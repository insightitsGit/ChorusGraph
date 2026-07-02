#!/usr/bin/env bash
# Run H9 A/B benchmark on Azure (or any Linux VM with Python 3.10+).
set -euo pipefail

: "${GEMINI_API_KEY:?Set GEMINI_API_KEY}"
export BENCHMARK_ENV="${BENCHMARK_ENV:-azure}"

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

pip install -e ".[dev,gemini,cortex]" -q

OUTPUT_DIR="${OUTPUT_DIR:-$ROOT/benchmark/results/azure_$(date -u +%Y%m%d_%H%M%S)}"
TASKS="${TASKS:-1000}"
BANDS="${BANDS:-20,40,60}"

echo "ChorusGraph H9 benchmark on $BENCHMARK_ENV"
echo "  tasks/band: $TASKS"
echo "  bands: $BANDS"
echo "  output: $OUTPUT_DIR"

python -m benchmark.run_volume \
  --tasks "$TASKS" \
  --bands "$BANDS" \
  --output-dir "$OUTPUT_DIR"

echo "Aggregate analysis: $OUTPUT_DIR/aggregate_analysis.json"
