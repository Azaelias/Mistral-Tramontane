#!/usr/bin/env python3

import argparse
import json
import os
import sys
import requests
import vigie_client as vigie

parser = argparse.ArgumentParser(description="Tickets Vigie")
parser.add_argument("--rapport", required=True, type=__import__("pathlib").Path)
parser.add_argument("--seuil", type=int, default=80)
a = parser.parse_args()

jeton = os.environ.get("VIGIE_TOKEN")
if not jeton:
    print("Erreur : VIGIE_TOKEN absent", file=sys.stderr)
    sys.exit(3)

rapport = json.loads(a.rapport.read_text())

if isinstance(rapport, dict):
    rapport = rapport.get("adresses", rapport.get("resultats", []))

session = vigie.creer_session(jeton)

crees = 0
deja_ouverts = 0

for r in rapport:
    if r["score"] < a.seuil:
        continue

    ip = r["ip"]
    print(f"Vérification : {ip} (score {r['score']})")

    url = f"{vigie.API}/tickets?ip={ip}"
    tickets = vigie.appeler(session, url)["tickets"]

    if tickets:
        deja_ouverts += 1
        print(f"[DÉJÀ OUVERT] {ip}")
        continue

    import time

    for essai in range(1, 7):
        reponse = session.post(
            f"{vigie.API}/tickets",
            json={
                "ip": ip,
                "score": r["score"],
                "titre": f"Adresse malveillante {ip} (score {r['score']})"
            },
            timeout=5
        )

        if reponse.status_code in (429, 503):
            attente = float(reponse.headers.get("Retry-After", 1))
            print(f"[ATTENTE] HTTP {reponse.status_code}, {attente}s")
            time.sleep(attente)
            continue

        reponse.raise_for_status()
        crees += 1
        print(f"[CRÉÉ] {ip}")
        break
    else:
        raise RuntimeError(f"Abandon après 6 essais : {ip}")

print("\n========== RÉSUMÉ ==========")
print(f"Tickets créés : {crees}")
print(f"Déjà ouverts  : {deja_ouverts}")
print("============================")
