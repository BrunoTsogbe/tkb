"""Formulaires d'inscription et de connexion."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import User


class SignupForm(UserCreationForm):
    """Inscription : e-mail, mot de passe, consentement IA et conditions."""

    ai_consent = forms.BooleanField(
        required=False,
        label=(
            "J'accepte que ma voix et le texte de mes rêves soient envoyés à des prestataires d'IA "
            "(OpenAI, hors Union européenne) pour la transcription et l'illustration."
        ),
        help_text="Facultatif : sans ce consentement, l'enregistrement de rêves reste désactivé.",
    )
    terms = forms.BooleanField(
        required=True,
        label="J'accepte les conditions d'utilisation et la politique de confidentialité.",
    )

    class Meta:
        model = User
        fields = ("email",)

    def clean_email(self) -> str:
        """Normalise l'e-mail et refuse les doublons.

        Returns:
            L'adresse en minuscules.

        Raises:
            forms.ValidationError: Si un compte existe déjà.
        """
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Un compte existe déjà avec cette adresse.")
        return email


class EmailAuthenticationForm(AuthenticationForm):
    """Connexion par e-mail."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Adresse e-mail"
        self.fields["username"].widget = forms.EmailInput(attrs={"autofocus": True, "autocomplete": "email"})
