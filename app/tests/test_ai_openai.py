"""Fournisseur OpenAI simulé par httpx.MockTransport (KAN-18, KAN-20, KAN-28)."""

from __future__ import annotations

import base64
import json
from decimal import Decimal

import httpx
import pytest

from ai.providers.base import ContentRefused, InvalidRequest, ProviderError, ProviderTimeout, QuotaExceeded
from ai.providers.openai_api import OpenAIImageGenerator, OpenAITranscriber

PNG = b"\x89PNG\r\n\x1a\n-fake"


def transport(status: int = 200, body: object = None, headers: dict | None = None) -> httpx.MockTransport:
    """Transport qui renvoie toujours la même réponse et mémorise la requête."""

    def handler(request: httpx.Request) -> httpx.Response:
        handler.last = request  # type: ignore[attr-defined]
        return httpx.Response(status, json=body, headers=headers)

    return httpx.MockTransport(handler)


def test_transcription_success_sends_model_language_and_key() -> None:
    """La requête vise gpt-transcribe en français, avec la clé ; la durée connue sert au coût."""
    mock = transport(body={"text": "  Je volais.  "})
    result = OpenAITranscriber(transport=mock).transcribe(b"RIFF....", "r.wav", duration_s=90)
    request = mock.handler.last  # type: ignore[attr-defined]
    assert request.url.path.endswith("/audio/transcriptions")
    assert request.headers["Authorization"] == "Bearer sk-test"
    assert b"gpt-transcribe" in request.content and b'name="language"' in request.content
    assert result.text == "Je volais." and result.billed_minutes == Decimal("1.5")


def test_transcription_uses_usage_seconds_when_duration_unknown() -> None:
    """Sans durée connue (WebM), on facture la durée renvoyée par le fournisseur, sinon 2 min."""
    with_usage = OpenAITranscriber(transport=transport(body={"text": "ok", "usage": {"seconds": 30}}))
    assert with_usage.transcribe(b"x", "r.webm").billed_minutes == Decimal("0.5")
    without = OpenAITranscriber(transport=transport(body={"text": "ok"}))
    assert without.transcribe(b"x", "r.webm").billed_minutes == Decimal(2)


def test_empty_transcription_is_not_retryable() -> None:
    """Aucune parole détectée : erreur définitive, inutile de relancer."""
    with pytest.raises(InvalidRequest):
        OpenAITranscriber(transport=transport(body={"text": " "})).transcribe(b"x", "r.wav")


@pytest.mark.parametrize(
    ("status", "body", "headers", "error", "retryable"),
    [
        (429, {"error": {"message": "slow down"}}, {"Retry-After": "7"}, QuotaExceeded, True),
        (500, {"error": {"message": "boom"}}, None, ProviderError, True),
        (413, {"error": {"message": "too big"}}, None, InvalidRequest, False),
        (401, {"error": {"message": "bad key"}}, None, InvalidRequest, False),
        (400, {"error": {"code": "content_policy_violation", "message": "no"}}, None, ContentRefused, False),
    ],
    ids=["429", "500", "413", "401", "refus"],
)
def test_http_errors_are_typed(status: int, body: object, headers: dict | None, error: type, retryable: bool) -> None:
    """Chaque erreur HTTP devient une erreur typée, relançable ou non."""
    with pytest.raises(error) as caught:
        OpenAIImageGenerator(transport=transport(status, body, headers)).generate("une forêt")
    assert caught.value.retryable is retryable and caught.value.http_status == status
    if status == 429:
        assert caught.value.retry_after == 7.0


def test_timeout_and_network_errors() -> None:
    """Délai dépassé et coupure réseau sont relançables."""

    def timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(ProviderTimeout):
        OpenAITranscriber(transport=httpx.MockTransport(timeout)).transcribe(b"x", "r.wav")
    with pytest.raises(ProviderError) as caught:
        OpenAITranscriber(transport=httpx.MockTransport(broken)).transcribe(b"x", "r.wav")
    assert caught.value.retryable


def test_unreadable_responses_are_errors() -> None:
    """Réponse non JSON ou incomplète : erreur relançable, jamais de plantage."""

    def not_json(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"<html>")

    def bad_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, content=b"Bad gateway")

    with pytest.raises(ProviderError):
        OpenAITranscriber(transport=httpx.MockTransport(not_json)).transcribe(b"x", "r.wav")
    with pytest.raises(ProviderError):
        OpenAIImageGenerator(transport=httpx.MockTransport(bad_error)).generate("x")
    with pytest.raises(ProviderError):
        OpenAIImageGenerator(transport=transport(body={"data": []})).generate("x")


def test_image_success_decodes_base64() -> None:
    """L'image est demandée en 1024×1024 qualité moyenne et décodée."""
    mock = transport(body={"data": [{"b64_json": base64.b64encode(PNG).decode()}]})
    image = OpenAIImageGenerator(transport=mock).generate("une forêt")
    sent = json.loads(mock.handler.last.content)  # type: ignore[attr-defined]
    assert sent == {
        "model": "gpt-image-1-mini",
        "prompt": "une forêt",
        "size": "1024x1024",
        "quality": "medium",
        "n": 1,
    }
    assert image.content == PNG and image.billed_images == 1
