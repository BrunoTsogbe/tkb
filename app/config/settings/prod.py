"""Réglages de production (Render ou Docker Compose)."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False
SECRET_KEY = env("DJANGO_SECRET_KEY")

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
# Désactivable uniquement pour Docker Compose en local (HTTP sur localhost).
SESSION_COOKIE_SECURE = env.bool("DJANGO_SECURE_COOKIES", default=True)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
X_FRAME_OPTIONS = "DENY"

LOGGING["handlers"]["console"]["formatter"] = env("LOG_FORMAT", default="json")  # type: ignore[index]  # noqa: F405

from core.observability import init_sentry  # noqa: E402

init_sentry(SENTRY_DSN, SENTRY_ENVIRONMENT, SENTRY_TRACES_SAMPLE_RATE)  # noqa: F405
