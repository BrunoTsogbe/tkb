"""Métriques de supervision dérivées de la base (specifications_architecture.pdf §6.3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.utils import timezone

from dreams.models import Dream

from . import budget
from .models import APICallLog


@dataclass(frozen=True)
class ProviderStats:
    """Fiabilité d'un fournisseur sur la fenêtre observée.

    Attributes:
        kind: Brique.
        provider: Fournisseur.
        calls: Nombre d'appels (tentatives comprises).
        errors: Nombre d'échecs.
    """

    kind: str
    provider: str
    calls: int
    errors: int

    @property
    def error_rate(self) -> float:
        """Taux d'erreur entre 0 et 1."""
        return self.errors / self.calls if self.calls else 0.0


def percentile(values: list[int], ratio: float) -> int | None:
    """Percentile par rang le plus proche.

    Args:
        values: Mesures.
        ratio: Percentile visé entre 0 et 1 (0,95 pour p95).

    Returns:
        La valeur, ou ``None`` sans mesure.
    """
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round(ratio * len(ordered)) - 1))
    return ordered[index]


def snapshot(days: int = 7) -> dict[str, object]:
    """Indicateurs clés pour la page de supervision.

    Args:
        days: Fenêtre d'observation en jours.

    Returns:
        Budget, latences de traitement, fiabilité des fournisseurs, part d'images de secours.
    """
    since = timezone.now() - timedelta(days=days)
    durations: list[int] = [
        value
        for value in Dream.objects.filter(
            created_at__gte=since, status=Dream.Status.DONE, processing_ms__isnull=False
        ).values_list("processing_ms", flat=True)
        if value is not None
    ]
    dreams = Dream.objects.filter(created_at__gte=since).aggregate(
        total=Count("id"),
        failed=Count("id", filter=Q(status=Dream.Status.FAILED)),
        done=Count("id", filter=Q(status=Dream.Status.DONE)),
        fallback=Count("id", filter=Q(image_is_fallback=True)),
    )
    providers = [
        ProviderStats(row["kind"], row["provider"], row["calls"], row["errors"])
        for row in APICallLog.objects.filter(created_at__gte=since)
        .values("kind", "provider")
        .annotate(calls=Count("id"), errors=Count("id", filter=~Q(status=APICallLog.Status.OK)))
        .order_by("kind", "provider")
    ]
    spent = budget.spent_eur(fresh=True)
    limit = budget.budget_eur()
    return {
        "days": days,
        "spent_eur": spent,
        "budget_eur": limit,
        "budget_ratio": float(spent / limit) if limit else 0.0,
        "remaining_eur": max(limit - spent, Decimal("0")),
        "p50_ms": percentile(durations, 0.5),
        "p95_ms": percentile(durations, 0.95),
        "dreams": dreams,
        "fallback_ratio": dreams["fallback"] / dreams["done"] if dreams["done"] else 0.0,
        "providers": providers,
    }
