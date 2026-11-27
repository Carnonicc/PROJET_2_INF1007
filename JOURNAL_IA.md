# Journal d'utilisation de l'IA

Projet 2 INF1007 : estimer le prix d'une voiture d'occasion au Québec.

Équipe : Carnon et Avery. Outil utilisé : **Claude Code** (Anthropic).

Ce journal décrit comment nous avons utilisé l'IA pendant le projet : ce que
nous lui avons demandé, ce que nous avons gardé ou modifié, et comment nous
l'avons vérifié. Le code remis a été relu, compris et testé par l'équipe ;
chacun de nous doit pouvoir expliquer n'importe quelle ligne.

## Notre façon de travailler

- **Les tests d'abord.** Avant que nous écrivions une seule ligne de code, l'IA
  a écrit les tests pytest (`tests/`) à partir de ce que chaque fonction devait
  faire. Ces tests décrivaient le comportement attendu ; nous avons ensuite
  écrit le code pour les faire passer, en lançant `python -m pytest` à chaque
  étape. Les tests ont été complétés au fil du projet (129 tests à la fin).
- **L'équipe décide, l'IA aide.** Les choix du projet ont été pris par nous
  deux ; l'IA a servi à expliquer, proposer des options et coder une fois la
  décision prise.
- **Comprendre avant de garder.** Pour chaque fonction écrite avec l'aide de
  l'IA, nous avons demandé des explications (ce qu'elle fait, pourquoi elle est
  écrite ainsi) jusqu'à pouvoir l'expliquer nous-mêmes.

## Utilisations

| Sujet | Ce que nous avons demandé | Ce qui a été gardé / modifié | Vérification |
| --- | --- | --- | --- |
| Tests | Écrire les tests pytest de chaque module avant le code. | Gardés comme spécification ; complétés au fil du projet (nettoyage, kilomètres, historique). | Lancés à chaque étape et par GitHub Actions à chaque `push`. |
| Compréhension du code | Expliquer des notions peu vues en cours : `ColumnTransformer`, `OneHotEncoder`, décorateurs, classes abstraites, `i % 2`, utilité de certains modules. | Explications seulement. | Questions de compréhension posées par l'IA sur le code, réponses écrites par nous. |
| Corriger les tests qui échouent | Trouver la cause des échecs (ex. `if not X` sur un DataFrame, sauvegarde du pipeline au lieu de l'objet, `pytest.exe` bloqué par Windows). | L'IA a expliqué les causes ; les corrections ont été faites dans notre code. | Les tests passent. |
| Données (`donnees.py`) | Aide pour écrire les classes `Variable`, `nettoyer`, `creer_variables`, `construire_hierarchie`. | Gardé après relecture. Le générateur `lire_par_blocs` a été retiré sur notre décision, car inutile pour un CSV de 2,4 Mo. | Tests de `test_donnees.py`. |
| Nettoyage | Coder nos règles : prix > 100 000 \$, kilométrage > 250 000 miles, marques de moins de 10 annonces, harmonisation des majuscules. | Les seuils ont été choisis par nous ; l'IA les a codés et a ajouté les tests correspondants. | Tests ; nouvelles métriques comparées aux anciennes (voir `DECISIONS.md`). |
| Modèle et entraînement | Expliquer les métadonnées, aider à écrire `entrainer.py`. | Gardé ; nous avons décidé de mettre les fichiers de `modeles/` sur Git. | Script lancé, métriques vérifiées contre le modèle de référence. |
| Interface | Comparer nos deux versions (branches `carnon` et `avery`) et recommander une option. | Version `carnon` gardée, enrichie des idées d'Avery : saisie en kilomètres et gestion de l'`OSError`. | Même prix obtenu avec les deux versions ; tests de l'interface. |
| Graphique dans l'interface | Ajouter un graphique Matplotlib intégré à la fenêtre, mis à jour à chaque prédiction, avec la logique séparée de l'affichage et des tests. | L'IA a proposé un plan (histogramme des prix des annonces comparables avec la position de l'estimation) et signalé que cela obligeait à relire le CSV, contrairement à une décision de `DECISIONS.md` ; nous avons accepté. Nous avons **refusé** que l'IA fasse des commits ou des envois sur GitHub (faits par nous) et exigé que le code existant ne soit pas modifié : le graphique est seulement ajouté (`ReferencePrix` dans `donnees.py`, `ajouter_graphique` dans `application.py`, qui enveloppe le rappel existant sans le changer). Source consultée : exemple Matplotlib « Embedding in Tk ». | 23 nouveaux tests (`tests/test_graphique.py`), les 106 anciens passent toujours ; fenêtre ouverte avec une saisie valide et une saisie invalide. |
| Git et GitHub | Expliquer les branches, les fusions et le retrait d'un fichier du dépôt. | Commandes lancées par nous après explication. | État vérifié sur GitHub. |
| Documentation | Aide à rédiger `DECISIONS.md`, `README.md` et ce journal ; un document d'explication du code pour étudier (retiré du dépôt). | Textes relus et corrigés par nous ; les chiffres viennent de `modeles/metadonnees.json`. | Relecture en équipe. |
| Présentation | Diagramme des liens entre les fichiers et les fonctions pour le PowerPoint. | Relu et adapté par nous. | — |
| Nettoyage du dépôt | Repérer et supprimer les fichiers inutiles (script d'exploration, réglages d'éditeur, doublons). | Supprimés après vérification. | 106 tests passent après le nettoyage. |

## Ce que l'IA n'a pas fait

- Les choix du projet (domaine, jeu de données, seuils de nettoyage, modèle,
  métriques, technologie d'interface) ont été pris par l'équipe (voir
  [DECISIONS.md](DECISIONS.md)).
- Nous ne lui avons pas confié de code sans le relire ni le tester.

## Bilan

- **Ce que l'IA nous a apporté :** des tests écrits dès le départ, qui nous ont
  guidés pendant tout le projet ; des explications sur des notions peu vues en
  cours ; un gain de temps sur le débogage et la documentation.
- **Ses limites :** elle propose parfois plus que nécessaire (comme la lecture
  par blocs, retirée), et il faut vérifier chaque proposition contre nos
  données et l'énoncé.
- **Ce que nous referions :** garder les tests en premier, et demander les
  explications au fur et à mesure plutôt qu'à la fin.
