#!/usr/bin/env bash
set -euo pipefail

# Fichiers temporaires pour stocker les en-tetes et le corps HTTP
HEADER_FILE="$(mktemp)"
BODY_FILE="$(mktemp)"
trap 'rm -f "$HEADER_FILE" "$BODY_FILE"' EXIT

# 1. Extraction securisee du jeton VIGIE_TOKEN et de VIGIE_URL
VIGIE_TOKEN="${VIGIE_TOKEN:-}"
VIGIE_URL="${VIGIE_URL:-}"

if [[ -f /etc/mistral/vigie.env ]]; then
    if [[ -z "$VIGIE_TOKEN" ]]; then
        VIGIE_TOKEN="$(sed -n 's/^[[:space:]]*\(export[[:space:]]*\)\?VIGIE_TOKEN=['"'"'"]\?//; s/['"'"'"]\?[[:space:]\r]*$//p' /etc/mistral/vigie.env | tail -n 1 || true)"
    fi
    if [[ -z "$VIGIE_URL" ]]; then
        VIGIE_URL="$(sed -n 's/^[[:space:]]*\(export[[:space:]]*\)\?VIGIE_URL=['"'"'"]\?//; s/['"'"'"]\?[[:space:]\r]*$//p' /etc/mistral/vigie.env | tail -n 1 || true)"
    fi
fi

if [[ -z "$VIGIE_TOKEN" ]]; then
    echo "erreur: VIGIE_TOKEN introuvable" >&2
    exit 3
fi

VIGIE_URL="${VIGIE_URL:-http://127.0.0.1:5000}"

# 2 & 3. Fonction d-appel HTTP avec curl, lecture des en-tetes et retries
appel() {
    local url="$1"
    local attempt=1
    local max_attempts=6

    while true; do
        : > "$HEADER_FILE"
        : > "$BODY_FILE"

        local http_code
        http_code="$(curl -s -m 5 -D "$HEADER_FILE" -o "$BODY_FILE" -w '%{http_code}' \
            -H "Authorization: Bearer $VIGIE_TOKEN" \
            -H "X-Vigie-Token: $VIGIE_TOKEN" \
            "$url" || true)"

        case "$http_code" in
            200)
                return 0
                ;;
            401)
                echo "jeton refusé" >&2
                exit 3
                ;;
            429)
                local retry_after
                retry_after="$(grep -i '^Retry-After:' "$HEADER_FILE" | tr -d '\r' | awk '{print $2}' || true)"
                if [[ -z "$retry_after" || ! "$retry_after" =~ ^[0-9]+$ ]]; then
                    retry_after=1
                fi
                sleep "$retry_after"
                ;;
            503|000)
                if (( attempt >= max_attempts )); then
                    echo "Erreur HTTP ${http_code}" >&2
                    exit 1
                fi
                sleep "$attempt"
                (( attempt++ ))
                ;;
            *)
                if (( attempt >= max_attempts )); then
                    echo "Erreur HTTP ${http_code:-inconnu}" >&2
                    exit 1
                fi
                sleep "$attempt"
                (( attempt++ ))
                ;;
        esac
    done
}

# 4. Formatage JSON avec jq : affiche "<adresse> <score>"
format_json() {
    jq -r '
        if type == "array" then
            .[]
        elif type == "object" and .tickets then
            .tickets[]
        else
            .
        end
        | select((.ip // .adresse) != null)
        | "\(.ip // .adresse) \(.score // .reputation)"
    ' "$BODY_FILE"
}

# Analyse de la sous-commande
if [[ $# -lt 1 ]]; then
    echo "Usage: $0 {reputation IP|tickets|ticket-ip IP}" >&2
    exit 1
fi

COMMAND="$1"

case "$COMMAND" in
    reputation)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $0 reputation IP" >&2
            exit 1
        fi
        IP="$2"
        appel "${VIGIE_URL}/reputation/${IP}"
        format_json
        ;;
    tickets)
        appel "${VIGIE_URL}/tickets"
        format_json
        ;;
    ticket-ip)
        if [[ $# -lt 2 ]]; then
            echo "Usage: $0 ticket-ip IP" >&2
            exit 1
        fi
        IP="$2"
        appel "${VIGIE_URL}/tickets/${IP}"
        format_json
        ;;
    *)
        echo "Erreur: sous-commande $COMMAND inconnue" >&2
        exit 1
        ;;
esac
