"""Formulaires d'inscription et de connexion."""

from __future__ import annotations

from typing import Any

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, UserCreationForm
from django.template import loader

from .models import User
from .tasks import send_email_task

DELETE_WORD = "SUPPRIMER"


class AsyncPasswordResetForm(PasswordResetForm):
    """Réinitialisation du mot de passe : e-mail envoyé par le worker (KAN-37)."""

    def send_mail(
        self,
        subject_template_name: str,
        email_template_name: str,
        context: dict[str, Any],
        from_email: str | None,
        to_email: str,
        html_email_template_name: str | None = None,
    ) -> None:
        """Met l'e-mail en file au lieu de l'envoyer pendant la requête.

        Args:
            subject_template_name: Gabarit de l'objet.
            email_template_name: Gabarit du texte.
            context: Contexte (lien signé à usage unique).
            from_email: Expéditeur (réglage par défaut si ``None``).
            to_email: Destinataire.
            html_email_template_name: Gabarit HTML facultatif.
        """
        subject = "".join(loader.render_to_string(subject_template_name, context).splitlines())
        body = loader.render_to_string(email_template_name, context)
        send_email_task.delay(subject, body, to_email)


class DeleteAccountForm(forms.Form):
    """Confirmation renforcée de la suppression du compte (wireframe « Compte »)."""

    confirm = forms.CharField(label=f"Saisissez {DELETE_WORD} pour confirmer", max_length=20)
    password = forms.CharField(label="Votre mot de passe", widget=forms.PasswordInput)

    def __init__(self, user: User, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_confirm(self) -> str:
        """Exige le mot de confirmation exact.

        Returns:
            Le mot saisi.

        Raises:
            forms.ValidationError: Si le mot ne correspond pas.
        """
        value = self.cleaned_data["confirm"].strip()
        if value != DELETE_WORD:
            raise forms.ValidationError(f"Saisissez exactement {DELETE_WORD}.")
        return value

    def clean_password(self) -> str:
        """Vérifie le mot de passe actuel.

        Returns:
            Le mot de passe saisi.

        Raises:
            forms.ValidationError: Si le mot de passe est faux.
        """
        password = self.cleaned_data["password"]
        if not self.user.check_password(password):
            raise forms.ValidationError("Mot de passe incorrect.")
        return password


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
