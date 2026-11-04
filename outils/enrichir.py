#!/usr/bin/env python3
"""Enrichit des adresses avec la réputation Vigie.

Les réponses sont mises en cache une heure dans
~/.cache/mistral/reputation.json pour éviter de redemander la même
adresse sans cesse. Chaque adresse est journalisée "cache" ou "api".
"""

import argparse
import csv
import json
import logging
import os
import sys
# >>> AJOUT 1.1 : time sert à dater les entrées du cache, Path à localiser le fichier
import time
from pathlib import Path
# <<< FIN AJOUT 1.1

from vigie_client import API, appeler, creer_session

log = logging.getLogger("enrichir")

# >>> AJOUT 1.2 : paramètres du cache
CACHE = Path.home() / ".cache" / "mistral" / "reputation.json"  # emplacement imposé par l'énoncé
DUREE = 3600  # durée de validité d'une réponse, en secondes (1 heure)
# <<< FIN AJOUT 1.2

# >>> AJOUT 2.1 : seuil au-dessus duquel une adresse est jugée dangereuse
SEUIL_DANGER = 50  # score >= 50 : apparaît dans le tableau Markdown
# <<< FIN AJOUT 2.1

def lire_adresses(chemin):
    """Dernier mot de chaque ligne, sans doublon (ordre conservé)."""
    adresses = []
    with open(chemin, encoding="utf-8") as f:
        for ligne in f:
            mots = ligne.split()
            if mots and mots[-1] not in adresses:
                adresses.append(mots[-1])
    return adresses


# >>> AJOUT 1.3 : les trois fonctions du cache
def charger_cache():
    """Lit le cache sur disque et le renvoie sous forme de dict {ip: entrée}.

    Fichier absent (premier lancement) ou illisible : on repart d'un cache vide
    plutôt que de planter.
    """
    try:
        with open(CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def sauver_cache(cache):
    """Écrit le cache sur disque de façon atomique.

    On écrit d'abord dans un fichier temporaire puis on le renomme : un autre
    lancement (cron) ne peut ainsi jamais lire un fichier à moitié écrit.
    """
    CACHE.parent.mkdir(parents=True, exist_ok=True)  # crée ~/.cache/mistral au besoin
    tmp = CACHE.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(cache, f)
    os.replace(tmp, CACHE)  # remplacement atomique


def reputation_avec_cache(session, ip, cache):
    """Renvoie la réputation de `ip` : depuis le cache si elle a moins d'une heure,
    sinon depuis l'API. Journalise "cache" ou "api" pour chaque adresse."""
    entree = cache.get(ip)
    # Entrée présente ET récente : on la réutilise sans appeler l'API.
    if entree and time.time() - entree["horodatage"] < DUREE:
        log.info("%s : cache", ip)
        return entree["reponse"]
    # Sinon : vrai appel à l'API, puis on mémorise la réponse avec son horodatage.
    data = appeler(session, f"{API}/reputation/{ip}")
    cache[ip] = {"horodatage": time.time(), "reponse": data}
    log.info("%s : api", ip)
    return data
# <<< FIN AJOUT 1.3

# >>> AJOUT 2.2 : génération du tableau Markdown
def ecrire_markdown(resultats, chemin):
    """Écrit un tableau Markdown des adresses dangereuses (score >= seuil).

    `resultats` est déjà trié (score décroissant), l'ordre est donc conservé.
    """
    dangereuses = [r for r in resultats if r["score"] >= SEUIL_DANGER]

    with open(chemin, "w", encoding="utf-8") as f:
        f.write("| Adresse | Score | Catégories |\n")
        # Ligne de séparation obligatoire pour que GitHub affiche un tableau.
        # ---: aligne la colonne Score à droite.
        f.write("|---|---:|---|\n")
        for r in dangereuses:
            # Un "|" dans une valeur casserait le tableau : on l'échappe.
            cats = ", ".join(r["categories"]).replace("|", "\\|")
            f.write(f"| `{r['ip']}` | {r['score']} | {cats} |\n")

    return len(dangereuses)
# <<< FIN AJOUT 2.2

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--entree", required=True)
    p.add_argument("--sortie", required=True)
    # >>> AJOUT 3 : option --markdown (facultative)
    p.add_argument("--markdown", action="store_true",
                   help="écrit aussi rapport.md (adresses dangereuses)")
    # <<< FIN AJOUT 3
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
    # >>> AJOUT 1.4 : chargement du cache une seule fois, avant la boucle
    cache = charger_cache()
    # <<< FIN AJOUT 1.4
    resultats = []
    try:  # >>> AJOUT : try/finally pour sauvegarder même en cas d'erreur (voir AJOUT 1.6)
        for ip in lire_adresses(args.entree):
            # >>> MODIFIÉ 1.5 : remplace l'ancienne ligne
            #     data = appeler(session, f"{API}/reputation/{ip}")
            data = reputation_avec_cache(session, ip, cache)
            # <<< FIN MODIFIÉ 1.5
            log.info("%s : score %s", ip, data["score"])
            resultats.append({
                "ip": data["ip"],
                "score": data["score"],
                "categories": data["categories"],
            })
    finally:
        # >>> AJOUT 1.6 : sauvegarde du cache, même si une adresse a fait planter la boucle,
        #     pour ne pas perdre les réponses déjà obtenues
        sauver_cache(cache)
        # <<< FIN AJOUT 1.6

    # score décroissant, puis adresse alphabétique
    resultats.sort(key=lambda r: (-r["score"], r["ip"]))

    with open(os.path.join(args.sortie, "rapport.json"), "w", encoding="utf-8") as f:
        json.dump(resultats, f, indent=2)

    with open(os.path.join(args.sortie, "rapport.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["ip", "score", "categories"])
        for r in resultats:
            w.writerow([r["ip"], r["score"], ",".join(r["categories"])])
   
    # >>> AJOUT 4 : écriture du rapport.md si demandé
    if args.markdown:
        n = ecrire_markdown(resultats, os.path.join(args.sortie, "rapport.md"))
        log.info("rapport.md : %d adresse(s) dangereuse(s)", n)
    # <<< FIN AJOUT 4
    return 0


if __name__ == "__main__":
    sys.exit(main())
