
import argparse
import csv
import sys
import os

from urllib.parse import urlencode
from vigie_client import API, creer_session, appeler
# Permet de manipuler les chemins de fichiers
from pathlib import Path

# Permet de compter les incidents par site et par gravité
from collections import Counter

# Permet d'effectuer des requêtes HTTP vers l'API
import requests

API = "http://vigie.mistral.test:8080/api/v1"


def fetch_all_incidents():
    # Récupère le jeton depuis l'environnement
    jeton = os.environ.get("VIGIE_TOKEN")
    if not jeton:
        raise SystemExit("Erreur : VIGIE_TOKEN absent")

    # Crée une session authentifiée
    session = creer_session(jeton)

    tous = []
    page = 1
    total_api = None
    derniere_page = None

    while True:
        # Construit l'URL avec les paramètres de pagination
        params = urlencode({"page": page, "par_page": 20})
        url = f"{API}/incidents?{params}"

        # Appelle le client commun : timeout et reprises inclus
        r = appeler(session, url)

        # Mémorise le total et le nombre de pages annoncés par l'API
        if page == 1:
            total_api = r["total"]
            derniere_page = r["pages"]
            print(f"pages={derniere_page}  total={total_api}")

        # Ajoute les incidents de la page à la liste globale
        tous.extend(r["incidents"])

        # Arrête à la dernière page
        if page >= derniere_page:
            break

        page += 1

    return tous, total_api

def main():
    p = argparse.ArgumentParser(
        description="Compter les incidents par site et par gravité"
    )
    p.add_argument("--sortie", required=True, type=Path)
    args = p.parse_args()

    # Récupère tous les incidents et le total annoncé par l'API
    tous, total_api = fetch_all_incidents()

    # Affiche le nombre d'incidents effectivement récupérés
    print(f"len(tous) = {len(tous)}")

    if len(tous) != total_api:
        raise RuntimeError(
            f"Total incohérent : {len(tous)} incidents récupérés, "
            f"{total_api} annoncés par l'API"
        )

    # Compte les incidents pour chaque couple (site, gravité)
    c = Counter((i["site"], i["gravite"]) for i in tous)

    # Récupère les sites uniques et les trie par ordre alphabétique
    sites = sorted({i["site"] for i in tous})

    # Affiche la liste des sites trouvés
    print(f"sites = {sites}")

    # Ouvre le fichier de sortie en écriture
    with open(args.sortie, "w", newline="", encoding="utf-8") as f:

        # Configure l'écriture du CSV avec le séparateur point-virgule
        w = csv.writer(f, delimiter=";")

        # Écrit la première ligne contenant les noms des colonnes
        w.writerow(["site", "haute", "moyenne", "basse", "total"])

        # Parcourt chaque site dans l'ordre alphabétique
        for s in sites:

            # Récupère le nombre d'incidents de chaque gravité pour ce site
            # Counter renvoie 0 si aucun incident ne correspond à la clé
            ligne = [c[(s, g)] for g in ("haute", "moyenne", "basse")]

            # Écrit le site, les trois nombres et leur somme
            w.writerow([s, *ligne, sum(ligne)])

    print(f"CSV écrit dans {args.sortie}")



if __name__ == "__main__":
    sys.exit(main())
