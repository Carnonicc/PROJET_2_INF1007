import numpy as np
import pytest

from donnees import (
    COLONNES_CATEGORIELLES,
    COLONNES_NUMERIQUES,
    kilometres_vers_miles,
    miles_vers_kilometres,
)
from historique import charger_historique
from main import _creer_callback_actualisation, _creer_callback_prediction


def _metadonnees():
    variables = {
        "miles": {"type": "numerique", "min": 0, "max": 200000},
        "year": {"type": "numerique", "min": 1990, "max": 2024},
        "engine_size": {"type": "numerique", "min": 0.6, "max": 8.3},
    }
    variables.update({
        nom: {"type": "categorielle", "valeurs": ["choix"]}
        for nom in COLONNES_CATEGORIELLES
    })
    return {"variables": variables}


def _saisies():
    return {
        "miles": "100000",
        "year": "2018",
        "engine_size": "2,0",
        "make": "Honda",
        "model": "Civic",
        "trim": "LX",
        "body_type": "Sedan",
        "drivetrain": "FWD",
        "transmission": "Automatic",
        "fuel_type": "Unleaded",
        "engine_block": "I",
    }


class FauxModele:
    def __init__(self, prix):
        self.prix = prix
        self.entrees = None

    def predire(self, entrees):
        self.entrees = entrees
        return np.array([self.prix])


class FauxStatut:
    def set(self, valeur):
        self.valeur = valeur


class FauxInterface:
    def __init__(self):
        self.statut = FauxStatut()
        self.resultat = None
        self.historique = None

    def afficher_resultat(self, texte):
        self.resultat = texte

    def afficher_historique(self, lignes):
        self.historique = lignes


def test_callback_construit_les_entrees_et_sauvegarde_le_prix(tmp_path):
    modele = FauxModele(24500)
    interface = FauxInterface()
    historique = []
    chemin = tmp_path / "historique.json"
    callback = _creer_callback_prediction(
        modele, _metadonnees(), historique, chemin
    )

    callback(interface, _saisies())
    callback(interface, _saisies())

    assert list(modele.entrees.columns) == (
        COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES
    )
    assert modele.entrees.iloc[0]["miles"] == pytest.approx(
        kilometres_vers_miles(100000)
    )
    assert modele.entrees.iloc[0]["year"] == 2018
    assert modele.entrees.iloc[0]["engine_size"] == 2.0
    assert interface.resultat == "Prix estimé : 24 500 $"
    assert interface.statut.valeur == "Prédiction terminée."
    assert len(historique) == 2
    assert historique[0]["caracteristiques"]["miles"] == 100000
    assert historique[0]["unites"] == {"miles": "km"}
    assert interface.historique == historique
    assert charger_historique(chemin) == historique


def test_callback_refuse_une_entree_numerique_invalide(tmp_path):
    modele = FauxModele(24500)
    callback = _creer_callback_prediction(
        modele, _metadonnees(), [], tmp_path / "historique.json"
    )
    saisies = _saisies()
    saisies["miles"] = "999999"

    with pytest.raises(ValueError, match="doit être entre"):
        callback(FauxInterface(), saisies)

    assert modele.entrees is None


def test_callback_ne_presente_pas_un_prix_non_positif(tmp_path):
    modele = FauxModele(-100)
    interface = FauxInterface()
    callback = _creer_callback_prediction(
        modele, _metadonnees(), [], tmp_path / "historique.json"
    )

    with pytest.raises(ValueError, match="estimation nulle ou négative"):
        callback(interface, _saisies())

    assert interface.resultat is None


def test_actualisation_affiche_l_historique_charge():
    interface = FauxInterface()
    lignes = [{"date_heure": "2026-01-01", "prix_estime": 12000,
               "caracteristiques": {"make": "Honda"}}]

    _creer_callback_actualisation(lignes)(interface)

    assert interface.historique == lignes
