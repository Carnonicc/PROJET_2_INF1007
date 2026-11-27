"""Fenêtre Tkinter de l'application.

L'interface se construit entièrement à partir des métadonnées (JSON écrit par
entrainer.py) : un champ par variable, les listes en cascade marque → modèle →
version et le résumé de la qualité du modèle. Elle ne connaît pas le modèle :
la prédiction est faite par la fonction `on_prediction` reçue en paramètre
(voir application.creer_rappels).
"""

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from application import formater_prix, texte_metriques
from exceptions import DonneeInvalideError, EstimationImpossibleError

# graphique intégré à la fenêtre Tkinter, d'après l'exemple « Embedding in Tk » :
# https://matplotlib.org/stable/gallery/user_interfaces/embedding_in_tk_sgskip.html
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

from donnees import DonneesGraphique

COULEUR_ANNONCES = "#257de0"      # barres : les annonces
COULEUR_ESTIMATION = "#f47230"    # ligne : l'estimation de l'utilisateur
COULEUR_TEXTE = "#444444"

# champs en cascade : choisir l'un vide et recalcule ceux qui le suivent
CASCADE = ["make", "model", "trim"]


def options_cascade(hierarchie: dict[str, dict[str, list[str]]], nom: str,
                    selection: dict[str, str]) -> list[str]:
    """Renvoie les choix permis pour `model` ou `trim` selon la sélection actuelle.

    Reçoit : la hiérarchie {marque: {modèle: [versions]}}, le nom du champ et
             {nom: valeur choisie} pour les champs déjà remplis.
    Renvoie : la liste triée (sans tenir compte des majuscules), vide si le champ
              précédent n'est pas encore choisi.
    """
    modeles = hierarchie.get(selection.get("make", ""), {})
    if nom == "model":
        choix = list(modeles)
    elif nom == "trim":
        choix = modeles.get(selection.get("model", ""), [])
    else:
        raise ValueError(f"{nom} ne fait pas partie de la cascade.")
    return sorted(choix, key=str.casefold)


def _formater_borne(valeur: float) -> str:
    """Affiche une borne lisiblement : « 1 609 343 » pour un entier, « 0.6 » sinon.

    (Le format :g donnerait « 1.60934e+06 » pour les grands nombres.)
    """
    if float(valeur).is_integer():
        return f"{int(valeur):,}".replace(",", " ")
    return f"{valeur:g}"


class InterfaceUtilisateur(ttk.Frame):
    """Contenu de la fenêtre : onglet d'estimation et onglet d'historique."""

    def __init__(self, parent: tk.Misc, metadonnees: dict,
                 on_prediction: Callable | None = None,
                 on_actualiser_historique: Callable | None = None) -> None:
        """Reçoit la fenêtre parente, les métadonnées et les deux fonctions de rappel.

        on_prediction(interface, saisies) : appelée par le bouton « Prédire » ;
        on_actualiser_historique(interface) : appelée par « Actualiser l'historique ».
        """
        super().__init__(parent, padding=10)
        self.metadonnees = metadonnees
        self.hierarchie = metadonnees.get("hierarchie", {})
        self.on_prediction = on_prediction
        self.on_actualiser_historique = on_actualiser_historique
        self.champs: dict[str, ttk.Entry | ttk.Combobox] = {}
        self.champs_categoriels: dict[str, ttk.Combobox] = {}
        self.lignes_historique: list[dict] = []
        self.pack(fill="both", expand=True)
        self._construire_fenetre()

    def _construire_fenetre(self) -> None:
        """Crée l'avertissement, les deux onglets et leur contenu."""
        avertissement = ttk.Label(
            self,
            text=("Avertissement pédagogique : les estimations sont un exercice "
                  "et ne constituent pas un conseil financier ni une aide à la "
                  "décision d’achat."),
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

        panneau_saisie = ttk.LabelFrame(contenu, text="Caractéristiques du véhicule",
                                        padding=12)
        panneau_saisie.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        panneau_saisie.columnconfigure(0, weight=1)
        panneau_saisie.columnconfigure(1, weight=1)
        panneau_saisie.rowconfigure(0, weight=1)

        conteneur_champs = ttk.Frame(panneau_saisie)
        conteneur_champs.grid(row=0, column=0, columnspan=2, sticky="nsew")
        conteneur_champs.columnconfigure(0, weight=1)
        conteneur_champs.columnconfigure(1, weight=1)
        self._construire_champs(conteneur_champs)

        self.statut = tk.StringVar(value="Remplissez les caractéristiques puis cliquez sur « Prédire ».")
        ttk.Button(panneau_saisie, text="Prédire", command=self._demander_prediction
                   ).grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 4))
        ttk.Label(panneau_saisie, textvariable=self.statut, wraplength=500, justify="left"
                  ).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(4, 0))

        panneau_resultat = ttk.Frame(contenu, padding=8)
        panneau_resultat.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        panneau_resultat.columnconfigure(0, weight=1)
        self.resultat = tk.StringVar(value="Le résultat de la prédiction apparaîtra ici.")
        ttk.Label(panneau_resultat, textvariable=self.resultat, wraplength=560,
                  justify="left", padding=10, font=("TkDefaultFont", 16, "bold")
                  ).grid(row=0, column=0, sticky="ew")

        qualite = ttk.LabelFrame(panneau_resultat, text="Qualité du modèle (voitures de test)",
                                 padding=10)
        qualite.grid(row=1, column=0, sticky="ew", pady=(20, 0))
        ttk.Label(qualite, text=texte_metriques(self.metadonnees.get("metriques", {})),
                  justify="left").grid(row=0, column=0, sticky="w")

        self._construire_graphique(panneau_resultat)

        self._construire_historique(page_historique)

    def _construire_champs(self, parent: ttk.Frame) -> None:
        """Crée un champ par variable : liste déroulante ou zone de texte."""
        for index, variable in enumerate(self.metadonnees["variables"]):
            colonne = index // 6
            ligne = index % 6
            cellule = ttk.Frame(parent, padding=(4, 6))
            cellule.grid(row=ligne, column=colonne, sticky="ew")
            cellule.columnconfigure(0, weight=1)

            etiquette = variable["etiquette"]
            nom = variable["nom"]
            if variable["type"] == "categorie":
                # modèle et version restent vides tant que le champ précédent n'est pas choisi
                choix = [] if nom in CASCADE[1:] else variable["choix"]
                champ = ttk.Combobox(cellule, values=choix, state="readonly", width=30)
                self.champs_categoriels[nom] = champ
                if nom in CASCADE:
                    champ.bind("<<ComboboxSelected>>",
                               lambda evenement, nom=nom: self._actualiser_choix(nom))
            else:
                etiquette = (f"{etiquette} ({_formater_borne(variable['minimum'])} à "
                             f"{_formater_borne(variable['maximum'])})")
                champ = ttk.Entry(cellule, width=32)

            ttk.Label(cellule, text=etiquette).grid(row=0, column=0, sticky="w")
            champ.grid(row=1, column=0, sticky="ew", pady=(3, 0))
            self.champs[nom] = champ

    def _actualiser_choix(self, variable_modifiee: str) -> None:
        """Après un choix dans la cascade, vide les champs suivants et recalcule leurs choix."""
        position = CASCADE.index(variable_modifiee)
        for nom in CASCADE[position + 1:]:
            if nom not in self.champs_categoriels:
                continue
            champ = self.champs_categoriels[nom]
            champ.set("")
            selection = {n: self.champs_categoriels[n].get()
                         for n in CASCADE if n in self.champs_categoriels}
            champ.configure(values=options_cascade(self.hierarchie, nom, selection))

    def _construire_historique(self, parent: ttk.Frame) -> None:
        """Crée le tableau des estimations, la zone de détails et le bouton."""
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)
        self.tableau = ttk.Treeview(parent, columns=("date", "prix", "vehicule"),
                                    show="headings", height=16)
        self.tableau.heading("date", text="Date et heure")
        self.tableau.heading("prix", text="Prix estimé")
        self.tableau.heading("vehicule", text="Véhicule")
        self.tableau.column("date", width=220, anchor="w")
        self.tableau.column("prix", width=140, anchor="e")
        self.tableau.column("vehicule", width=420, anchor="w")

        barre_defilement = ttk.Scrollbar(parent, orient="vertical",
                                         command=self.tableau.yview)
        self.tableau.configure(yscrollcommand=barre_defilement.set)
        self.tableau.grid(row=0, column=0, sticky="nsew")
        barre_defilement.grid(row=0, column=1, sticky="ns")
        self.tableau.bind("<<TreeviewSelect>>", self._afficher_details)

        self.details_historique = tk.Text(parent, height=7, wrap="word", state="disabled")
        self.details_historique.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Button(parent, text="Actualiser l’historique",
                   command=self._demander_actualisation
                   ).grid(row=2, column=0, sticky="w", pady=(8, 0))

    def _demander_prediction(self) -> None:
        """Bouton « Prédire » : envoie les saisies à on_prediction et affiche les erreurs."""
        if self.on_prediction is None:
            self.statut.set("Aucun modèle n'est branché à l'interface.")
            return

        saisies = {nom: champ.get() for nom, champ in self.champs.items()}
        try:
            self.on_prediction(self, saisies)
        except (DonneeInvalideError, ValueError) as erreur:
            messagebox.showwarning("Vérifiez les caractéristiques", str(erreur),
                                   parent=self.winfo_toplevel())
        except EstimationImpossibleError as erreur:
            self.afficher_resultat(str(erreur))
        except OSError as erreur:
            # idée d'Avery : le prix est affiché, seule la sauvegarde a échoué
            self.statut.set("Prix calculé, mais l'historique n'a pas pu être sauvegardé.")
            messagebox.showerror("Historique non sauvegardé", str(erreur),
                                 parent=self.winfo_toplevel())
        else:
            self.statut.set("Estimation ajoutée à l'historique.")

    def _demander_actualisation(self) -> None:
        """Bouton « Actualiser l'historique »."""
        if self.on_actualiser_historique is None:
            self.statut.set("Aucun historique n'est branché à l'interface.")
            return
        self.on_actualiser_historique(self)

    def _afficher_details(self, _evenement: tk.Event | None = None) -> None:
        """Affiche toutes les caractéristiques de l'estimation choisie dans le tableau."""
        selection = self.tableau.selection()
        if not selection:
            return
        index = int(selection[0])
        # le tableau montre la plus récente en premier : on inverse l'indice
        ligne = self.lignes_historique[len(self.lignes_historique) - 1 - index]
        etiquettes = {variable["nom"]: variable["etiquette"]
                      for variable in self.metadonnees["variables"]}
        details = "\n".join(f"{etiquettes.get(nom, nom)} : {valeur}"
                            for nom, valeur in ligne.get("caracteristiques", {}).items())
        self.details_historique.configure(state="normal")
        self.details_historique.delete("1.0", "end")
        self.details_historique.insert("1.0", details)
        self.details_historique.configure(state="disabled")

    def afficher_resultat(self, texte: str) -> None:
        """Affiche un texte dans la zone de résultat."""
        self.resultat.set(texte)

    def afficher_historique(self, lignes: list[dict]) -> None:
        """Remplace le contenu du tableau par `lignes` (la plus récente en haut)."""
        self.lignes_historique = lignes
        for identifiant in self.tableau.get_children():
            self.tableau.delete(identifiant)
        for index, ligne in enumerate(reversed(lignes)):
            caracteristiques = ligne.get("caracteristiques", {})
            vehicule = " ".join(str(caracteristiques.get(cle, ""))
                                for cle in ("year", "make", "model", "trim")).strip()
            self.tableau.insert("", "end", iid=str(index),
                                values=(ligne.get("date_heure", ""),
                                        formater_prix(ligne.get("prix_estime", 0)),
                                        vehicule))

    # ---------- graphique de comparaison (affichage seulement) ----------

    def _construire_graphique(self, parent: ttk.Frame) -> None:
        """Crée le cadre du graphique Matplotlib, intégré sous la qualité du modèle."""
        cadre = ttk.LabelFrame(parent, text="Comparaison avec les annonces du Québec",
                               padding=6)
        cadre.grid(row=2, column=0, sticky="nsew", pady=(20, 0))
        parent.rowconfigure(2, weight=1)
        self.figure = Figure(figsize=(5.8, 3.6), dpi=100, layout="constrained")
        self.axes = self.figure.add_subplot()
        self.canvas_graphique = FigureCanvasTkAgg(self.figure, master=cadre)
        self.canvas_graphique.get_tk_widget().pack(fill="both", expand=True)
        self.afficher_message_graphique(
            "Le graphique apparaîtra ici après une estimation.")

    def afficher_message_graphique(self, texte: str) -> None:
        """Remplace le graphique par un message (saisie invalide, données absentes...)."""
        self.axes.clear()
        self.axes.set_axis_off()
        self.axes.text(0.5, 0.5, texte, ha="center", va="center", wrap=True,
                       fontsize=11, color=COULEUR_TEXTE, transform=self.axes.transAxes)
        self.canvas_graphique.draw_idle()

    def afficher_graphique(self, donnees: DonneesGraphique) -> None:
        """Dessine l'histogramme des prix des annonces et la ligne de l'estimation."""
        axes = self.axes
        axes.clear()
        axes.set_axis_on()
        bornes = donnees.bornes
        axes.bar(bornes[:-1], donnees.comptes, width=bornes[1:] - bornes[:-1],
                 align="edge", color=COULEUR_ANNONCES, edgecolor="white", linewidth=1,
                 label=f"Annonces {donnees.groupe} ({donnees.nombre_annonces})")
        axes.axvline(donnees.prix_estime, color=COULEUR_ESTIMATION, linewidth=2.5,
                     label=f"Votre estimation : {formater_prix(donnees.prix_estime)}")
        centile = f"{donnees.centile:.0f} %"
        axes.set_title(f"Prix des annonces : {donnees.groupe}\n"
                       f"Votre estimation est plus élevée que {centile} d'entre elles",
                       fontsize=10)
        axes.set_xlabel("Prix affiché dans l'annonce ($)")
        axes.set_ylabel("Nombre d'annonces")
        axes.xaxis.set_major_formatter(
            FuncFormatter(lambda valeur, _position: f"{valeur:,.0f}".replace(",", " ")))
        axes.spines[["top", "right"]].set_visible(False)
        axes.grid(axis="y", color="#e0e0e0", linewidth=0.8)
        axes.set_axisbelow(True)
        axes.legend(fontsize=8, frameon=False, loc="upper right")
        self.canvas_graphique.draw_idle()


def lancer_interface(metadonnees: dict, on_prediction: Callable | None = None,
                     on_actualiser_historique: Callable | None = None,
                     lignes_historique: list[dict] | None = None) -> None:
    """Ouvre la fenêtre et attend que l'utilisateur la ferme."""
    fenetre = tk.Tk()
    fenetre.title("Estimation du prix d’une voiture d’occasion")
    fenetre.geometry("1250x820")
    fenetre.minsize(1000, 700)
    interface = InterfaceUtilisateur(fenetre, metadonnees, on_prediction,
                                     on_actualiser_historique)
    interface.afficher_historique(lignes_historique or [])
    fenetre.mainloop()
