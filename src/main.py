"""Point d'entrée de l'application.

Lancement (depuis la racine du projet, après « python src/entrainer.py ») :
    python src/main.py
"""

import os

from application import Estimateur, Historique, creer_rappels
from interface import lancer_interface
from modele import ModeleLineaire, charger_metadonnees

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CHEMIN_MODELE = os.path.join(RACINE, "modeles", "modele.joblib")
CHEMIN_METADONNEES = os.path.join(RACINE, "modeles", "metadonnees.json")
CHEMIN_HISTORIQUE = os.path.join(RACINE, "historique.json")


def main() -> None:
    """Charge le modèle et les métadonnées, puis ouvre la fenêtre."""
    try:
        modele = ModeleLineaire.charger(CHEMIN_MODELE)
        metadonnees = charger_metadonnees(CHEMIN_METADONNEES)
    except (FileNotFoundError, ValueError) as erreur:
        print(f"Impossible de lancer l'application : {erreur}")
        print("Entraînez d'abord le modèle avec : python src/entrainer.py")
        return

    historique = Historique(CHEMIN_HISTORIQUE)
    on_prediction, on_actualiser = creer_rappels(Estimateur(modele, metadonnees),
                                                 historique, metadonnees["metriques"])
    lancer_interface(metadonnees, on_prediction, on_actualiser, historique.lignes)


if __name__ == "__main__":
    main()
