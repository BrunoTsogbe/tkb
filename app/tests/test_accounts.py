"""KAN-13 (US-01) et KAN-36 : inscription, connexion, limitation, consentement."""

from __future__ import annotations

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from accounts.models import User
from tests.conftest import PASSWORD, UserFactory

pytestmark = pytest.mark.django_db

SIGNUP = {"email": "Lea@Exemple.fr", "password1": PASSWORD, "password2": PASSWORD, "terms": "on"}


def test_signup_creates_account_logs_in_and_records_consent(client: Client) -> None:
    """Étant donné un visiteur, quand il s'inscrit et consent, alors il est connecté et consentant."""
    response = client.post(reverse("accounts:signup"), {**SIGNUP, "ai_consent": "on"})
    assert response.status_code == 302
    user = User.objects.get(email="lea@exemple.fr")
    assert user.profile.has_ai_consent
    assert user.profile.consent_version == "1.0"
    assert client.get(reverse("dreams:record")).status_code == 200


def test_consent_is_optional_and_not_precheked(client: Client) -> None:
    """Le consentement est facultatif et la case n'est pas cochée par défaut."""
    page = client.get(reverse("accounts:signup")).content.decode()
    assert 'name="ai_consent"' in page and "checked" not in page.split('name="ai_consent"')[1][:40]
    client.post(reverse("accounts:signup"), SIGNUP)
    assert not User.objects.get(email="lea@exemple.fr").profile.has_ai_consent


def test_signup_rejects_duplicate_email_and_keeps_form(client: Client) -> None:
    """Un e-mail déjà utilisé affiche un message clair, le formulaire est conservé."""
    UserFactory(email="lea@exemple.fr")
    response = client.post(reverse("accounts:signup"), SIGNUP)
    assert response.status_code == 200
    assert "Un compte existe déjà" in response.content.decode()
    assert User.objects.filter(email="lea@exemple.fr").count() == 1


def test_signup_requires_terms(client: Client) -> None:
    """Les conditions d'utilisation doivent être acceptées."""
    data = {k: v for k, v in SIGNUP.items() if k != "terms"}
    assert client.post(reverse("accounts:signup"), data).status_code == 200
    assert not User.objects.exists()


def test_password_is_hashed_with_strong_rules(client: Client) -> None:
    """Le mot de passe n'est jamais stocké en clair ; un mot de passe court est refusé."""
    weak = {**SIGNUP, "password1": "court", "password2": "court"}
    assert client.post(reverse("accounts:signup"), weak).status_code == 200
    client.post(reverse("accounts:signup"), SIGNUP)
    user = User.objects.get(email="lea@exemple.fr")
    assert user.password != PASSWORD and user.check_password(PASSWORD)


def test_login_and_logout(client: Client) -> None:
    """Connexion par e-mail, puis déconnexion."""
    UserFactory(email="karim@exemple.fr")
    response = client.post(reverse("accounts:login"), {"username": "karim@exemple.fr", "password": PASSWORD})
    assert response.status_code == 302
    assert client.post(reverse("accounts:logout")).status_code == 302
    assert client.get(reverse("dreams:record")).status_code == 302


def test_login_is_rate_limited_after_five_failures(client: Client) -> None:
    """Étant donné 5 échecs, alors les tentatives suivantes sont refusées (429)."""
    cache.clear()
    UserFactory(email="karim@exemple.fr")
    bad = {"username": "karim@exemple.fr", "password": "faux"}
    for _ in range(5):
        assert client.post(reverse("accounts:login"), bad).status_code == 200
    response = client.post(reverse("accounts:login"), {"username": "karim@exemple.fr", "password": PASSWORD})
    assert response.status_code == 429
    assert "Trop de tentatives" in response.content.decode()
    cache.clear()


def test_consent_can_be_given_and_withdrawn(client_logged: Client, user: User) -> None:
    """Le consentement se retire puis se redonne depuis l'application."""
    client_logged.post(reverse("accounts:consent"), {"action": "withdraw"})
    user.profile.refresh_from_db()
    assert not user.profile.has_ai_consent
    response = client_logged.post(reverse("accounts:consent"), {"action": "give", "next": "https://evil.example"})
    user.profile.refresh_from_db()
    assert user.profile.has_ai_consent
    assert response.url == reverse("dreams:record")  # redirection externe refusée


def test_manager_requires_email() -> None:
    """La création d'un utilisateur sans e-mail est refusée."""
    with pytest.raises(ValueError):
        User.objects.create_user("")


def test_superuser_has_admin_rights() -> None:
    """Un administrateur créé en ligne de commande accède à l'admin."""
    admin = User.objects.create_superuser("admin@exemple.fr", PASSWORD)
    assert admin.is_staff and admin.is_superuser
    assert str(admin) == "admin@exemple.fr"
