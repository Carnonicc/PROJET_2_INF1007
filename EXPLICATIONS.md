# Explication de ce que l'IA (Claude) a ajouté au projet

Ce document explique **chaque fichier écrit ou modifié avec l'aide de Claude**, ligne par ligne ou bloc par bloc. Le but : que nous puissions tous les deux expliquer ce code à l'auxiliaire, puisqu'il peut nous interroger sur n'importe quelle ligne.

Point important : **la plupart des fonctions de `src/` sont des squelettes**. Elles ont un nom, des paramètres typés, une docstring, et le corps est `raise NotImplementedError`. **C'est à nous de les écrire.** Les tests décrivent exactement ce qu'elles doivent faire : tant qu'une fonction n'est pas écrite, ses tests échouent ; quand elle est bien écrite, ils passent.

---

## Sommaire

1. [Vue d'ensemble : ce qui a changé](#1-vue-densemble--ce-qui-a-changé)
2. [Configuration : `pytest.ini`, `requirements.txt`, workflow CI](#2-configuration)
3. [`src/exceptions.py`](#3-srcexceptionspy)
4. [`src/donnees.py`](#4-srcdonneespy)
5. [`src/modele.py`](#5-srcmodelepy)
6. [Notions de pytest à connaître](#6-notions-de-pytest-à-connaître)
7. [`tests/test_donnees.py`, test par test](#7-teststest_donneespy-test-par-test)
8. [`tests/test_modele.py`, test par test](#8-teststest_modelepy-test-par-test)
9. [Comment les tests ont été vérifiés](#9-comment-les-tests-ont-été-vérifiés)
10. [`DECISIONS.md`](#10-decisionsmd)
11. [Ce qu'il nous reste à faire](#11-ce-quil-nous-reste-à-faire)

---

## 1. Vue d'ensemble : ce qui a changé

| Fichier | Action | Résumé |
| --- | --- | --- |
| `src/donnes.py` → `src/donnees.py` | renommé (`git mv`) + réécrit | Orthographe de l'énoncé. Le script est devenu une fonction + squelette des classes de variables. |
| `tests/test_donnes.py` → `tests/test_donnees.py` | renommé + réécrit | Tests des données. |
| `src/exceptions.py` | écrit (complet) | Deux exceptions personnalisées. |
| `src/modele.py` | écrit (squelette) | Métriques, décorateur, modèles, sauvegarde. |
| `tests/test_modele.py` | réécrit | Tests du modèle. |
| `pytest.ini` | créé | Dit à pytest où trouver le code. |
| `requirements.txt` | rempli | Bibliothèques à installer. |
| `.github/workflows/tests.yml` | rempli | Lance les tests sur GitHub à chaque `push`. |
| `DECISIONS.md` | rempli | Fiche de décisions. |

`git mv` renomme un fichier **en gardant son historique Git** (contrairement à supprimer puis recréer).

---

## 2. Configuration

### `pytest.ini`

```ini
[pytest]
pythonpath = src
testpaths = tests
```

- `[pytest]` : section lue par pytest au démarrage.
- `pythonpath = src` : ajoute le dossier `src/` aux endroits où Python cherche les modules. C'est ce qui permet d'écrire `from donnees import ...` dans les tests, au lieu de `from src.donnees import ...`. Même logique que quand on lance `python src/main.py` : `main.py` pourra faire `import donnees` directement.
- `testpaths = tests` : quand on tape juste `pytest`, il cherche les tests dans `tests/` seulement.

### `requirements.txt`

```
pandas>=2.2
numpy>=1.26
scikit-learn>=1.5
joblib>=1.4
matplotlib>=3.8
pytest>=8.0
coverage>=7.4
```

Liste des bibliothèques que `pip install -r requirements.txt` installe. `>=` veut dire « cette version ou plus récente » : on évite ainsi d'utiliser une version trop ancienne sans bloquer les mises à jour.

- `pandas` : lire et manipuler le CSV (DataFrame).
- `numpy` : calculs vectorisés (nos métriques).
- `scikit-learn` : régression linéaire, encodage one-hot, `train_test_split`.
- `joblib` : sauvegarder le modèle entraîné dans un fichier (installé avec scikit-learn, mais on l'écrit explicitement car on l'importe nous-mêmes).
- `matplotlib` : graphiques.
- `pytest` : lancer les tests. `coverage` : mesurer quel pourcentage du code est exécuté par les tests (exigé dans le README).
- **Tkinter n'y est pas** : il est inclus avec Python, rien à installer.

### `.github/workflows/tests.yml`

```yaml
name: Tests                      # nom affiché dans l'onglet « Actions » de GitHub

on:                              # QUAND le workflow se lance :
  push:                          #   à chaque push sur n'importe quelle branche
  pull_request:                  #   et à chaque pull request

jobs:
  tests:                         # un « job » nommé tests
    runs-on: ubuntu-latest       # GitHub prête une machine Linux vide

    steps:                       # étapes exécutées dans l'ordre
      - name: Récupérer le code
        uses: actions/checkout@v4          # copie notre dépôt sur la machine

      - name: Installer Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.13"           # même version que sur nos ordis
          cache: pip                       # garde les paquets en cache : CI plus rapide

      - name: Installer les dépendances
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt

      - name: Lancer les tests avec couverture
        run: |
          coverage run --source=src -m pytest -v   # lance pytest en mesurant la couverture de src/
          coverage report -m                       # affiche le % couvert et les lignes non couvertes
```

Si un test échoue, la commande `pytest` renvoie une erreur → l'étape échoue → croix rouge sur le commit. Tous les tests passent → marque verte. **L'énoncé exige que le dernier commit soit vert.**

Pour faire la même chose sur nos ordis :

```
pip install -r requirements.txt
coverage run --source=src -m pytest
coverage report -m
```

---

## 3. `src/exceptions.py`

```python
class DonneeInvalideError(Exception):
    """Levée quand une donnée (fichier, colonne ou saisie utilisateur) est invalide."""


class ModeleNonEntraineError(Exception):
    """Levée quand on demande une prédiction à un modèle qui n'a pas été entraîné."""
```

- Une **exception personnalisée** est une classe qui **hérite de `Exception`**. Pas besoin de corps : la docstring suffit (une classe doit contenir au moins une instruction, et la docstring en est une).
- On la lève avec `raise DonneeInvalideError("message")` et on l'attrape avec `except DonneeInvalideError as e:`.
- Pourquoi nos propres exceptions plutôt que `ValueError` partout ? Pour que l'interface puisse attraper **précisément** les erreurs de saisie (`DonneeInvalideError`) et afficher un message clair, sans attraper par accident d'autres bugs. L'énoncé exige au moins une exception personnalisée levée avec `raise`.
- `DonneeInvalideError` : fichier sans les bonnes colonnes, saisie vide, texte au lieu d'un nombre, valeur hors intervalle, marque inconnue…
- `ModeleNonEntraineError` : on appelle `predire()` ou `sauvegarder()` sur un modèle jamais entraîné.

---

## 4. `src/donnees.py`

### Imports et constantes

```python
import os
from abc import ABC, abstractmethod

import pandas as pd

from exceptions import DonneeInvalideError

CIBLE = "price"
COLONNES_NUMERIQUES = ["miles", "year", "engine_size"]
COLONNES_CATEGORIELLES = ["make", "model", "trim", "body_type", "drivetrain",
                          "transmission", "fuel_type", "engine_block"]
COLONNES = [CIBLE] + COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES
```

- `os` : vérifier qu'un fichier existe (`os.path.exists`), construire des chemins (exigence ch. 5).
- `ABC`, `abstractmethod` : pour créer une **classe abstraite** (voir `Variable`).
- Les constantes (en MAJUSCULES par convention) regroupent les noms de colonnes à **un seul endroit**. Si on retire une colonne un jour, on change une ligne, pas dix.
- `COLONNES` : la cible + les 11 caractéristiques = les 12 colonnes du CSV du Québec.

### `extraire_quebec` (notre ancien script, transformé en fonction)

```python
def extraire_quebec(chemin_source: str, chemin_sortie: str) -> int:
    if not os.path.exists(chemin_source):
        raise FileNotFoundError(chemin_source)
    db = pd.read_csv(chemin_source)
    condition = db[COLONNES].notna().all(axis=1) & (db["state"] == "QC")
    resultat = db.loc[condition].drop_duplicates(subset="vin", keep="first")[COLONNES]
    resultat.to_csv(chemin_sortie, index=False)
    return len(resultat)
```

C'est **exactement notre code d'avant**, mis dans une fonction. Pourquoi ? Avant, le code était au niveau du module : **dès qu'on faisait `import donnees`, il relisait le fichier de 69 Mo et réécrivait le CSV**. Les tests importent ce module, donc chaque lancement des tests aurait refait tout ça (et planté en CI si le gros fichier est absent).

- `db[COLONNES].notna()` : tableau de Vrai/Faux, Vrai si la case n'est pas vide.
- `.all(axis=1)` : pour chaque **ligne**, Vrai si **toutes** ses colonnes sont remplies.
- `& (db["state"] == "QC")` : ET la province est le Québec. `&` combine deux conditions pandas (on ne peut pas utiliser `and` avec pandas).
- `db.loc[condition]` : garde les lignes où la condition est Vraie.
- `drop_duplicates(subset="vin", keep="first")` : une seule ligne par VIN (numéro unique du véhicule).
- `[COLONNES]` : ne garde que les 12 colonnes utiles.
- `to_csv(..., index=False)` : écrit le fichier sans la colonne d'index de pandas.
- `return len(resultat)` : renvoie le nombre de lignes au lieu de faire `print` (ch. 6 : les fonctions de calcul **retournent**, l'affichage est ailleurs).

### Fonctions à écrire (squelettes)

| Fonction | Reçoit | Renvoie | Erreurs attendues |
| --- | --- | --- | --- |
| `charger_csv(chemin)` | chemin du CSV | DataFrame | `FileNotFoundError` si absent ; `DonneeInvalideError` s'il manque une colonne de `COLONNES` |
| `nettoyer(df)` | DataFrame brut | **nouveau** DataFrame nettoyé, index remis à 0..n-1 | — |
| `creer_variables(df)` | DataFrame nettoyé | liste de `Variable` (3 numériques puis 8 catégorielles) | — |
| `construire_hierarchie(df)` | DataFrame nettoyé | `{marque: {modèle: [versions triées]}}` | — |
| `verifier_combinaison(h, marque, modele, version)` | hiérarchie + 3 saisies | `None` si OK | `DonneeInvalideError` dont le message contient la partie fautive |

Détails :

- **`nettoyer` ne doit pas modifier le DataFrame reçu** : on travaille sur une copie (`dropna`, filtrage avec des conditions… renvoient déjà de nouveaux DataFrames). Règles retenues : retirer les lignes avec une case vide dans `COLONNES`, les prix ≤ 0, les `miles` < 0. Une voiture à 0 mile est **gardée** (voiture neuve).
- **`construire_hierarchie`** sert aux **listes en cascade** de l'interface Tkinter : l'utilisateur choisit « Honda » → la liste des modèles ne montre que les modèles Honda → il choisit « Civic » → la liste des versions ne montre que les versions de Civic. On ne garde que les combinaisons qui existent vraiment dans les données.
- **`verifier_combinaison`** empêche une combinaison impossible (ex. Honda Corolla). Le message doit nommer ce qui ne va pas, pour afficher un message clair.

### Les classes de variables (héritage + polymorphisme)

```python
class Variable(ABC):
    def __init__(self, nom: str) -> None:
        self._nom = nom

    @property
    def nom(self) -> str:
        return self._nom

    @abstractmethod
    def valider(self, saisie: str): ...

    @abstractmethod
    def vers_dict(self) -> dict: ...
```

- `Variable(ABC)` : classe **abstraite**. On ne peut pas faire `Variable("x")` directement (Python lève `TypeError`) ; elle sert de modèle commun.
- `self._nom` : le `_` signale un attribut **protégé** (encapsulation) : on ne le modifie pas de l'extérieur.
- `@property` : permet de lire `variable.nom` comme un attribut, mais **sans pouvoir le modifier** (`variable.nom = "autre"` donnerait une erreur).
- `@abstractmethod` : chaque classe enfant **doit** redéfinir cette méthode, sinon elle reste abstraite.
- `valider(saisie)` : reçoit le texte tapé par l'utilisateur, le convertit et le vérifie, ou lève `DonneeInvalideError`.
- `vers_dict()` : décrit la variable pour le fichier JSON de métadonnées.

**Le polymorphisme** : l'interface pourra faire

```python
for variable in variables:
    valeur = variable.valider(texte_saisi)
```

sans savoir si c'est une variable numérique ou catégorielle : chacune valide **à sa façon**.

| | `VariableNumerique(nom, minimum, maximum)` | `VariableCategorielle(nom, valeurs)` |
| --- | --- | --- |
| Constructeur échoue si | `minimum > maximum` → `ValueError` | liste vide → `ValueError` |
| `valider("...")` renvoie | un `float` (espaces autour tolérés) | le texte sans espaces autour |
| `valider` lève `DonneeInvalideError` si | vide, pas un nombre, hors `[min, max]` (**bornes incluses**) | vide, ou pas dans la liste (**sensible aux majuscules** : « honda » ≠ « Honda ») |
| `vers_dict()` | `{"type": "numerique", "min": ..., "max": ...}` | `{"type": "categorielle", "valeurs": [...]}` |
| propriété en plus | — | `valeurs` : liste **triée** alphabétiquement |

Les deux redéfinissent aussi des **méthodes spéciales** (exigence ch. 9-11) :
- `__eq__` : permet `v1 == v2`. Deux variables sont égales si même nom et même intervalle (ou mêmes valeurs, peu importe l'ordre donné).
- `__repr__` : texte affiché quand on fait `print(repr(v))` ou dans le débogueur ; doit contenir le nom.

`super().__init__(nom)` dans les enfants appelle le constructeur de `Variable` pour stocker le nom.

### `JeuDeDonnees` (squelette)

| Méthode | Rôle |
| --- | --- |
| `__init__(df)` | reçoit le DataFrame brut, le **nettoie** (appelle `nettoyer`) et le garde dans un attribut protégé `self._df` |
| `__len__()` | méthode spéciale : `len(jeu)` donne le nombre de lignes après nettoyage |
| `separer(taille_test=0.2, graine=42)` | renvoie `(X_train, X_test, y_train, y_test)` avec `train_test_split` ; `X` = les 11 caractéristiques, `y` = le prix ; `ValueError` si `taille_test` n'est pas strictement entre 0 et 1 |

La **graine** (`random_state`) fixe le hasard : même graine → même découpage à chaque fois → résultats reproductibles (exigé par l'énoncé).

---

## 5. `src/modele.py`

### Constante et métriques (calcul vectorisé NumPy, ch. 12)

```python
TOLERANCE = 2000.0
```

| Fonction | Calcule | Formule NumPy (sans boucle) |
| --- | --- | --- |
| `taux_a_tolerance(y_vrai, y_predit, tolerance=2000)` | proportion de prédictions à **au plus** 2000 $ du vrai prix (entre 0 et 1) | `np.mean(np.abs(vrai - predit) <= tolerance)` |
| `erreur_absolue_moyenne` (MAE) | erreur moyenne en $ | `np.mean(np.abs(vrai - predit))` |
| `racine_erreur_quadratique` (RMSE) | comme la MAE mais punit plus les grosses erreurs | `np.sqrt(np.mean((vrai - predit) ** 2))` |

Pourquoi `np.mean` sur des Vrai/Faux donne une proportion : Vrai vaut 1, Faux vaut 0, donc la moyenne = nombre de Vrai / total.

Les trois lèvent `ValueError` si les tableaux sont **vides** ou de **longueurs différentes** (et `taux_a_tolerance` si la tolérance est négative).

MAE = métrique principale (« on se trompe en moyenne de X $ »), taux à ±2000 $ = métrique secondaire (notre objectif « à 2000 $ près »). Voir `DECISIONS.md`.

### Le décorateur `chronometrer` (outil du ch. 7)

C'est notre seul outil du chapitre 7. Un générateur `lire_par_blocs` avait d'abord été prévu, puis retiré : il n'était appelé nulle part, puisque notre CSV de 2,4 Mo se charge d'un coup sans problème.

Un décorateur est une fonction qui **enveloppe** une autre fonction pour lui ajouter un comportement. Usage prévu :

```python
@chronometrer
def entrainer(...):
    ...
```

À écrire : la fonction enveloppante note l'heure (`time.perf_counter()`), appelle la vraie fonction, calcule la durée, la range dans l'attribut `derniere_duree` de la fonction décorée, et **renvoie le résultat inchangé**.

### Les modèles (héritage + polymorphisme, encore)

```python
class ModelePrix(ABC):
    def __init__(self) -> None:
        self._entraine = False

    @property
    def est_entraine(self) -> bool:
        return self._entraine
```

- `ModelePrix` : classe abstraite parente. `self._entraine` passe à `True` après `entrainer()`.
- Méthodes abstraites : `entrainer(X, y)` et `predire(X)`.
- `evaluer(X, y)` (à écrire, **une seule fois dans la classe parente**) : appelle `self.predire(X)` puis renvoie `{"mae": ..., "rmse": ..., "taux_2000": ...}`. Comme elle appelle `predire`, elle marche automatiquement pour les deux enfants : c'est le polymorphisme.

| Classe enfant | `entrainer` | `predire` |
| --- | --- | --- |
| `ModeleReference` | calcule et retient la **moyenne** des prix d'entraînement | renvoie cette moyenne pour chaque ligne (`np.full`) |
| `ModeleLineaire(colonnes_numeriques, colonnes_categorielles)` | entraîne un pipeline scikit-learn : **one-hot** sur les colonnes texte + `LinearRegression` | renvoie un `np.ndarray` de prix |

Les deux lèvent `ModeleNonEntraineError` si on prédit avant d'entraîner.

**One-hot** : la régression linéaire ne comprend que des nombres. Le one-hot transforme `make` en une colonne 0/1 par marque (`make_Honda`, `make_Toyota`…). Chaque colonne reçoit son propre coefficient (« bonus » de prix). Avec `OneHotEncoder(handle_unknown="ignore")`, une valeur jamais vue à l'entraînement donne des 0 partout au lieu de planter.

Outils scikit-learn suggérés : `ColumnTransformer` (appliquer le one-hot seulement aux colonnes texte), `Pipeline` (enchaîner encodage + régression en un seul objet).

`ModeleLineaire` a aussi :
- `sauvegarder(chemin)` : `joblib.dump` ; `ModeleNonEntraineError` si pas entraîné.
- `charger(chemin)` (`@staticmethod` : appelée sur la classe, `ModeleLineaire.charger(...)`, pas sur un objet) : `joblib.load` ; `FileNotFoundError` si absent.

### Métadonnées JSON

```python
def sauvegarder_metadonnees(chemin, variables, metriques, hierarchie) -> None
def charger_metadonnees(chemin) -> dict
```

Format du JSON écrit :

```json
{
  "variables": {
    "year": {"type": "numerique", "min": 2000, "max": 2022},
    "make": {"type": "categorielle", "valeurs": ["Acura", "Toyota"]}
  },
  "metriques": {"mae": 3456.7, "taux_2000": 0.41},
  "hierarchie": {"Acura": {"MDX": ["Base", "Tech"]}}
}
```

L'interface lira ce fichier au lancement pour **se construire** (un champ par variable, les listes déroulantes, les cascades) sans réentraîner le modèle. Utiliser `with open(...)` et `json.dump` / `json.load`.

---

## 6. Notions de pytest à connaître

| Outil | À quoi ça sert | Exemple dans nos tests |
| --- | --- | --- |
| `def test_...():` | pytest exécute automatiquement toute fonction qui commence par `test_` | partout |
| `assert condition` | le test échoue si la condition est fausse | `assert len(df) == 20` |
| `pytest.raises(Erreur)` | le test **réussit seulement si** le bloc lève cette erreur | `with pytest.raises(FileNotFoundError): charger_csv("absent.csv")` |
| `pytest.raises(Erreur, match="Corolla")` | en plus, le message d'erreur doit contenir « Corolla » | test de `verifier_combinaison` |
| `pytest.approx(x)` | compare des flottants avec une petite tolérance (car `0.1 + 0.2 != 0.3` en informatique) | `assert mae == pytest.approx(...)` |
| `pytest.approx(x, abs=1)` | tolérance absolue de 1 (ici 1 $) | test de la régression |
| `@pytest.fixture` | fonction qui prépare des données réutilisées ; un test la reçoit en mettant son nom en paramètre | `df_petit`, `hierarchie`, `donnees_lineaires` |
| `tmp_path` | fixture **fournie par pytest** : un dossier temporaire neuf pour chaque test, effacé après. On ne salit pas le projet | tests de fichiers |
| `@pytest.mark.parametrize` | lance le même test avec plusieurs valeurs ; chaque valeur compte comme un test séparé | saisies invalides |
| `@pytest.mark.skipif(cond, reason=...)` | saute le test si la condition est vraie | test sur le vrai CSV, sauté s'il est absent |

Les trois sortes de cas demandées par l'énoncé : **usuel** (ça marche normalement), **limite** (pile sur la frontière : 0 mile, exactement 2000 $ d'écart, bornes de l'intervalle), **erreur** (`pytest.raises`).

---

## 7. `tests/test_donnees.py`, test par test

### Préparation commune

```python
CHEMIN_CSV_QC = os.path.join(os.path.dirname(__file__), "..", "donnees",
                             "ca-dealers-used-qc.csv")
```

Chemin vers le vrai CSV construit avec `os` (exigence ch. 5). `__file__` = chemin du fichier de test ; `dirname` = son dossier (`tests/`) ; `".."` = remonter d'un niveau. Ainsi ça marche peu importe d'où on lance pytest.

```python
def ligne(price=20000, miles=50000, year=2018, ...):
    return {"price": price, "miles": miles, ...}
```

Fabrique **une voiture valide** sous forme de dictionnaire. Chaque paramètre a une valeur par défaut : dans un test, on ne change que ce qui nous intéresse, ex. `ligne(price=-500)` = voiture valide sauf le prix. Ça rend les tests courts et lisibles.

```python
@pytest.fixture
def df_petit() -> pd.DataFrame:
    lignes = [ligne(price=10000 + 1000 * i, miles=5000 * i, year=2010 + i % 10,
                    make="Honda" if i % 2 else "Toyota")
              for i in range(20)]
    return pd.DataFrame(lignes)
```

Un petit jeu de **20 voitures valides** et variées (prix 10 000 à 29 000, années 2010 à 2019 grâce à `i % 10`, Honda pour i impair, Toyota pour i pair). Petit = tests rapides, et on connaît les bonnes réponses à l'avance.

### Fichiers

| Test | Vérifie | Type |
| --- | --- | --- |
| `test_charger_csv_fichier_valide` | on écrit `df_petit` dans un CSV temporaire, on le relit : 20 lignes et toutes les colonnes | usuel |
| `test_charger_csv_fichier_inexistant` | fichier absent → `FileNotFoundError` | erreur |
| `test_charger_csv_colonne_manquante` | CSV sans la colonne `year` → `DonneeInvalideError` | erreur |
| `test_vrai_jeu_respecte_criteres_enonce` | sur **notre vrai CSV** : entre 500 et 50 000 lignes, au moins 5 caractéristiques, prix numérique. Sauté si le fichier est absent | critères de l'énoncé |

### Nettoyage

| Test | Vérifie | Type |
| --- | --- | --- |
| `test_nettoyer_retire_valeurs_manquantes` | 3 lignes dont une sans marque (`None`) et une sans kilométrage (`nan`) → il en reste 1 | usuel |
| `test_nettoyer_retire_valeurs_aberrantes` | prix 0, prix négatif, miles négatif → retirés ; il reste la bonne ligne à 20 000 $ | erreur/aberrant |
| `test_nettoyer_garde_les_cas_limites_valides` | 0 mile et prix de 1 $ sont **gardés** (valeurs bizarres mais possibles) | limite |
| `test_nettoyer_ne_modifie_pas_l_original` | après `nettoyer(df)`, `df` a toujours ses 2 lignes : la fonction n'a pas d'effet de bord | bonne pratique |

### `VariableNumerique`

| Test | Vérifie | Type |
| --- | --- | --- |
| `test_variable_numerique_saisie_valide` | `"2015"` → `2015.0` ; `" 2018 "` (avec espaces) → `2018.0` | usuel |
| `test_variable_numerique_bornes_incluses` | intervalle [1.0, 6.5] : `"1.0"` et `"6.5"` acceptés | limite |
| `test_variable_numerique_saisie_invalide` (×6 avec `parametrize`) | `""`, `"   "` (vide), `"abc"`, `"12,5km"` (pas un nombre), `"0.99"`, `"6.51"` (juste hors bornes) → `DonneeInvalideError` | erreur + limite |
| `test_variable_numerique_bornes_inversees` | min 2022 > max 2000 → `ValueError` | erreur |

### `VariableCategorielle`

| Test | Vérifie | Type |
| --- | --- | --- |
| `test_variable_categorielle_saisie_valide` | `"Honda"` accepté ; `"  Acura "` → `"Acura"` | usuel |
| `test_variable_categorielle_saisie_invalide` (×3) | `""`, `"Ferrari"` (absente), `"honda"` (mauvaise casse) → `DonneeInvalideError` | erreur |
| `test_variable_categorielle_valeurs_triees` | `["Toyota", "Acura", "Honda"]` → `valeurs` donne `["Acura", "Honda", "Toyota"]` (pour une liste déroulante en ordre) | usuel |
| `test_variable_categorielle_liste_vide` | aucune valeur permise → `ValueError` | erreur |

### POO et `creer_variables`

| Test | Vérifie |
| --- | --- |
| `test_variable_est_abstraite` | `Variable("x")` → `TypeError` : la classe parente est bien abstraite |
| `test_polymorphisme_vers_dict` | la **même méthode** `vers_dict()` appelée sur deux types de variables donne deux résultats différents (`"numerique"` / `"categorielle"`) : c'est le polymorphisme |
| `test_egalite_et_repr` | `__eq__` : mêmes paramètres → égales ; borne différente → pas égales ; ordre des valeurs sans importance. `__repr__` contient le nom |
| `test_creer_variables_depuis_donnees` | à partir de `df_petit` : bons noms dans le bon ordre ; `year` va de 2010 à 2019 (min/max observés) ; `make` vaut `["Honda", "Toyota"]` |

### Hiérarchie (listes en cascade)

La fixture `hierarchie` construit la hiérarchie à partir de 5 voitures, dont un **doublon** (deux Honda Civic LX).

| Test | Vérifie | Type |
| --- | --- | --- |
| `test_construire_hierarchie_structure` | résultat exact : Honda → Accord [Touring], Civic [EX, LX] (doublon retiré, trié) ; Toyota → Corolla [LE] | usuel |
| `test_construire_hierarchie_vide` | DataFrame vide → `{}` | limite |
| `test_verifier_combinaison_valide` | Honda Civic EX existe → renvoie `None` sans erreur | usuel |
| `test_verifier_combinaison_invalide` (×3) | marque inconnue (Lada), modèle d'une autre marque (Honda Corolla), version d'un autre modèle (Civic Touring) → `DonneeInvalideError` **dont le message contient** la partie fautive | erreur |

### `JeuDeDonnees`

| Test | Vérifie | Type |
| --- | --- | --- |
| `test_jeu_de_donnees_nettoie_a_la_construction` | 20 bonnes voitures + 1 à prix négatif → `len(jeu) == 20` (le constructeur nettoie et `__len__` marche) | usuel |
| `test_separer_tailles_et_colonnes` | 25 % de test sur 20 lignes → 15 / 5 ; la cible `price` **n'est pas** dans `X` (sinon le modèle « tricherait ») ; les colonnes de `X` sont dans le bon ordre | usuel |
| `test_separer_reproductible_et_sans_chevauchement` | même graine → même ensemble de test ; aucune ligne à la fois dans l'entraînement et le test (on n'évalue jamais sur les données d'entraînement) | limite / rigueur |
| `test_separer_taille_test_invalide` (×4) | 0, 1, -0.2, 1.5 → `ValueError` | erreur |

---

## 8. `tests/test_modele.py`, test par test

### Fixture `donnees_lineaires`

```python
rng = np.random.default_rng(0)
n = 200
miles = rng.uniform(0, 150_000, n)
make = rng.choice(["Honda", "Toyota"], n)
X = pd.DataFrame({"miles": miles, "make": make})
y = pd.Series(30_000 - 0.1 * miles + np.where(make == "Toyota", 5000, 0))
```

On **fabrique** 200 voitures dont le prix suit une règle connue : 30 000 $ − 0,10 $ par mile, + 5 000 $ si Toyota.
- `default_rng(0)` : générateur aléatoire avec graine 0 → mêmes données à chaque lancement.
- `uniform(0, 150_000, n)` : 200 kilométrages au hasard entre 0 et 150 000.
- `choice([...], n)` : 200 marques au hasard.
- `np.where(cond, 5000, 0)` : 5000 là où c'est Toyota, 0 sinon (vectorisé).

Pourquoi ? Si notre régression linéaire est bien codée, elle **doit retrouver cette règle** presque parfaitement. Avec le vrai CSV, on ne connaîtrait pas la bonne réponse.

### Métriques

| Test | Vérifie | Type |
| --- | --- | --- |
| `test_taux_a_tolerance_cas_usuel` | écarts de 1000, 3000, 0, 2500 → 2 sur 4 sous 2000 $ → `0.5` | usuel |
| `test_taux_a_tolerance_borne_incluse` | écart d'**exactement** 2000 → compte ; écart de 2000,01 → ne compte pas → `0.5` | limite |
| `test_taux_a_tolerance_personnalisee` | tolérance 50 : écarts 50, 0, 100 → 2/3 | usuel |
| `test_metriques_entrees_invalides` (×2) | tableaux vides, ou de longueurs différentes → `ValueError` pour **les trois** métriques | erreur |
| `test_taux_a_tolerance_negative` | tolérance -1 → `ValueError` | erreur |
| `test_mae_et_rmse_identiques_a_scikit_learn` | 500 prix aléatoires : notre MAE = `mean_absolute_error` de scikit-learn, notre RMSE = `sqrt(mean_squared_error)`. C'est l'idée suggérée par l'énoncé (ch. 12) : prouver que notre calcul NumPy est juste | vérification |

### Décorateur

`test_chronometrer_garde_le_resultat_et_mesure` : on décore une petite fonction `addition` ; elle doit toujours renvoyer 5 pour (2, 3), et `addition.derniere_duree` doit exister et être ≥ 0.

### Modèles

| Test | Vérifie |
| --- | --- |
| `test_modele_reference_predit_la_moyenne` | prix d'entraînement 10k, 20k, 30k, 40k → prédit 25 000 pour n'importe quelle voiture |
| `test_predire_avant_entrainement` | pour les **deux** modèles : `est_entraine` vaut `False` et `predire` lève `ModeleNonEntraineError` |
| `test_modele_prix_est_abstrait` | `ModelePrix()` → `TypeError` |
| `test_modele_lineaire_retrouve_une_relation_lineaire` | après entraînement : Honda 0 mile → ≈ 30 000 $ ; Toyota 100 000 miles → 30 000 − 10 000 + 5 000 ≈ 25 000 $ (à 1 $ près) |
| `test_modele_lineaire_bat_la_reference` | la MAE de la régression est **plus petite** que celle de la moyenne : c'est la comparaison à la référence exigée par l'énoncé |
| `test_modele_lineaire_categorie_inconnue_ne_plante_pas` | une marque jamais vue (« Lada ») donne quand même **un** prix, et un vrai nombre (`np.isfinite` : pas `nan` ni infini). Vérifie le `handle_unknown="ignore"` |
| `test_evaluer_renvoie_les_trois_metriques` | `evaluer` renvoie exactement les clés `mae`, `rmse`, `taux_2000` ; sur ces données parfaites, 100 % sont à ±2000 $ ; et MAE ≤ RMSE (toujours vrai mathématiquement : une bonne vérification de cohérence) |

### Sauvegarde

| Test | Vérifie | Type |
| --- | --- | --- |
| `test_sauvegarder_puis_charger_donne_les_memes_predictions` | on sauvegarde, le fichier existe, on recharge : **mêmes prédictions** qu'avant. C'est ce qui garantit que l'interface utilisera bien le modèle entraîné | usuel |
| `test_sauvegarder_modele_non_entraine` | → `ModeleNonEntraineError` | erreur |
| `test_charger_modele_inexistant` | → `FileNotFoundError` | erreur |
| `test_metadonnees_aller_retour` | on écrit le JSON (variables, métriques, hiérarchie) puis on le relit : tout est identique, et les valeurs catégorielles sont triées | usuel |
| `test_charger_metadonnees_inexistant` | → `FileNotFoundError` | erreur |

---

## 9. Comment les tests ont été vérifiés

L'énoncé met en garde : « un test écrit d'après le code ne prouve pas grand-chose ». Ici, c'est l'inverse : **les tests ont été écrits avant le code**, d'après ce que chaque fonction doit faire.

Pour s'assurer que les tests eux-mêmes ne contiennent pas d'erreur, Claude a écrit une implémentation **temporaire, hors du projet** (dans un dossier jetable, jamais ajoutée au dépôt) et a lancé les tests dessus :

- contre cette implémentation temporaire : **62 tests passent** (y compris celui sur le vrai CSV) ;
- contre notre squelette actuel : ils échouent (normal, les fonctions ne sont pas écrites). Quelques-uns apparaissent comme « errors » au lieu de « failed » : c'est quand la **fixture** elle-même appelle une fonction pas encore écrite (`construire_hierarchie`).

Cette implémentation temporaire **ne nous est pas fournie exprès** : c'est à nous d'écrire le code (l'historique Git doit montrer notre travail à tous les deux).

---

## 10. `DECISIONS.md`

Tableau exigé par l'énoncé (colonnes : Choix · Options envisagées · Choix retenu et justification · Validé par l'auxiliaire). Rempli à partir de notre feuille de route et de nos réponses : domaine, jeu de données, CSV accepté par le chargé de projet, filtrage Québec, doublons, nettoyage, cible, métrique (MAE + ±2000 $), régression linéaire, `model`/`trim` gardés, Tkinter, etc.

À vérifier ensemble :
- les **dates** de validation sont à compléter (aucune n'a été inventée) ;
- les « options envisagées » pour le domaine et le jeu de données sont des suppositions : remplacer par ce qu'on a vraiment regardé ;
- la justification pour garder `model` et `trim` a été proposée par l'IA : la reformuler avec nos propres raisons ;
- encore à décider : le gros fichier de 69 Mo, la règle pour les marques rares.

---

## 11. Ce qu'il nous reste à faire

1. **Rendre la CI verte** : soit écrire les fonctions avant de pousser, soit mettre temporairement `@pytest.mark.skip(reason="à implémenter")` sur les tests pas encore réalisables, et les retirer au fur et à mesure.
2. **Écrire les fonctions de `src/`** en se répartissant le travail (pilote / copilote), en lançant `pytest` souvent.
3. Décider pour le fichier de 69 Mo et pour les marques rares (puis ajouter la règle dans `nettoyer` avec un test).
4. Créer `Prediction`, `Historique`, `Application` et l'interface Tkinter.
5. Ajouter des entrées dans `JOURNAL_IA.md` : génération des tests, du squelette, du workflow, de `DECISIONS.md` et de ce document, avec ce qu'on a vérifié.
