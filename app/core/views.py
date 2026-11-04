"""Sonde de santé pour Docker, Render et la surveillance externe."""

from __future__ import annotations

from django.db import DatabaseError, connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET


@never_cache
@require_GET
def healthz(request: HttpRequest) -> JsonResponse:
    """Vérifie que l'application répond et que la base est joignable.

    Aucune information sensible n'est renvoyée (ni version, ni configuration).

    Args:
        request: Requête HTTP.

    Returns:
        ``{"status": "ok"}`` (200) ou ``{"status": "error"}`` (503).
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})
