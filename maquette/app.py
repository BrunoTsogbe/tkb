"""Maquette interactive Streamlit du « Synthétiseur de rêves ».

Lancement :
    streamlit run maquette/app.py

Toutes les APIs sont simulées (voir ``services.py``) : aucune clé n'est
nécessaire et aucun coût n'est engagé.
"""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Iterator
from datetime import datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st
from streamlit.delta_generator import DeltaGenerator

import services
import theme

st.set_page_config(page_title="Synthétiseur de rêves", page_icon="🌙", layout="wide")


def init_state() -> None:
    """Initialise les clés de session utilisées par la maquette."""
    st.session_state.setdefault("dream", None)
    st.session_state.setdefault("history", [])
    st.session_state.setdefault("demo_count", 0)


def seed_history() -> None:
    """Ajoute des rêves d'exemple répartis sur deux semaines (démonstration du tableau de bord)."""
    now = datetime.now()
    for index, text in enumerate(services.SAMPLE_TRANSCRIPTS * 2):
        emotion = services.suggest_emotion(text)
        duration = 95.0 + index * 7
        st.session_state.history.append(
            {
                "text": text,
                "emotion": emotion.key,
                "scores": services.emotion_scores(text),
                "image": services.local_placeholder(emotion, size=384, seed=f"{text}{index}"),
                "fallback": True,
                "date": now - timedelta(days=index * 1.4 + 0.3, hours=index),
                "duration": duration,
                "elapsed": 18.0 + index,
                "cost": services.estimate_cost_eur(duration),
            }
        )
    st.session_state.history.sort(key=lambda item: item["date"], reverse=True)


def sidebar() -> tuple[float, bool, bool]:
    """Affiche les réglages de démonstration.

    Returns:
        Latence simulée, panne de transcription, panne d'image.
    """
    with st.sidebar:
        st.markdown("### 🎛️ Réglages de la démo")
        delay = st.slider("Latence simulée (s)", 0.0, 5.0, 1.5, 0.5)
        fail_stt = st.toggle("Simuler une panne de transcription")
        fail_img = st.toggle("Simuler une panne du service d'images")
        st.caption("Pour montrer la gestion d'erreurs et les indicateurs de chargement.")
        st.divider()
        st.markdown("### 🗂️ Données")
        if st.button("✨ Charger des rêves d'exemple", width="stretch"):
            seed_history()
            st.rerun()
        if st.button("🧹 Vider l'historique", width="stretch", disabled=not st.session_state.history):
            st.session_state.history = []
            st.rerun()
        st.divider()
        st.caption("Maquette de pré-production · Blocs 1 et 2")
    return delay, fail_stt, fail_img


def audio_input() -> tuple[str, bytes] | None:
    """Propose l'enregistrement micro ou l'upload d'un fichier.

    Returns:
        Le couple (nom de fichier, contenu) ou ``None`` si rien n'est fourni.
    """
    with st.container(key="card-input"):
        tab_rec, tab_up = st.tabs(["🎙️ Raconter à voix haute", "📁 Importer un fichier"])
        with tab_rec:
            recorded = st.audio_input("Appuyez sur le micro et racontez votre rêve")
        with tab_up:
            uploaded = st.file_uploader("Fichier .wav ou .mp3 · 25 Mo maximum", type=["wav", "mp3"])
    source = recorded or uploaded
    if source is None:
        return None
    name = source.name if source is uploaded else "enregistrement.wav"
    return name, source.getvalue()


def typewriter(text: str) -> Iterator[str]:
    """Restitue le texte mot à mot (effet de transcription en direct).

    Args:
        text: Texte à restituer.

    Yields:
        Les mots du texte, suivis d'une espace.
    """
    for word in text.split():
        yield word + " "
        time.sleep(0.035)


def process(name: str, data: bytes, delay: float, fail_stt: bool, fail_img: bool, pipeline: DeltaGenerator) -> None:
    """Exécute le traitement simulé d'un rêve et met à jour la session.

    Args:
        name: Nom du fichier audio.
        data: Contenu audio.
        delay: Latence simulée.
        fail_stt: Simule une panne de transcription.
        fail_img: Simule une panne d'image.
        pipeline: Emplacement de la frise des étapes, mise à jour en direct.
    """
    try:
        services.validate_audio(name, data)
    except services.AudioValidationError as exc:
        st.error(f"Fichier refusé : {exc}", icon="🚫")
        return

    start = time.perf_counter()
    pipeline.markdown(theme.pipeline_html(1), unsafe_allow_html=True)
    with st.status("Votre rêve prend forme…", expanded=True) as status:
        st.write("📝 Transcription de la voix…")
        try:
            text = services.mock_transcribe(data, delay_s=delay, fail=fail_stt)
        except services.MockAPIError as exc:
            status.update(label="La transcription a échoué", state="error")
            st.error(f"{exc} Votre enregistrement n'est pas perdu.", icon="⚠️")
            pipeline.markdown(theme.pipeline_html(0), unsafe_allow_html=True)
            return
        st.write_stream(typewriter(text))
        pipeline.markdown(theme.pipeline_html(2), unsafe_allow_html=True)

        st.write("💫 Lecture de l'ambiance…")
        scores = services.emotion_scores(text)
        emotion = services.suggest_emotion(text)
        pipeline.markdown(theme.pipeline_html(3), unsafe_allow_html=True)

        st.write("🎨 Peinture de l'image…")
        image, fallback = services.fetch_placeholder(text, emotion, fail=fail_img)
        pipeline.markdown(theme.pipeline_html(4), unsafe_allow_html=True)
        status.update(label=f"Rêve prêt {emotion.icon}", state="complete", expanded=False)

    duration = services.audio_duration_s(data)
    st.session_state.dream = {
        "text": text,
        "emotion": emotion.key,
        "scores": scores,
        "image": image,
        "fallback": fallback,
        "date": datetime.now(),
        "duration": duration,
        "elapsed": time.perf_counter() - start,
        "cost": services.estimate_cost_eur(duration),
    }


def show_result() -> None:
    """Affiche le résultat courant : image, émotion, texte corrigeable."""
    dream = st.session_state.dream
    if dream is None:
        return

    emotion = services.EMOTIONS[dream["emotion"]]
    col_img, col_txt = st.columns([1, 1.1], gap="large")
    with col_img, st.container(key="card-image"):
        st.markdown(theme.frame_style(emotion), unsafe_allow_html=True)
        st.image(dream["image"], width="stretch")
        st.caption("🤖 Image générée par IA (placeholder de la maquette)")
        if dream["fallback"]:
            st.warning("Le service d'images est indisponible : une image de secours est affichée.", icon="🌙")

    with col_txt, st.container(key="card-result"):
        st.markdown(theme.badge_html(emotion), unsafe_allow_html=True)
        st.markdown(theme.bars_html(dream["scores"]), unsafe_allow_html=True)
        st.write("")
        dream["text"] = st.text_area("Transcription · modifiable", dream["text"], height=120)
        keys = list(services.EMOTIONS)
        dream["emotion"] = st.selectbox(
            "Ce n'est pas ça ? Corrigez l'ambiance",
            keys,
            index=keys.index(dream["emotion"]),
            format_func=lambda k: f"{services.EMOTIONS[k].icon} {services.EMOTIONS[k].label}",
        )
        st.markdown(theme.kpis_html(dream["duration"], dream["elapsed"], dream["cost"]), unsafe_allow_html=True)
        st.caption("L'ambiance décrit le texte du rêve ; ce n'est pas un diagnostic.")
        if st.button("💾 Garder ce rêve dans mon ciel", type="primary", width="stretch"):
            st.session_state.history.insert(0, dict(dream))
            st.session_state.dream = None
            st.toast("Rêve enregistré dans votre historique", icon="🌙")
            st.rerun()


def charts(history: list[dict]) -> None:
    """Affiche la répartition des émotions et leur évolution dans le temps.

    Args:
        history: Rêves enregistrés.
    """
    frame = pd.DataFrame(
        {
            "jour": [item["date"].date() for item in history],
            "émotion": [services.EMOTIONS[item["emotion"]].label for item in history],
        }
    )
    colors = alt.Scale(
        domain=[e.label for e in services.EMOTIONS.values()], range=[e.color for e in services.EMOTIONS.values()]
    )
    donut = (
        alt.Chart(frame)
        .mark_arc(innerRadius=50, outerRadius=85, cornerRadius=6, padAngle=0.03)
        .encode(
            theta="count():Q",
            color=alt.Color("émotion:N", scale=colors, legend=alt.Legend(orient="bottom", title=None)),
            tooltip=["émotion:N", alt.Tooltip("count():Q", title="rêves")],
        )
        .properties(height=260, title="Émotions dominantes")
    )
    timeline = (
        alt.Chart(frame)
        .mark_bar(cornerRadiusTopLeft=6, cornerRadiusTopRight=6, width={"band": 0.7})
        .encode(
            x=alt.X(
                "yearmonthdate(jour):O",
                title=None,
                axis=alt.Axis(format="%d/%m", labelColor="#a7a3c9", labelAngle=0, grid=False),
            ),
            y=alt.Y("count():Q", title=None, axis=alt.Axis(tickMinStep=1, labelColor="#a7a3c9", gridOpacity=0.1)),
            color=alt.Color("émotion:N", scale=colors, legend=None),
            tooltip=[alt.Tooltip("jour:T", format="%d/%m/%Y"), "émotion:N", alt.Tooltip("count():Q", title="rêves")],
        )
        .properties(height=260, title="Évolution dans le temps")
    )
    col_a, col_b = st.columns([1, 1.6], gap="large")
    for column, chart in ((col_a, donut), (col_b, timeline)):
        with column:
            st.altair_chart(
                chart.configure(background="transparent")
                .configure_view(stroke=None)
                .configure_title(color="#ece9ff", font="Fraunces", fontSize=16, anchor="start")
                .configure_legend(labelColor="#ece9ff"),
                width="stretch",
            )


def show_history() -> None:
    """Affiche le tableau de bord et la galerie (simulation de l'espace personnel)."""
    history = st.session_state.history
    st.write("")
    st.subheader(f"Mon ciel de rêves ({len(history)})")
    if not history:
        st.markdown(theme.EMPTY_HTML, unsafe_allow_html=True)
        return

    counts = Counter(item["emotion"] for item in history)
    dominant = services.EMOTIONS[counts.most_common(1)[0][0]]
    with st.container(key="card-dashboard"):
        m1, m2, m3 = st.columns(3)
        m1.metric("Rêves racontés", len(history))
        m2.metric("Ambiance dominante", f"{dominant.icon} {dominant.label}")
        m3.metric("Coût API cumulé", f"{sum(item['cost'] for item in history):.2f} €".replace(".", ","))
        st.write("")
        charts(history)

    labels = {key: f"{emo.icon} {emo.label}" for key, emo in services.EMOTIONS.items() if key in counts}
    chosen = st.pills("Filtrer par ambiance", list(labels), format_func=labels.get, selection_mode="multi")
    visible = [item for item in history if not chosen or item["emotion"] in chosen]
    columns = st.columns(3, gap="medium")
    for index, item in enumerate(visible):
        emotion = services.EMOTIONS[item["emotion"]]
        with columns[index % 3], st.container(key=f"card-dream-{index}"):
            st.image(item["image"], width="stretch")
            st.markdown(
                theme.card_meta_html(emotion, f"{item['date']:%d/%m · %H:%M}", item["text"]), unsafe_allow_html=True
            )


def main() -> None:
    """Point d'entrée de la page."""
    init_state()
    st.markdown(theme.CSS, unsafe_allow_html=True)
    st.markdown(theme.hero_html(), unsafe_allow_html=True)
    pipeline = st.empty()
    pipeline.markdown(theme.pipeline_html(4 if st.session_state.dream else 0), unsafe_allow_html=True)
    delay, fail_stt, fail_img = sidebar()

    _, center, _ = st.columns([1, 3, 1])
    with center:
        audio = audio_input()
        col_go, col_demo = st.columns([2, 1])
        go = col_go.button("✨ Donner vie à mon rêve", type="primary", disabled=audio is None, width="stretch")
        demo = col_demo.button("🎲 Rêve d'exemple", width="stretch", help="Lance la démo sans micro")
        if demo:
            st.session_state.demo_count += 1
            audio = ("exemple.wav", services.demo_wav(seconds=1.0 + 0.25 * st.session_state.demo_count))
        if audio is not None and (go or demo):
            process(*audio, delay, fail_stt, fail_img, pipeline)

    show_result()
    show_history()
    st.markdown(theme.FOOTER_HTML, unsafe_allow_html=True)


main()
