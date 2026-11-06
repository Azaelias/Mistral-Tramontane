#!/usr/bin/env bash
# installer-cron.sh : installe les deux lignes cron, sans doublon.
set -euo pipefail

VEILLE=/guilde/outils/veille.sh
SAUVEGARDE=/guilde/outils/sauvegarde.sh

L1="*/5 * * * * $VEILLE >> /var/log/mistral/veille.log 2>&1"
L2="30 2 * * * $SAUVEGARDE /srv/mistral/partage >> /var/log/mistral/sauvegarde-cron.log 2>&1"

mkdir -p /var/log/mistral

{
    # On retire d'abord d'éventuelles anciennes versions de nos deux lignes.
    crontab -l 2>/dev/null | grep -v -e "$VEILLE" -e "$SAUVEGARDE" || true
    echo "$L1"
    echo "$L2"
} | crontab -

echo "crontab installée :"
crontab -l
