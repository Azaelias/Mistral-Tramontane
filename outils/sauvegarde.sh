#!/usr/bin/env bash
set -euo pipefail

GARDER=7

usage() {
    echo "usage: $0 [-k N] SOURCE [DESTINATION]" >&2
    exit 1
}

# Analyse des options courtes (-k et -h)
while getopts ":k:h" opt; do
    case "$opt" in
        k) GARDER="$OPTARG" ;;
        h) usage ;;
        *) usage ;;
    esac
done
shift $((OPTIND - 1))

# Contrôle des arguments obligatoires
if [[ $# -lt 1 ]]; then
    usage
fi

SOURCE="${1%/}"
DEST="${2:-/srv/sauvegardes}"

# Validation du dossier source
if [[ ! -d "$SOURCE" ]]; then
    echo "erreur: $SOURCE n'est pas un dossier" >&2
    exit 2
fi

# Fonction de journalisation horodatée ISO-8601
log() {
    local msg="$1"
    local horodate
    horodate="$(date +%Y-%m-%dT%H:%M:%S)"
    mkdir -p /var/log/mistral
    printf "[%s] %s\n" "$horodate" "$msg" | tee -a /var/log/mistral/sauvegarde.log
}

mkdir -p "$DEST"

NOM="$(basename "$SOURCE")"
HORODATE="$(date +%Y%m%d-%H%M%S)"
ARCHIVE_FINALE="$DEST/$NOM-$HORODATE.tar.gz"
ARCHIVE_PART="$ARCHIVE_FINALE.part"

# Sécurité : suppression du fichier .part si le script s'interrompt ou échoue
trap 'rm -f "$ARCHIVE_PART"' EXIT

log "Début de la sauvegarde de $SOURCE vers $ARCHIVE_FINALE"

# Création dans un fichier temporaire puis renommage atomique
tar -czf "$ARCHIVE_PART" -C "$(dirname "$SOURCE")" "$NOM"
mv "$ARCHIVE_PART" "$ARCHIVE_FINALE"

log "Archive créée : $ARCHIVE_FINALE"

# Rotation : isole les archives au-delà des K plus récentes
mapfile -t ANCIENNES < <(find "$DEST" -maxdepth 1 -type f -name "$NOM-*.tar.gz" | sort -r | tail -n +"$((GARDER + 1))")

if [[ ${#ANCIENNES[@]} -gt 0 ]]; then
    for archive in "${ANCIENNES[@]}"; do
        if [[ -n "$archive" ]]; then
            rm -f -- "$archive"
            log "rotation: $archive supprimee"
        fi
    done
fi

exit 0
