"""Tests du module modele (métriques NumPy, référence, régression, sauvegarde)."""

import os

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import mean_absolute_error, mean_squared_error

from donnees import VariableCategorielle, VariableNumerique
from exceptions import ModeleNonEntraineError
from modele import (
    ModeleLineaire, ModelePrix, ModeleReference, charger_metadonnees, chronometrer,
    erreur_absolue_moyenne, racine_erreur_quadratique, sauvegarder_metadonnees,
    taux_a_tolerance,
)


@pytest.fixture
def donnees_lineaires():
    """Prix exactement linéaire : 30000 - 0.1*miles + 5000 si Toyota.

    Une régression linéaire doit le retrouver presque parfaitement.
    """
    rng = np.random.default_rng(0)
    n = 200
    miles = rng.uniform(0, 150_000, n)
    make = rng.choice(["Honda", "Toyota"], n)
    X = pd.DataFrame({"miles": miles, "make": make})
    y = pd.Series(30_000 - 0.1 * miles + np.where(make == "Toyota", 5000, 0))
    return X, y


# ---------- métriques vectorisées ----------

def test_taux_a_tolerance_cas_usuel():
    vrai = np.array([10_000, 20_000, 30_000, 40_000])
    predit = np.array([11_000, 23_000, 30_000, 37_500])   # écarts 1000, 3000, 0, 2500
    assert taux_a_tolerance(vrai, predit) == pytest.approx(0.5)


def test_taux_a_tolerance_borne_incluse():
    """Un écart d'exactement 2000 $ compte comme « à 2000 $ près »."""
    vrai = np.array([10_000.0, 10_000.0])
    predit = np.array([12_000.0, 7_999.99])
    assert taux_a_tolerance(vrai, predit) == pytest.approx(0.5)


def test_taux_a_tolerance_personnalisee():
    vrai = np.array([100.0, 200.0, 300.0])
    predit = np.array([150.0, 200.0, 400.0])
    assert taux_a_tolerance(vrai, predit, tolerance=50) == pytest.approx(2 / 3)


@pytest.mark.parametrize("vrai, predit", [
    (np.array([]), np.array([])),
    (np.array([1.0, 2.0]), np.array([1.0])),
])
def test_metriques_entrees_invalides(vrai, predit):
    for metrique in (taux_a_tolerance, erreur_absolue_moyenne, racine_erreur_quadratique):
        with pytest.raises(ValueError):
            metrique(vrai, predit)


def test_taux_a_tolerance_negative():
    with pytest.raises(ValueError):
        taux_a_tolerance(np.array([1.0]), np.array([1.0]), tolerance=-1)


def test_mae_et_rmse_identiques_a_scikit_learn():
    rng = np.random.default_rng(42)
    vrai = rng.uniform(5_000, 80_000, 500)
    predit = vrai + rng.normal(0, 3_000, 500)
    assert erreur_absolue_moyenne(vrai, predit) == pytest.approx(
        mean_absolute_error(vrai, predit))
    assert racine_erreur_quadratique(vrai, predit) == pytest.approx(
        np.sqrt(mean_squared_error(vrai, predit)))


# ---------- décorateur ----------

def test_chronometrer_garde_le_resultat_et_mesure():
    @chronometrer
    def addition(a, b):
        return a + b

    assert addition(2, 3) == 5
    assert addition.derniere_duree >= 0


# ---------- ModeleReference ----------

def test_modele_reference_predit_la_moyenne():
    X = pd.DataFrame({"miles": [1, 2, 3, 4]})
    y = pd.Series([10_000, 20_000, 30_000, 40_000])
    reference = ModeleReference()
    reference.entrainer(X, y)
    predictions = reference.predire(pd.DataFrame({"miles": [99, 100]}))
    assert predictions == pytest.approx([25_000, 25_000])


def test_predire_avant_entrainement():
    X = pd.DataFrame({"miles": [1.0], "make": ["Honda"]})
    for modele in (ModeleReference(), ModeleLineaire(["miles"], ["make"])):
        assert not modele.est_entraine
        with pytest.raises(ModeleNonEntraineError):
            modele.predire(X)


def test_modele_prix_est_abstrait():
    with pytest.raises(TypeError):
        ModelePrix()


# ---------- ModeleLineaire ----------

def test_modele_lineaire_retrouve_une_relation_lineaire(donnees_lineaires):
    X, y = donnees_lineaires
    modele = ModeleLineaire(["miles"], ["make"])
    modele.entrainer(X, y)
    assert modele.est_entraine
    nouveau = pd.DataFrame({"miles": [0.0, 100_000.0], "make": ["Honda", "Toyota"]})
    assert modele.predire(nouveau) == pytest.approx([30_000, 25_000], abs=1)


def test_modele_lineaire_bat_la_reference(donnees_lineaires):
    X, y = donnees_lineaires
    lineaire, reference = ModeleLineaire(["miles"], ["make"]), ModeleReference()
    lineaire.entrainer(X, y)
    reference.entrainer(X, y)
    assert lineaire.evaluer(X, y)["mae"] < reference.evaluer(X, y)["mae"]


def test_modele_lineaire_categorie_inconnue_ne_plante_pas(donnees_lineaires):
    """Une marque jamais vue à l'entraînement doit quand même donner un prix."""
    X, y = donnees_lineaires
    modele = ModeleLineaire(["miles"], ["make"])
    modele.entrainer(X, y)
    prediction = modele.predire(pd.DataFrame({"miles": [50_000.0], "make": ["Lada"]}))
    assert prediction.shape == (1,)
    assert np.isfinite(prediction[0])


def test_evaluer_renvoie_les_trois_metriques(donnees_lineaires):
    X, y = donnees_lineaires
    modele = ModeleLineaire(["miles"], ["make"])
    modele.entrainer(X, y)
    resultats = modele.evaluer(X, y)
    assert set(resultats) == {"mae", "rmse", "taux_2000"}
    assert resultats["taux_2000"] == pytest.approx(1.0)   # relation parfaite
    assert 0 <= resultats["mae"] <= resultats["rmse"] + 1e-9


# ---------- sauvegarde ----------

def test_sauvegarder_puis_charger_donne_les_memes_predictions(tmp_path, donnees_lineaires):
    X, y = donnees_lineaires
    modele = ModeleLineaire(["miles"], ["make"])
    modele.entrainer(X, y)
    chemin = os.path.join(tmp_path, "modele.joblib")
    modele.sauvegarder(chemin)
    assert os.path.exists(chemin)
    recharge = ModeleLineaire.charger(chemin)
    assert recharge.predire(X) == pytest.approx(modele.predire(X))


def test_sauvegarder_modele_non_entraine(tmp_path):
    with pytest.raises(ModeleNonEntraineError):
        ModeleLineaire(["miles"], ["make"]).sauvegarder(os.path.join(tmp_path, "m.joblib"))


def test_charger_modele_inexistant(tmp_path):
    with pytest.raises(FileNotFoundError):
        ModeleLineaire.charger(os.path.join(tmp_path, "absent.joblib"))


def test_metadonnees_aller_retour(tmp_path):
    chemin = os.path.join(tmp_path, "metadonnees.json")
    variables = [VariableNumerique("year", 2000, 2022),
                 VariableCategorielle("make", ["Toyota", "Acura"])]
    hierarchie = {"Acura": {"MDX": ["Base", "Tech"]}, "Toyota": {"Corolla": ["LE"]}}
    sauvegarder_metadonnees(chemin, variables, {"mae": 3456.7, "taux_2000": 0.41}, hierarchie)
    meta = charger_metadonnees(chemin)
    assert meta["hierarchie"] == hierarchie
    assert meta["variables"]["year"] == {"type": "numerique", "min": 2000, "max": 2022}
    assert meta["variables"]["make"] == {"type": "categorielle", "valeurs": ["Acura", "Toyota"]}
    assert meta["metriques"]["mae"] == pytest.approx(3456.7)


def test_charger_metadonnees_inexistant(tmp_path):
    with pytest.raises(FileNotFoundError):
        charger_metadonnees(os.path.join(tmp_path, "absent.json"))
