# Fiche de décisions

Projet 2 INF1007 : estimer le prix d'une voiture d'occasion au Québec.

Une ligne par choix important, remplie au fil du projet. Les lignes marquées « À décider » restent ouvertes.

## Volet 1 : domaine et données

| Choix | Options envisagées | Choix retenu et justification | Validé par l'auxiliaire (date) |
| --- | --- | --- | --- |
| Domaine | Immobilier, transport, sport, voitures d'occasion | **Prix des voitures d'occasion.** Tout le monde comprend la question, et un acheteur ou un vendeur peut s'en servir pour savoir si un prix demandé est raisonnable. | Validation A : à compléter |
| Jeu de données | Autres jeux de voitures sur Kaggle ; jeux immobiliers | **« Used cars listings for US & Canada » (Kaggle, MarketCheck), fichier canadien des voitures d'occasion.** Il contient assez de lignes et mélange des variables numériques et catégorielles, comme l'exige l'énoncé. | Validation B : à compléter |
| Licence et dépôt du CSV | Mettre le CSV dans le dépôt ; ne donner qu'un lien Kaggle | **Le CSV du Québec (2,4 Mo) est dans `donnees/`.** Kaggle n'indique pas de licence, mais le chargé de projet a donné son accord. | Oui, chargé de projet (date à compléter) |
| Gros fichier canadien (69 Mo) | Le garder dans le dépôt ; le retirer et expliquer comment le télécharger | **À décider.** Il dépasse la limite de 25 Mo de l'énoncé. Il ne sert qu'à générer le CSV du Québec avec `extraire_quebec()`. | |
| Périmètre géographique | Tout le Canada ; Québec seulement | **Québec seulement.** Le projet est centré sur le Québec, et ce filtre ramène les 393 603 annonces à un volume conforme à l'énoncé (500 à 50 000 lignes) sans échantillonnage. | |
| Lignes incomplètes | Imputer les valeurs manquantes ; retirer les lignes | **Retirer les lignes où il manque une des 12 colonnes utiles.** Une voiture sans prix ne peut pas servir à l'entraînement, et il reste assez de données (59 924 lignes au Québec). | |
| Doublons | Garder toutes les annonces ; un exemplaire par VIN | **Un seul exemplaire par VIN** (59 924 → 33 333 lignes). 26 591 annonces étaient la même voiture listée plusieurs fois. Gardées, elles pourraient se retrouver à la fois dans l'entraînement et dans le test, ce qui gonflerait le score. | |
| Valeurs aberrantes | Ne rien faire ; retirer les valeurs impossibles | **Retirer les prix ≤ 0 et les kilométrages négatifs.** Ces valeurs sont impossibles. Une voiture à 0 mile est gardée, car une voiture neuve chez un concessionnaire est un cas réel. | |
| Marques rares et prix extrêmes | Minimum d'annonces par marque (ex. 100) ; prix maximum ; les deux | **À décider.** Lamborghini, Ferrari, etc. sont trop rares pour être bien prédites. | |
| Colonnes retirées | Garder tout ; garder seulement ce qu'un utilisateur peut saisir | **Retirer `id`, `vin`, `stock_no`, `seller_name`, `street`, `city`, `zip`, `state`, `vehicle_type`.** Ce sont des identifiants, des données sur le vendeur ou des colonnes constantes (`state` vaut toujours « QC »). Un utilisateur ne pourrait pas les saisir. | |

## Volet 2 : modèle

| Choix | Options envisagées | Choix retenu et justification | Validé par l'auxiliaire (date) |
| --- | --- | --- | --- |
| Variable cible | `price` en classification par tranches de 2000 $ ; `price` en régression | **`price`, en régression.** On prédit un montant en dollars, et la régression garde l'information sur la taille de l'erreur. | Validation C : à compléter |
| Caractéristiques | — | **Numériques :** `year`, `miles`, `engine_size`. **Catégorielles :** `make`, `model`, `trim`, `body_type`, `drivetrain`, `transmission`, `fuel_type`, `engine_block`. | |
| Garder `model` et `trim` | Avec ; sans | **Garder `model` et `trim`.** Dans une même marque, les prix varient énormément selon le modèle et la version (une Civic LX ne coûte pas le prix d'une Accord Touring). Sans ces colonnes, le modèle ne peut pas faire la différence. Contreparties : beaucoup de colonnes après l'encodage, et de longues listes déroulantes, réduites par des listes en cascade marque → modèle → version dans l'interface. | |
| Métrique | Exactitude par tranches, R², RMSE, MAE | **MAE comme métrique principale** : « on se trompe en moyenne de X $ », une phrase compréhensible par tous. **Métrique secondaire : % de prédictions à ±2000 $ du vrai prix**, qui correspond directement à l'objectif du projet. La RMSE est aussi calculée pour voir si quelques grosses erreurs dominent. Les métriques sont calculées avec NumPy et comparées à scikit-learn dans un test. | Validation C : à compléter |
| Modèle | Régression linéaire, forêt aléatoire, k plus proches voisins | **Régression linéaire.** Elle est simple, rapide et chaque coefficient s'explique (« +X $ pour un an de moins »). La forêt aléatoire a été envisagée puis écartée pour rester simple et consacrer le temps à l'interface. | Validation C : à compléter |
| Référence | Classe majoritaire (sans objet en régression) ; prix moyen | **Prix moyen de l'ensemble d'entraînement.** C'est le modèle trivial standard en régression, qui sert de point de comparaison. | |
| Encodage des catégories | Encodage ordinal ; one-hot | **One-hot (`OneHotEncoder`, avec `handle_unknown="ignore"`).** Un encodage ordinal inventerait un ordre entre les marques. L'option `ignore` évite un plantage si une valeur n'a jamais été vue à l'entraînement. | |
| Séparation entraînement / test | 70/30, 80/20 | **80 % entraînement / 20 % test, avec la graine `42`.** Avec 33 333 lignes, 20 % donnent environ 6 700 voitures de test, et la graine fixe rend les résultats reproductibles. | |
| Sauvegarde | Réentraîner à chaque lancement ; sauvegarder | **Modèle sauvegardé avec `joblib`, métadonnées dans un fichier JSON.** L'interface se construit à partir de ces fichiers sans réentraîner le modèle. | |

## Volet 3 : interface et code

| Choix | Options envisagées | Choix retenu et justification | Validé par l'auxiliaire (date) |
| --- | --- | --- | --- |
| Technologie d'interface | Streamlit, Tkinter | **Tkinter.** Il est inclus avec Python, donc rien à installer, et c'est l'option la plus proche du cours. Il fonctionne en local sans serveur, et la documentation de Matplotlib montre comment intégrer un graphique (`FigureCanvasTkAgg`). Streamlit aurait été plus rapide à apprendre, mais il ajoute une dépendance et un fonctionnement par navigateur. | Validation D : à compléter (avec la maquette papier) |
| Organisation du code | Un seul fichier ; plusieurs modules | **Modules `donnees`, `modele`, `exceptions`, `interface`, avec `main.py` comme point d'entrée.** La logique est séparée de l'interface pour pouvoir la tester avec pytest sans ouvrir de fenêtre. | |
| Hiérarchie des variables | Validation dans l'interface ; classes de variables | **`Variable` (abstraite) → `VariableNumerique` et `VariableCategorielle`**, qui redéfinissent chacune `valider()`. Chaque type valide sa saisie à sa façon, et l'interface n'a pas à connaître ces règles. | |
| Outil du chapitre 7 | Décorateur, générateur, lambda | **Décorateur `chronometrer`**, qui mesure la durée de l'entraînement sans modifier le code de `entrainer`. Un générateur `lire_par_blocs` (lecture du CSV par blocs) a été écrit puis retiré : notre CSV du Québec (2,4 Mo) se charge sans problème d'un coup, donc la fonction n'était appelée nulle part. | |
