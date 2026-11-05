"""Politique d'appel, budget, tarifs, prompt, émotion, registre (KAN-19, KAN-21, KAN-23)."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core.cache import cache

from ai import budget, policy
from ai.fallback import render_fallback
from ai.models import APICallLog
from ai.policy import FREE, Billing, call_with_policy
from ai.pricing import estimate_dream_cost_eur, image_cost_usd, stt_cost_usd, usd_to_eur
from ai.prompt import build_image_prompt, strip_identifiers
from ai.providers import get_emotion_classifier, get_image_generator, get_transcriber
from ai.providers.base import BudgetExhausted, CircuitOpen, ContentRefused, ProviderError, ProviderTimeout
from ai.providers.emotion import KeywordClassifier, ZeroShotClassifier
from ai.providers.fake import FakeImageGenerator, FakeTranscriber
from ai.providers.openai_api import OpenAIImageGenerator, OpenAITranscriber

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cache vide et attentes neutralisées."""
    cache.clear()
    monkeypatch.setattr(policy, "sleep", lambda seconds: None)


def flaky(failures: list[Exception], result: str = "ok"):
    """Opération qui échoue avec les erreurs données, puis réussit."""
    calls = {"n": 0}

    def operation() -> str:
        calls["n"] += 1
        if failures:
            raise failures.pop(0)
        return result

    operation.calls = calls  # type: ignore[attr-defined]
    return operation


def run(operation, retries: int = 2, billing=lambda r: Billing(Decimal("2"), Decimal("0.009"))) -> str:
    return call_with_policy(
        operation, kind="stt", provider="openai", model="gpt-transcribe", billing=billing, retries=retries
    )


# --- politique d'appel -------------------------------------------------------------------------------


def test_success_logs_latency_and_cost() -> None:
    """Un succès journalise la latence, les unités et le coût en dollars et en euros."""
    assert run(flaky([])) == "ok"
    log = APICallLog.objects.get()
    assert log.status == "ok" and log.attempt == 1 and log.units == Decimal("2")
    assert log.cost_usd == Decimal("0.00900") and log.cost_eur == Decimal("0.00828")


def test_transient_errors_are_retried_then_succeed() -> None:
    """Timeout puis 5xx : deux relances, trois lignes de journal, succès final."""
    operation = flaky([ProviderTimeout("t"), ProviderError("5xx", http_status=503)])
    assert run(operation) == "ok"
    assert operation.calls["n"] == 3
    assert list(APICallLog.objects.order_by("attempt").values_list("status", flat=True)) == ["timeout", "error", "ok"]


def test_retries_are_bounded() -> None:
    """Au-delà du nombre de relances, l'erreur remonte."""
    with pytest.raises(ProviderError):
        run(flaky([ProviderError("a"), ProviderError("b"), ProviderError("c")]), retries=1)
    assert APICallLog.objects.count() == 2


def test_non_retryable_errors_stop_immediately() -> None:
    """Un refus de contenu n'est jamais relancé (budget)."""
    operation = flaky([ContentRefused("non", http_status=400)])
    with pytest.raises(ContentRefused):
        run(operation)
    assert operation.calls["n"] == 1


def test_retry_after_is_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le délai ``Retry-After`` du fournisseur est appliqué (plafonné à 30 s)."""
    delays: list[float] = []
    monkeypatch.setattr(policy, "sleep", delays.append)
    run(flaky([ProviderError("429", retry_after=7)]))
    assert 7 <= delays[0] < 7.6


def test_circuit_opens_after_five_failures() -> None:
    """5 échecs en 5 minutes : le fournisseur est suspendu, l'appel est refusé sans être tenté."""
    for _ in range(5):
        with pytest.raises(ProviderError):
            run(flaky([ProviderError("x")]), retries=0)
    operation = flaky([])
    with pytest.raises(CircuitOpen):
        run(operation)
    assert operation.calls["n"] == 0


def test_free_calls_do_not_touch_budget() -> None:
    """Un appel gratuit (modèle local) est journalisé à coût nul."""
    run(flaky([]), billing=lambda r: FREE)
    assert APICallLog.objects.get().cost_eur == 0


# --- budget et tarifs --------------------------------------------------------------------------------


def test_prices_match_benchmark() -> None:
    """2 min + 1 image = 0,0184 € (dossier de cadrage, section 9.1)."""
    assert stt_cost_usd(Decimal(2)) == Decimal("0.00900") and image_cost_usd(1) == Decimal("0.01100")
    assert usd_to_eur(Decimal("0.02")) == Decimal("0.01840")
    assert estimate_dream_cost_eur(None) == estimate_dream_cost_eur(120) == Decimal("0.01840")


def spend(eur: str) -> None:
    APICallLog.objects.create(kind="stt", provider="openai", model="m", status="ok", latency_ms=1, cost_eur=eur)
    cache.clear()


@pytest.mark.parametrize(
    ("spent", "kind", "allowed"),
    [("10", "image", True), ("18.99", "image", False), ("18.99", "stt", True), ("19.99", "stt", False)],
    ids=["50%", "image-95%", "stt-95%", "stt-100%"],
)
def test_budget_thresholds(spent: str, kind: str, allowed: bool) -> None:
    """95 % : plus d'images ; 100 % : plus aucun appel payant."""
    spend(spent)
    if allowed:
        budget.ensure_can_spend(kind, Decimal("0.01"))
    else:
        with pytest.raises(BudgetExhausted):
            budget.ensure_can_spend(kind, Decimal("0.01"))


def test_budget_alert_is_logged_once_at_80_percent(caplog: pytest.LogCaptureFixture) -> None:
    """Le passage de 80 % déclenche une seule alerte."""
    spend("16.5")
    budget.record_spend()
    budget.record_spend()
    assert sum("budget_alert" in r.message for r in caplog.records) == 1
    assert budget.usage_ratio() == Decimal("0.825")


def test_spent_is_cached() -> None:
    """Le montant consommé est mis en cache 60 s ; ``fresh`` force le recalcul."""
    spend("1")
    assert budget.spent_eur() == Decimal("1")
    APICallLog.objects.create(kind="stt", provider="o", model="m", status="ok", latency_ms=1, cost_eur="2")
    assert budget.spent_eur() == Decimal("1") and budget.spent_eur(fresh=True) == Decimal("3")


# --- prompt, émotion, image de secours, registre -----------------------------------------------------


def test_prompt_removes_names_and_contacts() -> None:
    """Noms propres, e-mails et numéros ne partent pas chez le fournisseur d'images."""
    text = "Hier soir, je dansais avec Julien à Lyon. Il m'écrivait à julien@mail.fr ou au 06 12 34 56 78."
    cleaned = strip_identifiers(text)
    for secret in ("Julien", "Lyon", "@", "06 12"):
        assert secret not in cleaned
    assert cleaned.startswith("Hier soir") and "Il m'écrivait" in cleaned
    prompt = build_image_prompt(text * 30, "Heureux")
    assert "Ambiance : heureux" in prompt and len(prompt) < 1000 and "sans visage reconnaissable" in prompt


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("J'avais peur, j'étais en retard à l'examen", "stressant"),
        ("Quelle joie, du soleil !", "heureux"),
        ("Seul, je voulais pleurer", "triste"),
        ("C'était bizarre, la maison flottait", "etrange"),
        ("J'achetais du pain", "neutre"),
    ],
)
def test_keyword_classifier(text: str, expected: str) -> None:
    """Le classifieur de repli couvre les cinq ambiances ; la distribution somme à 1."""
    result = KeywordClassifier().classify(text)
    assert result.key == expected and abs(sum(result.scores.values()) - 1) < 0.01


def test_zero_shot_classifier_maps_french_labels(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le modèle Hugging Face renvoie des étiquettes françaises, ramenées aux clés du référentiel."""
    fake = lambda text, **kw: {"labels": ["étrange", "neutre"], "scores": [0.7, 0.3]}  # noqa: E731
    monkeypatch.setattr(ZeroShotClassifier, "_pipeline", fake)
    result = ZeroShotClassifier().classify("un rêve")
    assert result.key == "etrange" and result.scores == {"etrange": 0.7, "neutre": 0.3}


def test_registry_uses_configuration(settings: object) -> None:
    """Le fournisseur est une donnée de configuration ; Hugging Face absent → mots-clés."""
    assert isinstance(get_transcriber(), FakeTranscriber) and isinstance(get_image_generator(), FakeImageGenerator)
    settings.AI_STT_PROVIDER = settings.AI_IMAGE_PROVIDER = "openai"  # type: ignore[attr-defined]
    settings.AI_EMOTION_PROVIDER = "huggingface"  # type: ignore[attr-defined]
    assert isinstance(get_transcriber(), OpenAITranscriber) and isinstance(get_image_generator(), OpenAIImageGenerator)
    assert isinstance(get_emotion_classifier(), (KeywordClassifier, ZeroShotClassifier))


def test_fake_providers_are_deterministic_and_free() -> None:
    """Les doublures ne coûtent rien et répondent toujours pareil."""
    first = FakeTranscriber().transcribe(b"audio", "r.wav", duration_s=60)
    assert first == FakeTranscriber().transcribe(b"audio", "r.wav", duration_s=60)
    assert FakeImageGenerator().generate("p").content[:4] == b"\x89PNG"
    assert render_fallback("seed", "#f43f5e", size=64)[:4] == b"\x89PNG"
