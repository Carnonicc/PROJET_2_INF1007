from __future__ import annotations

import math
import tkinter as tk
from tkinter import messagebox, ttk

if __package__:
    from .donnees import miles_vers_kilometres
else:
    from donnees import miles_vers_kilometres


METADONNEES_DEMONSTRATION = {
    "variables": [
        {
            "nom": "miles",
            "etiquette": "Kilométrage (km)",
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
            minimum = min(bornes)
            maximum = max(bornes)
            if nom == "miles":
                minimum = miles_vers_kilometres(minimum)
                maximum = miles_vers_kilometres(maximum)
            variable["minimum"] = minimum
            variable["maximum"] = maximum
        variables.append(variable)
    return {"variables": variables}


def adapter_metadonnees_modele(metadonnees_modele, catalogue):
    variables_modele = metadonnees_modele.get("variables")
    if not isinstance(variables_modele, dict):
        raise ValueError("Les variables du modèle sont absentes ou invalides.")

    definitions_interface = METADONNEES_DEMONSTRATION["variables"]
    noms_attendus = {definition["nom"] for definition in definitions_interface}
    noms_fournis = set(variables_modele)
    if noms_fournis != noms_attendus:
        manquants = sorted(noms_attendus - noms_fournis)
        supplementaires = sorted(noms_fournis - noms_attendus)
        raise ValueError(
            "Les variables du modèle ne correspondent pas aux champs de "
            f"l’interface (manquantes : {manquants}, supplémentaires : "
            f"{supplementaires})."
        )

    variables = []
    for definition in definitions_interface:
        nom = definition["nom"]
        variable_modele = variables_modele[nom]
        variable = {
            "nom": nom,
            "etiquette": definition["etiquette"],
            "type": definition["type"],
        }
        if definition["type"] == "categorie":
            if variable_modele.get("type") != "categorielle":
                raise ValueError(f"Le type de la variable « {nom} » est invalide.")
            variable["choix"] = _options_compatibles(catalogue, nom, {})
        else:
            if variable_modele.get("type") != "numerique":
                raise ValueError(f"Le type de la variable « {nom} » est invalide.")
            try:
                minimum = float(variable_modele["min"])
                maximum = float(variable_modele["max"])
            except (KeyError, TypeError, ValueError) as erreur:
                raise ValueError(f"Les bornes de la variable « {nom} » sont invalides.") from erreur
            if not math.isfinite(minimum) or not math.isfinite(maximum) or minimum > maximum:
                raise ValueError(f"Les bornes de la variable « {nom} » sont invalides.")
            if nom == "miles":
                minimum = miles_vers_kilometres(minimum)
                maximum = miles_vers_kilometres(maximum)
            variable["minimum"] = minimum
            variable["maximum"] = maximum
        variables.append(variable)

    return {
        "variables": variables,
        "metriques": metadonnees_modele.get("metriques", {}),
    }


def formater_montant(montant):
    return f"{montant:,.0f}".replace(",", " ")


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
        if self.on_actualiser_historique is not None:
            self._demander_actualisation()
        if self.on_actualiser_historique is not None:
            self._demander_actualisation()

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
            text="Erreur absolue moyenne sur le test (MAE)",
            padding=10,
        ).grid(row=1, column=0, sticky="s")
        mae = self.metadonnees.get("metriques", {}).get("mae")
        valeur_mae = (
            f"{formater_montant(mae)} $"
            if isinstance(mae, (int, float)) and math.isfinite(mae) and mae >= 0
            else "Non disponible"
        )
        self.score_mae = tk.StringVar(value=valeur_mae)
        ttk.Label(
            panneau_resultat,
            textvariable=self.score_mae,
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
                    if variable["type"] == "entier":
                        bornes = (
                            f"{formater_montant(minimum)} à "
                            f"{formater_montant(maximum)}"
                        )
                    else:
                        bornes = f"{minimum:g} à {maximum:g}"
                    etiquette = f"{etiquette} ({bornes})"
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
        except OSError as erreur:
            messagebox.showerror(
                "Historique non sauvegardé",
                str(erreur),
                parent=self.winfo_toplevel(),
            )

    def _demander_actualisation(self):
        if self.on_actualiser_historique is None:
            self.statut.set("L’historique sera fourni par le traitement du modèle.")
            return
        try:
            self.on_actualiser_historique(self)
        except (OSError, ValueError) as erreur:
            self.statut.set("Impossible de charger l’historique.")
            messagebox.showerror(
                "Historique indisponible",
                str(erreur),
                parent=self.winfo_toplevel(),
            )

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
            prix = formater_montant(float(ligne["prix_estime"]))
            self.tableau.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    ligne.get("date_heure", ""),
                    f"{prix} $",
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
