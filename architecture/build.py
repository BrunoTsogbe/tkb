"""Génère les diagrammes SVG et le PDF « Spécifications et architecture ».

Usage (depuis la racine du projet) :
    python architecture/build.py

Le PDF est imprimé par Microsoft Edge ou Google Chrome en mode headless.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from pypdf import PdfReader

import diagrams

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
OUTPUT_HTML = HERE / "specifications_architecture.html"
OUTPUT_PDF = ROOT / "specifications_architecture.pdf"
MAX_PAGES = 10
BROWSERS = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
)


def find_browser() -> Path:
    """Trouve un navigateur Chromium installé.

    Returns:
        Chemin de l'exécutable.

    Raises:
        SystemExit: Si aucun navigateur n'est disponible.
    """
    for candidate in BROWSERS:
        if candidate.is_file():
            return candidate
    found = shutil.which("chromium") or shutil.which("google-chrome")
    if found:
        return Path(found)
    raise SystemExit("Aucun navigateur Chromium trouvé pour imprimer le PDF.")


def render_html() -> str:
    """Écrit les SVG et injecte les diagrammes dans le gabarit HTML.

    Returns:
        Le document HTML final.
    """
    document = (HERE / "document.html").read_text(encoding="utf-8")
    for name, draw in diagrams.ALL.items():
        drawing = draw()
        (HERE / "diagrammes" / f"{name}.svg").write_text(drawing, encoding="utf-8")
        document = document.replace("{{" + name + "}}", drawing)
    if "{{" in document:
        raise SystemExit("Un diagramme référencé dans document.html n'existe pas.")
    OUTPUT_HTML.write_text(document, encoding="utf-8")
    return document


def print_pdf(browser: Path) -> int:
    """Imprime le HTML en PDF et vérifie le nombre de pages.

    Args:
        browser: Exécutable Chromium.

    Returns:
        Nombre de pages du PDF.
    """
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
    return len(PdfReader(OUTPUT_PDF).pages)


def main() -> None:
    """Point d'entrée."""
    render_html()
    pages = print_pdf(find_browser())
    print(f"{OUTPUT_PDF.name} : {pages} pages")
    if pages > MAX_PAGES:
        sys.exit(f"Le document dépasse {MAX_PAGES} pages (contrainte du sujet).")


if __name__ == "__main__":
    main()
