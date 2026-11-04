"""Classification locale de l'ambiance d'un rêve (KAN-19).

- ``KeywordClassifier`` : repli toujours disponible (logique de la maquette).
- ``ZeroShotClassifier`` : modèle Hugging Face multilingue exécuté dans le worker,
  activé si ``transformers`` est installé ; choix final au spike KAN-39.
"""

from __future__ import annotations

import logging
import unicodedata
from typing import Any

from django.conf import settings

from .base import EmotionResult

logger = logging.getLogger(__name__)

KEYWORDS: dict[str, tuple[str, ...]] = {
    "heureux": ("joie", "rire", "riais", "soleil", "vol", "plage", "fete", "heureux", "sourire"),
    "stressant": ("peur", "poursuivi", "tomb", "retard", "examen", "perdu", "noir", "angoiss", "cri"),
    "triste": ("pleur", "seul", "adieu", "absent", "triste", "larme"),
    "etrange": ("bizarre", "flott", "transform", "etrange", "parl", "bizar"),
    "neutre": (),
}
NEUTRAL_BASELINE = 0.5
LABELS = {"heureux": "heureux", "stressant": "stressant", "triste": "triste", "étrange": "etrange", "neutre": "neutre"}


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


class KeywordClassifier:
    """Classifieur par mots-clés (repli, sans dépendance)."""

    provider = "local"
    model = "keywords-v1"
    paid = False

    def classify(self, text: str) -> EmotionResult:
        """Compte les mots indicateurs ; « neutre » reçoit une base fixe.

        Args:
            text: Texte du rêve.

        Returns:
            L'émotion la plus probable et la distribution.
        """
        normalized = _normalize(text)
        raw = {key: float(sum(normalized.count(k) for k in words)) for key, words in KEYWORDS.items()}
        raw["neutre"] = NEUTRAL_BASELINE
        total = sum(raw.values())
        scores = {key: round(value / total, 4) for key, value in raw.items()}
        return EmotionResult(key=max(scores, key=lambda k: scores[k]), scores=scores, model=self.model)


class ZeroShotClassifier:
    """Zero-shot multilingue (mDeBERTa-v3 XNLI) avec étiquettes françaises."""

    provider = "huggingface"
    paid = False
    _pipeline: Any = None

    def __init__(self) -> None:
        self.model = settings.EMOTION_HF_MODEL

    def _load(self) -> Any:
        if ZeroShotClassifier._pipeline is None:
            from transformers import pipeline  # import paresseux : dépendance lourde et optionnelle

            ZeroShotClassifier._pipeline = pipeline("zero-shot-classification", model=self.model, device=-1)
        return ZeroShotClassifier._pipeline

    def classify(self, text: str) -> EmotionResult:
        """Classe le texte parmi les cinq ambiances.

        Args:
            text: Texte du rêve.

        Returns:
            L'émotion la plus probable et la distribution.
        """
        output = self._load()(text, candidate_labels=list(LABELS), hypothesis_template="Ce rêve est {}.")
        scores = {
            LABELS[label]: round(float(score), 4)
            for label, score in zip(output["labels"], output["scores"], strict=True)
        }
        return EmotionResult(key=LABELS[output["labels"][0]], scores=scores, model=self.model)
