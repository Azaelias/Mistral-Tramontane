#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import Counter

# Regex de parsing : le 2e groupe (\d{2}) capture l'HEURE du horodatage
# ex. [10/Oct/2026:13:55:36 +0000] -> "13"
LIGNE = re.compile(
    r'^(\S+) \S+ \S+ \[[^:\]]+:(\d{2}):[^\]]+\] "(\S+) (\S+) [^"]*" (\d{3}) '
)

# Chemins sensibles surveillés
SENSITIVE_PATHS = [
    "/.env",
    "/.git/config",
    "/wp-login.php",
    "/wp-admin/",
    "/phpmyadmin/",
    "/backup.zip",
    "/admin/",
]


def main():
    parser = argparse.ArgumentParser(
        description="Analyseur de fichier journal access.log web"
    )
    parser.add_argument("fichier", help="Chemin vers le fichier access.log")
    parser.add_argument(
        "--top",
        type=int,
        default=5,
        help="Nombre de top IP 404 à afficher (défaut: 5)",
    )
    parser.add_argument(
        "--format",
        choices=["texte", "json"],
        default="texte",
        help="Format d'affichage de la sortie (texte ou json)",
    )
    # NOUVEAU : option histogramme des 404 par heure
    parser.add_argument(
        "--par-heure",
        action="store_true",
        help="Affiche un histogramme des 404 par heure (1 # = 10 requêtes)",
    )

    args = parser.parse_args()

    try:
        with open(args.fichier, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    except Exception as e:
        sys.stderr.write(f"erreur de lecture du fichier {args.fichier}: {e}\n")
        sys.exit(1)

    lignes_reconnues = 0
    statuts_counter = Counter()
    ip_404_counter = Counter()
    heure_404_counter = Counter()  # NOUVEAU : 404 comptées par heure
    sensitive_counter = {path: 0 for path in SENSITIVE_PATHS}

    for line in lines:
        match = LIGNE.search(line)
        if not match:
            continue

        lignes_reconnues += 1
        # NOUVEAU : "heure" est récupérée en plus
        ip, heure, method, path, status = match.groups()

        statuts_counter[status] += 1

        if status == "404":
            ip_404_counter[ip] += 1
            heure_404_counter[heure] += 1  # NOUVEAU

        if path in sensitive_counter:
            sensitive_counter[path] += 1

    # Départage des égalités : volume décroissant (-kv[1]), puis ordre alphabétique (kv[0])
    sorted_statuts = dict(
        sorted(
            [(str(k), v) for k, v in statuts_counter.items()],
            key=lambda kv: (-kv[1], kv[0]),
        )
    )

    sorted_top_ip_404 = [
        list(kv)
        for kv in sorted(
            ip_404_counter.items(), key=lambda kv: (-kv[1], kv[0])
        )[: args.top]
    ]

    sorted_chemins_sensibles = [
        list(kv)
        for kv in sorted(
            sensitive_counter.items(), key=lambda kv: (-kv[1], kv[0])
        )
    ]

    if args.format == "json":
        resultat = {
            "lignes": lignes_reconnues,
            "statuts": sorted_statuts,
            "top_ip_404": sorted_top_ip_404,
            "chemins_sensibles": sorted_chemins_sensibles,
        }
        print(json.dumps(resultat, indent=2, ensure_ascii=False))
    else:
        print(f"Rapport d'analyse Web - {lignes_reconnues} lignes reconnues")
        print("\nStatuts HTTP :")
        for st, count in sorted_statuts.items():
            print(f"  {st}: {count}")

        print(f"\nTop {args.top} IP avec erreurs 404 :")
        for ip, count in sorted_top_ip_404:
            print(f"  {ip}: {count}")

        print("\nAccès aux chemins sensibles :")
        for path, count in sorted_chemins_sensibles:
            print(f"  {path}: {count}")

    # NOUVEAU : histogramme des 404 par heure (1 # = 10 requêtes).
    # Uniquement en format texte, pour ne pas casser un JSON lu par jq.
    if args.par_heure and args.format == "texte":
        print("\n404 par heure (1 # = 10 requêtes) :")
        for h in range(24):
            n = heure_404_counter[f"{h:02d}"]
            print(f"  {h:02d}h | {'#' * (n // 10)} {n}")


if __name__ == "__main__":
    main()
