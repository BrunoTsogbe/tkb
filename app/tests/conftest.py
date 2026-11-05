"""Fixtures partagées : fabriques, fichiers audio de test, clients connectés."""

from __future__ import annotations

import io
import math
import struct
import wave
from collections.abc import Callable

import factory
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

from accounts.models import User

PASSWORD = "un-mot-de-passe-solide-42"


class UserFactory(factory.django.DjangoModelFactory):
    """Utilisateur de test (consentement donné par défaut)."""

    class Meta:
        model = User
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f"reveur{n}@exemple.fr")
    password = factory.PostGenerationMethodCall("set_password", PASSWORD)

    @factory.post_generation
    def consent(self, create: bool, extracted: bool | None, **kwargs: object) -> None:
        """Donne le consentement IA sauf si ``consent=False``."""
        self.save()
        if create and extracted is not False:
            self.profile.give_consent()


def make_wav(seconds: float = 1.0, rate: int = 8000) -> bytes:
    """Fabrique un WAV mono 16 bits.

    Args:
        seconds: Durée.
        rate: Fréquence d'échantillonnage.

    Returns:
        Contenu du fichier.
    """
    frames = b"".join(struct.pack("<h", int(2000 * math.sin(i / 8))) for i in range(int(seconds * rate)))
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return buffer.getvalue()


WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 64
MP3 = b"ID3\x04\x00" + b"\x00" * 64


@pytest.fixture(autouse=True)
def media_root(settings: object, tmp_path: object) -> None:
    """Isole les fichiers déposés dans un dossier temporaire."""
    settings.MEDIA_ROOT = tmp_path  # type: ignore[attr-defined]


@pytest.fixture
def user(db: None) -> User:
    """Utilisateur consentant."""
    return UserFactory()


@pytest.fixture
def client_logged(user: User) -> Client:
    """Client HTTP connecté avec ``user``."""
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def audio_file() -> Callable[..., SimpleUploadedFile]:
    """Fabrique de fichiers audio à déposer."""

    def build(name: str = "reve.wav", content: bytes | None = None) -> SimpleUploadedFile:
        return SimpleUploadedFile(name, make_wav() if content is None else content, content_type="audio/wav")

    return build
