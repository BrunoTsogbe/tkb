"""Génère le PDF UX (charte, parcours, wireframes) et les SVG des écrans.

Usage (depuis la racine du projet) :
    python ux/build.py
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader

import wireframes

HERE = Path(__file__).resolve().parent
OUTPUT_HTML = HERE / "ux_wireframes.html"
OUTPUT_PDF = HERE.parent / "ux_wireframes.pdf"
BROWSERS = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
)


def main() -> None:
    """Écrit les SVG, assemble le HTML et imprime le PDF."""
    document = (HERE / "document.html").read_text(encoding="utf-8")
    out_dir = HERE / "ecrans"
    out_dir.mkdir(exist_ok=True)
    for name, draw in wireframes.SCREENS.items():
        drawing = draw()
        (out_dir / f"{name}.svg").write_text(drawing, encoding="utf-8")
        document = document.replace("{{" + name + "}}", drawing)
    if "{{" in document:
        raise SystemExit("Un écran référencé dans document.html n'existe pas.")
    OUTPUT_HTML.write_text(document, encoding="utf-8")

    browser = next((b for b in BROWSERS if b.is_file()), None)
    if browser is None:
        raise SystemExit("Aucun navigateur Chromium trouvé pour imprimer le PDF.")
    profile = HERE / ".browser-profile"
    subprocess.run(
        [
            str(browser),
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
