"""Crée les comptes des saisonniers à partir de l'export RH."""

import argparse
import csv
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path


def normaliser(texte):
    """Enlève les accents et caractères inutiles."""
    sans_accent = (
        unicodedata.normalize("NFKD", texte)
        .encode("ascii", "ignore")
        .decode()
    )
    return re.sub(r"[^a-z-]", "", sans_accent.lower())


def date_iso(texte):
    """Convertit une date en ISO ou renvoie None."""
    try:
        return datetime.strptime(texte, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return None


def main():
    p = argparse.ArgumentParser(description="Comptes des saisonniers")
    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--sortie", required=True, type=Path)
    p.add_argument("--domaine", default="mistral.test")
##############################################
    p.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Format de sortie (csv ou json)")
    a = p.parse_args()
##############################################

    # Vérifier que le fichier existe
    if not a.csv.is_file():
        print(f"Erreur : {a.csv} introuvable", file=sys.stderr)
        return 2

    logins = set()
    vus = set()
    comptes = []
    rejets = []

    try:
        with a.csv.open(encoding="utf-8-sig", newline="") as f:
            lecteur = csv.DictReader(f, delimiter=";")

            colonnes = ["nom", "prenom", "email_perso",
                        "date_arrivee", "site"]

            if not lecteur.fieldnames or not all(
                colonne in lecteur.fieldnames for colonne in colonnes
            ):
                print("Erreur : colonnes manquantes dans le CSV.",
                      file=sys.stderr)
                return 1

            for num, ligne in enumerate(lecteur, start=2):
                nom = (ligne.get("nom") or "").strip()
                prenom = (ligne.get("prenom") or "").strip()
                email = (ligne.get("email_perso") or "").strip()
                site = (ligne.get("site") or "").strip()
                date_texte = (ligne.get("date_arrivee") or "").strip()

                # 1. Nom manquant
                if not nom:
                    rejets.append([num, "nom manquant"])
                    continue

                # 2. Prénom manquant
                if not prenom:
                    rejets.append([num, "prenom manquant"])
                    continue

                # 3. Date invalide
                date = date_iso(date_texte)
                if date is None:
                    rejets.append([num, "date invalide"])
                    continue

                # 4. Doublon RH
                cle = (nom.lower(), prenom.lower(), email.lower())

                if cle in vus:
                    rejets.append([num, "doublon"])
                    continue

                vus.add(cle)

                # Création du login
                base = f"{normaliser(prenom)}.{normaliser(nom)}"
                login = base
                i = 2

                while login in logins:
                    login = f"{base}{i}"
                    i += 1

                logins.add(login)

                comptes.append([
                    login,
                    f"{login}@{a.domaine}",
                    nom,
                    prenom,
                    site,
                    date,
                ])

        comptes.sort()

        a.sortie.mkdir(parents=True, exist_ok=True)
############################################################################
        # Écrire comptes.csv
#        with (a.sortie / "comptes.csv").open(
 #           "w", encoding="utf-8", newline=""
  #      ) as f:
   #         w = csv.writer(f, delimiter=";")
    #        w.writerow([
     #           "login", "email", "nom", "prenom", "site", "date_arrivee"
      #      ])
       #     w.writerows(comptes)
############################################################################
# Tiago fait des test merci de votre indulgence XD
############################################################################

        champs = [
            "login", "email", "nom", "prenom", "site", "date_arrivee"
        ]

        if a.format == "csv":
            with (a.sortie / "comptes.csv").open(
                "w", encoding="utf-8", newline=""
            ) as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(champs)
                w.writerows(comptes)

        else:
            comptes_json = [
                dict(zip(champs, compte))
                for compte in comptes
            ]

            with (a.sortie / "comptes.json").open(
                "w", encoding="utf-8"
            ) as f:
                json.dump(comptes_json, f, indent=2, ensure_ascii=False)
############################################################################
# Tiago fait des test merci de votre indulgence XD
############################################################################



        # Écrire rejets.csv
        with (a.sortie / "rejets.csv").open(
            "w", encoding="utf-8", newline=""
        ) as f:
            w = csv.writer(f, delimiter=";")
            w.writerow(["ligne", "raison"])
            w.writerows(rejets)

        print(f"{len(comptes)} comptes créés.")
        print(f"{len(rejets)} lignes rejetées.")
        return 0

    except (OSError, csv.Error) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
