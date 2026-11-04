#!/usr/bin/env bash
# comptes.sh : lanceur de comptes.py
#
# Usage : comptes.sh FICHIER_CSV DOSSIER
#
# Partage du travail :
#   - Bash (ce script) : vérifie les arguments, gère l'encodage,
#     choisit le bon Python, propage le code de sortie, écrit le journal.
#   - Python (comptes.py) : traite les données (nettoyage, logins, rejets).
#
# Codes de sortie :
#   2 : arguments invalides
#   sinon : le code de sortie de comptes.py

# Pas de "set -e" : on veut pouvoir journaliser l'échec de comptes.py
set -u

# --- Réglages --------------------------------------------------------------

# Dossier où se trouve ce script (comptes.py est à côté)
ICI="$(cd -- "$(dirname -- "$0")" && pwd)"
SCRIPT_PY="$ICI/comptes.py"
JOURNAL="/var/log/mistral/comptes.log"

usage() {
    echo "Usage : $(basename -- "$0") FICHIER_CSV DOSSIER" >&2
}

# --- 1. Vérification des arguments (code 2 si problème) -------------------

if [[ $# -ne 2 ]]; then
    usage
    exit 2
fi

CSV="$1"
DOSSIER="$2"

if [[ ! -f "$CSV" || ! -r "$CSV" ]]; then
    echo "Erreur : '$CSV' n'est pas un fichier lisible" >&2
    exit 2
fi

# On crée le dossier s'il n'existe pas (comme le fait comptes.py)
mkdir -p -- "$DOSSIER" 2>/dev/null
if [[ ! -d "$DOSSIER" || ! -w "$DOSSIER" ]]; then
    echo "Erreur : '$DOSSIER' n'est pas un dossier accessible en écriture" >&2
    exit 2
fi

# Fichier temporaire, effacé automatiquement à la sortie (même en cas d'erreur)
TMP="$(mktemp)" || exit 1
trap 'rm -f -- "$TMP"' EXIT

# --- 2. Détection de l'encodage --------------------------------------------

# Si la conversion utf-8 -> utf-8 réussit, le fichier est déjà en UTF-8 valide.
# Sinon, on le convertit depuis Latin-1 vers le fichier temporaire.
if iconv -f utf-8 -t utf-8 "$CSV" >/dev/null 2>&1; then
    ENCODAGE="utf8"
    ENTREE="$CSV"
else
    ENCODAGE="latin1"
    if ! iconv -f latin1 -t utf-8 "$CSV" > "$TMP"; then
        echo "Erreur : conversion Latin-1 -> UTF-8 impossible" >&2
        exit 1
    fi
    ENTREE="$TMP"
fi

# --- 3. Choix du Python et lancement ---------------------------------------

# Le venv peut être dans outils/ ou à la racine du projet ; sinon python3
PYTHON="python3"
for candidat in "$ICI/.venv/bin/python" "$ICI/../.venv/bin/python"; do
    if [[ -x "$candidat" ]]; then
        PYTHON="$candidat"
        break
    fi
done

"$PYTHON" "$SCRIPT_PY" --csv "$ENTREE" --sortie "$DOSSIER"
CODE=$?

# --- 4. Journal --------------------------------------------------------------

HORODATAGE="$(date '+%Y-%m-%d %H:%M:%S')"
mkdir -p -- "$(dirname -- "$JOURNAL")"

if [[ $CODE -ne 0 ]]; then
    echo "$HORODATAGE comptes.sh : ECHEC de comptes.py (code $CODE) sur $CSV" >> "$JOURNAL"
    echo "ECHEC de comptes.py (code $CODE) sur $CSV" >&2
    exit "$CODE"    # on propage le code de sortie de Python
fi

# wc -l compte les lignes ; on retire 1 pour l'en-tête de chaque fichier
CREES=$(( $(wc -l < "$DOSSIER/comptes.csv") - 1 ))
REJETEES=$(( $(wc -l < "$DOSSIER/rejets.csv") - 1 ))

echo "$HORODATAGE comptes.sh : $CREES comptes crees, $REJETEES lignes rejetees (encodage : $ENCODAGE)" >> "$JOURNAL"

exit 0
