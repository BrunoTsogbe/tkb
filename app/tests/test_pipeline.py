"""Pipeline d'un rêve et vues du Sprint 2 (KAN-14, KAN-18 à KAN-22)."""

from __future__ import annotations

from collections.abc import Callable
from decimal import Decimal
from pathlib import Path

import pytest
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from accounts.models import User
from ai import policy
from ai.models import APICallLog
from ai.providers.base import BudgetExhausted, ContentRefused, GeneratedImage, ProviderError, Transcript
from dreams.models import Dream, Emotion
from dreams.pipeline import process_dream
from tests.conftest import UserFactory, make_wav

pytestmark = pytest.mark.django_db
Upload = Callable[..., SimpleUploadedFile]


@pytest.fixture(autouse=True)
def no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cache vide, relances instantanées."""
    cache.clear()
    monkeypatch.setattr(policy, "sleep", lambda seconds: None)


def submit(client: Client, upload: Upload, django_capture_on_commit_callbacks) -> Dream:
    """Dépose un rêve et exécute le traitement (mode « eager »)."""
    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(reverse("dreams:collection"), {"audio": upload()})
    assert response.status_code == 302
    return Dream.objects.get(pk=response.url.split("/")[2])


class PaidTranscriber:
    """Transcripteur payant contrôlable."""

    provider, model, paid = "openai", "gpt-transcribe", True

    def __init__(self, errors: list[Exception] | None = None) -> None:
        self.errors, self.calls = errors or [], 0

    def transcribe(self, audio: bytes, filename: str, *, duration_s: float | None = None) -> Transcript:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return Transcript("Je volais avec Julien au-dessus d'une forêt, quelle joie !", self.model, Decimal(2))


class PaidImages:
    """Générateur d'images payant contrôlable."""

    provider, model, paid = "openai", "gpt-image-1-mini", True

    def __init__(self, error: Exception | None = None) -> None:
        self.error, self.prompts = error, []

    def generate(self, prompt: str) -> GeneratedImage:
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return GeneratedImage(b"\x89PNG-real", self.model)


def use(monkeypatch: pytest.MonkeyPatch, transcriber=None, images=None) -> None:
    if transcriber:
        monkeypatch.setattr("dreams.pipeline.get_transcriber", lambda: transcriber)
    if images:
        monkeypatch.setattr("dreams.pipeline.get_image_generator", lambda: images)


def test_full_pipeline_with_fake_providers(
    client_logged: Client, audio_file: Upload, django_capture_on_commit_callbacks
) -> None:
    """Dépôt → transcription, ambiance, image ; audio supprimé ; coût nul en mode démo."""
    dream = submit(client_logged, audio_file, django_capture_on_commit_callbacks)
    assert dream.status == Dream.Status.DONE
    assert dream.transcript and dream.transcript_model == "fake-stt"
    assert dream.emotion is not None and abs(sum(dream.emotion_scores.values()) - 1) < 0.01
    assert dream.image_file and dream.image_model == "fake-image" and not dream.image_is_fallback
    assert not dream.audio_file and dream.audio_deleted_at is not None
    assert dream.cost_eur == 0 and dream.processing_ms is not None
    assert set(APICallLog.objects.values_list("kind", flat=True)) == {"stt", "emotion", "image"}


def test_paid_pipeline_costs_and_minimised_prompt(monkeypatch: pytest.MonkeyPatch, user: User) -> None:
    """Avec des fournisseurs payants : coût réel cumulé, prompt sans nom propre."""
    images = PaidImages()
    use(monkeypatch, PaidTranscriber(), images)
    dream = Dream.objects.create(user=user, audio_format="wav", audio_duration_s=120)
    dream.audio_file.save("x.wav", SimpleUploadedFile("x.wav", make_wav()), save=True)
    dream = process_dream(dream.id)
    assert dream.status == Dream.Status.DONE and dream.emotion.key == "heureux"
    assert dream.cost_eur == Decimal("0.01840")
    assert "Julien" not in images.prompts[0] and dream.image_prompt == images.prompts[0]


def test_transcription_failure_then_retry_resumes(
    monkeypatch: pytest.MonkeyPatch, client_logged: Client, audio_file: Upload, django_capture_on_commit_callbacks
) -> None:
    """Panne durable : « failed » à l'étape transcription, audio conservé ; « Réessayer » termine le rêve."""
    transcriber = PaidTranscriber([ProviderError("503")] * 3)
    use(monkeypatch, transcriber, PaidImages())
    dream = submit(client_logged, audio_file, django_capture_on_commit_callbacks)
    assert (dream.status, dream.error_step, dream.error_code) == ("failed", "transcription", "provider_error")
    assert dream.audio_file and transcriber.calls == 3
    page = client_logged.get(reverse("dreams:detail", args=[dream.id])).content.decode()
    assert "Réessayer" in page and "conservé" in page

    with django_capture_on_commit_callbacks(execute=True):
        client_logged.post(reverse("dreams:retry", args=[dream.id]))
    dream.refresh_from_db()
    assert dream.status == Dream.Status.DONE and not dream.error_code


def test_retry_does_not_rebill_successful_steps(monkeypatch: pytest.MonkeyPatch, user: User) -> None:
    """Échec à l'image : la reprise ne relance pas la transcription (idempotence)."""
    transcriber = PaidTranscriber()
    use(monkeypatch, transcriber, PaidImages(ProviderError("down")))
    dream = Dream.objects.create(user=user, audio_format="wav")
    dream.audio_file.save("x.wav", SimpleUploadedFile("x.wav", make_wav()), save=True)
    dream = process_dream(dream.id)
    assert dream.status == "failed" and dream.error_step == "image"
    use(monkeypatch, images=PaidImages())
    dream = process_dream(dream.id)
    assert dream.status == "done" and transcriber.calls == 1


@pytest.mark.parametrize("error", [ContentRefused("non"), BudgetExhausted("budget")], ids=["refus", "budget"])
def test_image_fallback_keeps_dream_done(monkeypatch: pytest.MonkeyPatch, user: User, error: Exception) -> None:
    """Refus de contenu ou budget épuisé : image de secours, rêve tout de même « done »."""
    use(monkeypatch, PaidTranscriber(), PaidImages(error))
    dream = Dream.objects.create(user=user, audio_format="wav")
    dream.audio_file.save("x.wav", SimpleUploadedFile("x.wav", make_wav()), save=True)
    dream = process_dream(dream.id)
    assert dream.status == "done" and dream.image_is_fallback and dream.image_model == "fallback"


def test_budget_exhausted_blocks_transcription(monkeypatch: pytest.MonkeyPatch, user: User) -> None:
    """Budget à 100 % : aucun appel payant, le rêve échoue proprement."""
    APICallLog.objects.create(kind="stt", provider="openai", model="m", status="ok", latency_ms=1, cost_eur="20")
    transcriber = PaidTranscriber()
    use(monkeypatch, transcriber)
    dream = Dream.objects.create(user=user, audio_format="wav")
    dream.audio_file.save("x.wav", SimpleUploadedFile("x.wav", make_wav()), save=True)
    dream = process_dream(dream.id)
    assert dream.error_code == "budget_exhausted" and transcriber.calls == 0


def test_missing_audio_and_emotion_failure(monkeypatch: pytest.MonkeyPatch, user: User) -> None:
    """Audio disparu : échec non relançable ; panne du modèle d'émotion : repli sur les mots-clés."""
    dream = process_dream(Dream.objects.create(user=user).id)
    assert dream.error_code == "invalid_audio"

    class Broken:
        provider, model = "huggingface", "x"

        def classify(self, text: str) -> None:
            raise RuntimeError("model crashed")

    monkeypatch.setattr("dreams.pipeline.get_emotion_classifier", lambda: Broken())
    ready = Dream.objects.create(user=user, transcript="J'avais peur dans le noir")
    assert process_dream(ready.id).emotion.key == "stressant"


def test_locked_or_done_dreams_are_not_reprocessed(user: User) -> None:
    """Verrou par rêve ; un rêve terminé n'est pas retraité."""
    dream = Dream.objects.create(user=user, status=Dream.Status.DONE)
    assert process_dream(dream.id).status == "done" and not APICallLog.objects.exists()
    cache.add(f"dream:lock:{dream.id}", True)
    assert process_dream(dream.id) is None


# --- vues ---------------------------------------------------------------------------------------------


def done_dream(user: User, **fields: object) -> Dream:
    dream = Dream.objects.create(
        user=user,
        status="done",
        transcript="Je volais",
        transcript_model="m",
        emotion=Emotion.objects.get(key="heureux"),
        emotion_scores={"heureux": 1.0},
        **fields,
    )
    dream.image_file.save("i.png", SimpleUploadedFile("i.png", b"\x89PNG-img"), save=True)
    return dream


def test_result_page_status_fragment_and_private_image(client_logged: Client, user: User) -> None:
    """Résultat : image servie au seul propriétaire, mention IA, fragment de statut terminé."""
    dream = done_dream(user)
    page = client_logged.get(reverse("dreams:detail", args=[dream.id])).content.decode()
    assert "Image générée par IA" in page and "pas un diagnostic" in page and "Heureux" in page
    assert 'data-finished="1"' in client_logged.get(reverse("dreams:status", args=[dream.id])).content.decode()
    image = client_logged.get(reverse("dreams:image", args=[dream.id]))
    assert image.status_code == 200 and b"".join(image.streaming_content) == b"\x89PNG-img"
    assert image["Cache-Control"] == "private, max-age=3600"

    stranger = Client()
    stranger.force_login(UserFactory())
    assert stranger.get(reverse("dreams:image", args=[dream.id])).status_code == 404
    assert client_logged.get(reverse("dreams:image", args=[Dream.objects.create(user=user).id])).status_code == 404


def test_user_can_correct_transcript_and_emotion(client_logged: Client, user: User) -> None:
    """Corrections enregistrées et tracées (``transcript_edited``, ``emotion_corrected``)."""
    dream = done_dream(user)
    triste = Emotion.objects.get(key="triste")
    client_logged.post(reverse("dreams:edit", args=[dream.id]), {"transcript": "Je tombais", "emotion": triste.id})
    dream.refresh_from_db()
    assert dream.transcript == "Je tombais" and dream.transcript_edited
    assert dream.emotion == triste and dream.emotion_corrected


def test_edit_is_refused_while_processing(client_logged: Client, user: User) -> None:
    """Pas de correction tant que le traitement n'est pas terminé."""
    dream = Dream.objects.create(user=user, status="transcribing")
    client_logged.post(reverse("dreams:edit", args=[dream.id]), {"transcript": "x", "emotion": 1})
    dream.refresh_from_db()
    assert dream.transcript == "" and not dream.transcript_edited


def test_history_is_paginated_isolated_and_has_empty_state(client_logged: Client, user: User) -> None:
    """Historique : 20 par page, rêves de l'utilisateur seulement, état vide explicite."""
    assert "Votre ciel est encore vide" in client_logged.get(reverse("dreams:collection")).content.decode()
    for _ in range(21):
        done_dream(user)
    Dream.objects.create(user=UserFactory(), transcript="secret d'un autre")
    first = client_logged.get(reverse("dreams:collection"))
    assert len(first.context["page"].object_list) == 20 and "Page 1 / 2" in first.content.decode()
    assert "secret d'un autre" not in first.content.decode()
    assert len(client_logged.get(reverse("dreams:collection") + "?page=2").context["page"].object_list) == 1


def test_retry_ignores_dreams_that_did_not_fail(client_logged: Client, user: User) -> None:
    """« Réessayer » n'a d'effet que sur un rêve en échec."""
    dream = done_dream(user)
    client_logged.post(reverse("dreams:retry", args=[dream.id]))
    dream.refresh_from_db()
    assert dream.status == "done"


def test_celery_task_runs_pipeline(user: User) -> None:
    """La tâche Celery délègue au pipeline (exécutée de façon synchrone en test)."""
    from dreams.tasks import process_dream_task

    dream = Dream.objects.create(user=user)
    process_dream_task.delay(str(dream.id))
    dream.refresh_from_db()
    assert dream.error_code == "invalid_audio"


def test_media_is_written_under_media_root(user: User, settings: object) -> None:
    """Les images générées sont stockées dans le dossier des médias, sous un nom aléatoire."""
    dream = done_dream(user)
    assert Path(dream.image_file.path).is_relative_to(Path(settings.MEDIA_ROOT))  # type: ignore[attr-defined]
    assert str(dream.id) in dream.image_file.name
