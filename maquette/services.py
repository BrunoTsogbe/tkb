"""Services simulés de la maquette « Synthétiseur de rêves ».

Ce module ne dépend pas de Streamlit : il contient la logique testable
(validation audio, transcription fictive, émotions, coût, image
placeholder). En production, ces fonctions seront remplacées par les appels
réels (gpt-transcribe, modèle Hugging Face, GPT Image 1 Mini) derrière la
même interface ; le classifieur par mots-clés servira alors de repli.
"""

from __future__ import annotations

import hashlib
import io
import math
import random
import struct
import time
import unicodedata
import wave
from dataclasses import dataclass

import requests
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

MAX_AUDIO_BYTES = 25 * 1024 * 1024
ALLOWED_EXTENSIONS = (".wav", ".mp3")
PLACEHOLDER_URL = "https://picsum.photos/seed/{seed}/{size}/{size}"
IMAGE_TIMEOUT_S = 10

# Tarifs repris de benchmark.xlsx (scénario retenu).
STT_USD_PER_MIN = 0.0045
IMAGE_USD = 0.011
EUR_PER_USD = 0.92
NEUTRAL_BASELINE = 0.5


class AudioValidationError(ValueError):
    """Fichier audio refusé (format, taille ou contenu)."""


class MockAPIError(RuntimeError):
    """Erreur simulée d'une API externe (timeout, quota, 5xx)."""


@dataclass(frozen=True)
class Emotion:
    """Émotion affichable.

    Attributes:
        key: Identifiant stable (stocké en base en production).
        label: Libellé affiché.
        icon: Emoji associé.
        color: Couleur d'accent (hexadécimal) utilisée par l'interface.
        keywords: Mots indicateurs utilisés par la suggestion simulée.
    """

    key: str
    label: str
    icon: str
    color: str
    keywords: tuple[str, ...]


EMOTIONS: dict[str, Emotion] = {
    e.key: e
    for e in (
        Emotion("heureux", "Heureux", "😊", "#fbbf24", ("joie", "rire", "soleil", "vol", "plage", "fete", "heureux")),
        Emotion(
            "stressant",
            "Stressant",
            "😰",
            "#f43f5e",
            ("peur", "poursuivi", "tomb", "retard", "examen", "perdu", "noir"),
        ),
        Emotion("triste", "Triste", "😢", "#60a5fa", ("pleur", "seul", "adieu", "absent", "triste")),
        Emotion("etrange", "Étrange", "🌀", "#c084fc", ("bizarre", "flott", "transform", "etrange", "parl")),
        Emotion("neutre", "Neutre", "😐", "#94a3b8", ()),
    )
}

SAMPLE_TRANSCRIPTS: tuple[str, ...] = (
    "Je volais au-dessus d'une forêt endormie, le soleil se levait et je riais de joie.",
    "J'étais en retard pour un examen, je courais dans des couloirs sans fin et j'avais peur.",
    "Je marchais dans une ville où les maisons flottaient, un chat me parlait, c'était bizarre.",
    "Je me promenais au marché, j'achetais du pain puis je rentrais chez moi.",
    "Mon grand-père était absent de la maison, je me sentais seul et j'avais envie de pleurer.",
)


def validate_audio(filename: str, data: bytes) -> None:
    """Vérifie qu'un fichier audio est acceptable.

    Args:
        filename: Nom du fichier fourni par l'utilisateur.
        data: Contenu binaire du fichier.

    Raises:
        AudioValidationError: Si l'extension, la taille ou la signature est invalide.
    """
    name = filename.lower()
    if not name.endswith(ALLOWED_EXTENSIONS):
        raise AudioValidationError("Format non pris en charge : utilisez un fichier .wav ou .mp3.")
    if not data:
        raise AudioValidationError("Le fichier est vide.")
    if len(data) > MAX_AUDIO_BYTES:
        raise AudioValidationError("Le fichier dépasse 25 Mo (limite de l'API de transcription).")
    is_wav = data[:4] == b"RIFF" and data[8:12] == b"WAVE"
    is_mp3 = data[:3] == b"ID3" or (len(data) > 1 and data[0] == 0xFF and data[1] & 0xE0 == 0xE0)
    if name.endswith(".wav") and not is_wav:
        raise AudioValidationError("Le contenu ne correspond pas à un fichier WAV.")
    if name.endswith(".mp3") and not is_mp3:
        raise AudioValidationError("Le contenu ne correspond pas à un fichier MP3.")


def demo_wav(seconds: float = 2.0, rate: int = 16000) -> bytes:
    """Génère un court fichier WAV (murmure sinusoïdal) pour la démonstration.

    Args:
        seconds: Durée du son.
        rate: Fréquence d'échantillonnage en Hz.

    Returns:
        Fichier WAV mono 16 bits encodé.
    """
    frames = b"".join(
        struct.pack("<h", int(3000 * math.sin(2 * math.pi * 220 * i / rate) * math.sin(math.pi * i / (seconds * rate))))
        for i in range(int(seconds * rate))
    )
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(frames)
    return buffer.getvalue()


def audio_duration_s(data: bytes) -> float | None:
    """Calcule la durée d'un WAV.

    Args:
        data: Contenu audio.

    Returns:
        Durée en secondes, ou ``None`` si elle ne peut pas être lue (MP3, WAV corrompu).
    """
    try:
        with wave.open(io.BytesIO(data), "rb") as handle:
            return handle.getnframes() / float(handle.getframerate())
    except (wave.Error, EOFError, ZeroDivisionError):
        return None


def estimate_cost_eur(duration_s: float | None) -> float:
    """Estime le coût API d'un rêve (transcription + une image).

    Args:
        duration_s: Durée de l'audio ; 2 minutes par défaut si inconnue.

    Returns:
        Coût estimé en euros.
    """
    minutes = (duration_s if duration_s is not None else 120.0) / 60
    return (minutes * STT_USD_PER_MIN + IMAGE_USD) * EUR_PER_USD


def audio_fingerprint(data: bytes) -> str:
    """Calcule une empreinte stable d'un fichier audio.

    Args:
        data: Contenu binaire.

    Returns:
        Les 12 premiers caractères hexadécimaux du SHA-256.
    """
    return hashlib.sha256(data).hexdigest()[:12]


def mock_transcribe(data: bytes, *, delay_s: float = 1.0, fail: bool = False) -> str:
    """Transcription fictive : renvoie un texte d'exemple déterministe.

    Le même fichier donne toujours le même texte, ce qui rend la démo et les
    tests reproductibles.

    Args:
        data: Contenu audio (déjà validé).
        delay_s: Latence simulée en secondes.
        fail: Si vrai, simule une panne de l'API.

    Returns:
        Le texte « transcrit ».

    Raises:
        MockAPIError: Si ``fail`` est vrai.
    """
    time.sleep(delay_s)
    if fail:
        raise MockAPIError("Le service de transcription ne répond pas (délai dépassé). Réessayez.")
    index = int(audio_fingerprint(data), 16) % len(SAMPLE_TRANSCRIPTS)
    return SAMPLE_TRANSCRIPTS[index]


def _normalize(text: str) -> str:
    """Met en minuscules et retire les accents.

    Args:
        text: Texte brut.

    Returns:
        Texte normalisé.
    """
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def emotion_scores(text: str) -> dict[str, float]:
    """Calcule une distribution de probabilité simulée sur les émotions.

    Chaque mot-clé trouvé ajoute un point ; « neutre » reçoit une base fixe,
    si bien qu'un texte sans indice reste neutre.

    Args:
        text: Texte du rêve.

    Returns:
        Probabilités par clé d'émotion (somme égale à 1).
    """
    normalized = _normalize(text)
    raw = {key: float(sum(normalized.count(k) for k in emo.keywords)) for key, emo in EMOTIONS.items()}
    raw["neutre"] = NEUTRAL_BASELINE
    total = sum(raw.values())
    return {key: value / total for key, value in raw.items()}


def suggest_emotion(text: str) -> Emotion:
    """Suggère l'émotion la plus probable (simulation du modèle).

    Args:
        text: Texte du rêve.

    Returns:
        L'émotion de plus forte probabilité.
    """
    scores = emotion_scores(text)
    return EMOTIONS[max(scores, key=lambda key: scores[key])]


def placeholder_url(text: str, size: int = 512) -> str:
    """Construit l'URL stable d'une image placeholder liée au texte.

    Args:
        text: Texte du rêve (sert de graine).
        size: Côté de l'image en pixels.

    Returns:
        URL Picsum déterministe.
    """
    seed = hashlib.sha256(text.encode("utf-8")).hexdigest()[:10]
    return PLACEHOLDER_URL.format(seed=seed, size=size)


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    """Convertit ``#rrggbb`` en triplet RGB.

    Args:
        color: Couleur hexadécimale.

    Returns:
        Composantes rouge, vert, bleu.
    """
    value = color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def local_placeholder(emotion: Emotion, size: int = 512, seed: str = "") -> bytes:
    """Génère hors ligne un paysage nocturne teinté par l'émotion.

    Sert d'image de secours quand le service d'images ne répond pas.

    Args:
        emotion: Émotion qui détermine la teinte.
        size: Côté de l'image en pixels.
        seed: Graine (texte du rêve) pour varier les étoiles.

    Returns:
        Image PNG encodée.
    """
    rng = random.Random(seed + emotion.key)
    r, g, b = _hex_to_rgb(emotion.color)
    sky = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(sky)
    for y in range(size):
        k = y / size
        draw.line([(0, y), (size, y)], fill=(int(8 + r * 0.45 * k), int(8 + g * 0.35 * k), int(30 + b * 0.5 * k)))

    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow)
    cx, cy, radius = int(size * 0.68), int(size * 0.3), size // 10
    glow_draw.ellipse([cx - radius * 3, cy - radius * 3, cx + radius * 3, cy + radius * 3], fill=(r, g, b, 70))
    glow = glow.filter(ImageFilter.GaussianBlur(size // 12))
    sky.paste(glow, (0, 0), glow)

    draw = ImageDraw.Draw(sky)
    for _ in range(size // 4):
        x, y, s = rng.randrange(size), rng.randrange(int(size * 0.7)), rng.choice((1, 1, 1, 2))
        shade = rng.randint(150, 255)
        draw.ellipse([x, y, x + s, y + s], fill=(shade, shade, 255))
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(250, 246, 230))

    for layer, (height, tint) in enumerate(((0.72, 0.35), (0.82, 0.18))):
        base = int(size * height)
        points = [(0, size)]
        for x in range(0, size + 1, max(1, size // 16)):
            points.append((x, base + int(math.sin(x / size * 6 + layer * 2 + rng.random()) * size * 0.05)))
        points.append((size, size))
        draw.polygon(points, fill=(int(r * tint * 0.4), int(g * tint * 0.4), int(20 + b * tint * 0.5)))

    buffer = io.BytesIO()
    sky.save(buffer, format="PNG")
    return buffer.getvalue()


def dreamify(data: bytes, emotion: Emotion, size: int = 512) -> bytes:
    """Donne à une photo un rendu onirique aux couleurs de l'émotion.

    Recadrage carré, flou lumineux (« glow »), teinte de l'émotion et
    vignettage : la photo aléatoire du placeholder devient une image de rêve.

    Args:
        data: Image source (JPEG ou PNG).
        emotion: Émotion qui donne la teinte.
        size: Côté de l'image produite.

    Returns:
        Image PNG encodée.
    """
    photo = Image.open(io.BytesIO(data)).convert("RGB")
    side = min(photo.size)
    left, top = (photo.width - side) // 2, (photo.height - side) // 2
    photo = photo.crop((left, top, left + side, top + side)).resize((size, size))
    photo = ImageEnhance.Color(photo).enhance(0.6)
    glow = photo.filter(ImageFilter.GaussianBlur(size // 40))
    photo = ImageChops.screen(Image.blend(photo, glow, 0.5), ImageEnhance.Brightness(glow).enhance(0.35))
    tint = Image.new("RGB", (size, size), _hex_to_rgb(emotion.color))
    photo = Image.blend(photo, ImageChops.screen(ImageChops.multiply(photo, tint), tint.point(lambda v: v // 5)), 0.7)
    stars = ImageDraw.Draw(photo)
    rng = random.Random(emotion.key + str(len(data)))
    for _ in range(size // 6):
        x, y = rng.randrange(size), rng.randrange(int(size * 0.55))
        shade = rng.randint(190, 255)
        stars.point((x, y), fill=(shade, shade, 255))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse([-size // 4, -size // 4, size * 5 // 4, size * 5 // 4], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(size // 8))
    photo = Image.composite(photo, Image.new("RGB", (size, size), (7, 7, 24)), mask)
    buffer = io.BytesIO()
    photo.save(buffer, format="PNG")
    return buffer.getvalue()


def fetch_placeholder(text: str, emotion: Emotion, *, fail: bool = False) -> tuple[bytes, bool]:
    """Récupère l'image placeholder, avec repli local en cas d'échec.

    Args:
        text: Texte du rêve.
        emotion: Émotion retenue (pour l'image de secours).
        fail: Si vrai, simule une panne du service d'images.

    Returns:
        Un tuple (octets de l'image, ``True`` si l'image de secours a été utilisée).
    """
    if not fail:
        try:
            resp = requests.get(placeholder_url(text), timeout=IMAGE_TIMEOUT_S)
            resp.raise_for_status()
            if resp.headers.get("Content-Type", "").startswith("image/"):
                return dreamify(resp.content, emotion), False
        except (requests.RequestException, OSError):
            pass
    return local_placeholder(emotion, seed=text), True
