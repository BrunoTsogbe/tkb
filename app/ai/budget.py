"""Garde-fous du budget API de 20 € (specifications_architecture.pdf §5.3, KAN-23).

Seuils : 80 % alerte, 95 % plus d'images, 100 % plus aucun appel payant.
Le montant consommé est la somme du journal ``APICallLog`` (mis en cache 60 s).
"""

from __future__ import annotations

import logging
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum

from .models import APICallLog
from .providers.base import BudgetExhausted

logger = logging.getLogger(__name__)
CACHE_KEY = "ai:budget:spent_eur"
ALERT_KEY = "ai:budget:alert_sent"
ALERT_RATIO, IMAGE_STOP_RATIO, HARD_STOP_RATIO = Decimal("0.80"), Decimal("0.95"), Decimal("1.00")


def spent_eur(*, fresh: bool = False) -> Decimal:
    """Montant consommé depuis le début de la production.

    Args:
        fresh: Ignore le cache (après un appel payant).

    Returns:
        Somme des coûts en euros.
    """
    if not fresh:
        cached = cache.get(CACHE_KEY)
        if cached is not None:
            return Decimal(cached)
    total = APICallLog.objects.aggregate(total=Sum("cost_eur"))["total"] or Decimal("0")
    cache.set(CACHE_KEY, str(total), 60)
    return total


def budget_eur() -> Decimal:
    """Budget total configuré.

    Returns:
        Budget en euros.
    """
    return Decimal(str(settings.API_BUDGET_EUR))


def usage_ratio() -> Decimal:
    """Part du budget consommée.

    Returns:
        Ratio entre 0 et 1 (ou plus en cas de dépassement).
    """
    budget = budget_eur()
    return spent_eur() / budget if budget else HARD_STOP_RATIO


def ensure_can_spend(kind: str, estimated_eur: Decimal) -> None:
    """Vérifie, avant un appel payant, qu'il reste du budget.

    Args:
        kind: Brique appelée (``stt``, ``image``, ``tts``).
        estimated_eur: Coût estimé de l'appel.

    Raises:
        BudgetExhausted: Si l'appel franchirait le seuil applicable.
    """
    budget = budget_eur()
    projected = (spent_eur() + estimated_eur) / budget if budget else HARD_STOP_RATIO
    if kind == "image" and projected >= IMAGE_STOP_RATIO:
        raise BudgetExhausted("Budget à 95 % : la génération d'images est suspendue.")
    if projected >= HARD_STOP_RATIO:
        raise BudgetExhausted("Budget API épuisé : plus aucun appel payant.")


def record_spend() -> None:
    """Rafraîchit le montant consommé et alerte une fois au passage de 80 %."""
    cache.delete(CACHE_KEY)
    if usage_ratio() >= ALERT_RATIO and cache.add(ALERT_KEY, True, None):
        logger.warning("budget_alert ratio=%.2f spent_eur=%s budget_eur=%s", usage_ratio(), spent_eur(), budget_eur())
