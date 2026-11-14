"""Tests du module donnees (lecture, nettoyage, variables, séparation)."""

import os

import pandas as pd
import pytest

from donnees import (
    CIBLE, COLONNES, COLONNES_CATEGORIELLES, COLONNES_NUMERIQUES,
    JeuDeDonnees, Variable, VariableCategorielle, VariableNumerique,
    charger_csv, construire_hierarchie, creer_variables, nettoyer,
    verifier_combinaison,
)
from exceptions import DonneeInvalideError

CHEMIN_CSV_QC = os.path.join(os.path.dirname(__file__), "..", "donnees",
                             "ca-dealers-used-qc.csv")


def ligne(price=20000, miles=50000, year=2018, engine_size=2.0, make="Honda",
          model="Civic", trim="LX", body_type="Sedan", drivetrain="FWD",
          transmission="Automatic", fuel_type="Unleaded", engine_block="I"):
    """Construit une ligne valide ; on modifie seulement ce qui intéresse le test."""
    return {"price": price, "miles": miles, "year": year, "engine_size": engine_size,
            "make": make, "model": model, "trim": trim, "body_type": body_type,
            "drivetrain": drivetrain, "transmission": transmission,
            "fuel_type": fuel_type, "engine_block": engine_block}


@pytest.fixture
def df_petit() -> pd.DataFrame:
    """Petit jeu de 20 voitures valides."""
    lignes = [ligne(price=10000 + 1000 * i, miles=5000 * i, year=2010 + i % 10,
                    make="Honda" if i % 2 else "Toyota")
              for i in range(20)]
    return pd.DataFrame(lignes)


# ---------- charger_csv (fichiers) ----------

def test_charger_csv_fichier_valide(tmp_path, df_petit):
    chemin = os.path.join(tmp_path, "voitures.csv")
    df_petit.to_csv(chemin, index=False)
    df = charger_csv(chemin)
    assert len(df) == 20
    assert set(COLONNES).issubset(df.columns)


def test_charger_csv_fichier_inexistant(tmp_path):
    with pytest.raises(FileNotFoundError):
        charger_csv(os.path.join(tmp_path, "absent.csv"))


def test_charger_csv_colonne_manquante(tmp_path, df_petit):
    chemin = os.path.join(tmp_path, "incomplet.csv")
    df_petit.drop(columns=["year"]).to_csv(chemin, index=False)
    with pytest.raises(DonneeInvalideError):
        charger_csv(chemin)


@pytest.mark.skipif(not os.path.exists(CHEMIN_CSV_QC), reason="CSV du Québec absent")
def test_vrai_jeu_respecte_criteres_enonce():
    """Critères de la section 2 : 500 à 50 000 lignes, >= 5 caractéristiques."""
    df = charger_csv(CHEMIN_CSV_QC)
    assert 500 <= len(df) <= 50_000
    assert len(COLONNES_NUMERIQUES) + len(COLONNES_CATEGORIELLES) >= 5
    assert pd.api.types.is_numeric_dtype(df[CIBLE])


# ---------- nettoyer ----------

def test_nettoyer_retire_valeurs_manquantes():
    df = pd.DataFrame([ligne(), ligne(make=None), ligne(miles=float("nan"))])
    assert len(nettoyer(df)) == 1


def test_nettoyer_retire_valeurs_aberrantes():
    df = pd.DataFrame([ligne(), ligne(price=0), ligne(price=-500), ligne(miles=-1)])
    resultat = nettoyer(df)
    assert len(resultat) == 1
    assert resultat[CIBLE].iloc[0] == 20000


def test_nettoyer_garde_les_cas_limites_valides():
    """Une voiture neuve (0 mile) et un prix de 1 $ sont valides."""
    df = pd.DataFrame([ligne(miles=0), ligne(price=1)])
    assert len(nettoyer(df)) == 2


def test_nettoyer_ne_modifie_pas_l_original():
    df = pd.DataFrame([ligne(), ligne(price=-1)])
    nettoyer(df)
    assert len(df) == 2


# ---------- VariableNumerique ----------

def test_variable_numerique_saisie_valide():
    annee = VariableNumerique("year", 2000, 2022)
    assert annee.valider("2015") == pytest.approx(2015.0)
    assert annee.valider(" 2018 ") == pytest.approx(2018.0)   # espaces tolérés


def test_variable_numerique_bornes_incluses():
    moteur = VariableNumerique("engine_size", 1.0, 6.5)
    assert moteur.valider("1.0") == pytest.approx(1.0)
    assert moteur.valider("6.5") == pytest.approx(6.5)


@pytest.mark.parametrize("saisie", ["", "   ", "abc", "12,5km", "0.99", "6.51"])
def test_variable_numerique_saisie_invalide(saisie):
    moteur = VariableNumerique("engine_size", 1.0, 6.5)
    with pytest.raises(DonneeInvalideError):
        moteur.valider(saisie)


def test_variable_numerique_bornes_inversees():
    with pytest.raises(ValueError):
        VariableNumerique("year", 2022, 2000)


# ---------- VariableCategorielle ----------

def test_variable_categorielle_saisie_valide():
    marque = VariableCategorielle("make", ["Toyota", "Honda", "Acura"])
    assert marque.valider("Honda") == "Honda"
    assert marque.valider("  Acura ") == "Acura"


@pytest.mark.parametrize("saisie", ["", "Ferrari", "honda"])
def test_variable_categorielle_saisie_invalide(saisie):
    marque = VariableCategorielle("make", ["Toyota", "Honda"])
    with pytest.raises(DonneeInvalideError):
        marque.valider(saisie)


def test_variable_categorielle_valeurs_triees():
    marque = VariableCategorielle("make", ["Toyota", "Acura", "Honda"])
    assert marque.valeurs == ["Acura", "Honda", "Toyota"]


def test_variable_categorielle_liste_vide():
    with pytest.raises(ValueError):
        VariableCategorielle("make", [])


# ---------- polymorphisme, méthodes spéciales, creer_variables ----------

def test_variable_est_abstraite():
    with pytest.raises(TypeError):
        Variable("x")


def test_polymorphisme_vers_dict():
    variables = [VariableNumerique("year", 2000, 2022),
                 VariableCategorielle("make", ["Honda", "Acura"])]
    assert [v.vers_dict()["type"] for v in variables] == ["numerique", "categorielle"]
    assert variables[0].vers_dict()["min"] == pytest.approx(2000)
    assert variables[1].vers_dict()["valeurs"] == ["Acura", "Honda"]


def test_egalite_et_repr():
    assert VariableNumerique("year", 2000, 2022) == VariableNumerique("year", 2000, 2022)
    assert VariableNumerique("year", 2000, 2022) != VariableNumerique("year", 2001, 2022)
    assert VariableCategorielle("make", ["B", "A"]) == VariableCategorielle("make", ["A", "B"])
    assert "year" in repr(VariableNumerique("year", 2000, 2022))


def test_creer_variables_depuis_donnees(df_petit):
    variables = creer_variables(df_petit)
    noms = [v.nom for v in variables]
    assert noms == COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES
    par_nom = {v.nom: v for v in variables}
    assert par_nom["year"] == VariableNumerique("year", 2010, 2019)
    assert par_nom["make"].valeurs == ["Honda", "Toyota"]


# ---------- hiérarchie marque → modèle → version (listes en cascade) ----------

@pytest.fixture
def hierarchie() -> dict:
    df = pd.DataFrame([
        ligne(make="Honda", model="Civic", trim="LX"),
        ligne(make="Honda", model="Civic", trim="EX"),
        ligne(make="Honda", model="Civic", trim="LX"),      # doublon de version
        ligne(make="Honda", model="Accord", trim="Touring"),
        ligne(make="Toyota", model="Corolla", trim="LE"),
    ])
    return construire_hierarchie(df)


def test_construire_hierarchie_structure(hierarchie):
    assert hierarchie == {
        "Honda": {"Accord": ["Touring"], "Civic": ["EX", "LX"]},
        "Toyota": {"Corolla": ["LE"]},
    }


def test_construire_hierarchie_vide():
    assert construire_hierarchie(pd.DataFrame(columns=COLONNES)) == {}


def test_verifier_combinaison_valide(hierarchie):
    assert verifier_combinaison(hierarchie, "Honda", "Civic", "EX") is None


@pytest.mark.parametrize("marque, modele, version, partie_fautive", [
    ("Lada", "Civic", "LX", "Lada"),          # marque inconnue
    ("Honda", "Corolla", "LE", "Corolla"),    # modèle d'une autre marque
    ("Honda", "Civic", "Touring", "Touring"), # version d'un autre modèle
])
def test_verifier_combinaison_invalide(hierarchie, marque, modele, version, partie_fautive):
    with pytest.raises(DonneeInvalideError, match=partie_fautive):
        verifier_combinaison(hierarchie, marque, modele, version)


# ---------- JeuDeDonnees ----------

def test_jeu_de_donnees_nettoie_a_la_construction(df_petit):
    df = pd.concat([df_petit, pd.DataFrame([ligne(price=-1)])], ignore_index=True)
    assert len(JeuDeDonnees(df)) == 20


def test_separer_tailles_et_colonnes(df_petit):
    X_train, X_test, y_train, y_test = JeuDeDonnees(df_petit).separer(0.25, graine=42)
    assert len(X_train) == 15 and len(X_test) == 5
    assert len(y_train) == 15 and len(y_test) == 5
    assert CIBLE not in X_train.columns
    assert list(X_train.columns) == COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES


def test_separer_reproductible_et_sans_chevauchement(df_petit):
    jeu = JeuDeDonnees(df_petit)
    X_train_1, X_test_1, _, _ = jeu.separer(0.25, graine=7)
    X_train_2, X_test_2, _, _ = jeu.separer(0.25, graine=7)
    assert X_test_1.index.equals(X_test_2.index)
    assert set(X_train_1.index).isdisjoint(X_test_1.index)


@pytest.mark.parametrize("taille_test", [0, 1, -0.2, 1.5])
def test_separer_taille_test_invalide(df_petit, taille_test):
    with pytest.raises(ValueError):
        JeuDeDonnees(df_petit).separer(taille_test)
