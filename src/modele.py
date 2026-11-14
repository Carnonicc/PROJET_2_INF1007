"""Entraînement, évaluation, sauvegarde et prédiction du prix.

Squelette : les fonctions marquées NotImplementedError sont à compléter.
Les tests de tests/test_modele.py décrivent le comportement attendu.
"""
import os
from abc import ABC, abstractmethod
from typing import Callable
import time
import functools
import numpy as np
import pandas as pd
import json
import joblib
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder


from exceptions import ModeleNonEntraineError  # noqa: F401  (à utiliser)

TOLERANCE = 2000.0


def taux_a_tolerance(y_vrai: np.ndarray, y_predit: np.ndarray,
                     tolerance: float = TOLERANCE) -> float:
    """Proportion (entre 0 et 1) des prédictions à au plus `tolerance` $ du vrai prix.
    
    Calcul vectorisé avec NumPy (aucune boucle Python).
    Échoue : ValueError si les tableaux sont vides ou de longueurs différentes,
             ou si la tolérance est négative.
    """
    if len( y_vrai)==0 or len(y_predit)==0 or len(y_predit)!=len(y_vrai) or tolerance<0:
        raise ValueError('fonction taux a la tolerance ne marche pas, verfie les entres')
    else:
        y_vrai = np.asarray(y_vrai, dtype=float)
        return np.mean(np.abs(y_vrai - y_predit) <= tolerance)


def erreur_absolue_moyenne(y_vrai: np.ndarray, y_predit: np.ndarray) -> float:
    """MAE calculée avec NumPy. Échoue : ValueError comme taux_a_tolerance."""
    if len( y_vrai)==0 or len(y_predit)==0 or len(y_predit)!=len(y_vrai):
        raise ValueError('la fonction erreur_absolue_moyenne ne marche pas, verfie les entres')
    else:
        y_vrai = np.asarray(y_vrai, dtype=float)
        return np.mean(np.abs(y_vrai - y_predit))


def racine_erreur_quadratique(y_vrai: np.ndarray, y_predit: np.ndarray) -> float:
    """RMSE calculée avec NumPy. Échoue : ValueError comme taux_a_tolerance."""
    if len( y_vrai)==0 or len(y_predit)==0 or len(y_predit)!=len(y_vrai):
        raise ValueError('la fonction racine_erreur_quadratique ne marche pas, verfie les entres')
    else:
        y_vrai = np.asarray(y_vrai, dtype=float)
        return np.sqrt(np.mean((y_vrai - y_predit) ** 2))


def chronometrer(fonction: Callable) -> Callable:
    """Décorateur : mesure la durée d'exécution de `fonction`.
 
    La valeur de retour de `fonction` est renvoyée inchangée ; la durée en
    secondes est stockée dans l'attribut `derniere_duree` de la fonction décorée.
    """
 
    @functools.wraps(fonction)
    def enveloppe(*args, **kwargs):
        debut = time.perf_counter()            # 1. on note l'heure de départ
        resultat = fonction(*args, **kwargs)   # 2. on appelle la vraie fonction
        enveloppe.derniere_duree = time.perf_counter() - debut   # 3. durée
        return resultat                        # on renvoie son résultat tel quel
    return enveloppe

class ModelePrix(ABC):
    """Modèle de prédiction de prix (classe parente abstraite)."""

    def __init__(self) -> None:
        self._entraine = False

    @property
    def est_entraine(self) -> bool:
        return self._entraine

    @abstractmethod
    def entrainer(self, X: pd.DataFrame, y: pd.Series) -> None:
        """Entraîne le modèle."""
        pass


    @abstractmethod
    def predire(self, X: pd.DataFrame) -> np.ndarray:
        """Prédit un prix par ligne de X.

        Échoue : ModeleNonEntraineError si le modèle n'est pas entraîné.
        """
        pass

    def evaluer(self, X: pd.DataFrame, y: pd.Series) -> dict[str, float]:
        """Renvoie {"mae": ..., "rmse": ..., "taux_2000": ...} sur (X, y)."""

        if len(y)==0 or len(X)==0 :
            raise ValueError('la fonction evaluer ne marche pas, verfie les entres')
        else:
            predictions = self.predire(X)          # une seule prédiction, réutilisée 3 fois
            mae = erreur_absolue_moyenne(y, predictions)
            rmse = racine_erreur_quadratique(y, predictions)
            taux = taux_a_tolerance(y, predictions)
            return {"mae": mae, "rmse": rmse, "taux_2000": taux}
    


class ModeleReference(ModelePrix):
    """Modèle trivial : prédit toujours le prix moyen de l'entraînement."""

    def entrainer(self, X: pd.DataFrame, y: pd.Series) -> None:
        self._moyenne = float(np.mean(y))   # moyenne de tous les prix d'entraînement
        self._entraine = True 
    def predire(self, X: pd.DataFrame) -> np.ndarray:
        if not self._entraine:
            raise ModeleNonEntraineError("Le modèle de référence n'est pas entraîné.")
        return np.full(len(X), self._moyenne)


class ModeleLineaire(ModelePrix):
    """Régression linéaire (scikit-learn) avec encodage one-hot des catégories."""

    def __init__(self, colonnes_numeriques: list[str],
                 colonnes_categorielles: list[str]) -> None:
        super().__init__()
        
        if not colonnes_categorielles or not colonnes_numeriques:
            raise ValueError("les donnees d'entre ne sont pas bon")

        self._preparation=ColumnTransformer([("cat", OneHotEncoder(handle_unknown="ignore"), colonnes_categorielles),
                                ("num", "passthrough", colonnes_numeriques)])
            



    def entrainer(self, X: pd.DataFrame, y: pd.Series) -> None:
        if len(X)==0 or len( y)==0:
            raise ValueError('la fonction entrainer ne marche pas, verfie les entres')
        else:
            self._Pipeline= Pipeline([("prep", self._preparation),("reg",  LinearRegression())])
            self._Pipeline.fit(X, y)
            self._entraine=True
    

    def predire(self, X: pd.DataFrame) -> np.ndarray:
        if not self._entraine:
            raise ModeleNonEntraineError
        else:
            self.pred = self._Pipeline.predict(X)
            return self.pred

    def sauvegarder(self, chemin: str) -> None:
        """Sauvegarde le modèle avec joblib.

        Échoue : ModeleNonEntraineError si le modèle n'est pas entraîné.
        """
        if not self._entraine:
            raise ModeleNonEntraineError("Impossible de sauvegarder un modèle non entraîné.")
        joblib.dump(self, chemin)

    @staticmethod
    def charger(chemin: str) -> "ModeleLineaire":
        """Recharge un modèle sauvegardé. Échoue : FileNotFoundError."""
        if not os.path.exists(chemin):
            raise FileNotFoundError(chemin)
        return joblib.load(chemin)


def sauvegarder_metadonnees(chemin: str, variables: list, metriques: dict[str, float],
                            hierarchie: dict[str, dict[str, list[str]]]) -> None:
    """Écrit le JSON de métadonnées.

    Format : {"variables": {nom: variable.vers_dict(), ...},
              "metriques": {...},
              "hierarchie": {marque: {modèle: [versions]}}}
    La hiérarchie (voir donnees.construire_hierarchie) sert aux listes en
    cascade marque → modèle → version de l'interface.
    """
    metadonnees = {
        "variables": {variable.nom: variable.vers_dict() for variable in variables},
        "metriques": metriques,
        "hierarchie": hierarchie,
    }
    with open(chemin, "w", encoding="utf-8") as f:
        # indent=2 : fichier lisible ; ensure_ascii=False : garde les accents tels quels
        json.dump(metadonnees, f, indent=2, ensure_ascii=False)


def charger_metadonnees(chemin: str) -> dict:
    """Relit le JSON de métadonnées. Échoue : FileNotFoundError."""
    if not os.path.exists(chemin):
        raise FileNotFoundError(f"Fichier de métadonnées introuvable : {chemin}")
    with open(chemin, encoding="utf-8") as f:
        metadonnees = json.load(f)
    return metadonnees

