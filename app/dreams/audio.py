"""Validation des fichiers audio déposés (extension, taille, signature, durée).

Reprend et complète la logique testée dans la maquette (``maquette/services.py``) :
la signature du fichier est vérifiée, pas seulement son extension.
"""

from __future__ import annotations

import io
import wave
from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_FORMATS = ("wav", "mp3", "webm")
MAX_DURATION_S = 10 * 60
WEBM_MAGIC = b"\x1a\x45\xdf\xa3"


@dataclass(frozen=True)
class AudioInfo:
    """Caractéristiques d'un fichier audio validé.

    Attributes:
        format: Format détecté (wav, mp3 ou webm).
        duration_s: Durée en secondes si elle a pu être lue, sinon ``None``.
    """

    format: str
    duration_s: float | None


def detect_format(head: bytes) -> str | None:
    """Identifie le format d'après les premiers octets du fichier.

    Args:
        head: Début du fichier (au moins 12 octets).

    Returns:
        ``wav``, ``mp3``, ``webm`` ou ``None`` si la signature est inconnue.
    """
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "wav"
    if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and head[1] & 0xE0 == 0xE0):
        return "mp3"
    if head[:4] == WEBM_MAGIC:
        return "webm"
    return None


def wav_duration(data: bytes) -> float | None:
    """Lit la durée d'un fichier WAV.

    Args:
        data: Contenu du fichier.

    Returns:
        Durée en secondes, ou ``None`` si l'en-tête est illisible.
    """
    try:
        with wave.open(io.BytesIO(data), "rb") as handle:
            return handle.getnframes() / float(handle.getframerate())
    except (wave.Error, EOFError, ZeroDivisionError):
        return None


def validate_audio(filename: str, data: bytes) -> AudioInfo:
    """Vérifie qu'un fichier audio peut être transcrit.

    Args:
        filename: Nom d'origine du fichier.
        data: Contenu complet du fichier.

    Returns:
        Le format détecté et la durée.

    Raises:
        ValidationError: Si le fichier est vide, trop lourd, d'un format non pris en charge,
            incohérent avec son extension ou trop long.
    """
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ALLOWED_FORMATS:
        raise ValidationError("Format non pris en charge : utilisez un fichier .wav, .mp3 ou .webm.", code="format")
    if not data:
        raise ValidationError("Le fichier est vide.", code="empty")
    if len(data) > settings.AUDIO_MAX_BYTES:
        limit = settings.AUDIO_MAX_BYTES // (1024 * 1024)
        raise ValidationError(f"Le fichier dépasse {limit} Mo.", code="too_large")
    detected = detect_format(data[:16])
    if detected != extension:
        raise ValidationError("Le contenu du fichier ne correspond pas à son extension.", code="signature")
    duration = wav_duration(data) if detected == "wav" else None
    if duration is not None and duration > MAX_DURATION_S:
        raise ValidationError("L'enregistrement dépasse 10 minutes.", code="too_long")
    return AudioInfo(format=detected, duration_s=duration)
