# Plan de mise à jour du projet Jira KAN

État constaté le 4 novembre 2026 : 35 tickets (6 epics, 29 tâches), descriptions d'une ligne, champ
Priorité resté sur « Medium » pour tous les tickets alors que les descriptions indiquent la vraie
priorité. Ce plan aligne Jira sur le dossier de cadrage et sur `specifications_architecture.pdf`.

**Statut : entièrement appliqué le 4 novembre 2026**, puis vérifié par relecture du projet.
Le projet KAN compte désormais 68 tickets : 6 epics, 34 tâches (dont les nouvelles KAN-36 à KAN-40)
et 28 sous-tâches du Sprint 1 (KAN-41 à KAN-68). Chaque tâche a un epic, une priorité et un label de sprint.

Chaque description conserve sa ligne d'en-tête actuelle (sprint, priorité, points) et sa phrase
d'origine, puis ajoute les sections ci-dessous. Toutes se terminent par la même définition de terminé :

> **Définition de terminé** : code relu (checklist de PR), CI verte, couverture ≥ 70 % maintenue,
> docstrings Google, aucune clé en clair, ticket à jour.

---

## 1. Corrections de titre (alignement sur les décisions d'architecture)

| Ticket | Titre actuel | Nouveau titre |
|---|---|---|
| KAN-9 | Dockerfile + docker-compose (web + db) | Dockerfile + docker-compose (web, worker, PostgreSQL, Redis) |
| KAN-10 | Pipeline CI : lint (flake8/ruff), tests, couverture | Pipeline CI : lint (ruff, mypy), tests, couverture ≥ 70 % |
| KAN-11 | Pipeline CD : build + déploiement Render/Heroku | Pipeline CD : image Docker + déploiement Render |
| KAN-16 | Modèles de données : User, Dream, Emotion, APICallLog | Modèles de données : User, Profile, Dream, Emotion, APICallLog |
| KAN-22 | Traitement asynchrone du pipeline (Celery/Django-Q ou threads) | Traitement asynchrone (Celery + Redis) et suivi de progression |
| KAN-26 | UX/UI : templates Bootstrap/Tailwind, accessibilité, responsive | UX/UI : gabarits Tailwind + HTMX, accessibilité, responsive |

## 2. Champ Priorité (aujourd'hui « Medium » partout)

| Priorité | Tickets |
|---|---|
| Highest | KAN-13 ✅, KAN-16, KAN-17, KAN-18, KAN-34 |
| High | KAN-7, KAN-8 ✅, KAN-9, KAN-10, KAN-14, KAN-19, KAN-20, KAN-21, KAN-23, KAN-24, KAN-25, KAN-27, KAN-28, KAN-30, KAN-31, KAN-32, KAN-33 |
| Medium | KAN-11, KAN-12, KAN-15, KAN-22, KAN-26, KAN-29 |
| Low | KAN-35 |

## 3. Critères d'acceptation à ajouter

### KAN-7 · Dépôt GitHub (Sprint 1)
- Le dépôt contient un README minimal et un `.gitignore` Python/Django (exclut `.env`, `media/`, `.venv/`).
- `main` est protégée : push direct refusé, PR obligatoire, CI verte exigée avant fusion.
- Un modèle de PR (`.github/pull_request_template.md`) contient la checklist d'auto-revue : lisibilité, tests, sécurité, docstrings, ticket KAN lié.
- Convention de branches `feat/KAN-xx-…` / `fix/KAN-xx-…` ; chaque commit cite son ticket.
- Réf. : spécifications §6.2 · plan qualité du dossier de cadrage §8.

### KAN-9 · Docker (Sprint 1)
- `docker compose up` démarre `web` (Gunicorn), `worker` (Celery), `db` (PostgreSQL 16) et `redis` (Redis 7).
- Une seule image multi-étapes pour web et worker, exécutée avec un utilisateur non root.
- Volumes persistants pour la base et les médias ; healthchecks sur db et redis.
- Script d'installation en une commande : copie de `.env.example`, migrations, chargement des émotions.
- Note : première tâche à reporter au Sprint 2 si le sprint déborde (20 pts de capacité pour 24 planifiés) ; la même image sert de repli local (R9).

### KAN-10 · CI (Sprint 1)
- Workflow GitHub Actions déclenché sur chaque PR et sur `main`.
- Étapes : ruff (PEP 8, imports, docstrings Google), mypy + django-stubs, pip-audit, `makemigrations --check`, pytest avec un service PostgreSQL.
- Échec si lint ou test échoue, ou si couverture < 70 % (`--cov-fail-under=70`).
- Aucun appel réel aux APIs IA : la CI ne consomme pas de budget.

### KAN-11 · CD (Sprint 3)
- Sur `main` : image publiée sur GHCR (tag = SHA du commit), déploiement Render par deploy hook.
- Migrations en étape de pré-déploiement ; test de fumée sur `/healthz/` après déploiement.
- Secrets uniquement dans les variables d'environnement Render.
- Retour arrière documenté : redéployer le SHA précédent. Repli : `docker compose up` en local (R9).

### KAN-12 · Logs et monitoring (Sprint 3) · US-19
- Logs JSON sur la sortie standard, identifiant de corrélation propagé de la requête à la tâche Celery.
- **Aucun** texte de rêve, prompt ou audio dans les logs ni dans Sentry (`send_default_pii=False`, `before_send`).
- `/healthz/` : base, Redis, âge de la plus vieille tâche en file.
- Admin : coût cumulé, p50/p95 de `processing_ms`, taux d'erreur par fournisseur, part d'images de secours.
- Alertes : budget 80 %, file bloquée > 5 min, erreurs API > 2 % sur 1 h.

### KAN-14 · Historique (Sprint 2) · US-12
- *En tant que rêveur, je veux voir l'historique de mes rêves afin de les relire et de suivre leur évolution.*
- Liste paginée (20 par page), du plus récent au plus ancien : date, extrait, émotion (icône), miniature.
- Détail : texte, émotion, image avec la mention « générée par IA », date.
- **Étant donné** l'identifiant d'un rêve d'un autre utilisateur, **alors** la page renvoie 404.
- p95 ≤ 500 ms avec 200 rêves (index `user_id, created_at`).

### KAN-15 · Suppression RGPD (Sprint 3) · US-03, US-14
- Suppression d'un rêve après confirmation : ligne, image et audio éventuel supprimés du stockage.
- Suppression du compte : rêves, fichiers et profil supprimés, session fermée ; `APICallLog.user_id` mis à NULL (le budget reste exact, sans donnée personnelle).
- Un test vérifie l'absence de fichier orphelin dans le stockage.

### KAN-16 · Modèles (Sprint 1)
- Modèles conformes à l'ERD : `User`, `Profile` (consentement, quota), `Dream` (UUID, machine à états), `Emotion`, `APICallLog`.
- Migration de données : 5 émotions (heureux, stressant, triste, étrange, neutre).
- Manager `Dream.objects.for_user(user)` utilisé par toutes les vues.
- `APICallLog.user_id` facultatif (voir KAN-15).
- Admin configuré (APICallLog en lecture seule).
- Test : sérialisation d'un rêve conforme à `architecture/dream.schema.json`.

### KAN-17 · Enregistrer / importer (Sprint 1) · US-04, US-05
- *En tant que rêveur, je veux raconter mon rêve à voix haute ou importer un fichier afin de ne pas avoir à l'écrire au réveil.*
- **Étant donné** un utilisateur connecté et consentant, **quand** il appuie sur Enregistrer, **alors** l'enregistrement démarre (MediaRecorder, WebM/Opus) avec minuteur et bouton d'arrêt.
- **Étant donné** un refus d'accès au micro, **alors** un message d'aide propose l'import (R8).
- Import .wav / .mp3 / .webm, 25 Mo et 10 min maximum ; signature du fichier vérifiée.
- Fichier invalide : message précis, rien n'est stocké. Fichier valide : `Dream` au statut `received`, nom de fichier aléatoire.
- Quota quotidien vérifié avant stockage. Testé sur Chrome, Firefox, Safari.
- Réf. : logique de validation déjà écrite et testée dans `maquette/services.py`.

### KAN-18 · Transcription (Sprint 2) · US-07
- **Étant donné** un rêve `received`, **quand** le worker le traite, **alors** la transcription est enregistrée avec le modèle utilisé et une ligne `APICallLog` (durée, coût).
- Délai maximal 60 s ; 2 relances sur timeout, 429 et 5xx avec attente exponentielle ; jamais de relance sur 400, 401, 413.
- Audio supprimé après transcription réussie (`audio_deleted_at` renseigné).
- Texte modifiable par l'utilisateur (`transcript_edited`).
- Bascule possible vers Deepgram ou AssemblyAI par configuration (KAN-21).

### KAN-19 · Émotion (Sprint 2) · US-08
- **Cinq** émotions : heureux, stressant, triste, étrange, neutre (au lieu de trois).
- Modèle exécuté localement dans le worker : candidat zero-shot mDeBERTa-v3 multilingue, alternative `xlm-emo-t` ; choix sur 20 textes annotés, justesse ≥ 70 % (R6).
- Distribution complète stockée (`emotion_scores`) ; émotion corrigeable par l'utilisateur (`emotion_corrected`).
- Repli sur le classifieur par mots-clés de la maquette si le modèle ne se charge pas.
- Avertissement visible : l'ambiance décrit le texte, ce n'est pas un diagnostic.
- Classement en moins de 2 s sur CPU (p95).

### KAN-20 · Image (Sprint 2) · US-09
- Modèle retenu : **OpenAI GPT Image 1 Mini**, qualité moyenne, 1024×1024 (0,011 $ par image), au lieu de « DALL-E ou Stable Diffusion ».
- Prompt construit à partir du texte, minimisé (noms propres retirés), enregistré dans `image_prompt`.
- Délai maximal 90 s, 1 relance. Refus de contenu : aucune relance, image de secours (`image_is_fallback`).
- Budget ≥ 95 % : étape sautée, le rêve reste `done`.
- Image servie uniquement à son propriétaire, avec la mention « générée par IA ».

### KAN-21 · Abstraction des APIs (Sprint 2)
- Trois interfaces : `Transcriber`, `EmotionClassifier`, `ImageGenerator` (spécifications §4.2) ; fournisseur choisi par configuration.
- Décorateur commun : délais, relances `tenacity`, respect de `Retry-After`, coupe-circuit (5 échecs en 5 min : pause de 2 min), une ligne `APICallLog` par tentative.
- Doublures de test pour chaque interface : aucun test ne consomme de budget.

### KAN-22 · Asynchrone (Sprint 3) · US-06
- `POST /dreams/` répond en moins de 2 s (p95) avec 202 ; tâche `process_dream(id)` publiée dans Redis.
- Machine à états `received → transcribing → analyzing → generating → done | failed` ; tâche idempotente, verrou par `dream_id`.
- Page de suivi : fragment HTMX interrogé toutes les 2 s.
- Bouton « Réessayer » sur `failed`, reprise à `error_step` sans refacturer les étapes réussies.
- Note : en Sprint 2, `CELERY_TASK_ALWAYS_EAGER` exécute le pipeline de façon synchrone avant l'activation du worker.

### KAN-23 · Budget (Sprint 3) · US-18
- Coût estimé avant chaque appel, enregistré après (unités facturées, grille tarifaire en configuration).
- Seuils globaux : 80 % (16 €) e-mail + Sentry ; 95 % images désactivées ; 100 % plus aucun appel payant.
- Quota par utilisateur : 5 rêves par jour (`Profile.daily_dream_limit`), refus 429 avec message clair.
- Limite de dépense également configurée chez le fournisseur.
- Tests TDD des seuils et du calcul (2 min + 1 image = 0,0184 €).

### KAN-24 · Filtres (Sprint 3) · US-13
- Filtres : période (dates de début et de fin, raccourcis 7 et 30 jours) et émotion(s), combinables, appliqués côté serveur et reflétés dans l'URL.
- Résultat vide : message explicite.
- p95 ≤ 500 ms (index `user_id, emotion_id, created_at`).

### KAN-25 · Tableau de bord (Sprint 3) · US-15, US-16
- Indicateurs : nombre de rêves, ambiance dominante, fréquence par semaine.
- Graphiques Chart.js : répartition (anneau) et évolution dans le temps (barres empilées par émotion), qui respectent les filtres de KAN-24.
- Agrégations testées en TDD ; tableau de données alternatif pour l'accessibilité.
- Référence visuelle : « Mon ciel de rêves » de la maquette.

### KAN-26 · UX/UI (Sprint 3)
- Gabarits Tailwind + HTMX reprenant l'identité « ciel nocturne » de la maquette.
- Responsive dès 360 px ; contrastes WCAG AA ; navigation au clavier ; libellés ARIA sur l'enregistreur ; `prefers-reduced-motion` respecté.
- États de chargement, d'erreur et vides sur chaque écran ; aucune page d'erreur brute.
- Score d'accessibilité Lighthouse ≥ 90.

### KAN-27 · Tests unitaires (Sprint 2)
- Tests des modèles (contraintes, `for_user`), des vues (authentification requise, 404 sur un rêve étranger), des formulaires et de la validation audio.
- factory_boy pour les données ; TDD sur la logique métier (coût, filtres, agrégations).

### KAN-28 · Tests des services IA (Sprint 3)
- Doublures HTTP (`respx`) : succès, timeout, 429 avec `Retry-After`, 5xx, refus de contenu, réponse invalide.
- Vérifier relances, coupe-circuit, bascule de fournisseur, `APICallLog`, suppression de l'audio, statut `failed` puis reprise.
- Scénario BDD « raconter un rêve » de bout en bout, fournisseurs simulés.

### KAN-29 · Test de charge (Sprint 4)
- Paliers de 5, 20 et 50 utilisateurs ; 70 % navigation, 30 % dépôt ; fournisseurs simulés avec latence réaliste (10 s et 14 s).
- Critères : p95 des pages ≤ 500 ms, rêves p95 ≤ 30 s à 20 utilisateurs, aucune erreur 5xx à 50.
- Résultats intégrés au rapport technique.

### KAN-30 · README (Sprint 4)
- Présentation, captures, lien vers l'architecture, installation Docker et venv, `.env.example` commenté, commandes de test, de lint et de déploiement, dépannage.
- Script d'installation vérifié sur une machine vierge.

### KAN-31 · Rapport technique (Sprint 4)
- Schémas mis à jour en régénérant `architecture/build.py` ; résultats de KAN-29 ; métriques réelles de `APICallLog`.

### KAN-34 · Recette (Sprint 4)
- Recette menée à partir de la matrice de traçabilité (spécifications §7) ; chaque bug critique donne un ticket et un test de non-régression.

### KAN-35 · Bonus (Backlog)
- Voix : OpenAI `tts-1` (15 $ par million de caractères) ; activé seulement si le budget consommé est < 60 %.

---

## 4. Tickets à créer

| Ticket | Titre | Epic | Sprint | Pts | Priorité | Labels |
|---|---|---|---|---|---|---|
| KAN-36 | En tant qu'utilisateur, je donne mon consentement à l'envoi vers les prestataires d'IA (RGPD) | KAN-2 | 2 | 2 | High | auth, rgpd, sprint-2, user-story |
| KAN-37 | En tant qu'utilisateur, je réinitialise mon mot de passe (US-02) | KAN-2 | 3 | 2 | Medium | auth, sprint-3, user-story |
| KAN-38 | En tant qu'utilisateur, j'exporte mes rêves en JSON (US-17) | KAN-2 | Backlog | 2 | Low | rgpd, backlog, user-story |
| KAN-39 | Spike : mesurer les latences réelles, vérifier les DPA, choisir le modèle d'émotion | KAN-3 | 2 | 3 | High | ia, rgpd, sprint-2, spike |
| KAN-40 | Analyse d'impact RGPD (AIPD) allégée, jointe au rapport | KAN-5 | 4 | 2 | Medium | doc, rgpd, sprint-4 |

Critères principaux :
- **Consentement** : case distincte et non pré-cochée à l'inscription, mention des prestataires (OpenAI) et du transfert hors UE ; `ai_consent_at` et `consent_version` enregistrés ; sans consentement, l'enregistrement est désactivé ; retrait possible depuis le profil.
- **Mot de passe** : lien signé et à durée limitée envoyé par e-mail (de façon asynchrone) ; message identique que l'adresse existe ou non.
- **Export** : fichier JSON conforme à `dream.schema.json`, uniquement pour ses propres rêves.
- **Spike** : `benchmark_latency.py` lancé sur les vraies APIs ; checklist RGPD de `benchmark.xlsx` remplie ; modèle d'émotion évalué sur 20 textes annotés ; décisions reportées dans le dossier.
- **AIPD** : description du traitement, nécessité et proportionnalité, risques et mesures (reprise du §5 du dossier de cadrage).

## 5. Sous-tâches du Sprint 1 (KAN-41 à KAN-68, découpage du dossier de cadrage)

| Parent | Sous-tâches |
|---|---|
| KAN-7 | Créer le dépôt · Protéger `main` · Modèle de PR · `.gitignore` |
| KAN-8 | Squelette Django et apps · Réglages dev/prod · `.env` et `.env.example` · Base PostgreSQL |
| KAN-9 | Dockerfile multi-étapes · docker-compose (web, worker, db, redis) · Script d'installation |
| KAN-10 | Workflow GitHub Actions · Lint (ruff, mypy) · pytest + PostgreSQL · Seuil de couverture 70 % |
| KAN-16 | Modèles et contraintes · Migrations + données Emotion · Admin · Test de sérialisation JSON |
| KAN-13 | Formulaires · Vues · Gabarits · Messages d'erreur · Tests |
| KAN-17 | Enregistreur MediaRecorder · Upload · Validation (taille, format, signature) · Stockage |
