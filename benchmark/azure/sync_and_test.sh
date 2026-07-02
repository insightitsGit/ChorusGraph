#!/usr/bin/env bash
# Sync ChorusGraph on Azure VM and run tests (or benchmark).
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/ChorusGraph}"
BRANCH="${BRANCH:-master}"
RUN_BENCHMARK="${RUN_BENCHMARK:-0}"
TASKS="${TASKS:-30}"
SEED="${SEED:-42}"

if [[ ! -d "$REPO_DIR/.git" ]]; then
  echo "Cloning ChorusGraph into $REPO_DIR"
  sudo mkdir -p "$(dirname "$REPO_DIR")"
  sudo git clone https://github.com/insightitsGit/ChorusGraph.git "$REPO_DIR"
  sudo chown -R "$(whoami):$(whoami)" "$REPO_DIR"
fi

cd "$REPO_DIR"
git fetch origin
git checkout "$BRANCH"
git pull --ff-only origin "$BRANCH"

pip install -e ".[dev,gemini,cortex]" -q

echo "Running pytest..."
python -m pytest tests/ -q --tb=line

if [[ "$RUN_BENCHMARK" == "1" ]]; then
  if [[ -z "${GEMINI_API_KEY:-}" && -z "${GOOGLE_API_KEY:-}" ]]; then
    echo "GEMINI_API_KEY not set — skipping live benchmark"
    python -m benchmark.run_offline_ab --tasks "$TASKS" --seed "$SEED"
  else
    python -m benchmark.run --tasks "$TASKS" --seed "$SEED" \
      --output "benchmark/results/azure_$(date -u +%Y%m%d_%H%M%S)/live_ab.json"
  fi
fi

echo "Azure sync complete: $REPO_DIR @ $(git rev-parse --short HEAD)"
