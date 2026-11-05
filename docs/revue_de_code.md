# Revue de code en direct : préparation (KAN-33, 15 min)

Objectif du jury : voir le code, la manière de raisonner et la capacité à déboguer.
Plan conseillé : **3 min** de visite guidée, **7 min** sur le bug et sa correction,
**5 min** de questions sur les points faibles assumés.

## 1. Visite guidée (3 min)

À montrer dans cet ordre, l'éditeur déjà ouvert sur chaque fichier :

| Fichier | Ce qu'il faut dire |
|---|---|
| `app/dreams/views.py:36` `_enqueue` | La tâche n'est envoyée qu'après le commit (`transaction.on_commit`) : le worker ne lit jamais un rêve qui n'existe pas encore en base. |
| `app/dreams/pipeline.py:142` `process_dream` | Machine à états idempotente. Verrou par rêve (`cache.add`), chaque étape est sautée si son résultat existe déjà, donc « Relancer » reprend à l'étape en échec sans repayer les précédentes. |
| `app/ai/policy.py:65` `call_with_policy` | Point unique pour tous les appels d'IA : coupe-circuit, relances avec attente exponentielle et aléa, respect de `Retry-After`, une ligne `APICallLog` par tentative avec le coût, budget. |
| `app/ai/providers/__init__.py` | Registre des fournisseurs : `fake` / `openai` / `huggingface` choisis par variable d'environnement, sans toucher au pipeline. |
| `app/tests/test_pipeline.py` | Les APIs sont simulées avec `httpx.MockTransport` : on teste les vrais clients HTTP, erreurs 429 et 5xx comprises, sans réseau ni coût. |

## 2. Le bug : « le dépôt d'un rêve renvoie 500 sur Docker » (7 min)

### Symptôme

- Les 115 tests passent, en local et en CI.
- Sur la pile Docker Compose, `scripts/smoke_test.py` échoue à l'étape « dépôt d'un rêve » : **HTTP 500**.
- Le worker Celery ne démarre pas.

### Méthode de débogage (à raconter étape par étape)

1. **Reproduire** : `docker compose up` puis `python scripts/smoke_test.py`. L'échec est systématique.
2. **Lire les logs du bon service** : `docker compose logs worker`. On y voit
   `ModuleNotFoundError: No module named 'packaging'`, levée à l'import du transport Redis de kombu.
3. **Comprendre pourquoi les tests ne l'ont pas vu** : en test, `CELERY_TASK_ALWAYS_EAGER = True`,
   la tâche s'exécute dans le processus web et kombu ne charge jamais le transport Redis.
   En développement, `packaging` est présent par hasard (installé par pip ou par un outil de dev).
   L'image Docker n'installe que `requirements.txt` : la dépendance transitive manque.
4. **Pourquoi un 500 côté web** : `_enqueue` appelle `.delay()`, qui ouvre la connexion au broker
   et importe le même transport → exception non gérée dans la vue.
5. **Corriger, puis vérifier** : reconstruire l'image et rejouer le test de fumée (10 étapes au vert),
   puis le test de charge (50 utilisateurs, 0 échec).

### Avant / après (commit `65335e1`)

```diff
 # app/requirements.txt
 celery>=5.4,<6
 redis>=5.0
+packaging>=24.0  # requis par le transport Redis de kombu (Celery)
```

En corrigeant celui-ci, le même test de fumée a révélé trois autres bugs (à citer rapidement) :

```diff
 # docker-compose.yml (service web) : le web exécutait le pipeline lui-même
+      CELERY_TASK_ALWAYS_EAGER: "false"
 # config/settings/prod.py : la connexion échouait en HTTP local (cookies Secure)
-SESSION_COOKIE_SECURE = True
+SESSION_COOKIE_SECURE = env.bool("DJANGO_SECURE_COOKIES", default=True)
 # Dockerfile : Gunicorn ne pouvait pas écrire dans son dossier de travail
-    && mkdir -p /app/media && chown -R app:app /app/media /app/staticfiles
+    && mkdir -p /app/media && chown app:app /app && chown -R app:app /app/media /app/staticfiles
```

### Leçon à énoncer

> Les tests unitaires valident la logique ; seul un test de bout en bout sur l'image réellement
> déployée valide l'assemblage. D'où `scripts/smoke_test.py` (à lancer sur la pile Docker avant chaque
> fusion) ; après un déploiement, `deploy.yml` se limite à vérifier `/healthz/`. Piste : y lancer aussi le test de fumée.

## 3. Points faibles assumés (questions probables)

| Question probable | Réponse préparée |
|---|---|
| « `sleep` dans le worker, ce n'est pas bloquant ? » | Si : une relance bloque le worker jusqu'à 30 s. Acceptable à notre échelle (quota de 5 rêves par jour). Amélioration : `self.retry(countdown=...)` de Celery, pour rendre le worker pendant l'attente. |
| « Le budget est-il fiable avec plusieurs workers ? » | Le cumul est la somme de `APICallLog` en base (cache de 60 s, rafraîchi après chaque appel payant), pas un compteur en mémoire. Deux appels simultanés peuvent dépasser légèrement le seuil : marge prévue par l'arrêt à 100 % sur un budget de 20 €. |
| « Pourquoi pas Tailwind ni HTMX ? » | Feuille de style maison issue de la charte UX ; un script de 30 lignes remplace HTMX pour le suivi du statut. Moins de dépendances, même comportement. Écart documenté dans le rapport. |
| « Les APIs réelles ont-elles été testées ? » | Les clients sont testés contre des réponses simulées au format officiel ; les appels réels sont l'objet de KAN-39 (moins de 0,50 €). Être transparent. |
| « Que se passe-t-il si le verrou expire pendant le traitement ? » | `LOCK_TTL_S` est supérieur à la durée maximale d'un traitement (délais et relances bornés) ; et chaque étape est idempotente, donc un double passage ne refacture pas une étape déjà faite. |

## 4. Check-list avant la séance

- [ ] `docker compose up -d` lancé, `python scripts/smoke_test.py` au vert.
- [ ] Onglets ouverts : les 5 fichiers du §1 et `git show 65335e1`.
- [ ] `python -m pytest app/tests -q` prêt dans un terminal (environ 10 s).
- [ ] Police de l'éditeur agrandie, notifications coupées.
