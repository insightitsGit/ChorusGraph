#!/usr/bin/env bash
set -euo pipefail

TASKS="${BENCHMARK_TASKS:-12}"
TIER="${BENCHMARK_TIER:-}"
SEED="${BENCHMARK_SEED:-42}"
BAND="${BENCHMARK_REPEAT_BAND:-40}"
SCENARIOS="${BENCHMARK_SCENARIOS:-all}"
OUT_DIR="${BENCHMARK_OUTPUT_DIR:-/results/mvp_scenarios}"
RUN_ID="${BENCHMARK_RUN_ID:-$(date -u +%Y%m%d_%H%M%S)}"

TIER_ARGS=()
if [[ -n "$TIER" ]]; then
  TIER_ARGS+=(--tier "$TIER")
fi

mkdir -p "$OUT_DIR"

echo "=============================================="
echo "ChorusGraph MVP benchmark — Azure"
echo "  run_id:    $RUN_ID"
echo "  scenarios: $SCENARIOS"
echo "  tier:      ${TIER:-custom}"
echo "  tasks:     $TASKS"
echo "  seed:      $SEED"
echo "  band:      $BAND"
NO_CACHE="${BENCHMARK_NO_CACHE:-0}"
CACHE_ARGS=()
if [[ "$NO_CACHE" == "1" || "$NO_CACHE" == "true" ]]; then
  CACHE_ARGS+=(--no-cache)
fi

echo "  cache:     $([[ ${#CACHE_ARGS[@]} -gt 0 ]] && echo disabled || echo enabled)"
echo "=============================================="

python -m benchmark.run_scenarios \
  --scenarios "$SCENARIOS" \
  "${TIER_ARGS[@]}" \
  --tasks "$TASKS" \
  --seed "$SEED" \
  --repeat-band "$BAND" \
  --output-dir "$OUT_DIR" \
  "${CACHE_ARGS[@]}"

echo ""
echo "=============================================="
echo "COMPARISON REPORT"
echo "=============================================="
if [[ -f "$OUT_DIR/COMPARISON_REPORT.md" ]]; then
  cat "$OUT_DIR/COMPARISON_REPORT.md"
else
  echo "(no comparison report generated)"
fi

echo ""
echo "=============================================="
echo "RUN META"
echo "=============================================="
cat "$OUT_DIR/run_meta.json"

# Optional: upload tarball to Azure Blob (set AZURE_STORAGE_CONNECTION_STRING)
if [[ -n "${AZURE_STORAGE_CONNECTION_STRING:-}" ]]; then
  python - <<'PY'
import os
import tarfile
from datetime import datetime, timezone
from pathlib import Path

from azure.storage.blob import BlobServiceClient

out = Path(os.environ["BENCHMARK_OUTPUT_DIR"])
run_id = os.environ["BENCHMARK_RUN_ID"]
container = os.environ.get("BENCHMARK_BLOB_CONTAINER", "benchmark-results")
prefix = f"mvp_scenarios/{run_id}"

archive = Path(f"/tmp/{run_id}.tar.gz")
with tarfile.open(archive, "w:gz") as tar:
    tar.add(out, arcname=run_id)

client = BlobServiceClient.from_connection_string(os.environ["AZURE_STORAGE_CONNECTION_STRING"])
blob = client.get_blob_client(container=container, blob=f"{prefix}/results.tar.gz")
with archive.open("rb") as f:
    blob.upload_blob(f, overwrite=True)

meta = out / "run_meta.json"
if meta.exists():
    mb = client.get_blob_client(container=container, blob=f"{prefix}/run_meta.json")
    mb.upload_blob(meta.read_bytes(), overwrite=True)

report = out / "COMPARISON_REPORT.md"
if report.exists():
    rb = client.get_blob_client(container=container, blob=f"{prefix}/COMPARISON_REPORT.md")
    rb.upload_blob(report.read_bytes(), overwrite=True)

print(f"UPLOADED blob://{container}/{prefix}/")
PY
fi

echo ""
echo "BENCHMARK_COMPLETE run_id=$RUN_ID"
