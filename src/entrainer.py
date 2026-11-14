"""Entraîne le modèle UNE fois et écrit les fichiers que l'application relit.

Lancement (depuis la racine du projet) :
    python src/entrainer.py

Produit, dans le dossier modeles/ :
    modele.joblib        le modèle de régression linéaire entraîné
    metadonnees.json     variables, métriques et hiérarchie marque → modèle → version
    predit_vs_reel.png   graphique « prix prédit contre prix réel » sur l'ensemble de test
"""

import os

import matplotlib
matplotlib.use("Agg")   # dessine dans un fichier, sans ouvrir de fenêtre
import matplotlib.pyplot as plt
import numpy as np

from donnees import (COLONNES_CATEGORIELLES, COLONNES_NUMERIQUES, JeuDeDonnees,
                     charger_csv, construire_hierarchie, creer_variables)
from modele import ModeleLineaire, ModeleReference, sauvegarder_metadonnees

RACINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CHEMIN_CSV = os.path.join(RACINE, "donnees", "ca-dealers-used-qc.csv")
DOSSIER_MODELES = os.path.join(RACINE, "modeles")
CHEMIN_MODELE = os.path.join(DOSSIER_MODELES, "modele.joblib")
CHEMIN_METADONNEES = os.path.join(DOSSIER_MODELES, "metadonnees.json")
CHEMIN_GRAPHIQUE = os.path.join(DOSSIER_MODELES, "predit_vs_reel.png")

TAILLE_TEST = 0.2
GRAINE = 42


def tracer_predit_contre_reel(y_reel: np.ndarray, y_predit: np.ndarray, chemin: str) -> None:
    """Enregistre le graphique « prix prédit contre prix réel ».

    Reçoit : les vrais prix, les prix prédits (même longueur) et le chemin du PNG.
    Chaque point est une voiture ; plus il est proche de la diagonale, meilleure
    est la prédiction.
    """
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(y_reel, y_predit, s=4, alpha=0.3, label="Voitures de l'ensemble de test")
    borne = max(np.max(y_reel), np.max(y_predit))
    ax.plot([0, borne], [0, borne], color="red", label="Prédiction parfaite")
    ax.set_title("Prix prédit contre prix réel (ensemble de test)")
    ax.set_xlabel("Prix réel ($)")
    ax.set_ylabel("Prix prédit ($)")
    ax.legend()
    fig.savefig(chemin, dpi=150, bbox_inches="tight")
    plt.close(fig)   # libère la mémoire de la figure


def main() -> None:
    """Charge, nettoie, entraîne, évalue et sauvegarde le modèle."""
    # 1-2. données : chargement, nettoyage (dans JeuDeDonnees) et séparation
    jeu = JeuDeDonnees(charger_csv(CHEMIN_CSV))
    X_train, X_test, y_train, y_test = jeu.separer(taille_test=TAILLE_TEST, graine=GRAINE)
    print(f"{len(jeu)} voitures : {len(X_train)} pour l'entraînement, {len(X_test)} pour le test")

    # 3. entraînement des deux modèles
    reference = ModeleReference()
    reference.entrainer(X_train, y_train)
    modele = ModeleLineaire(COLONNES_NUMERIQUES, COLONNES_CATEGORIELLES)
    modele.entrainer(X_train, y_train)
    print(f"Entraînement de la régression : {modele.entrainer.derniere_duree:.2f} s")

    # 4. évaluation sur l'ensemble de TEST (voitures jamais vues)
    score_ref = reference.evaluer(X_test, y_test)
    score_lin = modele.evaluer(X_test, y_test)
    for nom, score in (("Référence (moyenne)", score_ref), ("Régression linéaire", score_lin)):
        print(f"{nom:20} MAE {score['mae']:>9,.0f} $   RMSE {score['rmse']:>9,.0f} $   "
              f"à ±2000 $ : {score['taux_2000']:.1%}")

    # 5. sauvegarde du modèle
    os.makedirs(DOSSIER_MODELES, exist_ok=True)
    modele.sauvegarder(CHEMIN_MODELE)

    # 6. métadonnées : construites depuis X_train, ce que le modèle a réellement vu
    metriques = {
        "mae": float(score_lin["mae"]),
        "rmse": float(score_lin["rmse"]),
        "taux_2000": float(score_lin["taux_2000"]),
        "mae_reference": float(score_ref["mae"]),
        "taux_2000_reference": float(score_ref["taux_2000"]),
    }
    sauvegarder_metadonnees(CHEMIN_METADONNEES, creer_variables(X_train), metriques,
                            construire_hierarchie(X_train))

    # 7. graphique prédit contre réel
    tracer_predit_contre_reel(y_test.to_numpy(), modele.predire(X_test), CHEMIN_GRAPHIQUE)
    print(f"Fichiers écrits dans {os.path.normpath(DOSSIER_MODELES)}")


if __name__ == "__main__":
    main()
