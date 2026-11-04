#!/usr/bin/env python3
"""
tickets.py - Outil de création et d'envoi de tickets vers l'API Vigie.
Contient la gestion de configuration, le mode simulation (Annexe E4) 
et le backoff exponentiel avec jitter (Annexe E2).
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request


def obtenir_config():
    """
    Charge VIGIE_TOKEN et VIGIE_URL depuis les variables d'environnement
    ou depuis le fichier /etc/mistral/vigie.env.
    """
    token = os.environ.get("VIGIE_TOKEN")
    url = os.environ.get("VIGIE_URL")

    # Parsing du fichier de configuration du lab si présent
    env_path = "/etc/mistral/vigie.env"
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("VIGIE_TOKEN=") and not token:
                    token = line.split("=", 1)[1].strip("'\"\r ")
                elif line.startswith("VIGIE_URL=") and not url:
                    url = line.split("=", 1)[1].strip("'\"\r ")

    # Si aucun jeton n'est trouvé : arrêt net avec message et code de sortie 3
    if not token:
        sys.stderr.write("erreur: VIGIE_TOKEN introuvable\n")
        sys.exit(3)

    # URL par défaut de l'API Vigie
    if not url:
        url = "http://vigie.mistral.test:8080/api/v1"

    return token, url.rstrip("/")


def appeler_api_post(url, token, payload):
    """
    Envoie une requête POST JSON à l'API Vigie.
    Gère le rejet 401 immédiat (code 3) et l'attente croissante (Annexe E2).
    """
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "X-Vigie-Token": token,
        },
        method="POST",
    )

    max_retries = 5
    attempt = 1

    while True:
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                content = resp.read().decode("utf-8")
                return json.loads(content) if content else {}

        except urllib.error.HTTPError as e:
            # =========================================================================
            # GESTION DES ERREURS HTTP
            # =========================================================================

            # 1. Jetons invalides / refusés -> Arrêt immédiat (code 3) sans retentative
            if e.code == 401:
                sys.stderr.write("jeton refusé\n")
                sys.exit(3)

            # 2. Limitation de débit 429
            elif e.code == 429:
                retry_after = e.headers.get("Retry-After")
                if retry_after and retry_after.isdigit():
                    delay = int(retry_after)
                    sys.stderr.write(f"Erreur 429: attente Retry-After de {delay}s...\n")
                else:
                    # =====================================================================
                    # [ANNEXE E2] Backoff exponentiel : 2^(essai-1) + Jitter (hasard)
                    # =====================================================================
                    base_delay = 2 ** (attempt - 1)
                    jitter = random.uniform(0.1, 0.5)
                    delay = round(base_delay + jitter, 2)
                    sys.stderr.write(f"Erreur 429: attente de {delay}s (essai {attempt})...\n")
                    attempt += 1
                time.sleep(delay)

            # 3. Serveur en panne (500, 503, etc.)
            else:
                if attempt > max_retries:
                    sys.stderr.write(f"Erreur HTTP {e.code}\n")
                    sys.exit(1)

                # =====================================================================
                # [ANNEXE E2] Attente croissante (1s, 2s, 4s, 8s...) + Hasard
                # =====================================================================
                base_delay = 2 ** (attempt - 1)        # Ex: 1s, 2s, 4s, 8s...
                jitter = random.uniform(0.1, 0.5)      # Petit aléatoire anti-collision
                delay = round(base_delay + jitter, 2)

                # Affichage explicite des attentes croissantes dans le journal stderr
                sys.stderr.write(
                    f"Vigie en panne ({e.code}): attente de {delay}s (essai {attempt})...\n"
                )
                time.sleep(delay)
                attempt += 1

        except urllib.error.URLError as e:
            # 4. Connexion au serveur impossible (Serveur tombé / Panne réseau)
            if attempt > max_retries:
                sys.stderr.write(f"Erreur connexion API: {e}\n")
                sys.exit(1)

            # =====================================================================
            # [ANNEXE E2] Backoff exponentiel sur panne réseau
            # =====================================================================
            base_delay = 2 ** (attempt - 1)
            jitter = random.uniform(0.1, 0.5)
            delay = round(base_delay + jitter, 2)

            sys.stderr.write(
                f"Vigie inaccessible: attente de {delay}s (essai {attempt})...\n"
            )
            time.sleep(delay)
            attempt += 1


def charger_rapport(chemin):
    """
    Lit le fichier de rapport JSON et extrait la liste des tickets.
    """
    if not os.path.exists(chemin):
        sys.stderr.write(f"Erreur: rapport {chemin} introuvable\n")
        sys.exit(1)

    try:
        with open(chemin, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        sys.stderr.write(f"Erreur lecture JSON {chemin}: {e}\n")
        sys.exit(1)

    # Normalisation du format (liste directe ou sous-clé dict)
    if isinstance(data, list):
        return data
    elif isinstance(data, dict):
        if "tickets" in data and isinstance(data["tickets"], list):
            return data["tickets"]
        elif "incidents" in data and isinstance(data["incidents"], list):
            return data["incidents"]
        elif "alertes" in data and isinstance(data["alertes"], list):
            return data["alertes"]
        else:
            return [data]
    return []


def main():
    parser = argparse.ArgumentParser(
        description="Génération et création de tickets sur l'API Vigie"
    )
    parser.add_argument(
        "--rapport", required=True, help="Fichier JSON du rapport d'incident"
    )

    # =========================================================================
    # [ANNEXE E4] Définition du paramètre --simulation
    # =========================================================================
    parser.add_argument(
        "--simulation",
        action="store_true",
        help="Affiche la liste des tickets à créer sans envoyer de requêtes à Vigie",
    )
    args = parser.parse_args()

    token, base_url = obtenir_config()
    tickets = charger_rapport(args.rapport)

    # =========================================================================
    # [ANNEXE E4] Traitement du mode simulation
    # Si --simulation est spécifié :
    # 1. On affiche la liste des tickets préparés.
    # 2. On interrompt le script SANS passer d'appel HTTP POST à l'API.
    # Ainsi, le nombre de tickets enregistrés sur Vigie ne bouge pas.
    # =========================================================================
    if args.simulation:
        print(f"[SIMULATION] {len(tickets)} ticket(s) prêt(s) à être créé(s) :")
        print(json.dumps(tickets, indent=2, ensure_ascii=False))
        return 0

    # Mode production : envoi réel des tickets via l'API
    resultats = []
    for ticket in tickets:
        res = appeler_api_post(f"{base_url}/tickets", token, ticket)
        resultats.append(res)

    print(json.dumps(resultats, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
