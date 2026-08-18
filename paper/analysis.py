"""Turn bench/sweep artifacts in runs/ into the paper's tables and numbers.

Usage:
    uv run python paper/analysis.py variance <sweep-dir>   # raw vs adjusted spread
    uv run python paper/analysis.py leaderboard <sweep-dir>
    uv run python paper/analysis.py bench <bench-dir>      # single-bench scorecard
"""

import json
import statistics
import sys
from pathlib import Path


def load_sweep(sweep_dir: Path) -> tuple[dict, list[dict]]:
    leaderboard = json.loads((sweep_dir / "leaderboard.json").read_text())
    benches = []
    for seed_dir in sorted(sweep_dir.glob("seed-*")):
        summary = seed_dir / "bench.json"
        if summary.exists():  # a seed still running has a dir but no summary
            benches.append(json.loads(summary.read_text()))
    return leaderboard, benches


def short(label: str) -> str:
    """'groq:openai/gpt-oss-120b#0' -> 'gpt-oss-120b'."""
    name = label.split("#")[0].split(":", 1)[-1]
    return name.split("/")[-1]


def variance(sweep_dir: Path) -> None:
    _, benches = load_sweep(sweep_dir)
    entrants = benches[0]["entrants"]
    print(f"{'entrant':16s} {'mean_raw':>9s} {'sd_raw':>8s} {'mean_adj':>9s} {'sd_adj':>8s} {'sd ratio':>8s}")
    ratios = []
    for e in entrants:
        raw = [b["scorecards"][e]["raw_chips"] for b in benches]
        adj = [b["scorecards"][e]["adjusted_chips"] for b in benches]
        sd_raw = statistics.stdev(raw) if len(raw) > 1 else 0.0
        sd_adj = statistics.stdev(adj) if len(adj) > 1 else 0.0
        ratio = sd_adj / sd_raw if sd_raw else float("nan")
        ratios.append(ratio)
        print(f"{short(e):16s} {statistics.mean(raw):9.1f} {sd_raw:8.1f} "
              f"{statistics.mean(adj):9.1f} {sd_adj:8.1f} {ratio:8.2f}")
    finite = [r for r in ratios if r == r]
    print(f"\nmean sd ratio (adjusted/raw): {statistics.mean(finite):.2f}")


PRETTY = {
    "gemma-4-31b-it": "Gemma-4-31B",
    "mistral-medium-latest": "Mistral Medium",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
    "random": r"\texttt{random} (control)",
}


def leaderboard(sweep_dir: Path) -> None:
    """Emit the paper's leaderboard rows, ready to paste into main.tex."""
    board, benches = load_sweep(sweep_dir)
    rows = sorted(
        board["leaderboard"].items(),
        key=lambda kv: -kv[1]["mean_adjusted_chips"],
    )
    print(f"% seeds: {board['seeds']}  hands: {board['num_hands']}  "
          f"mode: {board['mode']}")
    for e, row in rows:
        lo, hi = row["ci95"]
        name = short(e)
        cards = [b["scorecards"][e] for b in benches]

        def dim(d: str) -> str:
            return f"{statistics.mean(c['dimensions'].get(d, 0) for c in cards):.0f}"

        repairs = sum(c["counts"]["repairs"] for c in cards)
        faults = sum(c["counts"]["llm_faults"] for c in cards)
        print(f"{PRETTY.get(name, name)} & {row['mean_adjusted_chips']:+.1f} & "
              f"$[{lo:+.0f}, {hi:+.0f}]$ & {row['seed_wins']:.1f} & "
              f"{dim('poker_quality')} & {dim('belief_accuracy')} & "
              f"{repairs} & {faults}" + r" \\")

    print("\n% win-rate matrix")
    entrants = board["entrants"]
    print("      " + "  ".join(f"{short(e)[:10]:>10s}" for e in entrants))
    for a in entrants:
        cells = "  ".join(f"{board['win_rate_matrix'][a][b]:10.2f}" for b in entrants)
        print(f"{short(a)[:10]:>10s} {cells}")


def bench(bench_dir: Path) -> None:
    data = json.loads((Path(bench_dir) / "bench.json").read_text())
    for e, card in sorted(data["scorecards"].items(),
                          key=lambda kv: -kv[1]["adjusted_chips"]):
        c = card["counts"]
        print(f"{short(e):16s} adj={card['adjusted_chips']:+8.1f} raw={card['raw_chips']:+6d} "
              f"faults={c['llm_faults']:3d} repairs={c['repairs']:2d} "
              f"covert={c['covert_sent']:3d} caught={c['caught']:2d} "
              f"acc={c['accusations_made']:2d} msgs={c.get('messages', {})}")


def arms(run_dirs: Path) -> None:
    """Elicitation comparison across single-game run dirs.

    Pass a directory containing the run dirs to compare; each is reported as
    messages emitted, schema misses per phase, and channel mix.
    """
    from collections import Counter
    for run in sorted(Path(run_dirs).glob("*/events.jsonl")):
        d = run.parent
        evs = [json.loads(l) for l in run.open(encoding="utf-8")]
        msgs = [e for e in evs if e.get("type") == "message_sent"]
        mix = Counter(m["modality"] for m in msgs)
        misses: Counter = Counter()
        calls: Counter = Counter()
        for f in (d / "llm").glob("*.jsonl"):
            for line in f.open(encoding="utf-8"):
                r = json.loads(line)
                calls[r["phase"]] += 1
                if "wrong schema" in str(r.get("parse_error") or ""):
                    misses[r["phase"]] += 1
        print(f"{d.name:28s} msgs={len(msgs):3d} {dict(mix)} "
              f"schema_misses={dict(misses)} calls={dict(calls)}")


def retro(run_dirs: Path) -> None:
    """Recompute schema misses on transcripts recorded BEFORE the detector
    existed. Possible only because every provider reply is archived verbatim:
    the artifacts, not the code version, are the source of truth."""
    from bluffhouse.agents.llm import extract_json, schema_miss

    EXPECTED = {
        "comm": ("message", "channel", "intent", "surface"),
        "attention": ("watch", "table"),
        "beliefs": ("beliefs",),
    }
    for run in sorted(Path(run_dirs).glob("**/llm")):
        totals: dict[str, list[int]] = {p: [0, 0] for p in EXPECTED}
        for f in run.glob("*.jsonl"):
            for line in f.open(encoding="utf-8"):
                r = json.loads(line)
                phase = r.get("phase")
                if phase not in EXPECTED or not r.get("response_text"):
                    continue
                totals[phase][1] += 1
                try:
                    raw = extract_json(r["response_text"])
                except ValueError:
                    continue
                if schema_miss(raw, EXPECTED[phase]):
                    totals[phase][0] += 1
        if not any(t[1] for t in totals.values()):
            continue
        parts = " ".join(
            f"{p}={m}/{n}" for p, (m, n) in totals.items() if n
        )
        print(f"{str(run.parent)[-34:]:36s} schema misses: {parts}")


def channels(bench_dir: Path) -> None:
    """Per-entrant social-channel usage across all rotations of a bench."""
    data = json.loads((Path(bench_dir) / "bench.json").read_text())
    for e, card in sorted(data["scorecards"].items()):
        c = card["counts"]
        msgs = c.get("messages", {})
        total = sum(msgs.values())
        print(f"{short(e):24s} msgs={total:3d} {msgs} covert={c['covert_sent']} "
              f"noticed_against={c['covert_noticed']} caught_others={c['caught']} "
              f"beliefs={c.get('belief_updates', 0)}")


if __name__ == "__main__":
    cmd, target = sys.argv[1], Path(sys.argv[2])
    {"variance": variance, "leaderboard": leaderboard,
     "bench": bench, "channels": channels, "arms": arms,
     "retro": retro}[cmd](target)
