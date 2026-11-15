"""Tests de la logique de l'interface (sans ouvrir de fenêtre Tkinter)."""

from types import SimpleNamespace

import pytest

from interface import InterfaceUtilisateur, _formater_borne, options_cascade

HIERARCHIE = {
    "Honda": {"Civic": ["LX", "EX"], "Accord": ["Sport"]},
    "Toyota": {"Corolla": ["LE"]},
}


class FauxChamp:
    """Remplace une liste déroulante ttk.Combobox."""

    def __init__(self, valeur=""):
        self.valeur = valeur
        self.choix = []

    def get(self):
        return self.valeur

    def set(self, valeur):
        self.valeur = valeur

    def configure(self, *, values):
        self.choix = list(values)


def test_formater_borne():
    assert _formater_borne(1609343) == "1 609 343"     # et non « 1.60934e+06 »
    assert _formater_borne(2022.0) == "2 022"
    assert _formater_borne(0.6) == "0.6"


def test_options_cascade_modeles_et_versions():
    assert options_cascade(HIERARCHIE, "model", {"make": "Honda"}) == ["Accord", "Civic"]
    assert options_cascade(HIERARCHIE, "trim", {"make": "Honda", "model": "Civic"}) == ["EX", "LX"]


def test_options_cascade_vide_si_rien_choisi_ou_combinaison_absente():
    assert options_cascade(HIERARCHIE, "model", {}) == []
    assert options_cascade(HIERARCHIE, "trim", {"make": "Honda", "model": "Corolla"}) == []


def test_options_cascade_ignore_la_casse_pour_trier():
    hierarchie = {"BMW": {"i3": ["Base"], "X5": ["xDrive"], "M3": ["Base"]}}
    assert options_cascade(hierarchie, "model", {"make": "BMW"}) == ["i3", "M3", "X5"]


def test_options_cascade_champ_hors_cascade():
    with pytest.raises(ValueError):
        options_cascade(HIERARCHIE, "body_type", {})


def test_choisir_une_marque_vide_modele_et_version():
    champs = {"make": FauxChamp("Toyota"), "model": FauxChamp("Civic"),
              "trim": FauxChamp("LX")}
    interface = SimpleNamespace(hierarchie=HIERARCHIE, champs_categoriels=champs)

    InterfaceUtilisateur._actualiser_choix(interface, "make")

    assert champs["model"].get() == ""
    assert champs["trim"].get() == ""
    assert champs["model"].choix == ["Corolla"]
    assert champs["trim"].choix == []          # pas de modèle choisi : aucune version


def test_choisir_un_modele_garde_la_marque():
    champs = {"make": FauxChamp("Honda"), "model": FauxChamp("Civic"),
              "trim": FauxChamp("Sport")}
    interface = SimpleNamespace(hierarchie=HIERARCHIE, champs_categoriels=champs)

    InterfaceUtilisateur._actualiser_choix(interface, "model")

    assert champs["make"].get() == "Honda"
    assert champs["model"].get() == "Civic"
    assert champs["trim"].get() == ""
    assert champs["trim"].choix == ["EX", "LX"]
