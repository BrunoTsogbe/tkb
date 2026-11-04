"""Rêves : raconter, suivre, corriger, réessayer, historique, image privée."""

from __future__ import annotations

from uuid import UUID

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import FileResponse, Http404, HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.auth import current_user

from .forms import AudioUploadForm, DreamEditForm
from .models import Dream, Emotion
from .services import quota_for
from .tasks import process_dream_task

HISTORY_PAGE_SIZE = 20


def _wants_json(request: HttpRequest) -> bool:
    return "application/json" in request.headers.get("Accept", "")


def _own_dream(request: HttpRequest, pk: UUID) -> Dream:
    queryset = Dream.objects.for_user(current_user(request)).select_related("emotion")
    return get_object_or_404(queryset, pk=pk)


def _enqueue(dream: Dream) -> None:
    transaction.on_commit(lambda: process_dream_task.delay(str(dream.id)))


def _record_page(request: HttpRequest, form: AudioUploadForm, status: int = 200) -> HttpResponse:
    user = current_user(request)
    context = {"form": form, "quota": quota_for(user), "has_consent": user.profile.has_ai_consent}
    return render(request, "dreams/record.html", context, status=status)


@login_required
@require_GET
def record(request: HttpRequest) -> HttpResponse:
    """Affiche l'enregistreur et le formulaire d'import.

    Args:
        request: Requête HTTP.

    Returns:
        La page « Raconter ».
    """
    return _record_page(request, AudioUploadForm())


@login_required
@require_http_methods(["GET", "POST"])
def collection(request: HttpRequest) -> HttpResponse:
    """``GET /dreams/`` : historique ; ``POST /dreams/`` : dépôt d'un rêve.

    Args:
        request: Requête HTTP.

    Returns:
        L'historique paginé, ou la réponse au dépôt.
    """
    return create(request) if request.method == "POST" else history(request)


def history(request: HttpRequest) -> HttpResponse:
    """Historique paginé, du plus récent au plus ancien (KAN-14, US-12).

    Args:
        request: Requête HTTP (paramètre ``page``).

    Returns:
        La page d'historique.
    """
    dreams = Dream.objects.for_user(current_user(request)).select_related("emotion")
    page = Paginator(dreams, HISTORY_PAGE_SIZE).get_page(request.GET.get("page"))
    return render(request, "dreams/history.html", {"page": page})


def create(request: HttpRequest) -> HttpResponse:
    """Dépose un audio : consentement, quota, fichier, puis mise en file du traitement.

    Les contrôles sont faits avant tout stockage ; un refus ne laisse aucun fichier.

    Args:
        request: Requête HTTP multipart (champ ``audio``).

    Returns:
        202 + redirection vers le suivi si le dépôt est accepté ; 403, 429 ou 400 sinon.
    """
    user = current_user(request)
    form = AudioUploadForm(request.POST, request.FILES)
    if not user.profile.has_ai_consent:
        message, status = "Donnez votre consentement pour enregistrer un rêve.", 403
    elif quota_for(user).exhausted:
        message, status = "Vous avez atteint votre limite de rêves pour aujourd'hui. Revenez demain !", 429
    elif not form.is_valid():
        message, status = str(form.errors.get("audio", ["Fichier invalide."])[0]), 400
    else:
        info = form.audio_info
        dream = Dream(user=user, audio_format=info.format, audio_duration_s=info.duration_s)
        dream.audio_file.save(f"{dream.id}.{info.format}", form.cleaned_data["audio"], save=False)
        dream.save()
        _enqueue(dream)
        url = reverse("dreams:detail", args=[dream.id])
        if _wants_json(request):
            return JsonResponse({"id": str(dream.id), "redirect": url}, status=202)
        return redirect(url)

    if _wants_json(request):
        return JsonResponse({"error": message}, status=status)
    if status != 400:
        form.add_error(None, message)
    return _record_page(request, form, status=status)


@login_required
@require_GET
def detail(request: HttpRequest, pk: UUID) -> HttpResponse:
    """Page d'un rêve : suivi en direct puis résultat corrigeable.

    Args:
        request: Requête HTTP.
        pk: Identifiant du rêve.

    Returns:
        La page du rêve (404 pour un rêve d'un autre utilisateur).
    """
    dream = _own_dream(request, pk)
    form = DreamEditForm(initial={"transcript": dream.transcript, "emotion": dream.emotion_id})
    return render(request, "dreams/detail.html", {"dream": dream, "form": form, "emotions": Emotion.objects.all()})


@login_required
@require_GET
def status(request: HttpRequest, pk: UUID) -> HttpResponse:
    """Fragment de suivi, interrogé toutes les 2 s par la page du rêve.

    Args:
        request: Requête HTTP.
        pk: Identifiant du rêve.

    Returns:
        Le fragment HTML de l'avancement.
    """
    return render(request, "dreams/_status.html", {"dream": _own_dream(request, pk)})


@login_required
@require_POST
def edit(request: HttpRequest, pk: UUID) -> HttpResponse:
    """Corrige la transcription et/ou l'ambiance (KAN-18, KAN-19).

    Args:
        request: Requête HTTP (champs ``transcript`` et ``emotion``).
        pk: Identifiant du rêve.

    Returns:
        Redirection vers la page du rêve.
    """
    dream = _own_dream(request, pk)
    form = DreamEditForm(request.POST)
    if not dream.is_finished or not form.is_valid():
        messages.error(request, "La correction n'a pas pu être enregistrée.")
        return redirect("dreams:detail", pk=dream.id)
    text, emotion = form.cleaned_data["transcript"].strip(), form.cleaned_data["emotion"]
    if text and text != dream.transcript:
        dream.transcript, dream.transcript_edited = text, True
    if emotion and emotion != dream.emotion:
        dream.emotion, dream.emotion_corrected = emotion, True
    dream.save(update_fields=["transcript", "transcript_edited", "emotion", "emotion_corrected", "updated_at"])
    messages.success(request, "Vos corrections sont enregistrées.")
    return redirect("dreams:detail", pk=dream.id)


@login_required
@require_POST
def retry(request: HttpRequest, pk: UUID) -> HttpResponse:
    """Relance un rêve en échec à partir de l'étape échouée.

    Args:
        request: Requête HTTP.
        pk: Identifiant du rêve.

    Returns:
        Redirection vers la page du rêve.
    """
    dream = _own_dream(request, pk)
    if dream.status == Dream.Status.FAILED:
        dream.status = Dream.Status.RECEIVED
        dream.save(update_fields=["status", "updated_at"])
        _enqueue(dream)
    return redirect("dreams:detail", pk=dream.id)


@login_required
@require_GET
def image(request: HttpRequest, pk: UUID) -> FileResponse:
    """Sert l'image d'un rêve à son seul propriétaire (jamais par une URL publique).

    Args:
        request: Requête HTTP.
        pk: Identifiant du rêve.

    Returns:
        Le fichier PNG.

    Raises:
        Http404: Si le rêve n'a pas d'image ou appartient à un autre utilisateur.
    """
    dream = _own_dream(request, pk)
    if not dream.image_file:
        raise Http404("Pas encore d'image.")
    response = FileResponse(dream.image_file.open("rb"), content_type="image/png")
    response["Cache-Control"] = "private, max-age=3600"
    return response
