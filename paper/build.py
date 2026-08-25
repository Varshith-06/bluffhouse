"""Build the paper.

    uv run python paper/build.py            # submission (anonymous, line numbers)
    uv run python paper/build.py --final     # camera-ready (authors revealed)

Both builds come from the same main.tex; only the neurips_2026 package option
differs, so the two can never drift apart.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).parent
TECTONIC = shutil.which("tectonic") or str(
    Path.home()
    / "AppData/Local/Temp/claude/C--Users-Varshith-Documents-bluffhouse"
    / "73626d41-e02b-4bc4-af1c-5b65ecb37318/scratchpad/tectonic.exe"
)

SUBMISSION = r"\usepackage[dblblindworkshop]{neurips_2026}"
FINAL = r"\usepackage[final,dblblindworkshop]{neurips_2026}"
ANON_MARKERS = [
    "Paluru",
    "Chadalavada",
    "IIITM",
    "Gwalior",
    "Rice University",
    "iiitm.ac.in",
    "rice.edu",
    "saivarshith2006",
]


def main() -> int:
    final = "--final" in sys.argv
    src = (HERE / "main.tex").read_text(encoding="utf-8")

    if final:
        # only the uncommented package line, not the explanatory comments
        # lambda replacement: FINAL contains backslashes re.sub would eat
        src, n = re.subn(
            rf"(?m)^{re.escape(SUBMISSION)}$", lambda _: FINAL, src, count=1
        )
        if n != 1:
            print("could not find the submission \\usepackage line")
            return 1
        target = HERE / "main-camera-ready.tex"
        target.write_text(src, encoding="utf-8")
        tex = target.name
    else:
        tex = "main.tex"

    result = subprocess.run([TECTONIC, tex], cwd=HERE)
    if result.returncode:
        return result.returncode

    pdf = HERE / (tex.replace(".tex", ".pdf"))
    try:
        from pypdf import PdfReader
    except ImportError:
        print(f"built {pdf.name} (install pypdf to verify anonymity)")
        return 0

    text = " ".join(p.extract_text() for p in PdfReader(str(pdf)).pages)
    found = [m for m in ANON_MARKERS if m in text]
    if final:
        missing = [m for m in ANON_MARKERS if m not in text]
        print(f"built {pdf.name} (camera-ready)")
        print("  authors:", "all present" if not missing else f"MISSING {missing}")
    else:
        print(f"built {pdf.name} (submission)")
        if found:
            print(f"  ANONYMITY LEAK: {found} appear in the PDF")
            return 1
        print("  anonymity: no author identifiers in the PDF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
