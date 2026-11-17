"""Logique de l'application, séparée de la fenêtre Tkinter pour être testée avec pytest.

- Estimateur : valide les saisies de l'utilisateur et prédit un prix ;
- Historique : garde les estimations faites et les sauvegarde en JSON ;
- creer_rappels : crée les fonctions appelées par les boutons de l'interface ;
- formater_prix, texte_metriques, texte_resultat : mise en forme pour l'affichage.
"""

import json
import os
from datetime import datetime
from typing import Callable

import pandas as pd

from donnees import (COLONNES_CATEGORIELLES, COLONNES_NUMERIQUES, kilometres_vers_miles,
                     variable_depuis_dict, verifier_combinaison)
from exceptions import EstimationImpossibleError
from modele import TOLERANCE, ModelePrix


def formater_prix(prix: float) -> str:
    """Renvoie le prix arrondi au dollar, avec une espace entre les milliers : « 23 450 $ »."""
    return f"{prix:,.0f} $".replace(",", " ")


def texte_metriques(metriques: dict[str, float]) -> str:
    """Résume la qualité du modèle en quelques lignes lisibles.

    Reçoit : le dictionnaire "metriques" du JSON (mae, taux_2000, et
             éventuellement mae_reference). Un dictionnaire vide donne un message.
    """
    if "mae" not in metriques or "taux_2000" not in metriques:
        return "Qualité du modèle non disponible."
    # pourcentage à la française : 26,7 % (virgule décimale)
    pourcentage = f"{metriques['taux_2000'] * 100:.1f} %".replace(".", ",")
    lignes = [
        f"Erreur moyenne (MAE) : {formater_prix(metriques['mae'])}",
        f"Prédictions à ±{formater_prix(TOLERANCE)} du vrai prix : {pourcentage}",
    ]
    if "mae_reference" in metriques:
        lignes.append("Modèle de référence (prix moyen) : erreur moyenne de "
                      f"{formater_prix(metriques['mae_reference'])}")
    return "\n".join(lignes)


def texte_resultat(prix: float, metriques: dict[str, float]) -> str:
    """Texte affiché après une estimation : le prix et l'erreur moyenne du modèle."""
    texte = f"Prix estimé : {formater_prix(prix)}"
    if "mae" in metriques:
        texte += (f"\nEn moyenne, le modèle se trompe de {formater_prix(metriques['mae'])}"
                  " : c'est un ordre de grandeur, pas un prix exact.")
    return texte


class Estimateur:
    """Transforme les saisies de l'interface en prix prédit."""

    def __init__(self, modele: ModelePrix, metadonnees: dict) -> None:
        """Reçoit un modèle entraîné et les métadonnées lues par charger_metadonnees."""
        self._modele = modele
        self._variables = [variable_depuis_dict(d) for d in metadonnees["variables"]]
        self._hierarchie = metadonnees["hierarchie"]

    def valider(self, saisies: dict[str, str]) -> dict:
        """Valide chaque saisie avec sa Variable, puis le trio marque/modèle/version.

        Reçoit : {nom de colonne: texte saisi}.
        Renvoie : {nom de colonne: valeur convertie (int, float ou str)}.
        Échoue : DonneeInvalideError à la première saisie invalide.
        """
        valeurs = {}
        for variable in self._variables:
            # polymorphisme : chaque type de Variable valide à sa façon
            valeurs[variable.nom] = variable.valider(saisies.get(variable.nom, ""))
        verifier_combinaison(self._hierarchie, valeurs["make"], valeurs["model"],
                             valeurs["trim"])
        return valeurs

    def estimer(self, saisies: dict[str, str]) -> tuple[float, dict]:
        """Renvoie (prix prédit, caractéristiques validées).

        Le kilométrage est saisi en km : il est converti en miles pour le modèle,
        mais les caractéristiques renvoyées (et donc l'historique) restent en km.
        Échoue : DonneeInvalideError si une saisie est invalide ;
                 EstimationImpossibleError si le prix prédit est <= 0.
        """
        caracteristiques = self.valider(saisies)
        entrees_modele = dict(caracteristiques)      # copie : on garde les km pour l'affichage
        entrees_modele["miles"] = kilometres_vers_miles(caracteristiques["miles"])
        # une seule voiture : un DataFrame d'une ligne, avec les colonnes du modèle
        X = pd.DataFrame([entrees_modele])[COLONNES_NUMERIQUES + COLONNES_CATEGORIELLES]
        prix = float(self._modele.predire(X)[0])
        if prix <= 0:
            raise EstimationImpossibleError(
                "Estimation impossible pour ce véhicule : le modèle linéaire donne un prix "
                "négatif. Cela arrive pour des combinaisons rares ou très anciennes.")
        return prix, caracteristiques


class Historique:
    """Liste des estimations faites, sauvegardée dans un fichier JSON."""

    def __init__(self, chemin: str | None = None) -> None:
        """Reçoit le chemin du fichier JSON (None : historique en mémoire seulement).

        Si le fichier existe déjà, les anciennes estimations sont relues.
        Échoue : ValueError si le fichier existe mais est abîmé (JSON mal formé
                 ou pas une liste), par exemple après une modification à la main.
        """
        self._chemin = chemin
        self._lignes: list[dict] = []
        if chemin is not None and os.path.exists(chemin):
            try:
                with open(chemin, encoding="utf-8") as f:
                    lignes = json.load(f)
            except json.JSONDecodeError:
                # idée d'Avery : un message clair plutôt qu'une erreur incompréhensible
                raise ValueError(f"Le fichier d'historique est abîmé : {chemin}. "
                                 "Supprimez-le pour repartir d'un historique vide.") from None
            if not isinstance(lignes, list):
                raise ValueError(f"Le fichier d'historique ne contient pas une liste : {chemin}.")
            self._lignes = lignes

    def __len__(self) -> int:
        return len(self._lignes)

    @property
    def lignes(self) -> list[dict]:
        """Copie de la liste des estimations, de la plus ancienne à la plus récente."""
        return list(self._lignes)

    def ajouter(self, prix: float, caracteristiques: dict,
                date_heure: datetime | None = None) -> dict:
        """Ajoute une estimation, sauvegarde le fichier et renvoie la ligne ajoutée."""
        date_heure = date_heure or datetime.now()
        ligne = {
            "date_heure": date_heure.strftime("%Y-%m-%d %H:%M:%S"),
            "prix_estime": round(prix, 2),
            "caracteristiques": dict(caracteristiques),
        }
        self._lignes.append(ligne)
        self.sauvegarder()
        return ligne

    def sauvegarder(self) -> None:
        """Écrit l'historique dans son fichier JSON (rien si aucun chemin)."""
        if self._chemin is None:
            return
        with open(self._chemin, "w", encoding="utf-8") as f:
            json.dump(self._lignes, f, indent=2, ensure_ascii=False)


def creer_rappels(estimateur: Estimateur, historique: Historique,
                  metriques: dict[str, float]) -> tuple[Callable, Callable]:
    """Crée les deux fonctions que l'interface appelle quand on clique sur ses boutons.

    Renvoie : (on_prediction, on_actualiser_historique). L'interface reçoit ces
              fonctions sans savoir comment le prix est calculé.
    """

    def on_prediction(interface, saisies: dict[str, str]) -> None:
        # les erreurs (DonneeInvalideError, EstimationImpossibleError, OSError)
        # remontent jusqu'à l'interface, qui les affiche
        prix, caracteristiques = estimateur.estimer(saisies)
        # le prix s'affiche AVANT la sauvegarde : si l'écriture du fichier échoue
        # (OSError : disque plein, fichier verrouillé...), l'utilisateur a sa réponse
        interface.afficher_resultat(texte_resultat(prix, metriques))
        try:
            historique.ajouter(prix, caracteristiques)
        finally:
            # finally : s'exécute même si ajouter lève une erreur
            interface.afficher_historique(historique.lignes)

    def on_actualiser_historique(interface) -> None:
        interface.afficher_historique(historique.lignes)

    return on_prediction, on_actualiser_historique
