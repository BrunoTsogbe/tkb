"""Tâches Celery des rêves (KAN-22)."""

from __future__ import annotations

from celery import shared_task

from .pipeline import process_dream


@shared_task(name="dreams.process_dream", acks_late=True, ignore_result=True)
def process_dream_task(dream_id: str) -> None:
    """Traite un rêve dans le worker.

    Args:
        dream_id: Identifiant du rêve (chaîne, sérialisable en JSON).
    """
    process_dream(dream_id)
