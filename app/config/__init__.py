"""Configuration du projet Django « Synthétiseur de rêves »."""

from .celery import app as celery_app

__all__ = ("celery_app",)
