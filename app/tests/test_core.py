"""Socle : sonde de santé, admin, configuration de production."""

from __future__ import annotations

import pytest
from django.core.management import call_command
from django.db import DatabaseError
from django.test import Client
from django.urls import reverse

from accounts.models import User
from tests.conftest import PASSWORD

pytestmark = pytest.mark.django_db


def test_healthz_reports_ok(client: Client) -> None:
    """La sonde répond 200 sans exposer d'information sensible."""
    response = client.get(reverse("healthz"))
    assert response.status_code == 200 and response.json() == {"status": "ok", "database": "ok"}


def test_healthz_reports_database_failure(client: Client, monkeypatch: pytest.MonkeyPatch) -> None:
    """Base injoignable : 503, pour que la plateforme redémarre ou alerte."""

    def broken(*args: object, **kwargs: object) -> None:
        raise DatabaseError("down")

    monkeypatch.setattr("core.views.connection.cursor", broken)
    assert client.get(reverse("healthz")).status_code == 503


def test_admin_lists_models(client: Client) -> None:
    """L'admin affiche rêves, émotions et journal des appels (en lecture seule)."""
    client.force_login(User.objects.create_superuser("admin@exemple.fr", PASSWORD))
    for url in (
        "/admin/dreams/dream/",
        "/admin/dreams/emotion/",
        "/admin/ai/apicalllog/",
        "/admin/accounts/user/",
        "/admin/ai/apicalllog/add/",
    ):
        response = client.get(url)
        assert response.status_code == (403 if url.endswith("add/") else 200), url


def test_no_missing_migrations() -> None:
    """Les modèles et les migrations sont synchronisés (aussi vérifié en CI)."""
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)


def test_production_settings_pass_deploy_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Les réglages de production activent HTTPS, HSTS et cookies sécurisés."""
    monkeypatch.setenv("DJANGO_SECRET_KEY", "x" * 60)
    import importlib

    import config.settings.prod as prod

    importlib.reload(prod)
    assert prod.DEBUG is False and prod.SESSION_COOKIE_SECURE and prod.CSRF_COOKIE_SECURE
    assert prod.SECURE_HSTS_SECONDS >= 31536000 and prod.SECURE_SSL_REDIRECT
