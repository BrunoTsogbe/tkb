"""Formulaire de dépôt d'un rêve audio."""

from __future__ import annotations

from django import forms

from .audio import AudioInfo, validate_audio


class AudioUploadForm(forms.Form):
    """Dépôt d'un enregistrement (micro du navigateur ou fichier)."""

    audio = forms.FileField(label="Enregistrement")

    def clean_audio(self) -> object:
        """Valide le fichier et mémorise ses caractéristiques.

        Returns:
            Le fichier déposé.
        """
        upload = self.cleaned_data["audio"]
        data = upload.read()
        upload.seek(0)
        self.audio_info: AudioInfo = validate_audio(upload.name or "", data)
        return upload
