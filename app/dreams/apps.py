"""Configuration de l'app « dreams »."""

from django.apps import AppConfig


class DreamsConfig(AppConfig):
    """Rêves, émotions et dépôt audio."""

    name = "dreams"
    verbose_name = "Rêves"

    def ready(self) -> None:
        """Branche les signaux de l'app."""
        from . import signals  # noqa: F401
