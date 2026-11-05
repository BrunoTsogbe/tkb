"""Tests de l'interface Streamlit avec ``AppTest`` (sans navigateur)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from streamlit.testing.v1 import AppTest

import services

APP = str(Path(__file__).resolve().parents[1] / "app.py")
TIMEOUT = 30


def _button(at: AppTest, text: str):
    """Retourne le premier bouton dont le libellé contient ``text``."""
    return next(b for b in at.button if text in b.label)


def _demo_app(*, fail_stt: bool = False, fail_img: bool = True) -> AppTest:
    """Lance la page avec une latence nulle et les pannes demandées."""
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    at.slider[0].set_value(0.0)
    at.toggle[0].set_value(fail_stt)
    at.toggle[1].set_value(fail_img)  # pas d'appel réseau pendant les tests
    return at.run()


def _app_with_dream(fallback: bool = False) -> AppTest:
    """Prépare la page avec un rêve déjà traité dans la session."""
    at = AppTest.from_file(APP, default_timeout=TIMEOUT)
    text = "J'avais peur dans le noir"
    at.session_state["dream"] = {
        "text": text,
        "emotion": "stressant",
        "scores": services.emotion_scores(text),
        "image": services.local_placeholder(services.EMOTIONS["stressant"], size=16),
        "fallback": fallback,
        "date": datetime(2026, 11, 4, 7, 30),
        "duration": 120.0,
        "elapsed": 21.0,
        "cost": services.estimate_cost_eur(120.0),
    }
    return at.run()


def test_app_starts_without_error() -> None:
    """La page se charge, le bouton d'analyse est désactivé sans audio."""
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    assert not at.exception
    assert _button(at, "Donner vie").disabled
    assert at.subheader[0].value == "Mon ciel de rêves (0)"


def test_demo_dream_runs_full_pipeline() -> None:
    """Le rêve d'exemple traverse tout le traitement et affiche le résultat."""
    at = _demo_app()
    _button(at, "Rêve d'exemple").click().run()
    assert not at.exception
    dream = at.session_state["dream"]
    assert dream["text"] in services.SAMPLE_TRANSCRIPTS
    assert dream["fallback"] is True
    assert at.text_area[0].value == dream["text"]
    assert "indisponible" in at.warning[0].value


def test_transcription_failure_shows_error() -> None:
    """Une panne de transcription affiche une erreur sans résultat."""
    at = _demo_app(fail_stt=True)
    _button(at, "Rêve d'exemple").click().run()
    assert not at.exception
    assert at.session_state["dream"] is None
    assert "Réessayez" in at.error[0].value


def test_result_shows_editable_text_and_emotion() -> None:
    """Le résultat affiche le texte modifiable et l'émotion corrigeable."""
    at = _app_with_dream()
    assert not at.exception
    assert at.text_area[0].value == "J'avais peur dans le noir"
    assert at.selectbox[0].value == "stressant"
    assert not at.warning


def test_save_moves_corrected_dream_to_history() -> None:
    """La correction de l'émotion est conservée dans l'historique."""
    at = _app_with_dream()
    at.selectbox[0].set_value("etrange").run()
    _button(at, "Garder ce rêve").click().run()
    assert not at.exception
    assert at.session_state["dream"] is None
    assert at.session_state["history"][0]["emotion"] == "etrange"
    assert at.subheader[0].value == "Mon ciel de rêves (1)"


def test_seed_and_clear_history() -> None:
    """Les exemples alimentent le tableau de bord, puis l'historique se vide."""
    at = AppTest.from_file(APP, default_timeout=TIMEOUT).run()
    _button(at, "Charger des rêves").click().run()
    assert not at.exception
    assert len(at.session_state["history"]) == 2 * len(services.SAMPLE_TRANSCRIPTS)
    assert at.metric[0].value == str(2 * len(services.SAMPLE_TRANSCRIPTS))
    _button(at, "Vider").click().run()
    assert at.session_state["history"] == []
