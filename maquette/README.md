# Synthétiseur de rêves – Maquette Streamlit

Maquette interactive de la phase de pré-production (livrable 5.3). Toutes les APIs sont
**simulées** : aucune clé, aucun coût.

## Fonctionnalités

| Exigence du sujet | Réalisation |
|---|---|
| Enregistrer / uploader un audio (.wav/.mp3) | Onglet « Raconter à voix haute » (micro du navigateur) ou « Importer un fichier » ; contrôle du format, de la taille (25 Mo) et de la signature. Bouton **🎲 Rêve d'exemple** pour une démo sans micro |
| Transcription fictive (mock) | Texte d'exemple déterministe, affiché mot à mot comme une transcription en direct, puis **modifiable** |
| Image « placeholder » via une API publique | `picsum.photos/seed/<hash du texte>`, transformée en image « onirique » aux couleurs de l'émotion ; paysage nocturne généré en local si le service ne répond pas |
| Sélecteur d'émotion simulé + icône | Badge de l'émotion, barres de probabilité par émotion, correction par l'utilisateur |
| Gestion d'erreurs et indicateurs de chargement | Frise des étapes Voix → Texte → Émotion → Image animée en direct, `st.status`, messages clairs ; la barre latérale simule une latence, une panne de transcription ou une panne d'images |
| Bonus | « Mon ciel de rêves » : indicateurs (rêves, ambiance dominante, coût API cumulé), anneau des émotions, évolution dans le temps, filtres par ambiance, galerie. Bouton « Charger des rêves d'exemple » pour la vidéo de démo |

Indicateurs affichés pour chaque rêve : durée de l'audio, durée du traitement et coût API estimé
(tarifs de `benchmark.xlsx` : 0,0045 $/min de transcription + 0,011 $ par image).

## Installation

Prérequis : Python 3.11 ou 3.12. Le thème sombre est défini dans `.streamlit/config.toml` (lancer depuis la racine).

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate    ·    macOS/Linux : source .venv/bin/activate
pip install -r maquette/requirements.txt
```

## Lancement

Depuis la racine du projet :

```bash
streamlit run maquette/app.py
```

L'application s'ouvre sur http://localhost:8501. L'enregistrement micro demande l'autorisation
du navigateur (Chrome, Firefox ou Edge ; en cas de refus, utiliser l'upload).

## Vidéo de démonstration

`demo/demo_maquette.mp4` (83 s, 1280×720, sous-titrée) : enregistrement, traitement en direct,
résultat, panne de transcription, image de secours, tableau de bord et filtres. Elle est générée
automatiquement par `demo/record_demo.py`, qui pilote la maquette dans Edge (protocole DevTools),
ajoute les sous-titres et encode le MP4 :

```bash
pip install imageio-ffmpeg websockets
python maquette/demo/record_demo.py
```

La vidéo n'a pas de voix off ; pour en ajouter une, enregistrer la narration et la mixer avec
n'importe quel éditeur vidéo.

## Tests et qualité

```bash
pytest --cov=maquette --cov-report=term-missing   # tests unitaires + tests d'interface (AppTest)
ruff check .                                      # PEP 8, imports, docstrings Google
```

## Structure

```
maquette/
├── app.py              # interface Streamlit
├── services.py         # logique simulée, sans Streamlit (testable)
├── theme.py            # thème « ciel nocturne » (CSS) et fragments HTML
├── requirements.txt
└── tests/
    ├── test_services.py  # validation audio, mock STT, émotion, image et repli
    ├── test_theme.py     # fragments HTML (échappement, tri, frise)
    └── test_app.py       # parcours complet, panne, correction d'émotion, historique
```

`services.py` expose la même interface que les futurs services de production
(gpt-transcribe, modèle Hugging Face, GPT Image 1 Mini) : la maquette et ses tests servent
de base au Sprint 1.
