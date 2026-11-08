#!/usr/bin/env bash
# vigie.sh : interroge l'API Vigie avec curl et jq (aucun Python requis).
#
# Usage :
#   vigie.sh reputation IP    affiche "IP score"
#   vigie.sh tickets          affiche une ligne "IP score" par ticket
#   vigie.sh ticket-ip IP     affiche les tickets liés à cette IP
#
# Codes de sortie :
#   0 succès | 1 échec réseau/serveur après 6 essais
#   2 mauvais usage ou IP invalide | 3 jeton absent ou refusé

# -e : stop à la première erreur ; -u : variable non définie = erreur ;
# pipefail : un pipeline échoue si n'importe laquelle de ses commandes échoue.
set -euo pipefail

# --- Configuration -----------------------------------------------------------
API="http://vigie.mistral.test:8080/api/v1"
ENV_FILE="/etc/mistral/vigie.env"   # fichier protégé contenant VIGIE_TOKEN=...

# --- Lecture du jeton --------------------------------------------------------
# Priorité à la variable d'environnement. À défaut, on lit le fichier protégé
# avec sed (on ne le "source" pas : on n'exécute pas son contenu).
# "|| true" évite que set -e n'arrête le script si le fichier est illisible ;
# on traite ce cas juste après. Le jeton n'est jamais affiché.
if [[ -z "${VIGIE_TOKEN:-}" ]]; then
    VIGIE_TOKEN="$(sed -n 's/^VIGIE_TOKEN=//p' "$ENV_FILE" 2>/dev/null || true)"
fi
if [[ -z "${VIGIE_TOKEN:-}" ]]; then
    echo "erreur : aucun jeton Vigie disponible" >&2
    exit 3
fi

# --- Fonctions utilitaires ---------------------------------------------------

# Affiche l'aide sur stderr et sort avec le code 2 (mauvais usage).
usage() {
    echo "usage : $0 reputation IP | tickets | ticket-ip IP" >&2
    exit 2
}

# Vérifie qu'un argument ressemble à une adresse IPv4 (4 groupes de chiffres).
# Cela évite d'injecter n'importe quel texte dans l'URL.
verifier_ip() {
    [[ $1 =~ ^[0-9]{1,3}(\.[0-9]{1,3}){3}$ ]] || {
        echo "erreur : adresse IP invalide" >&2
        exit 2
    }
}

# appel CHEMIN : interroge l'API et affiche le corps JSON sur stdout si HTTP 200.
# Gère les erreurs selon le code HTTP, pas selon le code de sortie de curl
# (curl renvoie 0 même sur une réponse 500).
appel() {
    local chemin=$1 entetes corps code attente essai

    # Deux fichiers temporaires : un pour les en-têtes (utile pour Retry-After),
    # un pour le corps de la réponse.
    entetes=$(mktemp)
    corps=$(mktemp)
    # Supprime les fichiers temporaires quand la fonction se termine.
    # shellcheck disable=SC2064
    trap "rm -f '$entetes' '$corps'" RETURN

    # Jusqu'à 6 essais au total.
    for essai in 1 2 3 4 5 6; do
        # -s : silencieux ; -m 5 : abandon après 5 s ; -D : en-têtes dans un fichier ;
        # -o : corps dans un fichier ; -w : n'affiche que le code HTTP.
        # Si curl échoue (réseau coupé, délai dépassé), on force le code 000.
        code=$(curl -s -m 5 -D "$entetes" -o "$corps" -w '%{http_code}' \
            -H "Authorization: Bearer $VIGIE_TOKEN" \
            "$API$chemin" || echo 000)

        case "$code" in
            200)
                # Succès : on transmet le corps et on quitte la fonction.
                cat "$corps"
                return 0
                ;;
            401)
                # Jeton refusé : inutile de réessayer.
                echo "erreur : jeton refusé" >&2
                exit 3
                ;;
            429)
                # Trop de requêtes : le serveur indique combien de secondes
                # attendre dans l'en-tête Retry-After. Sans valeur, on attend 1 s.
                attente=$(sed -n 's/^[Rr]etry-[Aa]fter: *\([0-9]*\).*/\1/p' "$entetes" | head -n 1)
                sleep "${attente:-1}"
                ;;
            *)
                # 503 ou autre erreur : attente croissante (1 s, 2 s, 3 s...).
                sleep "$essai"
                ;;
        esac
    done

    # Les 6 essais ont échoué.
    echo "erreur : échec après 6 essais (dernier code HTTP $code)" >&2
    exit 1
}

# --- Programme principal -----------------------------------------------------

# Il faut au moins une sous-commande.
[[ $# -ge 1 ]] || usage

case "$1" in
    reputation)
        # Réputation d'une IP : l'API renvoie un objet avec "ip" et "score".
        # jq -r produit du texte brut, une ligne "adresse score".
        [[ $# -eq 2 ]] || usage
        verifier_ip "$2"
        appel "/reputation/$2" | jq -r '"\(.ip) \(.score)"'
        ;;
    tickets)
        # Liste de tous les tickets : l'API renvoie {"tickets": [...]}.
        # .tickets[] parcourt le tableau, une ligne par ticket.
        # Hypothèse : chaque ticket a les champs "ip" et "score".
        [[ $# -eq 1 ]] || usage
        appel "/tickets" | jq -r '.tickets[] | "\(.ip) \(.score)"'
        ;;
    ticket-ip)
        # Tickets d'une IP donnée : filtre côté serveur via ?ip=...
        # (le chemin /tickets/ip/IP n'existe pas : il renvoie 404).
        [[ $# -eq 2 ]] || usage
        verifier_ip "$2"
        appel "/tickets?ip=$2" | jq -r '.tickets[] | "\(.ip) \(.score)"'
        ;;
    *)
        usage
        ;;
esac
