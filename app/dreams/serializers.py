"""Représentation JSON d'un rêve, conforme à ``architecture/dream.schema.json``."""

from __future__ import annotations

from typing import Any

from django.urls import reverse

from .models import Dream

# Classifieur local (KAN-19) ; le nom exact sera fixé par le spike KAN-39.
EMOTION_MODEL = "emotion-local"


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


def dream_to_dict(dream: Dream) -> dict[str, Any]:
    """Sérialise un rêve pour l'API interne et l'export RGPD.

    Args:
        dream: Rêve à sérialiser.

    Returns:
        Dictionnaire conforme au schéma JSON du dossier de spécifications.
    """
    transcript = (
        {"text": dream.transcript, "language": "fr", "model": dream.transcript_model, "edited": dream.transcript_edited}
        if dream.transcript
        else None
    )
    emotion = (
        {
            "key": dream.emotion.key,
            "score": float(dream.emotion_scores.get(dream.emotion.key, 0.0)),
            "scores": {k: float(v) for k, v in dream.emotion_scores.items()},
            "model": EMOTION_MODEL,
            "corrected_by_user": dream.emotion_corrected,
        }
        if dream.emotion
        else None
    )
    image = (
        {
            "url": reverse("dreams:image", args=[dream.id]),
            "model": dream.image_model,
            "size": "1024x1024",
            "is_fallback": dream.image_is_fallback,
            "ai_generated": True,
        }
        if dream.image_file
        else None
    )
    error = (
        {"code": dream.error_code, "step": dream.error_step, "retryable": dream.error_code != "content_refused"}
        if dream.error_code
        else None
    )
    return {
        "id": str(dream.id),
        "user_id": dream.user_id,
        "status": dream.status,
        "created_at": _iso(dream.created_at),
        "audio": {
            "format": dream.audio_format or "webm",
            "duration_s": dream.audio_duration_s,
            "deleted_at": _iso(dream.audio_deleted_at),
        },
        "transcript": transcript,
        "emotion": emotion,
        "image": image,
        "processing": {
            "duration_ms": dream.processing_ms,
            "cost_eur": float(dream.cost_eur),
            "api_calls": dream.api_calls.count(),
        },
        "error": error,
    }
