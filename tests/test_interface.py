from types import SimpleNamespace

from src.interface import InterfaceUtilisateur, _options_compatibles


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
