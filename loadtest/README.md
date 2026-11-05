# Test de charge (KAN-29)

Scénario Locust (`locustfile.py`) : chaque utilisateur virtuel se connecte, puis enchaîne historique,
historique filtré, tableau de bord, détail d'un rêve (70 %) et dépôt d'un rêve (30 %), avec 1 à 3 s
d'attente entre deux actions. Les fournisseurs d'IA sont simulés : aucun budget n'est consommé.

```bash
python app/manage.py seed_loadtest --users 50
LOGIN_RATE=100000/m python app/manage.py runserver      # tous les utilisateurs virtuels partagent une IP
python loadtest/run.py --host http://127.0.0.1:8000 --duration 60s
```

## Résultats sur la pile cible : Docker Compose (5 novembre 2026, 30 s par palier)

Environnement : Gunicorn (3 workers), **PostgreSQL 16**, **Redis 7**, **worker Celery** (pipeline asynchrone).
Ces résultats figurent dans `results/synthese.md`.

| Palier | Pages (p95) | Dépôt d'un rêve (p95) | Débit | Échecs |
|---|---|---|---|---|
| 5 utilisateurs | 46 à 79 ms | 130 ms | 2,7 req/s | 0 |
| 20 utilisateurs | 56 à 85 ms | 100 ms | 10,2 req/s | 0 |
| 50 utilisateurs | 76 à 190 ms | 380 ms | 25,5 req/s | 0 |

**Tous les critères sont respectés**, y compris à 50 utilisateurs simultanés. Le dépôt répond en moins
de 400 ms (202) parce que le traitement est confié au worker.

## Premier passage : poste de développement (SQLite, sans worker)

Environnement : `runserver` Django, **SQLite**, pipeline exécuté **dans la requête** (pas de worker Celery).

| Palier | Pages (p95) | Dépôt d'un rêve (p95) | Débit | Échecs |
|---|---|---|---|---|
| 5 utilisateurs | 31 à 88 ms | 390 ms | 2,6 req/s | 0 |
| 20 utilisateurs | 200 à 220 ms | 620 ms | 9,8 req/s | 0 |
| 50 utilisateurs | 580 à 750 ms | 9,9 s | 15,6 req/s | 3 connexions sur 50 |


## Lecture

- **Critère « p95 des pages ≤ 500 ms jusqu'à 20 utilisateurs » : respecté** (220 ms au plus).
- **À 50 utilisateurs, le poste local sature.** Le journal du serveur montre 12 erreurs
  `database is locked` : SQLite n'accepte qu'une écriture à la fois, et chaque dépôt exécute ici tout
  le pipeline (transcription, ambiance, image simulées) dans la requête. Les trois connexions refusées
  et le p95 de 9,9 s du dépôt en découlent. Aucune erreur applicative n'a été relevée.
- **Ces deux goulots disparaissent sur la pile cible** (résultats ci-dessus) : PostgreSQL gère les
  écritures concurrentes et le dépôt ne fait qu'enregistrer le fichier et publier une tâche.

Rejouer sur Docker : ajouter `LOGIN_RATE=100000/m` dans `.env` (puis le retirer), `docker compose up -d`,
`docker compose exec web python manage.py seed_loadtest --users 50`, puis
`python loadtest/run.py --host http://localhost:8000`.

## Limites

- Les fournisseurs simulés répondent instantanément : la latence réelle des APIs (≈ 10 s pour la
  transcription, ≈ 14 s pour l'image d'après le budget de latence) se mesure avec le spike KAN-39.
- La limite anti-force brute (5 connexions par quart d'heure et par IP) est relevée uniquement pour ce
  test ; elle reste active par défaut.
