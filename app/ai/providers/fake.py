"""Doublures déterministes des fournisseurs (développement, démo, tests).

Aucune clé, aucun coût : le même audio donne toujours le même texte.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal

from ..fallback import render_fallback
from .base import GeneratedImage, Transcript

SAMPLES = (
    "Je volais au-dessus d'une forêt endormie, le soleil se levait et je riais de joie.",
    "J'étais en retard pour un examen, je courais dans des couloirs sans fin et j'avais peur.",
    "Je marchais dans une ville où les maisons flottaient, un chat me parlait, c'était bizarre.",
    "Je me promenais au marché, j'achetais du pain puis je rentrais chez moi.",
    "Mon grand-père était absent de la maison, je me sentais seul et j'avais envie de pleurer.",
)


class FakeTranscriber:
    """Transcription simulée."""

    provider = "fake"
    model = "fake-stt"
    paid = False

    def transcribe(self, audio: bytes, filename: str, *, duration_s: float | None = None) -> Transcript:
        """Renvoie un texte d'exemple choisi d'après l'empreinte de l'audio.

        Args:
            audio: Contenu du fichier.
            filename: Nom du fichier (ignoré).
            duration_s: Durée de l'audio.

        Returns:
            Une transcription d'exemple.
        """
        index = int(hashlib.sha256(audio).hexdigest()[:8], 16) % len(SAMPLES)
        minutes = Decimal(str(duration_s or 120)) / Decimal(60)
        return Transcript(text=SAMPLES[index], model=self.model, billed_minutes=minutes)


class FakeImageGenerator:
    """Génération d'image simulée (paysage nocturne local)."""

    provider = "fake"
    model = "fake-image"
    paid = False

    def generate(self, prompt: str) -> GeneratedImage:
        """Dessine un paysage déterministe d'après le prompt.

        Args:
            prompt: Description de l'image.

        Returns:
            Une image PNG.
        """
        return GeneratedImage(content=render_fallback(prompt, size=512), model=self.model)
