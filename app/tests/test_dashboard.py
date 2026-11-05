"""KAN-24 (filtres) et KAN-25 (tableau de bord)."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from dashboard.charts import donut, stacked_bars
from dashboard.services import compute_stats
from dreams.filters import DreamFilterForm
from dreams.models import Dream, Emotion
from tests.conftest import UserFactory

pytestmark = pytest.mark.django_db


def dream(user: User, key: str, days_ago: int = 0, text: str = "un rêve") -> Dream:
    created = Dream.objects.create(user=user, status="done", transcript=text, emotion=Emotion.objects.get(key=key))
    Dream.objects.filter(pk=created.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
    created.refresh_from_db()
    return created


# --- filtres (KAN-24) --------------------------------------------------------------------------------


def test_filters_combine_period_and_emotions(user: User) -> None:
    """Période et émotions se combinent ; les dates explicites priment sur le raccourci."""
    dream(user, "stressant", 2)
    dream(user, "heureux", 3)
    dream(user, "stressant", 40)
    mine = Dream.objects.for_user(user)
    assert DreamFilterForm({"period": "7"}).apply(mine).count() == 2
    assert DreamFilterForm({"period": "30", "emotion": ["stressant"]}).apply(mine).count() == 1
    assert DreamFilterForm({"emotion": ["stressant", "heureux"]}).apply(mine).count() == 3
    start = (timezone.localdate() - timedelta(days=45)).isoformat()
    end = (timezone.localdate() - timedelta(days=30)).isoformat()
    assert DreamFilterForm({"period": "7", "start": start, "end": end}).apply(mine).count() == 1


def test_invalid_filters_are_ignored_with_a_message(user: User) -> None:
    """Dates inversées : message d'erreur, aucun filtre appliqué."""
    dream(user, "heureux")
    form = DreamFilterForm({"start": "2026-11-05", "end": "2026-11-01"})
    assert form.apply(Dream.objects.for_user(user)).count() == 1
    assert "précéder" in form.non_field_errors()[0]


def test_history_filters_are_in_url_and_kept_by_pagination(client_logged: Client, user: User) -> None:
    """Filtres reflétés dans l'URL, conservés d'une page à l'autre ; résultat vide explicite."""
    for _ in range(21):
        dream(user, "triste")
    dream(user, "heureux")
    page = client_logged.get(reverse("dreams:collection"), {"emotion": "triste"})
    assert len(page.context["page"].object_list) == 20
    assert "emotion=triste&amp;page=2" in page.content.decode()
    empty = client_logged.get(reverse("dreams:collection"), {"emotion": "etrange"}).content.decode()
    assert "Aucun rêve ne correspond" in empty and "Réinitialiser" in empty


# --- statistiques (KAN-25, TDD) ----------------------------------------------------------------------


def test_stats_count_dominant_frequency_and_shares(user: User) -> None:
    """Volume, ambiance dominante, fréquence hebdomadaire et répartition sur 14 jours."""
    for days, key in [(0, "stressant"), (1, "stressant"), (3, "heureux"), (10, "stressant")]:
        dream(user, key, days)
    Dream.objects.create(user=user)  # pas encore classé : ignoré
    form = DreamFilterForm({"start": (timezone.localdate() - timedelta(days=13)).isoformat()})
    low, high = form.date_range()
    stats = compute_stats(form.apply(Dream.objects.for_user(user)), low, high)
    assert stats.total == 4 and stats.dominant.key == "stressant"
    assert stats.per_week == 2.0
    shares = {s.emotion.key: s.ratio for s in stats.shares}
    assert shares["stressant"] == 0.75 and shares["heureux"] == 0.25 and shares["triste"] == 0
    assert stats.granularity == "day" and len(stats.timeline) == 14
    assert sum(b.total for b in stats.timeline) == 4


def test_long_periods_are_grouped_by_week(user: User) -> None:
    """Au-delà de 31 jours, l'évolution est hebdomadaire."""
    dream(user, "heureux", 0)
    dream(user, "triste", 60)
    stats = compute_stats(Dream.objects.for_user(user))
    assert stats.granularity == "week" and stats.timeline[0].start.weekday() == 0
    assert sum(b.total for b in stats.timeline) == 2


def test_empty_period(user: User) -> None:
    """Sans rêve : compteurs à zéro, pas de division par zéro."""
    stats = compute_stats(Dream.objects.for_user(user))
    assert stats.total == 0 and stats.dominant is None and stats.per_week == 0
    assert "Aucun rêve" in donut(stats.shares) and "<svg" in stacked_bars(stats.timeline, stats.shares)


def test_charts_are_accessible_and_escaped(user: User) -> None:
    """Les SVG portent un titre accessible et une infobulle par segment."""
    dream(user, "heureux")
    dream(user, "triste")
    stats = compute_stats(Dream.objects.for_user(user))
    ring = donut(stats.shares)
    assert 'role="img"' in ring and "Heureux 50 %" in ring and ring.count("<circle") == 3
    bars = stacked_bars(stats.timeline, stats.shares)
    assert "Évolution des émotions" in bars and "Triste : 1" in bars


# --- vue ----------------------------------------------------------------------------------------------


def test_dashboard_page_defaults_to_30_days_and_is_isolated(client_logged: Client, user: User) -> None:
    """30 jours par défaut, indicateurs, graphiques, tableau alternatif, données de l'utilisateur seulement."""
    dream(user, "stressant", 1)
    dream(user, "stressant", 45)
    dream(UserFactory(), "heureux", 1)
    response = client_logged.get(reverse("dashboard:index"))
    page = response.content.decode()
    assert response.context["stats"].total == 1
    assert "Stressant" in page and "<svg" in page and "sous forme de tableau" in page
    assert client_logged.get(reverse("dashboard:index"), {"period": ""}).context["stats"].total == 2


def test_dashboard_empty_state(client_logged: Client) -> None:
    """Aucune donnée : message et invitation à raconter un rêve."""
    assert "Aucun rêve sur cette période" in client_logged.get(reverse("dashboard:index")).content.decode()
