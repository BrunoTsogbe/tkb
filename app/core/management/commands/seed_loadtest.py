"""Prépare les comptes du test de charge (KAN-29)."""

from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from accounts.models import User

PASSWORD = "charge-test-mot-de-passe-42"


class Command(BaseCommand):
    """Crée ``charge1@exemple.fr`` … ``chargeN@exemple.fr``, consentants et sans quota bloquant."""

    help = "Crée les comptes utilisés par loadtest/locustfile.py."

    def add_arguments(self, parser: CommandParser) -> None:
        """Déclare les options.

        Args:
            parser: Analyseur d'arguments.
        """
        parser.add_argument("--users", type=int, default=50)

    def handle(self, *args: Any, **options: Any) -> None:
        """Crée ou réinitialise les comptes de test.

        Args:
            *args: Arguments positionnels.
            **options: Options de la commande.
        """
        for index in range(1, options["users"] + 1):
            user, _ = User.objects.get_or_create(email=f"charge{index}@exemple.fr")
            user.set_password(PASSWORD)
            user.save()
            user.profile.daily_dream_limit = 10_000
            user.profile.save(update_fields=["daily_dream_limit"])
            user.profile.give_consent()
        self.stdout.write(self.style.SUCCESS(f"{options['users']} comptes de test prêts."))
