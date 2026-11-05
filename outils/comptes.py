
#!/usr/bin/env python3
"""Crée les comptes des saisonniers à partir de l'export RH."""

import argparse
import csv
import json
import logging
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
        return datetime.strptime(
            texte, "%d/%m/%Y"
        ).date().isoformat()
    except (ValueError, TypeError):
        return None


def main():
    p = argparse.ArgumentParser(
        description="Comptes des saisonniers"
    )

    p.add_argument("--csv", required=True, type=Path)
    p.add_argument("--sortie", required=True, type=Path)
    p.add_argument("--domaine", default="mistral.test")

    p.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Format de sortie"
    )

    p.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Active les messages détaillés"
    )

    a = p.parse_args()

    # Configuration des logs
    niveau = logging.INFO if a.verbose else logging.ERROR
    logging.basicConfig(
        level=niveau,
        format="%(levelname)s: %(message)s"
    )

    # Vérifier que le fichier existe
    if not a.csv.is_file():
        print(
            f"Erreur : {a.csv} introuvable",
            file=sys.stderr
        )
        return 2

    logins = set()
    vus = set()
    comptes = []
    rejets = []

    try:
        with a.csv.open(
            encoding="utf-8-sig",
            newline=""
        ) as f:

            lecteur = csv.DictReader(f, delimiter=";")

            colonnes = [
                "nom", "prenom", "email_perso",
                "date_arrivee", "site"
            ]

            if not lecteur.fieldnames or not all(
                c in lecteur.fieldnames for c in colonnes
            ):
                print(
                    "Erreur : colonnes manquantes dans le CSV.",
                    file=sys.stderr
                )
                return 1

            for num, ligne in enumerate(lecteur, start=2):

                nom = (ligne.get("nom") or "").strip()
                prenom = (ligne.get("prenom") or "").strip()
                email = (ligne.get("email_perso") or "").strip()
                site = (ligne.get("site") or "").strip()
                date_texte = (
                    ligne.get("date_arrivee") or ""
                ).strip()

                # Vérification du nom
                if not nom:
                    raison = "nom manquant"
                    rejets.append([num, raison])
                    logging.warning(
                        "Ligne %d rejetée : %s", num, raison
                    )
                    continue

                # Vérification du prénom
                if not prenom:
                    raison = "prenom manquant"
                    rejets.append([num, raison])
                    logging.warning(
                        "Ligne %d rejetée : %s", num, raison
                    )
                    continue

                # Vérification de la date
                date = date_iso(date_texte)

                if date is None:
                    raison = "date invalide"
                    rejets.append([num, raison])
                    logging.warning(
                        "Ligne %d rejetée : %s", num, raison
                    )
                    continue

                # Vérification des doublons
                cle = (
                    nom.lower(),
                    prenom.lower(),
                    email.lower()
                )

                if cle in vus:
                    raison = "doublon"
                    rejets.append([num, raison])
                    logging.warning(
                        "Ligne %d rejetée : %s", num, raison
                    )
                    continue

                vus.add(cle)

                # Création du login
                base = (
                    f"{normaliser(prenom)}."
                    f"{normaliser(nom)}"
                )

                login = base
                i = 2

                while login in logins:
                    login = f"{base}{i}"
                    i += 1

                logins.add(login)

                compte = [
                    login,
                    f"{login}@{a.domaine}",
                    nom,
                    prenom,
                    site,
                    date
                ]

                comptes.append(compte)

                logging.info(
                    "Compte créé : %s", login
                )

        # Tri par login
        comptes.sort(key=lambda c: c[0])

        # Création du dossier de sortie
        a.sortie.mkdir(parents=True, exist_ok=True)

        champs = [
            "login", "email", "nom",
            "prenom", "site", "date_arrivee"
        ]

        # Écriture CSV
        if a.format == "csv":
            with (a.sortie / "comptes.csv").open(
                "w", encoding="utf-8", newline=""
            ) as f:

                w = csv.writer(f, delimiter=";")
                w.writerow(champs)
                w.writerows(comptes)

        # Écriture JSON
        else:
            comptes_json = [
                dict(zip(champs, compte))
                for compte in comptes
            ]

            with (a.sortie / "comptes.json").open(
                "w", encoding="utf-8"
            ) as f:

                json.dump(
                    comptes_json,
                    f,
                    indent=2,
                    ensure_ascii=False
                )

        # Écriture des rejets
        with (a.sortie / "rejets.csv").open(
            "w", encoding="utf-8", newline=""
        ) as f:

            w = csv.writer(f, delimiter=";")
            w.writerow(["ligne", "raison"])
            w.writerows(rejets)

        print(
            f"{len(comptes)} comptes créés, "
            f"{len(rejets)} lignes rejetées"
        )

        return 0

    except (OSError, csv.Error) as erreur:
        print(f"Erreur : {erreur}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
