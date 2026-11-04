"""Journal des appels API en lecture seule (supervision des coûts)."""

from django.contrib import admin
from django.http import HttpRequest

from .models import APICallLog


@admin.register(APICallLog)
class APICallLogAdmin(admin.ModelAdmin):
    """Le journal est une preuve : il ne se modifie pas depuis l'admin."""

    list_display = ("created_at", "kind", "provider", "model", "status", "attempt", "latency_ms", "cost_eur")
    list_filter = ("kind", "provider", "status")
    date_hierarchy = "created_at"

    def has_add_permission(self, request: HttpRequest) -> bool:  # noqa: D102
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:  # noqa: D102
        return False
