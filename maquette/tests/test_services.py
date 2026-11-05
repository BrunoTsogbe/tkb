"""Tests prototypaux des services simulés de la maquette."""

from __future__ import annotations

import pytest
import requests

import services

WAV = b"RIFF\x24\x00\x00\x00WAVEfmt " + b"\x00" * 32
MP3_ID3 = b"ID3\x04\x00" + b"\x00" * 32
MP3_FRAME = b"\xff\xfb\x90\x00" + b"\x00" * 32


class TestValidateAudio:
    """Validation des fichiers audio."""

    @pytest.mark.parametrize(("name", "data"), [("reve.wav", WAV), ("reve.MP3", MP3_ID3), ("r.mp3", MP3_FRAME)])
    def test_accepts_valid_files(self, name: str, data: bytes) -> None:
        """Un WAV ou un MP3 valide est accepté."""
        services.validate_audio(name, data)

    @pytest.mark.parametrize(
        ("name", "data", "message"),
        [
            ("reve.ogg", WAV, "Format"),
            ("reve.wav", b"", "vide"),
            ("reve.wav", MP3_ID3, "WAV"),
            ("reve.mp3", WAV, "MP3"),
        ],
    )
    def test_rejects_invalid_files(self, name: str, data: bytes, message: str) -> None:
        """Extension, contenu vide ou signature incohérente sont refusés."""
        with pytest.raises(services.AudioValidationError, match=message):
            services.validate_audio(name, data)

    def test_rejects_too_large_file(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Un fichier au-delà de la limite est refusé."""
        monkeypatch.setattr(services, "MAX_AUDIO_BYTES", 10)
        with pytest.raises(services.AudioValidationError, match="25 Mo"):
            services.validate_audio("reve.wav", WAV)


class TestMockTranscribe:
    """Transcription simulée."""

    def test_is_deterministic(self) -> None:
        """Le même audio donne toujours le même texte, issu des exemples."""
        first = services.mock_transcribe(WAV, delay_s=0)
        assert first == services.mock_transcribe(WAV, delay_s=0)
        assert first in services.SAMPLE_TRANSCRIPTS

    def test_simulated_failure_raises(self) -> None:
        """Une panne simulée lève une erreur explicite."""
        with pytest.raises(services.MockAPIError, match="Réessayez"):
            services.mock_transcribe(WAV, delay_s=0, fail=True)


class TestSuggestEmotion:
    """Suggestion d'émotion par mots-clés."""

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("J'avais peur, j'étais poursuivi et en retard", "stressant"),
            ("Quelle JOIE, du soleil et une fête", "heureux"),
            ("Je me sentais seul et je voulais pleurer", "triste"),
            ("Un rêve bizarre, la maison se transforme", "etrange"),
            ("J'achetais du pain", "neutre"),
            ("", "neutre"),
        ],
    )
    def test_keywords(self, text: str, expected: str) -> None:
        """Les mots-clés (accents et majuscules ignorés) orientent l'émotion."""
        assert services.suggest_emotion(text).key == expected

    def test_every_sample_has_an_emotion(self) -> None:
        """Chaque texte d'exemple produit une émotion connue."""
        for text in services.SAMPLE_TRANSCRIPTS:
            assert services.suggest_emotion(text).key in services.EMOTIONS


class TestPlaceholder:
    """Image placeholder et repli local."""

    def test_url_is_stable_and_text_dependent(self) -> None:
        """L'URL dépend du texte et reste la même pour un même texte."""
        url = services.placeholder_url("forêt")
        assert url == services.placeholder_url("forêt")
        assert url != services.placeholder_url("océan")
        assert url.startswith("https://picsum.photos/seed/")

    def test_local_placeholder_is_png(self) -> None:
        """L'image de secours est un PNG valide."""
        assert services.local_placeholder(services.EMOTIONS["heureux"], size=16)[:8] == b"\x89PNG\r\n\x1a\n"

    def test_fetch_uses_remote_image(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Une réponse image valide est utilisée telle quelle."""

        class FakeResponse:
            headers = {"Content-Type": "image/jpeg"}
            content = services.local_placeholder(services.EMOTIONS["heureux"], size=32)

            def raise_for_status(self) -> None:
                """Réponse 200."""

        monkeypatch.setattr(services.requests, "get", lambda *a, **k: FakeResponse())
        image, fallback = services.fetch_placeholder("rêve", services.EMOTIONS["neutre"])
        assert fallback is False
        assert image[1:4] == b"PNG"

    def test_fetch_falls_back_on_corrupt_image(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Une image illisible déclenche aussi le repli local."""

        class FakeResponse:
            headers = {"Content-Type": "image/jpeg"}
            content = b"pas-une-image"

            def raise_for_status(self) -> None:
                """Réponse 200."""

        monkeypatch.setattr(services.requests, "get", lambda *a, **k: FakeResponse())
        assert services.fetch_placeholder("rêve", services.EMOTIONS["neutre"])[1] is True

    def test_fetch_falls_back_on_network_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Un timeout réseau déclenche l'image de secours, sans exception."""

        def boom(*args: object, **kwargs: object) -> None:
            raise requests.Timeout("timeout")

        monkeypatch.setattr(services.requests, "get", boom)
        image, fallback = services.fetch_placeholder("rêve", services.EMOTIONS["neutre"])
        assert fallback is True
        assert image[:4] == b"\x89PNG"

    def test_fetch_falls_back_when_forced(self) -> None:
        """La panne simulée n'appelle pas le réseau et renvoie le secours."""
        _, fallback = services.fetch_placeholder("rêve", services.EMOTIONS["neutre"], fail=True)
        assert fallback is True


class TestCostAndAudio:
    """Durée audio, coût estimé et WAV de démonstration."""

    def test_demo_wav_is_valid_and_timed(self) -> None:
        """Le WAV de démo passe la validation et a la bonne durée."""
        data = services.demo_wav(seconds=0.5, rate=8000)
        services.validate_audio("demo.wav", data)
        assert services.audio_duration_s(data) == 0.5

    def test_duration_unknown_for_mp3(self) -> None:
        """La durée d'un MP3 n'est pas lue (``None``)."""
        assert services.audio_duration_s(MP3_ID3) is None

    def test_cost_matches_benchmark(self) -> None:
        """2 min de STT + 1 image = (2 x 0,0045 + 0,011) $ x 0,92."""
        assert services.estimate_cost_eur(120) == pytest.approx(0.0184)
        assert services.estimate_cost_eur(None) == services.estimate_cost_eur(120)

    def test_scores_are_a_distribution(self) -> None:
        """Les probabilités sont positives et somment à 1."""
        scores = services.emotion_scores("peur et joie")
        assert sum(scores.values()) == pytest.approx(1)
        assert set(scores) == set(services.EMOTIONS)
