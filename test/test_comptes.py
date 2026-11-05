"""Tests de la fonction de nettoyage normaliser() de comptes.py.

Lancer depuis /guilde :  .venv/bin/pytest -q
"""

import os
import sys

# comptes.py est dans ../outils : on ajoute ce dossier au chemin de recherche.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "outils"))

from comptes import normaliser  # noqa: E402


def test_accents():
    # Les lettres accentuées perdent leur accent
    assert normaliser("Anaïs") == "anais"
    assert normaliser("Hélène") == "helene"
    assert normaliser("Zoé") == "zoe"


def test_apostrophe():
    # L'apostrophe disparaît, qu'elle soit droite (') ou typographique (’)
    assert normaliser("N'Diaye") == "ndiaye"
    assert normaliser("O'Neil") == "oneil"
    assert normaliser("O’Neil") == "oneil"


def test_tiret():
    # Le tiret est conservé
    assert normaliser("Jean-Baptiste") == "jean-baptiste"


def test_espaces():
    # Les espaces disparaissent : au milieu, au début et à la fin
    assert normaliser("De La Fontaine") == "delafontaine"
    assert normaliser("  Emma ") == "emma"


def test_majuscules():
    # Tout passe en minuscules
    assert normaliser("GARCIA") == "garcia"
    assert normaliser("McDonald") == "mcdonald"


def test_cedille():
    # Le ç devient c
    assert normaliser("Garçon") == "garcon"
    assert normaliser("François") == "francois"
