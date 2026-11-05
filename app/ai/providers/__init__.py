"""Registre des fournisseurs : le fournisseur est une donnée de configuration."""

from __future__ import annotations

import logging

from django.conf import settings

from .base import EmotionClassifier, ImageGenerator, Transcriber
from .emotion import KeywordClassifier, ZeroShotClassifier
from .fake import FakeImageGenerator, FakeTranscriber
from .openai_api import OpenAIImageGenerator, OpenAITranscriber

logger = logging.getLogger(__name__)

TRANSCRIBERS: dict[str, type] = {"fake": FakeTranscriber, "openai": OpenAITranscriber}
IMAGE_GENERATORS: dict[str, type] = {"fake": FakeImageGenerator, "openai": OpenAIImageGenerator}


def get_transcriber() -> Transcriber:
    """Fournisseur de transcription configuré (``AI_STT_PROVIDER``).

    Returns:
        Une instance de fournisseur.
    """
    return TRANSCRIBERS[settings.AI_STT_PROVIDER]()


def get_image_generator() -> ImageGenerator:
    """Fournisseur d'images configuré (``AI_IMAGE_PROVIDER``).

    Returns:
        Une instance de fournisseur.
    """
    return IMAGE_GENERATORS[settings.AI_IMAGE_PROVIDER]()


def get_emotion_classifier() -> EmotionClassifier:
    """Classifieur d'émotion configuré, avec repli sur les mots-clés.

    Returns:
        Le modèle Hugging Face s'il est demandé et disponible, sinon le classifieur par mots-clés.
    """
    if settings.AI_EMOTION_PROVIDER == "huggingface":
        try:
            import transformers  # noqa: F401
        except ImportError:
            logger.warning("emotion_model_unavailable fallback=keywords")
        else:
            return ZeroShotClassifier()
    return KeywordClassifier()
