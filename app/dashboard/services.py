"""Statistiques du tableau de bord (KAN-25, US-15 et US-16)."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from django.utils import timezone

from dreams.models import DreamQuerySet, Emotion


@dataclass(frozen=True)
class Share:
    """Part d'une émotion dans la période.

    Attributes:
        emotion: Émotion concernée.
        count: Nombre de rêves.
        ratio: Part entre 0 et 1.
    """

    emotion: Emotion
    count: int
    ratio: float


@dataclass(frozen=True)
class Bucket:
    """Rêves d'un jour ou d'une semaine, par émotion.

    Attributes:
        start: Premier jour de l'intervalle.
        label: Libellé court affiché sous la barre.
        counts: Nombre de rêves par clé d'émotion.
    """

    start: date
    label: str
    counts: dict[str, int] = field(default_factory=dict)

    @property
    def total(self) -> int:
        """Nombre total de rêves de l'intervalle."""
        return sum(self.counts.values())


@dataclass(frozen=True)
class DashboardStats:
    """Indicateurs d'une période.

    Attributes:
        total: Nombre de rêves classés.
        dominant: Ambiance la plus fréquente (``None`` si aucun rêve).
        per_week: Fréquence moyenne par semaine.
        shares: Répartition par émotion (toutes les émotions, même absentes).
        timeline: Évolution par jour ou par semaine.
        granularity: ``day`` ou ``week``.
    """

    total: int
    dominant: Emotion | None
    per_week: float
    shares: list[Share]
    timeline: list[Bucket]
    granularity: str


def _week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def compute_stats(dreams: DreamQuerySet, low: datetime | None = None, high: datetime | None = None) -> DashboardStats:
    """Calcule les indicateurs des rêves classés d'une période.

    Args:
        dreams: Rêves déjà filtrés (utilisateur, période, émotions).
        low: Début de la période, ou ``None`` (depuis le premier rêve).
        high: Fin de la période, ou ``None`` (jusqu'à aujourd'hui).

    Returns:
        Les indicateurs ; une période sans rêve donne des compteurs à zéro.
    """
    rows = list(dreams.filter(emotion__isnull=False).values_list("created_at", "emotion__key"))
    emotions = list(Emotion.objects.all())
    by_key = {e.key: e for e in emotions}
    counts = Counter(key for _, key in rows)
    total = len(rows)
    shares = [Share(e, counts[e.key], counts[e.key] / total if total else 0.0) for e in emotions]
    dominant = by_key[counts.most_common(1)[0][0]] if total else None

    today = timezone.localdate()
    days = [timezone.localtime(created).date() for created, _ in rows]
    first = low.date() if low else (min(days) if days else today)
    last = high.date() if high else today
    span = max((last - first).days + 1, 1)
    per_week = round(total / max(span / 7, 1), 1)

    granularity = "day" if span <= 31 else "week"
    buckets: dict[date, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for day, (_, key) in zip(days, rows, strict=True):
        buckets[day if granularity == "day" else _week_start(day)][key] += 1
    cursor = first if granularity == "day" else _week_start(first)
    step = timedelta(days=1 if granularity == "day" else 7)
    timeline: list[Bucket] = []
    while cursor <= last:
        timeline.append(Bucket(cursor, cursor.strftime("%d/%m"), dict(buckets.get(cursor, {}))))
        cursor += step
    return DashboardStats(total, dominant, per_week, shares, timeline, granularity)
