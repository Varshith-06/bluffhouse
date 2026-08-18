#!/usr/bin/env bash
# E5 elicitation ablation: identical seed, identical models, one paragraph of
# difference in the system prompt. Arm A = phase-explicit prompt only;
# Arm B = phase-explicit prompt + uniform social framing.
set -euo pipefail
cd "$(dirname "$0")/.."

KEYS_ENV="${KEYS_ENV:-C:/Users/Varshith/AppData/Local/Temp/claude/C--Users-Varshith-Documents-bluffhouse/73626d41-e02b-4bc4-af1c-5b65ecb37318/scratchpad/keys.env}"
if [ -f "$KEYS_ENV" ]; then source "$KEYS_ENV"; fi

export BLUFFHOUSE_MAX_TOKENS=2000
export BLUFFHOUSE_LLM_RETRIES=5
# per-model requests-per-minute ceilings (free-tier caps are per model)
export BLUFFHOUSE_GEMMA_4_31B_IT_RPM=24
export BLUFFHOUSE_MISTRAL_MEDIUM_LATEST_RPM=50

MODELS="google:gemma-4-31b-it,mistral:mistral-medium-latest,random,checkcall"
HANDS="${HANDS:-5}"
SEED="${SEED:-77}"

echo "=== ARM A: default (phase-explicit prompt, no framing) ==="
unset BLUFFHOUSE_SOCIAL_NUDGE
uv run bluffhouse run --mode 6 --hands "$HANDS" --bots "$MODELS" \
  --seed "$SEED" --out runs/arm-a 2>&1 | tail -3

echo "=== ARM B: elicited (same prompt + social framing paragraph) ==="
export BLUFFHOUSE_SOCIAL_NUDGE=1
uv run bluffhouse run --mode 6 --hands "$HANDS" --bots "$MODELS" \
  --seed "$SEED" --out runs/arm-b 2>&1 | tail -3

echo "=== comparison ==="
uv run python paper/analysis.py arms runs/arm-a
uv run python paper/analysis.py arms runs/arm-b
