"""Client Vigie : une session, une fonction d'appel (réutilisable en 3.3 et 3.4)."""

import logging
import time

import requests

API = "http://vigie.mistral.test:8080/api/v1"
log = logging.getLogger("enrichir")


def creer_session(jeton):
    """Session qui envoie le jeton à chaque appel."""
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {jeton}"
    return session


def appeler(session, url):
    """GET avec réessais sur 429/503 (6 essais au plus)."""
    for essai in range(1, 7):
        r = session.get(url, timeout=5)
        if r.status_code in (429, 503):
            attente = float(r.headers.get("Retry-After", 1))
            log.warning("essai %d : %d, attente %.1f s", essai, r.status_code, attente)
            time.sleep(attente)
            continue
        r.raise_for_status()
        return r.json()
    raise RuntimeError(f"abandon après 6 essais : {url}")
