import csv
from pathlib import Path


if __package__:
    from .interface import lancer_interface
else:
    from interface import lancer_interface


def _charger_catalogue():
    chemin = Path(__file__).resolve().parents[1] / "donnees" / "ca-dealers-used-qc.csv"
    with chemin.open(encoding="utf-8-sig", newline="") as fichier:
        return list(csv.DictReader(fichier))


if __name__ == "__main__":
    lancer_interface(catalogue=_charger_catalogue())
