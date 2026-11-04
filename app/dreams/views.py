"""Raconter un rêve : page d'enregistrement, dépôt de l'audio, détail."""

from __future__ import annotations

from uuid import UUID

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST

from core.auth import current_user

from .forms import AudioUploadForm
from .models import Dream
from .services import quota_for


def _wants_json(request: HttpRequest) -> bool:
    return "application/json" in request.headers.get("Accept", "")


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
@require_POST
def create(request: HttpRequest) -> HttpResponse:
    """Dépose un audio : contrôle du consentement, du quota, puis du fichier.

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
    """Affiche un rêve de l'utilisateur connecté (404 pour un rêve d'un autre utilisateur).

    Args:
        request: Requête HTTP.
        pk: Identifiant du rêve.

    Returns:
        La page du rêve.
    """
    dream = get_object_or_404(Dream.objects.for_user(current_user(request)).select_related("emotion"), pk=pk)
    return render(request, "dreams/detail.html", {"dream": dream})
