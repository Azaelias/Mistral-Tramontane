#!/usr/bin/env bash
# top-attaquants.sh : affiche les N adresses qui ont le plus de
# « Failed password » dans FICHIER.
#
# Usage : top-attaquants.sh [-n N] [FICHIER]
#   -n N     nombre d'adresses à afficher (entier >= 1, défaut : 5)
#   FICHIER  journal à analyser (défaut : /var/log/mistral/auth.log)
#
# Sortie : "NOMBRE ADRESSE", une ligne par adresse, du plus grand au plus petit.
#
# Codes de sortie :
#   0 : succès
#   1 : erreur d'utilisation
#   2 : fichier illisible

set -u

usage() {
    cat <<EOF
Usage : $(basename "$0") [-n N] [FICHIER]
  Affiche les N adresses (5 par défaut) qui ont le plus de
  « Failed password » dans FICHIER (défaut : /var/log/mistral/auth.log).
EOF
}

N=5
FICHIER_DEFAUT="/var/log/mistral/auth.log"

# --- Lecture des options ---
while getopts ":n:" opt; do
    case "$opt" in
        n) N="$OPTARG" ;;
        :)
            echo "Erreur : l'option -$OPTARG attend une valeur." >&2
            usage >&2
            exit 1
            ;;
        \?)
            echo "Erreur : option inconnue -$OPTARG" >&2
            usage >&2
            exit 1
            ;;
    esac
done
shift $((OPTIND - 1))

# --- Vérification de N : entier >= 1 ---
if ! [[ "$N" =~ ^[0-9]+$ ]] || (( 10#$N < 1 )); then
    echo "Erreur : N doit être un entier >= 1 (reçu : '$N')." >&2
    exit 1
fi

# --- Zéro ou un argument : FICHIER ---
if [[ $# -gt 1 ]]; then
    usage >&2
    exit 1
fi

FICHIER="${1:-$FICHIER_DEFAUT}"

if [[ ! -f "$FICHIER" || ! -r "$FICHIER" ]]; then
    echo "Erreur : fichier illisible : '$FICHIER'." >&2
    exit 2
fi

# --- Extraction, comptage, classement ---
# LC_ALL=C : tri alphabétique identique quelle que soit la langue du système.
export LC_ALL=C

grep -- 'Failed password' "$FICHIER" |
    awk '{
        ip = ""
        for (i = 1; i < NF; i++)
            if ($i == "from") ip = $(i + 1)   # garde le DERNIER "from"
        if (ip != "") print ip
    }' |
    sort |
    uniq -c |
    sort -k1,1nr -k2,2 |
    head -n "$N" |
    awk '{ print $1, $2 }'

exit 0
