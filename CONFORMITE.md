# Conformité au sujet (état au 5 novembre 2026)

Relecture exigence par exigence des deux énoncés du dossier `sujet/`.
Légende : ✅ fait et vérifié · 🟡 fait, mais non vérifié en conditions réelles · ❌ à faire.

## Bloc 3 – Production

### 3.1 Application fonctionnelle

| Exigence | État | Preuve / remarque |
|---|---|---|
| Stack Django + BDD SQL | ✅ | Django 5.2 LTS, PostgreSQL 16 (Docker), SQLite en développement |
| Bootstrap ou Tailwind (recommandé) | 🟡 | Feuille de style maison (charte UX) ; Tailwind prévu par KAN-26, non intégré. Recommandation, pas obligation |
| Authentification, espace utilisateur, historique | ✅ | Inscription / connexion par e-mail, historique paginé et filtrable, isolation testée (404) |
| Enregistrement audio | 🟡 | Import de fichier vérifié dans le navigateur et sur Docker ; l'enregistreur micro (MediaRecorder) n'a pas été essayé avec un vrai micro |
| Transcription (Whisper / OpenAI ou équivalent) | 🟡 | OpenAI `gpt-transcribe` implémenté et testé avec un serveur simulé ; **aucun appel réel** (clé requise, KAN-39) |
| Classification émotionnelle (NLTK, Hugging Face…) | 🟡 | Par défaut : classifieur par mots-clés (repli). Le modèle **Hugging Face** zero-shot est implémenté mais **jamais exécuté** : `transformers` n'est pas installé. À activer et évaluer (KAN-39) |
| Génération d'image (Stable Diffusion / DALL-E) | 🟡 | OpenAI `gpt-image-1-mini` (famille DALL-E / GPT Image) implémenté et testé avec un serveur simulé ; **aucun appel réel** |
| Micro-vidéo + ambiance sonore (bonus) | ❌ | KAN-35, backlog (Could) |
| Tableau de bord : filtres date / humeur, fréquences, émotions dominantes | ✅ | `/dashboard/` vérifié dans le navigateur |
| CI/CD : tests, lint, build, déploiement automatisé | 🟡 | `.github/workflows/ci.yml` et `deploy.yml` écrits ; **jamais exécutés sur GitHub** (PR non ouvertes) ; Render non configuré |
| README complet + script d'installation (Docker / venv + .env) | ✅ | `README.md`, `scripts/install.ps1` / `install.sh`, `.env.example` ; pile Docker validée de bout en bout |

### 3.2 à 3.4 Livrables écrits et oraux

| Exigence | État | Remarque |
|---|---|---|
| Rapport technique `rapport_<groupe>.pdf` | ✅ | `rapport_tsogbe.pdf` (sources `rapport/`, régénérer : `python rapport/build.py`) ; à refaire après KAN-39 avec les latences réelles |
| Post-mortem `postmortem_<prenom>.pdf` | 🟡 | KAN-32. Trame `docs/postmortem.html` pré-remplie (faits, points forts / faibles, améliorations) ; encadrés « À rédiger » pour l'auteur, puis `python docs/build_pdf.py docs/postmortem.html postmortem_bruno.pdf` |
| Code review live (15 min) | ✅ | KAN-33. Déroulé, bug `packaging` (avant / après, méthode de débogage) et questions probables : `docs/revue_de_code.md` |
| Accès au dépôt GitHub et au suivi Jira | ✅ | github.com/BrunoTsogbe/tkb (privé : donner l'accès au jury) · projet Jira KAN |

### 4. Contraintes techniques

| Contrainte | État | Preuve |
|---|---|---|
| Python (Django) | ✅ | Python 3.12 dans l'image Docker et la CI |
| Déploiement Heroku / Render / Docker Compose local | ✅ / 🟡 | **Docker Compose local validé** (`scripts/smoke_test.py`, 10 étapes) ; Render : blueprint prêt, non déployé |
| Budget API ≤ 20 € | ✅ | Garde-fous 80 / 95 / 100 % testés ; mode démo gratuit par défaut |
| Couverture ≥ 70 % des fonctionnalités critiques | ✅ | 115 tests de l'application, 98 % de couverture de `app/` ; seuil bloquant en CI |
| PEP 8, docstrings Google | ✅ | ruff (convention Google) et mypy sans erreur |
| Branches Git avec PR | 🟡 | Une branche par lot de tickets ; **PR à ouvrir et fusionner** (dans l'ordre Sprint 1 → 4) |

### 6. Grille d'évaluation

| Axe | État | Remarque |
|---|---|---|
| Fonctionnalités | 🟡 | Tout est en place, sauf le bonus ; les APIs réelles restent à valider |
| Qualité du code | ✅ | Structure par apps, interfaces de fournisseurs, docstrings, typage |
| Intégration des outils IA (timeout, quota…) | ✅ | Délais, relances, `Retry-After`, coupe-circuit, journal des coûts, image de secours |
| Tests et validation (couverture, charge, stratégie) | ✅ | 159 tests ; charge 5 / 20 / 50 utilisateurs sur Docker sans échec (`loadtest/README.md`) |
| CI/CD, config d'environnement, monitoring, logs | 🟡 | Logs JSON, Sentry, `/healthz/`, `/supervision/` ; pipelines non encore exécutés |
| Performance (temps de réponse, latence API, UX) | 🟡 | Pages p95 ≤ 190 ms à 50 utilisateurs ; latence réelle des APIs non mesurée (KAN-39) |
| Documentation (schémas mis à jour) | ✅ | Rapport technique §1 : conteneurs mis à jour et tableau des écarts |

## Blocs 1 et 2 – Pré-production

| Exigence | État | Livrable |
|---|---|---|
| §5 Analyse d'impact RGPD (KAN-40) | ✅ | `aipd_synthetiseur.pdf` (2 p., méthode CNIL allégée ; sources `docs/aipd.html`) |
| 5.1 Dossier de cadrage (≤ 15 p.) | ✅ | `dossier_cadrage.pdf` (7 p.) et `dossier_cadrage_v1.1.pdf` (8 p.) |
| 5.2 Spécifications et architecture (≤ 10 p.) | ✅ | `specifications_architecture.pdf` (10 p.) |
| 5.3 Maquette Streamlit, vidéo ≤ 3 min, README | ✅ | `maquette/`, `maquette/demo/demo_maquette.mp4` (83 s, sans voix off) |
| 5.4 `benchmark.xlsx`, scripts pytest | ✅ | Temps de réponse encore « à mesurer » (KAN-39) |
| §6 Wireframes Figma, charte, flow diagram | 🟡 | `ux_wireframes.pdf` ; dessinés en code, **pas dans Figma** |
| §6 Script de latence, coût sur 10 rêves/jour | ✅ / 🟡 | `benchmark_latency.py` prêt ; jamais lancé sur les vraies APIs |
| §6 Tickets Jira pour la production | ✅ | 68 tickets (épics, critères d'acceptation, sous-tâches) |

## Écarts entre l'architecture prévue et l'application livrée

À reporter dans le rapport technique (« architecture finale mise à jour ») :

1. **Stockage S3 compatible** ajouté : sur Render, le web et le worker ne partagent pas de disque.
2. **Graphiques en SVG côté serveur** au lieu de Chart.js : pas de JavaScript tiers, tableau accessible.
3. **Suivi en direct par un script de 30 lignes** au lieu de HTMX : même comportement, aucune dépendance.
4. **Feuille de style maison** au lieu de Tailwind.
5. **Émotion** : classifieur par mots-clés par défaut, Hugging Face en option.
6. **Bugs révélés par la pile Docker** et corrigés : dépendance `packaging` manquante pour Celery/Redis,
   pipeline exécuté par le web au lieu du worker, cookies « Secure » bloquant la connexion en HTTP local,
   dossier de travail de Gunicorn non inscriptible.

## Ce qui reste à faire, par priorité

1. **KAN-39** (clé OpenAI requise, moins de 0,50 €) : premiers appels réels de transcription et d'image,
   mesure des latences, activation et évaluation du modèle Hugging Face.
2. **Ouvrir et fusionner les PR**, vérifier que la CI passe sur GitHub.
3. **KAN-32** post-mortem : compléter les encadrés « À rédiger » de `docs/postmortem.html` (auto-évaluation personnelle).
4. Actions de l'AIPD avant mise en production : contrats de sous-traitance (DPA), politique de confidentialité.
5. Optionnel : déploiement Render, Tailwind (KAN-26), bonus voix / vidéo (KAN-35).
