# PROJET_2_INF1007

## Interface graphique

L’application présente les champs de saisie d’un véhicule, une zone de résultat,
la MAE du modèle sur l’ensemble de test et un onglet d’historique. Les champs
sont construits à partir des métadonnées fournies à `lancer_interface`.

L’application charge le modèle et ses métadonnées depuis `modeles/`, valide les
saisies et affiche le prix estimé lorsqu’une prédiction positive est produite.
Le kilométrage est saisi en kilomètres, puis converti en miles pour le modèle.
La MAE mesurée sur l’ensemble de test est affichée depuis les métadonnées. Les
listes déroulantes sont alimentées par le CSV du Québec et se filtrent selon les
combinaisons réellement présentes; l’année saisie filtre aussi les choix
lorsqu’elle est dans le CSV. Les prédictions sont conservées dans
`donnees/historique.json`, un fichier local ignoré par Git.

Les choix affichés lorsque l’application est lancée sans métadonnées sont des
exemples visuels, pas des valeurs du modèle entraîné.

### Lancement

Installez les dépendances avec `pip install -r requirements.txt`, puis lancez
`python src\main.py` depuis la racine du projet.