import json

import pytest

from historique import charger_historique, sauvegarder_historique


def test_historique_absent_est_vide(tmp_path):
    assert charger_historique(tmp_path / "absent.json") == []


def test_historique_est_sauvegarde_et_recharge(tmp_path):
    chemin = tmp_path / "sous-dossier" / "historique.json"
    lignes = [{
        "date_heure": "2026-11-14T16:30:00-05:00",
        "prix_estime": 24500.5,
        "caracteristiques": {"year": 2020, "make": "Honda"},
    }]

    sauvegarder_historique(chemin, lignes)

    assert charger_historique(chemin) == lignes
    assert json.loads(chemin.read_text(encoding="utf-8")) == lignes


def test_historique_invalide_est_signale(tmp_path):
    chemin = tmp_path / "historique.json"
    chemin.write_text("{", encoding="utf-8")

    with pytest.raises(ValueError, match="fichier d’historique est invalide"):
        charger_historique(chemin)


def test_historique_refuse_une_entree_non_valide(tmp_path):
    with pytest.raises(ValueError, match="prix.*invalide"):
        sauvegarder_historique(
            tmp_path / "historique.json",
            [{
                "date_heure": "2026-11-14",
                "prix_estime": float("nan"),
                "caracteristiques": {},
            }],
        )


def test_ancien_historique_est_converti_de_miles_en_kilometres(tmp_path):
    chemin = tmp_path / "historique.json"
    chemin.write_text(
        json.dumps([{
            "date_heure": "2026-11-14T16:30:00-05:00",
            "prix_estime": 24500,
            "caracteristiques": {"miles": 100000},
        }]),
        encoding="utf-8",
    )

    lignes = charger_historique(chemin)

    assert lignes[0]["caracteristiques"]["miles"] == pytest.approx(160934.4)
    assert lignes[0]["unites"] == {"miles": "km"}
    assert charger_historique(chemin) == lignes
