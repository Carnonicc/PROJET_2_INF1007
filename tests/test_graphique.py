"""Tests de la logique du graphique de comparaison (sans ouvrir de fenêtre)."""

import os

import numpy as np
import pandas as pd
import pytest

from application import (MESSAGE_GRAPHIQUE_IMPOSSIBLE, MESSAGE_GRAPHIQUE_SAISIE,
                         MESSAGE_GRAPHIQUE_SANS_DONNEES, ajouter_graphique)
from donnees import (DonneesGraphique, ReferencePrix, centile_prix, distribution_prix,
                     prix_comparables)
from exceptions import (DonneeInvalideError, EstimationImpossibleError,
                        GraphiqueIndisponibleError)


@pytest.fixture
def annonces():
    """40 Honda Civic (10 000 à 49 000 $), 5 Honda Accord, 3 Toyota Corolla."""
    civic = pd.DataFrame({"make": "Honda", "model": "Civic",
                          "price": np.arange(10_000, 50_000, 1_000, dtype=float)})
    accord = pd.DataFrame({"make": "Honda", "model": "Accord",
                           "price": [30_000.0] * 5})
    corolla = pd.DataFrame({"make": "Toyota", "model": "Corolla",
                            "price": [20_000.0] * 3})
    return pd.concat([civic, accord, corolla], ignore_index=True)


# ---------- centile_prix ----------

def test_centile_cas_usuel():
    prix = np.array([10_000, 20_000, 30_000, 40_000])
    # 2 prix sur 4 sont plus bas que 25 000 $
    assert centile_prix(prix, 25_000) == pytest.approx(50.0)


def test_centile_aux_extremites():
    prix = np.array([10_000.0, 20_000.0, 30_000.0])
    assert centile_prix(prix, 5_000) == pytest.approx(0.0)
    assert centile_prix(prix, 99_000) == pytest.approx(100.0)


def test_centile_un_prix_egal_ne_compte_pas():
    """« Plus élevée que » : un prix identique à l'estimation n'est pas dépassé."""
    prix = np.array([20_000.0, 20_000.0, 10_000.0])
    assert centile_prix(prix, 20_000) == pytest.approx(100 / 3)


@pytest.mark.parametrize("prix, valeur", [
    (np.array([]), 10_000.0),
    (np.array([10_000.0, np.nan]), 10_000.0),
    (np.array([10_000.0]), np.inf),
])
def test_centile_entrees_invalides(prix, valeur):
    with pytest.raises(ValueError):
        centile_prix(prix, valeur)


# ---------- distribution_prix ----------

def test_distribution_compte_toutes_les_annonces():
    prix = np.array([10_000, 12_000, 19_000, 21_000, 29_000, 30_000], dtype=float)
    comptes, bornes = distribution_prix(prix, nb_classes=2)
    assert len(bornes) == len(comptes) + 1
    assert comptes.sum() == len(prix)
    assert bornes[0] == pytest.approx(10_000)
    assert bornes[-1] == pytest.approx(30_000)
    assert list(comptes) == [3, 3]          # classes [10 000, 20 000[ et [20 000, 30 000]


def test_distribution_prix_tous_identiques():
    comptes, bornes = distribution_prix(np.array([15_000.0] * 4), nb_classes=3)
    assert comptes.sum() == 4
    assert bornes[0] < 15_000 < bornes[-1]


@pytest.mark.parametrize("prix, nb_classes", [
    (np.array([]), 10),
    (np.array([1.0, np.nan]), 10),
    (np.array([1.0, 2.0]), 0),
])
def test_distribution_entrees_invalides(prix, nb_classes):
    with pytest.raises(ValueError):
        distribution_prix(prix, nb_classes)


# ---------- prix_comparables ----------

def test_comparables_meme_modele(annonces):
    prix, groupe = prix_comparables(annonces, "Honda", "Civic", minimum=30)
    assert groupe == "Honda Civic"
    assert len(prix) == 40
    assert prix.min() == pytest.approx(10_000)


def test_comparables_repli_sur_la_marque(annonces):
    """Seulement 5 Accord : on compare à toutes les Honda (45 annonces)."""
    prix, groupe = prix_comparables(annonces, "Honda", "Accord", minimum=30)
    assert groupe == "Honda (tous modèles)"
    assert len(prix) == 45


def test_comparables_repli_sur_toutes_les_marques(annonces):
    prix, groupe = prix_comparables(annonces, "Toyota", "Corolla", minimum=30)
    assert groupe == "toutes les marques"
    assert len(prix) == len(annonces)


def test_comparables_aucune_annonce():
    vide = pd.DataFrame({"make": [], "model": [], "price": []})
    with pytest.raises(ValueError):
        prix_comparables(vide, "Honda", "Civic")


# ---------- ReferencePrix ----------

def test_reference_preparer(annonces):
    reference = ReferencePrix(annonces)
    donnees = reference.preparer(20_500, "Honda", "Civic", nb_classes=4)
    assert isinstance(donnees, DonneesGraphique)
    assert donnees.groupe == "Honda Civic"
    assert donnees.nombre_annonces == 40
    assert donnees.comptes.sum() == 40
    # 11 Civic sur 40 (10 000 à 20 000 $) sont moins chères que 20 500 $
    assert donnees.centile == pytest.approx(27.5)
    assert donnees.prix_estime == pytest.approx(20_500)


def test_reference_prix_estime_invalide(annonces):
    with pytest.raises(GraphiqueIndisponibleError):
        ReferencePrix(annonces).preparer(float("nan"), "Honda", "Civic")


def test_reference_colonne_manquante():
    with pytest.raises(DonneeInvalideError):
        ReferencePrix(pd.DataFrame({"make": ["Honda"], "price": [1.0]}))


def test_reference_csv_inexistant(tmp_path):
    with pytest.raises(FileNotFoundError):
        ReferencePrix.depuis_csv(os.path.join(tmp_path, "absent.csv"))


# ---------- ajouter_graphique (connexion avec l'interface) ----------

class FausseInterface:
    """Garde ce qu'on demande d'afficher dans la zone du graphique."""

    def __init__(self):
        self.donnees = None
        self.message = None

    def afficher_graphique(self, donnees):
        self.donnees = donnees

    def afficher_message_graphique(self, texte):
        self.message = texte


class FauxEstimateur:
    def __init__(self, prix=25_000.0):
        self.prix = prix

    def estimer(self, saisies):
        return self.prix, {"make": saisies["make"], "model": saisies["model"]}


def test_graphique_mis_a_jour_apres_prediction(annonces):
    appels = []
    on_prediction = ajouter_graphique(lambda interface, saisies: appels.append(saisies),
                                      FauxEstimateur(25_000), ReferencePrix(annonces))
    interface = FausseInterface()
    on_prediction(interface, {"make": "Honda", "model": "Civic"})
    assert len(appels) == 1                      # le rappel d'origine est bien appelé
    assert interface.donnees.groupe == "Honda Civic"
    assert interface.donnees.centile == pytest.approx(37.5)   # 15 Civic sur 40


@pytest.mark.parametrize("erreur, message", [
    (DonneeInvalideError("Année invalide"), MESSAGE_GRAPHIQUE_SAISIE),
    (EstimationImpossibleError("prix négatif"), MESSAGE_GRAPHIQUE_IMPOSSIBLE),
])
def test_graphique_message_si_erreur_et_erreur_relancee(annonces, erreur, message):
    def on_prediction_qui_echoue(interface, saisies):
        raise erreur

    on_prediction = ajouter_graphique(on_prediction_qui_echoue, FauxEstimateur(),
                                      ReferencePrix(annonces))
    interface = FausseInterface()
    with pytest.raises(type(erreur)):            # l'interface affiche toujours l'erreur
        on_prediction(interface, {"make": "Honda", "model": "Civic"})
    assert interface.message == message
    assert interface.donnees is None


def test_graphique_sans_reference():
    on_prediction = ajouter_graphique(lambda interface, saisies: None, FauxEstimateur(), None)
    interface = FausseInterface()
    on_prediction(interface, {"make": "Honda", "model": "Civic"})
    assert interface.message == MESSAGE_GRAPHIQUE_SANS_DONNEES
