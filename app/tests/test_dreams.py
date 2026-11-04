"""KAN-16 et KAN-17 : modèles, dépôt d'un rêve, isolation, quota, sérialisation."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from jsonschema import Draft202012Validator

from accounts.models import User
from ai.models import APICallLog
from dreams.models import Dream, Emotion
from dreams.serializers import dream_to_dict
from dreams.services import quota_for
from tests.conftest import WEBM, UserFactory

pytestmark = pytest.mark.django_db

SCHEMA = json.loads((Path(__file__).resolve().parents[2] / "architecture" / "dream.schema.json").read_text("utf-8"))
Upload = Callable[..., SimpleUploadedFile]


def test_five_emotions_are_loaded() -> None:
    """La migration de données charge le référentiel des 5 émotions."""
    assert list(Emotion.objects.values_list("key", flat=True)) == [
        "heureux",
        "stressant",
        "triste",
        "etrange",
        "neutre",
    ]


def test_upload_creates_received_dream_with_random_file_name(
    client_logged: Client, user: User, audio_file: Upload
) -> None:
    """Étant donné un fichier valide, alors un rêve « received » est créé sous un nom aléatoire."""
    response = client_logged.post(reverse("dreams:create"), {"audio": audio_file("mon-reve-intime.wav")})
    dream = Dream.objects.get()
    assert response.status_code == 302 and response.url == reverse("dreams:detail", args=[dream.id])
    assert dream.user == user and dream.status == Dream.Status.RECEIVED
    assert dream.audio_format == "wav" and dream.audio_duration_s == pytest.approx(1)
    assert dream.audio_file.name == f"audio/{dream.id}.wav"
    assert "intime" not in dream.audio_file.name
    assert Path(dream.audio_file.path).exists()


def test_recorder_upload_returns_json_202(client_logged: Client, audio_file: Upload) -> None:
    """L'enregistreur du navigateur (WebM) reçoit un 202 et l'URL de suivi."""
    response = client_logged.post(
        reverse("dreams:create"), {"audio": audio_file("enregistrement.webm", WEBM)}, HTTP_ACCEPT="application/json"
    )
    assert response.status_code == 202
    assert response.json()["redirect"].startswith("/dreams/")


def test_invalid_file_is_rejected_and_nothing_is_stored(client_logged: Client, audio_file: Upload) -> None:
    """Étant donné un fichier invalide, alors un message précis s'affiche et rien n'est stocké."""
    response = client_logged.post(reverse("dreams:create"), {"audio": audio_file("reve.mp3", b"texte" * 10)})
    assert response.status_code == 400
    assert "ne correspond pas" in response.content.decode()
    assert not Dream.objects.exists()


def test_upload_requires_consent(audio_file: Upload) -> None:
    """Sans consentement, le dépôt est refusé (403) et l'enregistreur n'est pas proposé."""
    client = Client()
    client.force_login(UserFactory(consent=False))
    assert "J'accepte et je commence" in client.get(reverse("dreams:record")).content.decode()
    response = client.post(reverse("dreams:create"), {"audio": audio_file()}, HTTP_ACCEPT="application/json")
    assert response.status_code == 403
    assert not Dream.objects.exists()


def test_daily_quota_is_enforced(client_logged: Client, user: User, audio_file: Upload) -> None:
    """Au-delà de 5 rêves en 24 h, le dépôt est refusé (429) avec un message clair."""
    for _ in range(5):
        assert client_logged.post(reverse("dreams:create"), {"audio": audio_file()}).status_code == 302
    assert quota_for(user).exhausted
    response = client_logged.post(reverse("dreams:create"), {"audio": audio_file()})
    assert response.status_code == 429
    assert "Revenez demain" in response.content.decode()
    assert Dream.objects.count() == 5


def test_pages_require_login(client: Client) -> None:
    """Toutes les pages de rêves exigent une session."""
    assert client.get(reverse("dreams:record")).status_code == 302
    assert client.post(reverse("dreams:create")).status_code == 302


def test_detail_of_another_users_dream_is_404(client_logged: Client) -> None:
    """Un rêve d'un autre utilisateur renvoie 404 (et non 403)."""
    other = Dream.objects.create(user=UserFactory())
    assert client_logged.get(reverse("dreams:detail", args=[other.id])).status_code == 404


def test_detail_shows_received_status(client_logged: Client, user: User) -> None:
    """La page de suivi affiche l'état du rêve."""
    dream = Dream.objects.create(user=user, audio_duration_s=42)
    page = client_logged.get(reverse("dreams:detail", args=[dream.id])).content.decode()
    assert "bien reçu" in page and "42 s" in page


def test_for_user_isolates_dreams(user: User) -> None:
    """Le manager ``for_user`` ne renvoie que les rêves du propriétaire."""
    mine = Dream.objects.create(user=user)
    Dream.objects.create(user=UserFactory())
    assert list(Dream.objects.for_user(user)) == [mine]


def test_delete_audio_keeps_proof_of_deletion(client_logged: Client, audio_file: Upload) -> None:
    """La suppression de l'audio efface le fichier et horodate l'opération (RGPD)."""
    client_logged.post(reverse("dreams:create"), {"audio": audio_file()})
    dream = Dream.objects.get()
    path = Path(dream.audio_file.path)
    dream.delete_audio()
    assert not path.exists() and dream.audio_deleted_at is not None and not dream.audio_file


def test_api_call_log_survives_account_deletion(user: User) -> None:
    """Supprimer un compte supprime ses rêves mais garde le coût, anonymisé."""
    dream = Dream.objects.create(user=user)
    log = APICallLog.objects.create(
        dream=dream,
        user=user,
        kind="stt",
        provider="openai",
        model="gpt-transcribe",
        status="ok",
        latency_ms=8000,
        cost_eur="0.00828",
    )
    user.delete()
    log.refresh_from_db()
    assert log.user is None and log.dream is None and str(log.cost_eur) == "0.00828"
    assert "Transcription" in str(log)


def test_serialization_matches_json_schema(user: User) -> None:
    """Un rêve reçu puis un rêve complet sont conformes au schéma JSON documenté."""
    validator = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)
    dream = Dream.objects.create(user=user, audio_format="wav", audio_duration_s=12.5)
    validator.validate(dream_to_dict(dream))

    dream.status = Dream.Status.DONE
    dream.transcript, dream.transcript_model = "Je volais au-dessus d'une forêt.", "gpt-transcribe"
    dream.emotion = Emotion.objects.get(key="heureux")
    dream.emotion_scores = {"heureux": 0.8, "neutre": 0.2}
    dream.image_file.name, dream.image_model = "dreams/2026/11/x.png", "gpt-image-1-mini"
    dream.save()
    data = dream_to_dict(dream)
    validator.validate(data)
    assert data["image"]["ai_generated"] is True and data["emotion"]["score"] == 0.8

    dream.status, dream.error_code, dream.error_step = Dream.Status.FAILED, "timeout", "image"
    validator.validate(dream_to_dict(dream))
    assert str(dream).startswith("Rêve") and dream.is_finished
