"""Règles métier du dépôt d'un rêve (consentement, quota)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .models import Dream

if TYPE_CHECKING:
    from accounts.models import User


@dataclass(frozen=True)
class Quota:
    """État du quota quotidien d'un utilisateur.

    Attributes:
        limit: Nombre de rêves autorisés sur 24 heures.
        used: Nombre de rêves déjà déposés sur 24 heures.
    """

    limit: int
    used: int

    @property
    def remaining(self) -> int:
        """Nombre de dépôts encore possibles."""
        return max(0, self.limit - self.used)

    @property
    def exhausted(self) -> bool:
        """Vrai si le quota est atteint."""
        return self.remaining == 0


def quota_for(user: User) -> Quota:
    """Calcule le quota quotidien (fenêtre glissante de 24 heures).

    Args:
        user: Utilisateur concerné.

    Returns:
        L'état du quota.
    """
    used = Dream.objects.for_user(user).created_today().count()
    return Quota(limit=user.profile.daily_dream_limit, used=used)
