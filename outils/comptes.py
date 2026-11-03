#!/usr/bin/env python3
import argparse
import csv
import json
import io
import logging
import os 
import re
import sys
import unicodedata
from datetime import datetime


def normaliser(texte):
    s = unicodedata.normalize("NFKD", texte)
    s = s.encode("ascii", "ignore").decode("utf-8")
    s = s.lower()
    s = re.sub(r"[^a-z-]", "", s)
    return s


def parse_date_iso(date_str):
    if not date_str or not date_str.strip():
        return None
    date_str = date_str.strip()
    formats = ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d")
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None


def main():
<<<<<<< HEAD
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
=======
    parser = argparse.ArgumentParser(
        description="Générateur de comptes CSV avec gestion des rejets et logs"
    )
    parser.add_argument("--csv", help="Fichier CSV source RH")
    parser.add_argument("--sortie", help="Dossier de destination")
    parser.add_argument(
        "--domaine", default="mistral.test", help="Domaine email (défaut: mistral.test)"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Mode verbeux (affiche INFO et WARNING)"
    )
    parser.add_argument("pos_csv", nargs="?", help="Fichier CSV positionnel")
    parser.add_argument("pos_sortie", nargs="?", help="Dossier sortie positionnel")
>>>>>>> 0e4541c (quete M4 ajout du mode verbeux -v avec logging)

    args = parser.parse_args()

    # Configuration du module logging
    # Sans -v : niveau ERROR (silence radio sauf erreur critique)
    # Avec -v : niveau INFO (affiche les INFO et les WARNING de rejets)
    log_level = logging.INFO if args.verbose else logging.ERROR
    logging.basicConfig(level=log_level, format="%(levelname)s: %(message)s")

    fichier_csv = args.csv or args.pos_csv
    dossier_sortie = args.sortie or args.pos_sortie

    if not fichier_csv or not dossier_sortie:
        sys.stderr.write("erreur: arguments --csv et --sortie obligatoires\n")
        sys.exit(2)

    if not os.path.isfile(fichier_csv):
        sys.stderr.write(f"erreur: le fichier {fichier_csv} n'existe pas\n")
        sys.exit(2)

    os.makedirs(dossier_sortie, exist_ok=True)
    logging.info("Dossier de sortie : %s", dossier_sortie)

    try:
        with open(fichier_csv, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()
    except Exception as e:
        sys.stderr.write(f"erreur de lecture de {fichier_csv}: {e}\n")
        sys.exit(2)

    if content.startswith("\ufeff"):
        content = content[1:]

    delimiter = ";" if ";" in content[:2048] else ","
    reader = csv.reader(io.StringIO(content), delimiter=delimiter)

    rows = list(reader)
    if not rows:
        sys.stderr.write("erreur: le fichier CSV est vide\n")
        sys.exit(2)

    logging.info("Lecture de %d lignes dans %s", len(rows), fichier_csv)

    header = [h.lower() for h in rows[0]]

    col_nom = next((i for i, h in enumerate(header) if "nom" in h and "pre" not in h and "email" not in h), 0)
    col_prenom = next((i for i, h in enumerate(header) if "pre" in h or "prénom" in h), 1)
    col_email_perso = next((i for i, h in enumerate(header) if "email" in h or "mail" in h), 2)
    col_date = next((i for i, h in enumerate(header) if "date" in h or "arrive" in h), 3)
    col_site = next((i for i, h in enumerate(header) if "site" in h or "ville" in h), 4)

    accepted_comptes = []
    rejets = []
    accepted_identities = set()
    used_logins = set()

    for idx_line, row in enumerate(rows[1:], start=2):
        if not row or not any(cell.strip() for cell in row):
            continue

        nom = row[col_nom].strip() if len(row) > col_nom else ""
        prenom = row[col_prenom].strip() if len(row) > col_prenom else ""
        email_perso = row[col_email_perso].strip() if len(row) > col_email_perso else ""
        date_raw = row[col_date].strip() if len(row) > col_date else ""
        site = row[col_site].strip() if len(row) > col_site else ""

        # Contrôles de validité avec journalisation en WARNING pour chaque rejet
        if not nom:
            reason = "nom manquant"
            rejets.append((idx_line, reason))
            logging.warning("Ligne %d rejetée : %s", idx_line, reason)
            continue

        if not prenom:
            reason = "prenom manquant"
            rejets.append((idx_line, reason))
            logging.warning("Ligne %d rejetée : %s", idx_line, reason)
            continue

        date_iso = parse_date_iso(date_raw)
        if not date_iso:
            reason = "date invalide"
            rejets.append((idx_line, reason))
            logging.warning("Ligne %d rejetée : %s", idx_line, reason)
            continue

        identity_key = (nom.lower(), prenom.lower(), email_perso.lower())
        if identity_key in accepted_identities:
            reason = "doublon"
            rejets.append((idx_line, reason))
            logging.warning("Ligne %d rejetée : %s", idx_line, reason)
            continue

        accepted_identities.add(identity_key)

<<<<<<< HEAD
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


=======
        norm_p = normaliser(prenom)
        norm_n = normaliser(nom)
        base_login = f"{norm_p}.{norm_n}"

        login = base_login
        counter = 2
        while login in used_logins:
            login = f"{base_login}{counter}"
            counter += 1

        used_logins.add(login)

        logging.info("Compte créé (ligne %d) : %s <%s@%s>", idx_line, login, login, args.domaine)

        accepted_comptes.append({
            "login": login,
            "email": f"{login}@{args.domaine}",
            "nom": nom,
            "prenom": prenom,
            "site": site,
            "date_arrivee": date_iso,
        })

    accepted_comptes.sort(key=lambda c: c["login"])

    # Écriture de comptes.csv
    f_comptes = os.path.join(dossier_sortie, "comptes.csv")
    with open(f_comptes, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["login", "email", "nom", "prenom", "site", "date_arrivee"])
        for c in accepted_comptes:
            writer.writerow([
                c["login"],
                c["email"],
                c["nom"],
                c["prenom"],
                c["site"],
                c["date_arrivee"],
            ])
>>>>>>> 0e4541c (quete M4 ajout du mode verbeux -v avec logging)

    # Écriture de rejets.csv
    f_rejets = os.path.join(dossier_sortie, "rejets.csv")
    with open(f_rejets, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, delimiter=";")
        writer.writerow(["ligne", "raison"])
        for line_num, reason in rejets:
            writer.writerow([line_num, reason])

    # Seule ligne affichée sur stdout en mode normal (sans -v)
    print(f"{len(accepted_comptes)} comptes crees, {len(rejets)} lignes rejetees")


if __name__ == "__main__":
    main()
