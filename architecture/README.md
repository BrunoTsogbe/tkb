# Spécifications et architecture (livrable 5.2)

Sources du document `specifications_architecture.pdf` (10 pages, à la racine du projet).

## Contenu du document

| § | Exigence du sujet | Où |
|---|---|---|
| 1 | Diagrammes C4 Context + Container | Figures 1 et 2, tableaux des systèmes externes et des conteneurs |
| 2 | Modèle de données : ERD + dictionnaire d'attributs | Figure 3, §2.1 ; schéma JSON d'un rêve en §2.2 |
| 3 | Séquence clé : traitement complet d'un rêve (UML) | Figure 4, machine à états, cas d'erreur |
| 4 | API interne : choix argumenté des APIs | §4.1 à §4.4 (APIs externes, interfaces, politique d'appel, routes) |
| 5 | Exigences : performance, SLO, budget API | §5.1 à §5.4 (SLO, budget de latence, garde-fous, test de charge) |
| 6 | Justification technologique : libs, CI/CD, monitoring | §6.1 à §6.4 |

## Régénérer le PDF

```bash
python architecture/build.py
```

Le script dessine les diagrammes (`diagrams.py`, à l'aide de `svg.py`), les injecte dans
`document.html`, puis imprime le PDF avec Edge ou Chrome en mode headless. Il échoue si le
document dépasse 10 pages.

## Fichiers

```
architecture/
├── document.html            # texte du document (gabarit, diagrammes en {{…}})
├── diagrams.py, svg.py      # diagrammes générés en code (versionnables, relus en PR)
├── build.py                 # génération SVG + PDF
├── dream.schema.json        # schéma JSON (2020-12) d'un rêve stocké
├── dream.example.json       # exemple conforme
├── diagrammes/              # SVG générés + sources PlantUML équivalentes (.puml)
└── tests/test_dream_schema.py
```

Les fichiers `.puml` décrivent les mêmes diagrammes en PlantUML (bibliothèque C4-PlantUML) pour
une édition dans draw.io ou PlantUML ; ils n'ont pas été rendus dans cet environnement.
