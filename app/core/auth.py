"""Utilitaires d'authentification partagés par les vues."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from django.http import HttpRequest

if TYPE_CHECKING:
    from accounts.models import User


def current_user(request: HttpRequest) -> User:
    """Renvoie l'utilisateur d'une vue protégée par ``login_required``.

    Args:
        request: Requête d'un utilisateur connecté.

    Returns:
        L'utilisateur, typé comme compte réel (jamais anonyme ici).
    """
    return cast("User", request.user)
