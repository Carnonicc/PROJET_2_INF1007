"""Exceptions personnalisées du projet de prédiction de prix de voitures."""


class DonneeInvalideError(Exception):
    """Levée quand une donnée (fichier, colonne ou saisie utilisateur) est invalide."""


class ModeleNonEntraineError(Exception):
    """Levée quand on demande une prédiction à un modèle qui n'a pas été entraîné."""


class EstimationImpossibleError(Exception):
    """Levée quand le modèle donne un prix impossible (nul ou négatif)."""


class GraphiqueIndisponibleError(Exception):
    """Levée quand les données du graphique de comparaison ne peuvent pas être préparées."""
