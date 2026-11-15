"""Tests du module application (estimation, historique, mise en forme)."""

import json
import os
from datetime import datetime

import numpy as np
import pytest

from application import (Estimateur, Historique, creer_rappels, formater_prix,
                         texte_metriques, texte_resultat)
from donnees import COLONNES_CATEGORIELLES, COLONNES_NUMERIQUES, VariableCategorielle, VariableNumerique
from exceptions import DonneeInvalideError, EstimationImpossibleError


class FauxModele:
    """Remplace la régression : renvoie toujours `prix` et garde le X reçu."""

    def __init__(self, prix):
        self.prix = prix
        self.X_recu = None

    def predire(self, X):
        self.X_recu = X
        return np.full(len(X), self.prix)


class FausseInterface:
    """Remplace la fenêtre Tkinter : garde ce qu'on lui demande d'afficher."""

    def __init__(self):
        self.resultat = None
        self.historique = None

    def afficher_resultat(self, texte):
        self.resultat = texte

    def afficher_historique(self, lignes):
        self.historique = lignes


@pytest.fixture
def metadonnees():
    """Métadonnées minimales au format de charger_metadonnees (une variable par colonne)."""
    variables = [
        VariableNumerique("miles", 0, 300000, entier=True, etiquette="Kilométrage"),
        VariableNumerique("year", 2000, 2022, entier=True, etiquette="Année"),
        VariableNumerique("engine_size", 1.0, 6.5, etiquette="Cylindrée"),
        VariableCategorielle("make", ["Honda", "Toyota"], etiquette="Marque"),
        VariableCategorielle("model", ["Civic", "Corolla"]),
        VariableCategorielle("trim", ["LX", "LE"]),
        VariableCategorielle("body_type", ["Sedan"]),
        VariableCategorielle("drivetrain", ["FWD"]),
        VariableCategorielle("transmission", ["Automatic"]),
        VariableCategorielle("fuel_type", ["Unleaded"]),
        VariableCategorielle("engine_block", ["I"]),
    ]
    return {
        "variables": [v.vers_dict() for v in variables],
        "metriques": {"mae": 6468.9, "taux_2000": 0.267, "mae_reference": 11144.9},
        "hierarchie": {"Honda": {"Civic": ["LX"]}, "Toyota": {"Corolla": ["LE"]}},
    }


@pytest.fixture
def saisies():
    """Saisies valides, en texte, comme celles de l'interface."""
    return {"miles": "50000", "year": "2018", "engine_size": "2,0", "make": "Honda",
            "model": "Civic", "trim": "LX", "body_type": "Sedan", "drivetrain": "FWD",
            "transmission": "Automatic", "fuel_type": "Unleaded", "engine_block": "I"}


# ---------- mise en forme ----------

def test_formater_prix():
    assert formater_prix(23450.4) == "23 450 $"
    assert formater_prix(999) == "999 $"


def test_texte_metriques(metadonnees):
    texte = texte_metriques(metadonnees["metriques"])
    assert "6 469 $" in texte
    assert "26,7 %" in texte
    assert "11 145 $" in texte


def test_texte_metriques_absentes():
    assert "non disponible" in texte_metriques({})


def test_texte_resultat():
    assert texte_resultat(23450, {"mae": 6469}).startswith("Prix estimé : 23 450 $")
    assert texte_resultat(23450, {}) == "Prix estimé : 23 450 $"


# ---------- Estimateur ----------

def test_estimer_convertit_et_predit(metadonnees, saisies):
    modele = FauxModele(25000.0)
    prix, caracteristiques = Estimateur(modele, metadonnees).estimer(saisies)
    assert prix == pytest.approx(25000.0)
    assert caracteristiques["year"] == 2018            # entier, plus du texte
    assert caracteristiques["engine_size"] == pytest.approx(2.0)   # « 2,0 » accepté
    # le modèle reçoit une seule ligne avec exactement ses colonnes
    assert list(modele.X_recu.columns) == COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES
    assert len(modele.X_recu) == 1


def test_estimer_convertit_les_km_en_miles_pour_le_modele(metadonnees, saisies):
    modele = FauxModele(25000.0)
    saisies["miles"] = "96561"                          # km tapés par l'utilisateur
    _, caracteristiques = Estimateur(modele, metadonnees).estimer(saisies)
    assert modele.X_recu["miles"].iloc[0] == pytest.approx(60000, abs=1)   # le modèle voit des miles
    assert caracteristiques["miles"] == 96561          # l'historique garde les km


@pytest.mark.parametrize("champ, valeur, message", [
    ("year", "", "Année"),
    ("year", "2015.5", "entier"),
    ("miles", "-5", "Kilométrage"),
    ("make", "Ferrari", "Marque"),
])
def test_estimer_refuse_une_saisie_invalide(metadonnees, saisies, champ, valeur, message):
    saisies[champ] = valeur
    with pytest.raises(DonneeInvalideError, match=message):
        Estimateur(FauxModele(25000.0), metadonnees).estimer(saisies)


def test_estimer_refuse_une_combinaison_inexistante(metadonnees, saisies):
    saisies["model"] = "Corolla"    # chaque valeur existe, mais pas une Honda Corolla
    with pytest.raises(DonneeInvalideError, match="Corolla"):
        Estimateur(FauxModele(25000.0), metadonnees).estimer(saisies)


@pytest.mark.parametrize("prix", [0.0, -12000.0])
def test_estimer_refuse_un_prix_impossible(metadonnees, saisies, prix):
    with pytest.raises(EstimationImpossibleError):
        Estimateur(FauxModele(prix), metadonnees).estimer(saisies)


# ---------- Historique ----------

def test_historique_ajouter_et_lignes():
    historique = Historique()
    ligne = historique.ajouter(23450.123, {"year": 2018}, datetime(2026, 11, 14, 15, 30))
    assert len(historique) == 1
    assert ligne == {"date_heure": "2026-11-14 15:30:00", "prix_estime": 23450.12,
                     "caracteristiques": {"year": 2018}}
    historique.lignes.clear()          # une copie : l'historique n'est pas touché
    assert len(historique) == 1


def test_historique_sauvegarde_et_relit(tmp_path):
    chemin = os.path.join(tmp_path, "historique.json")
    Historique(chemin).ajouter(20000, {"make": "Honda"})
    with open(chemin, encoding="utf-8") as f:
        assert len(json.load(f)) == 1
    relu = Historique(chemin)          # nouveau lancement de l'application
    assert len(relu) == 1
    assert relu.lignes[0]["caracteristiques"] == {"make": "Honda"}


def test_historique_fichier_absent_commence_vide(tmp_path):
    assert len(Historique(os.path.join(tmp_path, "absent.json"))) == 0


# ---------- creer_rappels (lien entre l'interface et le modèle) ----------

def test_rappel_prediction_affiche_et_ajoute(metadonnees, saisies):
    historique = Historique()
    on_prediction, on_actualiser = creer_rappels(
        Estimateur(FauxModele(25000.0), metadonnees), historique, metadonnees["metriques"])
    interface = FausseInterface()
    on_prediction(interface, saisies)
    assert "25 000 $" in interface.resultat
    assert len(historique) == 1
    assert interface.historique == historique.lignes

    autre = FausseInterface()
    on_actualiser(autre)
    assert autre.historique == historique.lignes


def test_rappel_sauvegarde_impossible_affiche_quand_meme_le_prix(tmp_path, metadonnees,
                                                                 saisies):
    # le dossier « absent » n'existe pas : écrire le fichier lève une OSError
    historique = Historique(os.path.join(tmp_path, "absent", "historique.json"))
    on_prediction, _ = creer_rappels(Estimateur(FauxModele(25000.0), metadonnees),
                                     historique, {})
    interface = FausseInterface()
    with pytest.raises(OSError):
        on_prediction(interface, saisies)
    assert "25 000 $" in interface.resultat           # le prix est quand même affiché
    assert len(interface.historique) == 1             # et visible pendant cette session


def test_rappel_prediction_invalide_n_ajoute_rien(metadonnees, saisies):
    historique = Historique()
    on_prediction, _ = creer_rappels(Estimateur(FauxModele(25000.0), metadonnees),
                                     historique, {})
    saisies["year"] = "abc"
    with pytest.raises(DonneeInvalideError):
        on_prediction(FausseInterface(), saisies)
    assert len(historique) == 0
