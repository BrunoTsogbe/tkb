"""Logs structurés, identifiant de corrélation et Sentry (KAN-12).

Règle absolue : aucun texte de rêve, prompt ou audio ne sort de l'application
par les logs ou par Sentry. Seuls des identifiants, durées et codes y figurent.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from django.http import HttpRequest, HttpResponse

request_id: ContextVar[str] = ContextVar("request_id", default="-")
SENSITIVE_KEYS = {"transcript", "image_prompt", "prompt", "text", "audio", "password", "body", "data", "cookies"}


class RequestIdFilter(logging.Filter):
    """Ajoute l'identifiant de la requête courante à chaque enregistrement."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Complète l'enregistrement.

        Args:
            record: Enregistrement de log.

        Returns:
            Toujours vrai (le filtre n'écarte rien).
        """
        record.request_id = request_id.get()
        return True


class JsonFormatter(logging.Formatter):
    """Une ligne JSON par événement, lisible par Render et les outils de logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Sérialise l'enregistrement.

        Args:
            record: Enregistrement de log.

        Returns:
            Ligne JSON.
        """
        payload: dict[str, Any] = {
            "time": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


class RequestIdMiddleware:
    """Attribue un identifiant à chaque requête (ou reprend ``X-Request-ID``) et le renvoie."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Traite la requête dans le contexte de son identifiant.

        Args:
            request: Requête HTTP.

        Returns:
            La réponse, avec l'en-tête ``X-Request-ID``.
        """
        incoming = request.headers.get("X-Request-ID", "")
        value = incoming if 0 < len(incoming) <= 64 and incoming.replace("-", "").isalnum() else uuid.uuid4().hex
        token = request_id.set(value)
        try:
            response = self.get_response(request)
        finally:
            request_id.reset(token)
        response["X-Request-ID"] = value
        return response


def scrub(value: Any) -> Any:
    """Masque récursivement les champs sensibles d'un événement Sentry.

    Args:
        value: Structure à nettoyer.

    Returns:
        Structure nettoyée.
    """
    if isinstance(value, dict):
        return {k: "[filtré]" if str(k).lower() in SENSITIVE_KEYS else scrub(v) for k, v in value.items()}
    if isinstance(value, list):
        return [scrub(v) for v in value]
    return value


def before_send(event: Any, hint: Any) -> Any:
    """Retire corps de requête, cookies et variables locales sensibles avant envoi à Sentry.

    Args:
        event: Événement Sentry.
        hint: Informations complémentaires (inutilisées).

    Returns:
        L'événement nettoyé.
    """
    request = event.get("request") or {}
    for key in ("data", "cookies", "query_string"):
        request.pop(key, None)
    return scrub(event)


def init_sentry(dsn: str, environment: str, traces_sample_rate: float) -> bool:
    """Active Sentry sur le web et le worker si un DSN est configuré.

    Args:
        dsn: DSN du projet Sentry (vide : désactivé).
        environment: Nom de l'environnement.
        traces_sample_rate: Part des transactions tracées.

    Returns:
        Vrai si Sentry a été initialisé.
    """
    if not dsn:
        return False
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=traces_sample_rate,
        send_default_pii=False,
        include_local_variables=False,
        before_send=before_send,
    )
    return True
