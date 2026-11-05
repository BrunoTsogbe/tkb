"""Diagrammes d'architecture du « Synthétiseur de rêves » (C4, ERD, séquence, CI/CD)."""

from __future__ import annotations

from svg import (
    LINE,
    Rect,
    boundary,
    entity,
    entity_height,
    link,
    node,
    svg,
    text,
)


def c4_context() -> str:
    """Diagramme C4 de niveau 1 (contexte).

    Returns:
        Document SVG.
    """
    dreamer = Rect(30, 60, 190, 100)
    admin = Rect(30, 290, 190, 100)
    system = Rect(355, 160, 250, 130)
    openai = Rect(720, 20, 230, 86)
    backup = Rect(720, 128, 230, 86)
    sentry = Rect(720, 236, 230, 74)
    hf = Rect(720, 332, 230, 74)
    mail = Rect(355, 360, 250, 70)
    body = "".join(
        [
            node(dreamer, "Rêveur", "person", desc=["Raconte ses rêves au réveil,", "consulte son historique"]),
            node(admin, "Administrateur", "person", desc=["Porteur du projet : suit", "coûts, erreurs, quotas"]),
            node(
                system,
                "Synthétiseur de rêves",
                "system",
                "Application web",
                ["Transcrit, classe l'émotion,", "illustre et archive les rêves"],
            ),
            node(openai, "OpenAI API", "external", "SaaS · US", ["gpt-transcribe", "GPT Image 1 Mini"]),
            node(backup, "STT de secours", "external", "Deepgram / AssemblyAI", ["Bascule si OpenAI indisponible"]),
            node(sentry, "Sentry", "external", "SaaS", ["Erreurs et traces"]),
            node(hf, "Hugging Face Hub", "external", "Registre de modèles", ["Modèle d'émotion (au build)"]),
            node(mail, "Service d'e-mail", "external", "SMTP transactionnel", ["Réinitialisation du mot de passe"]),
            link(dreamer, system, ["Raconte, corrige, consulte", "[HTTPS, navigateur]"], t=0.45),
            link(admin, system, ["Supervise", "[HTTPS, /admin]"], t=0.45),
            link(system, openai, ["Audio → texte, prompt → image", "[HTTPS/JSON, clé API]"], t=0.5, dy=-6),
            link(system, backup, ["Audio → texte", "[HTTPS]"], t=0.55, dy=4),
            link(system, sentry, ["Exceptions (sans contenu)"], t=0.5, dy=-2),
            link(system, hf, ["Télécharge le modèle"], t=0.45, dy=10),
            link(system, mail, ["Envoie [SMTP/TLS]"], t=0.5, dx=58),
        ]
    )
    return svg(970, 440, body, "Diagramme C4 de contexte")


def c4_container() -> str:
    """Diagramme C4 de niveau 2 (conteneurs).

    Returns:
        Document SVG.
    """
    user = Rect(15, 235, 150, 95)
    ui = Rect(230, 48, 250, 100)
    web = Rect(230, 228, 250, 110)
    redis = Rect(530, 48, 250, 100)
    worker = Rect(530, 228, 250, 110)
    pg = Rect(230, 418, 250, 100)
    media = Rect(530, 418, 250, 100)
    openai = Rect(845, 40, 170, 90)
    backup = Rect(845, 170, 170, 80)
    sentry = Rect(845, 300, 170, 72)
    mail = Rect(845, 420, 170, 72)
    body = "".join(
        [
            boundary(Rect(205, 18, 600, 545), "Synthétiseur de rêves  [système]"),
            node(user, "Rêveur", "person"),
            node(
                ui,
                "Interface web",
                "container",
                "Gabarits Django, HTMX, Tailwind",
                ["Enregistrement (MediaRecorder),", "suivi en direct, tableau de bord"],
            ),
            node(
                web,
                "Application web",
                "container",
                "Django 5.2 · Gunicorn",
                ["Auth, upload, historique, filtres,", "budget, admin, /healthz"],
            ),
            node(redis, "File de tâches", "db", "Redis 7", ["Broker Celery, cache, quotas"]),
            node(
                worker,
                "Worker IA",
                "container",
                "Celery 5 · Python 3.12",
                ["Pipeline : STT → émotion (HF local)", "→ image ; relances, coûts"],
            ),
            node(
                pg,
                "Base de données",
                "db",
                "PostgreSQL 16",
                ["Utilisateurs, rêves, émotions,", "journal des appels API"],
            ),
            node(media, "Stockage des médias", "db", "Volume disque / S3", ["Audio (temporaire), images"]),
            node(openai, "OpenAI API", "external", "SaaS", ["STT + images"]),
            node(backup, "STT de secours", "external", "Deepgram / AssemblyAI"),
            node(sentry, "Sentry", "external", "SaaS"),
            node(mail, "E-mail", "external", "SMTP"),
            link(user, ui, ["Utilise", "[HTTPS]"], t=0.42),
            link(ui, web, ["Requêtes, upload audio,", "polling du statut [HTMX]"], t=0.5, dx=-22),
            link(web, redis, ["Publie", "process_dream(id)"], t=0.62, dx=30, dy=4),
            link(redis, worker, ["Consomme les tâches"], t=0.5),
            link(web, pg, ["Lit / écrit [SQL, ORM]"], t=0.5),
            link(worker, pg, ["Statut, résultats, coûts"], t=0.2, dx=-40, dy=-2),
            link(web, media, ["Dépose l'audio"], t=0.72, dx=24, dy=6),
            link(worker, media, ["Lit l'audio, écrit l'image,", "supprime l'audio"], t=0.5, dx=8),
            link(worker, openai, ["HTTPS, timeouts,", "relances bornées"], t=0.58, dy=-4),
            link(worker, backup, ["Bascule STT"], t=0.42, dy=-2),
            link(worker, sentry, ["Erreurs (web + worker)"], t=0.55, dy=6),
            link(worker, mail, ["E-mails asynchrones"], t=0.6, dy=8),
        ]
    )
    return svg(1030, 580, body, "Diagramme C4 des conteneurs")


USER_ROWS = [
    ("PK", "id", "bigint"),
    ("UQ", "email", "varchar(254)"),
    ("", "password", "hash Argon2"),
    ("", "is_active", "bool"),
    ("", "date_joined", "timestamptz"),
    ("", "last_login", "timestamptz ?"),
]
PROFILE_ROWS = [
    ("PK", "id", "bigint"),
    ("FK", "user_id  (UQ)", "→ User"),
    ("", "ai_consent_at", "timestamptz ?"),
    ("", "consent_version", "varchar(10)"),
    ("", "daily_dream_limit", "smallint = 5"),
    ("", "timezone", "varchar(40)"),
]
DREAM_ROWS = [
    ("PK", "id", "uuid"),
    ("FK", "user_id", "→ User"),
    ("", "status", "enum (6)"),
    ("", "created_at / updated_at", "timestamptz"),
    ("", "audio_file", "varchar ?"),
    ("", "audio_format", "varchar(8)"),
    ("", "audio_duration_s", "real ?"),
    ("", "audio_deleted_at", "timestamptz ?"),
    ("", "transcript", "text ?"),
    ("", "transcript_model", "varchar(40)"),
    ("", "transcript_edited", "bool"),
    ("FK", "emotion_id", "→ Emotion ?"),
    ("", "emotion_scores", "jsonb"),
    ("", "emotion_corrected", "bool"),
    ("", "image_file", "varchar ?"),
    ("", "image_prompt", "text ?"),
    ("", "image_is_fallback", "bool"),
    ("", "error_code / error_step", "varchar ?"),
    ("", "processing_ms", "integer ?"),
    ("", "cost_eur", "numeric(8,5)"),
]
EMOTION_ROWS = [
    ("PK", "id", "smallint"),
    ("UQ", "key", "varchar(20)"),
    ("", "label", "varchar(40)"),
    ("", "icon", "varchar(8)"),
    ("", "color", "char(7)"),
]
APICALL_ROWS = [
    ("PK", "id", "bigint"),
    ("FK", "dream_id", "→ Dream ?"),
    ("FK", "user_id", "→ User ?"),
    ("", "kind", "stt | emotion | image"),
    ("", "provider / model", "varchar(40)"),
    ("", "status", "ok | error | timeout"),
    ("", "http_status", "smallint ?"),
    ("", "attempt", "smallint"),
    ("", "latency_ms", "integer"),
    ("", "units", "numeric (min, img)"),
    ("", "cost_usd / cost_eur", "numeric(8,5)"),
    ("", "error_code", "varchar ?"),
    ("", "created_at", "timestamptz"),
]


def erd() -> str:
    """Diagramme entité-association.

    Returns:
        Document SVG.
    """
    user = Rect(20, 20, 235, entity_height(len(USER_ROWS)))
    profile = Rect(20, 250, 235, entity_height(len(PROFILE_ROWS)))
    dream = Rect(335, 20, 300, entity_height(len(DREAM_ROWS)))
    emotion = Rect(715, 20, 255, entity_height(len(EMOTION_ROWS)))
    api = Rect(715, 175, 255, entity_height(len(APICALL_ROWS)))
    bottom = max(dream.y + dream.h, api.y + api.h) + 22

    def card(x: float, y: float, value: str, anchor: str = "middle") -> str:
        return text(x, y, value, 10.5, 700, "#6d28d9", anchor=anchor)

    body = "".join(
        [
            entity(user.x, user.y, user.w, "User", USER_ROWS, "django.contrib.auth"),
            entity(profile.x, profile.y, profile.w, "Profile", PROFILE_ROWS, "consentement, quotas"),
            entity(dream.x, dream.y, dream.w, "Dream", DREAM_ROWS, "cœur du domaine"),
            entity(emotion.x, emotion.y, emotion.w, "Emotion", EMOTION_ROWS, "référentiel"),
            entity(api.x, api.y, api.w, "APICallLog", APICALL_ROWS, "coûts, latences"),
            # User 1 — 0..N Dream
            f'<line x1="{user.x + user.w}" y1="70" x2="{dream.x}" y2="70" stroke="{LINE}" stroke-width="1.4"/>',
            card(user.x + user.w + 8, 62, "1", "start"),
            card(dream.x - 8, 62, "0..N", "end"),
            # User 1 — 1 Profile
            f'<line x1="137" y1="{user.y + user.h}" x2="137" y2="{profile.y}" stroke="{LINE}" stroke-width="1.4"/>',
            card(146, user.y + user.h + 14, "1", "start"),
            card(146, profile.y - 8, "1", "start"),
            # Emotion 0..1 — 0..N Dream
            f'<line x1="{emotion.x}" y1="70" x2="{dream.x + dream.w}" y2="70" stroke="{LINE}" stroke-width="1.4"/>',
            card(emotion.x - 8, 62, "0..1", "end"),
            card(dream.x + dream.w + 8, 62, "0..N", "start"),
            # Dream 0..1 — 0..N APICallLog
            f'<line x1="{dream.x + dream.w}" y1="260" x2="{api.x}" y2="260" stroke="{LINE}" stroke-width="1.4"/>',
            card(dream.x + dream.w + 8, 252, "0..1", "start"),
            card(api.x - 8, 252, "0..N", "end"),
            # User 1 — 0..N APICallLog (contourne Dream par le bas)
            f'<polyline points="{user.x + user.w},120 300,120 300,{bottom} {api.x + api.w / 2},{bottom} '
            f'{api.x + api.w / 2},{api.y + api.h}" fill="none" stroke="{LINE}" stroke-width="1.4" '
            'stroke-dasharray="5 4"/>',
            card(user.x + user.w + 8, 112, "1", "start"),
            card(api.x + api.w / 2 + 8, api.y + api.h + 14, "0..N", "start"),
            text(
                560,
                bottom + 14,
                "APICallLog.user_id : NULL après suppression du compte (le coût reste compté)",
                9.5,
                400,
                "#64748b",
                italic=True,
            ),
        ]
    )
    return svg(990, int(bottom + 30), body, "Modèle entité-association")


def sequence() -> str:
    """Diagramme de séquence UML : traitement complet d'un rêve.

    Returns:
        Document SVG.
    """
    actors = ["Rêveur", "Navigateur", "Django web", "PostgreSQL", "Redis", "Worker Celery", "Stockage", "OpenAI"]
    xs = [60 + i * 127 for i in range(len(actors))]
    pos = dict(zip(actors, xs, strict=True))
    top, step = 62, 27.5

    steps: list[tuple] = [
        ("msg", "Rêveur", "Navigateur", "Enregistre son rêve (micro)"),
        ("msg", "Navigateur", "Django web", "POST /dreams/ (audio, CSRF)"),
        ("self", "Django web", "Valide format, taille, quota, budget"),
        ("msg", "Django web", "Stockage", "Enregistre l'audio"),
        ("msg", "Django web", "PostgreSQL", "INSERT Dream (received)"),
        ("msg", "Django web", "Redis", "process_dream.delay(id)"),
        ("ret", "Django web", "Navigateur", "202 + page de suivi"),
        ("msg", "Redis", "Worker Celery", "Tâche process_dream"),
        ("msg", "Worker Celery", "PostgreSQL", "status = transcribing"),
        ("msg", "Worker Celery", "OpenAI", "POST /audio/transcriptions (60 s)"),
        ("ret", "OpenAI", "Worker Celery", "Texte"),
        ("msg", "Worker Celery", "PostgreSQL", "transcript + APICallLog"),
        ("msg", "Worker Celery", "Stockage", "Supprime l'audio"),
        ("self", "Worker Celery", "Classe l'émotion (modèle local)"),
        ("self", "Worker Celery", "Budget OK ? prompt minimisé"),
        ("msg", "Worker Celery", "OpenAI", "POST /images/generations (90 s)"),
        ("ret", "OpenAI", "Worker Celery", "Image (base64)"),
        ("msg", "Worker Celery", "Stockage", "Enregistre l'image"),
        ("msg", "Worker Celery", "PostgreSQL", "status = done + APICallLog"),
        ("gap",),
        ("msg", "Navigateur", "Django web", "GET /dreams/{id}/status/"),
        ("msg", "Django web", "PostgreSQL", "Lit statut et résultats"),
        ("ret", "Django web", "Navigateur", "Fragment HTMX (étape / résultat)"),
        ("msg", "Navigateur", "Rêveur", "Texte, émotion, image"),
    ]
    height = top + 30 + step * len(steps) + 70
    parts = []
    for name, x in pos.items():
        parts.append(
            f'<line x1="{x}" y1="{top + 16}" x2="{x}" y2="{height - 50}" stroke="#cbd5e1" '
            'stroke-width="1.2" stroke-dasharray="4 4"/>'
        )
        fill = "#1e3a8a" if name == "Rêveur" else "#64748b" if name == "OpenAI" else "#7c3aed"
        parts.append(
            f'<rect x="{x - 58}" y="{top - 22}" width="116" height="36" rx="8" fill="{fill}" filter="url(#sh)"/>'
        )
        parts.append(text(x, top - 4, name, 11.5, 700, "#fff"))
    # activation du worker
    w_start = top + 30 + step * 7 - 8
    w_end = top + 30 + step * 18 + 8
    parts.append(
        f'<rect x="{pos["Worker Celery"] - 5}" y="{w_start}" width="10" height="{w_end - w_start}" '
        'fill="#ede9fe" stroke="#7c3aed"/>'
    )
    # cadres
    first = top + 30 + step * 7 - 16
    parts.append(
        f'<rect x="{pos["Redis"] - 70}" y="{first}" width="{pos["OpenAI"] - pos["Redis"] + 130}" '
        f'height="{step * 12 + 12}" rx="6" fill="none" stroke="#a78bfa" stroke-width="1.2"/>'
    )
    parts.append(text(pos["OpenAI"] + 52, first + 11, "asynchrone · worker", 9.5, 700, "#7c3aed", anchor="end"))
    loop_y = top + 30 + step * 20 - 20
    parts.append(
        f'<rect x="{pos["Rêveur"] + 60}" y="{loop_y}" width="{pos["PostgreSQL"] - pos["Rêveur"] + 10}" '
        f'height="{step * 3 + 10}" rx="6" fill="none" stroke="#f59e0b" stroke-width="1.2"/>'
    )
    parts.append(
        text(
            pos["PostgreSQL"] + 64,
            loop_y + step * 3 + 2,
            ["loop · toutes les 2 s", "jusqu'à done / failed"],
            9.5,
            700,
            "#b45309",
            anchor="end",
        )
    )

    for index, item in enumerate(steps):
        y = top + 30 + step * index + 6
        kind = item[0]
        if kind == "gap":
            parts.append(
                text(
                    pos["Navigateur"] - 40,
                    y - 6,
                    "… en parallèle, la page interroge le statut",
                    9.5,
                    400,
                    "#64748b",
                    anchor="start",
                    italic=True,
                )
            )
            continue
        if kind == "self":
            x = pos[item[1]]
            parts.append(
                f'<path d="M{x + 5},{y - 7} h28 v12 h-26" fill="none" stroke="{LINE}" '
                'stroke-width="1.3" marker-end="url(#arr)"/>'
            )
            parts.append(text(x + 40, y - 1, item[2], 10.5, 400, "#0f172a", anchor="start"))
            continue
        x1, x2 = pos[item[1]], pos[item[2]]
        offset = 5 if item[1] == "Worker Celery" else 0
        end_offset = 5 if item[2] == "Worker Celery" else 0
        sign = 1 if x2 > x1 else -1
        dash = ' stroke-dasharray="5 4"' if kind == "ret" else ""
        parts.append(
            f'<line x1="{x1 + sign * offset}" y1="{y}" x2="{x2 - sign * (end_offset + 1)}" y2="{y}" '
            f'stroke="{LINE}" stroke-width="1.3"{dash} marker-end="url(#arr)"/>'
        )
        parts.append(text((x1 + x2) / 2, y - 11, item[3], 10.5, 400, "#0f172a"))
    note_y = height - 40
    parts.append(
        f'<rect x="20" y="{note_y}" width="{xs[-1] + 40}" height="32" rx="6" fill="#fff7ed" stroke="#fdba74"/>'
    )
    parts.append(
        text(
            32,
            note_y + 16,
            "Erreurs : timeout / 429 / 5xx → relance avec attente exponentielle ;"
            " refus de contenu → image de secours ; budget atteint → étape image sautée ;"
            " échec définitif → failed + « Réessayer ».",
            10,
            400,
            "#7c2d12",
            anchor="start",
        )
    )
    return svg(xs[-1] + 80, int(height), "".join(parts), "Séquence de traitement d'un rêve")


def pipeline() -> str:
    """Pipeline CI/CD (GitHub Actions → Render).

    Returns:
        Document SVG.
    """
    stages = [
        ("Push / PR", ["branche par ticket"]),
        ("Lint", ["ruff, mypy", "pip-audit"]),
        ("Tests", ["pytest + PostgreSQL", "couverture ≥ 70 %"]),
        ("Build", ["image Docker", "multi-étapes"]),
        ("Publication", ["GHCR, tag = SHA", "main uniquement"]),
        ("Déploiement", ["Render", "deploy hook"]),
        ("Vérification", ["smoke test", "/healthz + Sentry"]),
    ]
    w, gap = 128, 18
    parts = []
    for i, (title, desc) in enumerate(stages):
        x = 10 + i * (w + gap)
        fill = "#7c3aed" if i in (1, 2) else "#0e7490" if i >= 4 else "#1e293b"
        parts.append(f'<rect x="{x}" y="20" width="{w}" height="78" rx="10" fill="{fill}" filter="url(#sh)"/>')
        parts.append(text(x + w / 2, 42, title, 12.5, 700, "#fff"))
        parts.append(text(x + w / 2, 72, desc, 10, 400, "#e2e8f0"))
        if i < len(stages) - 1:
            parts.append(
                f'<line x1="{x + w + 2}" y1="59" x2="{x + w + gap - 2}" y2="59" stroke="{LINE}" '
                'stroke-width="1.6" marker-end="url(#arr)"/>'
            )
    parts.append(
        text(10 + 1.5 * (w + gap) + w / 2, 125, "✕ échec = fusion bloquée (main protégée)", 10, 600, "#b91c1c")
    )
    last = 10 + 4 * (w + gap)
    parts.append(
        f'<rect x="{last}" y="112" width="{3 * w + 2 * gap}" height="26" rx="6" fill="#ecfeff" stroke="#67e8f9"/>'
    )
    parts.append(
        text(
            last + (3 * w + 2 * gap) / 2, 125, "Repli R9 : docker compose up (même image, en local)", 10, 400, "#155e75"
        )
    )
    return svg(10 + len(stages) * (w + gap), 150, "".join(parts), "Pipeline CI/CD")


ALL = {
    "c4_contexte": c4_context,
    "c4_conteneurs": c4_container,
    "modele_donnees": erd,
    "sequence_reve": sequence,
    "pipeline_cicd": pipeline,
}
