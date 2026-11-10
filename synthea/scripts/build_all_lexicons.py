"""SYNTHEA - Reconstruit l integralite des CSV de lexiques.

Usage :  python scripts/build_all_lexicons.py
Les CSV sont deja livres dans data/lexicons/ ; ce script permet de les
regenerer ou de les enrichir (ajoute tes termes dans les listes des
modules build_0*.py puis relance).
"""
from __future__ import annotations

import os
import runpy
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

MODULES = [
    "build_01_metiers.py",
    "build_02_lexiques_a.py",
    "build_03_lexiques_b.py",
    "build_04_lexiques_c.py",
    "build_05_langue_contextes.py",
]

if __name__ == "__main__":
    for m in MODULES:
        runpy.run_path(os.path.join(HERE, m), run_name="__main__")
    lex = os.path.join(os.path.dirname(HERE), "data", "lexicons")
    files = sorted(f for f in os.listdir(lex) if f.endswith(".csv"))
    total = 0
    for f in files:
        with open(os.path.join(lex, f), encoding="utf-8") as fh:
            total += sum(1 for _ in fh) - 1
    print(f"\n[SYNTHEA] {len(files)} fichiers CSV, {total} lignes de vocabulaire au total.")
