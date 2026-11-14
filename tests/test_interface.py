from types import SimpleNamespace

import pytest

from src.interface import (
    InterfaceUtilisateur,
    _metadonnees_du_catalogue,
    _options_compatibles,
    adapter_metadonnees_modele,
)
from src.donnees import miles_vers_kilometres


class FauxChamp:
    def __init__(self, valeur=""):
        self.valeur = valeur
        self.choix = []

    def get(self):
        return self.valeur

    def set(self, valeur):
        self.valeur = valeur

    def configure(self, *, values):
        self.choix = list(values)


def test_options_compatibles_filtrent_les_combinaisons_absentes():
    catalogue = [
        {"make": "Honda", "model": "Civic", "trim": "LX"},
        {"make": "Honda", "model": "Accord", "trim": "Sport"},
        {"make": "Toyota", "model": "Corolla", "trim": "LE"},
    ]

    assert _options_compatibles(
        catalogue,
        "model",
        {"make": "Honda"},
    ) == ["Accord", "Civic"]
    assert _options_compatibles(
        catalogue,
        "trim",
        {"make": "Honda", "model": "Corolla"},
    ) == []


def test_changement_de_selection_efface_les_champs_incompatibles():
    catalogue = [
        {"year": "2020", "make": "Honda", "model": "Civic", "trim": "LX"},
        {"year": "2019", "make": "Toyota", "model": "Corolla", "trim": "LE"},
    ]
    champs = {
        "make": FauxChamp("Toyota"),
        "model": FauxChamp("Civic"),
        "trim": FauxChamp("LX"),
    }
    interface = SimpleNamespace(
        catalogue=catalogue,
        champs_categoriels=champs,
        annees_disponibles={"2019", "2020"},
        champs={"year": FauxChamp("2019")},
    )

    InterfaceUtilisateur._actualiser_choix(interface, "make")

    assert champs["model"].get() == ""
    assert champs["trim"].get() == ""
    assert champs["model"].choix == ["Corolla"]


def test_metadonnees_modele_deviennent_metadonnees_interface():
    noms_numeriques = ("miles", "year", "engine_size")
    noms_categoriques = (
        "make", "model", "trim", "body_type", "drivetrain",
        "transmission", "fuel_type", "engine_block",
    )
    variables = {
        nom: {"type": "numerique", "min": 1, "max": 10}
        for nom in noms_numeriques
    }
    variables.update({
        nom: {"type": "categorielle", "valeurs": ["valeur-entrainee"]}
        for nom in noms_categoriques
    })
    catalogue = [{
        nom: "valeur-catalogue"
        for nom in noms_categoriques
    }]
    metadonnees = {
        "version_schema": 2,
        "variables": variables,
        "metriques": {"mae": 1234.5},
    }

    adapte = adapter_metadonnees_modele(metadonnees, catalogue)

    champs = {variable["nom"]: variable for variable in adapte["variables"]}
    assert champs["miles"]["minimum"] == pytest.approx(
        miles_vers_kilometres(1)
    )
    assert champs["miles"]["etiquette"] == "Kilométrage (km)"
    assert champs["engine_size"]["maximum"] == 10
    assert champs["make"]["type"] == "categorie"
    assert champs["make"]["choix"] == ["valeur-catalogue"]
    assert adapte["metriques"] == {"mae": 1234.5}


def test_metadonnees_modele_incompletes_sont_refusees():
    with pytest.raises(ValueError, match="variables du modèle"):
        adapter_metadonnees_modele({"variables": {}}, [])


def test_metadonnees_du_catalogue_convertissent_les_bornes_en_km():
    catalogue = [{
        "miles": "100",
        "year": "2018",
        "make": "Honda",
        "model": "Civic",
        "trim": "LX",
        "body_type": "Sedan",
        "drivetrain": "FWD",
        "transmission": "Automatic",
        "fuel_type": "Unleaded",
        "engine_size": "2.0",
        "engine_block": "I",
    }]

    metadonnees = _metadonnees_du_catalogue(catalogue)
    kilometrage = next(
        variable for variable in metadonnees["variables"]
        if variable["nom"] == "miles"
    )

    assert kilometrage["minimum"] == pytest.approx(
        miles_vers_kilometres(100)
    )
    assert kilometrage["maximum"] == pytest.approx(
        miles_vers_kilometres(100)
    )
