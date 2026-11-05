# Synthétiseur de rêves

Raconter un rêve à voix haute et le voir devenir texte, émotion et image, puis suivre l'évolution
de son humeur dans un espace personnel. Ce dépôt réunit les livrables de pré-production
(blocs 1 et 2) et l'application de production (bloc 3, dossier `app/`).

Auteur : Bruno Tsogbe · suivi Jira : projet **KAN** (bruno-tsogbe.atlassian.net)

## Application de production (bloc 3)

Django 5.2 LTS · PostgreSQL 16 · Celery + Redis · Docker Compose · GitHub Actions.

```bash
# Avec Docker (recommandé) : crée .env, construit et démarre web, worker, db, redis
.\scripts\install.ps1          # Windows
sh scripts/install.sh          # macOS / Linux
# → http://localhost:8000 · admin : docker compose exec web python manage.py createsuperuser

# Sans Docker (SQLite, pipeline exécuté de façon synchrone)
pip install -r app/requirements-dev.txt
cd app && python manage.py migrate && python manage.py runserver
```

Qualité : `ruff check . && ruff format --check .` · `mypy` · `pytest app/tests --cov=app --cov-fail-under=70`.
Règles de contribution (branches, PR, définition de terminé) : `CONTRIBUTING.md`.

| Sprint 1 | État |
|---|---|
| KAN-7 Dépôt, modèle de PR, conventions | ✅ fichiers prêts · protection de `main` à activer sur GitHub (`CONTRIBUTING.md`) |
| KAN-8 Projet Django, réglages dev / test / prod, `.env` | ✅ `check --deploy` sans alerte |
| KAN-9 Dockerfile multi-étapes + compose (web, worker, db, redis) | ✅ écrit · à valider avec `docker compose up` |
| KAN-10 CI : ruff, mypy, pip-audit, migrations, tests PostgreSQL, couverture ≥ 70 %, image | ✅ `.github/workflows/ci.yml` |
| KAN-16 Modèles User, Profile, Dream, Emotion, APICallLog + 5 émotions + admin | ✅ |
| KAN-13 Inscription, connexion par e-mail, limitation des tentatives, Argon2 | ✅ |
| KAN-17 Enregistrement micro (MediaRecorder) et import, validation par signature, quota | ✅ |
| KAN-36 (avance) Consentement IA à l'inscription, retrait possible | ✅ |

| Sprint 2 | État |
|---|---|
| KAN-21 Interfaces fournisseurs, délais, relances, `Retry-After`, coupe-circuit, journal des coûts | ✅ `app/ai/` |
| KAN-18 Transcription OpenAI `gpt-transcribe`, audio supprimé ensuite, texte corrigeable | ✅ |
| KAN-19 Ambiance locale (mots-clés, option Hugging Face zero-shot), corrigeable | ✅ |
| KAN-20 Image OpenAI `gpt-image-1-mini`, prompt minimisé, image de secours, garde-fou budget | ✅ |
| KAN-14 Historique paginé, isolé par utilisateur, image servie au seul propriétaire | ✅ |
| Pipeline idempotent + tâche Celery, suivi en direct, « Réessayer » (avance sur KAN-22) | ✅ |
| KAN-39 Spike : latences réelles, DPA, modèle d'émotion | ⏳ nécessite tes clés API |

Par défaut, les fournisseurs sont simulés (`AI_STT_PROVIDER=fake`) : aucune clé, aucun coût. Pour les vrais
appels, renseigner `OPENAI_API_KEY` et passer `AI_STT_PROVIDER` / `AI_IMAGE_PROVIDER` à `openai`.

| Sprint 3 | État |
|---|---|
| KAN-24 Filtres période / émotions, dans l'URL, conservés par la pagination | ✅ |
| KAN-25 Tableau de bord : indicateurs, répartition, évolution (SVG serveur + tableau accessible) | ✅ `/dashboard/` |
| KAN-15 Suppression d'un rêve et du compte, fichiers effacés, coûts anonymisés | ✅ |
| KAN-37 Mot de passe oublié (lien unique 1 h, envoi par le worker) | ✅ |
| KAN-38 Export JSON conforme au schéma | ✅ `/accounts/export/` |
| KAN-12 Logs JSON + identifiant de requête, Sentry filtré, `/healthz/` (file bloquée), `/supervision/` | ✅ |
| KAN-11 Blueprint Render + workflow Deploy (GHCR, deploy hooks, test de fumée) | ✅ écrit · à brancher sur ton compte Render |

Déploiement Render : créer le blueprint depuis `render.yaml`, renseigner les secrets `sync: false`
(clé OpenAI, bucket S3, DSN Sentry, `EMAIL_URL`), puis ajouter dans GitHub les secrets
`RENDER_DEPLOY_HOOK_WEB`, `RENDER_DEPLOY_HOOK_WORKER` et la variable `APP_URL`.

115 tests dédiés à l'application, 159 tests au total.

## Livrables de pré-production

| Exigence du sujet | Livrable | État |
|---|---|---|
| **5.1** Dossier de cadrage (≤ 15 p.) | `dossier_cadrage.pdf` (v1.0, 7 p.) · `dossier_cadrage_v1.1.pdf` (8 p., + page de mise à jour) | ✅ |
| **5.2** Spécifications et architecture (≤ 10 p.) | `specifications_architecture.pdf` (10 p.) · sources dans `architecture/` | ✅ |
| **5.3** Maquette Streamlit | `maquette/` (`streamlit run maquette/app.py`) | ✅ |
| **5.3** Vidéo de démo (≤ 3 min) | `maquette/demo/demo_maquette.mp4` (83 s, sous-titrée) | ✅ |
| **5.3** README d'installation | `maquette/README.md` | ✅ |
| **5.4** Tableau benchmark | `benchmark.xlsx` | ✅ |
| **5.4** Scripts de test prototypaux (pytest) | `maquette/tests/`, `architecture/tests/` (44 tests) | ✅ |
| **§6** Script de mesure de latence | `benchmark_latency.py` (`--dry-run` sans clé) | ✅ |
| **§6** Wireframes, charte, flow diagram | `ux_wireframes.pdf` (6 p.) · sources dans `ux/` | ✅ |
| **§6** Modèle relationnel + schéma JSON | `specifications_architecture.pdf` §2 · `architecture/dream.schema.json` | ✅ |
| **§6** Tickets Jira de production | Projet KAN : 6 epics, 34 tâches, 28 sous-tâches (plan : `jira/plan_jira.md`) | ✅ |

## Installation

Prérequis : Python 3.11 ou 3.12, Microsoft Edge ou Google Chrome (génération des PDF et de la vidéo).

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate    ·    macOS/Linux : source .venv/bin/activate
pip install -r maquette/requirements.txt -r architecture/requirements.txt -r requirements-benchmark.txt
```

## Commandes

```bash
streamlit run maquette/app.py                  # maquette (http://localhost:8501)
pytest --cov=maquette                          # 44 tests, couverture 99 %
ruff check .                                   # PEP 8, imports, docstrings Google
python benchmark_latency.py --dry-run          # mesure de latence simulée (clés : voir .env.example)
python architecture/build.py                   # régénère specifications_architecture.pdf
python ux/build.py                             # régénère ux_wireframes.pdf
python dossier/build_v1_1.py                   # régénère dossier_cadrage_v1.1.pdf
python maquette/demo/record_demo.py            # réenregistre la vidéo (pip install imageio-ffmpeg websockets)
```

## Organisation

```
├── dossier_cadrage.pdf, dossier_cadrage_v1.1.pdf   # 5.1
├── specifications_architecture.pdf                 # 5.2
├── ux_wireframes.pdf                               # §6 UX/UI
├── benchmark.xlsx, benchmark_latency.py            # 5.4 + §6 benchmark
├── maquette/          # 5.3 : app Streamlit, services simulés, thème, tests, vidéo
├── architecture/      # diagrammes en code, gabarit du PDF, schéma JSON, sources PlantUML
├── ux/                # wireframes en code, gabarit du PDF
├── dossier/           # page de mise à jour du dossier de cadrage
├── jira/              # plan appliqué au projet Jira KAN
└── sujet/             # énoncés des blocs 1+2 et 3
```

Les diagrammes et wireframes sont générés en code (`architecture/diagrams.py`, `ux/wireframes.py`) :
ils sont versionnables, relus en PR et toujours cohérents avec les documents. Des sources PlantUML
équivalentes sont fournies dans `architecture/diagrammes/*.puml`.

## Points à valider avant la production

Repris dans le ticket **KAN-39** : latences réelles des APIs, DPA et région UE des fournisseurs,
choix du modèle d'émotion sur 20 textes annotés, tarifs confirmés sur les pages officielles.
