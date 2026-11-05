"""Supprime les fichiers d'un rêve quand le rêve est supprimé (KAN-15, RGPD).

Le signal ``post_delete`` est aussi émis lors des suppressions en cascade
(suppression du compte) : aucun fichier orphelin ne reste dans le stockage.
"""

from __future__ import annotations

from typing import Any

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Dream


@receiver(post_delete, sender=Dream)
def delete_dream_files(sender: type, instance: Dream, **kwargs: Any) -> None:
    """Efface l'audio et l'image du stockage.

    Args:
        sender: Modèle émetteur.
        instance: Rêve supprimé.
        **kwargs: Arguments du signal.
    """
    for field in (instance.audio_file, instance.image_file):
        if field:
            field.delete(save=False)
