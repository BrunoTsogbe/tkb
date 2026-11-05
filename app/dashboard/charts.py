"""Graphiques SVG rendus côté serveur (aucune bibliothèque JavaScript).

Chaque graphique porte un titre accessible ; les mêmes données sont proposées
sous forme de tableau dans la page (alternative WCAG).
"""

from __future__ import annotations

import math
from html import escape

from django.utils.safestring import SafeString, mark_safe

from .services import Bucket, Share


def donut(shares: list[Share], size: int = 220) -> SafeString:
    """Anneau de répartition des émotions.

    Args:
        shares: Répartition par émotion.
        size: Côté du dessin.

    Returns:
        Balise ``<svg>`` prête à insérer.
    """
    radius, stroke = size * 0.34, size * 0.14
    circumference = 2 * math.pi * radius
    center = size / 2
    parts = [
        f'<circle cx="{center}" cy="{center}" r="{radius:.1f}" fill="none" stroke="rgba(255,255,255,.08)" '
        f'stroke-width="{stroke:.1f}"/>'
    ]
    offset = 0.0
    for share in shares:
        if not share.count:
            continue
        length = share.ratio * circumference
        parts.append(
            f'<circle cx="{center}" cy="{center}" r="{radius:.1f}" fill="none" stroke="{escape(share.emotion.color)}" '
            f'stroke-width="{stroke:.1f}" stroke-dasharray="{length:.2f} {circumference - length:.2f}" '
            f'stroke-dashoffset="{-offset:.2f}" transform="rotate(-90 {center} {center})">'
            f"<title>{escape(share.emotion.label)} : {share.count}</title></circle>"
        )
        offset += length
    total = sum(s.count for s in shares)
    parts.append(
        f'<text x="{center}" y="{center + 8}" text-anchor="middle" font-size="26" font-weight="700" '
        f'fill="currentColor">{total}</text>'
    )
    title = ", ".join(f"{s.emotion.label} {round(s.ratio * 100)} %" for s in shares if s.count) or "Aucun rêve"
    return mark_safe(  # noqa: S308 — contenu entièrement échappé ci-dessus
        f'<svg viewBox="0 0 {size} {size}" role="img" class="chart-donut"><title>Répartition : {escape(title)}</title>'
        + "".join(parts)
        + "</svg>"
    )


def stacked_bars(timeline: list[Bucket], shares: list[Share], width: int = 560, height: int = 220) -> SafeString:
    """Barres empilées par émotion, dans le temps.

    Args:
        timeline: Intervalles (jours ou semaines).
        shares: Émotions, dans l'ordre d'empilement et avec leurs couleurs.
        width: Largeur du dessin.
        height: Hauteur du dessin.

    Returns:
        Balise ``<svg>`` prête à insérer.
    """
    top, bottom, left = 10, 24, 22
    plot_h = height - top - bottom
    highest = max((b.total for b in timeline), default=0) or 1
    slot = (width - left) / max(len(timeline), 1)
    bar_w = max(min(slot * 0.7, 28), 2)
    parts = [f'<line x1="{left}" y1="{top + plot_h}" x2="{width}" y2="{top + plot_h}" stroke="rgba(255,255,255,.2)"/>']
    parts.append(f'<text x="0" y="{top + 8}" font-size="10" fill="currentColor">{highest}</text>')
    label_every = max(1, math.ceil(len(timeline) / 10))
    for index, bucket in enumerate(timeline):
        x = left + index * slot + (slot - bar_w) / 2
        y: float = top + plot_h
        for share in shares:
            count = bucket.counts.get(share.emotion.key, 0)
            if not count:
                continue
            h = count / highest * plot_h
            y -= h
            parts.append(
                f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w:.1f}" height="{h:.1f}" rx="2" '
                f'fill="{escape(share.emotion.color)}"><title>{escape(bucket.label)} · '
                f"{escape(share.emotion.label)} : {count}</title></rect>"
            )
        if index % label_every == 0:
            parts.append(
                f'<text x="{x + bar_w / 2:.1f}" y="{height - 6}" font-size="10" text-anchor="middle" '
                f'fill="currentColor">{escape(bucket.label)}</text>'
            )
    return mark_safe(  # noqa: S308 — contenu entièrement échappé ci-dessus
        f'<svg viewBox="0 0 {width} {height}" role="img" class="chart-bars">'
        f"<title>Évolution des émotions dans le temps</title>" + "".join(parts) + "</svg>"
    )
