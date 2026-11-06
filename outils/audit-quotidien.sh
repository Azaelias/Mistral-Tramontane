#!/usr/bin/env bash
# audit-quotidien.sh [AAAA-MM-JJ]
# Lance l'audit du parc et tient l'historique des postes non conformes.
set -euo pipefail

HISTORIQUE=/var/lib/mistral/audit/historique.csv
FICHIER=/srv/mistral/parc/postes.json
SORTIE=/tmp/audit-sortie
AUDIT=/guilde/outils/Audit-Parc.ps1

date_audit="${1:-$(date +%F)}"

# 1. Validation du format ET de l'existence réelle de la date
if [[ ! "$date_audit" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] \
   || ! date -d "$date_audit" +%F >/dev/null 2>&1 \
   || [[ "$(date -d "$date_audit" +%F)" != "$date_audit" ]]; then
    echo "Date invalide : '$date_audit' (attendu AAAA-MM-JJ)" >&2
    exit 2
fi

# 2. Lancement de l'audit : set -e propage l'échec
mkdir -p "$SORTIE" "$(dirname "$HISTORIQUE")"
pwsh -NoProfile -File "$AUDIT" -Fichier "$FICHIER" -Sortie "$SORTIE" -Date "$date_audit"

# 3. Nombre de non-conformes (lignes du CSV moins l'en-tête)
total=$(( $(wc -l < "$SORTIE/non-conformes.csv") - 1 ))

# 4. Historique : en-tête si absent, puis remplacement de la ligne du jour
[[ -f "$HISTORIQUE" ]] || echo "date;non_conformes" > "$HISTORIQUE"
tmp=$(mktemp)
grep -v "^${date_audit};" "$HISTORIQUE" > "$tmp" || true
echo "${date_audit};${total}" >> "$tmp"
{ head -n 1 "$tmp"; tail -n +2 "$tmp" | sort; } > "$HISTORIQUE"
rm -f "$tmp"

# 5. Écart avec la ligne précédente (la date juste avant dans l'historique)
precedent=$(awk -F';' -v d="$date_audit" 'NR>1 && $1<d {v=$2} END {print v}' "$HISTORIQUE")

if [[ -z "$precedent" ]]; then
    echo "${date_audit} : ${total} postes non conformes (premier relevé, pas de comparaison)."
else
    ecart=$(( total - precedent ))
    if (( ecart > 0 )); then
        echo "${date_audit} : ${total} postes non conformes, soit ${ecart} de plus que la veille (${precedent})."
    elif (( ecart < 0 )); then
        echo "${date_audit} : ${total} postes non conformes, soit $(( -ecart )) de moins que la veille (${precedent})."
    else
        echo "${date_audit} : ${total} postes non conformes, inchangé depuis le relevé précédent (${precedent})."
    fi
fi
