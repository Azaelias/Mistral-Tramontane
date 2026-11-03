#!/usr/bin/env python3
import argparse
import json
import re
import sys
from collections import Counter

# Regex de parsing conforme aux spécifications
LIGNE = re.compile(r'^(\S+) \S+ \S+ \[[^\]]+\] "(\S+) (\S+) [^"]*" (\d{3}) ')

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
    sensitive_counter = {path: 0 for path in SENSITIVE_PATHS}

    for line in lines:
        match = LIGNE.search(line)
        if not match:
            continue

        lignes_reconnues += 1
        ip, method, path, status = match.groups()

        statuts_counter[status] += 1

        if status == "404":
            ip_404_counter[ip] += 1

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


if __name__ == "__main__":
    main()
