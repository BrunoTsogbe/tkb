"""Crée le profil de chaque nouvel utilisateur."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_profile(sender: type, instance: Any, created: bool, **kwargs: Any) -> None:
    """Associe un profil à l'utilisateur dès sa création.

    Args:
        sender: Modèle émetteur.
        instance: Utilisateur enregistré.
        created: Vrai lors de la création.
        **kwargs: Arguments du signal.
    """
    if created:
        Profile.objects.create(user=instance, daily_dream_limit=settings.DAILY_DREAM_LIMIT)
