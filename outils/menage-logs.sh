#!/usr/bin/env bash
# menage-logs.sh : compresse avec gzip les fichiers .log d'un dossier
# modifiés il y a JOURS jours ou plus (2 par défaut).
#
# Usage : menage-logs.sh [-n] [-j JOURS] DOSSIER
#   -n        simulation : affiche ce qui serait fait sans rien toucher
#   -j JOURS  âge minimal en jours (entier >= 1, défaut : 2)
#
# Codes de sortie :
#   0 : succès (y compris s'il n'y a rien à faire)
#   1 : erreur d'utilisation (option inconnue, argument manquant...)
#   2 : DOSSIER n'est pas un dossier
#   3 : au moins une compression a échoué

set -u

usage() {
    cat <<EOF
Usage : $(basename "$0") [-n] [-j JOURS] DOSSIER
  Compresse avec gzip les fichiers .log de DOSSIER modifiés
  il y a JOURS jours ou plus (2 par défaut).
  -n        simulation : affiche ce qui serait fait sans rien modifier
  -j JOURS  âge minimal en jours (entier >= 1)
EOF
}

SIMULATION=0
JOURS=2

# --- Lecture des options ---
while getopts ":nj:" opt; do
    case "$opt" in
        n) SIMULATION=1 ;;
        j) JOURS="$OPTARG" ;;
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

# --- Vérification de JOURS : entier >= 1 ---
if ! [[ "$JOURS" =~ ^[0-9]+$ ]] || (( JOURS < 1 )); then
    echo "Erreur : JOURS doit être un entier >= 1 (reçu : '$JOURS')." >&2
    exit 1
fi

# --- Un seul argument : DOSSIER ---
if [[ $# -ne 1 ]]; then
    usage >&2
    exit 1
fi

DOSSIER="$1"

if [[ ! -d "$DOSSIER" ]]; then
    echo "Erreur : '$DOSSIER' n'est pas un dossier." >&2
    exit 2
fi

# --- Boucle sûre (espaces, caractères spéciaux) ---
# Substitution de processus < <(...) plutôt qu'un pipe : la boucle reste
# dans le shell courant, donc les compteurs restent visibles après la boucle.
nb=0
erreurs=0

while IFS= read -r -d '' f; do
    if [[ "$SIMULATION" -eq 1 ]]; then
        echo "a compresser : $f"
        nb=$((nb + 1))
    else
        # Ne jamais écraser une archive existante
        if [[ -e "$f.gz" ]]; then
            echo "ignore (existe deja) : $f.gz" >&2
            erreurs=$((erreurs + 1))
            continue
        fi
        if gzip -- "$f"; then
            echo "compresse : $f.gz"
            nb=$((nb + 1))
        else
            echo "echec : $f" >&2
            erreurs=$((erreurs + 1))
        fi
    fi
done < <(find "$DOSSIER" -maxdepth 1 -type f -name '*.log' \
              -mtime +"$((JOURS - 1))" -print0)

if [[ "$nb" -eq 0 && "$erreurs" -eq 0 ]]; then
    echo "rien a faire"
fi

if [[ "$erreurs" -gt 0 ]]; then
    exit 3
fi

exit 0
