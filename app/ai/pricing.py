"""Grille tarifaire (benchmark.xlsx) et calcul des coûts.

Les prix sont en configuration (variables d'environnement), jamais en dur dans
le métier : une hausse de tarif se corrige sans déploiement de code.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings

FIVE_PLACES = Decimal("0.00001")


def usd_to_eur(usd: Decimal) -> Decimal:
    """Convertit un montant en euros au taux configuré.

    Args:
        usd: Montant en dollars.

    Returns:
        Montant en euros, arrondi à 5 décimales.
    """
    return (usd * Decimal(str(settings.EUR_PER_USD))).quantize(FIVE_PLACES, ROUND_HALF_UP)


def stt_cost_usd(minutes: Decimal) -> Decimal:
    """Coût d'une transcription.

    Args:
        minutes: Minutes d'audio facturées.

    Returns:
        Coût en dollars.
    """
    return (minutes * Decimal(str(settings.STT_USD_PER_MIN))).quantize(FIVE_PLACES, ROUND_HALF_UP)


def image_cost_usd(images: int) -> Decimal:
    """Coût d'une génération d'image.

    Args:
        images: Nombre d'images facturées.

    Returns:
        Coût en dollars.
    """
    return (Decimal(images) * Decimal(str(settings.IMAGE_USD))).quantize(FIVE_PLACES, ROUND_HALF_UP)


def estimate_dream_cost_eur(duration_s: float | None) -> Decimal:
    """Estime le coût d'un rêve standard (transcription + une image).

    Args:
        duration_s: Durée de l'audio ; 2 minutes si inconnue.

    Returns:
        Coût estimé en euros (0,0184 € pour 2 minutes avec la grille par défaut).
    """
    minutes = Decimal(str(duration_s if duration_s is not None else 120)) / Decimal(60)
    return usd_to_eur(stt_cost_usd(minutes) + image_cost_usd(1))
