# Circuit RC série — modèle physique et calcul scientifique

## Hypothèses et références

Le modèle utilise une résistance R et une capacité C positives et constantes,
une source continue idéale et des composants idéaux, sans fuite, inductance,
résistance série du condensateur ni autre effet parasite. Les tensions sont
mesurées suivant une même référence de polarité. Une source signée est admise.

Pour la réponse générale, le condensateur porte Uc0 et la source E est
connectée à t = 0. La charge depuis zéro est le cas Uc0 = 0.
Pour la décharge, le condensateur porte initialement U0 et
la source est déconnectée : la boucle ne contient que R et C. Les deux courbes
tracées sont des expériences indépendantes, chacune avec son propre t = 0.

## Démonstration des relations

En convention récepteur pour le condensateur : i = C × dUc/dt.
La loi des mailles lors de la charge donne E = R × i + Uc, donc :

```text
R × C × dUc/dt + Uc = E
τ = R × C
Uc(t) = E + (Uc(0) − E) × exp(−t/τ)
```

Cette relation générale est implémentée par `capacitor_voltage()`, avec Uc0
fini signé. Elle impose Uc(0) = Uc0 et tend vers E ; si Uc0 = E, elle décrit
un équilibre sans transitoire. Uc0 peut être supérieur ou inférieur à E.

Avec Uc(0) = 0, la relation compatible conservée est :
**Uc(t) = E × (1 − exp(−t/τ))**.

Lors de la décharge, le courant pris dans cette référence est négatif pour
Uc positive : τ × dUc/dt + Uc = 0. Avec Uc(0) = U0 :
**Uc(t) = U0 × exp(−t/τ)**.

## Courant et convention de signe

Le courant positif va de la source vers le condensateur, entrant par sa borne
de référence positive. Avec Uc mesurée de cette borne vers la masse :

```text
i(t) = (E − Uc(t)) / R
     = (E − Uc0) / R × exp(−t/τ)
     = C × dUc/dt
i(0) = (E − Uc0) / R
```

L'amplitude du courant décroît exponentiellement, avec un signe constant
pendant chaque réponse. Uc0 < E donne i > 0 ; Uc0 > E donne i < 0.
Une décharge avec E = 0 et Uc0 > 0 donne i = −Uc0/R × exp(−t/τ), négatif,
même si l'énergie est dissipée dans R. Le courant n'est donc pas contraint
à être positif.

La dérivée de la réponse générale vaut (E − Uc0)/τ × exp(−t/τ). Puisque
τ = R × C, sa multiplication par C restitue le courant. Les tests contrôlent
aussi cette cohérence par une différence finie centrée aux temps usuels.

L'analyse dimensionnelle confirme Ω × F = (V/A) × (A·s/V) = s. Les
arguments de l'exponentielle sont sans dimension. R se saisit en Ω, C en F,
t en s et les tensions en V ; le graphique peut présenter le temps en ms.

## Interprétation

À τ, exp(−1) ≈ 0.367879 : la charge atteint 0.632121 × E, et la décharge
conserve 0.367879 × U0. À 5τ, exp(−5) ≈ 0.006738. Pour R = 1000 Ω,
C = 1 µF et E = U0 = 5 V :

| Temps | Charge (V) | Décharge (V) |
| --- | --- | --- |
| 0 | 0 | 5 |
| 1 ms = τ | ≈ 3.160603 | ≈ 1.839397 |
| 5 ms = 5τ | ≈ 4.966310 | ≈ 0.033690 |

Avec E = U0, les deux tensions s'additionnent à E, à l'arrondi près. Pour
des tensions positives, la charge croît et la décharge décroît ; les sens
s'inversent pour des références de tension négatives. L'exponentielle tend
vers zéro sans s'annuler exactement à un temps fini dans le modèle mathématique.

## Contrats logiciels

`model.py` valide les paramètres physiques, puis calcule avec NumPy. Il ne
lit pas le clavier et ne trace aucune figure. Les résultats scalaires sont
des `float` et les vecteurs sont des tableaux `float64`. Les temps doivent
être finis, non négatifs, scalaires ou à une dimension. Le modèle accepte
un vecteur dans un ordre quelconque : chaque valeur est indépendante ; le
tracé exige, lui, un temps strictement croissant.

Les types non numériques, les booléens et les nombres complexes sont refusés.
Les valeurs hors des contraintes physiques produisent `ValueError` ; les
types incompatibles produisent `TypeError`. L'application traduit ces erreurs
en messages de saisie et quitte avec le code 2.

Les fonctions `charge_voltage()` et `discharge_voltage()` conservent leurs
signatures et leurs calculs. `capacitor_voltage()` généralise leur usage ;
`circuit_current()` accepte les mêmes temps, composants, source E et état Uc0.
L'option historique `--initial-voltage` reste réservée à la décharge indépendante.
`--charge-initial-voltage` définit Uc0 de la réponse vers E et de son courant.

`time_grid()` construit des fractions de l'intervalle [0, 1], puis les multiplie
par la durée. Cette forme évite une valeur intermédiaire trop grande pour une
durée proche du maximum de `float64`. La grille inclut les deux extrémités et
refuse les points répétés dus à une durée trop petite. Le nombre de points est
limité à un million pour borner les allocations du générateur.

## Stabilité et limites numériques

Pour la charge, `-expm1(-t/τ)` évite de soustraire deux nombres presque égaux
quand t est très petit. Cette propriété est décrite dans la
[documentation NumPy](https://numpy.org/doc/stable/reference/generated/numpy.expm1.html).
Pour un rapport subnormal, la réponse linéaire E × t/τ diffère de la formule
exponentielle d'une quantité très inférieure à la précision relative de
`float64`. `frexp()` et `ldexp()` conservent alors les exposants séparés :
par exemple, t = 1e-300 s, τ = 1e300 s et E = 1e300 V donnent environ
1e-300 V, même si t/τ seul s'arrondit à zéro. Il s'agit d'un test numérique,
pas d'un choix réaliste de composants.

Pour une décharge avec t/τ > 700, le code multiplie U0 par quatre facteurs
`exp(-(t/τ)/4)`. Cela évite que l'exponentielle seule s'arrondisse à zéro
avant le produit, alors que la tension finale reste représentable. Chaque
facteur est entre 0 et 1, et les valeurs intermédiaires ne croissent pas.
Le résultat demeure une approximation flottante, sans garantie d'arrondi exact.

Pour la réponse générale, le code réutilise ces deux calculs pour Uc0 = 0
ou E = 0. Si les tensions ont le même signe, il choisit une expression ancrée
sur Uc0 aux temps courts et sur E aux temps longs. Cela évite de perdre une
petite correction par soustraction. Pour des tensions opposées, il utilise
E × (1 − exp(−t/τ)) + Uc0 × exp(−t/τ) : chaque terme reste borné et la
différence Uc0 − E, potentiellement hors plage, n'est pas formée directement.

Le courant est calculé sous la forme (E − Uc0)/R × exp(−t/τ). Former
E − Uc(t) à partir d'une tension déjà arrondie à E ferait disparaître un
courant encore représentable, par exemple à 40τ. Le code normalise la
différence des tensions et R en mantisses et exposants, puis décompose
l'exponentielle en une puissance de deux et un facteur borné. Il n'exige
donc pas que la différence E − Uc0 ou l'amplitude initiale soient représentables
si le courant au temps demandé l'est. Un courant final non fini est refusé ;
un résultat trop petit peut s'arrondir à zéro. Les exposants limites utilisés
correspondent au format `float64`.

Un rapport t/τ trop grand peut devenir infini en calcul flottant : la charge
est alors à E et la décharge à zéro à la précision disponible. Les arrondis
de τ et des tensions restent présents. Des tensions subnormales ou nulles
par arrondi sont possibles ; elles ne signifient pas que le condensateur
est physiquement déchargé de manière exacte. Aucun calcul symbolique ni
tolérance de composant n'est inclus.

## Présentation et validation

`plotting.py` reçoit les données calculées, contrôle leur forme et les trace
avec un canevas Agg. L'export PNG fonctionne sans fenêtre graphique. Les
figures CLI contiennent deux panneaux partageant le temps : les tensions
au-dessus et le courant de la réponse vers E au-dessous. Les calculs et CSV
restent en SI ; le courant n'est converti en mA que pour l'affichage quand
son amplitude maximale est inférieure à 1 A. Sinon le panneau utilise les A.
Sa ligne horizontale à zéro permet de lire directement le signe ; les
repères de τ sont identiques dans les deux panneaux.

`plot_response(current=None)` conserve la présentation historique à un
panneau. Fournir un vecteur de courant fini, de même longueur que les temps,
active le deuxième panneau. Il reçoit les valeurs calculées sans recomposer
le courant à partir des tensions arrondies. Pour E = 5 V, Uc0 = 0, R = 1000 Ω,
le courant commence à +5 mA ; pour E = 0 et Uc0 = 5 V, il commence à −5 mA.
Le courant est attaché à la réponse générale, pas à la décharge indépendante
affichée en comparaison. Les axes automatiques ne constituent pas une
garantie de rendu de toutes les combinaisons extrêmes de `float64`.

Les tests contrôlent les lois, les invariants physiques, les valeurs de référence,
la validation et les limites numériques. Ils vérifient aussi les données
des courbes et un fichier PNG réel. Le rendu visuel de l'exemple est contrôlé
séparément des tests automatisés.

La CLI accepte les nombres négatifs scientifiques passés en argument séparé,
comme `--voltage -1e-3`. La validation commune des nombres réels est aussi
appliquée à τ lors du tracé : un entier trop grand provoque un `ValueError`,
sans laisser échapper une erreur de conversion. Les chemins PNG et CSV
partagent les contrôles de nom, extension, type de destination et dossier
parent ; un lien symbolique final est refusé pour protéger son fichier cible.

## Données CSV

`export.py` est indépendant de Matplotlib. `save_csv()` reçoit trois vecteurs
finis de même longueur, en secondes, volts et ampères, puis écrit :

```text
time_s,capacitor_voltage_v,current_a
```

La sortie représente uniquement la réponse vers E avec son état Uc0, pas
la courbe de décharge indépendante affichée pour comparaison. Les temps
doivent être non négatifs et strictement croissants ; un point unique est
accepté. Un vecteur non trié peut être calculé par le modèle mais doit être
réordonné avec ses tensions et courants avant cet export temporel.

Les types, les valeurs et le chemin sont contrôlés avant l'écriture. Les
nombres utilisent 17 chiffres significatifs pour un aller-retour `float64`.
Les répertoires manquants sont créés après validation ; la destination doit
être un fichier .csv ordinaire, sans lien symbolique final. Un fichier voisin
temporaire est écrit puis remplace la destination ; un échec avant ce
remplacement préserve un CSV antérieur. Cette opération ne rend pas les deux
exports PNG et CSV transactionnels ensemble et ne garantit pas la durabilité
en cas de coupure système. Voir les exemples dans le README.

La suite comprend **224 tests**, dont les **203 tests existants inchangés**.
Les nouveaux contrôles vérifient l'état initial, le courant signé, sa relation
avec la dérivée, les cas limites et le contenu des CSV relus après export.
Les tests du courant tracé vérifient les signes, l'échelle mA/A, la conservation
des tensions, les entrées invalides et le PNG à deux panneaux. Les régressions
CLI et les destinations symboliques font également l'objet de contrôles.

Voir [l'installation et l'utilisation](../README.md),
[les tests](../tests/README.md) et [l'exemple graphique](../figures/README.md).
