# Estimateur de prix de voitures d'occasion au Québec

Projet 2 – INF1007. Une application de bureau (Tkinter) qui estime le prix d'une
voiture d'occasion au Québec à partir de ses caractéristiques (marque, modèle,
version, année, kilométrage, cylindrée, carrosserie, etc.), grâce à une
régression linéaire entraînée sur des annonces réelles de concessionnaires.

Les choix du projet (données, nettoyage, modèle, interface) et leur justification
sont dans [DECISIONS.md](DECISIONS.md). L'utilisation de l'IA est décrite dans
[JOURNAL_IA.md](JOURNAL_IA.md).

## Résultats

Mesurés sur l'ensemble de test (20 % des données, environ 6 700 voitures jamais
vues pendant l'entraînement) :

| Modèle | Erreur moyenne (MAE) | RMSE | Prédictions à ±2000 \$ |
| --- | --- | --- | --- |
| Référence (prix moyen) | 9 671 \$ | — | 12,0 % |
| **Régression linéaire** | **3 988 \$** | 5 957 \$ | **36,8 %** |

Le graphique `modeles/predit_vs_reel.png` compare le prix prédit au prix réel
pour chaque voiture de test.

## Installation et lancement

Python 3.13 recommandé. Depuis la racine du projet :

```bash
pip install -r requirements.txt
python src/main.py          # ouvre l'application
```

Le modèle entraîné est déjà fourni dans `modeles/`. Pour le réentraîner (par
exemple après une modification du nettoyage) :

```bash
python src/entrainer.py     # réécrit modeles/modele.joblib, metadonnees.json et predit_vs_reel.png
```

Pour lancer les tests avec la couverture :

```bash
coverage run --source=src -m pytest
coverage report -m
```

Les tests sont aussi lancés automatiquement par GitHub Actions à chaque `push`
(`.github/workflows/tests.yml`).

## Données

- Source : « Used cars listings for US & Canada » (Kaggle, données MarketCheck),
  fichier des voitures d'occasion vendues par des concessionnaires canadiens.
- `donnees/ca-dealers-used-qc.csv` (2,4 Mo) : les annonces du Québec, incluses
  dans le dépôt avec l'accord du chargé de projet.
- Le fichier canadien complet (`ca-dealers-used.csv`, 69 Mo) n'est pas dans le
  dépôt (limite de 25 Mo). Il ne sert qu'à régénérer le CSV du Québec avec
  `extraire_quebec()` de `src/donnees.py` : le télécharger sur Kaggle et le
  placer dans `donnees/`.

Le nettoyage (lignes incomplètes, doublons par VIN, prix au-dessus de 100 000 \$,
kilométrages au-dessus de 250 000 miles, marques rares, harmonisation des
majuscules) est fait par `JeuDeDonnees` et ramène les données à 33 333 voitures.

## Utilisation de l'application

- Les champs, leurs étiquettes en français et leurs bornes sont construits à
  partir de `modeles/metadonnees.json`.
- Les listes marque → modèle → version se remplissent en cascade : seules les
  combinaisons présentes dans les données peuvent être choisies.
- Le kilométrage est saisi en **kilomètres**, puis converti en miles pour le
  modèle.
- Chaque saisie est validée par les classes `Variable` : un champ vide, une
  valeur hors bornes ou une année à virgule est refusé avec un message clair.
- Le prix estimé s'affiche avec la qualité du modèle (MAE, part des prédictions
  à ±2000 \$, comparaison avec la référence). Si le modèle donne un prix nul ou
  négatif, le message « Estimation impossible » est affiché.
- Les estimations sont conservées dans l'onglet *Historique* et dans
  `donnees/historique.json` (fichier local, ignoré par Git). Si ce fichier ne
  peut pas être écrit, le prix reste affiché et un message l'indique.

## Organisation du dépôt

```
src/
  donnees.py       lecture, nettoyage, classes Variable, séparation entraînement/test
  modele.py        métriques (NumPy), ModeleReference, ModeleLineaire, sauvegarde
  exceptions.py    exceptions du projet
  application.py   Estimateur (validation + prédiction) et Historique
  interface.py     fenêtre Tkinter
  entrainer.py     point d'entrée : entraînement et évaluation
  main.py          point d'entrée : application
tests/             tests pytest (logique et interface)
donnees/           CSV du Québec
modeles/           modèle entraîné, métadonnées et graphique
```

## Équipe

- Carnon Carel Irishura
- Avery
