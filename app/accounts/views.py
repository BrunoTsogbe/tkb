"""Inscription, connexion (limitée en fréquence) et déconnexion."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from django_ratelimit.decorators import ratelimit

from core.auth import current_user
from dreams.models import Dream
from dreams.serializers import dream_to_dict

from .forms import DeleteAccountForm, EmailAuthenticationForm, SignupForm


def signup(request: HttpRequest) -> HttpResponse:
    """Crée un compte, enregistre le consentement éventuel et connecte l'utilisateur.

    Args:
        request: Requête HTTP.

    Returns:
        Le formulaire (GET ou erreurs) ou une redirection vers l'accueil.
    """
    if request.user.is_authenticated:
        return redirect(settings.LOGIN_REDIRECT_URL)
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        if form.cleaned_data["ai_consent"]:
            user.profile.give_consent()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        messages.success(request, "Bienvenue ! Votre compte est créé.")
        return redirect(settings.LOGIN_REDIRECT_URL)
    return render(request, "accounts/signup.html", {"form": form})


@login_required
@require_POST
def consent(request: HttpRequest) -> HttpResponse:
    """Donne ou retire le consentement à l'envoi vers les prestataires d'IA (KAN-36).

    Args:
        request: Requête HTTP (champ ``action`` : ``give`` ou ``withdraw``).

    Returns:
        Redirection vers la page d'origine ou l'accueil.
    """
    profile = current_user(request).profile
    if request.POST.get("action") == "withdraw":
        profile.withdraw_consent()
        messages.info(request, "Consentement retiré : l'enregistrement de nouveaux rêves est désactivé.")
    else:
        profile.give_consent()
        messages.success(request, "Merci ! Vous pouvez maintenant raconter vos rêves.")
    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = settings.LOGIN_REDIRECT_URL
    return redirect(next_url)


@login_required
@require_GET
def account(request: HttpRequest) -> HttpResponse:
    """Page « Mon compte » : consentement, export, suppression.

    Args:
        request: Requête HTTP.

    Returns:
        La page du compte.
    """
    user = current_user(request)
    return render(request, "accounts/account.html", {"profile": user.profile, "delete_form": DeleteAccountForm(user)})


@login_required
@require_GET
def export(request: HttpRequest) -> JsonResponse:
    """Exporte tous les rêves de l'utilisateur en JSON (portabilité RGPD, KAN-38, US-17).

    Args:
        request: Requête HTTP.

    Returns:
        Fichier JSON en pièce jointe, conforme à ``dream.schema.json`` pour chaque rêve.
    """
    user = current_user(request)
    dreams = Dream.objects.for_user(user).select_related("emotion").order_by("created_at")
    payload = {
        "exported_at": timezone.now().isoformat(),
        "account": {"email": user.email, "date_joined": user.date_joined.isoformat()},
        "dreams": [dream_to_dict(dream) for dream in dreams],
    }
    response = JsonResponse(payload, json_dumps_params={"ensure_ascii": False, "indent": 2})
    response["Content-Disposition"] = f'attachment; filename="mes-reves-{timezone.localdate():%Y-%m-%d}.json"'
    return response


@login_required
@require_POST
def delete_account(request: HttpRequest) -> HttpResponse:
    """Supprime le compte, les rêves et leurs fichiers (KAN-15, US-03).

    Le journal des coûts est conservé sans lien avec la personne (``user_id`` à NULL).

    Args:
        request: Requête HTTP (``confirm`` et ``password``).

    Returns:
        Redirection vers l'inscription, ou la page du compte avec les erreurs.
    """
    user = current_user(request)
    form = DeleteAccountForm(user, request.POST)
    if not form.is_valid():
        return render(request, "accounts/account.html", {"profile": user.profile, "delete_form": form}, status=400)
    logout(request)
    user.delete()
    messages.success(request, "Votre compte et tous vos rêves ont été supprimés.")
    return redirect("accounts:signup")


@method_decorator(ratelimit(key="ip", rate=settings.LOGIN_RATE, method="POST", block=False), name="post")
class RateLimitedLoginView(LoginView):
    """Connexion par e-mail, refusée après trop de tentatives."""

    form_class = EmailAuthenticationForm
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def post(self, request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Refuse la tentative si la limite est atteinte.

        Args:
            request: Requête HTTP.
            *args: Arguments positionnels de la vue.
            **kwargs: Arguments nommés de la vue.

        Returns:
            La réponse de connexion, ou le formulaire avec un message (HTTP 429).
        """
        if getattr(request, "limited", False):
            form = self.get_form()
            form.add_error(None, "Trop de tentatives. Réessayez dans quelques minutes.")
            return self.render_to_response(self.get_context_data(form=form), status=429)
        return super().post(request, *args, **kwargs)
