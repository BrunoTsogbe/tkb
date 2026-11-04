"""Réglages des tests : rapides, isolés, sans service externe."""

from .base import *  # noqa: F403

DEBUG = False
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
CELERY_TASK_ALWAYS_EAGER = True
AI_STT_PROVIDER = AI_IMAGE_PROVIDER = "fake"
AI_EMOTION_PROVIDER = "keywords"
OPENAI_API_KEY = "sk-test"
AI_BACKOFF_S = 0.0
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
STORAGES["staticfiles"] = {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}  # noqa: F405
MIDDLEWARE = [m for m in MIDDLEWARE if "whitenoise" not in m]  # noqa: F405
