#!/usr/bin/env sh
# Installation en une commande (macOS / Linux) : sh scripts/install.sh
# Crée le .env, démarre la pile Docker et charge les données de référence.
set -eu
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  cp .env.example .env
  key=$(python3 -c "import secrets; print(secrets.token_urlsafe(50))")
  sed -i.bak "s|^DJANGO_SECRET_KEY=.*|DJANGO_SECRET_KEY=${key}|" .env && rm -f .env.bak
  echo ".env créé à partir de .env.example (clé secrète générée)."
fi

docker compose up --build -d
echo "Application disponible sur http://localhost:8000 (premier démarrage : quelques minutes)."
echo "Créer un administrateur : docker compose exec web python manage.py createsuperuser"
