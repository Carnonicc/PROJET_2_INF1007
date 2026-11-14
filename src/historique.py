"""Lecture et sauvegarde locale de l'historique des prédictions."""

import json
import math
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from donnees import miles_vers_kilometres


def _valider_lignes(lignes: object) -> list[dict[str, object]]:
    if not isinstance(lignes, list):
        raise ValueError("L’historique doit être une liste.")

    for index, ligne in enumerate(lignes):
        if not isinstance(ligne, dict):
            raise ValueError(f"La ligne {index + 1} de l’historique est invalide.")
        if not isinstance(ligne.get("date_heure"), str):
            raise ValueError(f"La date de la ligne {index + 1} est invalide.")

        prix = ligne.get("prix_estime")
        try:
            prix_numerique = float(prix)
        except (OverflowError, TypeError, ValueError):
            raise ValueError(f"Le prix de la ligne {index + 1} est invalide.") from None
        if isinstance(prix, bool) or not math.isfinite(prix_numerique) or prix_numerique <= 0:
            raise ValueError(f"Le prix de la ligne {index + 1} est invalide.")

        caracteristiques = ligne.get("caracteristiques")
        if not isinstance(caracteristiques, dict) or not all(
            isinstance(nom, str) for nom in caracteristiques
        ):
            raise ValueError(
                f"Les caractéristiques de la ligne {index + 1} sont invalides."
            )
        unites = ligne.get("unites")
        if unites is None:
            if "miles" in caracteristiques:
                try:
                    miles = float(caracteristiques["miles"])
                except (OverflowError, TypeError, ValueError):
                    raise ValueError(
                        f"Le kilométrage de la ligne {index + 1} est invalide."
                    ) from None
                if not math.isfinite(miles) or miles < 0:
                    raise ValueError(
                        f"Le kilométrage de la ligne {index + 1} est invalide."
                    )
                kilometres = miles_vers_kilometres(miles)
                caracteristiques["miles"] = (
                    int(round(kilometres))
                    if round(kilometres, 6).is_integer()
                    else round(kilometres, 6)
                )
            ligne["unites"] = {"miles": "km"}
        elif unites != {"miles": "km"}:
            raise ValueError(f"Les unités de la ligne {index + 1} sont invalides.")
        elif "miles" in caracteristiques:
            try:
                kilometres = float(caracteristiques["miles"])
            except (OverflowError, TypeError, ValueError):
                raise ValueError(
                    f"Le kilométrage de la ligne {index + 1} est invalide."
                ) from None
            if not math.isfinite(kilometres) or kilometres < 0:
                raise ValueError(
                    f"Le kilométrage de la ligne {index + 1} est invalide."
                )
            kilometres = round(kilometres, 6)
            caracteristiques["miles"] = (
                int(kilometres) if kilometres.is_integer() else kilometres
            )

    return lignes


def charger_historique(chemin: str | Path) -> list[dict[str, object]]:
    """Charge l’historique. Un fichier absent représente un historique vide."""
    chemin = Path(chemin)
    if not chemin.exists():
        return []

    try:
        with chemin.open(encoding="utf-8") as fichier:
            lignes = json.load(fichier)
    except json.JSONDecodeError as erreur:
        raise ValueError(f"Le fichier d’historique est invalide : {chemin}") from erreur

    avant_normalisation = json.dumps(lignes, ensure_ascii=False, sort_keys=True)
    lignes = _valider_lignes(lignes)
    apres_normalisation = json.dumps(lignes, ensure_ascii=False, sort_keys=True)
    if avant_normalisation != apres_normalisation:
        sauvegarder_historique(chemin, lignes)
    return lignes


def sauvegarder_historique(
    chemin: str | Path,
    lignes: list[dict[str, object]],
) -> None:
    """Sauvegarde l’historique en remplaçant le fichier de façon atomique."""
    chemin = Path(chemin)
    lignes = _valider_lignes(lignes)
    chemin.parent.mkdir(parents=True, exist_ok=True)

    temporaire = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=chemin.parent,
            prefix=f".{chemin.name}.",
            suffix=".tmp",
            delete=False,
        ) as fichier:
            temporaire = Path(fichier.name)
            json.dump(lignes, fichier, indent=2, ensure_ascii=False, allow_nan=False)
            fichier.flush()
            os.fsync(fichier.fileno())
        os.replace(temporaire, chemin)
    finally:
        if temporaire is not None and temporaire.exists():
            temporaire.unlink()
