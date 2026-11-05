"""Fournisseur OpenAI : transcription (``gpt-transcribe``) et image (``gpt-image-1-mini``)."""

from __future__ import annotations

import base64
from decimal import Decimal
from typing import Any

import httpx
from django.conf import settings

from .base import (
    ContentRefused,
    GeneratedImage,
    InvalidRequest,
    ProviderError,
    ProviderTimeout,
    QuotaExceeded,
    Transcript,
)

CONTENT_POLICY_CODES = {"content_policy_violation", "moderation_blocked"}
DEFAULT_MINUTES = Decimal(2)


def _client(timeout_s: float, transport: httpx.BaseTransport | None = None) -> httpx.Client:
    return httpx.Client(
        base_url=settings.OPENAI_BASE_URL,
        headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
        timeout=httpx.Timeout(timeout_s, connect=10.0),
        transport=transport,
    )


def _raise_for(response: httpx.Response) -> None:
    """Traduit une réponse HTTP en erreur typée.

    Args:
        response: Réponse reçue.

    Raises:
        QuotaExceeded: Sur 429.
        ContentRefused: Sur refus des filtres de sécurité.
        InvalidRequest: Sur 400, 401, 403, 404 ou 413.
        ProviderError: Sur toute autre erreur (5xx : relançable).
    """
    if response.is_success:
        return
    try:
        error = response.json().get("error") or {}
    except ValueError:
        error = {}
    message = str(error.get("message") or f"HTTP {response.status_code}")[:200]
    status = response.status_code
    if status == 429:
        retry_after = response.headers.get("Retry-After")
        raise QuotaExceeded(message, http_status=status, retry_after=float(retry_after) if retry_after else None)
    if error.get("code") in CONTENT_POLICY_CODES or error.get("type") in CONTENT_POLICY_CODES:
        raise ContentRefused(message, http_status=status)
    if status in {400, 401, 403, 404, 413}:
        raise InvalidRequest(message, http_status=status)
    raise ProviderError(message, http_status=status)


def _post(client: httpx.Client, path: str, **kwargs: Any) -> dict[str, Any]:
    try:
        response = client.post(path, **kwargs)
    except httpx.TimeoutException as exc:
        raise ProviderTimeout("Le fournisseur n'a pas répondu à temps.") from exc
    except httpx.HTTPError as exc:
        raise ProviderError(f"Erreur réseau : {exc.__class__.__name__}") from exc
    _raise_for(response)
    try:
        return response.json()
    except ValueError as exc:
        raise ProviderError("Réponse illisible du fournisseur.") from exc


class OpenAITranscriber:
    """Transcription par l'API OpenAI."""

    provider = "openai"

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.model = settings.OPENAI_STT_MODEL
        self.transport = transport

    def transcribe(self, audio: bytes, filename: str, *, duration_s: float | None = None) -> Transcript:
        """Transcrit un audio en français.

        Args:
            audio: Contenu du fichier.
            filename: Nom du fichier.
            duration_s: Durée connue de l'audio.

        Returns:
            Le texte et les minutes facturées.
        """
        with _client(settings.AI_STT_TIMEOUT_S, self.transport) as client:
            data = _post(
                client,
                "/audio/transcriptions",
                files={"file": (filename, audio)},
                data={"model": self.model, "language": "fr", "response_format": "json"},
            )
        text = str(data.get("text", "")).strip()
        if not text:
            raise InvalidRequest("Aucune parole détectée dans l'enregistrement.")
        usage_seconds = (data.get("usage") or {}).get("seconds")
        seconds = duration_s if duration_s is not None else usage_seconds
        minutes = Decimal(str(seconds)) / Decimal(60) if seconds is not None else DEFAULT_MINUTES
        return Transcript(text=text, model=self.model, billed_minutes=minutes)


class OpenAIImageGenerator:
    """Génération d'image par l'API OpenAI."""

    provider = "openai"

    def __init__(self, transport: httpx.BaseTransport | None = None) -> None:
        self.model = settings.OPENAI_IMAGE_MODEL
        self.transport = transport

    def generate(self, prompt: str) -> GeneratedImage:
        """Génère une image 1024×1024 de qualité moyenne.

        Args:
            prompt: Description de l'image.

        Returns:
            L'image PNG.
        """
        with _client(settings.AI_IMAGE_TIMEOUT_S, self.transport) as client:
            data = _post(
                client,
                "/images/generations",
                json={"model": self.model, "prompt": prompt, "size": "1024x1024", "quality": "medium", "n": 1},
            )
        try:
            content = base64.b64decode(data["data"][0]["b64_json"])
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise ProviderError("Réponse d'image incomplète.") from exc
        return GeneratedImage(content=content, model=self.model)
