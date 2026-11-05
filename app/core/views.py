"""Sonde de santé et page de supervision."""

from __future__ import annotations

from datetime import timedelta

from django.contrib.admin.views.decorators import staff_member_required
from django.db import DatabaseError, connection
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

from ai.metrics import snapshot
from dreams.models import Dream

STALLED_AFTER = timedelta(minutes=5)


@never_cache
@require_GET
def healthz(request: HttpRequest) -> JsonResponse:
    """Vérifie la base et signale une file de traitement bloquée.

    Aucune information sensible n'est renvoyée (ni version, ni configuration).

    Args:
        request: Requête HTTP.

    Returns:
        200 si l'application répond, 503 si la base est injoignable. ``queue`` vaut ``stalled``
        si un rêve attend depuis plus de 5 minutes (worker arrêté ?).
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        oldest = (
            Dream.objects.filter(status__in=[Dream.Status.RECEIVED, Dream.Status.TRANSCRIBING])
            .order_by("updated_at")
            .values_list("updated_at", flat=True)
            .first()
        )
    except DatabaseError:
        return JsonResponse({"status": "error", "database": "unreachable"}, status=503)
    stalled = oldest is not None and timezone.now() - oldest > STALLED_AFTER
    return JsonResponse({"status": "ok", "database": "ok", "queue": "stalled" if stalled else "ok"})


@staff_member_required
@require_GET
def supervision(request: HttpRequest) -> HttpResponse:
    """Indicateurs clés pour l'administrateur : budget, latences, fiabilité (KAN-12).

    Args:
        request: Requête HTTP (``days`` : fenêtre, 7 par défaut).

    Returns:
        La page de supervision.
    """
    try:
        days = max(1, min(int(request.GET.get("days", 7)), 90))
    except ValueError:
        days = 7
    return render(request, "core/supervision.html", {"metrics": snapshot(days)})
