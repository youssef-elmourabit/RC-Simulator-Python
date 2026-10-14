# Exemple graphique de référence

`rc_charge_decharge.png` présente deux expériences indépendantes dans son
panneau supérieur : charge depuis Uc(0) = 0 V et décharge depuis Uc(0) = U0 = 5 V.
Le panneau inférieur montre uniquement le courant de la charge vers E.

- R = 1000 Ω.
- C = 1e-6 F = 1 µF.
- E = U0 = 5 V.
- τ = 0.001 s = 1 ms.
- Intervalle : 0 à 5τ = 5 ms ; 501 points.
- Export : PNG, 1600 × 1280 pixels, avec deux panneaux.

La ligne pointillée repère τ ; elle ne représente pas une troisième tension.
À cet instant, la charge vaut environ 3.1606 V et la décharge 1.8394 V.
Le courant de la charge commence à +5 mA, vaut environ 1.8394 mA à τ
et décroît vers zéro. Sa référence positive va de la source vers le condensateur.
Une décharge obtenue avec E = 0 et Uc0 > 0 donne un courant négatif.
À 5τ, les réponses sont proches de leurs limites, sans les atteindre
mathématiquement. Le modèle idéal ignore les effets parasites et les tolérances.

Pour régénérer cet exemple, depuis la racine avec `.venv` activé :

```sh
python src/main.py
```

Cette commande remplace le PNG de référence s'il existe. Pour conserver
un autre résultat sans toucher à cet exemple, utiliser `--output` avec un
nom différent. Le PNG de référence est destiné au dépôt ; les autres PNG
générés sont ignorés par Git.
L'option `--csv-output figures/rc_reference.csv` exporte également les temps,
la tension de la réponse vers E et son courant, en unités SI. Les CSV générés
dans `figures/` restent locaux et ignorés.
