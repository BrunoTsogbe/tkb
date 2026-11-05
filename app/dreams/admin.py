"""Administration des rêves et des émotions."""

from django.contrib import admin

from .models import Dream, Emotion


@admin.register(Emotion)
class EmotionAdmin(admin.ModelAdmin):
    """Référentiel des émotions."""

    list_display = ("key", "label", "icon", "color")


@admin.register(Dream)
class DreamAdmin(admin.ModelAdmin):
    """Rêves : métadonnées seulement, le contenu reste privé."""

    list_display = ("id", "user", "status", "emotion", "created_at", "processing_ms", "cost_eur")
    list_filter = ("status", "emotion")
    readonly_fields = ("id", "created_at", "updated_at", "audio_deleted_at")
    exclude = ("transcript", "image_prompt")
