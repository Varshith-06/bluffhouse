#!/usr/bin/env bash
# Paper experiments. Usage: bash paper/run_experiments.sh <e1|e2-mode0|e1-directed>
# Runs are checkpointed per rotation; re-running with the same --out resumes.
set -euo pipefail
cd "$(dirname "$0")/.."

KEYS_ENV="${KEYS_ENV:-C:/Users/Varshith/AppData/Local/Temp/claude/C--Users-Varshith-Documents-bluffhouse/73626d41-e02b-4bc4-af1c-5b65ecb37318/scratchpad/keys.env}"
if [ -f "$KEYS_ENV" ]; then source "$KEYS_ENV"; fi

export BLUFFHOUSE_MAX_TOKENS=2000
export BLUFFHOUSE_LLM_RETRIES=5
# per-model requests-per-minute ceilings (free-tier caps are per model)
export BLUFFHOUSE_GEMMA_4_31B_IT_RPM=24
export BLUFFHOUSE_MISTRAL_MEDIUM_LATEST_RPM=50

# The two models with sustainable free-tier capacity, plus the bot control
# that anchors the duplicate scale at zero token cost.
MODELS="google:gemma-4-31b-it,mistral:mistral-medium-latest,random"
HANDS="${HANDS:-8}"

case "$1" in
  e1)          # headline: mode 6, default prompt, two seeds
    uv run bluffhouse bench --models "$MODELS" --hands "$HANDS" --mode 6 \
      --seeds "41,42" --out runs/e1-final ;;
  e2-mode0)    # ladder floor: pure poker, same entrants and seeds as e1
    uv run bluffhouse bench --models "$MODELS" --hands "$HANDS" --mode 0 \
      --seeds "41,42" --no-beliefs --out runs/e2-mode0 ;;
  e1-directed) # mode 6 with the channel actually in use
    BLUFFHOUSE_SOCIAL_NUDGE=2 \
    uv run bluffhouse bench --models "$MODELS" --hands "$HANDS" --mode 6 \
      --seed 41 --out runs/e1-directed ;;
  *) echo "unknown experiment: $1"; exit 1 ;;
esac
