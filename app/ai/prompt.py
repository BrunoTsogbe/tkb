"""Construction du prompt d'image, minimisé (RGPD, dossier de cadrage §5).

Les noms propres et les coordonnées sont retirés : le prompt décrit la scène,
pas les personnes.
"""

from __future__ import annotations

import re

MAX_SCENE_CHARS = 700
EMAIL = re.compile(r"\S+@\S+")
NUMBERS = re.compile(r"\+?\d[\d .-]{5,}\d")
WORD = re.compile(r"\b[^\W\d_][\w'-]*", re.UNICODE)
SENTENCE_END = re.compile(r"[.!?…]\s*$")
STYLE = (
    "Illustration onirique et poétique, style aquarelle numérique, lumière douce, "
    "sans texte, sans visage reconnaissable ni personne réelle."
)


def strip_identifiers(text: str) -> str:
    """Retire e-mails, numéros et noms propres (mots en capitale hors début de phrase).

    Args:
        text: Texte du rêve.

    Returns:
        Texte minimisé.
    """
    text = NUMBERS.sub("", EMAIL.sub("", text))
    kept: list[str] = []
    cursor = 0
    sentence_start = True
    for match in WORD.finditer(text):
        word = match.group(0)
        before = text[cursor : match.start()]
        if SENTENCE_END.search(before) or not kept and not before.strip():
            sentence_start = True
        if word[0].isupper() and not sentence_start:
            replacement = "quelqu'un"
        else:
            replacement = word
        kept.append(before + replacement)
        cursor = match.end()
        sentence_start = False
    kept.append(text[cursor:])
    return re.sub(r"\s{2,}", " ", "".join(kept)).strip()


def build_image_prompt(text: str, emotion_label: str) -> str:
    """Construit le prompt envoyé au générateur d'images.

    Args:
        text: Transcription (éventuellement corrigée) du rêve.
        emotion_label: Ambiance retenue.

    Returns:
        Prompt minimisé et tronqué.
    """
    scene = strip_identifiers(text)[:MAX_SCENE_CHARS]
    return f"{STYLE} Ambiance : {emotion_label.lower()}. Scène du rêve : {scene}"
