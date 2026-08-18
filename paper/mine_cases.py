"""Mine finished runs for paper-worthy social traces.

Usage: uv run python paper/mine_cases.py <runs-glob>
e.g.   uv run python paper/mine_cases.py "runs/e1-mode6/**/rotation-*"

Reports, per run: covert messages with interceptions (fragments), the
declared intent beside the surface, accusations (and whether the accuser
had caught a fragment earlier), notes read by bystanders, and codebook
setups (whispers that mention gestures/signals).
"""

import glob
import json
import sys
from pathlib import Path

SIGNAL_WORDS = ("tap", "signal", "gesture", "code", "scratch", "cough",
                "glance", "wink", "chip", "stack")


def scan(run_dir: Path) -> None:
    events_file = run_dir / "events.jsonl"
    if not events_file.exists():
        return
    events = [json.loads(l) for l in events_file.open(encoding="utf-8")]
    msgs = [e for e in events if e.get("type") == "message_sent"]
    interesting = []
    fragment_catchers: dict[str, list] = {}

    for e in msgs:
        recs = e.get("receptions", {})
        frags = {a: r for a, r in recs.items()
                 if r.get("outcome") == "fragment"}
        covert = e.get("modality") not in ("speech", "accusation")
        if covert and frags:
            interesting.append(("INTERCEPTED", e, frags))
            for agent in frags:
                fragment_catchers.setdefault(agent, []).append(e)
        if e.get("modality") == "accusation":
            prior = fragment_catchers.get(e.get("sender"), [])
            interesting.append(("ACCUSATION" + ("+PRIOR-FRAGMENT" if prior else ""), e, {}))
        if e.get("modality") == "note" and any(
            r.get("outcome") == "fragment" for a, r in recs.items()
            if a not in e.get("targets", [])
        ):
            interesting.append(("NOTE-READ", e, {}))
        if covert and any(w in (e.get("text") or "").lower() for w in SIGNAL_WORDS):
            interesting.append(("CODEBOOK?", e, {}))

    if not interesting:
        return
    print(f"\n=== {run_dir} ===")
    for tag, e, frags in interesting:
        print(f"[hand {e.get('hand_no')}] {tag} {e.get('sender')} -> {e.get('targets')} ({e.get('modality')})")
        print(f"   surface: {(e.get('text') or '')[:160]}")
        print(f"   intent:  {(e.get('intent') or '')[:160]}")
        for agent, r in frags.items():
            print(f"   caught by {agent} ({r.get('confidence', 0):.2f}): {(r.get('text') or '')[:120]}")


if __name__ == "__main__":
    pattern = sys.argv[1] if len(sys.argv) > 1 else "runs/**/rotation-*"
    for d in sorted(glob.glob(pattern, recursive=True)):
        scan(Path(d))
