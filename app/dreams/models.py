"""Rêves et référentiel des émotions (specifications_architecture.pdf §2)."""

from __future__ import annotations

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import TYPE_CHECKING

from django.conf import settings
from django.db import models
from django.utils import timezone

if TYPE_CHECKING:
    from accounts.models import User


class Emotion(models.Model):
    """Ambiance d'un rêve (référentiel chargé par migration)."""

    key = models.CharField("clé", max_length=20, unique=True)
    label = models.CharField("libellé", max_length=40)
    icon = models.CharField("icône", max_length=8)
    color = models.CharField("couleur", max_length=7)

    class Meta:
        verbose_name = "émotion"
        ordering = ("id",)

    def __str__(self) -> str:
        return f"{self.icon} {self.label}"


class DreamQuerySet(models.QuerySet["Dream"]):
    """Requêtes sur les rêves, toujours filtrables par propriétaire."""

    def for_user(self, user: User) -> DreamQuerySet:
        """Restreint aux rêves d'un utilisateur (isolation des données).

        Args:
            user: Propriétaire.

        Returns:
            Les rêves de cet utilisateur.
        """
        return self.filter(user=user)

    def created_today(self) -> DreamQuerySet:
        """Restreint aux rêves déposés dans les dernières 24 heures (fenêtre du quota).

        Returns:
            Les rêves récents.
        """
        return self.filter(created_at__gte=timezone.now() - timedelta(days=1))


def audio_upload_to(instance: Dream, filename: str) -> str:
    """Construit un chemin de stockage aléatoire (aucune donnée personnelle dans le nom).

    Args:
        instance: Rêve concerné.
        filename: Nom d'origine (seule l'extension est conservée).

    Returns:
        Chemin relatif au stockage des médias.
    """
    return f"audio/{instance.id}.{instance.audio_format or 'bin'}"


def image_upload_to(instance: Dream, filename: str) -> str:
    """Construit le chemin de stockage de l'image générée.

    Args:
        instance: Rêve concerné.
        filename: Nom proposé (ignoré).

    Returns:
        Chemin relatif au stockage des médias.
    """
    now = timezone.now()
    return f"dreams/{now:%Y/%m}/{instance.id}.png"


class Dream(models.Model):
    """Un rêve raconté, de l'audio déposé jusqu'à l'image générée."""

    class Status(models.TextChoices):
        RECEIVED = "received", "Reçu"
        TRANSCRIBING = "transcribing", "Transcription"
        ANALYZING = "analyzing", "Analyse de l'ambiance"
        GENERATING = "generating", "Génération de l'image"
        DONE = "done", "Terminé"
        FAILED = "failed", "Échec"

    class Step(models.TextChoices):
        TRANSCRIPTION = "transcription", "Transcription"
        EMOTION = "emotion", "Émotion"
        IMAGE = "image", "Image"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="dreams")
    status = models.CharField("statut", max_length=12, choices=Status.choices, default=Status.RECEIVED)
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    updated_at = models.DateTimeField("modifié le", auto_now=True)

    audio_file = models.FileField("audio", upload_to=audio_upload_to, blank=True)
    audio_format = models.CharField("format audio", max_length=8, blank=True)
    audio_duration_s = models.FloatField("durée audio (s)", null=True, blank=True)
    audio_deleted_at = models.DateTimeField("audio supprimé le", null=True, blank=True)

    transcript = models.TextField("transcription", blank=True)
    transcript_model = models.CharField("modèle de transcription", max_length=40, blank=True)
    transcript_edited = models.BooleanField("transcription corrigée", default=False)

    emotion = models.ForeignKey(Emotion, on_delete=models.PROTECT, null=True, blank=True, related_name="dreams")
    emotion_scores = models.JSONField("probabilités des émotions", default=dict, blank=True)
    emotion_corrected = models.BooleanField("émotion corrigée", default=False)

    image_file = models.ImageField("image", upload_to=image_upload_to, blank=True)
    image_prompt = models.TextField("prompt d'image", blank=True)
    image_model = models.CharField("modèle d'image", max_length=40, blank=True)
    image_is_fallback = models.BooleanField("image de secours", default=False)

    error_code = models.CharField("code d'erreur", max_length=30, blank=True)
    error_step = models.CharField("étape en erreur", max_length=13, choices=Step.choices, blank=True)
    processing_ms = models.PositiveIntegerField("durée de traitement (ms)", null=True, blank=True)
    cost_eur = models.DecimalField("coût (€)", max_digits=8, decimal_places=5, default=Decimal("0"))

    objects = DreamQuerySet.as_manager()

    class Meta:
        verbose_name = "rêve"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["user", "-created_at"], name="dream_user_created"),
            models.Index(fields=["user", "emotion", "created_at"], name="dream_user_emotion"),
        ]

    def __str__(self) -> str:
        return f"Rêve {self.id} ({self.get_status_display()})"

    @property
    def is_finished(self) -> bool:
        """Vrai si le traitement est terminé, avec succès ou en échec."""
        return self.status in {self.Status.DONE, self.Status.FAILED}

    def delete_audio(self) -> None:
        """Supprime le fichier audio et horodate la suppression (minimisation RGPD)."""
        if self.audio_file:
            self.audio_file.delete(save=False)
        self.audio_deleted_at = timezone.now()
        self.save(update_fields=["audio_file", "audio_deleted_at", "updated_at"])
