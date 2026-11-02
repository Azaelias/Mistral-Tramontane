#!/usr/bin/env bash
set -euo pipefail
usage() {
 echo "usage : $0 [-k N] SOURCE [DESTINATION]" >&2
 exit 1
}
[[ $# -ge 1 ]] || usage
SOURCE="${1%/}"
DEST="${2:-/srv/sauvegardes}"
