import csv
import math
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

DOSSIER_SRC = Path(__file__).resolve().parent
if str(DOSSIER_SRC) not in sys.path:
    # Le fichier joblib référence la classe sous le nom de module `modele`.
    sys.path.insert(0, str(DOSSIER_SRC))

from donnees import (COLONNES_CATEGORIELLES, COLONNES_NUMERIQUES,
                     VariableNumerique, kilometres_vers_miles,
                     miles_vers_kilometres)
from exceptions import DonneeInvalideError
from interface import adapter_metadonnees_modele, formater_montant, lancer_interface
from historique import charger_historique, sauvegarder_historique
from modele import ModeleLineaire, charger_metadonnees


RACINE = Path(__file__).resolve().parents[1]
CHEMIN_CSV = RACINE / "donnees" / "ca-dealers-used-qc.csv"
CHEMIN_METADONNEES = RACINE / "modeles" / "metadonnees.json"
CHEMIN_MODELE = RACINE / "modeles" / "modele.joblib"
CHEMIN_HISTORIQUE = RACINE / "donnees" / "historique.json"


def _charger_catalogue() -> list[dict[str, str]]:
    chemin = CHEMIN_CSV
    with chemin.open(encoding="utf-8-sig", newline="") as fichier:
        return list(csv.DictReader(fichier))


def _creer_callback_prediction(modele, metadonnees, historique, chemin_historique):
    variables = metadonnees["variables"]

    def predire(interface, saisies):
        caracteristiques = {}
        for nom in COLONNES_NUMERIQUES:
            definition = variables[nom]
            minimum = definition["min"]
            maximum = definition["max"]
            if nom == "miles":
                minimum = miles_vers_kilometres(minimum)
                maximum = miles_vers_kilometres(maximum)
            try:
                valeur = VariableNumerique(
                    nom, minimum, maximum
                ).valider(saisies.get(nom, ""))
            except DonneeInvalideError as erreur:
                raise ValueError(str(erreur)) from erreur
            if nom in {"miles", "year"}:
                if not valeur.is_integer():
                    raise ValueError(f"Le champ « {nom} » doit être un entier.")
                caracteristiques[nom] = int(valeur)
            else:
                caracteristiques[nom] = valeur

        for nom in COLONNES_CATEGORIELLES:
            definition = variables[nom]
            if definition["type"] != "categorielle":
                raise ValueError(f"Le type de la variable « {nom} » est invalide.")
            valeur = saisies.get(nom, "").strip()
            if not valeur:
                raise ValueError(f"Veuillez choisir une valeur pour « {nom} ».")
            caracteristiques[nom] = valeur

        colonnes = COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES
        entrees_modele = dict(caracteristiques)
        entrees_modele["miles"] = kilometres_vers_miles(
            caracteristiques["miles"]
        )
        X = pd.DataFrame([entrees_modele], columns=colonnes)
        prix = float(modele.predire(X)[0])
        if not math.isfinite(prix):
            raise ValueError("Le modèle n’a pas produit une estimation finie.")
        if prix <= 0:
            raise ValueError(
                "Le modèle a produit une estimation nulle ou négative; "
                "aucun prix ne peut être affiché pour ces caractéristiques."
            )

        ligne = {
            "date_heure": datetime.now().astimezone().isoformat(timespec="seconds"),
            "prix_estime": prix,
            "caracteristiques": caracteristiques,
            "unites": {"miles": "km"},
        }
        nouvelles_lignes = [*historique, ligne]
        interface.afficher_resultat(
            f"Prix estimé : {formater_montant(prix)} $"
        )
        try:
            sauvegarder_historique(chemin_historique, nouvelles_lignes)
        except OSError:
            interface.statut.set(
                "Prédiction calculée, mais l’historique n’a pas pu être sauvegardé."
            )
            raise

        historique[:] = nouvelles_lignes
        interface.afficher_historique(historique)
        interface.statut.set("Prédiction terminée.")

    return predire


def _creer_callback_actualisation(historique):
    def actualiser(interface):
        interface.afficher_historique(historique)

    return actualiser


def main() -> None:
    catalogue = _charger_catalogue()
    metadonnees = charger_metadonnees(str(CHEMIN_METADONNEES))
    modele = ModeleLineaire.charger(str(CHEMIN_MODELE))
    historique = charger_historique(CHEMIN_HISTORIQUE)
    metadonnees_interface = adapter_metadonnees_modele(metadonnees, catalogue)
    lancer_interface(
        metadonnees=metadonnees_interface,
        on_prediction=_creer_callback_prediction(
            modele, metadonnees, historique, CHEMIN_HISTORIQUE
        ),
        on_actualiser_historique=_creer_callback_actualisation(historique),
        catalogue=catalogue,
    )


if __name__ == "__main__":
    main()
