#!/usr/bin/env python3
"""Enrichit des adresses avec la réputation Vigie."""

import argparse
import csv
import json
import logging
import os
import sys

from vigie_client import API, appeler, creer_session

log = logging.getLogger("enrichir")


def lire_adresses(chemin):
    """Dernier mot de chaque ligne, sans doublon (ordre conservé)."""
    adresses = []
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            mots = ligne.split()
            if mots and mots[-1] not in adresses:
                adresses.append(mots[-1])
    return adresses


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--entree", required=True)
    p.add_argument("--sortie", required=True)
    args = p.parse_args()

    jeton = os.environ.get("VIGIE_TOKEN", "")
    if not jeton:
        print("erreur : VIGIE_TOKEN est vide", file=sys.stderr)
        return 3

    os.makedirs(args.sortie, exist_ok=True)
    logging.basicConfig(
        filename=os.path.join(args.sortie, "enrichir.log"),
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    session = creer_session(jeton)
    resultats = []
    for ip in lire_adresses(args.entree):
        data = appeler(session, f"{API}/reputation/{ip}")
        log.info("%s : score %s", ip, data["score"])
        resultats.append({
            "ip": data["ip"],
            "score": data["score"],
            "categories": data["categories"],
        })

    # score décroissant, puis adresse alphabétique
    resultats.sort(key=lambda r: (-r["score"], r["ip"]))

    with open(os.path.join(args.sortie, "rapport.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=2)

    with open(os.path.join(args.sortie, "rapport.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ip", "score", "categories"])
        for r in resultats:
            w.writerow([r["ip"], r["score"], ",".join(r["categories"])])

    return 0


if __name__ == "__main__":
    sys.exit(main())
