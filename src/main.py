"""Point d'entrée de l'application.

Lancement (depuis la racine du projet, après « python src/entrainer.py ») :
    python src/main.py
"""

import os

from application import Estimateur, Historique, creer_rappels
from interface import lancer_interface
from modele import ModeleLineaire, charger_metadonnees
from application import ajouter_graphique
from donnees import ReferencePrix
from exceptions import DonneeInvalideError

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CHEMIN_MODELE = os.path.join(RACINE, "modeles", "modele.joblib")
CHEMIN_METADONNEES = os.path.join(RACINE, "modeles", "metadonnees.json")
# avec les autres données; fichier propre à chaque utilisateur, ignoré par Git
CHEMIN_HISTORIQUE = os.path.join(RACINE, "donnees", "historique.json")
# annonces du Québec : servent seulement au graphique de comparaison
CHEMIN_CSV = os.path.join(RACINE, "donnees", "ca-dealers-used-qc.csv")


def charger_reference(chemin: str) -> ReferencePrix | None:
    """Charge les annonces du graphique ; renvoie None (sans planter) si c'est impossible."""
    if not os.path.exists(chemin):
        print(f"Graphique désactivé : fichier introuvable ({chemin}).")
        return None
    try:
        return ReferencePrix.depuis_csv(chemin)
    except (FileNotFoundError, DonneeInvalideError) as erreur:
        print(f"Graphique désactivé : {erreur}")
        return None


def main() -> None:
    """Charge le modèle, les métadonnées et l'historique, puis ouvre la fenêtre."""
    try:
        modele = ModeleLineaire.charger(CHEMIN_MODELE)
        metadonnees = charger_metadonnees(CHEMIN_METADONNEES)
    except (FileNotFoundError, ValueError) as erreur:
        print(f"Impossible de lancer l'application : {erreur}")
        print("Entraînez d'abord le modèle avec : python src/entrainer.py")
        return
    try:
        historique = Historique(CHEMIN_HISTORIQUE)
    except ValueError as erreur:
        print(f"Impossible de lancer l'application : {erreur}")
        return

    on_prediction, on_actualiser = creer_rappels(Estimateur(modele, metadonnees),
                                                 historique, metadonnees["metriques"])
    on_prediction = ajouter_graphique(on_prediction, Estimateur(modele, metadonnees),
                                      charger_reference(CHEMIN_CSV))
    lancer_interface(metadonnees, on_prediction, on_actualiser, historique.lignes)


if __name__ == "__main__":
    main()
