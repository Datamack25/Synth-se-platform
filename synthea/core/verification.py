"""SYNTHEA - Agent ARGUS : autoverification de la couverture et de la fidelite.

ARGUS repond a une seule question, mais de facon verifiable :
« tout le document a-t-il reellement ete lu, analyse et resume ? »

Neuf controles independants :
  C1 inventaire des unites extraites et des avertissements d extraction
  C2 couverture par la segmentation (chaque page appartient a un bloc)
  C3 couverture par la synthese (chaque page a un digest ou une section)
  C4 pages orphelines explicitement listees
  C5 fidelite numerique (aucun chiffre de la synthese absent du document)
  C6 fidelite litterale (chaque constat retrouve dans le texte source)
  C7 tracabilite (chaque constat porte une reference de page)
  C8 redondance interne de la synthese
  C9 taux de compression et equilibre des sections
"""
from __future__ import annotations

import json
import os

from . import ml, utils
from .models import Chunk, Document, SummaryTree

SEUILS = {"couverture_ok": 0.995, "couverture_alerte": 0.95,
          "fidelite_ok": 0.98, "tracabilite_ok": 0.95, "redondance_max": 0.15}


def _pct(x: float) -> float:
    return round(100.0 * x, 2)


def audit(doc: Document, chunks: list[Chunk], tree: SummaryTree) -> dict:
    pages = [p.index for p in doc.pages]
    n = len(pages) or 1
    empties = set(doc.empty_pages)
    exploitables = [p for p in pages if p not in empties]
    n_expl = len(exploitables) or 1

    # ---------------- C1 inventaire -------------------------------
    warnings = [{"page": p.index, "fichier": p.source_file, "message": p.warning}
                for p in doc.pages if p.warning]
    c1 = {
        "libelle": "Inventaire de l extraction",
        "unites_extraites": len(pages),
        "pages_exploitables": len(exploitables),
        "pages_vides": sorted(empties),
        "pages_ocr": doc.ocr_pages,
        "avertissements": warnings[:200],
        "n_avertissements": len(warnings),
        "fichiers": doc.files,
        "tronque": bool(doc.meta.get("tronque")),
        "statut": "alerte" if doc.meta.get("tronque") else
                  ("attention" if len(empties) > 0.10 * n else "ok"),
    }

    # ---------------- C2 couverture segmentation ------------------
    seg = set()
    for ch in chunks:
        seg.update(ch.pages)
    seg_missing = [p for p in exploitables if p not in seg]
    r_seg = 1.0 - utils.safe_div(len(seg_missing), n_expl)
    c2 = {
        "libelle": "Couverture par la segmentation",
        "taux": _pct(r_seg),
        "pages_non_segmentees": seg_missing[:200],
        "n_manquantes": len(seg_missing),
        "statut": _statut(r_seg, "couverture"),
    }

    # ---------------- C3 couverture synthese ----------------------
    cov = tree.covered_pages
    digested = {p for p, v in tree.page_digests.items() if v}
    sec_pages: set[int] = set()
    for s in tree.sections:
        sec_pages.update(range(s.page_start, s.page_end + 1))
    resumee = (digested | sec_pages)
    missing = [p for p in exploitables if p not in resumee]
    r_sum = 1.0 - utils.safe_div(len(missing), n_expl)
    c3 = {
        "libelle": "Couverture par la synthese",
        "taux": _pct(r_sum),
        "pages_avec_digest": len(digested),
        "pages_dans_une_section": len(sec_pages),
        "pages_couvertes": len(resumee & set(exploitables)),
        "statut": _statut(r_sum, "couverture"),
    }

    # ---------------- C4 pages orphelines -------------------------
    orphan_rows = []
    for p in missing[:200]:
        pg = doc.page(p)
        orphan_rows.append({
            "page": p,
            "fichier": pg.source_file if pg else "",
            "mots": pg.word_count if pg else 0,
            "cause": (pg.warning if pg and pg.warning else
                      "page non retenue par la selection"),
            "extrait": utils.truncate(pg.text, 160) if pg else "",
        })
    c4 = {
        "libelle": "Pages non resumees",
        "n": len(missing),
        "detail": orphan_rows,
        "statut": "ok" if not missing else
                  ("attention" if len(missing) <= 0.05 * n_expl else "alerte"),
    }

    # ---------------- C5 fidelite numerique -----------------------
    src_nums = ml.numeric_facts(doc.full_text()[:2_000_000])
    bad: list[dict] = []
    checked = 0
    for c in tree.all_claims:
        for v in ml.numeric_facts(c.text):
            checked += 1
            if v not in src_nums:
                bad.append({"valeur": v, "constat": utils.truncate(c.text, 140),
                            "ref": c.ref})
    r_num = 1.0 - utils.safe_div(len(bad), max(checked, 1))
    c5 = {
        "libelle": "Fidelite numerique",
        "valeurs_verifiees": checked,
        "anomalies": bad[:50],
        "taux": _pct(r_num),
        "statut": _statut(r_num, "fidelite"),
        "commentaire": "la synthese extractive ne doit contenir aucun chiffre "
                       "absent du document source",
    }

    # ---------------- C6 fidelite litterale -----------------------
    page_norm = {p.index: utils.normalize(p.text) for p in doc.pages if p.text}
    verbatim = absent = 0
    exemples = []
    for c in tree.all_claims:
        probe = utils.normalize(c.text)[:60]
        if not probe:
            continue
        found = any(probe in page_norm.get(p, "") for p in c.pages) or \
            any(probe in body for body in page_norm.values())
        if found:
            verbatim += 1
        else:
            absent += 1
            if len(exemples) < 20:
                exemples.append({"constat": utils.truncate(c.text, 150), "ref": c.ref})
    r_lit = utils.safe_div(verbatim, max(verbatim + absent, 1), 1.0)
    c6 = {
        "libelle": "Fidelite litterale des constats",
        "constats_retrouves": verbatim,
        "constats_non_retrouves": absent,
        "exemples": exemples,
        "taux": _pct(r_lit),
        "statut": _statut(r_lit, "fidelite"),
    }

    # ---------------- C7 tracabilite ------------------------------
    claims = tree.all_claims
    with_ref = sum(1 for c in claims if c.pages)
    r_trace = utils.safe_div(with_ref, max(len(claims), 1), 1.0)
    c7 = {
        "libelle": "Tracabilite des constats",
        "constats": len(claims),
        "avec_reference": with_ref,
        "taux": _pct(r_trace),
        "statut": "ok" if r_trace >= SEUILS["tracabilite_ok"] else "attention",
    }

    # ---------------- C8 redondance -------------------------------
    # un constat repris par plusieurs sections est le MEME objet (sa reference
    # de page a ete enrichie) : il ne compte qu une fois
    uniques, vus_id = [], set()
    partages = 0
    for c in claims:
        if id(c) in vus_id:
            partages += 1
            continue
        vus_id.add(id(c))
        uniques.append(c)
    seen: list[set[str]] = []
    dup = 0
    for c in uniques:
        toks = set(utils.normalize(c.text).split())
        if any(len(toks & s) / max(len(toks | s), 1) > 0.6 for s in seen):
            dup += 1
        seen.append(toks)
    r_dup = utils.safe_div(dup, max(len(uniques), 1))
    c8 = {
        "libelle": "Redondance interne",
        "constats_distincts": len(uniques),
        "constats_redondants": dup,
        "constats_partages_entre_sections": partages,
        "taux": _pct(r_dup),
        "statut": "ok" if r_dup <= SEUILS["redondance_max"] else "attention",
    }

    # ---------------- C9 compression ------------------------------
    sum_words = sum(utils.word_count(c.text) for c in claims) + \
        sum(utils.word_count(v) for v in tree.page_digests.values())
    ratio = utils.safe_div(sum_words, max(doc.n_words, 1))
    sec_sizes = [len(s.claims) for s in tree.sections] or [0]
    # le taux attendu depend de la taille : un document court se comprime peu
    haut = 0.45 if doc.n_words > 60000 else (0.65 if doc.n_words > 15000 else 0.90)
    c9 = {
        "libelle": "Compression et equilibre",
        "mots_source": doc.n_words,
        "mots_synthese": sum_words,
        "taux_compression": _pct(ratio),
        "plage_attendue": f"0,2 % – {haut * 100:.0f} %",
        "sections": len(tree.sections),
        "constats_par_section_min": min(sec_sizes),
        "constats_par_section_max": max(sec_sizes),
        "statut": "ok" if 0.002 <= ratio <= haut else "attention",
    }

    controles = {"C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5,
                 "C6": c6, "C7": c7, "C8": c8, "C9": c9}

    # ---------------- score global --------------------------------
    score = (0.30 * r_sum + 0.18 * r_seg + 0.18 * r_num + 0.14 * r_lit
             + 0.10 * r_trace + 0.10 * (1.0 - min(r_dup, 1.0)))
    if doc.meta.get("tronque"):
        score *= 0.85
    statuts = [c["statut"] for c in controles.values()]
    verdict = ("Document integralement analyse et resume" if score >= 0.97 and
               "alerte" not in statuts else
               "Analyse complete avec points de vigilance" if score >= 0.90 else
               "Analyse partielle : action requise")

    return {
        "doc_id": doc.doc_id,
        "titre": doc.title,
        "date": utils.now_fr(),
        "score": _pct(score),
        "verdict": verdict,
        "controles": controles,
        "recommandations": recommendations(controles, doc),
        "empreinte": {
            "pages": doc.n_pages,
            "sha1_corpus": utils.short_sha(doc.full_text()[:500000], 16),
            "sha1_synthese": utils.short_sha(
                " ".join(c.text for c in tree.all_claims), 16),
        },
    }


def _statut(ratio: float, kind: str) -> str:
    if kind == "couverture":
        if ratio >= SEUILS["couverture_ok"]:
            return "ok"
        return "attention" if ratio >= SEUILS["couverture_alerte"] else "alerte"
    return "ok" if ratio >= SEUILS["fidelite_ok"] else (
        "attention" if ratio >= 0.90 else "alerte")


def recommendations(controles: dict, doc: Document) -> list[str]:
    rec: list[str] = []
    c1, c3, c4, c5 = controles["C1"], controles["C3"], controles["C4"], controles["C5"]
    if c1["tronque"]:
        rec.append(f"Le corpus a ete tronque a {doc.meta.get('max_pages')} unites : "
                   f"relancer en augmentant la limite ou scinder le document.")
    if c1["pages_vides"]:
        n = len(c1["pages_vides"])
        rec.append(f"{n} page(s) sans texte extractible. Activer l OCR "
                   f"(pytesseract + tesseract-ocr) pour les pages numerisees.")
    if c4["n"]:
        rec.append(f"{c4['n']} page(s) non resumee(s) : passer en profondeur "
                   f"« exhaustif » ou relancer SCRIBE sur ces pages.")
    if c3["taux"] < 100:
        rec.append("Couverture de synthese incomplete : verifier l onglet "
                   "« Verification ARGUS » page par page.")
    if c5["anomalies"]:
        rec.append("Des chiffres de la synthese sont introuvables dans la source : "
                   "desactiver la reformulation abstractive pour revenir au mode "
                   "strictement extractif.")
    if controles["C8"]["statut"] != "ok":
        rec.append("Synthese redondante : reduire le nombre de constats par section.")
    if not rec:
        rec.append("Aucune action requise : couverture, fidelite et tracabilite "
                   "conformes aux seuils.")
    return rec


# ------------------------------------------------------------ page par page
def page_table(doc: Document, chunks: list[Chunk], tree: SummaryTree) -> list[dict]:
    """Tableau de controle ligne a ligne, exportable en Excel."""
    from .chunking import coverage_map
    cov = coverage_map(doc, chunks)
    sec_of: dict[int, str] = {}
    for s in tree.sections:
        for p in range(s.page_start, s.page_end + 1):
            sec_of.setdefault(p, s.title)
    rows = []
    for p in doc.pages:
        digest = tree.page_digests.get(p.index, "")
        rows.append({
            "page": p.index,
            "fichier": p.source_file,
            "unite": p.unit,
            "mots": p.word_count,
            "ocr": "oui" if p.ocr else "",
            "blocs": ";".join(str(c) for c in cov.get(p.index, [])),
            "section": sec_of.get(p.index, ""),
            "resumee": "oui" if (digest or p.index in sec_of) else
                       ("vide" if p.is_empty else "NON"),
            "digest": utils.truncate(digest, 180),
            "avertissement": p.warning,
            "sha1": p.sha1,
        })
    return rows


def save_report(report: dict, outdir: str | None = None) -> str:
    outdir = outdir or utils.EXPORTS
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, f"argus-{utils.slugify(report['titre'])}-"
                                f"{utils.stamp()}.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    return path
