"""Wireframes basse fidélité et parcours utilisateur de l'application de production.

Les écrans sont dessinés en niveaux de gris (basse fidélité) : ils fixent la
structure, la hiérarchie et les états, pas le style. Les pastilles numérotées
renvoient aux annotations du document.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "architecture"))

from svg import Rect, label, link, svg, text  # noqa: E402

INK = "#334155"
LINE = "#94a3b8"
FILL = "#f1f5f9"
SOFT = "#e2e8f0"
NOTE = "#e11d48"


def box(
    x: float, y: float, w: float, h: float, fill: str = "#fff", stroke: str = LINE, rx: float = 6, dashed: bool = False
) -> str:
    """Rectangle de wireframe.

    Args:
        x: Abscisse.
        y: Ordonnée.
        w: Largeur.
        h: Hauteur.
        fill: Remplissage.
        stroke: Couleur du contour.
        rx: Rayon des coins.
        dashed: Contour pointillé.

    Returns:
        Fragment SVG.
    """
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="1.3"{dash}/>'
    )


def bars(x: float, y: float, w: float, count: int = 3, gap: float = 11, height: float = 6) -> str:
    """Lignes de texte simulées (barres grises).

    Args:
        x: Abscisse.
        y: Ordonnée de la première ligne.
        w: Largeur maximale.
        count: Nombre de lignes.
        gap: Interligne.
        height: Épaisseur d'une ligne.

    Returns:
        Fragment SVG.
    """
    widths = (1.0, 0.92, 0.78, 0.85, 0.6)
    return "".join(
        f'<rect x="{x}" y="{y + i * gap}" width="{w * widths[i % len(widths)]:.0f}" height="{height}" rx="3" '
        f'fill="{SOFT}"/>'
        for i in range(count)
    )


def words(
    x: float, y: float, content: str, size: float = 11, weight: int = 400, anchor: str = "start", fill: str = INK
) -> str:
    """Texte réel (titres, libellés de boutons).

    Args:
        x: Abscisse.
        y: Ordonnée (centre de la ligne).
        content: Texte.
        size: Taille.
        weight: Graisse.
        anchor: Ancrage horizontal.
        fill: Couleur.

    Returns:
        Fragment SVG.
    """
    return text(x, y, content, size, weight, fill, anchor=anchor)


def button(x: float, y: float, w: float, h: float, content: str, primary: bool = False) -> str:
    """Bouton.

    Args:
        x: Abscisse.
        y: Ordonnée.
        w: Largeur.
        h: Hauteur.
        content: Libellé.
        primary: Bouton principal (rempli).

    Returns:
        Fragment SVG.
    """
    fill, ink = ("#475569", "#fff") if primary else ("#fff", INK)
    return box(x, y, w, h, fill, "#475569", rx=h / 2) + words(x + w / 2, y + h / 2, content, 10.5, 600, "middle", ink)


def field(x: float, y: float, w: float, name: str, h: float = 26) -> str:
    """Champ de formulaire avec libellé.

    Args:
        x: Abscisse.
        y: Ordonnée du libellé.
        w: Largeur.
        name: Libellé.
        h: Hauteur du champ.

    Returns:
        Fragment SVG.
    """
    return words(x, y, name, 9.5, 600) + box(x, y + 8, w, h, "#fff", LINE, 5)


def picture(x: float, y: float, w: float, h: float) -> str:
    """Emplacement d'image (rectangle barré).

    Args:
        x: Abscisse.
        y: Ordonnée.
        w: Largeur.
        h: Hauteur.

    Returns:
        Fragment SVG.
    """
    return (
        box(x, y, w, h, FILL, LINE, 8)
        + f'<path d="M{x},{y} L{x + w},{y + h} M{x + w},{y} L{x},{y + h}" stroke="{SOFT}" stroke-width="1.3"/>'
    )


def chip(x: float, y: float, content: str, active: bool = False) -> str:
    """Pastille de filtre ou d'émotion.

    Args:
        x: Abscisse.
        y: Ordonnée.
        content: Libellé.
        active: Pastille sélectionnée.

    Returns:
        Fragment SVG.
    """
    w = len(content) * 6 + 18
    fill = "#cbd5e1" if active else "#fff"
    return box(x, y, w, 20, fill, LINE, 10) + words(x + w / 2, y + 10, content, 9, 600, "middle")


def note(x: float, y: float, number: int) -> str:
    """Pastille d'annotation numérotée.

    Args:
        x: Centre horizontal.
        y: Centre vertical.
        number: Numéro.

    Returns:
        Fragment SVG.
    """
    return f'<circle cx="{x}" cy="{y}" r="9" fill="{NOTE}"/>' + words(x, y, str(number), 10, 700, "middle", "#fff")


def browser(title: str, body: str, nav: str = "Raconter", w: int = 820, h: int = 500) -> str:
    """Cadre de navigateur avec barre de navigation de l'application.

    Args:
        title: Nom de l'écran (barre d'adresse).
        body: Contenu de la page.
        nav: Onglet actif.
        w: Largeur.
        h: Hauteur.

    Returns:
        Document SVG.
    """
    tabs = ["Raconter", "Historique", "Tableau de bord", "Compte"]
    parts = [
        box(1, 1, w - 2, h - 2, "#fff", "#64748b", 10),
        f'<path d="M1,11 a10,10 0 0 1 10,-10 h{w - 22} a10,10 0 0 1 10,10 v17 h-{w - 2} z" fill="{FILL}"/>',
        *(f'<circle cx="{16 + i * 13}" cy="14" r="4" fill="{LINE}"/>' for i in range(3)),
        box(70, 6, 360, 16, "#fff", SOFT, 8),
        words(80, 14, title, 8.5, 400, "start", "#64748b"),
        f'<line x1="1" y1="28" x2="{w - 1}" y2="28" stroke="{SOFT}"/>',
        f'<circle cx="30" cy="50" r="9" fill="{SOFT}"/>',
        words(46, 50, "Synthétiseur de rêves", 11, 700),
    ]
    x = w - 380
    for tab in tabs:
        parts.append(words(x, 50, tab, 10, 700 if tab == nav else 400, "start", INK if tab == nav else "#64748b"))
        if tab == nav:
            parts.append(f'<line x1="{x}" y1="60" x2="{x + len(tab) * 5.6}" y2="60" stroke="{INK}" stroke-width="2"/>')
        x += len(tab) * 5.6 + 26
    parts.append(f'<circle cx="{w - 26}" cy="50" r="10" fill="{SOFT}"/>')
    parts.append(f'<line x1="1" y1="72" x2="{w - 1}" y2="72" stroke="{SOFT}"/>')
    return svg(w, h, "".join(parts) + body, f"Wireframe : {title}")


def phone(title: str, body: str, w: int = 250, h: int = 500) -> str:
    """Cadre de smartphone.

    Args:
        title: Nom de l'écran.
        body: Contenu.
        w: Largeur.
        h: Hauteur.

    Returns:
        Document SVG.
    """
    frame = (
        box(1, 1, w - 2, h - 2, "#fff", "#64748b", 26)
        + box(w / 2 - 32, 10, 64, 12, FILL, FILL, 6)
        + f'<line x1="1" y1="62" x2="{w - 1}" y2="62" stroke="{SOFT}"/>'
        + words(20, 44, "☰", 14)
        + words(w / 2, 44, "Synthétiseur de rêves", 10.5, 700, "middle")
        + f'<circle cx="{w - 26}" cy="44" r="9" fill="{SOFT}"/>'
    )
    return svg(w, h, frame + body, f"Wireframe mobile : {title}")


# ---------------------------------------------------------------- écrans


def signup() -> str:
    """Écran 1 : inscription avec consentement.

    Returns:
        Document SVG.
    """
    x, y, w = 270, 95, 280
    body = "".join(
        [
            box(x - 30, y - 10, w + 60, 385, "#fff", LINE, 12),
            words(410, y + 16, "Créer mon compte", 16, 700, "middle"),
            bars(x + 30, y + 34, 220, 1),
            field(x, y + 62, w, "Adresse e-mail"),
            field(x, y + 110, w, "Mot de passe"),
            words(x, y + 152, "12 caractères minimum · indicateur de robustesse", 8.5, 400, "start", "#64748b"),
            box(x, y + 168, 14, 14, "#fff", INK, 3),
            words(x + 22, y + 175, "J'accepte que ma voix et mes rêves soient envoyés à", 9.5),
            words(x + 22, y + 189, "des prestataires d'IA (OpenAI, hors UE). En savoir plus", 9.5),
            box(x, y + 208, 14, 14, "#fff", INK, 3),
            words(x + 22, y + 215, "J'accepte les conditions et la politique de confidentialité", 9.5),
            button(x, y + 240, w, 32, "Créer mon compte", primary=True),
            words(410, y + 292, "Déjà un compte ? Se connecter", 10, 600, "middle"),
            box(x, y + 312, w, 44, "#fff", NOTE, 6, dashed=True),
            words(x + 10, y + 326, "État d'erreur : message sous le champ concerné,", 9, 400, "start", NOTE),
            words(x + 10, y + 342, "saisie conservée, focus placé sur le premier champ fautif.", 9, 400, "start", NOTE),
            note(x - 14, y + 175, 1),
            note(x + w + 16, y + 117, 2),
            note(x + w + 16, y + 334, 3),
        ]
    )
    return browser("/accounts/signup/", body, nav="Compte")


def record() -> str:
    """Écran 2 : raconter un rêve.

    Returns:
        Document SVG.
    """
    body = "".join(
        [
            words(410, 108, "Racontez votre rêve", 20, 700, "middle"),
            words(410, 132, "Parlez librement, l'application s'occupe du reste.", 10.5, 400, "middle", "#64748b"),
            f'<circle cx="410" cy="215" r="52" fill="{FILL}" stroke="#475569" stroke-width="2"/>',
            '<rect x="401" y="190" width="18" height="32" rx="9" fill="#475569"/>',
            '<path d="M392,214 a18,18 0 0 0 36,0 M410,232 v10" stroke="#475569" stroke-width="2.5" fill="none"/>',
            words(410, 290, "00:42  ·  Appuyez pour terminer", 11, 600, "middle"),
            "".join(
                f'<rect x="{300 + i * 9}" y="{318 - (i * 7 % 18)}" width="5" height="{8 + (i * 7 % 18) * 2}" '
                f'rx="2" fill="{SOFT}"/>'
                for i in range(25)
            ),
            words(410, 368, "ou", 10, 400, "middle", "#64748b"),
            box(270, 382, 280, 56, "#fff", LINE, 10, dashed=True),
            words(410, 404, "Déposer un fichier .wav / .mp3", 10.5, 600, "middle"),
            words(410, 422, "25 Mo · 10 minutes maximum", 9, 400, "middle", "#64748b"),
            chip(640, 90, "3 / 5 rêves aujourd'hui"),
            box(40, 445, 210, 40, FILL, LINE, 8),
            words(50, 460, "Micro bloqué ? Autorisez-le dans", 9),
            words(50, 474, "votre navigateur ou importez un fichier.", 9),
            note(476, 170, 1),
            note(560, 410, 2),
            note(630, 100, 3),
            note(262, 465, 4),
        ]
    )
    return browser("/  (Raconter)", body)


def progress() -> str:
    """Écran 3 : suivi du traitement (normal et en échec).

    Returns:
        Document SVG.
    """
    steps = ["Reçu", "Transcription", "Ambiance", "Image"]
    parts = [words(410, 105, "Votre rêve prend forme…", 17, 700, "middle")]
    for i, step in enumerate(steps):
        cx = 250 + i * 107
        state = "done" if i < 2 else "current" if i == 2 else "todo"
        fill = "#475569" if state == "done" else "#fff"
        parts.append(f'<circle cx="{cx}" cy="150" r="13" fill="{fill}" stroke="#475569" stroke-width="2"/>')
        if state == "done":
            parts.append(words(cx, 150, "✓", 12, 700, "middle", "#fff"))
        if state == "current":
            parts.append(f'<circle cx="{cx}" cy="150" r="5" fill="#475569"/>')
        parts.append(words(cx, 178, step, 9.5, 700 if state == "current" else 400, "middle"))
        if i < 3:
            parts.append(f'<line x1="{cx + 15}" y1="150" x2="{cx + 92}" y2="150" stroke="{LINE}" stroke-width="2"/>')
    parts += [
        box(220, 200, 380, 90, FILL, LINE, 10),
        words(235, 218, "Transcription", 9.5, 700),
        bars(235, 230, 345, 4),
        words(
            410,
            310,
            "Environ 20 secondes. Vous pouvez quitter la page : votre rêve est conservé.",
            9.5,
            400,
            "middle",
            "#64748b",
        ),
        box(220, 340, 380, 120, "#fff", NOTE, 10, dashed=True),
        words(235, 360, "État « échec »", 10, 700, "start", NOTE),
        words(235, 380, "La transcription n'a pas abouti (service indisponible).", 10),
        words(235, 396, "Votre enregistrement est conservé.", 10),
        button(235, 415, 120, 28, "Réessayer", primary=True),
        button(365, 415, 150, 28, "Revenir à l'accueil"),
        note(206, 150, 1),
        note(610, 245, 2),
        note(610, 400, 3),
    ]
    return browser("/dreams/6f1c…/", "".join(parts))


def result() -> str:
    """Écran 4 : résultat d'un rêve.

    Returns:
        Document SVG.
    """
    body = "".join(
        [
            words(40, 98, "Mardi 4 novembre · 07:12", 10, 400, "start", "#64748b"),
            picture(40, 112, 330, 330),
            words(40, 458, "Image générée par IA", 9, 600, "start", "#64748b"),
            box(400, 112, 140, 28, "#cbd5e1", LINE, 14),
            words(470, 126, "😊 Heureux", 11, 700, "middle"),
            *(
                words(400, 162 + i * 17, name, 9)
                + box(470, 157 + i * 17, 230, 7, FILL, FILL, 3)
                + box(470, 157 + i * 17, 230 * share, 7, "#94a3b8", "#94a3b8", 3)
                for i, (name, share) in enumerate(
                    [("Heureux", 0.82), ("Neutre", 0.1), ("Étrange", 0.05), ("Stressant", 0.02), ("Triste", 0.01)]
                )
            ),
            words(400, 258, "Transcription · modifiable", 9.5, 700),
            box(400, 266, 380, 84, "#fff", LINE, 6),
            bars(412, 278, 350, 5),
            words(400, 366, "Ce n'est pas ça ? Corriger l'ambiance", 9.5, 700),
            box(400, 374, 220, 26, "#fff", LINE, 5),
            words(410, 387, "😊 Heureux            ▾", 10),
            words(
                400,
                418,
                "L'ambiance décrit le texte du rêve, ce n'est pas un diagnostic.",
                8.5,
                400,
                "start",
                "#64748b",
            ),
            button(400, 440, 190, 30, "Enregistrer les corrections", primary=True),
            button(600, 440, 120, 30, "Supprimer"),
            note(30, 112, 1),
            note(548, 126, 2),
            note(790, 300, 3),
            note(790, 418, 4),
            note(730, 455, 5),
        ]
    )
    return browser("/dreams/6f1c…/", body, nav="Historique")


def history() -> str:
    """Écran 5 : historique filtré.

    Returns:
        Document SVG.
    """
    parts = [
        words(40, 100, "Mes rêves", 17, 700),
        box(40, 116, 170, 26, "#fff", LINE, 5),
        words(50, 129, "📅  01/10 → 04/11", 10),
        chip(222, 119, "7 j"),
        chip(258, 119, "30 j", True),
        chip(310, 119, "😊 Heureux"),
        chip(392, 119, "😰 Stressant", True),
        chip(482, 119, "😢 Triste"),
        chip(556, 119, "🌀 Étrange"),
        chip(636, 119, "😐 Neutre"),
        words(780, 129, "Réinitialiser", 9.5, 600, "end"),
    ]
    for index in range(6):
        col, row = index % 3, index // 3
        x, y = 40 + col * 252, 158 + row * 150
        parts += [
            box(x, y, 236, 138, "#fff", LINE, 10),
            picture(x + 8, y + 8, 80, 80),
            words(x + 98, y + 20, "02/11 · 08:15", 9, 600),
            chip(x + 98, y + 30, "😰 Stressant"),
            bars(x + 98, y + 62, 125, 2),
            bars(x + 8, y + 100, 220, 2),
        ]
    parts += [
        words(410, 478, "‹  1  2  3  ›", 11, 600, "middle"),
        note(30, 129, 1),
        note(254, 165, 2),
        note(445, 478, 3),
    ]
    return browser("/dreams/?emotion=stressant&from=2026-10-01", "".join(parts), nav="Historique")


def dashboard() -> str:
    """Écran 6 : tableau de bord.

    Returns:
        Document SVG.
    """
    parts = [words(40, 100, "Mon tableau de bord", 17, 700), chip(640, 90, "30 derniers jours", True)]
    for i, (name, value) in enumerate(
        [("Rêves racontés", "18"), ("Ambiance dominante", "😰 Stressant"), ("Rêves par semaine", "4,2")]
    ):
        x = 40 + i * 252
        parts += [
            box(x, 116, 236, 62, FILL, LINE, 10),
            words(x + 12, 134, name, 9, 600, "start", "#64748b"),
            words(x + 12, 158, value, 15, 700),
        ]
    parts += [
        box(40, 192, 250, 250, "#fff", LINE, 10),
        words(52, 210, "Répartition des émotions", 10, 700),
        f'<circle cx="165" cy="320" r="70" fill="none" stroke="{SOFT}" stroke-width="28"/>',
        '<circle cx="165" cy="320" r="70" fill="none" stroke="#94a3b8" stroke-width="28" '
        'stroke-dasharray="160 440" transform="rotate(-90 165 320)"/>',
        box(304, 192, 476, 250, "#fff", LINE, 10),
        words(316, 210, "Évolution dans le temps", 10, 700),
    ]
    for i in range(12):
        height = 30 + (i * 37 % 120)
        parts.append(box(330 + i * 36, 420 - height, 22, height, "#cbd5e1", "#cbd5e1", 3))
    parts += [
        f'<line x1="320" y1="420" x2="765" y2="420" stroke="{LINE}"/>',
        words(780, 462, "Voir les données sous forme de tableau", 9.5, 600, "end"),
        note(30, 147, 1),
        note(296, 210, 2),
        note(560, 462, 3),
    ]
    return browser("/dashboard/?period=30", "".join(parts), nav="Tableau de bord")


def account() -> str:
    """Écran 7 : compte et droits RGPD.

    Returns:
        Document SVG.
    """
    body = "".join(
        [
            words(40, 100, "Mon compte", 17, 700),
            box(40, 118, 360, 110, "#fff", LINE, 10),
            words(54, 138, "Consentement IA", 11, 700),
            bars(54, 152, 320, 2),
            box(54, 186, 36, 18, "#475569", "#475569", 9),
            '<circle cx="81" cy="195" r="6" fill="#fff"/>',
            words(100, 195, "Actif depuis le 4 novembre 2026 · version 1.0", 9.5),
            box(420, 118, 360, 110, "#fff", LINE, 10),
            words(434, 138, "Mes données", 11, 700),
            bars(434, 152, 320, 2),
            button(434, 182, 200, 28, "Exporter mes rêves (JSON)"),
            box(40, 244, 740, 96, "#fff", NOTE, 10, dashed=True),
            words(54, 264, "Zone sensible", 11, 700, "start", NOTE),
            words(54, 284, "Supprimer mon compte efface définitivement mes rêves, images et enregistrements.", 10),
            button(54, 300, 200, 28, "Supprimer mon compte"),
            box(470, 356, 310, 120, "#fff", "#475569", 10),
            words(484, 376, "Confirmer la suppression ?", 11, 700),
            words(484, 396, "Saisissez SUPPRIMER pour confirmer.", 9.5),
            box(484, 406, 280, 24, "#fff", LINE, 5),
            button(484, 440, 130, 26, "Annuler"),
            button(624, 440, 140, 26, "Supprimer", primary=True),
            note(30, 138, 1),
            note(410, 196, 2),
            note(262, 314, 3),
            note(460, 376, 4),
        ]
    )
    return browser("/account/", body, nav="Compte")


def mobile_record() -> str:
    """Écran mobile : raconter (persona Léa, au lit).

    Returns:
        Document SVG.
    """
    body = "".join(
        [
            words(125, 100, "Racontez votre rêve", 14, 700, "middle"),
            f'<circle cx="125" cy="200" r="58" fill="{FILL}" stroke="#475569" stroke-width="2"/>',
            '<rect x="115" y="172" width="20" height="36" rx="10" fill="#475569"/>',
            words(125, 285, "Appuyez et parlez", 10.5, 600, "middle"),
            words(125, 330, "ou", 9.5, 400, "middle", "#64748b"),
            button(40, 345, 170, 32, "Importer un fichier"),
            chip(70, 400, "3 / 5 aujourd'hui"),
            f'<line x1="1" y1="440" x2="249" y2="440" stroke="{SOFT}"/>',
            *(words(35 + i * 60, 470, icon, 15, 400, "middle") for i, icon in enumerate(["🎙️", "📚", "📊", "👤"])),
            note(196, 150, 1),
            note(222, 470, 2),
        ]
    )
    return phone("Raconter", body)


def mobile_result() -> str:
    """Écran mobile : résultat.

    Returns:
        Document SVG.
    """
    body = "".join(
        [
            picture(20, 76, 210, 170),
            box(20, 258, 110, 24, "#cbd5e1", LINE, 12),
            words(75, 270, "😊 Heureux", 10, 700, "middle"),
            words(20, 300, "Transcription", 9.5, 700),
            box(20, 308, 210, 70, "#fff", LINE, 6),
            bars(30, 318, 190, 4),
            box(20, 388, 210, 24, "#fff", LINE, 5),
            words(30, 400, "Corriger l'ambiance  ▾", 9.5),
            button(20, 424, 210, 30, "Enregistrer", primary=True),
            note(236, 82, 1),
            note(236, 340, 2),
        ]
    )
    return phone("Résultat", body)


# ---------------------------------------------------------------- parcours


def flow() -> str:
    """Parcours utilisateur (flow diagram).

    Returns:
        Document SVG.
    """
    w, h = 190, 58
    col = [20, 270, 520, 770]
    row1, row2 = 140, 330

    def step(r: Rect, title: str, sub: str = "", kind: str = "main") -> str:
        styles = {
            "main": ("#6d28d9", "#fff", "#ede9fe"),
            "aux": ("#fff", INK, "#64748b"),
            "error": ("#fff1f2", "#9f1239", "#be123c"),
        }
        fill, ink, sub_ink = styles[kind]
        dash = kind != "main"
        stroke = "#6d28d9" if kind == "main" else NOTE if kind == "error" else LINE
        out = box(r.x, r.y, r.w, r.h, fill, stroke, 12, dashed=dash)
        out += words(r.x + r.w / 2, r.y + (r.h / 2 - 7 if sub else r.h / 2), title, 11.5, 700, "middle", ink)
        if sub:
            out += words(r.x + r.w / 2, r.y + r.h / 2 + 10, sub, 9, 400, "middle", sub_ink)
        return out

    s = [
        Rect(col[0], row1, w, h),
        Rect(col[1], row1, w, h),
        Rect(col[2], row1, w, h),
        Rect(col[3], row1, w, h),
        Rect(col[3], row2, w, h),
        Rect(col[2], row2, w, h),
        Rect(col[1], row2, w, h),
        Rect(col[0], row2, w, h),
    ]
    consent = Rect(col[1], 20, w, 54)
    compte = Rect(col[2], 20, w, 54)
    invalid = Rect(col[3], 20, w, 54)
    retry = Rect(col[3], 450, w, 54)
    fix = Rect(col[2], 450, w, 54)
    body = "".join(
        [
            step(s[0], "1 · Arrivée", "lien, favori, rappel"),
            step(s[1], "2 · Inscription / connexion", "e-mail + mot de passe"),
            step(s[2], "3 · Raconter", "accueil connecté"),
            step(s[3], "4 · Enregistrer ou importer", "micro ou fichier"),
            step(s[4], "5 · Suivi du traitement", "étapes en direct (≈ 30 s)"),
            step(s[5], "6 · Résultat", "texte, ambiance, image"),
            step(s[6], "7 · Historique", "filtres date / humeur"),
            step(s[7], "8 · Tableau de bord", "évolution de l'humeur"),
            step(consent, "Consentement IA", "case non pré-cochée", "aux"),
            step(compte, "Compte", "export, retrait, suppression", "aux"),
            step(invalid, "Fichier invalide / micro refusé", "message précis + import", "error"),
            step(retry, "Échec d'une API", "« Réessayer » à l'étape", "error"),
            step(fix, "Corriger · Supprimer", "image de secours si refus", "aux"),
            *(link(a, b) for a, b in zip(s, s[1:], strict=False)),
            link(consent, s[1], dashed=True),
            link(s[2], compte, dashed=True),
            link(s[3], invalid, dashed=True),
            link(invalid, s[2], ["retour"], t=0.45, dashed=True),
            link(s[4], retry, dashed=True),
            link(s[5], fix, dashed=True),
            label(col[0] + w / 2, row1 + h + 28, "déjà connecté : 1 → 3"),
            label(col[1] + w + 30, row2 + h + 24, "nouveau rêve → 3"),
        ]
    )
    return svg(980, 520, body, "Parcours utilisateur")


SCREENS = {
    "flow": flow,
    "signup": signup,
    "record": record,
    "progress": progress,
    "result": result,
    "history": history,
    "dashboard": dashboard,
    "account": account,
    "mobile_record": mobile_record,
    "mobile_result": mobile_result,
}
