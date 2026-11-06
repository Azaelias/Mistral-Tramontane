#!/bin/bash
set -euo pipefail

# 1. Vérification de la présence d'Ansible
if ! command -v ansible-playbook >/dev/null 2>&1; then
    echo "Erreur : ansible-playbook n'est pas installé sur ce serveur." >&2
    exit 1
fi

# 2. Récupération du dossier absolu où se trouve installer.sh
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 3. Exécution du playbook Ansible en local
ansible-playbook -i "localhost," -c local "${SCRIPT_DIR}/outils/playbook.yml"
