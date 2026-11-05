"""Imprime une page HTML de ``docs/`` en PDF (Edge ou Chrome en mode headless).

Usage (depuis la racine du projet) :
    python docs/build_pdf.py docs/aipd.html aipd_synthetiseur.pdf
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

from pypdf import PdfReader

BROWSERS = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
)


def main() -> None:
    """Convertit le fichier HTML donné en PDF."""
    source, target = Path(sys.argv[1]).resolve(), Path(sys.argv[2]).resolve()
    browser = next((b for b in BROWSERS if b.is_file()), None)
    if browser is None:
        raise SystemExit("Aucun navigateur Chromium trouvé.")
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [
                str(browser),
                "--headless=new",
                "--disable-gpu",
                "--no-pdf-header-footer",
                f"--user-data-dir={profile}",
                f"--print-to-pdf={target}",
                source.as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    print(f"{target.name} : {len(PdfReader(target).pages)} pages")


if __name__ == "__main__":
    main()
