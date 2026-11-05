"""Journal des appels aux fournisseurs d'IA (coûts, latences, erreurs)."""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models


class APICallLog(models.Model):
    """Un appel à un fournisseur, relances comprises (base du budget et des SLO)."""

    class Kind(models.TextChoices):
        STT = "stt", "Transcription"
        EMOTION = "emotion", "Émotion"
        IMAGE = "image", "Image"
        TTS = "tts", "Voix"

    class Status(models.TextChoices):
        OK = "ok", "Succès"
        ERROR = "error", "Erreur"
        TIMEOUT = "timeout", "Délai dépassé"

    dream = models.ForeignKey(
        "dreams.Dream", on_delete=models.SET_NULL, null=True, blank=True, related_name="api_calls"
    )
    # NULL après suppression du compte : le coût reste compté, sans donnée personnelle.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="api_calls"
    )
    kind = models.CharField("brique", max_length=8, choices=Kind.choices)
    provider = models.CharField("fournisseur", max_length=40)
    model = models.CharField("modèle", max_length=40)
    status = models.CharField("statut", max_length=8, choices=Status.choices)
    http_status = models.PositiveSmallIntegerField("code HTTP", null=True, blank=True)
    attempt = models.PositiveSmallIntegerField("tentative", default=1)
    latency_ms = models.PositiveIntegerField("latence (ms)")
    units = models.DecimalField("unités facturées", max_digits=10, decimal_places=4, default=Decimal("0"))
    cost_usd = models.DecimalField("coût ($)", max_digits=8, decimal_places=5, default=Decimal("0"))
    cost_eur = models.DecimalField("coût (€)", max_digits=8, decimal_places=5, default=Decimal("0"))
    error_code = models.CharField("code d'erreur", max_length=30, blank=True)
    created_at = models.DateTimeField("date", auto_now_add=True)

    class Meta:
        verbose_name = "appel API"
        verbose_name_plural = "appels API"
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["created_at"], name="apicall_created"),
            models.Index(fields=["kind", "created_at"], name="apicall_kind_created"),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()} · {self.provider} · {self.status}"
