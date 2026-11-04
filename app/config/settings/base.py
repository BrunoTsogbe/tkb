"""Réglages communs à tous les environnements.

Toute valeur sensible ou propre à un environnement est lue dans les variables
d'environnement (fichier ``.env`` à la racine du dépôt en local).
"""

from __future__ import annotations

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = BASE_DIR.parent

env = environ.Env()
environ.Env.read_env(REPO_DIR / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-insecure-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "accounts",
    "dreams",
    "ai",
    "dashboard",
    "core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}

AUTH_USER_MODEL = "accounts.User"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 12}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "dreams:record"
LOGOUT_REDIRECT_URL = "accounts:login"

LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Europe/Paris"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "media/"
MEDIA_ROOT = env.path("MEDIA_ROOT", default=BASE_DIR / "media")
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Uploads : la limite de l'API de transcription est de 25 Mo par fichier.
AUDIO_MAX_BYTES = env.int("AUDIO_MAX_BYTES", default=25 * 1024 * 1024)
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024

# Règles métier (dossier de cadrage, KAN-23).
DAILY_DREAM_LIMIT = env.int("DAILY_DREAM_LIMIT", default=5)
CONSENT_VERSION = "1.0"
API_BUDGET_EUR = env.float("API_BUDGET_EUR", default=20.0)

# Fournisseurs d'IA (KAN-21) : « fake » par défaut, aucun appel payant sans configuration explicite.
AI_STT_PROVIDER = env("AI_STT_PROVIDER", default="fake")
AI_IMAGE_PROVIDER = env("AI_IMAGE_PROVIDER", default="fake")
AI_EMOTION_PROVIDER = env("AI_EMOTION_PROVIDER", default="keywords")
OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_BASE_URL = env("OPENAI_BASE_URL", default="https://api.openai.com/v1")
OPENAI_STT_MODEL = env("OPENAI_STT_MODEL", default="gpt-transcribe")
OPENAI_IMAGE_MODEL = env("OPENAI_IMAGE_MODEL", default="gpt-image-1-mini")
EMOTION_HF_MODEL = env("EMOTION_HF_MODEL", default="MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7")
AI_STT_TIMEOUT_S = env.float("AI_STT_TIMEOUT_S", default=60.0)
AI_IMAGE_TIMEOUT_S = env.float("AI_IMAGE_TIMEOUT_S", default=90.0)
AI_STT_RETRIES = env.int("AI_STT_RETRIES", default=2)
AI_IMAGE_RETRIES = env.int("AI_IMAGE_RETRIES", default=1)
AI_BACKOFF_S = env.float("AI_BACKOFF_S", default=2.0)

# Grille tarifaire (benchmark.xlsx, novembre 2026).
STT_USD_PER_MIN = env.float("STT_USD_PER_MIN", default=0.0045)
IMAGE_USD = env.float("IMAGE_USD", default=0.011)
EUR_PER_USD = env.float("EUR_PER_USD", default=0.92)

# Celery (KAN-22) : exécution synchrone tant que le worker n'est pas activé.
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=True)
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_DEFAULT_QUEUE = "default"

# Limitation des tentatives de connexion (django-ratelimit).
RATELIMIT_USE_CACHE = "default"
LOGIN_RATE = env("LOGIN_RATE", default="5/15m")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
