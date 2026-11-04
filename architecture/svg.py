"""Petite bibliothèque de dessin SVG pour les diagrammes d'architecture.

Les diagrammes (C4, ERD, séquence, pipeline) sont générés en code pour rester
versionnables, relisibles en revue de code et cohérents entre eux.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from html import escape

FONT = "Inter, 'Segoe UI', Arial, sans-serif"

PALETTE = {
    "person": ("#1e3a8a", "#ffffff"),
    "system": ("#6d28d9", "#ffffff"),
    "container": ("#7c3aed", "#ffffff"),
    "external": ("#64748b", "#ffffff"),
    "db": ("#0e7490", "#ffffff"),
    "ci": ("#f1f5f9", "#0f172a"),
}
LINE = "#475569"


@dataclass(frozen=True)
class Rect:
    """Rectangle (coordonnées SVG).

    Attributes:
        x: Abscisse du coin supérieur gauche.
        y: Ordonnée du coin supérieur gauche.
        w: Largeur.
        h: Hauteur.
    """

    x: float
    y: float
    w: float
    h: float

    @property
    def center(self) -> tuple[float, float]:
        """Centre du rectangle."""
        return self.x + self.w / 2, self.y + self.h / 2

    def border_toward(self, tx: float, ty: float) -> tuple[float, float]:
        """Point du bord situé sur la droite centre → (tx, ty).

        Args:
            tx: Abscisse visée.
            ty: Ordonnée visée.

        Returns:
            Coordonnées du point d'intersection avec le bord.
        """
        cx, cy = self.center
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return cx, cy
        sx = (self.w / 2) / abs(dx) if dx else math.inf
        sy = (self.h / 2) / abs(dy) if dy else math.inf
        s = min(sx, sy)
        return cx + dx * s, cy + dy * s


def defs() -> str:
    """Définitions communes (pointes de flèches, ombres).

    Returns:
        Bloc ``<defs>``.
    """
    return (
        "<defs>"
        '<marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        'orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{LINE}"/></marker>'
        '<filter id="sh" x="-10%" y="-10%" width="120%" height="130%">'
        '<feDropShadow dx="0" dy="2" stdDeviation="2.5" flood-color="#0f172a" flood-opacity=".18"/></filter>'
        "</defs>"
    )


def svg(width: int, height: int, body: str, title: str) -> str:
    """Enveloppe un dessin dans une balise ``<svg>`` autonome.

    Args:
        width: Largeur du viewBox.
        height: Hauteur du viewBox.
        body: Contenu SVG.
        title: Titre accessible du diagramme.

    Returns:
        Document SVG.
    """
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img" '
        f'font-family="{FONT}"><title>{escape(title)}</title>{defs()}{body}</svg>'
    )


def text(
    x: float,
    y: float,
    lines: list[str] | str,
    size: float = 12,
    weight: int = 400,
    fill: str = "#0f172a",
    anchor: str = "middle",
    italic: bool = False,
) -> str:
    """Écrit un texte multiligne centré verticalement sur ``y``.

    Args:
        x: Abscisse d'ancrage.
        y: Ordonnée du centre du bloc.
        lines: Ligne ou liste de lignes.
        size: Taille de police.
        weight: Graisse.
        fill: Couleur.
        anchor: Ancrage horizontal SVG.
        italic: Style italique.

    Returns:
        Élément ``<text>``.
    """
    lines = [lines] if isinstance(lines, str) else lines
    lh = size * 1.25
    start = y - (len(lines) - 1) * lh / 2 + size * 0.35
    style = ' font-style="italic"' if italic else ""
    spans = "".join(
        f'<tspan x="{x:.1f}" y="{start + i * lh:.1f}">{escape(line)}</tspan>' for i, line in enumerate(lines)
    )
    return f'<text font-size="{size}" font-weight="{weight}" fill="{fill}" text-anchor="{anchor}"{style}>{spans}</text>'


def node(r: Rect, title: str, kind: str, tech: str = "", desc: list[str] | None = None) -> str:
    """Dessine un élément C4 (personne, système, conteneur, base).

    Args:
        r: Position et taille.
        title: Nom de l'élément.
        kind: Clé de ``PALETTE``.
        tech: Technologie (affichée entre crochets).
        desc: Lignes de description.

    Returns:
        Fragment SVG.
    """
    fill, ink = PALETTE[kind]
    desc = desc or []
    parts = []
    if kind == "db":
        e = 9
        parts.append(
            f'<path d="M{r.x},{r.y + e} L{r.x},{r.y + r.h - e} A{r.w / 2},{e} 0 0 0 {r.x + r.w},{r.y + r.h - e} '
            f'L{r.x + r.w},{r.y + e} A{r.w / 2},{e} 0 0 0 {r.x},{r.y + e} z" fill="{fill}" filter="url(#sh)"/>'
            f'<ellipse cx="{r.x + r.w / 2}" cy="{r.y + e}" rx="{r.w / 2}" ry="{e}" fill="#22a3bf"/>'
        )
    else:
        parts.append(
            f'<rect x="{r.x}" y="{r.y}" width="{r.w}" height="{r.h}" rx="10" fill="{fill}" filter="url(#sh)"/>'
        )
    if kind == "person":
        cx = r.x + r.w / 2
        parts.append(f'<circle cx="{cx}" cy="{r.y - 2}" r="15" fill="{fill}" stroke="#fff" stroke-width="2.5"/>')
    lines: list[tuple[str, float, int, bool]] = [(title, 13, 700, False)]
    if tech:
        lines.append((f"[{tech}]", 10, 400, True))
    lines += [(d, 10.5, 400, False) for d in desc]
    total = sum(s * 1.3 for _, s, _, _ in lines)
    y = r.y + r.h / 2 - total / 2 + (6 if kind == "db" else 0) + (4 if kind == "person" else 0)
    for content, size, weight, italic in lines:
        parts.append(text(r.x + r.w / 2, y + size * 0.65, content, size, weight, ink, italic=italic))
        y += size * 1.3
    return "".join(parts)


def label(x: float, y: float, lines: list[str] | str, size: float = 10) -> str:
    """Étiquette de flèche sur fond blanc.

    Args:
        x: Centre horizontal.
        y: Centre vertical.
        lines: Ligne ou liste de lignes.
        size: Taille de police.

    Returns:
        Fragment SVG.
    """
    lines = [lines] if isinstance(lines, str) else lines
    w = max(len(line) for line in lines) * size * 0.57 + 12
    h = len(lines) * size * 1.25 + 6
    return (
        f'<rect x="{x - w / 2:.1f}" y="{y - h / 2:.1f}" width="{w:.1f}" height="{h:.1f}" rx="4" fill="#fff" '
        f'fill-opacity=".94"/>' + text(x, y, lines, size, 400, "#334155")
    )


def link(
    a: Rect, b: Rect, lines: list[str] | str = "", t: float = 0.5, dx: float = 0, dy: float = 0, dashed: bool = False
) -> str:
    """Flèche droite de ``a`` vers ``b`` avec étiquette optionnelle.

    Args:
        a: Élément source.
        b: Élément cible.
        lines: Étiquette.
        t: Position de l'étiquette le long de la flèche (0 à 1).
        dx: Décalage horizontal de l'étiquette.
        dy: Décalage vertical de l'étiquette.
        dashed: Trait pointillé.

    Returns:
        Fragment SVG.
    """
    ax, ay = a.border_toward(*b.center)
    bx, by = b.border_toward(*a.center)
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    out = (
        f'<line x1="{ax:.1f}" y1="{ay:.1f}" x2="{bx:.1f}" y2="{by:.1f}" stroke="{LINE}" stroke-width="1.4"'
        f'{dash} marker-end="url(#arr)"/>'
    )
    if lines:
        out += label(ax + (bx - ax) * t + dx, ay + (by - ay) * t + dy, lines)
    return out


def polyline(points: list[tuple[float, float]], dashed: bool = False) -> str:
    """Flèche brisée passant par ``points``.

    Args:
        points: Sommets successifs.
        dashed: Trait pointillé.

    Returns:
        Fragment SVG.
    """
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    return f'<polyline points="{pts}" fill="none" stroke="{LINE}" stroke-width="1.4"{dash} marker-end="url(#arr)"/>'


def boundary(r: Rect, title: str) -> str:
    """Cadre pointillé d'un système (frontière C4).

    Args:
        r: Position et taille.
        title: Libellé de la frontière.

    Returns:
        Fragment SVG.
    """
    return (
        f'<rect x="{r.x}" y="{r.y}" width="{r.w}" height="{r.h}" rx="14" fill="#f5f3ff" stroke="#6d28d9" '
        f'stroke-width="1.6" stroke-dasharray="8 5"/>'
        + text(r.x + 14, r.y + r.h - 14, title, 12, 700, "#6d28d9", anchor="start")
    )


def entity(x: float, y: float, w: float, name: str, rows: list[tuple[str, str, str]], note: str = "") -> str:
    """Table d'un diagramme entité-association.

    Args:
        x: Abscisse.
        y: Ordonnée.
        w: Largeur.
        name: Nom de l'entité.
        rows: Lignes (clé, attribut, type) ; clé parmi ``PK``, ``FK``, ``UQ`` ou vide.
        note: Sous-titre facultatif.

    Returns:
        Fragment SVG.
    """
    head = 28
    row = 17
    h = head + row * len(rows) + 6
    parts = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="#fff" stroke="#c4b5fd" filter="url(#sh)"/>',
        f'<path d="M{x},{y + 9} a9,9 0 0 1 9,-9 h{w - 18} a9,9 0 0 1 9,9 v{head - 9} h-{w} z" fill="#6d28d9"/>',
        text(x + 12, y + head / 2, name, 13, 700, "#fff", anchor="start"),
    ]
    if note:
        parts.append(text(x + w - 10, y + head / 2, note, 9.5, 400, "#ede9fe", anchor="end", italic=True))
    colors = {"PK": "#b45309", "FK": "#0e7490", "UQ": "#6d28d9", "PK FK": "#b45309"}
    for i, (key, attr, typ) in enumerate(rows):
        cy = y + head + 3 + row * i + row / 2
        if i % 2:
            parts.append(f'<rect x="{x + 1}" y="{cy - row / 2}" width="{w - 2}" height="{row}" fill="#faf5ff"/>')
        if key:
            parts.append(text(x + 10, cy, key, 8.5, 700, colors.get(key, "#334155"), anchor="start"))
        parts.append(text(x + 42, cy, attr, 10.5, 600 if key == "PK" else 400, "#0f172a", anchor="start"))
        parts.append(text(x + w - 10, cy, typ, 9.5, 400, "#64748b", anchor="end"))
    return "".join(parts)


def entity_height(rows: int) -> float:
    """Hauteur d'une table d'ERD.

    Args:
        rows: Nombre d'attributs.

    Returns:
        Hauteur en unités SVG.
    """
    return 28 + 17 * rows + 6
