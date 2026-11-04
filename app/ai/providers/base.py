"""Contrats communs des fournisseurs d'IA (specifications_architecture.pdf §4.2).

Le métier ne dépend que de ces interfaces : changer de fournisseur revient à
écrire une classe et à modifier une variable d'environnement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class Transcript:
    """Résultat d'une transcription.

    Attributes:
        text: Texte transcrit.
        model: Modèle utilisé.
        billed_minutes: Minutes facturées (base du coût).
    """

    text: str
    model: str
    billed_minutes: Decimal


@dataclass(frozen=True)
class EmotionResult:
    """Résultat d'une classification d'ambiance.

    Attributes:
        key: Émotion retenue (clé du référentiel).
        scores: Probabilités par émotion (somme égale à 1).
        model: Modèle ou méthode utilisés.
    """

    key: str
    scores: dict[str, float] = field(default_factory=dict)
    model: str = ""


@dataclass(frozen=True)
class GeneratedImage:
    """Image produite par un fournisseur.

    Attributes:
        content: Octets PNG.
        model: Modèle utilisé.
        billed_images: Nombre d'images facturées.
    """

    content: bytes
    model: str
    billed_images: int = 1


class ProviderError(Exception):
    """Erreur d'un fournisseur.

    Attributes:
        code: Code d'erreur stable (stocké dans ``Dream.error_code``).
        retryable: Vrai si une nouvelle tentative a des chances d'aboutir.
        http_status: Code HTTP reçu, le cas échéant.
        retry_after: Délai suggéré par le fournisseur (secondes).
    """

    code = "provider_error"
    retryable = True

    def __init__(self, message: str, *, http_status: int | None = None, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.retry_after = retry_after


class ProviderTimeout(ProviderError):
    """Délai maximal dépassé."""

    code = "timeout"


class QuotaExceeded(ProviderError):
    """Limite de débit du fournisseur (HTTP 429)."""

    code = "quota_exceeded"


class InvalidRequest(ProviderError):
    """Requête refusée (400, 401, 413) : relancer ne servirait à rien."""

    code = "provider_error"
    retryable = False


class ContentRefused(ProviderError):
    """Refus de contenu par les filtres de sécurité du fournisseur."""

    code = "content_refused"
    retryable = False


class BudgetExhausted(ProviderError):
    """Le budget API ne permet plus cet appel (KAN-23)."""

    code = "budget_exhausted"
    retryable = False


class CircuitOpen(ProviderError):
    """Fournisseur suspendu après des échecs répétés (coupe-circuit)."""

    code = "provider_error"


class Transcriber(Protocol):
    """Transcription d'un fichier audio."""

    provider: str
    model: str

    def transcribe(self, audio: bytes, filename: str, *, duration_s: float | None = None) -> Transcript:
        """Transcrit un audio en texte français.

        Args:
            audio: Contenu du fichier.
            filename: Nom du fichier (l'extension indique le format).
            duration_s: Durée connue de l'audio, pour le calcul du coût.

        Returns:
            La transcription.
        """
        ...


class EmotionClassifier(Protocol):
    """Classification de l'ambiance d'un texte."""

    provider: str
    model: str

    def classify(self, text: str) -> EmotionResult:
        """Classe l'ambiance d'un texte de rêve.

        Args:
            text: Texte du rêve.

        Returns:
            L'émotion retenue et la distribution.
        """
        ...


class ImageGenerator(Protocol):
    """Génération d'une image à partir d'un prompt."""

    provider: str
    model: str

    def generate(self, prompt: str) -> GeneratedImage:
        """Génère une image carrée.

        Args:
            prompt: Description de l'image.

        Returns:
            L'image générée.
        """
        ...
