"""Thème visuel « ciel nocturne » et fragments HTML de la maquette.

Le style est injecté une fois par page ; les fonctions ``*_html`` renvoient
des fragments autonomes, ce qui les garde testables sans Streamlit.
"""

from __future__ import annotations

from html import escape

from services import EMOTIONS, Emotion

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;500;600&display=swap');

:root {
  --night: #070718;
  --ink: #ece9ff;
  --muted: #a7a3c9;
  --violet: #a78bfa;
  --rose: #f472b6;
  --cyan: #67e8f9;
  --glass: rgba(255, 255, 255, 0.045);
  --glass-border: rgba(196, 181, 253, 0.18);
}

html, body, .stApp, .stMarkdown, p, label, button, input, textarea, [data-baseweb] { font-family: 'Inter', system-ui, sans-serif; }
.stApp {
  isolation: isolate;
  color: var(--ink);
  background:
    radial-gradient(1200px 600px at 10% -10%, rgba(124, 58, 237, 0.35), transparent 60%),
    radial-gradient(900px 500px at 100% 0%, rgba(236, 72, 153, 0.22), transparent 60%),
    radial-gradient(900px 700px at 50% 120%, rgba(34, 211, 238, 0.18), transparent 60%),
    var(--night);
  background-attachment: fixed;
}
.stApp::before, .stApp::after {
  content: ""; position: fixed; inset: 0; z-index: -1; pointer-events: none;
  background-image:
    radial-gradient(1.2px 1.2px at 12% 18%, #fff, transparent),
    radial-gradient(1px 1px at 34% 62%, #fff, transparent),
    radial-gradient(1.4px 1.4px at 71% 28%, #fff, transparent),
    radial-gradient(1px 1px at 88% 74%, #fff, transparent),
    radial-gradient(1.2px 1.2px at 52% 8%, #fff, transparent),
    radial-gradient(1px 1px at 22% 88%, #fff, transparent),
    radial-gradient(1.3px 1.3px at 64% 92%, #fff, transparent),
    radial-gradient(1px 1px at 93% 41%, #fff, transparent);
  background-size: 420px 420px;
  animation: twinkle 5s ease-in-out infinite alternate;
}
.stApp::after { background-size: 650px 650px; background-position: 130px 210px; animation-delay: -2.5s; }
@keyframes twinkle { from { opacity: .25 } to { opacity: .9 } }

[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
  background: rgba(10, 8, 34, 0.72); backdrop-filter: blur(14px);
  border-right: 1px solid var(--glass-border);
}
.block-container { padding-top: 2.2rem; max-width: 1000px; }
h1, h2, h3 { font-family: 'Fraunces', Georgia, serif !important; letter-spacing: -0.01em; }
p, label, .stMarkdown, .stCaption { color: var(--ink); }

/* Héros */
.hero { text-align: center; padding: 1.2rem 0 0.6rem; }
.moon {
  width: 74px; height: 74px; margin: 0 auto 0.8rem; border-radius: 50%;
  background: radial-gradient(circle at 35% 35%, #fffbe8, #f5e7b8 55%, #d8c48a);
  box-shadow: 0 0 40px 8px rgba(253, 230, 138, .35), 0 0 120px 30px rgba(167, 139, 250, .25);
  animation: float 6s ease-in-out infinite;
}
@keyframes float { 50% { transform: translateY(-8px) } }
.hero h1 {
  font-size: clamp(2.3rem, 6vw, 3.6rem); margin: 0; line-height: 1.05;
  background: linear-gradient(100deg, #fff 10%, var(--violet) 45%, var(--rose) 75%, var(--cyan));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.hero p { color: var(--muted); font-size: 1.08rem; margin-top: .6rem; }

/* Pipeline */
.pipeline { display: flex; justify-content: center; flex-wrap: wrap; gap: .5rem; margin: 1rem 0 1.6rem; }
.step {
  display: flex; align-items: center; gap: .45rem; padding: .45rem .9rem; border-radius: 999px;
  background: var(--glass); border: 1px solid var(--glass-border); color: var(--muted); font-size: .9rem;
  transition: all .4s ease;
}
.step.on { color: #fff; border-color: rgba(244, 114, 182, .6);
  background: linear-gradient(90deg, rgba(167, 139, 250, .28), rgba(244, 114, 182, .22));
  box-shadow: 0 0 18px rgba(167, 139, 250, .35); }
.arrow { color: var(--glass-border); align-self: center; }

/* Cartes en verre (conteneurs Streamlit à clé « card-… ») */
[class*="st-key-card"] {
  background: var(--glass); border: 1px solid var(--glass-border); border-radius: 22px;
  padding: 1.3rem 1.4rem; backdrop-filter: blur(10px);
  box-shadow: 0 10px 40px rgba(0, 0, 0, .35), inset 0 1px 0 rgba(255, 255, 255, .06);
}

/* Boutons */
.stButton > button, .stDownloadButton > button {
  border-radius: 999px; border: 1px solid var(--glass-border); background: var(--glass); color: var(--ink);
  transition: transform .15s ease, box-shadow .3s ease;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 0 22px rgba(167, 139, 250, .45); }
.stButton > button[kind="primary"] {
  border: 0; color: #fff; font-weight: 600;
  background: linear-gradient(100deg, #7c3aed, #db2777 25%, #f59e0b 50%, #db2777 75%, #7c3aed);
  background-size: 200% 100%; animation: sheen 8s linear infinite;
}
@keyframes sheen { to { background-position: 200% 0 } }

/* Résultat */
.dream-image img, [data-testid="stImage"] img { border-radius: 18px; }
.glow-frame { border-radius: 22px; padding: 3px; }
.emotion-badge {
  display: inline-flex; align-items: center; gap: .6rem; padding: .55rem 1.1rem; border-radius: 999px;
  font-weight: 600; font-size: 1.05rem; color: #fff;
}
.emotion-badge .icon { font-size: 1.8rem; line-height: 1; }
.bars { margin-top: .9rem; display: grid; gap: .45rem; }
.bar { display: grid; grid-template-columns: 7.5rem 1fr 3rem; align-items: center; gap: .6rem; font-size: .86rem; color: var(--muted); }
.bar .track { height: 8px; border-radius: 99px; background: rgba(255, 255, 255, .07); overflow: hidden; }
.bar .fill { height: 100%; border-radius: 99px; animation: grow 1s cubic-bezier(.2, .8, .2, 1) both; }
@keyframes grow { from { width: 0 !important } }
.bar .pct { text-align: right; font-variant-numeric: tabular-nums; }

.kpis { display: grid; grid-template-columns: repeat(3, 1fr); gap: .7rem; margin: .4rem 0 .2rem; }
.kpi { background: rgba(255, 255, 255, .04); border: 1px solid var(--glass-border); border-radius: 16px; padding: .7rem .9rem; }
.kpi b { display: block; font-size: 1.25rem; color: #fff; font-variant-numeric: tabular-nums; }
.kpi span { font-size: .78rem; color: var(--muted); text-transform: uppercase; letter-spacing: .06em; }

/* Galerie */
.dream-card-meta { display: flex; justify-content: space-between; align-items: center; margin: .5rem 0 .2rem; font-size: .85rem; color: var(--muted); }
.chip { padding: .15rem .6rem; border-radius: 99px; font-size: .78rem; font-weight: 600; color: #fff; }
.excerpt { font-size: .9rem; color: var(--ink); opacity: .85; line-height: 1.4; }

.empty { text-align: center; padding: 2rem 1rem; color: var(--muted); }
.empty .big { font-size: 2.4rem; }
.footer { text-align: center; color: var(--muted); font-size: .8rem; margin-top: 2.5rem; opacity: .8; }

@media (max-width: 640px) {
  .kpis { grid-template-columns: 1fr 1fr; }
  .bar { grid-template-columns: 6rem 1fr 2.6rem; }
}
@media (prefers-reduced-motion: reduce) {
  *, .stApp::before, .stApp::after { animation: none !important; transition: none !important; }
}
</style>
"""

PIPELINE_STEPS: tuple[tuple[str, str], ...] = (
    ("🎙️", "Voix"),
    ("📝", "Texte"),
    ("💫", "Émotion"),
    ("🎨", "Image"),
)


def hero_html() -> str:
    """Renvoie l'en-tête animé de la page.

    Returns:
        Fragment HTML.
    """
    return (
        '<div class="hero"><div class="moon"></div><h1>Synthétiseur de rêves</h1>'
        "<p>Racontez votre rêve au réveil. Il devient texte, émotion et image en quelques secondes.</p></div>"
    )


def pipeline_html(done: int) -> str:
    """Renvoie la frise des étapes du traitement.

    Args:
        done: Nombre d'étapes terminées (0 à 4).

    Returns:
        Fragment HTML.
    """
    parts = []
    for index, (icon, label) in enumerate(PIPELINE_STEPS):
        state = "on" if index < done else ""
        parts.append(f'<div class="step {state}">{icon} {label}</div>')
    return '<div class="pipeline">' + '<span class="arrow">›</span>'.join(parts) + "</div>"


def badge_html(emotion: Emotion) -> str:
    """Renvoie le badge de l'émotion retenue.

    Args:
        emotion: Émotion à afficher.

    Returns:
        Fragment HTML.
    """
    return (
        f'<div class="emotion-badge" style="background:linear-gradient(90deg,{emotion.color}cc,{emotion.color}55);'
        f'box-shadow:0 0 26px {emotion.color}66"><span class="icon">{emotion.icon}</span>{escape(emotion.label)}</div>'
    )


def bars_html(scores: dict[str, float]) -> str:
    """Renvoie les barres de probabilité par émotion, triées.

    Args:
        scores: Probabilités par clé d'émotion.

    Returns:
        Fragment HTML.
    """
    rows = []
    for key, value in sorted(scores.items(), key=lambda item: item[1], reverse=True):
        emo = EMOTIONS[key]
        pct = round(value * 100)
        rows.append(
            f'<div class="bar"><span>{emo.icon} {escape(emo.label)}</span>'
            f'<div class="track"><div class="fill" style="width:{pct}%;background:{emo.color}"></div></div>'
            f'<span class="pct">{pct} %</span></div>'
        )
    return '<div class="bars">' + "".join(rows) + "</div>"


def kpis_html(duration_s: float | None, elapsed_s: float, cost_eur: float) -> str:
    """Renvoie la rangée d'indicateurs du traitement.

    Args:
        duration_s: Durée de l'audio (``None`` si inconnue).
        elapsed_s: Durée totale du traitement.
        cost_eur: Coût API estimé.

    Returns:
        Fragment HTML.
    """
    audio = f"{duration_s:.0f} s" if duration_s is not None else "—"
    cost = f"{cost_eur:.3f}".replace(".", ",")
    elapsed = f"{elapsed_s:.1f}".replace(".", ",")
    return (
        '<div class="kpis">'
        f'<div class="kpi"><span>Audio</span><b>{audio}</b></div>'
        f'<div class="kpi"><span>Traitement</span><b>{elapsed:s} s</b></div>'
        f'<div class="kpi"><span>Coût API</span><b>{cost:s} €</b></div>'
        "</div>"
    )


def frame_style(emotion: Emotion) -> str:
    """Renvoie le cadre lumineux de l'image, aux couleurs de l'émotion.

    Args:
        emotion: Émotion retenue.

    Returns:
        Balise ``<style>`` ciblant la carte image.
    """
    return (
        f"<style>.st-key-card-image [data-testid='stImage'] img {{"
        f"box-shadow: 0 0 0 2px {emotion.color}88, 0 0 50px {emotion.color}55, 0 20px 60px rgba(0,0,0,.5);}}</style>"
    )


def card_meta_html(emotion: Emotion, date_label: str, text: str, limit: int = 110) -> str:
    """Renvoie le pied d'une carte de la galerie.

    Args:
        emotion: Émotion du rêve.
        date_label: Date déjà formatée.
        text: Texte du rêve.
        limit: Longueur maximale de l'extrait.

    Returns:
        Fragment HTML.
    """
    excerpt = text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
    return (
        f'<div class="dream-card-meta"><span>{escape(date_label)}</span>'
        f'<span class="chip" style="background:{emotion.color}aa">{emotion.icon} {escape(emotion.label)}</span></div>'
        f'<div class="excerpt">{escape(excerpt)}</div>'
    )


EMPTY_HTML = (
    '<div class="empty"><div class="big">🌌</div>Votre ciel est encore vide.<br>'
    "Racontez un premier rêve, ou chargez des exemples depuis la barre latérale.</div>"
)

FOOTER_HTML = (
    '<div class="footer">Maquette de pré-production · APIs simulées, aucune donnée envoyée · '
    "L'ambiance décrit le texte du rêve, ce n'est pas un diagnostic.</div>"
)
