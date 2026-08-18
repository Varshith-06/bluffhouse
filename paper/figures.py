"""Paper figures. Vector PDFs into paper/figures/.

Usage:
  uv run --with matplotlib python paper/figures.py mock       # layout check
  uv run --with matplotlib python paper/figures.py real       # from runs/
"""

import json
import statistics
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# validated categorical palette (dataviz default, light mode);
# the bot control is a neutral gray reference, not a competing identity
COLORS = {
    "gemma-4-31b-it": "#2a78d6",
    "mistral-medium-latest": "#eb6834",
    "gemini-3.1-flash-lite": "#1baf7a",
    "random": "#757570",
}
MARKERS = {
    "gemma-4-31b-it": "o",
    "mistral-medium-latest": "s",
    "gemini-3.1-flash-lite": "^",
    "random": "x",
}
LABELS = {
    "gemma-4-31b-it": "Gemma-4-31B",
    "mistral-medium-latest": "Mistral Medium",
    "gemini-3.1-flash-lite": "Gemini 3.1 Flash Lite",
    "random": "random bot",
}
ORDER = list(COLORS)

plt.rcParams.update({
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8,
    "xtick.labelsize": 7, "ytick.labelsize": 7,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": "#e6e6e3", "grid.linewidth": 0.5,
    "axes.axisbelow": True, "pdf.fonttype": 42,
})

FIGDIR = Path(__file__).parent / "figures"
FIGDIR.mkdir(exist_ok=True)


def short(label: str) -> str:
    return label.split("#")[0].split(":", 1)[-1].split("/")[-1]


def bench_scores(bench_dir: Path) -> dict[str, float]:
    data = json.loads((bench_dir / "bench.json").read_text())
    return {short(e): card["adjusted_chips"] for e, card in data["scorecards"].items()}


def find_bench(root: str) -> Path | None:
    hits = sorted(Path("runs").glob(f"{root}/*/bench.json"))
    return hits[-1].parent if hits else None


def _seed_benches(root: str) -> dict[int, Path]:
    """seed -> bench dir for a sweep written under runs/<root>/<stamp>/seed-*."""
    out = {}
    for f in sorted(Path("runs").glob(f"{root}/*/seed-*/bench.json")):
        out[int(f.parent.name.split("-")[1])] = f.parent
    return out


def ladder_data_real() -> dict[str, dict[int, float]]:
    """mode -> entrant -> adjusted chips, averaged over whatever seeds ran
    at BOTH modes so the comparison stays paired."""
    floor, top = _seed_benches("e2-mode0"), _seed_benches("e1-final")
    shared = sorted(set(floor) & set(top))
    out: dict[str, dict[int, float]] = {}
    for mode, source in ((0, floor), (6, top)):
        acc: dict[str, list[float]] = {}
        for seed in shared:
            for e, v in bench_scores(source[seed]).items():
                acc.setdefault(e, []).append(v)
        for e, vals in acc.items():
            out.setdefault(e, {})[mode] = sum(vals) / len(vals)
    return out


def ladder_data_mock() -> dict[str, dict[int, float]]:
    return {
        "gemma-4-31b-it": {0: 40, 2: 55, 4: 30, 6: 80},
        "gemini-3.1-flash-lite": {0: 90, 2: 70, 4: 95, 6: 120},
        "mistral-medium-latest": {0: 10, 2: -5, 4: 20, 6: -40},
        "random": {0: -140, 2: -120, 4: -145, 6: -160},
    }


def fig_ladder(data: dict[str, dict[int, float]]) -> None:
    if not any(pts for pts in data.values()):
        print("ladder: no paired modes available yet, skipping")
        return
    fig, ax = plt.subplots(figsize=(5.5, 2.6))
    for e in ORDER:
        pts = data.get(e, {})
        if not pts:
            continue
        xs = sorted(pts)
        ys = [pts[x] for x in xs]
        ax.plot(xs, ys, color=COLORS[e], marker=MARKERS[e], linewidth=1.6,
                markersize=4.5, label=LABELS[e],
                linestyle="--" if e == "random" else "-")
        ax.annotate(LABELS[e], (xs[-1], ys[-1]), xytext=(6, 0),
                    textcoords="offset points", va="center", fontsize=7,
                    color="#3a3a37")
    ax.axhline(0, color="#c9c9c4", linewidth=0.8)
    modes = sorted({m for pts in data.values() for m in pts})
    ax.set_xticks(modes)
    names = {0: "0\npure poker", 2: "2\n+ whispers", 4: "4\n+ signals",
             6: "6\nfull manipulation"}
    ax.set_xticklabels([names.get(m, str(m)) for m in modes])
    ax.set_ylabel("adjusted chips")
    ax.set_xlim(modes[0] - 0.3, modes[-1] + 2.6)
    fig.tight_layout()
    fig.savefig(FIGDIR / "ladder.pdf")
    print("wrote", FIGDIR / "ladder.pdf")


def leaderboard_data_real() -> list[tuple[str, float, float, float]]:
    """(entrant, mean, min, max) over the E1 seeds."""
    per: dict[str, list[float]] = {}
    for pattern in ("e1-final/*/seed-*/bench.json",):
        for f in sorted(Path("runs").glob(pattern)):
            for e, v in bench_scores(f.parent).items():
                per.setdefault(e, []).append(v)
    rows = []
    for e, vals in per.items():
        m = statistics.mean(vals)
        s = statistics.stdev(vals) if len(vals) > 1 else 0.0
        rows.append((e, m, min(vals), max(vals)))
    return sorted(rows, key=lambda r: -r[1])


def leaderboard_data_mock() -> list[tuple[str, float, float, float]]:
    return [("gemini-3.1-flash-lite", 120, 60, 180),
            ("gemma-4-31b-it", 80, 20, 130),
            ("mistral-medium-latest", -40, -90, 10),
            ("random", -160, -220, -110)]


def fig_leaderboard(rows: list[tuple[str, float, float, float]]) -> None:
    fig, ax = plt.subplots(figsize=(5.5, 1.8))
    ys = range(len(rows), 0, -1)
    for y, (e, m, lo, hi) in zip(ys, rows):
        ax.plot([lo, hi], [y, y], color=COLORS.get(e, "#999"), linewidth=1.6)
        ax.plot([m], [y], marker=MARKERS.get(e, "o"),
                color=COLORS.get(e, "#999"), markersize=5.5)
        ax.annotate(f"{m:+.0f}", (m, y), xytext=(0, 6),
                    textcoords="offset points", ha="center", fontsize=7,
                    color="#3a3a37")
    ax.axvline(0, color="#c9c9c4", linewidth=0.8)
    ax.set_yticks(list(ys))
    ax.set_yticklabels([LABELS.get(e, e) for e, *_ in rows])
    ax.set_xlabel("adjusted chips, mode 6 (mean and range over seeds)")
    fig.tight_layout()
    fig.savefig(FIGDIR / "leaderboard.pdf")
    print("wrote", FIGDIR / "leaderboard.pdf")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "mock"
    if mode == "mock":
        fig_ladder(ladder_data_mock())
        fig_leaderboard(leaderboard_data_mock())
    else:
        fig_ladder(ladder_data_real())
        fig_leaderboard(leaderboard_data_real())
