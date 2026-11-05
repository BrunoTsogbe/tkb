"""Filtres de l'historique et du tableau de bord (KAN-24, US-13).

Les filtres sont lus dans l'URL (``?period=30&emotion=stressant``) : le lien se
partage et le bouton « retour » du navigateur fonctionne.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta

from django import forms
from django.utils import timezone

from .models import DreamQuerySet, Emotion

PERIODS = {"7": 7, "30": 30}


class DreamFilterForm(forms.Form):
    """Période (raccourci ou dates) et émotions, combinables."""

    period = forms.ChoiceField(
        label="Période",
        required=False,
        choices=[("", "Tout"), ("7", "7 derniers jours"), ("30", "30 derniers jours")],
    )
    start = forms.DateField(label="Du", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    end = forms.DateField(label="Au", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    emotion = forms.ModelMultipleChoiceField(
        label="Ambiance",
        required=False,
        queryset=Emotion.objects.all(),
        to_field_name="key",
        widget=forms.CheckboxSelectMultiple,
    )

    def clean(self) -> dict:
        """Vérifie la cohérence des dates.

        Returns:
            Les données nettoyées.

        Raises:
            forms.ValidationError: Si la date de début suit la date de fin.
        """
        data = super().clean() or {}
        start, end = data.get("start"), data.get("end")
        if start and end and start > end:
            raise forms.ValidationError("La date de début doit précéder la date de fin.")
        return data

    def date_range(self) -> tuple[datetime | None, datetime | None]:
        """Bornes de la période choisie (dates explicites prioritaires sur le raccourci).

        Returns:
            Début et fin (inclusifs, fuseau courant), ``None`` si non bornés.
        """
        data = self.cleaned_data if self.is_valid() else {}
        start: date | None = data.get("start")
        end: date | None = data.get("end")
        if not start and not end and data.get("period") in PERIODS:
            start = timezone.localdate() - timedelta(days=PERIODS[data["period"]] - 1)
        tz = timezone.get_current_timezone()
        low = datetime.combine(start, time.min, tz) if start else None
        high = datetime.combine(end, time.max, tz) if end else None
        return low, high

    def apply(self, queryset: DreamQuerySet) -> DreamQuerySet:
        """Applique les filtres valides ; des filtres invalides sont ignorés.

        Args:
            queryset: Rêves de l'utilisateur.

        Returns:
            Les rêves filtrés.
        """
        if not self.is_valid():
            return queryset
        low, high = self.date_range()
        if low:
            queryset = queryset.filter(created_at__gte=low)
        if high:
            queryset = queryset.filter(created_at__lte=high)
        if self.cleaned_data.get("emotion"):
            queryset = queryset.filter(emotion__in=self.cleaned_data["emotion"])
        return queryset

    @property
    def is_filtered(self) -> bool:
        """Vrai si au moins un filtre est actif."""
        return self.is_bound and any(self.data.get(name) for name in ("period", "start", "end", "emotion"))
