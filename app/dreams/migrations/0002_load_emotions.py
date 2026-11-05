"""Charge le référentiel des cinq émotions (couleurs de la charte UX)."""

from django.db import migrations

EMOTIONS = [
    ("heureux", "Heureux", "😊", "#fbbf24"),
    ("stressant", "Stressant", "😰", "#f43f5e"),
    ("triste", "Triste", "😢", "#60a5fa"),
    ("etrange", "Étrange", "🌀", "#c084fc"),
    ("neutre", "Neutre", "😐", "#94a3b8"),
]


def load(apps, schema_editor):
    """Crée ou met à jour les émotions de référence."""
    Emotion = apps.get_model("dreams", "Emotion")
    for key, label, icon, color in EMOTIONS:
        Emotion.objects.update_or_create(key=key, defaults={"label": label, "icon": icon, "color": color})


def unload(apps, schema_editor):
    """Supprime les émotions de référence."""
    apps.get_model("dreams", "Emotion").objects.filter(key__in=[e[0] for e in EMOTIONS]).delete()


class Migration(migrations.Migration):
    dependencies = [("dreams", "0001_initial")]
    operations = [migrations.RunPython(load, unload)]
