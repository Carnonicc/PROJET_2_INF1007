from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk


METADONNEES_DEMONSTRATION = {
    "variables": [
        {
            "nom": "miles",
            "etiquette": "Kilométrage (miles)",
            "type": "entier",
            "minimum": 0,
            "maximum": 999999,
        },
        {
            "nom": "year",
            "etiquette": "Année",
            "type": "entier",
            "minimum": 1994,
            "maximum": 2022,
        },
        {
            "nom": "make",
            "etiquette": "Marque",
            "type": "categorie",
            "choix": ["Acura", "Chevrolet", "Ford", "Honda", "Toyota"],
        },
        {
            "nom": "model",
            "etiquette": "Modèle",
            "type": "categorie",
            "choix": ["Civic", "F-150", "NSX", "RAV4"],
        },
        {
            "nom": "trim",
            "etiquette": "Version",
            "type": "categorie",
            "choix": ["Base", "EX", "Lariat", "XLT"],
        },
        {
            "nom": "body_type",
            "etiquette": "Type de carrosserie",
            "type": "categorie",
            "choix": ["Berline", "Coupé", "Hayon", "Camionnette"],
        },
        {
            "nom": "drivetrain",
            "etiquette": "Roues motrices",
            "type": "categorie",
            "choix": ["4WD", "FWD", "RWD"],
        },
        {
            "nom": "transmission",
            "etiquette": "Boîte de vitesses",
            "type": "categorie",
            "choix": ["Automatique", "Manuelle"],
        },
        {
            "nom": "fuel_type",
            "etiquette": "Type de carburant",
            "type": "categorie",
            "choix": ["Diesel", "Électrique", "Essence"],
        },
        {
            "nom": "engine_size",
            "etiquette": "Cylindrée",
            "type": "decimal",
            "minimum": 0.6,
            "maximum": 8.3,
        },
        {
            "nom": "engine_block",
            "etiquette": "Configuration du moteur",
            "type": "categorie",
            "choix": ["H", "I", "V"],
        },
    ]
}


def _options_compatibles(
    catalogue,
    variable,
    contraintes,
):
    valeurs = {
        ligne[variable]
        for ligne in catalogue
        if ligne.get(variable)
        and all(ligne.get(nom) == valeur for nom, valeur in contraintes.items())
    }
    return sorted(valeurs, key=str.casefold)


def _metadonnees_du_catalogue(
    catalogue,
):
    variables = []
    for definition in METADONNEES_DEMONSTRATION["variables"]:
        variable = dict(definition)
        nom = variable["nom"]
        valeurs = [ligne[nom] for ligne in catalogue if ligne.get(nom)]
        if variable["type"] == "categorie":
            variable["choix"] = sorted(set(valeurs), key=str.casefold)
        else:
            bornes = [float(valeur) for valeur in valeurs]
            variable["minimum"] = min(bornes)
            variable["maximum"] = max(bornes)
        variables.append(variable)
    return {"variables": variables}


class InterfaceUtilisateur(ttk.Frame):
    def __init__(
        self,
        parent,
        metadonnees,
        on_prediction=None ,
        on_actualiser_historique=None,
        catalogue= None,
    ):
        super().__init__(parent, padding=10)
        self.metadonnees = metadonnees
        self.on_prediction = on_prediction
        self.on_actualiser_historique = on_actualiser_historique
        self.catalogue = catalogue or []
        self.champs_categoriels= {}
        self.annees_disponibles = {
            ligne["year"] for ligne in self.catalogue if ligne.get("year")
        }
        self.champs = {}
        self.lignes_historique = []
        self.pack(fill="both", expand=True)
        self._construire_fenetre()

    def _construire_fenetre(self):
        avertissement = ttk.Label(
            self,
            text=(
                "Avertissement pédagogique : les estimations sont un exercice "
                "et ne constituent pas un conseil financier ni une aide à la "
                "décision d’achat."
            ),
            wraplength=1200,
            justify="center",
            padding=(8, 6),
        )
        avertissement.pack(fill="x")

        onglets = ttk.Notebook(self)
        onglets.pack(fill="both", expand=True, pady=(8, 0))
        page_prediction = ttk.Frame(onglets, padding=12)
        page_historique = ttk.Frame(onglets, padding=12)
        onglets.add(page_prediction, text="Estimer un prix")
        onglets.add(page_historique, text="Historique")

        contenu = ttk.Frame(page_prediction)
        contenu.pack(fill="both", expand=True)
        contenu.columnconfigure(0, weight=1)
        contenu.columnconfigure(1, weight=1)
        contenu.rowconfigure(0, weight=1)

        panneau_saisie = ttk.LabelFrame(
            contenu,
            text="Caractéristiques du véhicule",
            padding=12,
        )
        panneau_saisie.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        panneau_saisie.columnconfigure(0, weight=1)
        panneau_saisie.columnconfigure(1, weight=1)
        panneau_saisie.rowconfigure(0, weight=1)

        conteneur_champs = ttk.Frame(panneau_saisie)
        conteneur_champs.grid(
            row=0,
            column=0,
            columnspan=2,
            sticky="nsew",
        )
        conteneur_champs.columnconfigure(0, weight=1)
        conteneur_champs.columnconfigure(1, weight=1)
        self._construire_champs(conteneur_champs)

        self.statut = tk.StringVar(value="Prêt à recevoir les caractéristiques.")
        ttk.Button(
            panneau_saisie,
            text="Prédire",
            command=self._demander_prediction,
        ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        ttk.Label(
            panneau_saisie,
            textvariable=self.statut,
            wraplength=500,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        panneau_resultat = ttk.Frame(contenu, padding=8)
        panneau_resultat.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        panneau_resultat.columnconfigure(0, weight=1)
        panneau_resultat.rowconfigure(2, weight=1)
        self.resultat = tk.StringVar(
            value="Le résultat de la prédiction apparaîtra ici."
        )
        ttk.Label(
            panneau_resultat,
            textvariable=self.resultat,
            wraplength=560,
            justify="left",
            padding=10,
        ).grid(row=0, column=0, sticky="ew")

        ttk.Label(
            panneau_resultat,
            text="Score R² du modèle (multiplié par 100)",
            padding=10,
        ).grid(row=1, column=0, sticky="s")
        self.score_r2 = tk.StringVar(
            value="Non disponible (modèle non entraîné)"
        )
        ttk.Label(
            panneau_resultat,
            textvariable=self.score_r2,
            font=("TkDefaultFont", 24, "bold"),
            padding=10,
        ).grid(row=2, column=0, sticky="nsew")

        self._construire_historique(page_historique)

    def _construire_champs(self, parent: ttk.Frame):
        for index, variable in enumerate(self.metadonnees["variables"]):
            colonne = index // 6
            ligne = index % 6
            cellule = ttk.Frame(parent, padding=(4, 6))
            cellule.grid(row=ligne, column=colonne, sticky="ew")
            cellule.columnconfigure(0, weight=1)

            etiquette = variable["etiquette"]
            if variable["type"] == "categorie":
                champ: ttk.Entry | ttk.Combobox = ttk.Combobox(
                    cellule,
                    values=variable["choix"],
                    state="readonly",
                    width=30,
                )
                self.champs_categoriels[variable["nom"]] = champ
                champ.bind(
                    "<<ComboboxSelected>>",
                    lambda event, nom=variable["nom"]: self._traiter_selection(
                        event,
                        nom,
                    ),
                )
            else:
                minimum = variable.get("minimum")
                maximum = variable.get("maximum")
                if minimum is not None and maximum is not None:
                    etiquette = f"{etiquette} ({minimum:g} à {maximum:g})"
                champ = ttk.Entry(cellule, width=32)
                if variable["nom"] == "year":
                    champ.bind(
                        "<FocusOut>",
                        lambda event: self._traiter_selection(event, "year"),
                    )

            ttk.Label(cellule, text=etiquette).grid(
                row=0,
                column=0,
                sticky="w",
            )
            champ.grid(row=1, column=0, sticky="ew", pady=(3, 0))
            self.champs[variable["nom"]] = champ

    def _traiter_selection(self, evenement, variable_modifiee):
        del evenement
        self._actualiser_choix(variable_modifiee)

    def _actualiser_choix(self, variable_modifiee):
        if not self.catalogue:
            return

        noms = list(self.champs_categoriels)
        if variable_modifiee == "year":
            for champ in self.champs_categoriels.values():
                champ.set("")
        elif variable_modifiee in self.champs_categoriels:
            position = noms.index(variable_modifiee)
            for nom in noms[position + 1:]:
                self.champs_categoriels[nom].set("")

        contraintes = {}
        champ_annee = self.champs.get("year")
        if champ_annee is not None:
            annee = champ_annee.get()
            if annee in self.annees_disponibles:
                contraintes["year"] = annee

        for nom in noms:
            champ = self.champs_categoriels[nom]
            champ.configure(
                values=_options_compatibles(
                    self.catalogue,
                    nom,
                    contraintes,
                )
            )
            if champ.get():
                contraintes[nom] = champ.get()

    def _construire_historique(self, parent: ttk.Frame):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        self.tableau = ttk.Treeview(
            parent,
            columns=("date", "prix", "vehicule"),
            show="headings",
            height=16,
        )
        self.tableau.heading("date", text="Date et heure")
        self.tableau.heading("prix", text="Prix estimé")
        self.tableau.heading("vehicule", text="Véhicule")
        self.tableau.column("date", width=220, anchor="w")
        self.tableau.column("prix", width=140, anchor="e")
        self.tableau.column("vehicule", width=420, anchor="w")

        barre_defilement = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=self.tableau.yview,
        )
        self.tableau.configure(yscrollcommand=barre_defilement.set)
        self.tableau.grid(row=0, column=0, sticky="nsew")
        barre_defilement.grid(row=0, column=1, sticky="ns")
        self.tableau.bind("<<TreeviewSelect>>", self._afficher_details)

        self.details_historique = tk.Text(
            parent,
            height=7,
            wrap="word",
            state="disabled",
        )
        self.details_historique.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="ew",
            pady=(10, 0),
        )
        ttk.Button(
            parent,
            text="Actualiser l’historique",
            command=self._demander_actualisation,
        ).grid(row=2, column=0, sticky="w", pady=(8, 0))

    def _demander_prediction(self):
        if self.on_prediction is None:
            self.statut.set("Le traitement du modèle sera branché par le collaborateur.")
            return

        saisies = {nom: champ.get() for nom, champ in self.champs.items()}
        try:
            self.on_prediction(self, saisies)
        except ValueError as erreur:
            messagebox.showwarning(
                "Vérifiez les caractéristiques",
                str(erreur),
                parent=self.winfo_toplevel(),
            )

    def _demander_actualisation(self):
        if self.on_actualiser_historique is None:
            self.statut.set("L’historique sera fourni par le traitement du modèle.")
            return
        self.on_actualiser_historique(self)

    def _afficher_details(self, _evenement= None):
        del _evenement
        selection = self.tableau.selection()
        if not selection:
            return
        index = int(selection[0])
        ligne = self.lignes_historique[len(self.lignes_historique) - 1 - index]
        etiquettes = {
            variable["nom"]: variable["etiquette"]
            for variable in self.metadonnees["variables"]
        }
        details = "\n".join(
            f"{etiquettes.get(nom, nom)} : {valeur}"
            for nom, valeur in ligne.get("caracteristiques", {}).items()
        )
        self.details_historique.configure(state="normal")
        self.details_historique.delete("1.0", "end")
        self.details_historique.insert("1.0", details)
        self.details_historique.configure(state="disabled")

    def afficher_resultat(self, texte):
        self.resultat.set(texte)

    def afficher_score_r2(self, score_r2):
        if not math.isfinite(score_r2):
            raise ValueError("Le score R² doit être un nombre fini.")
        self.score_r2.set(f"{score_r2 * 100:.1f} %")

    def afficher_historique(self, lignes):
        self.lignes_historique = lignes
        for identifiant in self.tableau.get_children():
            self.tableau.delete(identifiant)
        for index, ligne in enumerate(reversed(lignes)):
            caracteristiques = ligne.get("caracteristiques", {})
            vehicule = " ".join(
                str(caracteristiques.get(cle, ""))
                for cle in ("year", "make", "model")
            ).strip()
            self.tableau.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    ligne.get("date_heure", ""),
                    ligne.get("prix_estime", ""),
                    vehicule,
                ),
            )

def lancer_interface(
    metadonnees= None,
    on_prediction=None,
    on_actualiser_historique= None,
    catalogue= None,
):
    if catalogue is not None and not catalogue:
        raise ValueError("Le catalogue de véhicules est vide.")
    if metadonnees is None:
        metadonnees = (
            _metadonnees_du_catalogue(catalogue)
            if catalogue is not None
            else METADONNEES_DEMONSTRATION
        )

    fenetre = tk.Tk()
    fenetre.title("Estimation du prix d’une voiture d’occasion")
    fenetre.geometry("1250x820")
    fenetre.minsize(1000, 700)
    InterfaceUtilisateur(
        fenetre,
        metadonnees,
        on_prediction,
        on_actualiser_historique,
        catalogue,
    )
    fenetre.mainloop()
