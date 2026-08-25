"""Build the paper.

    uv run python paper/build.py            # submission (anonymous, line numbers)
    uv run python paper/build.py --final     # camera-ready (authors revealed)

Both builds come from the same main.tex; only the neurips_2026 package option
differs, so the two can never drift apart.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).parent

SUBMISSION = r"\usepackage[dblblindworkshop]{neurips_2026}"
FINAL = r"\usepackage[final,dblblindworkshop]{neurips_2026}"

# Words an author block carries without identifying anybody. "bluffhouse" is
# here because the contribution footnote names the system, which is meant to
# appear in both builds.
GENERIC = {
    "all", "and", "benchmarks", "bluffhouse", "carried", "computer", "computing",
    "contributed", "correspondence", "design", "engineering", "experimental",
    "for", "framework", "here", "houston", "implementation", "india",
    "mathematics", "of", "out", "reported", "research", "scientific",
    "solely", "the", "to", "university", "usa", "was", "writing",
}


def find_tectonic() -> str:
    """tectonic from $TECTONIC, then PATH, then a scratch download."""
    if env := os.environ.get("TECTONIC"):
        return env
    if found := shutil.which("tectonic"):
        return found
    scratch = Path(tempfile.gettempdir()) / "claude"
    for exe in sorted(scratch.glob("*/*/scratchpad/tectonic*")):
        if exe.is_file():
            return str(exe)
    return "tectonic"  # let the failure name the missing binary


def anon_markers(src: str) -> list[str]:
    """Every identifier the author block carries, read out of the block itself.

    A hardcoded list would put a tidy roster of names, emails and institutions
    in a file that ships in the repository, which is the one thing an
    anonymised mirror of that repository must not serve. Deriving the list
    keeps the check correct when the authors change and keeps the names in a
    single place: main.tex, which a mirror can simply omit.
    """
    block = re.search(r"\\author\{(.*?)\n\}", src, re.S)
    if not block:
        return []
    text = block.group(1)
    emails = set(re.findall(r"[\w.+-]+@[\w.-]+\.\w+", text.replace("\\_", "_")))
    markers = set(emails)
    for address in emails:
        local, _, domain = address.partition("@")
        markers.update({local, domain})
    stripped = re.sub(r"\\[a-zA-Z]+|[{}\\]", " ", text)
    markers.update(
        word
        for word in re.findall(r"[A-Z][\w-]{2,}", stripped)
        if word.lower() not in GENERIC
    )
    return sorted(markers)


def main() -> int:
    final = "--final" in sys.argv
    src = (HERE / "main.tex").read_text(encoding="utf-8")
    markers = anon_markers(src)
    if not markers:
        print("could not read the author block; anonymity is unchecked")
        return 1

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

    result = subprocess.run([find_tectonic(), tex], cwd=HERE)
    if result.returncode:
        return result.returncode

    pdf = HERE / (tex.replace(".tex", ".pdf"))
    try:
        from pypdf import PdfReader
    except ImportError:
        print(f"built {pdf.name} (install pypdf to verify anonymity)")
        return 0

    text = " ".join(p.extract_text() for p in PdfReader(str(pdf)).pages)
    # Kerning can split a run of glyphs, so a hyphenated institution comes back
    # from extraction with a stray space in it. A name broken that way is still
    # a name: match with whitespace removed on both sides.
    squashed = re.sub(r"\s+", "", text)

    def present(marker: str) -> bool:
        return marker in text or re.sub(r"\s+", "", marker) in squashed

    found = [m for m in markers if present(m)]
    if final:
        missing = [m for m in markers if not present(m)]
        print(f"built {pdf.name} (camera-ready)")
        print("  authors:", "all present" if not missing else f"MISSING {missing}")
    else:
        print(f"built {pdf.name} (submission)")
        if found:
            print(f"  ANONYMITY LEAK: {found} appear in the PDF")
            return 1
        print(f"  anonymity: none of {len(markers)} author identifiers in the PDF")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
