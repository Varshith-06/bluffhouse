# Plan: bluffhouse → NeurIPS 2026 Workshop paper

Target: **Workshop on Evaluation of Interactive Agents @ NeurIPS 2026** (Atlanta, Dec 12–13).
Deadline: **Aug 29, 2026 AoE** (12 days from today, Aug 17). Submission: OpenReview
(`NeurIPS.cc/2026/Workshop/IAEval`). Double-blind, non-archival. Full papers ≤9 pages,
short papers ≤4 pages (both excluding references + appendices), official NeurIPS 2026 style.

## 1. Why this can get in, and how to frame it

The workshop's stated topics map almost one-to-one onto what bluffhouse already is:

| Workshop topic (verbatim from CFP) | bluffhouse's answer |
| --- | --- |
| Evaluation protocols for multi-turn / collaborative agents | Duplicate-poker protocol: rotations over identical seeded deals, adversity-adjusted chips |
| Trajectory-level evaluation (transcripts, tool calls, states, outcomes) | Append-only typed event log; ground truth vs. per-agent subjective projections |
| Grader design (deterministic checks, model-based rubrics, human eval) | **Judge-free by construction**: every metric is a mechanical count over events; intent-vs-surface gap makes deception measurable without any judge |
| Realistic simulation of interaction partners | Other frontier models *are* the interaction partners; scripted bots are free control conditions |
| Benchmarks for long-horizon interaction, memory, adaptation | Social memory across hands; codebooks set up in hand 1 pay off in hand 4; mode ladder isolates capabilities |
| Reliability across repeated trials | Byte-identical determinism given a seed; multi-seed sweeps with bootstrap CIs |

**Core pitch (one sentence):** most evaluations of social capability in LLMs depend on
LLM judges or human labels; bluffhouse shows you can measure deception, detection, and
information control *mechanically*, by (a) making the environment record the gap between
what an agent says and what it declares it means, (b) resolving perception with seeded
dice at emit time, and (c) cancelling luck with duplicate scoring so chips become a
skill metric.

Three named methodological contributions:
1. **Intent–surface split + resolve-at-emit perception** → ground truth for social
   events without judges (grader design).
2. **Duplicate rotations + adversity-adjusted chips + anonymized seats** → variance
   reduction and bias control for stochastic multi-agent games (evaluation protocol).
3. **The mode ladder** → capability isolation: the same entrants and seeds, with social
   physics added one channel at a time (benchmark design).

Paper length: **full paper, ~7–8 content pages** (limit 9). The contribution is a
benchmark + protocol; workshops expect real experiments, uncertainty estimates, and an
honest validity/limitations section more than they expect big-model SOTA tables.
This is a first-edition workshop (no prior accepted papers to imitate); the sibling
NeurIPS 2025 Multi-Turn Interactions workshop's accepted papers are the calibration:
focused contribution + modest but real experiments + good writing.

Proposed title: **"The House Always Records: Judge-Free Evaluation of Deception and
Social Skill in Multi-Agent LLM Play"** (working; alternatives in §6).

## 2a. Course corrections (Aug 18, after first live runs)

Two findings changed the experiment plan; both are recorded in the paper.

**Provider reality.** Groq's free tier caps each model at 200K tokens/day —
less than one duplicate cycle at ~9.5 calls/hand/seat — so GPT-OSS-120B and
Qwen were cut mid-flight. Cerebras is out of quota (payment required),
OpenRouter has $0 credits, and Gemini 3.6 Flash allows only 5 req/min. Final
roster: **Gemma-4-31B + Gemini 3.1 Flash Lite (Google) + Mistral Medium +
random control**, four seats. Harness gained per-*model* call pacing
(free-tier RPM caps are per model, not per provider).

**The schema-miss bug (now a paper contribution).** Mode-6 games produced
zero messages from every model. Cause: the system prompt mandated the
betting schema, so models answered the talk/attention/belief phases with
well-formed betting JSON. Missing `message` key → parsed as "chose silence",
logged as a clean call. The evaluator's prompt-design error was being
recorded as a model behavior. Fixed by (a) a phase-explicit system prompt
and (b) a `schema_miss` check that logs off-schema replies as faults in all
three non-betting phases. This generalizes: **a non-action must be
distinguishable from an off-schema action at parse time.** Written up as
§"Instrumenting non-decisions" plus experiment E5.

**Measured free-tier budgets (Aug 18).** These set the daily experiment
schedule; all are per calendar day and reset on the provider's clock.

| Model | Limit that binds | Practical capacity |
| --- | --- | --- |
| `gemma-4-31b-it` (Google) | 30 RPM | the workhorse; no daily wall hit yet |
| `gemini-3.1-flash-lite` (Google) | **500 requests/day** | ~1 duplicate cycle/day, then dead |
| `mistral-medium-latest` | generous | reliable second seat |
| `openai/gpt-oss-120b`, `qwen3.6-27b` (Groq) | 200K tokens/day | ~4 short games, then dead |
| Cerebras / OpenRouter | quota exhausted / $0 | unusable |

A 12-hand duplicate cycle costs ~80 provider calls per LLM seat per rotation
(~960 calls for a 3-LLM, 4-rotation bench). Runs are checkpointed per
rotation and resumable, so a bench can straddle a quota reset.

**E5 — Elicitation ablation:** anchored prompt vs phase-explicit prompt
(and an optional uniform social-framing nudge, `BLUFFHOUSE_SOCIAL_NUDGE=1`),
measuring schema-miss rate per phase and messages per game. Directly on the
workshop's "grader design" topic.

## 2b. Final experiment set (what actually ran)

| ID | What | Status |
| --- | --- | --- |
| E3 | Bots-only variance study, 10 seeds × 20 hands, zero tokens | **done** — paired design cuts SD to 0.21–0.47× naive |
| E5 | Elicitation arms: anchored / phase-explicit / +framing / +directive | **done** — 0, 0, 0, 19 messages; schema misses 27.7% → 0% |
| E1 | Mode-6 duplicate benchmark, gemma + mistral + random, seeds 41–42, 8 hands | **done** — Mistral +433.8, Gemma +141.0, random −574.8; zero messages, zero faults |
| E2 | Mode-0 floor, same entrants/seeds/decks → the ladder comparison | running |
| E4 | Case study from directed-arm logs | **done** — written from real intents |

Headline shape: the environment works, the protocol reduces variance as
designed, and the models decline the social layer entirely unless directed.

## 2. Experiments (constrained by free-tier API budgets)

Verified provider status (tested Aug 17):
- **Groq** (`openai/gpt-oss-120b`, `qwen/qwen3.6-27b`): works. ~1000 req/day, 8K tokens/min per model. The binding constraint.
- **Google AI Studio** (`gemini-3.6-flash`): works, free tier (RPD limit unknown, probe early).
- **Mistral** (`mistral-medium-latest`): works, most generous throughput.
- **Cerebras**: free quota exhausted — *payment required*. Unusable.
- **OpenRouter**: key valid but $0 credits / free tier → ~50 req/day. Unusable at benchmark scale.

Entrants (4 model families + 1 control):
`groq:openai/gpt-oss-120b`, `google:gemini-3.6-flash`, `mistral:mistral-medium-latest`,
`groq:qwen/qwen3.6-27b` (separate Groq rate pool), and `random` (zero-token control that
anchors the duplicate math). 5 entrants → 5 rotations per bench, 5-handed tables.

Measured cost: mock mode-6 game ≈ 3.75 calls/hand/seat (lower bound; assume ~6).
Per entrant per bench at 12 hands: 5 rot × 12 × 6 ≈ **360 calls**. Groq's 1000 RPD
allows ~2 benches/day per Groq model; runs are checkpointed per rotation and resumable.

- **E1 — Main table (mode 6):** seeds {41, 42, 43}, 12 hands. Headline leaderboard:
  adjusted chips + bootstrap CIs + scorecard dimensions (detection, information control,
  cover, discipline, belief accuracy, poker quality) + win-rate matrix.
- **E2 — Mode ladder:** modes {0, 2, 4, 6} (poker only → whispers → symbolic signals →
  full manipulation), seed 42, 12 hands. The capability-isolation figure: how each
  model's adjusted chips and social dimensions move as channels are added.
- **E3 — Validity checks (zero token cost):** bots-only duplicate benches (random /
  fold / check-call / all-in) showing luck cancellation (columns sum to zero, sensible
  bot ordering across seeds); determinism (byte-identical logs per mode, already
  tested); variance-reduction analysis: adjusted vs. raw chips spread across seeds.
- **E4 — Qualitative traces:** 1–2 boxed case studies mined from E1 logs (e.g. an
  intercepted whisper converted into a public accusation; a codebook set up and used
  hands later), each grounded in event-log excerpts with ground truth alongside.

Fallbacks if a provider dies mid-plan: drop qwen (4 entrants incl. bot), reduce E2 to
modes {0, 3, 6}, cut seeds to 2. E3/E4 are free and survive any provider failure.

## 3. Engineering tasks

1. Add `groq`, `cerebras`, `mistral`, `google` presets to `PRESETS` in
   `llm/openai_compat.py` + `LLM_PROVIDERS` in `harness/cli.py` (a few lines; Google's
   OpenAI-compatible base URL `https://generativelanguage.googleapis.com/v1beta/openai/`).
2. Smoke test: 1 bench, 2 hands, mode 6, all 5 entrants → verify JSON parse rates
   (qwen/gemini are thinking models; `extract_json` must find the final JSON), measure
   real calls+tokens/hand, latency, 429 behavior.
3. Tune provider concurrency / retries if 429s bite (openai SDK max_retries=3 already).
4. Launch E1/E2 as resumable background runs; monitor and resume across rate windows.
5. Analysis notebook/script: bench.json → LaTeX tables + matplotlib figures.

## 4. Paper skeleton (NeurIPS 2026 style, anonymized)

1. **Introduction** — solitaire evals vs. interactive social capability; the judge
  problem; contributions list.
2. **Related work** — social-deduction game benchmarks (Werewolf/Avalon/Hoodwinked/
   Diplomacy), LLM poker (PokerBench etc.), LLM-as-judge critiques, duplicate formats in
   games (duplicate bridge), agent evaluation surveys. (Verify all citations exist.)
3. **The environment** — truth vs. view; intent–surface split; resolve-at-emit
   perception (the receptions JSON as a figure); attention economy; mode ladder table;
   manipulation layer; determinism.
4. **The evaluation protocol** — duplicate rotations, anonymized seats,
   adversity-adjusted chips (formula), the judge-free scorecard dimensions, what is
   deliberately *not* scored and why.
5. **Experiments** — E3 validity first (the instrument works), then E1 leaderboard,
   E2 mode ladder, E4 case studies. Bootstrap CIs everywhere; per-provider token/cost
   accounting.
6. **Discussion & limitations** — perception model is dice not vision; social skill
   entangled with poker skill (mode 0 baseline subtracts this); prompt-format
   sensitivity; small-n seeds; free-tier model roster, not frontier-lab SOTA;
   contamination-resistance (seeded, procedurally generated).
7. **Conclusion**, references, **appendix**: full prompts, event schema, scorecard
   formulas, reproducibility statement, NeurIPS checklist.

Anonymization: no GitHub link, no author names, "code in supplementary / released on
publication". Keep the system name (standard practice; flag to author: the public repo
shares the name — acceptable under NeurIPS policy, reviewers are told not to search).

## 5. Toolchain

- LaTeX: Tectonic 0.17 (downloaded, verified compiling the official template).
- Style: official `neurips_2026.sty` + `neurips_2026.tex` + `checklist.tex` (downloaded
  from media.neurips.cc — matches the PDF the author placed in the repo).
- Figures: matplotlib (via `uv run --with matplotlib`), PDF vector output.
- Paper lives in `paper/` in the repo; build script included.

## 6. Timeline (deadline Aug 29)

- **Day 1 (Aug 17–18):** presets + smoke test; launch E1; write §3–§4 (no results needed).
- **Day 2–3:** E1 completes; launch E2; run E3; write §1, §2, §5-validity; first tables.
- **Day 4–5:** E2 completes; ladder figure; case-study mining; full draft; compile.
- **Day 6–7:** polish, checklist, appendix, page-limit pass, final PDF.
- Buffer: 5 days for rate-limit slippage / provider failures / author review.

Alternative titles: "Duplicate Poker for Language Models"; "Bluff, Whisper, Accuse:
A Judge-Free Benchmark for Social Manipulation in LLMs"; "Every Lie on the Record".

## 7. What the author must do themselves (I cannot)

- Create/confirm the OpenReview account and actually submit the PDF.
- Decide the author list + affiliations (kept out of the anonymized PDF).
- Confirm one author can attend in person (workshop expectation).
- Optionally: put a few dollars on Groq/Cerebras/OpenRouter to unlock bigger rosters.
