"""Validation des fichiers audio (KAN-17)."""

from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError

from dreams.audio import MAX_DURATION_S, validate_audio, wav_duration
from tests.conftest import MP3, WEBM, make_wav


@pytest.mark.parametrize(
    ("name", "data", "fmt"),
    [("r.wav", make_wav(), "wav"), ("r.MP3", MP3, "mp3"), ("r.webm", WEBM, "webm")],
    ids=["wav", "mp3", "webm"],
)
def test_accepts_supported_formats(name: str, data: bytes, fmt: str) -> None:
    """WAV, MP3 et WebM (enregistreur du navigateur) sont acceptés."""
    assert validate_audio(name, data).format == fmt


def test_reads_wav_duration() -> None:
    """La durée d'un WAV est lue (affichage, coût)."""
    assert validate_audio("r.wav", make_wav(seconds=2)).duration_s == pytest.approx(2)
    assert wav_duration(b"pas un wav") is None


@pytest.mark.parametrize(
    ("name", "data", "code"),
    [
        ("r.ogg", make_wav(), "format"),
        ("sans_extension", make_wav(), "format"),
        ("r.wav", b"", "empty"),
        ("r.mp3", make_wav(), "signature"),
        ("r.wav", b"<script>alert(1)</script>" * 4, "signature"),
    ],
    ids=["extension", "sans-extension", "vide", "mp3-deguise", "script-deguise"],
)
def test_rejects_invalid_files(name: str, data: bytes, code: str) -> None:
    """Extension, contenu vide ou signature incohérente sont refusés avec un code précis."""
    with pytest.raises(ValidationError) as error:
        validate_audio(name, data)
    assert error.value.code == code


def test_rejects_too_large_file(settings: object) -> None:
    """Un fichier au-delà de la limite est refusé."""
    settings.AUDIO_MAX_BYTES = 100  # type: ignore[attr-defined]
    with pytest.raises(ValidationError) as error:
        validate_audio("r.wav", make_wav())
    assert error.value.code == "too_large"


def test_rejects_too_long_recording(monkeypatch: pytest.MonkeyPatch) -> None:
    """Un enregistrement de plus de 10 minutes est refusé."""
    monkeypatch.setattr("dreams.audio.wav_duration", lambda data: MAX_DURATION_S + 1)
    with pytest.raises(ValidationError) as error:
        validate_audio("r.wav", make_wav())
    assert error.value.code == "too_long"
