"""Lecture, nettoyage et description des données de voitures d'occasion du Québec.

Les tests de tests/test_donnees.py décrivent le comportement attendu.
"""

import math
import os
from abc import ABC, abstractmethod

import pandas as pd
from sklearn.model_selection import train_test_split

from exceptions import DonneeInvalideError

CIBLE = "price"
COLONNES_NUMERIQUES = ["miles", "year", "engine_size"]
COLONNES_CATEGORIELLES = ["make", "model", "trim", "body_type", "drivetrain",
                          "transmission", "fuel_type", "engine_block"]
COLONNES = [CIBLE] + COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES
# colonnes numériques qui n'acceptent que des nombres entiers (engine_size est décimal)
COLONNES_ENTIERES = ["miles", "year"]
# le CSV et le modèle sont en miles, mais l'utilisateur saisit des kilomètres
KILOMETRES_PAR_MILE = 1.609344
# texte affiché à l'utilisateur pour chaque colonne (interface et messages d'erreur)
ETIQUETTES = {
    "miles": "Kilométrage (km)",
    "year": "Année",
    "engine_size": "Cylindrée (litres)",
    "make": "Marque",
    "model": "Modèle",
    "trim": "Version",
    "body_type": "Type de carrosserie",
    "drivetrain": "Roues motrices",
    "transmission": "Boîte de vitesses",
    "fuel_type": "Type de carburant",
    "engine_block": "Configuration du moteur",
}


def miles_vers_kilometres(miles: float) -> float:
    """Convertit des miles en kilomètres (idée et code d'Avery)."""
    return miles * KILOMETRES_PAR_MILE


def kilometres_vers_miles(kilometres: float) -> float:
    """Convertit des kilomètres en miles (idée et code d'Avery)."""
    return kilometres / KILOMETRES_PAR_MILE


def extraire_quebec(chemin_source: str, chemin_sortie: str) -> int:
    """Filtre le jeu canadien complet pour ne garder que les annonces du Québec.

    Reçoit : le chemin du CSV complet et le chemin du CSV à écrire.
    Renvoie : le nombre de lignes écrites.
    Échoue : FileNotFoundError si le fichier source n'existe pas.
    """
    if not os.path.exists(chemin_source):
        raise FileNotFoundError(chemin_source)
    db = pd.read_csv(chemin_source)
    # lignes avec les 12 colonnes remplies et au Québec
    condition = db[COLONNES].notna().all(axis=1) & (db["state"] == "QC")
    # un seul exemplaire par VIN, puis on garde seulement les 12 colonnes
    resultat = db.loc[condition].drop_duplicates(subset="vin", keep="first")[COLONNES]
    resultat.to_csv(chemin_sortie, index=False)
    return len(resultat)


def charger_csv(chemin: str) -> pd.DataFrame:
    """Charge le CSV des voitures.

    Reçoit : le chemin du fichier CSV.
    Renvoie : un DataFrame contenant au moins les colonnes de COLONNES.
    Échoue : FileNotFoundError si le fichier n'existe pas ;
             DonneeInvalideError s'il manque une colonne de COLONNES.
    """
    if os.path.exists(chemin):
        df = pd.read_csv(chemin)
        manquantes = [c for c in COLONNES if c not in df.columns]
        if manquantes:
                raise DonneeInvalideError(f"Colonnes manquantes : {manquantes}")
        return df
    else:
        raise FileNotFoundError




def nettoyer(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie les données sans modifier le DataFrame reçu.

    Retire : les lignes avec une valeur manquante dans COLONNES,
             les prix <= 0, le kilométrage (miles) négatif.
    Reçoit : un DataFrame brut.
    Renvoie : un nouveau DataFrame nettoyé (index réinitialisé).
    """
    # 1. lignes complètes : dropna renvoie un NOUVEAU DataFrame, df n'est pas modifié
    propre = df.dropna(subset=COLONNES)
    # 2. valeurs impossibles : on garde les prix > 0 et les colonnes numériques >= 0
    #    .all(axis=1) : Vrai si TOUTES les colonnes numériques de la ligne sont >= 0
    valide = (propre[CIBLE] > 0) & (propre[COLONNES_NUMERIQUES] >= 0).all(axis=1)
    propre = propre[valide]
    # 3. index renuméroté 0, 1, 2... (sinon il garde des « trous »)
    return propre.reset_index(drop=True)


class Variable(ABC):
    """Variable d'entrée du modèle (classe parente abstraite)."""

    def __init__(self, nom: str, etiquette: str | None = None) -> None:
        """Reçoit le nom de la colonne et le texte à afficher (le nom par défaut)."""
        self._nom = nom
        self._etiquette = etiquette if etiquette else nom

    @property
    def nom(self) -> str:
        """Nom de la colonne correspondante."""
        return self._nom

    @property
    def etiquette(self) -> str:
        """Texte affiché à l'utilisateur (ex. « Année » pour year)."""
        return self._etiquette

    @abstractmethod
    def valider(self, saisie: str):
        """Convertit et valide une saisie texte de l'utilisateur.

        Échoue : DonneeInvalideError si la saisie est vide ou invalide.
        """

    @abstractmethod
    def vers_dict(self) -> dict:
        """Décrit la variable pour le fichier JSON de métadonnées."""


class VariableNumerique(Variable):
    """Variable numérique bornée par [minimum, maximum] (bornes incluses)."""

    def __init__(self, nom: str, minimum: float, maximum: float,
                 entier: bool = False, etiquette: str | None = None) -> None:
        """`entier=True` refuse les nombres à virgule (ex. l'année).

        Échoue : ValueError si minimum > maximum.
        """
        super().__init__(nom, etiquette)
        if minimum > maximum:
            raise ValueError(f"Pour {nom}, le minimum ({minimum}) dépasse le maximum ({maximum}).")
        self._minimum = float(minimum)
        self._maximum = float(maximum)
        self._entier = entier

    @property
    def entier(self) -> bool:
        """Vrai si seuls les nombres entiers sont acceptés."""
        return self._entier

    def valider(self, saisie: str) -> float | int:
        """Renvoie la saisie convertie en nombre (int si la variable est entière).

        Accepte la virgule comme séparateur décimal (« 2,5 » donne 2.5).
        Échoue : DonneeInvalideError si vide, non numérique, à virgule pour une
                 variable entière, ou hors intervalle.
        """
        texte = saisie.strip().replace(",", ".")
        if texte == "":
            raise DonneeInvalideError(f"Le champ « {self._etiquette} » est vide.")
        try:
            valeur = float(texte)
        except ValueError:
            raise DonneeInvalideError(
                f"« {saisie} » n'est pas un nombre valide pour « {self._etiquette} ».") from None
        # float() accepte aussi "nan" et "inf" : on les refuse
        if not math.isfinite(valeur):
            raise DonneeInvalideError(
                f"« {saisie} » n'est pas un nombre valide pour « {self._etiquette} ».")
        # is_integer() : Vrai pour 2015.0, Faux pour 2015.5
        if self._entier and not valeur.is_integer():
            raise DonneeInvalideError(f"« {self._etiquette} » doit être un nombre entier.")
        if not self._minimum <= valeur <= self._maximum:
            raise DonneeInvalideError(
                f"« {self._etiquette} » doit être entre {self._minimum:g} et {self._maximum:g}.")
        return int(valeur) if self._entier else valeur

    def vers_dict(self) -> dict:
        """Renvoie le format lu par l'interface :
        {"nom", "etiquette", "type": "entier" ou "decimal", "minimum", "maximum"}.
        """
        if self._entier:
            return {"nom": self._nom, "etiquette": self._etiquette, "type": "entier",
                    "minimum": int(self._minimum), "maximum": int(self._maximum)}
        return {"nom": self._nom, "etiquette": self._etiquette, "type": "decimal",
                "minimum": self._minimum, "maximum": self._maximum}

    def __eq__(self, autre: object) -> bool:
        if not isinstance(autre, VariableNumerique):
            return NotImplemented
        return (self._nom == autre._nom and self._minimum == autre._minimum
                and self._maximum == autre._maximum and self._entier == autre._entier)

    def __repr__(self) -> str:
        return f"VariableNumerique({self._nom!r}, {self._minimum:g}, {self._maximum:g})"


class VariableCategorielle(Variable):
    """Variable catégorielle dont les valeurs permises sont connues."""

    def __init__(self, nom: str, valeurs: list[str], etiquette: str | None = None) -> None:
        """Échoue : ValueError si la liste de valeurs est vide."""
        super().__init__(nom, etiquette)
        if len(valeurs) == 0:
            raise ValueError(f"La liste de valeurs de {nom} est vide.")
        # set() retire les doublons, sorted() trie par ordre alphabétique
        self._valeurs = sorted(set(str(v) for v in valeurs))

    @property
    def valeurs(self) -> list[str]:
        """Valeurs permises, triées par ordre alphabétique."""
        return list(self._valeurs)   # une copie : on ne peut pas modifier la liste interne

    def valider(self, saisie: str) -> str:
        """Renvoie la saisie (sans espaces autour) si elle fait partie des valeurs.

        La comparaison respecte les majuscules (« honda » est refusé).
        Échoue : DonneeInvalideError si vide ou non permise.
        """
        texte = saisie.strip()
        if texte == "":
            raise DonneeInvalideError(f"Veuillez choisir une valeur pour « {self._etiquette} ».")
        if texte not in self._valeurs:
            raise DonneeInvalideError(
                f"« {texte} » n'est pas une valeur permise pour « {self._etiquette} ».")
        return texte

    def vers_dict(self) -> dict:
        """Renvoie le format lu par l'interface :
        {"nom", "etiquette", "type": "categorie", "choix": [...]}.
        """
        return {"nom": self._nom, "etiquette": self._etiquette, "type": "categorie",
                "choix": self.valeurs}

    def __eq__(self, autre: object) -> bool:
        if not isinstance(autre, VariableCategorielle):
            return NotImplemented
        return self._nom == autre._nom and self._valeurs == autre._valeurs

    def __repr__(self) -> str:
        return f"VariableCategorielle({self._nom!r}, {len(self._valeurs)} valeurs)"


def creer_variables(df: pd.DataFrame) -> list[Variable]:
    """Construit une Variable par caractéristique à partir des données nettoyées.

    Renvoie : une VariableNumerique (min/max observés) pour chaque colonne de
              COLONNES_NUMERIQUES, puis une VariableCategorielle (valeurs uniques)
              pour chaque colonne de COLONNES_CATEGORIELLES, dans cet ordre.
              Les variables décrivent ce que l'utilisateur SAISIT : la colonne
              miles a donc des bornes en kilomètres (arrondies à l'entier qui
              englobe tout l'intervalle).
    """
    variables: list[Variable] = []
    for colonne in COLONNES_NUMERIQUES:
        # intervalle permis = plus petite et plus grande valeur vues dans les données
        minimum, maximum = df[colonne].min(), df[colonne].max()
        if colonne == "miles":
            # floor / ceil : on arrondit vers l'extérieur pour ne refuser aucune valeur vue
            minimum = math.floor(miles_vers_kilometres(minimum))
            maximum = math.ceil(miles_vers_kilometres(maximum))
        variables.append(VariableNumerique(colonne, minimum, maximum,
                                           entier=colonne in COLONNES_ENTIERES,
                                           etiquette=ETIQUETTES.get(colonne)))
    for colonne in COLONNES_CATEGORIELLES:
        # valeurs permises = valeurs différentes présentes dans la colonne
        variables.append(VariableCategorielle(colonne, df[colonne].unique().tolist(),
                                              etiquette=ETIQUETTES.get(colonne)))
    return variables


def variable_depuis_dict(description: dict) -> Variable:
    """Reconstruit une Variable à partir de son vers_dict() (lu dans le JSON).

    Échoue : ValueError si le type est inconnu.
    """
    genre = description["type"]
    if genre in ("entier", "decimal"):
        return VariableNumerique(description["nom"], description["minimum"],
                                 description["maximum"], entier=genre == "entier",
                                 etiquette=description.get("etiquette"))
    if genre == "categorie":
        return VariableCategorielle(description["nom"], description["choix"],
                                    etiquette=description.get("etiquette"))
    raise ValueError(f"Type de variable inconnu : {genre}")


def construire_hierarchie(df: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    """Construit la hiérarchie marque → modèle → versions pour les listes en cascade.

    Reçoit : un DataFrame nettoyé avec les colonnes make, model et trim.
    Renvoie : {marque: {modèle: [versions triées, sans doublon]}}, en ne gardant
              que les combinaisons présentes dans les données. Un DataFrame vide
              donne {}.
    """
    # un seul exemplaire de chaque trio (marque, modèle, version), en texte, trié
    trios = (df[["make", "model", "trim"]].astype(str)
             .drop_duplicates()
             .sort_values(["make", "model", "trim"]))
    hierarchie: dict[str, dict[str, list[str]]] = {}
    for marque, modele, version in zip(trios["make"], trios["model"], trios["trim"]):
        # setdefault : renvoie la valeur de la clé, en la créant d'abord si elle n'existe pas
        modeles_de_la_marque = hierarchie.setdefault(marque, {})
        modeles_de_la_marque.setdefault(modele, []).append(version)
    return hierarchie


def verifier_combinaison(hierarchie: dict[str, dict[str, list[str]]],
                         marque: str, modele: str, version: str) -> None:
    """Vérifie que le trio (marque, modèle, version) existe dans la hiérarchie.

    Reçoit : la hiérarchie de construire_hierarchie et les trois saisies.
    Renvoie : None si la combinaison existe.
    Échoue : DonneeInvalideError (message qui nomme la partie fautive) si la
             marque est inconnue, si le modèle n'existe pas pour cette marque ou
             si la version n'existe pas pour ce modèle.
    """
    if marque not in hierarchie:
        raise DonneeInvalideError(f"La marque « {marque} » est inconnue.")
    if modele not in hierarchie[marque]:
        raise DonneeInvalideError(f"Le modèle « {modele} » n'existe pas pour {marque}.")
    if version not in hierarchie[marque][modele]:
        raise DonneeInvalideError(
            f"La version « {version} » n'existe pas pour {marque} {modele}.")


class JeuDeDonnees:
    """Jeu de données chargé, nettoyé et séparé en entraînement / test."""

    def __init__(self, df: pd.DataFrame) -> None:
        """Reçoit un DataFrame brut, le nettoie et le garde en attribut protégé."""
        self._df = nettoyer(df)

    def __len__(self) -> int:
        """Nombre de lignes après nettoyage."""
        return len(self._df)

    def separer(self, taille_test: float = 0.2, graine: int = 42
                ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Sépare en (X_train, X_test, y_train, y_test) avec train_test_split.

        X contient COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES ; y contient CIBLE.
        Échoue : ValueError si taille_test n'est pas strictement entre 0 et 1.
        """
        if not 0 < taille_test < 1:
            raise ValueError(f"taille_test doit être entre 0 et 1 (exclus), reçu {taille_test}.")
        X = self._df[COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES]   # entrées, SANS le prix
        y = self._df[CIBLE]                                          # réponse : le prix
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=taille_test, random_state=graine)
        return X_train, X_test, y_train, y_test
