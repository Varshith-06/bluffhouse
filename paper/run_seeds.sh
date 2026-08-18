#!/usr/bin/env bash
# Seed expansion for the headline benchmark.
#
#   bash paper/run_seeds.sh extend   # more seeds, published 3-entrant roster
#   bash paper/run_seeds.sh wide     # 3 model families + control, fresh bench
#   bash paper/run_seeds.sh mode0    # matching mode-0 floor for the ladder
#
# Pins BLUFFHOUSE_SYSTEM_PROMPT=neutral so these runs are the SAME condition
# as the published ones: main's default prompt now frames the game as one of
# influence, which is a different experiment (see the paper's reproducibility
# appendix). Mixing the two in one benchmark would be exactly the error the
# paper warns about.
set -euo pipefail
cd "$(dirname "$0")/.."

KEYS_ENV="${KEYS_ENV:-C:/Users/Varshith/AppData/Local/Temp/claude/C--Users-Varshith-Documents-bluffhouse/73626d41-e02b-4bc4-af1c-5b65ecb37318/scratchpad/keys.env}"
if [ -f "$KEYS_ENV" ]; then source "$KEYS_ENV"; fi

export BLUFFHOUSE_SYSTEM_PROMPT=neutral
export BLUFFHOUSE_MAX_TOKENS=2000
export BLUFFHOUSE_LLM_RETRIES=5
# free-tier ceilings are published per model
export BLUFFHOUSE_GEMMA_4_31B_IT_RPM=24
export BLUFFHOUSE_MISTRAL_MEDIUM_LATEST_RPM=50
export BLUFFHOUSE_GEMINI_3_1_FLASH_LITE_RPM=12

PUBLISHED="google:gemma-4-31b-it,mistral:mistral-medium-latest,random"
WIDE="google:gemma-4-31b-it,mistral:mistral-medium-latest,google:gemini-3.1-flash-lite,random"
HANDS="${HANDS:-8}"

case "${1:-extend}" in
  extend)   # resume the published bench and add seeds; entrant set must match
    uv run bluffhouse bench --models "$PUBLISHED" --hands "$HANDS" --mode 6 \
      --seeds "${SEEDS:-41,42,43,44,45,46,47,48}" \
      --resume runs/e1-final/20260818-034855-seeds ;;
  wide)     # third model family; flash-lite's 500/day caps this to ~1 seed/day
    uv run bluffhouse bench --models "$WIDE" --hands "$HANDS" --mode 6 \
      --seeds "${SEEDS:-41,42}" --out runs/e1-wide ;;
  mode0)    # ladder floor on whatever seeds the mode-6 bench has
    uv run bluffhouse bench --models "$PUBLISHED" --hands "$HANDS" --mode 0 \
      --seeds "${SEEDS:-41,42,43,44,45,46,47,48}" --no-beliefs \
      --resume runs/e2-mode0/20260818-053716-seeds ;;
  *) echo "unknown: $1"; exit 1 ;;
esac
