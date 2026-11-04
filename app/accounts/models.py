"""Utilisateur (identifié par son e-mail) et profil (consentement, quota)."""

from __future__ import annotations

from typing import Any, ClassVar

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager["User"]):
    """Gestionnaire d'utilisateurs sans nom d'utilisateur."""

    use_in_migrations = True

    def _create(self, email: str, password: str | None, **extra: Any) -> User:
        if not email:
            raise ValueError("L'adresse e-mail est obligatoire.")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra: Any) -> User:
        """Crée un utilisateur standard.

        Args:
            email: Adresse e-mail (identifiant).
            password: Mot de passe en clair, haché avant enregistrement.
            **extra: Autres champs du modèle.

        Returns:
            L'utilisateur créé.
        """
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email: str, password: str | None = None, **extra: Any) -> User:
        """Crée un administrateur.

        Args:
            email: Adresse e-mail (identifiant).
            password: Mot de passe en clair.
            **extra: Autres champs du modèle.

        Returns:
            L'administrateur créé.
        """
        extra.update(is_staff=True, is_superuser=True)
        return self._create(email, password, **extra)


class User(AbstractUser):
    """Utilisateur de l'application, identifié par son adresse e-mail."""

    username = None  # type: ignore[assignment]
    email = models.EmailField("adresse e-mail", unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects = UserManager()  # type: ignore[assignment,misc]

    def __str__(self) -> str:
        return self.email


class Profile(models.Model):
    """Préférences et consentement d'un utilisateur (ERD : Profile)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    ai_consent_at = models.DateTimeField("consentement IA le", null=True, blank=True)
    consent_version = models.CharField("version du consentement", max_length=10, blank=True)
    daily_dream_limit = models.PositiveSmallIntegerField("rêves par jour", default=5)
    timezone = models.CharField("fuseau horaire", max_length=40, default="Europe/Paris")

    class Meta:
        verbose_name = "profil"

    def __str__(self) -> str:
        return f"Profil de {self.user}"

    @property
    def has_ai_consent(self) -> bool:
        """Indique si l'envoi vers les prestataires d'IA est autorisé."""
        return self.ai_consent_at is not None

    def give_consent(self) -> None:
        """Enregistre le consentement à la version courante."""
        self.ai_consent_at = timezone.now()
        self.consent_version = settings.CONSENT_VERSION
        self.save(update_fields=["ai_consent_at", "consent_version"])

    def withdraw_consent(self) -> None:
        """Retire le consentement : les nouveaux traitements sont bloqués."""
        self.ai_consent_at = None
        self.save(update_fields=["ai_consent_at"])
