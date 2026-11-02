#!/usr/bin/env bash
set -euo pipefail

usage() {
    echo "usage: $0 SOURCE [DESTINATION]" >&2
    exit 1
}

# 1. Contrôle du nombre d'arguments
[[ $# -ge 1 ]] || usage

# 2. Récupération des arguments et nettoyage du slash final
SOURCE="${1%/}"
DEST="${2:-/srv/sauvegardes}"

# 3. Vérification de l'existence du dossier source
if [[ ! -d "$SOURCE" ]]; then
    echo "erreur: $SOURCE n'est pas un dossier" >&2
    exit 2
fi

# 4. Calcul des noms et de l'horodatage
NOM="$(basename "$SOURCE")"
HORODATE="$(date +%Y%m%d-%H%M%S)"
ARCHIVE="$DEST/$NOM-$HORODATE.tar.gz"

# 5. Création du dossier destination s'il n'existe pas
mkdir -p "$DEST"

# 6. Archivage tar.gz à partir du dossier parent
tar -czf "$ARCHIVE" -C "$(dirname "$SOURCE")" "$NOM"

echo "Sauvegarde réussie : $ARCHIVE"
