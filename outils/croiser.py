#!/usr/bin/env python3
"""croiser.py : adresses présentes à la fois dans les échecs SSH (auth.log)
et dans les 404 web (access.log), avec les deux compteurs.

Usage : croiser.py [--auth FICHIER] [--web FICHIER]
Sortie : une ligne par adresse, triée par total décroissant.
"""
import argparse
import re
import sys
from collections import Counter

AUTH_DEFAUT = "/var/log/mistral/auth.log"
WEB_DEFAUT = "/srv/mistral/web/access.log"

# auth.log : l'adresse est le mot qui suit "from" sur les lignes d'échec
# (sa colonne varie selon la présence de "invalid user", donc on cherche "from")
ECHEC_SSH = re.compile(r"Failed password .*? from (\S+)")

# access.log : même regex que analyse_web.py, on garde IP et statut
LIGNE_WEB = re.compile(r'^(\S+) \S+ \S+ \[[^\]]+\] "[^"]*" (\d{3}) ')


def compter_ssh(chemin):
    """Retourne un Counter {adresse: nombre d'échecs SSH}."""
    compteur = Counter()
    with open(chemin, "r", encoding="utf-8", errors="replace") as f:
        for ligne in f:
            m = ECHEC_SSH.search(ligne)
            if m:
                compteur[m.group(1)] += 1
    return compteur


def compter_404(chemin):
    """Retourne un Counter {adresse: nombre de 404 web}."""
    compteur = Counter()
    with open(chemin, "r", encoding="utf-8", errors="replace") as f:
        for ligne in f:
            m = LIGNE_WEB.search(ligne)
            if m and m.group(2) == "404":
                compteur[m.group(1)] += 1
    return compteur


def main():
    p = argparse.ArgumentParser(description="Croise échecs SSH et 404 web")
    p.add_argument("--auth", default=AUTH_DEFAUT)
    p.add_argument("--web", default=WEB_DEFAUT)
    a = p.parse_args()

    try:
        ssh = compter_ssh(a.auth)
        web = compter_404(a.web)
    except OSError as e:
        sys.stderr.write(f"erreur de lecture : {e}\n")
        sys.exit(1)

    # Intersection : seules les adresses présentes dans LES DEUX journaux
    communes = set(ssh) & set(web)

    # Tri : total décroissant, puis adresse (ordre alphabétique) pour
    # départager les égalités de façon stable
    lignes = sorted(
        ((ip, ssh[ip], web[ip]) for ip in communes),
        key=lambda t: (-(t[1] + t[2]), t[0]),
    )

    print(f"{'ADRESSE':<18}{'SSH':>6}{'404':>6}{'TOTAL':>8}")
    for ip, n_ssh, n_web in lignes:
        print(f"{ip:<18}{n_ssh:>6}{n_web:>6}{n_ssh + n_web:>8}")


if __name__ == "__main__":
    main()
