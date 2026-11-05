"""Traitement complet d'un rêve (specifications_architecture.pdf §3).

``received → transcribing → analyzing → generating → done | failed``

Chaque étape est idempotente : une étape réussie n'est jamais rejouée, donc
jamais refacturée ; « Réessayer » reprend à l'étape en échec. Un verrou par rêve
empêche deux workers de traiter le même rêve.
"""

from __future__ import annotations

import logging
import time
from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.core.cache import cache
from django.core.files.base import ContentFile
from django.db.models import Sum

from ai import budget
from ai.fallback import render_fallback
from ai.policy import FREE, Billing, call_with_policy
from ai.pricing import image_cost_usd, stt_cost_usd, usd_to_eur
from ai.prompt import build_image_prompt
from ai.providers import get_emotion_classifier, get_image_generator, get_transcriber
from ai.providers.base import (
    BudgetExhausted,
    ContentRefused,
    EmotionResult,
    GeneratedImage,
    InvalidRequest,
    ProviderError,
    Transcript,
)

from .models import Dream, Emotion

logger = logging.getLogger(__name__)
LOCK_TTL_S = 15 * 60


class AudioMissing(InvalidRequest):
    """L'audio a disparu avant d'être transcrit."""

    code = "invalid_audio"


def _set_status(dream: Dream, status: str) -> None:
    dream.status = status
    dream.save(update_fields=["status", "updated_at"])


def _transcribe(dream: Dream) -> None:
    _set_status(dream, Dream.Status.TRANSCRIBING)
    if not dream.audio_file:
        raise AudioMissing("L'enregistrement n'est plus disponible.")
    with dream.audio_file.open("rb") as handle:
        audio = handle.read()
    transcriber = get_transcriber()
    paid = getattr(transcriber, "paid", True)
    minutes = Decimal(str(dream.audio_duration_s or 120)) / Decimal(60)
    if paid:
        budget.ensure_can_spend("stt", usd_to_eur(stt_cost_usd(minutes)))

    def bill(result: Transcript) -> Billing:
        return Billing(result.billed_minutes, stt_cost_usd(result.billed_minutes)) if paid else FREE

    result = call_with_policy(
        lambda: transcriber.transcribe(audio, f"{dream.id}.{dream.audio_format}", duration_s=dream.audio_duration_s),
        kind="stt",
        provider=transcriber.provider,
        model=transcriber.model,
        billing=bill,
        retries=settings.AI_STT_RETRIES,
        dream=dream,
        user=dream.user,
    )
    dream.transcript, dream.transcript_model = result.text, result.model
    dream.save(update_fields=["transcript", "transcript_model", "updated_at"])
    dream.delete_audio()


def _classify(dream: Dream) -> None:
    _set_status(dream, Dream.Status.ANALYZING)
    classifier = get_emotion_classifier()
    try:
        result: EmotionResult = call_with_policy(
            lambda: classifier.classify(dream.transcript),
            kind="emotion",
            provider=classifier.provider,
            model=classifier.model,
            billing=lambda _: FREE,
            retries=0,
            dream=dream,
            user=dream.user,
        )
    except Exception:  # le modèle local ne doit jamais bloquer le rêve
        logger.exception("emotion_failed fallback=keywords dream=%s", dream.id)
        from ai.providers.emotion import KeywordClassifier

        result = KeywordClassifier().classify(dream.transcript)
    dream.emotion = Emotion.objects.get(key=result.key)
    dream.emotion_scores = result.scores
    dream.save(update_fields=["emotion", "emotion_scores", "updated_at"])


def _illustrate(dream: Dream) -> None:
    _set_status(dream, Dream.Status.GENERATING)
    assert dream.emotion is not None
    prompt = build_image_prompt(dream.transcript, dream.emotion.label)
    dream.image_prompt = prompt
    generator = get_image_generator()
    paid = getattr(generator, "paid", True)
    try:
        if paid:
            budget.ensure_can_spend("image", usd_to_eur(image_cost_usd(1)))

        def bill(result: GeneratedImage) -> Billing:
            return Billing(Decimal(result.billed_images), image_cost_usd(result.billed_images)) if paid else FREE

        image = call_with_policy(
            lambda: generator.generate(prompt),
            kind="image",
            provider=generator.provider,
            model=generator.model,
            billing=bill,
            retries=settings.AI_IMAGE_RETRIES,
            dream=dream,
            user=dream.user,
        )
        content, model, fallback = image.content, image.model, False
    except (ContentRefused, BudgetExhausted) as error:
        logger.info("image_fallback dream=%s reason=%s", dream.id, error.code)
        content, model, fallback = render_fallback(str(dream.id), dream.emotion.color), "fallback", True
    dream.image_file.save(f"{dream.id}.png", ContentFile(content), save=False)
    dream.image_model, dream.image_is_fallback = model, fallback
    dream.save(update_fields=["image_file", "image_prompt", "image_model", "image_is_fallback", "updated_at"])


def process_dream(dream_id: UUID | str) -> Dream | None:
    """Exécute ou reprend le traitement d'un rêve.

    Args:
        dream_id: Identifiant du rêve.

    Returns:
        Le rêve à jour, ou ``None`` s'il est déjà en cours de traitement ailleurs.
    """
    lock = f"dream:lock:{dream_id}"
    if not cache.add(lock, True, LOCK_TTL_S):
        logger.info("dream_locked dream=%s", dream_id)
        return None
    try:
        dream = Dream.objects.select_related("user", "emotion").get(pk=dream_id)
        if dream.status == Dream.Status.DONE:
            return dream
        started = time.perf_counter()
        dream.error_code = dream.error_step = ""
        step = Dream.Step.TRANSCRIPTION
        try:
            if not dream.transcript:
                _transcribe(dream)
            step = Dream.Step.EMOTION
            if not dream.emotion_id:
                _classify(dream)
            step = Dream.Step.IMAGE
            if not dream.image_file:
                _illustrate(dream)
        except ProviderError as error:
            dream.status, dream.error_code, dream.error_step = Dream.Status.FAILED, error.code, step
            logger.info("dream_failed dream=%s step=%s code=%s", dream.id, step, error.code)
        else:
            dream.status = Dream.Status.DONE
        dream.processing_ms = int((time.perf_counter() - started) * 1000)
        dream.cost_eur = dream.api_calls.aggregate(total=Sum("cost_eur"))["total"] or Decimal("0")
        dream.save(update_fields=["status", "error_code", "error_step", "processing_ms", "cost_eur", "updated_at"])
        return dream
    finally:
        cache.delete(lock)
