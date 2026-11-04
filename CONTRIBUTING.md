# Contribuer

## Branches et commits

- `main` est protégée : aucun push direct, une PR relue et une CI verte sont obligatoires.
- Une branche par ticket : `feat/KAN-17-enregistrement-audio`, `fix/KAN-42-quota`, `docs/KAN-30-readme`.
- Chaque message de commit cite son ticket : `KAN-17 Valide la signature des fichiers audio`.

## Avant d'ouvrir une PR

```bash
ruff check . && ruff format --check .
mypy
pytest app/tests --cov=app --cov-fail-under=70
```

Remplir le modèle de PR (`.github/pull_request_template.md`) et cocher la checklist d'auto-revue.

## Définition de « terminé »

Code relu (checklist de PR), CI verte, couverture ≥ 70 % maintenue, docstrings Google, aucune clé
en clair, ticket Jira à jour.

## Protection de `main` (réglage GitHub, une seule fois)

Settings → Branches → Add branch ruleset : cible `main`, cocher *Require a pull request before
merging*, *Require status checks to pass* (jobs `Lint, typage, audit`, `Tests (PostgreSQL,
couverture ≥ 70 %)`, `Construction de l'image`) et *Block force pushes*.
