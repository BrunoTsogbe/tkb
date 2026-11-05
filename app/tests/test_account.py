"""KAN-15 (suppression), KAN-37 (mot de passe oublié), KAN-38 (export JSON)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from jsonschema import Draft202012Validator

from accounts.models import User
from ai.models import APICallLog
from dreams.models import Dream, Emotion
from tests.conftest import PASSWORD, UserFactory, make_wav

pytestmark = pytest.mark.django_db
SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "architecture" / "dream.schema.json").read_text("utf-8"))


def dream_with_files(user: User) -> Dream:
    dream = Dream.objects.create(
        user=user,
        status="done",
        transcript="Je volais",
        transcript_model="m",
        emotion=Emotion.objects.get(key="heureux"),
        emotion_scores={"heureux": 1.0},
    )
    dream.audio_file.save("a.wav", SimpleUploadedFile("a.wav", make_wav()), save=False)
    dream.image_file.save("i.png", SimpleUploadedFile("i.png", b"\x89PNG"), save=True)
    return dream


def test_delete_dream_removes_row_and_files(client_logged: Client, user: User) -> None:
    """Supprimer un rêve efface la ligne, l'image et l'audio (aucun fichier orphelin)."""
    dream = dream_with_files(user)
    files = [Path(dream.audio_file.path), Path(dream.image_file.path)]
    response = client_logged.post(reverse("dreams:delete", args=[dream.id]))
    assert response.url == reverse("dreams:collection")
    assert not Dream.objects.exists() and not any(f.exists() for f in files)


def test_cannot_delete_someone_elses_dream(client_logged: Client) -> None:
    """Le rêve d'un autre utilisateur n'est ni visible ni supprimable."""
    other = Dream.objects.create(user=UserFactory())
    assert client_logged.post(reverse("dreams:delete", args=[other.id])).status_code == 404
    assert Dream.objects.filter(pk=other.pk).exists()


def test_account_page_shows_consent_export_and_danger_zone(client_logged: Client) -> None:
    """La page Compte regroupe consentement, export et zone sensible."""
    page = client_logged.get(reverse("accounts:account")).content.decode()
    assert "Retirer mon consentement" in page and "Exporter mes rêves" in page and "SUPPRIMER" in page


def test_export_is_a_schema_compliant_json_attachment(client_logged: Client, user: User) -> None:
    """Export : pièce jointe JSON, rêves de l'utilisateur seulement, conformes au schéma."""
    dream_with_files(user)
    Dream.objects.create(user=UserFactory(), transcript="secret")
    response = client_logged.get(reverse("accounts:export"))
    assert response["Content-Disposition"].startswith('attachment; filename="mes-reves-')
    payload = json.loads(response.content)
    assert payload["account"]["email"] == user.email and len(payload["dreams"]) == 1
    validator = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)
    for item in payload["dreams"]:
        validator.validate(item)
    assert "secret" not in response.content.decode()


@pytest.mark.parametrize(("confirm", "password"), [("supprimer", PASSWORD), ("SUPPRIMER", "faux")], ids=["mot", "mdp"])
def test_account_deletion_requires_word_and_password(
    client_logged: Client, user: User, confirm: str, password: str
) -> None:
    """Confirmation renforcée : mot exact et mot de passe actuel."""
    response = client_logged.post(reverse("accounts:delete"), {"confirm": confirm, "password": password})
    assert response.status_code == 400 and User.objects.filter(pk=user.pk).exists()


def test_account_deletion_erases_everything_but_anonymous_costs(client_logged: Client, user: User) -> None:
    """Compte, rêves et fichiers supprimés ; coûts conservés sans lien avec la personne ; session fermée."""
    dream = dream_with_files(user)
    files = [Path(dream.audio_file.path), Path(dream.image_file.path)]
    APICallLog.objects.create(
        dream=dream, user=user, kind="stt", provider="openai", model="m", status="ok", latency_ms=1, cost_eur="0.01"
    )
    response = client_logged.post(reverse("accounts:delete"), {"confirm": "SUPPRIMER", "password": PASSWORD})
    assert response.url == reverse("accounts:signup")
    assert not User.objects.filter(pk=user.pk).exists() and not Dream.objects.exists()
    assert not any(f.exists() for f in files)
    log = APICallLog.objects.get()
    assert log.user is None and log.dream is None
    assert client_logged.get(reverse("dreams:record")).status_code == 302


def test_password_reset_sends_single_use_link_without_revealing_accounts(client: Client) -> None:
    """Même réponse que l'adresse existe ou non ; un seul e-mail, pour le compte existant."""
    UserFactory(email="lea@exemple.fr")
    for email in ("lea@exemple.fr", "inconnu@exemple.fr"):
        response = client.post(reverse("accounts:password_reset"), {"email": email})
        assert response.url == reverse("accounts:password_reset_done")
    assert len(mail.outbox) == 1 and mail.outbox[0].to == ["lea@exemple.fr"]
    link = next(line for line in mail.outbox[0].body.splitlines() if "/accounts/reset/" in line)
    path = link.split("testserver")[1]
    form = client.get(path, follow=True)
    assert form.context["validlink"]
    done = client.post(
        form.redirect_chain[-1][0], {"new_password1": "un-nouveau-secret-73", "new_password2": "un-nouveau-secret-73"}
    )
    assert done.url == reverse("accounts:password_reset_complete")
    assert User.objects.get(email="lea@exemple.fr").check_password("un-nouveau-secret-73")
    assert not client.get(path, follow=True).context["validlink"]  # lien à usage unique
