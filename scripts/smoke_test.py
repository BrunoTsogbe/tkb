"""Test de fumée de bout en bout sur une instance en marche (Docker Compose ou Render).

Usage :
    python scripts/smoke_test.py --url http://localhost:8000

Parcours : santé → inscription avec consentement → dépôt d'un WAV → traitement par le worker
(statut « done ») → page du résultat → image privée → historique → tableau de bord → export JSON.
Crée un compte jetable ``smoke-<horodatage>@exemple.fr``.
"""

from __future__ import annotations

import argparse
import io
import math
import re
import struct
import sys
import time
import wave

import requests

PASSWORD = "un-mot-de-passe-solide-42"
CSRF = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')


def make_wav(seconds: float = 2.0, rate: int = 8000) -> bytes:
    """Fabrique un WAV mono.

    Args:
        seconds: Durée.
        rate: Fréquence d'échantillonnage.

    Returns:
        Contenu du fichier.
    """
    frames = b"".join(struct.pack("<h", int(2000 * math.sin(i / 8))) for i in range(int(seconds * rate)))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return buffer.getvalue()


def check(condition: bool, label: str) -> None:
    """Affiche le résultat d'une étape et s'arrête au premier échec.

    Args:
        condition: Résultat attendu.
        label: Description de l'étape.
    """
    print(("  OK  " if condition else "  ÉCHEC ") + label)
    if not condition:
        sys.exit(1)


def main() -> None:
    """Déroule le parcours complet."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--url", default="http://localhost:8000")
    parser.add_argument("--timeout", type=float, default=120, help="Délai maximal du traitement (s)")
    base = parser.parse_args().url.rstrip("/")
    session = requests.Session()
    session.headers["Referer"] = base + "/"

    health = session.get(f"{base}/healthz/", timeout=10)
    check(health.status_code == 200 and health.json()["database"] == "ok", f"santé : {health.json()}")

    page = session.get(f"{base}/accounts/signup/", timeout=10)
    email = f"smoke-{int(time.time())}@exemple.fr"
    signup = session.post(
        f"{base}/accounts/signup/",
        data={
            "csrfmiddlewaretoken": CSRF.search(page.text).group(1),
            "email": email,
            "password1": PASSWORD,
            "password2": PASSWORD,
            "ai_consent": "on",
            "terms": "on",
        },
        timeout=10,
    )
    check("Se déconnecter" in signup.text, f"inscription et connexion ({email})")

    upload = session.post(
        f"{base}/dreams/",
        files={"audio": ("reve.wav", make_wav(), "audio/wav")},
        headers={"X-CSRFToken": session.cookies.get("csrftoken", ""), "Accept": "application/json"},
        timeout=30,
    )
    check(upload.status_code == 202, f"dépôt accepté ({upload.status_code})")
    detail_url = base + upload.json()["redirect"]

    started = time.monotonic()
    while time.monotonic() - started < parser.parse_args().timeout:
        fragment = session.get(detail_url + "status/", timeout=10).text
        if 'data-finished="1"' in fragment:
            break
        time.sleep(1)
    elapsed = time.monotonic() - started
    check('data-finished="1"' in fragment, f"traitement terminé par le worker en {elapsed:.1f} s")

    result = session.get(detail_url, timeout=10).text
    check("Image générée par IA" in result or "Image de substitution" in result, "page du résultat (image, ambiance)")
    image = session.get(detail_url + "image/", timeout=10)
    check(image.status_code == 200 and image.content[:4] == b"\x89PNG", "image servie au propriétaire")
    anonymous = requests.get(detail_url + "image/", timeout=10, allow_redirects=False)
    check(anonymous.status_code in {302, 404}, "image refusée à un visiteur anonyme")
    check(upload.json()["id"] in session.get(f"{base}/dreams/", timeout=10).text, "historique")
    check("Rêves racontés" in session.get(f"{base}/dashboard/", timeout=10).text, "tableau de bord")
    export = session.get(f"{base}/accounts/export/", timeout=10).json()
    check(len(export["dreams"]) == 1 and export["dreams"][0]["status"] == "done", "export JSON")
    print("Parcours complet validé.")


if __name__ == "__main__":
    main()
