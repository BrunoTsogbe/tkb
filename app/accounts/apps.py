"""Configuration de l'app « accounts »."""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Comptes, profils et consentement."""

    name = "accounts"
    verbose_name = "Comptes"

    def ready(self) -> None:
        """Branche les signaux de l'app."""
        from . import signals  # noqa: F401
