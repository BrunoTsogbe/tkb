"""Tableau de bord personnel (KAN-25)."""

from __future__ import annotations

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from core.auth import current_user
from dreams.filters import DreamFilterForm
from dreams.models import Dream

from .charts import donut, stacked_bars
from .services import compute_stats


@login_required
@require_GET
def dashboard(request: HttpRequest) -> HttpResponse:
    """Indicateurs, répartition et évolution des ambiances sur la période filtrée.

    Args:
        request: Requête HTTP (mêmes filtres que l'historique ; 30 jours par défaut).

    Returns:
        La page du tableau de bord.
    """
    params = request.GET.copy()
    if not params:
        params["period"] = "30"
    form = DreamFilterForm(params)
    dreams = form.apply(Dream.objects.for_user(current_user(request)))
    low, high = form.date_range()
    stats = compute_stats(dreams, low, high)
    context = {
        "form": form,
        "stats": stats,
        "donut": donut(stats.shares),
        "bars": stacked_bars(stats.timeline, stats.shares),
    }
    return render(request, "dashboard/dashboard.html", context)
