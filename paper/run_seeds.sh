#!/usr/bin/env bash
# Seed expansion for the headline benchmark.
#
#   bash paper/run_seeds.sh redo     # headline bench, all seeds, pinned prompt
#   bash paper/run_seeds.sh extend   # more seeds, published 3-entrant roster
#   bash paper/run_seeds.sh wide     # 3 model families + control, fresh bench
#   bash paper/run_seeds.sh mode0    # matching mode-0 floor for the ladder
#
# Pins BLUFFHOUSE_SYSTEM_PROMPT=neutral so these runs are the SAME condition
# as the published ones: main's default prompt now frames the game as one of
# influence, which is a different experiment (see the paper's reproducibility
# appendix). Mixing the two in one benchmark would be exactly the error the
# paper warns about.
#
# That pin used to cover only the system message. The 2026-08-18 `extend` run
# (runs/e1-final/20260818-034855-seeds, seeds 43-48) therefore paired the
# neutral system prompt with main's REWRITTEN talk prompt, which argues for
# working the table and answers, point by point, the reasons models had given
# for staying silent. Those seeds are a separate elicitation arm, not an
# extension of the headline bench; `redo` is the corrected re-run. The pin now
# covers the talk phase too (comm_instructions_neutral), with regression tests
# in tests/test_llm_agent.py.
set -euo pipefail
cd "$(dirname "$0")/.."

KEYS_ENV="${KEYS_ENV:-C:/Users/Varshith/AppData/Local/Temp/claude/C--Users-Varshith-Documents-bluffhouse/73626d41-e02b-4bc4-af1c-5b65ecb37318/scratchpad/keys.env}"
if [ -f "$KEYS_ENV" ]; then source "$KEYS_ENV"; fi

export BLUFFHOUSE_SYSTEM_PROMPT=neutral
export BLUFFHOUSE_MAX_TOKENS=2000
export BLUFFHOUSE_LLM_RETRIES=5
# free-tier ceilings are published per model
export BLUFFHOUSE_GEMMA_4_31B_IT_RPM=24
# Gemma answers in ~13s, so at concurrency 1 a seed spends ~36 minutes waiting
# on a 24 RPM budget it never comes close to using. Five in flight saturates
# the rate gate instead of the socket; the gate, not the semaphore, is what
# keeps us inside the quota. Scheduling only -- rotations are independent
# games, so this changes throughput and nothing about the results.
export BLUFFHOUSE_GOOGLE_CONCURRENCY=5
export BLUFFHOUSE_MISTRAL_CONCURRENCY=3
export BLUFFHOUSE_MISTRAL_MEDIUM_LATEST_RPM=50
export BLUFFHOUSE_GEMINI_3_1_FLASH_LITE_RPM=12

PUBLISHED="google:gemma-4-31b-it,mistral:mistral-medium-latest,random"
WIDE="google:gemma-4-31b-it,mistral:mistral-medium-latest,google:gemini-3.1-flash-lite,random"
HANDS="${HANDS:-8}"

case "${1:-redo}" in
  redo)     # every seed under one pinned prompt, in one window; seeds 41-42
            # are re-run rather than reused, so the bench is also a replication
            # test of the zero-message result
    uv run bluffhouse bench --models "$PUBLISHED" --hands "$HANDS" --mode 6 \
      --seeds "${SEEDS:-41,42,43,44,45,46,47,48}" --out runs/e1-pinned ;;
  extend)   # resume the published bench and add seeds; entrant set must match
    uv run bluffhouse bench --models "$PUBLISHED" --hands "$HANDS" --mode 6 \
      --seeds "${SEEDS:-41,42,43,44,45,46,47,48}" \
      --resume runs/e1-final/20260818-034855-seeds ;;
  wide)     # third model family; flash-lite's 500/day caps this to ~1 seed/day
    uv run bluffhouse bench --models "$WIDE" --hands "$HANDS" --mode 6 \
      --seeds "${SEEDS:-41,42}" --out runs/e1-wide ;;
  more)     # extend the CORRECTED pinned bench with fresh seeds. Resumes
            # runs/e1-ext (a copy of e1-pinned) so the published 8-seed
            # result survives intact if a longer run has to be abandoned.
            # Completed seed dirs are reused, so this only pays for new seeds.
    uv run bluffhouse bench --hands "$HANDS" --mode 6 \
      --seeds "${SEEDS:-41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57,58,59,60,61,62,63,64}" \
      --resume runs/e1-ext/20260818-160459-seeds ;;
  mode0)    # ladder floor on whatever seeds the mode-6 bench has
    uv run bluffhouse bench --models "$PUBLISHED" --hands "$HANDS" --mode 0 \
      --seeds "${SEEDS:-41,42,43,44,45,46,47,48}" --no-beliefs \
      --resume runs/e2-mode0/20260818-053716-seeds ;;
  *) echo "unknown: $1"; exit 1 ;;
esac
