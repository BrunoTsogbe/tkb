"""KAN-12 : identifiant de requête, logs JSON, Sentry filtré, santé, supervision."""

from __future__ import annotations

import json
import logging
from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from ai.metrics import percentile, snapshot
from ai.models import APICallLog
from core.observability import JsonFormatter, RequestIdFilter, before_send, init_sentry, request_id, scrub
from dreams.models import Dream
from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db


def test_request_id_is_generated_or_propagated(client: Client) -> None:
    """Chaque réponse porte un identifiant ; un identifiant entrant valide est repris, un invalide remplacé."""
    generated = client.get(reverse("healthz"))["X-Request-ID"]
    assert len(generated) == 32
    assert client.get(reverse("healthz"), HTTP_X_REQUEST_ID="abc-123")["X-Request-ID"] == "abc-123"
    assert client.get(reverse("healthz"), HTTP_X_REQUEST_ID="<script>")["X-Request-ID"] != "<script>"


def test_json_formatter_includes_request_id() -> None:
    """Une ligne JSON par événement, avec l'identifiant de corrélation."""
    record = logging.LogRecord("dreams", logging.INFO, __file__, 1, "dream_failed dream=%s", ("42",), None)
    token = request_id.set("req-1")
    try:
        RequestIdFilter().filter(record)
    finally:
        request_id.reset(token)
    payload = json.loads(JsonFormatter().format(record))
    assert payload["message"] == "dream_failed dream=42" and payload["request_id"] == "req-1"
    assert payload["level"] == "INFO" and payload["time"].endswith("+00:00")


def test_json_formatter_serialises_exceptions() -> None:
    """Les exceptions sont incluses dans la ligne JSON."""
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        record = logging.LogRecord("x", logging.ERROR, __file__, 1, "oops", (), sys.exc_info())
    assert "ValueError: boom" in json.loads(JsonFormatter().format(record))["exception"]


def test_sentry_events_never_carry_dream_content() -> None:
    """Corps, cookies et champs sensibles sont retirés avant l'envoi à Sentry."""
    event = {
        "request": {"url": "/dreams/", "data": {"transcript": "rêve intime"}, "cookies": {"sessionid": "x"}},
        "extra": {"transcript": "rêve intime", "dream_id": "42", "nested": [{"prompt": "secret"}]},
    }
    cleaned = before_send(event, {})
    text = json.dumps(cleaned, ensure_ascii=False)
    assert "rêve intime" not in text and "secret" not in text and "sessionid" not in text
    assert cleaned["extra"]["dream_id"] == "42"
    assert scrub({"Password": "x"}) == {"Password": "[filtré]"}


def test_sentry_is_disabled_without_dsn() -> None:
    """Sans DSN, Sentry n'est pas initialisé."""
    assert init_sentry("", "test", 0.1) is False


def test_sentry_init_with_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avec un DSN, Sentry est initialisé sans données personnelles."""
    captured: dict = {}
    monkeypatch.setattr("sentry_sdk.init", lambda **kwargs: captured.update(kwargs))
    assert init_sentry("https://key@sentry.example/1", "production", 0.1) is True
    assert captured["send_default_pii"] is False and captured["before_send"] is before_send


def test_healthz_detects_stalled_queue(client: Client, user: User) -> None:
    """Un rêve en attente depuis plus de 5 minutes signale un worker bloqué."""
    stuck = Dream.objects.create(user=user)
    Dream.objects.filter(pk=stuck.pk).update(updated_at=timezone.now() - timedelta(minutes=10))
    assert client.get(reverse("healthz")).json()["queue"] == "stalled"


def test_supervision_is_staff_only_and_shows_metrics(client: Client, client_logged: Client, user: User) -> None:
    """Supervision réservée à l'administrateur : budget, latences, fiabilité."""
    assert client_logged.get(reverse("supervision")).status_code == 302
    for ms in (10_000, 20_000, 40_000):
        Dream.objects.create(user=user, status="done", processing_ms=ms)
    Dream.objects.create(user=user, status="failed")
    for status in ("ok", "ok", "error"):
        APICallLog.objects.create(
            kind="stt",
            provider="openai",
            model="m",
            status=status,
            latency_ms=1,
            cost_eur="1.0" if status == "ok" else "0",
        )
    admin = User.objects.create_superuser("admin@exemple.fr", PASSWORD)
    client.force_login(admin)
    response = client.get(reverse("supervision"), {"days": "abc"})
    metrics = response.context["metrics"]
    assert metrics["p50_ms"] == 20_000 and metrics["p95_ms"] == 40_000
    assert metrics["spent_eur"] == 2 and metrics["dreams"]["failed"] == 1
    assert metrics["providers"][0].error_rate == pytest.approx(1 / 3)
    assert "Budget API consommé" in response.content.decode()


def test_metrics_helpers() -> None:
    """Percentile par rang ; fenêtre vide sans erreur."""
    assert percentile([], 0.95) is None and percentile([5, 1, 3], 0.5) == 3
    assert snapshot(1)["p95_ms"] is None
