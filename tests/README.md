# Validation automatisée

Depuis la racine du projet, avec l'environnement virtuel activé :

```sh
python -m pytest -q
```

La configuration `pytest.ini` rend `src/` importable, sélectionne `tests/`
et traite les avertissements inattendus comme des erreurs. `conftest.py`
conserve le cache Matplotlib dans `.cache/`, ignoré par Git, sauf configuration
explicite de `MPLCONFIGDIR`.

| Suite | Contrôles |
| --- | --- |
| `test_model.py` | Unités SI, conditions initiales, valeurs à τ, tableaux, monotonie, complémentarité, types et valeurs invalides, plages numériques |
| `test_plotting.py` | Données réellement tracées, axes avec unités, validation des vecteurs, signature et dimensions du PNG exporté |
| `test_cli.py` | Exécution de `src/main.py`, paramètres indépendants, tensions signées, affichage avec unités et absence d'export après saisie invalide |
| `test_response.py` | État initial quelconque, courant signé, dérivée du condensateur, compatibilité et limites numériques |
| `test_csv.py` | Aller-retour exact float64, noms et données invalides, remplacement et préservation d'un CSV existant |
| `test_cli_extensions.py` | Nouvelle tension initiale, courant et contenu du CSV produit par l'application réelle |
| `test_current_plotting.py` | Panneaux de tension et de courant, signes, unités mA/A, validation de τ et protection des cibles de liens symboliques |
| `test_finalisation.py` | PNG à deux panneaux, CSV conforme et arguments scientifiques négatifs |

Les comparaisons scientifiques utilisent des tolérances, pas une égalité
exacte systématique de décimaux. Les cas très petits utilisent une tolérance
absolue nulle afin de ne pas confondre un résultat positif avec zéro.
Les lois physiques servent aussi de référence : charge + décharge = E si
U0 = E, réponses bornées et conditions initiales imposées.

Les fichiers d'export des tests sont placés dans les dossiers temporaires
de pytest. Le PNG d'exemple du projet n'est pas remplacé par les tests.
Résultat de validation sous macOS avec les versions du README : **224 tests réussis**,
soit **203 tests précédents conservés sans modification et 21 nouveaux cas**.
La suite n'évalue pas l'esthétique du graphique, ni un circuit physique réel,
et ne remplace pas une validation sur d'autres systèmes d'exploitation.
