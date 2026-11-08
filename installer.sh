#!/bin/bash
set -euo pipefail

# Couleurs pour les logs
GREEN="\033[0;32m"
RED="\033[0;31m"
NC="\033[0m" # No Color

echo -e "${GREEN}[*] Début du déploiement du kit de veille - Opération Mistral${NC}"

# 1. Vérification des privilèges root (recommandé pour Ansible et la crontab système)
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[erreur] Ce script doit être exécuté en tant que root.${NC}" >&2
  exit 1
fi

# 2. Vérification de la présence d'Ansible
if ! command -v ansible-playbook &> /dev/null; then
  echo -e "${RED}[erreur] Ansible n'est pas installé. Veuillez l'installer avant de continuer.${NC}" >&2
  exit 1
fi

# 3. Sécurisation des permissions des dossiers et scripts
echo -e "${GREEN}[*] Sécurisation des permissions des scripts...${NC}"
find /guilde/scripts -type f -name "*.sh" -exec chmod 750 {} +

# 4. Exécution du playbook Ansible de manière idempotente
PLAYBOOK_PATH="/guilde/deploiement/playbook.yml"

if [ ! -f "$PLAYBOOK_PATH" ]; then
  echo -e "${RED}[erreur] Playbook introuvable à l'emplacement : $PLAYBOOK_PATH${NC}" >&2
  exit 1
fi

echo -e "${GREEN}[*] Application du playbook Ansible (idempotence garantie)...${NC}"
ansible-playbook "$PLAYBOOK_PATH"

echo -e "${GREEN}[✔] Déploiement terminé avec succès ! Le kit est opérationnel.${NC}"
