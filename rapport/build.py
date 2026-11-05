"""Génère le rapport technique PDF (KAN-31) avec les diagrammes de l'architecture.

Usage (depuis la racine du projet) :
    python rapport/build.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "architecture"))

import diagrams  # noqa: E402

OUTPUT_HTML = HERE / "rapport.html"
OUTPUT_PDF = HERE.parent / "rapport_tsogbe.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def main() -> None:
    """Injecte les diagrammes, puis imprime le PDF avec Edge."""
    document = (HERE / "document.html").read_text(encoding="utf-8")
    for name, draw in diagrams.ALL.items():
        document = document.replace("{{" + name + "}}", draw())
    if "{{" in document:
        raise SystemExit("Un diagramme référencé n'existe pas.")
    OUTPUT_HTML.write_text(document, encoding="utf-8")
    profile = HERE / ".browser-profile"
    subprocess.run(
        [
            str(EDGE),
            "--headless=new",
            "--disable-gpu",
            "--no-pdf-header-footer",
            "--virtual-time-budget=15000",
            f"--user-data-dir={profile}",
            f"--print-to-pdf={OUTPUT_PDF}",
            OUTPUT_HTML.as_uri(),
        ],
        check=True,
        capture_output=True,
    )
    shutil.rmtree(profile, ignore_errors=True)
    print(f"{OUTPUT_PDF.name} : {len(PdfReader(OUTPUT_PDF).pages)} pages")


if __name__ == "__main__":
    main()
