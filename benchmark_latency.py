"""Mesure de latence des APIs candidates (STT, image, TTS).

Usage:
    python benchmark_latency.py --audio sample.mp3 --runs 5
    python benchmark_latency.py --dry-run          # sans clé API, simule les appels

Les clés sont lues dans l'environnement (voir .env.example) :
    OPENAI_API_KEY, DEEPGRAM_API_KEY, ASSEMBLYAI_API_KEY

Les résultats sont écrits dans latency_results.csv et à reporter dans
benchmark.xlsx (colonne « Temps de réponse »).
"""

from __future__ import annotations

import argparse
import csv
import os
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import requests

TIMEOUT_S = 60
POLL_INTERVAL_S = 1.0


def load_dotenv(path: Path = Path(".env")) -> None:
    """Charge un fichier ``.env`` simple (CLE=valeur) dans l'environnement.

    Les variables déjà définies ne sont pas écrasées. Aucune dépendance
    externe n'est nécessaire.

    Args:
        path: Chemin du fichier ``.env``.
    """
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass
class Result:
    """Résultat agrégé de N appels pour un fournisseur.

    Attributes:
        provider: Nom du fournisseur et du modèle.
        kind: Catégorie (stt, image, tts).
        latencies: Durées en secondes des appels réussis.
        errors: Nombre d'appels en échec.
    """

    provider: str
    kind: str
    latencies: list[float]
    errors: int

    def summary(self) -> dict[str, float | str | int]:
        """Retourne les statistiques de latence.

        Returns:
            Dictionnaire avec moyenne, médiane, p95 et nombre d'erreurs.
        """
        if not self.latencies:
            return {
                "provider": self.provider,
                "kind": self.kind,
                "mean_s": "",
                "median_s": "",
                "p95_s": "",
                "errors": self.errors,
            }
        ordered = sorted(self.latencies)
        p95_index = max(0, int(round(0.95 * len(ordered))) - 1)
        return {
            "provider": self.provider,
            "kind": self.kind,
            "mean_s": round(statistics.mean(ordered), 3),
            "median_s": round(statistics.median(ordered), 3),
            "p95_s": round(ordered[p95_index], 3),
            "errors": self.errors,
        }


def timed(call: Callable[[], None], runs: int, provider: str, kind: str) -> Result:
    """Exécute ``call`` plusieurs fois et mesure la durée de chaque appel.

    Args:
        call: Fonction sans argument qui effectue un appel API.
        runs: Nombre de répétitions.
        provider: Libellé du fournisseur.
        kind: Catégorie de l'API.

    Returns:
        Un ``Result`` agrégé.
    """
    latencies: list[float] = []
    errors = 0
    for _ in range(runs):
        start = time.perf_counter()
        try:
            call()
            latencies.append(time.perf_counter() - start)
        except (requests.RequestException, RuntimeError) as exc:
            errors += 1
            print(f"[{provider}] erreur : {exc}")
    return Result(provider, kind, latencies, errors)


def openai_stt(audio: Path, model: str = "gpt-transcribe") -> Callable[[], None]:
    """Construit un appel de transcription OpenAI.

    Args:
        audio: Fichier audio local.
        model: Identifiant du modèle de transcription.

    Returns:
        Fonction qui exécute l'appel.
    """

    def _call() -> None:
        with audio.open("rb") as handle:
            resp = requests.post(
                "https://api.openai.com/v1/audio/transcriptions",
                headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
                files={"file": handle},
                data={"model": model},
                timeout=TIMEOUT_S,
            )
        resp.raise_for_status()

    return _call


def deepgram_stt(audio: Path) -> Callable[[], None]:
    """Construit un appel de transcription Deepgram (Nova-3).

    Args:
        audio: Fichier audio local.

    Returns:
        Fonction qui exécute l'appel.
    """

    def _call() -> None:
        resp = requests.post(
            "https://api.deepgram.com/v1/listen?model=nova-3&language=fr",
            headers={"Authorization": f"Token {os.environ['DEEPGRAM_API_KEY']}", "Content-Type": "audio/mpeg"},
            data=audio.read_bytes(),
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()

    return _call


def assemblyai_stt(audio: Path) -> Callable[[], None]:
    """Construit un appel de transcription AssemblyAI (Universal-2, asynchrone).

    L'appel complet est mesuré : envoi du fichier, création de la
    transcription puis interrogation jusqu'au résultat.

    Args:
        audio: Fichier audio local.

    Returns:
        Fonction qui exécute l'appel.
    """
    base = "https://api.assemblyai.com/v2"

    def _call() -> None:
        headers = {"authorization": os.environ["ASSEMBLYAI_API_KEY"]}
        upload = requests.post(f"{base}/upload", headers=headers, data=audio.read_bytes(), timeout=TIMEOUT_S)
        upload.raise_for_status()
        job = requests.post(
            f"{base}/transcript",
            headers=headers,
            json={"audio_url": upload.json()["upload_url"], "language_code": "fr", "speech_model": "universal"},
            timeout=TIMEOUT_S,
        )
        job.raise_for_status()
        deadline = time.monotonic() + TIMEOUT_S
        while time.monotonic() < deadline:
            status = requests.get(f"{base}/transcript/{job.json()['id']}", headers=headers, timeout=TIMEOUT_S)
            status.raise_for_status()
            state = status.json()["status"]
            if state == "completed":
                return
            if state == "error":
                raise RuntimeError(status.json().get("error", "échec AssemblyAI"))
            time.sleep(POLL_INTERVAL_S)
        raise RuntimeError(f"délai de {TIMEOUT_S} s dépassé")

    return _call


def openai_image(prompt: str, model: str = "gpt-image-1-mini") -> Callable[[], None]:
    """Construit un appel de génération d'image OpenAI.

    Args:
        prompt: Description de l'image.
        model: Identifiant du modèle d'image.

    Returns:
        Fonction qui exécute l'appel.
    """

    def _call() -> None:
        resp = requests.post(
            "https://api.openai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": model, "prompt": prompt, "size": "1024x1024", "quality": "medium"},
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()

    return _call


def openai_tts(text: str, model: str = "tts-1") -> Callable[[], None]:
    """Construit un appel de synthèse vocale OpenAI.

    Args:
        text: Texte à lire.
        model: Identifiant du modèle TTS.

    Returns:
        Fonction qui exécute l'appel.
    """

    def _call() -> None:
        resp = requests.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"},
            json={"model": model, "voice": "alloy", "input": text},
            timeout=TIMEOUT_S,
        )
        resp.raise_for_status()

    return _call


def fake_call(delay: float) -> Callable[[], None]:
    """Appel simulé pour le mode ``--dry-run``.

    Args:
        delay: Durée simulée en secondes.

    Returns:
        Fonction qui dort ``delay`` secondes.
    """
    return lambda: time.sleep(delay)


def build_plan(args: argparse.Namespace) -> list[tuple[str, str, Callable[[], None]]]:
    """Construit la liste des appels à mesurer selon les clés disponibles.

    Args:
        args: Arguments de la ligne de commande.

    Returns:
        Liste de tuples (fournisseur, catégorie, appel).
    """
    if args.dry_run:
        return [
            ("dry-run STT", "stt", fake_call(0.05)),
            ("dry-run image", "image", fake_call(0.08)),
            ("dry-run TTS", "tts", fake_call(0.03)),
        ]
    plan: list[tuple[str, str, Callable[[], None]]] = []
    audio = Path(args.audio) if args.audio else None
    if os.getenv("OPENAI_API_KEY"):
        if audio:
            plan.append(("OpenAI gpt-transcribe", "stt", openai_stt(audio)))
        plan.append(("OpenAI gpt-image-1-mini", "image", openai_image("Un rêve de forêt flottante, style aquarelle")))
        plan.append(("OpenAI tts-1", "tts", openai_tts("Je volais au-dessus d'une forêt endormie.")))
    if os.getenv("DEEPGRAM_API_KEY") and audio:
        plan.append(("Deepgram nova-3", "stt", deepgram_stt(audio)))
    if os.getenv("ASSEMBLYAI_API_KEY") and audio:
        plan.append(("AssemblyAI universal-2", "stt", assemblyai_stt(audio)))
    return plan


def main() -> None:
    """Point d'entrée : exécute le plan de mesure et écrit le CSV."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--audio", help="Fichier audio de test (.mp3/.wav, ~2 min)")
    parser.add_argument("--runs", type=int, default=5, help="Nombre d'appels par API")
    parser.add_argument("--out", default="latency_results.csv")
    parser.add_argument("--dry-run", action="store_true", help="Simule les appels (sans clé)")
    args = parser.parse_args()

    load_dotenv()
    plan = build_plan(args)
    if not plan:
        raise SystemExit("Aucune API à mesurer : définissez des clés d'API ou utilisez --dry-run.")

    rows = [timed(call, args.runs, name, kind).summary() for name, kind, call in plan]
    with open(args.out, "w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["provider", "kind", "mean_s", "median_s", "p95_s", "errors"])
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        print(row)


if __name__ == "__main__":
    main()
