# Installation en une commande (Windows) : .\scripts\install.ps1
# Crée le .env, démarre la pile Docker et charge les données de référence.
$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    $key = -join ((48..57) + (65..90) + (97..122) | Get-Random -Count 64 | ForEach-Object { [char]$_ })
    (Get-Content .env) -replace '^DJANGO_SECRET_KEY=.*', "DJANGO_SECRET_KEY=$key" | Set-Content .env -Encoding utf8
    Write-Host ".env créé à partir de .env.example (clé secrète générée)."
}

docker compose up --build -d
Write-Host "Application disponible sur http://localhost:8000 (premier démarrage : quelques minutes)."
Write-Host "Créer un administrateur : docker compose exec web python manage.py createsuperuser"
