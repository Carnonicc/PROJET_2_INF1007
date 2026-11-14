# PROJET_2_INF1007

## Interface graphique

L’application présente les champs de saisie d’un véhicule, une zone de résultat,
le score R² du modèle et un onglet d’historique. Les champs peuvent être
construits à partir des métadonnées fournies à `lancer_interface`.

Cette version est le squelette graphique : le modèle, la validation des valeurs,
la prédiction, le score R² calculé par le modèle et la persistance de l’historique
restent à connecter par le collaborateur. Le score s’affiche en pourcentage
lorsqu’il est transmis à `afficher_score_r2`. Les listes déroulantes sont
alimentées par le CSV du Québec et se filtrent selon les combinaisons réellement
présentes; l’année saisie filtre aussi les choix lorsqu’elle est dans le CSV.

Les choix affichés lorsque l’application est lancée sans métadonnées sont des
exemples visuels, pas des valeurs du modèle entraîné.

### Lancement

Installez les dépendances avec `pip install -r requirements.txt`, puis lancez
`python src\main.py` depuis la racine du projet.