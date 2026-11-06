#!/usr/bin/env bash
# veille.sh : enchaîne top-attaquants -> enrichir -> tickets.
# Lancé par cron toutes les 2 minutes. Se protège avec flock.
set -euo pipefail

# Cron ne connaît presque rien : on pose tout nous-mêmes.
export PATH=/usr/local/bin:/usr/bin:/bin
export LC_ALL=C

OUTILS=/guilde/outils
JOURNAL=/var/log/mistral/auth.log
SORTIE=/tmp/veille
SEUIL=80
VERROU=/var/lock/veille.lock
ENV_FILE=/etc/mistral/vigie.env

log() { printf '%s veille: %s\n' "$(date '+%F %T')" "$*"; }

# Verrou : si une veille tourne encore, on sort tout de suite, sans erreur.
exec 9>"$VERROU"
flock -n 9 || exit 0

# Le jeton vient uniquement du fichier protégé, jamais de la crontab.
if [[ ! -r "$ENV_FILE" ]]; then
    log "ERREUR $ENV_FILE illisible"
    exit 1
fi
set -a
# shellcheck source=/dev/null
. "$ENV_FILE"
set +a

mkdir -p "$SORTIE"
cd "$OUTILS"

log "début"

# Étape 1 : toutes les adresses en échec (pas seulement le top 5).
"$OUTILS/top-attaquants.sh" -n 1000000 "$JOURNAL" > "$SORTIE/adresses.txt"
nb=$(wc -l < "$SORTIE/adresses.txt")
log "étape 1 : $nb adresses en échec"

# Étape 2 : réputation de chaque adresse.
if (( nb > 0 )); then
    /usr/bin/python3 "$OUTILS/enrichir.py" --entree "$SORTIE/adresses.txt" --sortie "$SORTIE"
    log "étape 2 : réputation calculée"

    # Étape 3 : un ticket pour chaque score >= seuil (sans doublon).
    /usr/bin/python3 "$OUTILS/tickets.py" --rapport "$SORTIE/rapport.json" --seuil "$SEUIL"
    log "étape 3 : tickets traités (seuil $SEUIL)"
else
    log "aucune adresse en échec, rien à faire"
fi

log "fin"
