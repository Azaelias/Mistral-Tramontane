#!/usr/bin/env python3

import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

CONFIG = Path("/etc/mistral/telegram.env")
JOURNAL = Path("/var/log/mistral/alertes.log")


def lire_config():
    config = {}
    with CONFIG.open(encoding="utf-8") as fichier:
        for ligne in fichier:
            if "=" in ligne:
                cle, valeur = ligne.strip().split("=", 1)
                config[cle] = valeur
    return config


def notifier(message):
    config = lire_config()
    token = config["TELEGRAM_BOT_TOKEN"]
    chat_id = config["TELEGRAM_CHAT_ID"]

    JOURNAL.parent.mkdir(parents=True, exist_ok=True)
    horodatage = datetime.now().astimezone().isoformat(timespec="seconds")

    with JOURNAL.open("a", encoding="utf-8") as fichier:
        fichier.write(f"[{horodatage}] {message}\n")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    donnees = json.dumps({
        "chat_id": chat_id,
        "text": message
    }).encode("utf-8")

    requete = urllib.request.Request(
        url,
        data=donnees,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    with urllib.request.urlopen(requete, timeout=10) as reponse:
        resultat = json.load(reponse)

    if not resultat.get("ok"):
        raise RuntimeError("Telegram a refusé le message")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : telegram_notify.py MESSAGE", file=sys.stderr)
        sys.exit(2)

    message = " ".join(sys.argv[1:])

    try:
        notifier(message)
        print("Notification Telegram envoyée.")
    except Exception as erreur:
        print(f"Erreur notification Telegram : {erreur}", file=sys.stderr)
        sys.exit(1)
