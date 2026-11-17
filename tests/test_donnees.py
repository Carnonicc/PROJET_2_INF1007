"""Tests du module donnees (lecture, nettoyage, variables, séparation)."""

import os

import pandas as pd
import pytest

from donnees import (
    CIBLE, COLONNES, COLONNES_CATEGORIELLES, COLONNES_NUMERIQUES,
    JeuDeDonnees, Variable, VariableCategorielle, VariableNumerique,
    MILES_MAXIMUM, PRIX_MAXIMUM, charger_csv, construire_hierarchie, creer_variables,
    harmoniser_majuscules, nettoyer,
    kilometres_vers_miles, miles_vers_kilometres, variable_depuis_dict,
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

# minimum_annonces=1 : ces petits tableaux n'ont qu'une ou deux voitures par marque

def test_nettoyer_retire_valeurs_manquantes():
    df = pd.DataFrame([ligne(), ligne(make=None), ligne(miles=float("nan"))])
    assert len(nettoyer(df, minimum_annonces=1)) == 1


def test_nettoyer_retire_valeurs_aberrantes():
    df = pd.DataFrame([ligne(), ligne(price=0), ligne(price=-500), ligne(miles=-1)])
    resultat = nettoyer(df, minimum_annonces=1)
    assert len(resultat) == 1
    assert resultat[CIBLE].iloc[0] == 20000


def test_nettoyer_garde_les_cas_limites_valides():
    """Une voiture neuve (0 mile), un prix de 1 $ et les plafonds exacts sont gardés."""
    df = pd.DataFrame([ligne(miles=0), ligne(price=1), ligne(price=PRIX_MAXIMUM),
                       ligne(miles=MILES_MAXIMUM)])
    assert len(nettoyer(df, minimum_annonces=1)) == 4


@pytest.mark.parametrize("trop", [{"price": PRIX_MAXIMUM + 1}, {"miles": MILES_MAXIMUM + 1},
                                  {"miles": 999_999}])
def test_nettoyer_retire_au_dessus_des_plafonds(trop):
    df = pd.DataFrame([ligne(), ligne(**trop)])
    assert len(nettoyer(df, minimum_annonces=1)) == 1


def test_nettoyer_ne_modifie_pas_l_original():
    df = pd.DataFrame([ligne(), ligne(price=-1), ligne(trim="lx")])
    nettoyer(df, minimum_annonces=1)
    assert len(df) == 3
    assert df["trim"].iloc[2] == "lx"


def test_harmoniser_majuscules_garde_l_ecriture_la_plus_frequente():
    serie = pd.Series(["Base", "base", "Base", "E-PACE", "E-Pace", "LX"])
    # égalité E-PACE / E-Pace : la première dans l'ordre alphabétique
    assert list(harmoniser_majuscules(serie)) == ["Base", "Base", "Base",
                                                  "E-PACE", "E-PACE", "LX"]


def test_nettoyer_harmonise_modele_et_version():
    df = pd.DataFrame([ligne(trim="Base"), ligne(trim="Base"), ligne(trim="base"),
                       ligne(model="civic")])
    resultat = nettoyer(df, minimum_annonces=1)
    assert set(resultat["trim"]) == {"Base", "LX"}
    assert set(resultat["model"]) == {"Civic"}


def test_nettoyer_retire_les_marques_rares():
    df = pd.DataFrame([ligne(make="Honda")] * 3 + [ligne(make="Lotus")] * 2)
    resultat = nettoyer(df, minimum_annonces=3)
    assert list(resultat["make"]) == ["Honda"] * 3


def test_nettoyer_compte_les_marques_apres_les_autres_filtres():
    # 3 Ferrari, mais 2 sont trop chères : il n'en reste qu'une, donc la marque part
    df = pd.DataFrame([ligne(make="Ferrari", price=250_000)] * 2
                      + [ligne(make="Ferrari", price=90_000)] + [ligne()] * 3)
    assert set(nettoyer(df, minimum_annonces=2)["make"]) == {"Honda"}

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
    variables = [VariableNumerique("year", 2000, 2022, entier=True, etiquette="Année"),
                 VariableNumerique("engine_size", 1.0, 6.5),
                 VariableCategorielle("make", ["Honda", "Acura"], etiquette="Marque")]
    assert [v.vers_dict()["type"] for v in variables] == ["entier", "decimal", "categorie"]
    assert variables[0].vers_dict() == {"nom": "year", "etiquette": "Année", "type": "entier",
                                        "minimum": 2000, "maximum": 2022}
    assert variables[2].vers_dict() == {"nom": "make", "etiquette": "Marque",
                                        "type": "categorie", "choix": ["Acura", "Honda"]}


def test_etiquette_par_defaut_et_dans_les_messages():
    assert VariableNumerique("year", 2000, 2022).etiquette == "year"
    annee = VariableNumerique("year", 2000, 2022, etiquette="Année")
    with pytest.raises(DonneeInvalideError, match="Année"):
        annee.valider("1990")


# ---------- variable entière ----------

def test_variable_entiere_renvoie_un_int():
    annee = VariableNumerique("year", 2000, 2022, entier=True)
    assert annee.valider("2015") == 2015
    assert isinstance(annee.valider("2015"), int)
    assert isinstance(annee.valider("2015.0"), int)   # 2015.0 est bien un entier


@pytest.mark.parametrize("saisie", ["2015.5", "2015,5"])
def test_variable_entiere_refuse_les_decimales(saisie):
    annee = VariableNumerique("year", 2000, 2022, entier=True)
    with pytest.raises(DonneeInvalideError, match="entier"):
        annee.valider(saisie)


def test_egalite_et_repr():
    assert VariableNumerique("year", 2000, 2022) == VariableNumerique("year", 2000, 2022)
    assert VariableNumerique("year", 2000, 2022) != VariableNumerique("year", 2001, 2022)
    assert VariableNumerique("year", 2000, 2022) != VariableNumerique("year", 2000, 2022,
                                                                      entier=True)
    assert VariableCategorielle("make", ["B", "A"]) == VariableCategorielle("make", ["A", "B"])
    assert "year" in repr(VariableNumerique("year", 2000, 2022))


def test_creer_variables_depuis_donnees(df_petit):
    variables = creer_variables(df_petit)
    noms = [v.nom for v in variables]
    assert noms == COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES
    par_nom = {v.nom: v for v in variables}
    assert par_nom["year"] == VariableNumerique("year", 2010, 2019, entier=True)
    assert par_nom["year"].etiquette == "Année"
    assert not par_nom["engine_size"].entier
    assert par_nom["make"].valeurs == ["Honda", "Toyota"]


def test_conversion_miles_kilometres():
    assert miles_vers_kilometres(1) == pytest.approx(1.609344)
    assert kilometres_vers_miles(1.609344) == pytest.approx(1)
    assert kilometres_vers_miles(miles_vers_kilometres(60000)) == pytest.approx(60000)


def test_creer_variables_kilometrage_en_km(df_petit):
    # df_petit : de 0 à 95 000 miles, soit de 0 à 152 887,68 km
    kilometrage = {v.nom: v for v in creer_variables(df_petit)}["miles"]
    assert kilometrage.etiquette == "Kilométrage (km)"
    assert kilometrage.vers_dict()["minimum"] == 0
    assert kilometrage.vers_dict()["maximum"] == 152888      # arrondi vers le haut
    assert kilometrage.valider("152888") == 152888          # la borne est acceptée


def test_variable_depuis_dict_aller_retour(df_petit):
    for variable in creer_variables(df_petit):
        recree = variable_depuis_dict(variable.vers_dict())
        assert recree == variable
        assert recree.etiquette == variable.etiquette


def test_variable_depuis_dict_type_inconnu():
    with pytest.raises(ValueError, match="inconnu"):
        variable_depuis_dict({"nom": "x", "type": "date"})


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
