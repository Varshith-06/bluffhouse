"""Build the paper.

    uv run python paper/build.py

Builds main.pdf from main.tex and checks the author block reached the PDF.
"""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).parent

# Words in the author block that are not worth checking for. "bluffhouse" is
# here because the contribution footnote names the system.
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


def author_markers(src: str) -> list[str]:
    """Every identifier the author block carries, read out of the block itself."""
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
    src = (HERE / "main.tex").read_text(encoding="utf-8")
    markers = author_markers(src)
    if not markers:
        print("could not read the author block")
        return 1

    result = subprocess.run([find_tectonic(), "main.tex"], cwd=HERE)
    if result.returncode:
        return result.returncode

    pdf = HERE / "main.pdf"
    try:
        from pypdf import PdfReader
    except ImportError:
        print(f"built {pdf.name} (install pypdf to verify the authors)")
        return 0

    text = " ".join(p.extract_text() for p in PdfReader(str(pdf)).pages)
    # Kerning can split a run of glyphs, so a hyphenated institution comes back
    # from extraction with a stray space in it. A name broken that way is still
    # a name: match with whitespace removed on both sides.
    squashed = re.sub(r"\s+", "", text)
    missing = [m for m in markers if re.sub(r"\s+", "", m) not in squashed]
    print(f"built {pdf.name}")
    print("  authors:", "all present" if not missing else f"MISSING {missing}")
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
