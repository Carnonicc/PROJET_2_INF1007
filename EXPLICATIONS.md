# Explication du code, fonction par fonction

Ce document décrit **chaque fonction et chaque classe du dossier `src/`** : ce qu'elle fait, pourquoi elle existe et pourquoi elle est écrite de cette façon. Il sert à préparer les questions de l'auxiliaire, qui peut nous interroger sur n'importe quelle ligne.

Pour chaque élément :
- **Ce qu'elle fait** : le comportement, avec un exemple quand c'est utile ;
- **Pourquoi elle existe** : le problème qu'elle règle dans le projet ;
- **Pourquoi elle est écrite comme ça** : les choix de code qui ne sont pas évidents.

---

## Sommaire

0. [Vue d'ensemble : comment les fichiers s'enchaînent](#0-vue-densemble)
1. [`exceptions.py`](#1-exceptionspy)
2. [`donnees.py`](#2-donneespy)
3. [`modele.py`](#3-modelepy)
4. [`entrainer.py`](#4-entrainerpy)
5. [`application.py`](#5-applicationpy)
6. [`interface.py`](#6-interfacepy)
7. [`main.py`](#7-mainpy)
8. [Les classes « fausses » des tests](#8-les-classes-fausses-des-tests)
9. [Où se trouvent les notions du cours](#9-où-se-trouvent-les-notions-du-cours)

---

## 0. Vue d'ensemble

Le projet a **deux programmes** qu'on lance séparément.

**`python src/entrainer.py`** : on le lance une fois, ou chaque fois que le nettoyage change.
```
CSV ─► charger_csv ─► JeuDeDonnees (nettoyer) ─► separer ─► entraînement des 2 modèles
    ─► evaluer sur le test ─► modeles/modele.joblib + modeles/metadonnees.json + graphique
```

**`python src/main.py`** : c'est l'application. Elle ne réentraîne rien.
```
modele.joblib + metadonnees.json ─► Estimateur, Historique ─► creer_rappels ─► fenêtre Tkinter
```

**Ce qui se passe quand on clique sur « Prédire » :**
```
interface (textes saisis) ─► on_prediction ─► Estimateur.estimer
    ─► chaque Variable.valider (polymorphisme) ─► verifier_combinaison
    ─► km convertis en miles ─► modele.predire ─► prix
    ─► affichage du prix ─► Historique.ajouter (fichier JSON) ─► tableau mis à jour
```

**Pourquoi séparer l'entraînement de l'application ?** L'entraînement relit tout le CSV. L'application, elle, doit s'ouvrir vite et fonctionner sans le CSV. Le modèle entraîné est donc sauvegardé une fois, puis relu.

**Pourquoi séparer la logique (`application.py`) de la fenêtre (`interface.py`) ?** On ne peut pas facilement tester une fenêtre avec pytest. Tout ce qui « réfléchit » (valider, prédire, garder l'historique) est donc dans des classes sans Tkinter, testées à 100 %. La fenêtre ne fait que dessiner et transmettre les clics.

---

## 1. `exceptions.py`

Le fichier contient trois classes d'exception, toutes héritées d'`Exception` et vides, à part leur docstring.

| Exception | Levée quand… | Levée par | Attrapée par |
|---|---|---|---|
| `DonneeInvalideError` | une donnée ou une saisie est invalide | `charger_csv`, `Variable.valider`, `verifier_combinaison` | l'interface (boîte de message) |
| `ModeleNonEntraineError` | on utilise un modèle pas encore entraîné | `predire`, `sauvegarder` | personne : c'est une erreur de programmation |
| `EstimationImpossibleError` | le modèle donne un prix ≤ 0 | `Estimateur.estimer` | l'interface (zone de résultat) |

**Pourquoi des exceptions à nous ?** Pour **distinguer les cas**. Une erreur de l'utilisateur (« Année doit être un nombre entier ») doit s'afficher gentiment. Un vrai bogue doit, lui, rester visible. Si tout était une `ValueError`, l'interface ne pourrait pas faire la différence.

**Pourquoi des classes vides ?** On n'a besoin que d'un **nom** différent : le message est passé à la création, par exemple `raise DonneeInvalideError("...")`.

---

## 2. `donnees.py`

Ce fichier contient tout ce qui touche aux données : lecture, nettoyage, description des variables, hiérarchie marque → modèle → version et séparation entraînement / test.

### Les constantes

| Constante | Valeur | Rôle |
|---|---|---|
| `CIBLE` | `"price"` | ce qu'on prédit |
| `COLONNES_NUMERIQUES` | `miles`, `year`, `engine_size` | caractéristiques en nombres |
| `COLONNES_CATEGORIELLES` | `make`, `model`, `trim`, … (8 colonnes) | caractéristiques en texte |
| `COLONNES` | les 12 réunies | colonnes obligatoires du CSV |
| `COLONNES_ENTIERES` | `miles`, `year` | refusent les nombres à virgule |
| `KILOMETRES_PAR_MILE` | `1.609344` | conversion km ↔ miles |
| `ETIQUETTES` | `{"year": "Année", ...}` | texte français affiché à l'utilisateur |

**Pourquoi des constantes ?** Les noms de colonnes servent partout : nettoyage, modèle, tests, interface. Si on en change un, on le change **à un seul endroit**. Une faute de frappe dans un nom, comme `"yaer"`, donnerait ailleurs une erreur difficile à trouver.

### `miles_vers_kilometres(miles)` et `kilometres_vers_miles(kilometres)`

- **Ce qu'elles font** : elles multiplient ou divisent par 1,609344. Par exemple, 60 000 miles donnent 96 560,6 km.
- **Pourquoi elles existent** : c'est l'idée d'Avery. Au Québec, on connaît le kilométrage de sa voiture en km, mais le CSV, et donc le modèle, est en miles.
- **Pourquoi écrites comme ça** : chacune est une petite fonction avec un nom clair, plutôt qu'un `* 1.609344` répété dans le code. On lit ce que fait la ligne, et le facteur n'est écrit qu'une fois.

### `extraire_quebec(chemin_source, chemin_sortie)`

- **Ce qu'elle fait** : à partir du gros CSV canadien (69 Mo, 393 603 annonces), elle écrit le CSV du Québec (33 333 annonces). Elle renvoie le nombre de lignes écrites.
- **Pourquoi elle existe** : c'est notre script de départ, transformé en fonction. Le gros fichier dépasse la limite de 25 Mo de l'énoncé. Cette fonction montre comment on a obtenu notre CSV, et permet de le refaire.
- **Pourquoi écrite comme ça** :
  - `db[COLONNES].notna().all(axis=1)` donne « Vrai si les 12 colonnes de la ligne sont remplies ». `axis=1` veut dire « sur chaque ligne ».
  - `& (db["state"] == "QC")` est un masque booléen, qu'on combine avec `&` et non `and`, parce qu'on compare deux colonnes entières.
  - `drop_duplicates(subset="vin")` garde un seul exemplaire par numéro de série (VIN). Une même voiture était parfois annoncée plusieurs fois. Si elle se retrouvait à la fois dans l'entraînement et dans le test, le score serait faussement bon.
  - On retire les doublons **avant** de garder seulement les 12 colonnes, parce que `vin` ne fait pas partie des 12.
  - `index=False` évite d'écrire une colonne de numéros de ligne inutile dans le CSV.

### `charger_csv(chemin)`

- **Ce qu'elle fait** : elle lit le CSV et vérifie que les 12 colonnes sont présentes.
- **Pourquoi elle existe** : c'est le seul point d'entrée des données. Si le fichier est mauvais, on veut le savoir tout de suite, avec un message clair.
- **Pourquoi écrite comme ça** :
  - On vérifie que le fichier existe **avant** de le lire, pour lever `FileNotFoundError`.
  - `[c for c in COLONNES if c not in df.columns]` est une liste en compréhension qui garde les colonnes absentes. Le message nomme donc **exactement** celles qui manquent, au lieu de dire seulement « fichier invalide ».

### `harmoniser_majuscules(serie)`

- **Ce qu'elle fait** : elle regroupe les écritures qui ne diffèrent que par les majuscules (« Base » et « base ») et les remplace toutes par l'écriture la plus fréquente du groupe.
- **Pourquoi elle existe** : dans le CSV, 13 modèles et 26 versions existaient en deux écritures. Pour le modèle, « E-Pace » et « E-PACE » étaient deux voitures différentes, chacune avec moins d'exemples, et l'interface les affichait deux fois.
- **Pourquoi écrite comme ça** :
  - `casefold()` met en minuscules (en plus complet que `lower()`) : c'est la « clé » du groupe.
  - On parcourt les écritures de la plus fréquente à la moins fréquente ; `setdefault` ne garde que la **première** rencontrée pour chaque clé. À égalité, l'ordre alphabétique décide, pour que le résultat soit toujours le même.
  - `serie.map(lambda ...)` applique le remplacement à toute la colonne et renvoie une **nouvelle** colonne.

### `nettoyer(df, minimum_annonces=10)`

- **Ce qu'elle fait** : elle renvoie un **nouveau** DataFrame :
  - sans les lignes incomplètes ;
  - sans les prix ≤ 0 ou au-dessus de `PRIX_MAXIMUM` (100 000 $) ;
  - sans les valeurs numériques négatives ni les kilométrages au-dessus de `MILES_MAXIMUM` (250 000 miles) ;
  - avec les majuscules harmonisées pour le modèle et la version ;
  - sans les marques qui ont moins de `minimum_annonces` annonces.
- **Pourquoi elle existe** : une ligne sans prix ne peut pas servir à l'entraînement, et un prix de 0 $ ou un kilométrage négatif sont impossibles. Les voitures très chères, les kilométrages absurdes et les marques presque absentes faussaient la droite pour toutes les autres voitures (les choix et leurs chiffres sont dans DECISIONS.md).
  - Les seuils sont des **constantes** en haut du fichier : pour les changer, on modifie une ligne, puis on relance `entrainer.py`.
  - `minimum_annonces` est un **paramètre** (10 par défaut) : les tests peuvent passer 1 pour nettoyer un petit tableau de 2 ou 3 voitures sans que tout disparaisse.
  - Les marques sont comptées **après** les autres filtres : une marque qui avait 12 annonces mais dont 5 coûtent plus de 100 000 $ n'en a vraiment que 7 pour apprendre. `groupby("make")["make"].transform("size")` donne, pour chaque ligne, le nombre d'annonces de sa marque.
  - `.copy()` avant d'harmoniser : on modifie des colonnes, et pandas avertit (`SettingWithCopyWarning`) si on modifie une partie filtrée d'un autre DataFrame.
- **Pourquoi écrite comme ça** :
  - `dropna(subset=COLONNES)` renvoie une copie, donc le DataFrame reçu **n'est pas modifié**. Un test le vérifie. Modifier les données de l'appelant en cachette est une source classique de bogues.
  - `(propre[COLONNES_NUMERIQUES] >= 0).all(axis=1)` donne « toutes les colonnes numériques de la ligne sont ≥ 0 ». **Sans le `.all(axis=1)`**, pandas tente de combiner une colonne (Series) avec un tableau (DataFrame). Sur le vrai CSV, le programme bloquait : c'est un bogue qu'on a eu.
  - `reset_index(drop=True)` renumérote les lignes 0, 1, 2… Sinon l'index garde les « trous » des lignes retirées.
  - On garde les voitures à 0 mile : une voiture neuve chez un concessionnaire est un cas réel.

### Classe `Variable` (abstraite)

- **Ce qu'elle fait** : elle décrit une caractéristique que l'utilisateur doit saisir. Elle a un `nom` (la colonne), une `etiquette` (le texte affiché) et deux méthodes abstraites, `valider` et `vers_dict`.
- **Pourquoi elle existe** : on a deux sortes de saisies (nombres et listes), mais l'application veut les traiter **de la même façon**, avec une seule boucle qui appelle `valider` sur chacune. C'est la classe parente commune.
- **Pourquoi écrite comme ça** :
  - `ABC` et `@abstractmethod` : on ne peut pas créer une `Variable` « tout court » (`Variable("x")` lève `TypeError`, et un test le vérifie). Toute sous-classe est aussi **obligée** d'écrire `valider` et `vers_dict`.
  - `self._nom` et `self._etiquette` : le `_` signale un attribut protégé, à ne pas modifier de l'extérieur.
  - `@property nom` et `etiquette` permettent de lire `variable.nom` comme un attribut, sans pouvoir écrire `variable.nom = ...`. C'est de l'encapsulation.
  - `etiquette if etiquette else nom` : sans étiquette, on affiche le nom de la colonne. Les tests peuvent ainsi créer des variables sans étiquette.

### Classe `VariableNumerique(Variable)`

- **Ce qu'elle fait** : c'est une variable bornée par `[minimum, maximum]`, éventuellement limitée aux nombres entiers. Par exemple, `VariableNumerique("year", 1994, 2022, entier=True, etiquette="Année")`.
- **Pourquoi elle existe** : elle sert pour l'année, le kilométrage et la cylindrée.

**`__init__`**
- Elle lève `ValueError` si `minimum > maximum`. C'est une `ValueError` et non une `DonneeInvalideError`, parce que ce serait une **erreur de programmation** et pas une erreur de l'utilisateur.
- Elle convertit les bornes en `float`, parce que pandas renvoie parfois des types NumPy (`np.int64`). On veut des nombres Python ordinaires.

**`valider(saisie)`** convertit le texte tapé, étape par étape. Chaque étape a sa raison :
1. `strip()` retire les espaces autour : « 2018 » tapé avec des espaces est accepté.
2. `replace(",", ".")` permet d'écrire « 2,5 » à la française, puisque Python attend « 2.5 ».
3. Un texte vide donne « Le champ « Année » est vide. »
4. `float(texte)` est placé dans un `try` / `except ValueError` : « abc » donne un message clair. `from None` cache l'erreur Python d'origine, pour que seul notre message apparaisse.
5. `math.isfinite` : `float()` accepte aussi « nan » et « inf », qu'il faut refuser.
6. `valeur.is_integer()`, seulement si `entier=True` : 2015.0 passe, mais 2015.5 donne « doit être un nombre entier ».
7. Les bornes : `self._minimum <= valeur <= self._maximum`. En Python, on peut enchaîner les comparaisons.
8. La fonction renvoie un `int` si la variable est entière, sinon un `float`.

Les messages utilisent l'**étiquette** (« Année ») et non le nom de colonne (`year`), parce que c'est ce que l'utilisateur voit à l'écran.

**`vers_dict()`** renvoie `{"nom", "etiquette", "type": "entier" ou "decimal", "minimum", "maximum"}`. C'est **exactement** le format que lit l'interface, ce qui évite d'avoir à convertir. Pour une variable entière, les bornes sont écrites en `int` : on lit « 1994 » au lieu de « 1994.0 ».

**`__eq__(autre)`** compare deux variables par leur contenu (nom, bornes, entier). Sans elle, `==` vérifierait seulement s'il s'agit du **même objet**, et les tests ne pourraient pas comparer une variable attendue à une variable créée. Le `return NotImplemented` pour un autre type laisse Python gérer le cas : la comparaison donne alors `False`.

**`__repr__()`** donne un affichage lisible, `VariableNumerique('year', 1994, 2022)`, au lieu de `<object at 0x...>`. C'est utile dans les messages d'erreur de pytest.

### Classe `VariableCategorielle(Variable)`

- **Ce qu'elle fait** : c'est une variable dont les valeurs permises sont une liste, par exemple les marques.
- **Pourquoi elle existe** : elle sert pour les 8 colonnes en texte.
- **Pourquoi écrite comme ça** :
  - `sorted(set(str(v) for v in valeurs))` : `set` retire les doublons, `sorted` trie (pour l'affichage), et `str` convertit au cas où pandas donnerait autre chose que du texte.
  - Une liste vide lève `ValueError` : une liste déroulante vide n'aurait pas de sens.
  - `@property valeurs` renvoie une **copie** (`list(...)`). Même si on modifie la liste reçue, la variable reste intacte.
  - `valider` **respecte les majuscules** (« honda » est refusé). Le modèle a appris « Honda » exactement. Avec « honda », le `OneHotEncoder` (option `handle_unknown="ignore"`) ignorerait la marque **sans prévenir**, et le prix serait faux.
  - `vers_dict()` renvoie `{"nom", "etiquette", "type": "categorie", "choix"}`.
  - `__eq__` et `__repr__` suivent le même principe que pour `VariableNumerique`.

### `creer_variables(df)`

- **Ce qu'elle fait** : elle renvoie la liste des 11 variables, d'abord les 3 numériques puis les 8 catégorielles, avec les bornes et les valeurs observées dans `df`.
- **Pourquoi elle existe** : l'interface doit savoir quels champs afficher, avec quelles bornes et quels choix. Ces informations viennent des données et sont écrites dans le JSON.
- **Pourquoi écrite comme ça** :
  - Les bornes sont le minimum et le maximum **observés**. Le modèle n'a rien appris en dehors de cet intervalle : une voiture de 1950 donnerait une extrapolation absurde.
  - `entrainer.py` l'appelle sur **`X_train`**, c'est-à-dire ce que le modèle a vraiment vu.
  - Pour `miles`, les bornes sont converties en km, parce que la variable décrit ce que l'utilisateur **saisit**. `math.floor` et `math.ceil` arrondissent vers l'extérieur (0 et 402 336 km, soit le plafond de 250 000 miles), pour ne refuser aucune valeur réelle.
  - `entier=colonne in COLONNES_ENTIERES` : l'expression `in` donne directement `True` ou `False`.
  - `ETIQUETTES.get(colonne)` renvoie `None` si une colonne n'a pas d'étiquette. La variable utilise alors son nom.

### `variable_depuis_dict(description)`

- **Ce qu'elle fait** : c'est l'inverse de `vers_dict()`. À partir de `{"nom": "year", "type": "entier", ...}`, elle recrée la `VariableNumerique` correspondante.
- **Pourquoi elle existe** : le JSON ne contient que des dictionnaires. Pour valider une saisie, il faut l'**objet**, puisque c'est lui qui a la méthode `valider`. `Estimateur` s'en sert au lancement de l'application.
- **Pourquoi écrite comme ça** :
  - `entier=genre == "entier"` donne `True` pour « entier » et `False` pour « decimal ».
  - Un type inconnu lève `ValueError`, plutôt que de créer une mauvaise variable sans rien dire.
  - Un test vérifie l'aller-retour : `variable_depuis_dict(v.vers_dict()) == v`.

### `construire_hierarchie(df)`

- **Ce qu'elle fait** : elle renvoie `{marque: {modèle: [versions]}}`, par exemple `{"Honda": {"Civic": ["DX", "EX", ...], ...}, ...}`.
- **Pourquoi elle existe** : on a 50 marques, 618 modèles et 771 versions. Une liste de 618 modèles serait inutilisable. Avec la hiérarchie, l'interface fait des listes **en cascade** : choisir Honda ne propose que les modèles Honda.
- **Pourquoi écrite comme ça** :
  - `drop_duplicates()` garde un seul exemplaire de chaque trio (marque, modèle, version).
  - `sort_values` trie les trios : les listes sont alors déjà dans l'ordre.
  - `astype(str)` force le texte, au cas où une version serait lue comme un nombre.
  - `setdefault(cle, valeur_par_defaut)` renvoie la valeur de la clé, en la créant d'abord si elle n'existe pas. On évite ainsi d'écrire « si la marque n'est pas encore dans le dictionnaire, l'ajouter ».

### `verifier_combinaison(hierarchie, marque, modele, version)`

- **Ce qu'elle fait** : elle ne renvoie rien si le trio existe. Sinon, elle lève `DonneeInvalideError` avec un message qui nomme la partie fautive.
- **Pourquoi elle existe** : chaque valeur peut exister séparément (« Honda », « Corolla ») sans que la combinaison « Honda Corolla » existe. Le modèle donnerait quand même un prix, qui n'aurait aucun sens.
- **Pourquoi écrite comme ça** : les trois vérifications sont faites **dans l'ordre** (marque, puis modèle de cette marque, puis version de ce modèle). La première qui échoue donne le message le plus précis possible.

### Classe `JeuDeDonnees`

- **Ce qu'elle fait** : elle garde les données nettoyées et sait les séparer en entraînement et test.
- **Pourquoi elle existe** : elle regroupe en un objet « les données prêtes à l'emploi ».
- **Pourquoi écrite comme ça** :
  - `__init__` appelle `nettoyer` : **impossible d'oublier le nettoyage**, puisqu'il se fait à la création.
  - `__len__` permet d'écrire `len(jeu)`, soit 33 333.
  - `separer(taille_test=0.2, graine=42)` :
    - Elle lève `ValueError` si `taille_test` n'est pas strictement entre 0 et 1, parce qu'un test de 0 % ou de 100 % n'a pas de sens.
    - `X` contient les 11 caractéristiques **sans le prix**. Sinon, le modèle « tricherait » en lisant la réponse.
    - `y` contient le prix.
    - `random_state=graine` : avec la même graine, on obtient la même séparation, donc les mêmes résultats à chaque lancement (reproductibilité).

---

## 3. `modele.py`

Ce fichier contient les métriques, le décorateur, les modèles, ainsi que la sauvegarde et le chargement.

### Les constantes

- `TOLERANCE = 2000.0` : le « à 2000 $ près » de l'objectif.
- `VERSION_SCHEMA_METADONNEES = 3` : le numéro de **forme** du JSON. Si on change sa structure, on change ce numéro, et un ancien fichier est refusé avec un message clair au lieu de planter plus loin.

### Les trois métriques : `taux_a_tolerance`, `erreur_absolue_moyenne`, `racine_erreur_quadratique`

- **Ce qu'elles font** :
  - `taux_a_tolerance` donne la proportion de prédictions à au plus 2000 $ du vrai prix (0,368, soit 36,8 %) ;
  - `erreur_absolue_moyenne` (MAE) donne l'erreur moyenne en dollars (3 988 $) ;
  - `racine_erreur_quadratique` (RMSE) donne une erreur qui punit fortement les grosses erreurs (14 988 $).
- **Pourquoi elles existent** :
  - La **MAE** est notre métrique principale, parce qu'elle se dit en une phrase : « on se trompe en moyenne de 3 988 $ ».
  - Le **taux à ±2000 $** correspond directement à l'objectif du projet.
  - La **RMSE** sert de comparaison : beaucoup plus grande que la MAE, elle montre que quelques très grosses erreurs existent (les voitures de luxe).
- **Pourquoi écrites comme ça** :
  - **Avec NumPy, sans boucle** : `np.abs(y_vrai - y_predit)` calcule toutes les erreurs d'un coup. C'est demandé par l'énoncé, et beaucoup plus rapide.
  - Des tableaux vides, des longueurs différentes ou une tolérance négative lèvent `ValueError` : une moyenne sur zéro élément n'a pas de sens.
  - `np.asarray(y_vrai, dtype=float)` : `y_vrai` est souvent une Series pandas, avec un index. Soustraire deux objets pandas les **aligne par index**, ce qui peut donner des résultats faux. En convertissant en tableau NumPy, on compare position par position.
  - `np.abs(...) <= tolerance` donne un tableau de `True` / `False`. Sa moyenne est directement la proportion de `True`.
  - Un test compare nos résultats à ceux de scikit-learn, pour prouver que nos formules sont justes.

### `chronometrer(fonction)` : le décorateur (outil du chapitre 7)

- **Ce qu'il fait** : il mesure la durée d'une fonction, sans modifier son code, et range la durée dans `fonction.derniere_duree`.
- **Pourquoi il existe** : l'énoncé demande au moins un outil du chapitre 7. On l'utilise sur `ModeleLineaire.entrainer`, et `entrainer.py` affiche « Entraînement de la régression : 0.07 s ».
- **Pourquoi écrit comme ça** :
  - `enveloppe(*args, **kwargs)` accepte **n'importe quels** arguments et les transmet à la vraie fonction. Le décorateur fonctionne donc sur n'importe quelle fonction.
  - `time.perf_counter()` est l'horloge la plus précise pour mesurer une durée.
  - `return resultat` : la fonction décorée renvoie **la même chose** qu'avant. Le décorateur est invisible pour l'appelant.
  - `@functools.wraps(fonction)` permet à `enveloppe` de garder le nom et la docstring de la vraie fonction.
  - On range la durée dans un attribut au lieu de l'afficher avec `print`. Elle est ainsi **testable**, et c'est `entrainer.py` qui décide de l'afficher.
  - `@chronometrer` au-dessus de `def entrainer` revient à écrire `entrainer = chronometrer(entrainer)`.

### Classe `ModelePrix` (abstraite)

- **Ce qu'elle fait** : c'est la classe parente des deux modèles. Elle oblige à écrire `entrainer` et `predire`, et fournit `evaluer` à tous.
- **Pourquoi elle existe** : le modèle de référence et la régression doivent pouvoir être **évalués de la même façon**. `evaluer` est écrite une seule fois et fonctionne pour les deux. C'est du polymorphisme.
- **Pourquoi écrite comme ça** :
  - `self._entraine = False` dans `__init__`, et `@property est_entraine` permet de le lire sans pouvoir le modifier de l'extérieur. C'est un bogue qu'on a eu : `self.est_entraine = True` échouait justement parce que la propriété est en lecture seule.
  - `evaluer` appelle `self.predire(X)` **une seule fois** et réutilise le résultat pour les 3 métriques, au lieu de prédire 3 fois.
  - `evaluer` ne sait pas si `self` est une référence ou une régression : chaque sous-classe a son propre `predire`.

### Classe `ModeleReference(ModelePrix)`

- **Ce qu'elle fait** : elle prédit **toujours** le prix moyen de l'entraînement, quelle que soit la voiture.
- **Pourquoi elle existe** : c'est le point de comparaison. Si notre régression ne battait pas « répondre toujours la moyenne », elle ne servirait à rien. Résultat : 9 671 $ d'erreur pour la référence, contre 3 988 $ pour la régression.
- **Pourquoi écrite comme ça** :
  - `entrainer` ne fait que calculer `float(np.mean(y))`.
  - `predire` renvoie `np.full(len(X), moyenne)`, c'est-à-dire un tableau de la bonne longueur rempli de la même valeur.
  - Elle lève `ModeleNonEntraineError` si on prédit avant d'entraîner.

### Classe `ModeleLineaire(ModelePrix)`

- **Ce qu'elle fait** : c'est la régression linéaire de scikit-learn, précédée d'un encodage des catégories.
- **Pourquoi elle existe** : c'est notre vrai modèle. On a choisi la régression linéaire parce qu'elle est simple, rapide et que chaque coefficient s'explique (« +X $ pour un an de moins »).

**`__init__(colonnes_numeriques, colonnes_categorielles)`**
- Elle lève `ValueError` si une des listes est vide.
- Elle prépare un `ColumnTransformer`, qui applique un traitement différent selon la colonne :
  - **colonnes catégorielles** : `OneHotEncoder` transforme « make = Honda » en une colonne `make_Honda` qui vaut 0 ou 1, une colonne par marque. La régression ne sait calculer qu'avec des nombres. Un encodage 1, 2, 3 inventerait un ordre entre les marques, ce qui n'a pas de sens.
  - **`handle_unknown="ignore"`** : une valeur jamais vue à l'entraînement ne fait pas planter le modèle.
  - **colonnes numériques** : `"passthrough"`, elles passent sans changement.

**`entrainer(X, y)`**, décorée par `@chronometrer` :
- Elle crée un `Pipeline` qui enchaîne la préparation puis la `LinearRegression`, et appelle `fit`.
- **Pourquoi un Pipeline** : à la prédiction, le **même** encodage, appris à l'entraînement, est appliqué automatiquement. Sans lui, il faudrait encoder à la main dans `predire`, avec le risque de le faire différemment.

**`predire(X)`** lève `ModeleNonEntraineError` si le modèle n'est pas entraîné. Sinon, elle renvoie `self._Pipeline.predict(X)`.

**`sauvegarder(chemin)`**
- Elle utilise `joblib.dump(self, chemin)` et sauvegarde **tout l'objet** `ModeleLineaire`, pas seulement le Pipeline.
- C'est un bogue qu'on a eu : en sauvegardant le Pipeline seul, l'objet relu n'avait pas de méthode `predire` (« 'Pipeline' has no attribute 'predire' »).
- Elle refuse de sauvegarder un modèle non entraîné.

**`charger(chemin)`** est un `@staticmethod` :
- Il s'appelle sur la classe, `ModeleLineaire.charger(...)`, parce qu'au moment de charger, **on n'a pas encore d'objet**.
- Il vérifie que le fichier existe, pour lever `FileNotFoundError` avec le chemin.

### `sauvegarder_metadonnees(chemin, variables, metriques, hierarchie)`

- **Ce qu'elle fait** : elle écrit `modeles/metadonnees.json` :
  ```json
  {"version_schema": 3,
   "variables": [{"nom": "miles", "etiquette": "Kilométrage (km)", "type": "entier", ...}, ...],
   "metriques": {"mae": 6468.9, "taux_2000": 0.267, ...},
   "hierarchie": [{"marque": "Acura", "modeles": [{"nom": "MDX", "versions": [...]}]}, ...]}
  ```
- **Pourquoi elle existe** : l'interface **se construit** à partir de ce fichier (les champs, les bornes, les choix, la cascade, la qualité affichée), sans relire le CSV ni réentraîner.
- **Pourquoi écrite comme ça** :
  - `variables` est une **liste** : l'interface affiche les champs dans cet ordre, et c'est le format qu'elle attend.
  - `hierarchie` est une liste de marques plutôt que des clés de dictionnaire. C'est l'idée d'Avery : chez BMW, il existe un modèle `I3` **et** un modèle `i3`, et des listes les gardent distincts dans tous les cas.
  - `indent=2` rend le fichier lisible, et `ensure_ascii=False` écrit « Année » au lieu de « Année ».
  - `with open(...)` ferme le fichier automatiquement, même en cas d'erreur.

### `charger_metadonnees(chemin)`

- **Ce qu'elle fait** : elle relit le JSON et renvoie un dictionnaire où la hiérarchie est redevenue `{marque: {modèle: [versions]}}`.
- **Pourquoi elle existe** : `main.py` en a besoin au lancement.
- **Pourquoi écrite comme ça** :
  - Un fichier absent lève `FileNotFoundError`, avec un message qui donne le chemin.
  - Un fichier **sans** `version_schema` (très ancien) est renvoyé tel quel, par compatibilité.
  - Une version différente de 3 lève `ValueError` avec la solution : « Relancez python src/entrainer.py ».
  - La hiérarchie est reconstruite en dictionnaires, la forme pratique pour `verifier_combinaison` et la cascade.

---

## 4. `entrainer.py`

Le script se lance avec `python src/entrainer.py`.

### Les constantes de chemins

`RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")` donne le dossier du projet, calculé **à partir de l'emplacement du fichier**. Le script fonctionne donc peu importe d'où on le lance. Les autres chemins (CSV, `modeles/`) en découlent.

`TAILLE_TEST = 0.2` et `GRAINE = 42` sont écrites en haut du fichier, pour être faciles à trouver et à changer.

`matplotlib.use("Agg")` dessine dans un fichier PNG, **sans ouvrir de fenêtre**. Le script marche donc aussi sur le serveur de GitHub Actions, qui n'a pas d'écran.

### `tracer_predit_contre_reel(y_reel, y_predit, chemin)`

- **Ce qu'elle fait** : elle enregistre le graphique « prix prédit contre prix réel ». Chaque point est une voiture du test, et la ligne rouge représente une prédiction parfaite.
- **Pourquoi elle existe** : le graphique montre **où** le modèle se trompe. Les voitures de luxe sont sous-estimées, et certaines prédictions sont négatives. Ce sont les limites à présenter.
- **Pourquoi écrite comme ça** :
  - `s=4, alpha=0.3` : les points sont petits et transparents. Sur 6 667 points, on voit ainsi où ils sont les plus nombreux.
  - La diagonale va de 0 à la plus grande valeur, réelle ou prédite.
  - `plt.close(fig)` libère la mémoire de la figure.
  - C'est une fonction séparée de `main` : une fonction égale une responsabilité.

### `main()`

Elle enchaîne les 7 étapes :
1. charger le CSV ;
2. nettoyer et séparer (`JeuDeDonnees`) ;
3. entraîner la référence et la régression, puis afficher la durée (`derniere_duree` du décorateur) ;
4. évaluer les deux modèles sur le **test**, des voitures jamais vues, pour que le score soit honnête ;
5. sauvegarder le modèle (`.joblib`), après `os.makedirs(..., exist_ok=True)` qui crée `modeles/` s'il n'existe pas ;
6. écrire les métadonnées, construites depuis `X_train`. Les métriques sont converties avec `float(...)` : NumPy renvoie des `np.float64`, que `json` ne sait pas écrire ;
7. tracer le graphique.

`if __name__ == "__main__":` : `main()` s'exécute seulement quand on **lance** le fichier, pas quand on l'importe (par exemple dans un test).

---

## 5. `application.py`

C'est la logique de l'application, sans Tkinter, testée à 100 %.

### `formater_prix(prix)`

- **Ce qu'elle fait** : `23450.4` donne `"23 450 $"`.
- **Pourquoi écrite comme ça** : `{prix:,.0f}` met un séparateur de milliers et arrondit au dollar (« 23,450 »). Ensuite, `.replace(",", " ")` remplace la virgule anglaise par une espace, à la française.
- **Pourquoi une fonction** : le même format sert à 4 endroits (résultat, métriques, tableau de l'historique, tolérance).

### `texte_metriques(metriques)`

- **Ce qu'elle fait** : elle fabrique le texte de l'encadré « Qualité du modèle » (MAE, % à ±2000 $, référence).
- **Pourquoi écrite comme ça** :
  - S'il manque une métrique, elle renvoie « non disponible » au lieu de planter.
  - Le pourcentage s'écrit à la française (« 36,8 % ») : on multiplie par 100, puis on remplace le point par une virgule.
  - La ligne de la référence n'est ajoutée que si elle existe.
  - `"\n".join(lignes)` colle les lignes avec un retour à la ligne entre chacune.

### `texte_resultat(prix, metriques)`

- **Ce qu'elle fait** : elle produit « Prix estimé : 23 057 $ », suivi d'une phrase qui rappelle l'erreur moyenne du modèle.
- **Pourquoi** : par honnêteté. Avec 36,8 % des prédictions à ±2000 $, on ne doit pas faire croire que le prix est exact.

### Classe `Estimateur`

- **Ce qu'elle fait** : elle transforme les textes saisis dans l'interface en prix prédit.
- **Pourquoi elle existe** : elle réunit en un objet le modèle, les variables et la hiérarchie, tout ce qu'il faut pour estimer.

**`__init__(modele, metadonnees)`** recrée les objets `Variable` depuis le JSON avec `variable_depuis_dict`, parce qu'on a besoin de leur méthode `valider`.

**`valider(saisies)`**
- Elle fait une boucle `for variable in self._variables:` et appelle `variable.valider(...)`. **C'est le polymorphisme** : la même ligne appelle `VariableNumerique.valider` pour l'année et `VariableCategorielle.valider` pour la marque.
- `saisies.get(variable.nom, "")` : un champ absent devient `""`, qui déclenchera le message « champ vide ».
- Elle appelle ensuite `verifier_combinaison` pour le trio marque/modèle/version.
- Elle renvoie des **valeurs converties** (`2018` en `int`, `2.0` en `float`), et plus du texte.

**`estimer(saisies)`**
1. Elle valide les saisies (ci-dessus).
2. Elle **copie** les caractéristiques (`dict(...)`) et convertit, dans la copie seulement, les km en miles. Le modèle reçoit des miles, alors que l'historique garde les km tapés par l'utilisateur.
3. Elle construit `pd.DataFrame([entrees_modele])`, un tableau d'**une seule ligne**. Le modèle a été entraîné sur un DataFrame, il en veut donc un même pour une seule voiture. `[COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES]` met les colonnes dans l'ordre de l'entraînement.
4. `float(self._modele.predire(X)[0])` : `predire` renvoie un tableau, et `[0]` prend le premier et seul prix.
5. Si le prix est ≤ 0, elle lève `EstimationImpossibleError`. La régression linéaire peut donner un prix négatif pour une combinaison rare, et afficher « -12 000 $ » n'aurait aucun sens.

### Classe `Historique`

- **Ce qu'elle fait** : elle garde la liste des estimations et la sauvegarde dans `donnees/historique.json`. Chaque estimation a la forme `{"date_heure", "prix_estime", "caracteristiques"}`.
- **Pourquoi elle existe** : l'onglet Historique de l'interface. Les estimations sont gardées d'un lancement à l'autre.

**`__init__(chemin=None)`**
- Si le fichier existe, elle relit les anciennes estimations.
- Avec `chemin=None`, l'historique reste en mémoire seulement. C'est pratique pour les tests, qui n'écrivent alors aucun fichier.
- Un JSON abîmé (`JSONDecodeError`) ou qui ne contient pas une liste lève `ValueError`, avec un message qui dit quoi faire. C'est l'idée d'Avery : quelqu'un a peut-être modifié le fichier à la main.

**`__len__`** permet d'écrire `len(historique)`.

**`@property lignes`** renvoie une **copie** de la liste : l'extérieur ne peut pas modifier l'historique par accident.

**`ajouter(prix, caracteristiques, date_heure=None)`**
- `date_heure or datetime.now()` : sans date, on prend l'heure actuelle. Le paramètre existe pour que les tests puissent donner une date fixe et vérifier le résultat exact.
- `strftime("%Y-%m-%d %H:%M:%S")` transforme la date en texte, parce que JSON ne sait pas stocker un objet `datetime`.
- On sauvegarde **à chaque ajout** : si l'application se ferme mal, rien n'est perdu.

**`sauvegarder()`** suit le même principe que `sauvegarder_metadonnees`. Elle ne fait rien s'il n'y a pas de chemin.

### `creer_rappels(estimateur, historique, metriques)`

- **Ce qu'elle fait** : elle **fabrique et renvoie deux fonctions**, `on_prediction` et `on_actualiser_historique`, que l'interface appelle au clic.
- **Pourquoi elle existe** : l'interface attend une fonction `on_prediction(interface, saisies)`. Pour prédire, cette fonction a besoin de l'estimateur, de l'historique et des métriques, que l'interface ne connaît pas.
- **Pourquoi écrite comme ça** :
  - `on_prediction` est définie **à l'intérieur** de `creer_rappels`. Elle peut donc utiliser `estimateur`, `historique` et `metriques`, et s'en souvient même après la fin de `creer_rappels`. On appelle ça une **fermeture** (*closure*). C'est le même mécanisme que dans le décorateur, où `enveloppe` utilise `fonction`.
  - **Ordre des étapes** : on estime, puis on **affiche le prix**, puis on sauvegarde. C'est l'idée d'Avery : si la sauvegarde échoue (`OSError` : disque plein, fichier verrouillé), l'utilisateur a quand même sa réponse.
  - `try` / `finally` : le tableau de l'historique est mis à jour **même si** la sauvegarde échoue.
  - Les erreurs (`DonneeInvalideError`, `EstimationImpossibleError`, `OSError`) ne sont pas attrapées ici. Elles « remontent » jusqu'à l'interface, qui sait comment les afficher.

---

## 6. `interface.py`

C'est la fenêtre Tkinter. La mise en page d'origine est celle d'Avery.

### `CASCADE = ["make", "model", "trim"]`

C'est l'ordre des listes en cascade. Choisir un champ vide et recalcule ceux qui **le suivent** dans cette liste.

### `options_cascade(hierarchie, nom, selection)`

- **Ce qu'elle fait** : elle renvoie les choix permis pour `model` (les modèles de la marque choisie) ou `trim` (les versions du modèle choisi). La liste est vide si le champ précédent n'est pas choisi.
- **Pourquoi elle existe** : c'est le cœur de la cascade. C'est une fonction **hors de la classe**, donc testable sans fenêtre.
- **Pourquoi écrite comme ça** :
  - `hierarchie.get(..., {})` : si rien n'est choisi, on obtient un dictionnaire vide au lieu d'une erreur.
  - `sorted(choix, key=str.casefold)` trie sans tenir compte des majuscules (`i3` arrive entre `G` et `M`). C'est l'idée d'Avery.
  - Un autre nom de champ lève `ValueError`.

### `_formater_borne(valeur)`

- **Ce qu'elle fait** : `402336` donne `"402 336"`, et `0.6` donne `"0.6"`.
- **Pourquoi** : le format `:g` affichait « 1.60934e+06 » pour les grands nombres, illisible pour l'utilisateur.
- **Le `_` au début** signale une fonction « interne » au module.

### Classe `InterfaceUtilisateur(ttk.Frame)`

- **Ce qu'elle fait** : c'est tout le contenu de la fenêtre (avertissement, onglet d'estimation, onglet d'historique).
- **Pourquoi elle hérite de `ttk.Frame`** : elle **est** un cadre Tkinter, qu'on peut placer dans la fenêtre et qui contient les autres éléments. C'est l'héritage d'une classe d'une bibliothèque.

**`__init__(parent, metadonnees, on_prediction, on_actualiser_historique)`**
- Elle garde les métadonnées, la hiérarchie et les deux fonctions de rappel, puis construit la fenêtre.
- **L'interface ne connaît pas le modèle** : elle reçoit seulement des fonctions à appeler. On pourrait la brancher sur un autre modèle sans la modifier.

**`_construire_fenetre()`** crée :
- l'avertissement pédagogique (l'estimation n'est pas un conseil financier) ;
- les deux onglets (`ttk.Notebook`) ;
- le panneau de saisie et le bouton « Prédire » ;
- la zone de résultat en gros caractères ;
- l'encadré « Qualité du modèle », rempli par `texte_metriques`.

`grid` place les éléments en lignes et colonnes, et `columnconfigure(..., weight=1)` permet à une colonne de s'agrandir avec la fenêtre.

**`_construire_champs(parent)`**
- Elle crée un champ par variable du JSON. Le type de la variable donne le genre du champ : une liste déroulante (`Combobox`) pour « categorie », une zone de texte (`Entry`) sinon.
- `index // 6` et `index % 6` placent 6 champs par colonne. `//` est la division entière et `%` le reste.
- `state="readonly"` : on ne peut que choisir dans la liste, pas taper n'importe quoi. Cela évite les fautes de frappe.
- `Modèle` et `Version` commencent **vides** : il faut d'abord choisir la marque.
- **`lambda evenement, nom=nom: self._actualiser_choix(nom)`** :
  - C'est une fonction anonyme (`lambda`, chapitre 7), appelée quand on choisit une valeur.
  - Le **`nom=nom`** est indispensable. Sans lui, les trois `lambda` créées dans la boucle utiliseraient toutes la **dernière** valeur de `nom` (`trim`), parce que Python lit la variable au moment de l'appel et non à la création. Avec `nom=nom`, chaque `lambda` garde sa propre valeur.
  - `evenement` est l'information que Tkinter envoie toujours. On ne s'en sert pas.
- Pour les nombres, l'étiquette affiche les bornes, par exemple « Année (1994 à 2022) ».

**`_actualiser_choix(variable_modifiee)`**
- Pour chaque champ qui **suit** le champ modifié dans `CASCADE`, elle le vide (`set("")`) puis recalcule ses choix avec `options_cascade`.
- Choisir une marque vide donc Modèle et Version. Choisir un modèle vide seulement Version.
- `if nom not in self.champs_categoriels: continue` : la fonction ne plante pas si un champ n'existe pas.

**`_construire_historique(parent)`** crée :
- le tableau (`ttk.Treeview`) de 3 colonnes : date, prix et véhicule ;
- une barre de défilement reliée au tableau. `yscrollcommand` et `yview` les relient dans les deux sens ;
- une zone de détails, désactivée pour qu'on ne puisse pas écrire dedans ;
- le bouton « Actualiser ».

**`_demander_prediction()`** est appelée par le bouton « Prédire ». Elle lit tous les champs, puis appelle `on_prediction`. Chaque type d'erreur a sa réaction :

| Erreur | Réaction | Pourquoi |
|---|---|---|
| `DonneeInvalideError`, `ValueError` | boîte d'avertissement | l'utilisateur doit corriger sa saisie |
| `EstimationImpossibleError` | message dans la zone de résultat | ce n'est pas une faute de l'utilisateur |
| `OSError` | statut et boîte d'erreur | le prix est affiché, seule la sauvegarde a échoué |
| aucune (`else`) | « Estimation ajoutée à l'historique » | confirmation |

**`_demander_actualisation()`** est appelée par le bouton « Actualiser ». Elle appelle `on_actualiser_historique`.

**`_afficher_details()`** affiche toutes les caractéristiques de l'estimation cliquée, avec leurs étiquettes françaises. Le tableau montre **la plus récente en premier**, alors que la liste va de la plus ancienne à la plus récente. On inverse donc l'indice : `len(...) - 1 - index`.

**`afficher_resultat(texte)`** change le texte de la zone de résultat. C'est une `tk.StringVar` : modifier la variable met l'affichage à jour automatiquement.

**`afficher_historique(lignes)`** vide le tableau, puis le remplit avec `reversed(lignes)` pour avoir la plus récente en haut. `iid=str(index)` donne un identifiant à chaque ligne, que `_afficher_details` relit.

`afficher_resultat` et `afficher_historique` n'ont **pas de `_`** : ce sont les deux méthodes que l'extérieur (`creer_rappels`) a le droit d'appeler.

### `lancer_interface(metadonnees, on_prediction, on_actualiser_historique, lignes_historique)`

- **Ce qu'elle fait** : elle crée la fenêtre (`tk.Tk()`), donne le titre et la taille, affiche l'historique existant, puis appelle `mainloop()`.
- `mainloop()` « attend » les clics jusqu'à ce qu'on ferme la fenêtre. La fonction ne se termine qu'à ce moment-là.

---

## 7. `main.py`

Le script se lance avec `python src/main.py`.

### Les constantes de chemins

Elles suivent le même principe que dans `entrainer.py` (à partir de `__file__`). L'historique est dans `donnees/historique.json`, avec les autres données. Ce fichier est ignoré par Git, parce que chaque utilisateur a son propre historique.

### `main()`

1. Elle charge le modèle et les métadonnées. Si un fichier manque ou si le JSON est d'une ancienne version, elle **affiche un message et s'arrête proprement** (« Entraînez d'abord le modèle avec : python src/entrainer.py »), au lieu d'afficher une longue erreur Python.
2. Elle charge l'historique. Un fichier abîmé donne aussi un message clair.
3. Elle crée l'`Estimateur`, puis les deux rappels avec `creer_rappels`.
4. Elle ouvre la fenêtre avec `lancer_interface`.

`main.py` est volontairement **court** : il ne fait que relier les morceaux. Toute la logique est dans `application.py`, où elle est testée.

---

## 8. Les classes « fausses » des tests

Les tests utilisent de petites classes qui **remplacent** les vraies, pour tester un morceau à la fois.

| Classe (fichier) | Remplace | Pourquoi |
|---|---|---|
| `FauxModele` (`test_application.py`) | `ModeleLineaire` | renvoie toujours le prix qu'on lui donne, ce qui permet de tester un prix négatif. Elle garde aussi le `X` reçu, pour vérifier que le modèle reçoit bien des miles |
| `FausseInterface` (`test_application.py`) | la fenêtre | garde ce qu'on lui demande d'afficher, sans ouvrir de fenêtre |
| `FauxChamp` (`test_interface.py`) | `ttk.Combobox` | possède les mêmes méthodes `get`, `set` et `configure`, pour tester la cascade sans Tkinter |

**Pourquoi ça marche** : `Estimateur` et `creer_rappels` n'exigent pas un type précis. Ils appellent seulement `predire` ou `afficher_resultat`. Tout objet qui a ces méthodes convient. C'est aussi une forme de polymorphisme.

---

## 9. Où se trouvent les notions du cours

| Notion | Où dans le code |
|---|---|
| Classes abstraites (`ABC`) | `Variable`, `ModelePrix` |
| Héritage | `VariableNumerique` et `VariableCategorielle` héritent de `Variable` ; `ModeleReference` et `ModeleLineaire` de `ModelePrix` ; `InterfaceUtilisateur` de `ttk.Frame` |
| Polymorphisme | `Estimateur.valider` (boucle sur `variable.valider`) ; `ModelePrix.evaluer` (appelle le `predire` de la sous-classe) |
| Encapsulation (`_attribut`, `@property`) | `_nom`, `_etiquette`, `_entraine`, `valeurs` et `lignes` qui renvoient des copies |
| Méthodes spéciales | `__eq__`, `__repr__` (variables), `__len__` (`JeuDeDonnees`, `Historique`) |
| Méthode statique | `ModeleLineaire.charger` |
| Exceptions personnalisées | `exceptions.py` |
| Fichiers (`with open`) | `sauvegarder_metadonnees`, `charger_metadonnees`, `Historique` |
| NumPy vectorisé | les trois métriques |
| pandas | `nettoyer`, `extraire_quebec`, `construire_hierarchie`, `separer` |
| Décorateur (ch. 7) | `chronometrer` sur `ModeleLineaire.entrainer` |
| `lambda` (ch. 7) | les listes en cascade dans `_construire_champs` |
| Fermeture (fonction dans une fonction) | `enveloppe` dans `chronometrer`, et `on_prediction` dans `creer_rappels` |
