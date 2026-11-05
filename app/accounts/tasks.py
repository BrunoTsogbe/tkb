"""Envoi d'e-mails en tâche de fond (le web ne bloque pas sur le serveur SMTP)."""

from __future__ import annotations

from celery import shared_task
from django.core.mail import EmailMultiAlternatives


@shared_task(name="accounts.send_email", autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_email_task(subject: str, body: str, to: str, html: str | None = None) -> None:
    """Envoie un e-mail transactionnel.

    Args:
        subject: Objet.
        body: Texte brut.
        to: Destinataire.
        html: Version HTML facultative.
    """
    message = EmailMultiAlternatives(subject, body, to=[to])
    if html:
        message.attach_alternative(html, "text/html")
    message.send()
