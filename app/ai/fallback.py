"""Image de secours générée localement (refus de contenu, budget, mode démo).

Paysage nocturne teinté par l'émotion, repris de la maquette : aucune donnée
n'est envoyée et aucun coût n'est engagé.
"""

from __future__ import annotations

import io
import math
import random

from PIL import Image, ImageDraw, ImageFilter


def _rgb(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def render_fallback(seed: str, color: str = "#a78bfa", size: int = 768) -> bytes:
    """Dessine un ciel nocturne avec lune, étoiles et collines.

    Args:
        seed: Graine (identifiant du rêve) pour varier le dessin.
        color: Couleur de l'émotion (``#rrggbb``).
        size: Côté de l'image en pixels.

    Returns:
        Image PNG encodée.
    """
    rng = random.Random(seed)
    r, g, b = _rgb(color)
    sky = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(sky)
    for y in range(size):
        k = y / size
        draw.line([(0, y), (size, y)], fill=(int(8 + r * 0.45 * k), int(8 + g * 0.35 * k), int(30 + b * 0.5 * k)))
    cx, cy, radius = int(size * (0.25 + rng.random() * 0.5)), int(size * 0.28), size // 11
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse(
        [cx - radius * 3, cy - radius * 3, cx + radius * 3, cy + radius * 3], fill=(r, g, b, 70)
    )
    glow = glow.filter(ImageFilter.GaussianBlur(size // 12))
    sky.paste(glow, (0, 0), glow)
    draw = ImageDraw.Draw(sky)
    for _ in range(size // 4):
        x, y, s = rng.randrange(size), rng.randrange(int(size * 0.7)), rng.choice((1, 1, 2))
        shade = rng.randint(150, 255)
        draw.ellipse([x, y, x + s, y + s], fill=(shade, shade, 255))
    draw.ellipse([cx - radius, cy - radius, cx + radius, cy + radius], fill=(250, 246, 230))
    for layer, (height, tint) in enumerate(((0.72, 0.35), (0.83, 0.18))):
        base = int(size * height)
        points = [(0, size)] + [
            (x, base + int(math.sin(x / size * 6 + layer * 2 + rng.random()) * size * 0.05))
            for x in range(0, size + 1, size // 16)
        ]
        points.append((size, size))
        draw.polygon(points, fill=(int(r * tint * 0.4), int(g * tint * 0.4), int(20 + b * tint * 0.5)))
    buffer = io.BytesIO()
    sky.save(buffer, format="PNG")
    return buffer.getvalue()
