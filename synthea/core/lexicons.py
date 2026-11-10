"""SYNTHEA - chargement et interrogation des lexiques CSV.

Toute la connaissance hors ligne de la plateforme vit ici : 57 fichiers CSV
(metiers, lexiques sectoriels, jargon familier, sigles, formules par contexte,
stopwords, contextes de restitution, sources de veille, pays).
"""
from __future__ import annotations

import csv
import functools
import os

from . import utils

LANGS = ["fr", "en", "es", "pt", "ht"]
LANG_LABELS = {
    "fr": "Francais",
    "en": "English",
    "es": "Espanol",
    "pt": "Portugues",
    "ht": "Kreyol ayisyen",
}


# --------------------------------------------------------------- lecture
def _read(name: str) -> list[dict]:
    path = os.path.join(utils.LEXICONS, name)
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as fh:
        return [dict(r) for r in csv.DictReader(fh)]


@functools.lru_cache(maxsize=1)
def catalogue() -> list[str]:
    if not os.path.isdir(utils.LEXICONS):
        return []
    return sorted(f for f in os.listdir(utils.LEXICONS) if f.endswith(".csv"))


@functools.lru_cache(maxsize=1)
def inventory() -> list[dict]:
    """Inventaire des CSV : nom, lignes, colonnes (affiche dans l UI)."""
    out = []
    for f in catalogue():
        rows = _read(f)
        out.append({
            "fichier": f,
            "lignes": len(rows),
            "colonnes": ", ".join(rows[0].keys()) if rows else "",
            "famille": _family(f),
        })
    return out


def _family(fname: str) -> str:
    if fname.startswith("00_"):
        return "referentiel metiers"
    if "_lex_" in fname:
        return "lexique sectoriel"
    if fname.startswith(("40_", "41_", "42_", "43_", "44_", "45_", "46_", "60_")):
        return "langue et traduction"
    if fname.startswith("47_"):
        return "formules par contexte"
    if fname.startswith(("5", "6")) and "stopwords" in fname:
        return "stopwords"
    if fname.startswith(("55_", "56_", "57_")):
        return "restitution"
    if fname.startswith(("58_", "59_")):
        return "veille et institutions"
    return "autre"


# --------------------------------------------------------------- metiers
@functools.lru_cache(maxsize=1)
def metiers() -> list[dict]:
    return _read("00_metiers_referentiel.csv")


@functools.lru_cache(maxsize=1)
def secteurs() -> list[str]:
    return sorted({m["secteur"] for m in metiers()})


def metiers_du_secteur(secteur: str) -> list[dict]:
    return [m for m in metiers() if m["secteur"] == secteur]


def chercher_metier(q: str, limit: int = 20) -> list[dict]:
    qn = utils.normalize(q)
    if not qn:
        return []
    out = []
    for m in metiers():
        blob = utils.normalize(" ".join([
            m.get("metier_fr", ""), m.get("secteur", ""), m.get("famille", ""),
            m.get("mots_cles", ""), m.get("en", ""), m.get("es", ""),
            m.get("pt", ""), m.get("ht", ""),
        ]))
        if qn in blob:
            out.append(m)
    return out[:limit]


# ----------------------------------------------------- lexiques sectoriels
@functools.lru_cache(maxsize=1)
def lexique_sectoriel() -> list[dict]:
    rows: list[dict] = []
    for f in catalogue():
        if "_lex_" in f:
            rows.extend(_read(f))
    return rows


@functools.lru_cache(maxsize=1)
def _index_termes() -> dict[str, dict]:
    idx: dict[str, dict] = {}
    for r in lexique_sectoriel():
        idx.setdefault(utils.normalize(r["terme_fr"]), r)
    return idx


@functools.lru_cache(maxsize=1)
def termes_par_secteur() -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in lexique_sectoriel():
        out.setdefault(r.get("secteur", "autre"), []).append(r)
    return out


def definir(terme: str) -> dict | None:
    return _index_termes().get(utils.normalize(terme))


def chercher_terme(q: str, limit: int = 40, secteur: str | None = None) -> list[dict]:
    qn = utils.normalize(q)
    rows = lexique_sectoriel()
    if secteur:
        rows = [r for r in rows if r.get("secteur") == secteur]
    if not qn:
        return rows[:limit]
    out = []
    for r in rows:
        blob = utils.normalize(" ".join([
            r.get("terme_fr", ""), r.get("definition_fr", ""), r.get("en", ""),
            r.get("es", ""), r.get("pt", ""), r.get("ht", ""), r.get("registre", ""),
        ]))
        if qn in blob:
            out.append(r)
    return out[:limit]


def detecter_secteurs(texte: str, top: int = 5) -> list[tuple[str, int, list[str]]]:
    """Identifie les secteurs dont le vocabulaire apparait dans le texte."""
    tn = " " + utils.normalize(texte) + " "
    scores: dict[str, list[str]] = {}
    for r in lexique_sectoriel():
        t = utils.normalize(r["terme_fr"])
        if len(t) < 5:
            continue
        if f" {t} " in tn:
            scores.setdefault(r["secteur"], []).append(r["terme_fr"])
    ranked = sorted(scores.items(), key=lambda kv: -len(kv[1]))
    return [(s, len(ts), ts[:12]) for s, ts in ranked[:top]]


def jargon_present(texte: str, limit: int = 60) -> list[dict]:
    """Termes techniques et familiers effectivement presents dans le texte."""
    tn = " " + utils.normalize(texte) + " "
    out = []
    for r in lexique_sectoriel():
        t = utils.normalize(r["terme_fr"])
        if len(t) >= 5 and f" {t} " in tn:
            out.append(r)
    for r in familier():
        t = utils.normalize(r["expression"])
        if len(t) >= 5 and f" {t} " in tn:
            out.append({
                "terme_fr": r["expression"], "registre": r["niveau"],
                "definition_fr": r["sens_courant"], "secteur": "registre_familier",
                "en": "", "es": "", "pt": "", "ht": "",
            })
    return out[:limit]


# ------------------------------------------------------------- stopwords
@functools.lru_cache(maxsize=8)
def stopwords(lang: str = "fr") -> frozenset[str]:
    rows = _read(f"5{LANGS.index(lang) if lang in LANGS else 0}_stopwords_{lang}.csv")
    if not rows:
        rows = _read("50_stopwords_fr.csv")
    return frozenset(r["mot"] for r in rows)


@functools.lru_cache(maxsize=1)
def stopwords_all() -> frozenset[str]:
    s: set[str] = set()
    for lg in LANGS:
        s |= set(stopwords(lg))
    return frozenset(s)


# ----------------------------------------------------- langue et traduction
@functools.lru_cache(maxsize=1)
def multilingue() -> list[dict]:
    return _read("40_langue_multilingue_core.csv")


@functools.lru_cache(maxsize=1)
def connecteurs() -> list[dict]:
    return _read("41_langue_connecteurs_rhetoriques.csv")


@functools.lru_cache(maxsize=1)
def verbes_action() -> list[dict]:
    return _read("42_langue_verbes_action.csv")


@functools.lru_cache(maxsize=1)
def familier() -> list[dict]:
    return _read("43_langue_argot_familier_fr.csv")


@functools.lru_cache(maxsize=1)
def idiomes() -> list[dict]:
    return _read("44_langue_expressions_idiomatiques.csv")


@functools.lru_cache(maxsize=1)
def sigles() -> list[dict]:
    return _read("45_langue_sigles_abreviations.csv")


@functools.lru_cache(maxsize=1)
def creole() -> list[dict]:
    return _read("46_langue_creole_haitien.csv")


@functools.lru_cache(maxsize=1)
def faux_amis() -> list[dict]:
    return _read("60_faux_amis_traduction.csv")


@functools.lru_cache(maxsize=16)
def glossaire(source: str = "fr", cible: str = "en") -> dict[str, str]:
    """Dictionnaire terme source -> terme cible, construit sur tous les CSV."""
    gl: dict[str, str] = {}

    def add(src: str, dst: str) -> None:
        s, d = (src or "").strip(), (dst or "").strip()
        if len(s) >= 3 and d:
            gl.setdefault(utils.normalize(s), d)

    for r in multilingue():
        add(r.get(source, ""), r.get(cible, ""))
    for r in connecteurs():
        add(r.get(source, ""), r.get(cible, ""))
    for r in lexique_sectoriel():
        s = r.get("terme_fr", "") if source == "fr" else r.get(source, "")
        d = r.get("terme_fr", "") if cible == "fr" else r.get(cible, "")
        add(s, d)
    for r in verbes_action():
        s = r.get("verbe_fr", "") if source == "fr" else r.get(source, "")
        d = r.get("verbe_fr", "") if cible == "fr" else r.get(cible, "")
        add(s, d)
    for r in creole():
        s = r.get("ht", "") if source == "ht" else r.get(source, "")
        d = r.get("ht", "") if cible == "ht" else r.get(cible, "")
        add(s, d)
    for r in idiomes():
        add(r.get(source, ""), r.get(cible, ""))
    return gl


def traduire_terme(terme: str, cible: str, source: str = "fr") -> str | None:
    return glossaire(source, cible).get(utils.normalize(terme))


def developper_sigles(texte: str) -> list[dict]:
    present = []
    for r in sigles():
        if r["sigle"] and r["sigle"] in texte:
            present.append(r)
    return present


# ------------------------------------------------- contextes et formules
@functools.lru_cache(maxsize=1)
def contextes() -> list[dict]:
    return _read("55_contextes_restitution.csv")


@functools.lru_cache(maxsize=1)
def contextes_index() -> dict[str, dict]:
    return {c["cle"]: c for c in contextes()}


@functools.lru_cache(maxsize=1)
def trames() -> list[dict]:
    return _read("56_trames_narratives.csv")


@functools.lru_cache(maxsize=1)
def registres() -> list[dict]:
    return _read("57_registres_langue.csv")


@functools.lru_cache(maxsize=1)
def formules() -> list[dict]:
    return _read("47_formules_par_contexte.csv")


def formules_du_contexte(cle: str, lang: str = "fr") -> dict[str, str]:
    out: dict[str, str] = {}
    for r in formules():
        if r.get("contexte") == cle:
            val = r.get("formule_fr" if lang == "fr" else lang, "") or r.get("formule_fr", "")
            out.setdefault(r.get("fonction", ""), val)
    return out


# ------------------------------------------------------- veille et pays
@functools.lru_cache(maxsize=1)
def sources_veille() -> list[dict]:
    return _read("58_sources_veille.csv")


@functools.lru_cache(maxsize=1)
def pays() -> list[dict]:
    return _read("59_pays_institutions.csv")


def pays_cites(texte: str) -> list[dict]:
    tn = utils.normalize(texte)
    return [p for p in pays() if utils.normalize(p["pays"]) in tn]


def sources_pour(thematique: str, limit: int = 8) -> list[dict]:
    qn = utils.normalize(thematique)
    scored = []
    for s in sources_veille():
        blob = utils.normalize(s.get("thematique", "") + " " + s.get("nom", ""))
        hits = sum(1 for w in qn.split() if len(w) > 3 and w in blob)
        if hits:
            scored.append((hits, s))
    scored.sort(key=lambda t: -t[0])
    out = [s for _, s in scored[:limit]]
    if not out:
        out = [s for s in sources_veille() if s.get("fiabilite") == "officielle"][:limit]
    return out


# ------------------------------------------------------------ statistiques
def stats() -> dict:
    inv = inventory()
    return {
        "fichiers_csv": len(inv),
        "lignes_totales": sum(i["lignes"] for i in inv),
        "metiers": len(metiers()),
        "secteurs": len(secteurs()),
        "termes_sectoriels": len(lexique_sectoriel()),
        "entrees_multilingues": len(multilingue()),
        "sigles": len(sigles()),
        "expressions_familieres": len(familier()) + len(idiomes()),
        "contextes": len(contextes()),
        "sources_veille": len(sources_veille()),
        "langues": len(LANGS),
    }
