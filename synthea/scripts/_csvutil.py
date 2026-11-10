"""Utilitaires communs aux generateurs de lexiques SYNTHEA."""
from __future__ import annotations

import csv
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEX = os.path.join(ROOT, "data", "lexicons")

LEX_HEADER = [
    "terme_fr", "registre", "definition_fr",
    "en", "es", "pt", "ht",
    "secteur", "metiers",
]


def ensure_dir() -> None:
    os.makedirs(LEX, exist_ok=True)


def write_csv(name: str, header: list[str], rows: list[tuple | list]) -> str:
    ensure_dir()
    path = os.path.join(LEX, name)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, quoting=csv.QUOTE_MINIMAL)
        w.writerow(header)
        for r in rows:
            w.writerow(list(r))
    print(f"  + {name:46s} {len(rows):5d} lignes")
    return path


def write_sector(name: str, secteur: str, metiers: str, terms: list[tuple]) -> str:
    """terms = (terme_fr, registre, definition_fr, en, es, pt, ht)"""
    rows = [list(t) + [secteur, metiers] for t in terms]
    return write_csv(name, LEX_HEADER, rows)
