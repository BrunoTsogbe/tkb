"""Politique d'appel commune à tous les fournisseurs (KAN-21).

Relances bornées avec attente exponentielle et aléa, respect de ``Retry-After``,
coupe-circuit (5 échecs en 5 min : fournisseur suspendu 2 min) et une ligne
``APICallLog`` par tentative, avec la durée et le coût réellement facturé.
"""

from __future__ import annotations

import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import TYPE_CHECKING, TypeVar

from django.conf import settings
from django.core.cache import cache

from . import budget
from .models import APICallLog
from .pricing import usd_to_eur
from .providers.base import CircuitOpen, ProviderError, ProviderTimeout

if TYPE_CHECKING:
    from accounts.models import User
    from dreams.models import Dream

logger = logging.getLogger(__name__)
T = TypeVar("T")
CIRCUIT_FAILURES, CIRCUIT_WINDOW_S, CIRCUIT_OPEN_S = 5, 300, 120
sleep = time.sleep  # remplaçable dans les tests


@dataclass(frozen=True)
class Billing:
    """Ce qu'un appel réussi a coûté.

    Attributes:
        units: Quantité facturée (minutes, images).
        cost_usd: Coût en dollars.
    """

    units: Decimal = Decimal("0")
    cost_usd: Decimal = Decimal("0")


FREE = Billing()


def _circuit_key(provider: str, kind: str) -> str:
    return f"ai:circuit:{provider}:{kind}"


def _note_failure(provider: str, kind: str) -> None:
    key = f"{_circuit_key(provider, kind)}:failures"
    cache.add(key, 0, CIRCUIT_WINDOW_S)
    if cache.incr(key) >= CIRCUIT_FAILURES:
        cache.set(_circuit_key(provider, kind), True, CIRCUIT_OPEN_S)
        cache.delete(key)
        logger.warning("circuit_open provider=%s kind=%s", provider, kind)


def call_with_policy(
    operation: Callable[[], T],
    *,
    kind: str,
    provider: str,
    model: str,
    billing: Callable[[T], Billing],
    retries: int,
    dream: Dream | None = None,
    user: User | None = None,
) -> T:
    """Exécute un appel fournisseur sous la politique commune.

    Args:
        operation: Appel à exécuter (sans argument).
        kind: Brique (``stt``, ``emotion``, ``image``).
        provider: Nom du fournisseur.
        model: Modèle appelé.
        billing: Calcule la facturation d'un résultat.
        retries: Nombre maximal de relances.
        dream: Rêve concerné (journal).
        user: Utilisateur imputé (journal).

    Returns:
        Le résultat de l'appel.

    Raises:
        CircuitOpen: Si le fournisseur est suspendu.
        ProviderError: Si l'appel échoue définitivement.
    """
    if cache.get(_circuit_key(provider, kind)):
        raise CircuitOpen(f"{provider} est momentanément suspendu.")
    base = {"dream": dream, "user": user, "kind": kind, "provider": provider, "model": model}
    for attempt in range(1, retries + 2):
        started = time.perf_counter()
        try:
            result = operation()
        except ProviderError as error:
            elapsed = int((time.perf_counter() - started) * 1000)
            APICallLog.objects.create(
                **base,
                attempt=attempt,
                latency_ms=elapsed,
                http_status=error.http_status,
                error_code=error.code,
                status=APICallLog.Status.TIMEOUT if isinstance(error, ProviderTimeout) else APICallLog.Status.ERROR,
            )
            logger.info("ai_call kind=%s provider=%s attempt=%s error=%s", kind, provider, attempt, error.code)
            if error.retryable:
                _note_failure(provider, kind)
            if not error.retryable or attempt > retries:
                raise
            delay = error.retry_after or settings.AI_BACKOFF_S * 2 ** (attempt - 1)
            sleep(min(delay, 30) + random.uniform(0, 0.5))
            continue
        elapsed = int((time.perf_counter() - started) * 1000)
        cost = billing(result)
        APICallLog.objects.create(
            **base,
            attempt=attempt,
            latency_ms=elapsed,
            status=APICallLog.Status.OK,
            units=cost.units,
            cost_usd=cost.cost_usd,
            cost_eur=usd_to_eur(cost.cost_usd),
        )
        logger.info("ai_call kind=%s provider=%s attempt=%s latency_ms=%s ok", kind, provider, attempt, elapsed)
        if cost.cost_usd:
            budget.record_spend()
        return result
    raise AssertionError("unreachable")  # pragma: no cover
