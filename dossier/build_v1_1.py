"""Assemble la version 1.1 du dossier de cadrage : original intact + page de mise à jour.

Usage (depuis la racine du projet) :
    python dossier/build_v1_1.py
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from pypdf import PdfReader, PdfWriter

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
ORIGINAL = ROOT / "dossier_cadrage.pdf"
OUTPUT = ROOT / "dossier_cadrage_v1.1.pdf"
EDGE = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")


def main() -> None:
    """Imprime la page de mise à jour et la concatène à l'original."""
    with tempfile.TemporaryDirectory() as tmp:
        addendum = Path(tmp) / "addendum.pdf"
        subprocess.run(
            [
                str(EDGE),
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--user-data-dir={Path(tmp) / 'profile'}",
                f"--print-to-pdf={addendum}",
                (HERE / "addendum_v1_1.html").as_uri(),
            ],
            check=True,
            capture_output=True,
        )
        writer = PdfWriter()
        for source in (ORIGINAL, addendum):
            for page in PdfReader(source).pages:
                writer.add_page(page)
        writer.add_metadata({"/Title": "Synthétiseur de rêves – Dossier de cadrage v1.1", "/Author": "Bruno Tsogbe"})
        with OUTPUT.open("wb") as handle:
            writer.write(handle)
    pages = len(PdfReader(OUTPUT).pages)
    print(f"{OUTPUT.name} : {pages} pages (dont {len(PdfReader(ORIGINAL).pages)} d'origine)")


if __name__ == "__main__":
    main()
