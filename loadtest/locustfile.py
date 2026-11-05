"""Test de charge (KAN-29, specifications_architecture.pdf §5.4).

Scénario : 70 % de navigation (historique, filtres, tableau de bord, détail),
30 % de dépôt d'un rêve. Les fournisseurs d'IA sont simulés : aucun budget consommé.

Préparation des comptes :
    python app/manage.py seed_loadtest --users 50

Le serveur doit relever la limite anti-force brute (tous les utilisateurs virtuels partagent une IP) :
    LOGIN_RATE=100000/m python app/manage.py runserver

Lancement (paliers 5, 20, 50 utilisateurs) :
    python loadtest/run.py --host http://127.0.0.1:8000
"""

from __future__ import annotations

import io
import itertools
import math
import random
import re
import struct
import wave

from locust import HttpUser, between, task

PASSWORD = "charge-test-mot-de-passe-42"
_ids = itertools.count(1)
CSRF = re.compile(r'name="csrfmiddlewaretoken" value="([^"]+)"')
DREAM_LINK = re.compile(r'href="(/dreams/[0-9a-f-]{36}/)"')


def make_wav(seconds: float = 2.0, rate: int = 8000) -> bytes:
    """Petit WAV de test.

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


AUDIO = make_wav()


class Dreamer(HttpUser):
    """Un rêveur connecté qui consulte et dépose des rêves."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        """Connexion avec un compte préparé par ``seed_loadtest``."""
        email = f"charge{next(_ids)}@exemple.fr"
        page = self.client.get("/accounts/login/", name="connexion (formulaire)")
        token = CSRF.search(page.text)
        with self.client.post(
            "/accounts/login/",
            {"username": email, "password": PASSWORD, "csrfmiddlewaretoken": token.group(1) if token else ""},
            name="connexion",
            catch_response=True,
        ) as response:
            # Une connexion refusée fausserait toutes les mesures (pages de connexion au lieu des pages réelles).
            if "Se déconnecter" not in response.text:
                response.failure("connexion refusée : relever LOGIN_RATE pour le test de charge")
        self.dreams: list[str] = []

    def _csrf(self) -> str:
        return self.client.cookies.get("csrftoken", "")

    @task(3)
    def history(self) -> None:
        """Historique (et collecte des liens de détail)."""
        response = self.client.get("/dreams/", name="historique")
        self.dreams = DREAM_LINK.findall(response.text)[:10] or self.dreams

    @task(2)
    def filtered_history(self) -> None:
        """Historique filtré."""
        emotion = random.choice(["heureux", "stressant", "triste", "etrange", "neutre"])
        self.client.get(f"/dreams/?period=30&emotion={emotion}", name="historique filtré")

    @task(2)
    def dashboard(self) -> None:
        """Tableau de bord sur 30 jours."""
        self.client.get("/dashboard/", name="tableau de bord")

    @task(1)
    def detail(self) -> None:
        """Page d'un rêve."""
        if self.dreams:
            self.client.get(random.choice(self.dreams), name="détail d'un rêve")

    @task(3)
    def submit(self) -> None:
        """Dépôt d'un rêve (pipeline simulé)."""
        self.client.post(
            "/dreams/",
            files={"audio": ("reve.wav", AUDIO, "audio/wav")},
            headers={"X-CSRFToken": self._csrf(), "Accept": "application/json", "Referer": self.host + "/"},
            name="dépôt d'un rêve",
        )
