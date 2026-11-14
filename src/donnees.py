"""Lecture, nettoyage et description des données de voitures d'occasion du Québec.

Squelette : les fonctions marquées NotImplementedError sont à compléter.
Les tests de tests/test_donnees.py décrivent le comportement attendu.
"""

import math
import os
from abc import ABC, abstractmethod

import pandas as pd

from exceptions import DonneeInvalideError

CIBLE = "price"
COLONNES_NUMERIQUES = ["miles", "year", "engine_size"]
COLONNES_CATEGORIELLES = ["make", "model", "trim", "body_type", "drivetrain",
                          "transmission", "fuel_type", "engine_block"]
COLONNES = [CIBLE] + COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES


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
    # 2. valeurs impossibles : on garde les prix > 0 et les kilométrages >= 0
    valide = (propre[CIBLE] > 0) & (propre[COLONNES_NUMERIQUES] >= 0)
    propre = propre[valide]
    # 3. index renuméroté 0, 1, 2... (sinon il garde des « trous »)
    return propre.reset_index(drop=True)


class Variable(ABC):
    """Variable d'entrée du modèle (classe parente abstraite)."""

    def __init__(self, nom: str) -> None:
        self._nom = nom

    @property
    def nom(self) -> str:
        """Nom de la colonne correspondante."""
        return self._nom

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

    def __init__(self, nom: str, minimum: float, maximum: float) -> None:
        """Échoue : ValueError si minimum > maximum."""
        super().__init__(nom)
        if minimum > maximum:
            raise ValueError(f"Pour {nom}, le minimum ({minimum}) dépasse le maximum ({maximum}).")
        self._minimum = float(minimum)
        self._maximum = float(maximum)

    def valider(self, saisie: str) -> float:
        """Renvoie la saisie convertie en float.

        Accepte la virgule comme séparateur décimal (« 2,5 » donne 2.5).
        Échoue : DonneeInvalideError si vide, non numérique ou hors intervalle.
        """
        texte = saisie.strip().replace(",", ".")
        if texte == "":
            raise DonneeInvalideError(f"Le champ « {self._nom} » est vide.")
        try:
            valeur = float(texte)
        except ValueError:
            raise DonneeInvalideError(
                f"« {saisie} » n'est pas un nombre valide pour « {self._nom} ».") from None
        # float() accepte aussi "nan" et "inf" : on les refuse
        if not math.isfinite(valeur):
            raise DonneeInvalideError(f"« {saisie} » n'est pas un nombre valide pour « {self._nom} ».")
        if not self._minimum <= valeur <= self._maximum:
            raise DonneeInvalideError(
                f"« {self._nom} » doit être entre {self._minimum:g} et {self._maximum:g}.")
        return valeur

    def vers_dict(self) -> dict:
        """Renvoie {"type": "numerique", "min": ..., "max": ...}."""
        return {"type": "numerique", "min": self._minimum, "max": self._maximum}

    def __eq__(self, autre: object) -> bool:
        if not isinstance(autre, VariableNumerique):
            return NotImplemented
        return (self._nom == autre._nom and self._minimum == autre._minimum
                and self._maximum == autre._maximum)

    def __repr__(self) -> str:
        return f"VariableNumerique({self._nom!r}, {self._minimum:g}, {self._maximum:g})"


class VariableCategorielle(Variable):
    """Variable catégorielle dont les valeurs permises sont connues."""

    def __init__(self, nom: str, valeurs: list[str]) -> None:
        """Échoue : ValueError si la liste de valeurs est vide."""
        super().__init__(nom)
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
            raise DonneeInvalideError(f"Veuillez choisir une valeur pour « {self._nom} ».")
        if texte not in self._valeurs:
            raise DonneeInvalideError(f"« {texte} » n'est pas une valeur permise pour « {self._nom} ».")
        return texte

    def vers_dict(self) -> dict:
        """Renvoie {"type": "categorielle", "valeurs": [...]}."""
        return {"type": "categorielle", "valeurs": self.valeurs}

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
    """
    raise NotImplementedError


def construire_hierarchie(df: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    """Construit la hiérarchie marque → modèle → versions pour les listes en cascade.

    Reçoit : un DataFrame nettoyé avec les colonnes make, model et trim.
    Renvoie : {marque: {modèle: [versions triées, sans doublon]}}, en ne gardant
              que les combinaisons présentes dans les données. Un DataFrame vide
              donne {}.
    """
    raise NotImplementedError


def verifier_combinaison(hierarchie: dict[str, dict[str, list[str]]],
                         marque: str, modele: str, version: str) -> None:
    """Vérifie que le trio (marque, modèle, version) existe dans la hiérarchie.

    Reçoit : la hiérarchie de construire_hierarchie et les trois saisies.
    Renvoie : None si la combinaison existe.
    Échoue : DonneeInvalideError (message qui nomme la partie fautive) si la
             marque est inconnue, si le modèle n'existe pas pour cette marque ou
             si la version n'existe pas pour ce modèle.
    """
    raise NotImplementedError


class JeuDeDonnees:
    """Jeu de données chargé, nettoyé et séparé en entraînement / test."""

    def __init__(self, df: pd.DataFrame) -> None:
        """Reçoit un DataFrame brut, le nettoie et le garde en attribut protégé."""
        raise NotImplementedError

    def __len__(self) -> int:
        """Nombre de lignes après nettoyage."""
        raise NotImplementedError

    def separer(self, taille_test: float = 0.2, graine: int = 42
                ) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
        """Sépare en (X_train, X_test, y_train, y_test) avec train_test_split.

        X contient COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES ; y contient CIBLE.
        Échoue : ValueError si taille_test n'est pas strictement entre 0 et 1.
        """
        raise NotImplementedError
