# PROJET_2_INF1007

## Interface graphique

L’application présente les champs de saisie d’un véhicule, une zone de résultat,
la qualité du modèle mesurée sur l’ensemble de test (erreur moyenne MAE, part des
prédictions à ±2000 $ et comparaison avec le modèle de référence) et un onglet
d’historique. Les champs, leurs étiquettes en français et leurs bornes sont
construits à partir des métadonnées `modeles/metadonnees.json`.

L’application charge le modèle et ses métadonnées depuis `modeles/`, valide les
saisies avec les classes `Variable` (une saisie vide, hors bornes ou une année à
virgule est refusée avec un message) et affiche le prix estimé lorsqu’une
prédiction positive est produite ; un prix nul ou négatif donne le message
« Estimation impossible ». Le kilométrage est saisi en kilomètres, puis converti
en miles pour le modèle. Les listes déroulantes marque → modèle → version se
remplissent en cascade à partir de la hiérarchie des métadonnées : seules les
combinaisons présentes dans les données peuvent être choisies. Les prédictions
sont conservées dans `donnees/historique.json`, un fichier local ignoré par Git ;
si ce fichier ne peut pas être écrit, le prix reste affiché et un message
l’indique.

### Lancement

Installez les dépendances avec `pip install -r requirements.txt`, puis, depuis la
racine du projet :

1. `python src/entrainer.py` : entraîne le modèle et écrit les fichiers de
   `modeles/` (inutile si ces fichiers sont déjà présents) ;
2. `python src/main.py` : ouvre l’application.
