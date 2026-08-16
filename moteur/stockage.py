"""Persistance des simulations dans une base SQLite embarquée."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path

CHEMIN_BASE = Path(__file__).resolve().parent.parent / "data" / "simulations.db"


def _connexion() -> sqlite3.Connection:
    CHEMIN_BASE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(CHEMIN_BASE)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS simulations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            horodatage TEXT NOT NULL,
            code_tarif TEXT NOT NULL,
            libelle TEXT NOT NULL,
            periode TEXT NOT NULL,
            energie_kwh REAL NOT NULL,
            montant_ht REAL NOT NULL,
            total_ttc REAL NOT NULL,
            details TEXT
        )
    """)
    return conn


def enregistrer(facture, commentaire: str = "") -> int:
    """Enregistre une facture simulée et retourne son identifiant."""
    details = json.dumps({
        "lignes": facture.lignes,
        "tco": facture.tco,
        "tva": facture.tva,
        "redevance": facture.redevance,
        "commentaire": commentaire,
    })
    with _connexion() as conn:
        curseur = conn.execute(
            "INSERT INTO simulations (horodatage, code_tarif, libelle, periode,"
            " energie_kwh, montant_ht, total_ttc, details)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (datetime.now().isoformat(timespec="seconds"), facture.code_tarif,
             facture.libelle, facture.periode, facture.energie_kwh,
             facture.montant_ht, facture.total_ttc, details),
        )
        return curseur.lastrowid


def lister() -> list:
    """Toutes les simulations enregistrées, de la plus récente à la plus ancienne."""
    with _connexion() as conn:
        conn.row_factory = sqlite3.Row
        lignes = conn.execute(
            "SELECT * FROM simulations ORDER BY horodatage DESC"
        ).fetchall()
    return [dict(l) for l in lignes]


def supprimer(identifiant: int) -> None:
    with _connexion() as conn:
        conn.execute("DELETE FROM simulations WHERE id = ?", (identifiant,))


def vider() -> None:
    with _connexion() as conn:
        conn.execute("DELETE FROM simulations")
