#!/usr/bin/env python3
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

TELEGRAM_CONFIG = Path("/etc/mistral/telegram.env")
VIGIE_CONFIG = Path("/etc/mistral/vigie.env")
JOURNAUX = [
    Path("/var/log/mistral/auth.log"),
    Path("/var/log/mistral/sauvegarde.log"),
    Path("/var/log/mistral/vigie.log"),
]
DOSSIER_SAUVEGARDES = Path("/srv/sauvegardes")
ETAT = Path("/var/lib/mistral/surveillance-telegram.json")
API = "http://vigie.mistral.test:8080/api/v1"
INTERVALLE = 60


def lire_config(fichier):
    config = {}
    if not fichier.exists():
        return config
    for ligne in fichier.read_text().splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#"):
            continue
        if ligne.startswith("export "):
            ligne = ligne[7:].strip()
        if "=" in ligne:
            cle, valeur = ligne.split("=", 1)
            config[cle.strip()] = valeur.strip().strip("'\"")
    return config


def envoyer_telegram(message):
    config = lire_config(TELEGRAM_CONFIG)
    token = config.get("TELEGRAM_BOT_TOKEN")
    chat_id = config.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        raise RuntimeError("Configuration Telegram incomplète")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    donnees = urlencode({
        "chat_id": chat_id,
        "text": message
    }).encode()

    requete = Request(url, data=donnees, method="POST")
    with urlopen(requete, timeout=10) as reponse:
        resultat = json.loads(reponse.read().decode())
        if not resultat.get("ok"):
            raise RuntimeError("Telegram a refusé le message")


def charger_etat():
    ETAT.parent.mkdir(parents=True, exist_ok=True)
    try:
        return json.loads(ETAT.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"positions": {}, "vigie_en_panne": False,
                "sauvegarde_en_retard": False}


def enregistrer_etat(etat):
    temporaire = ETAT.with_suffix(".tmp")
    temporaire.write_text(json.dumps(etat, indent=2))
    os.replace(temporaire, ETAT)


def surveiller_journaux(etat):
    motifs = re.compile(
        r"\b(ERROR|CRITICAL|ERREUR|FATAL)\b|échec|echec|"
        r"Failed password|authentication failure|Invalid user",
        re.IGNORECASE
    )

    for fichier in JOURNAUX:
        if not fichier.exists():
            continue

        nom = str(fichier)
        position = etat["positions"].get(nom)

        with fichier.open("rb") as f:
            taille = f.seek(0, 2)
            if position is None:
                etat["positions"][nom] = taille
                continue
            if taille < position:
                position = 0
            f.seek(position)
            nouvelles = f.read().decode("utf-8", errors="replace")
            etat["positions"][nom] = f.tell()

        alertes = [
            ligne.strip() for ligne in nouvelles.splitlines()
            if motifs.search(ligne)
        ]

        if alertes:
            extrait = "\n".join(alertes[-8:])
            envoyer_telegram(
                f"⚠️ ALERTE MISTRAL\nJournal : {fichier.name}\n{extrait}"
            )


def verifier_sauvegarde(etat):
    archives = []
    if DOSSIER_SAUVEGARDES.exists():
        archives = [
            f for f in DOSSIER_SAUVEGARDES.iterdir()
            if f.is_file() and (
                f.name.endswith(".tar.gz") or f.name.endswith(".tgz")
            )
        ]

    derniere = max(archives, key=lambda f: f.stat().st_mtime, default=None)
    retard = derniere is None or (time.time() - derniere.stat().st_mtime > 26 * 3600)

    if retard and not etat["sauvegarde_en_retard"]:
        envoyer_telegram(
            "⚠️ ALERTE MISTRAL : aucune sauvegarde récente détectée "
            "(seuil : 26 heures)."
        )
    elif not retard and etat["sauvegarde_en_retard"]:
        envoyer_telegram("✅ MISTRAL : une sauvegarde récente est disponible.")

    etat["sauvegarde_en_retard"] = retard


def verifier_vigie(etat):
    config = lire_config(VIGIE_CONFIG)
    token = config.get("VIGIE_TOKEN")

    if not token:
        raise RuntimeError("VIGIE_TOKEN absent de la configuration")

    url = API + "/incidents?" + urlencode({
        "page": 1, "par_page": 1
    })
    requete = Request(url, headers={
        "Authorization": f"Bearer {token}"
    })

    try:
        with urlopen(requete, timeout=8):
            if etat["vigie_en_panne"]:
                envoyer_telegram("✅ MISTRAL : l'API Vigie est de nouveau disponible.")
            etat["vigie_en_panne"] = False
    except Exception as erreur:
        if not etat["vigie_en_panne"]:
            envoyer_telegram(
                f"🚨 ALERTE MISTRAL : API Vigie indisponible.\n{erreur}"
            )
        etat["vigie_en_panne"] = True


def main():
    etat = charger_etat()

    try:
        envoyer_telegram("✅ Surveillance Telegram Mistral démarrée.")
    except Exception as erreur:
        print(f"Erreur Telegram : {erreur}", file=sys.stderr)
        return 1

    print("Surveillance Mistral démarrée. Arrêt : Ctrl+C")

    while True:
        try:
            surveiller_journaux(etat)
            verifier_sauvegarde(etat)
            verifier_vigie(etat)
            enregistrer_etat(etat)
        except Exception as erreur:
            print(f"Erreur de surveillance : {erreur}", file=sys.stderr)

        time.sleep(INTERVALLE)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nSurveillance arrêtée.")
