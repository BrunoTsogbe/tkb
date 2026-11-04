"""Tests des fragments HTML du thème."""

from __future__ import annotations

import services
import theme


def test_pipeline_marks_completed_steps() -> None:
    """Seules les étapes terminées sont allumées."""
    html = theme.pipeline_html(2)
    assert html.count('class="step on"') == 2
    assert html.count('class="step "') == 2


def test_bars_are_sorted_and_sum_to_about_100() -> None:
    """Les barres sont triées par probabilité décroissante."""
    html = theme.bars_html(services.emotion_scores("peur, retard, examen"))
    assert html.index("Stressant") < html.index("Neutre")
    assert "%" in html


def test_card_meta_escapes_and_truncates() -> None:
    """Le texte utilisateur est échappé et tronqué."""
    html = theme.card_meta_html(services.EMOTIONS["neutre"], "04/11", "<b>" + "x" * 200, limit=20)
    assert "<b>" not in html and "&lt;b&gt;" in html
    assert "…" in html


def test_kpis_handle_unknown_duration() -> None:
    """Une durée inconnue (MP3) s'affiche sous forme de tiret."""
    assert "—" in theme.kpis_html(None, 1.0, 0.02)
