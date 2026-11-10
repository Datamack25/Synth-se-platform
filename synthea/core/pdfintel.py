"""SYNTHEA - agent COLLATEUR : intelligence documentaire sur PDF.

Comparer deux versions, extraire les tableaux, detecter et remplir les
formulaires, lire et corriger les metadonnees, inspecter un document, et
brancher la synthese (SCRIBE) et la traduction (BABEL) directement sur un PDF.
"""
from __future__ import annotations

import difflib
import html as _html
import io
import os
import time

from . import doctools as dt
from . import utils
from .doctools import Resultat, echec

AG = "COLLATEUR"


def _t(fn):
    def wrap(*a, **k) -> Resultat:
        t0 = time.time()
        try:
            r = fn(*a, **k)
        except Exception as exc:                       # pragma: no cover
            r = echec(AG, fn.__name__, f"{exc.__class__.__name__}: {exc}")
        r.duree = round(time.time() - t0, 2)
        return r
    return wrap


def _pages_text(data: bytes) -> list[str]:
    from .convert import _pdf_pages_text
    return [t for _, t, _ in _pdf_pages_text(data)]


# ===================================================================
# Comparaison
# ===================================================================
@_t
def compare_pdf(nom_a: str, data_a: bytes, nom_b: str, data_b: bytes,
                granularite: str = "phrase") -> Resultat:
    """Compare deux documents et produit un rapport HTML cote a cote."""
    pa, pb = _pages_text(data_a), _pages_text(data_b)
    if not pa and not pb:
        return echec(AG, "Comparer", "aucun texte extractible dans les deux "
                                     "documents (scans ? passe-les par l OCR)")

    def decoupe(txt: str) -> list[str]:
        if granularite == "mot":
            return utils.words(txt)
        if granularite == "ligne":
            return [l.strip() for l in txt.split("\n") if l.strip()]
        return utils.split_sentences(txt, min_len=12)

    a_all = [s for t in pa for s in decoupe(t)]
    b_all = [s for t in pb for s in decoupe(t)]
    sm = difflib.SequenceMatcher(None, a_all, b_all, autojunk=False)
    ops = sm.get_opcodes()
    ajouts = sum(j2 - j1 for tag, _, _, j1, j2 in ops if tag in ("insert", "replace"))
    suppr = sum(i2 - i1 for tag, i1, i2, _, _ in ops if tag in ("delete", "replace"))
    similarite = sm.ratio()

    lignes = []
    for tag, i1, i2, j1, j2 in ops:
        if tag == "equal":
            for s in a_all[i1:i2][:3]:
                lignes.append(("=", s, s))
            if i2 - i1 > 3:
                lignes.append(("~", f"[... {i2 - i1 - 3} elements identiques ...]", ""))
        elif tag == "delete":
            for s in a_all[i1:i2]:
                lignes.append(("-", s, ""))
        elif tag == "insert":
            for s in b_all[j1:j2]:
                lignes.append(("+", "", s))
        else:
            for s in a_all[i1:i2]:
                lignes.append(("-", s, ""))
            for s in b_all[j1:j2]:
                lignes.append(("+", "", s))

    rows = []
    for signe, g, d in lignes[:4000]:
        cls = {"-": "sup", "+": "add", "=": "eq", "~": "skip"}[signe]
        rows.append(f"<tr class='{cls}'><td class='n'>{signe}</td>"
                    f"<td>{_html.escape(g)}</td><td>{_html.escape(d)}</td></tr>")

    rapport = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<title>Comparaison — {_html.escape(nom_a)} / {_html.escape(nom_b)}</title><style>
body{{font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
background:#F1EEE8;color:#17202A;margin:0;padding:28px;line-height:1.5}}
.wrap{{max-width:1180px;margin:auto;background:#fff;border:1px solid #DDD7CC;
border-radius:12px;overflow:hidden}}
header{{padding:24px 30px;border-bottom:1px solid #DDD7CC;background:#FBFAF7}}
h1{{margin:0 0 6px;font-size:1.35rem}}
.kpi{{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px}}
.kpi div{{border:1px solid #DDD7CC;border-radius:9px;padding:9px 14px;background:#fff}}
.kpi b{{display:block;font-size:1.25rem}}
table{{width:100%;border-collapse:collapse;font-size:.84rem}}
th{{background:#F1EEE8;text-align:left;padding:9px 12px;font-size:.7rem;
text-transform:uppercase;letter-spacing:.08em;color:#44525F}}
td{{padding:6px 12px;border-bottom:1px solid #F1EEE8;vertical-align:top;width:46%}}
td.n{{width:28px;text-align:center;font-weight:700;color:#8A97A3}}
tr.sup td{{background:#FBEDEA}} tr.add td{{background:#EAF4EE}}
tr.skip td{{color:#8A97A3;font-style:italic;background:#FCFBF8}}
</style></head><body><div class="wrap"><header>
<h1>Comparaison de documents</h1>
<div>A : <strong>{_html.escape(nom_a)}</strong> ({len(pa)} pages) ·
B : <strong>{_html.escape(nom_b)}</strong> ({len(pb)} pages)</div>
<div class="kpi">
<div>Similarite<b>{similarite:.1%}</b></div>
<div>Ajouts<b>{ajouts}</b></div>
<div>Suppressions<b>{suppr}</b></div>
<div>Granularite<b>{granularite}</b></div>
</div></header>
<table><tr><th></th><th>Document A</th><th>Document B</th></tr>
{''.join(rows)}</table></div></body></html>"""

    return Resultat(True, AG, "Comparer",
                    [(dt.safe_name(f"{nom_a}-vs-{nom_b}", "comparaison", "html"),
                      rapport.encode("utf-8"))],
                    f"Similarite {similarite:.1%} — {ajouts} ajout(s), "
                    f"{suppr} suppression(s).",
                    {"similarite": round(similarite, 4), "ajouts": ajouts,
                     "suppressions": suppr, "pages_a": len(pa), "pages_b": len(pb)})


# ===================================================================
# Tableaux
# ===================================================================
@_t
def extract_tables(nom: str, data: bytes, plages: str = "",
                   format_sortie: str = "xlsx") -> Resultat:
    if not utils.has_module("pdfplumber"):
        return echec(AG, "Extraire les tableaux", "pdfplumber requis")
    import pdfplumber
    total = dt.page_count(data)
    cibles = set(dt.parse_pages(plages, total))
    trouves: list[tuple[int, int, list]] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            if i not in cibles:
                continue
            try:
                tabs = page.extract_tables() or []
            except Exception:
                tabs = []
            for k, tab in enumerate(tabs, start=1):
                if tab and len(tab) > 1:
                    trouves.append((i, k, tab))
    if not trouves:
        return echec(AG, "Extraire les tableaux",
                     "aucun tableau detecte. Les tableaux sans bordures ou "
                     "issus d un scan ne sont pas reconnus ; essaie l OCR "
                     "d abord, ou l export « PDF vers Excel » en mode texte.")

    if format_sortie == "csv":
        import csv as _csv
        import zipfile
        zbuf = io.BytesIO()
        with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
            for pno, k, tab in trouves:
                s = io.StringIO()
                w = _csv.writer(s)
                for row in tab:
                    w.writerow(["" if c is None else str(c) for c in row])
                z.writestr(f"p{pno:04d}-tableau{k}.csv", s.getvalue())
        return Resultat(True, AG, "Extraire les tableaux",
                        [(dt.safe_name(nom, "tableaux", "zip"), zbuf.getvalue())],
                        f"{len(trouves)} tableau(x) exportes en CSV.",
                        {"tableaux": len(trouves)})

    import xlsxwriter
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    f_head = wb.add_format({"bold": True, "bg_color": "#1F6F6B",
                            "font_color": "white", "border": 1})
    f_cell = wb.add_format({"border": 1, "text_wrap": True, "valign": "top",
                            "font_size": 9})
    idx = wb.add_worksheet("Index")
    idx.set_column(0, 3, 18)
    for j, h in enumerate(["page", "tableau", "lignes", "colonnes"]):
        idx.write(0, j, h, f_head)
    for r, (pno, k, tab) in enumerate(trouves, start=1):
        idx.write_row(r, 0, [pno, k, len(tab), len(tab[0] or [])])
        ws = wb.add_worksheet(f"p{pno}_t{k}"[:31])
        for i, row in enumerate(tab):
            for j, cell in enumerate(row):
                ws.write(i, j, "" if cell is None else str(cell),
                         f_head if i == 0 else f_cell)
        ws.set_column(0, 30, 20)
    wb.close()
    return Resultat(True, AG, "Extraire les tableaux",
                    [(dt.safe_name(nom, "tableaux", "xlsx"), buf.getvalue())],
                    f"{len(trouves)} tableau(x) extraits sur "
                    f"{len({p for p, _, _ in trouves})} page(s).",
                    {"tableaux": len(trouves)})


# ===================================================================
# Formulaires
# ===================================================================
@_t
def inspect_forms(nom: str, data: bytes) -> Resultat:
    """Detecte les champs de formulaire et leur type."""
    try:
        r = dt.reader(data)
        champs = r.get_fields() or {}
    except Exception as exc:
        return echec(AG, "Formulaires", f"lecture impossible : {exc}")
    if not champs:
        return echec(AG, "Formulaires",
                     "ce PDF ne contient aucun champ interactif. C est "
                     "probablement un formulaire a plat (image ou texte) : "
                     "utilise « Editer » pour y ecrire, ou « Caviarder » pour "
                     "masquer des zones.")
    types = {"/Tx": "texte", "/Btn": "case ou bouton", "/Ch": "liste",
             "/Sig": "signature"}
    rows = []
    for k, v in champs.items():
        rows.append({
            "champ": k,
            "type": types.get(str(v.get("/FT", "")), str(v.get("/FT", "?"))),
            "valeur": str(v.get("/V", ""))[:80],
            "options": ", ".join(str(o) for o in (v.get("/Opt") or []))[:80],
        })
    return Resultat(True, AG, "Formulaires", [],
                    f"{len(rows)} champ(s) detecte(s).",
                    {"champs": rows})


@_t
def fill_forms(nom: str, data: bytes, valeurs: dict[str, str],
               aplatir: bool = False) -> Resultat:
    from pypdf import PdfReader, PdfWriter
    try:
        r = PdfReader(io.BytesIO(data))
        w = PdfWriter()
        w.append(r)
        remplis = 0
        for page in w.pages:
            try:
                w.update_page_form_field_values(page, valeurs)
                remplis += 1
            except Exception:
                continue
        try:
            w.set_need_appearances_writer(True)
        except Exception:
            pass
        out = dt.writer_bytes(w)
    except Exception as exc:
        return echec(AG, "Remplir le formulaire", f"{exc}")

    avert = []
    if aplatir:
        rendus = dt.render_pages(out, dpi=150)
        if rendus:
            out = dt.images_to_pdf([im for _, im in rendus], quality=92)
            avert.append("Formulaire aplati : les champs ne sont plus "
                         "modifiables et le texte devient une image.")
    return Resultat(True, AG, "Remplir le formulaire",
                    [(dt.safe_name(nom, "rempli", "pdf"), out)],
                    f"{len(valeurs)} champ(s) renseigne(s).",
                    {"champs": list(valeurs)[:30]}, avert)


# ===================================================================
# Metadonnees et inspection
# ===================================================================
@_t
def read_metadata(nom: str, data: bytes) -> Resultat:
    infos: dict = {"fichier": nom, "octets": len(data),
                   "pages": dt.page_count(data),
                   "chiffre": dt.is_encrypted(data)}
    try:
        r = dt.reader(data)
        meta = r.metadata or {}
        for k, v in meta.items():
            infos[str(k).lstrip("/")] = str(v)[:200]
    except Exception:
        pass
    try:
        import pikepdf
        with pikepdf.open(io.BytesIO(data)) as pdf:
            infos["version_pdf"] = str(pdf.pdf_version)
            infos["linearise"] = bool(getattr(pdf, "is_linearized", False))
            with pdf.open_metadata() as m:
                for k in ("dc:title", "dc:creator", "pdfaid:part"):
                    if k in m:
                        infos[k] = str(m[k])[:200]
    except Exception:
        pass
    tailles = dt.page_sizes(data)[:1]
    if tailles:
        W, H = tailles[0]
        infos["format_page"] = f"{W / 2.8346:.0f} x {H / 2.8346:.0f} mm"
    textes = _pages_text(data)
    mots = sum(utils.word_count(t) for t in textes)
    infos["mots_extractibles"] = mots
    infos["pages_sans_texte"] = sum(1 for t in textes if utils.word_count(t) < 5)
    return Resultat(True, AG, "Inspecter", [],
                    f"{infos['pages']} page(s), {utils.human_int(mots)} mots "
                    f"extractibles.", {"infos": infos})


@_t
def write_metadata(nom: str, data: bytes, titre: str = "", auteur: str = "",
                   sujet: str = "", mots_cles: str = "",
                   effacer: bool = False) -> Resultat:
    try:
        import pikepdf
        with pikepdf.open(io.BytesIO(data)) as pdf:
            if effacer:
                pdf.docinfo.clear()
                try:
                    del pdf.Root.Metadata
                except Exception:
                    pass
            else:
                if titre:
                    pdf.docinfo["/Title"] = titre
                if auteur:
                    pdf.docinfo["/Author"] = auteur
                if sujet:
                    pdf.docinfo["/Subject"] = sujet
                if mots_cles:
                    pdf.docinfo["/Keywords"] = mots_cles
            buf = io.BytesIO()
            pdf.save(buf)
            out = buf.getvalue()
    except Exception as exc:
        return echec(AG, "Metadonnees", f"{exc}")
    msg = ("Toutes les metadonnees ont ete effacees." if effacer
           else "Metadonnees mises a jour.")
    return Resultat(True, AG, "Metadonnees",
                    [(dt.safe_name(nom, "metadonnees", "pdf"), out)], msg, {})


# ===================================================================
# Branchement sur la chaine d analyse
# ===================================================================
@_t
def summarize_pdf(nom: str, data: bytes, objectif: str = "lecture_rapide",
                  contexte: str = "", langue: str = "fr") -> Resultat:
    """Lance la chaine SYNTHEA complete sur un PDF et rend la synthese."""
    from . import agents as ag_mod
    from . import budget as bud_mod
    orch = ag_mod.Orchestrator({
        "objectif": objectif, "profondeur": "auto",
        "contextes": [contexte] if contexte else [],
        "langues_cibles": [], "visuels": False, "veille": False,
        "langue": langue,
    })
    state = orch.run([(nom, data)], progress=None)
    if not state.get("tree"):
        return echec(AG, "Resumer", "analyse interrompue : aucun texte exploitable")
    rend = next(iter(state["renditions"].values()))
    bud: bud_mod.Budget = state["budget"]
    ctrl = state.get("controle_budget") or {}
    md = rend.to_markdown()
    return Resultat(True, AG, "Resumer",
                    [(dt.safe_name(nom, "synthese", "md"), md.encode("utf-8"))],
                    f"{bud.pages_source} pages → "
                    f"{ctrl.get('pages_produites', '?')} page(s) de synthese "
                    f"({rend.context_label}).",
                    {"budget": bud.to_dict(), "controle": ctrl,
                     "score_argus": (state.get("audit") or {}).get("score"),
                     "etat": state})


@_t
def translate_pdf(nom: str, data: bytes, cible: str = "en",
                  moteur: str = "", source: str = "fr") -> Resultat:
    """Traduit le texte d un PDF page par page et rend un PDF bilingue."""
    from . import translation
    from .convert import _reconstruire_pdf
    pages = _pages_text(data)
    if not any(p.strip() for p in pages):
        return echec(AG, "Traduire", "aucun texte extractible (scan ? OCR d abord)")
    moteur = moteur or translation.best_engine()
    blocs: list[tuple[str, str]] = []
    couvertures = []
    moteurs = set()
    for i, txt in enumerate(pages, start=1):
        if not txt.strip():
            continue
        blocs.append(("titre2", f"Page {i}"))
        r = translation.translate_text(txt, cible, source, moteur)
        couvertures.append(r["couverture"])
        moteurs.add(r["moteur"])
        blocs.append(("normal", r["texte"]))
    cov = sum(couvertures) / len(couvertures) if couvertures else 0.0
    out = _reconstruire_pdf(
        f"{os.path.splitext(os.path.basename(nom))[0]} — "
        f"{translation.lexicons.LANG_LABELS.get(cible, cible)}", blocs)
    eff = "+".join(sorted(moteurs))
    return Resultat(True, AG, "Traduire",
                    [(dt.safe_name(nom, f"traduit-{cible}", "pdf"), out)],
                    f"{len(couvertures)} page(s) traduites vers "
                    f"{translation.lexicons.LANG_LABELS.get(cible, cible)} "
                    f"(moteur {eff}, couverture {cov:.0%}).",
                    {"moteur": eff, "couverture": round(cov, 3)},
                    [] if cov > 0.85 else
                    ["Traduction assistee par glossaire : les termes hors "
                     "referentiel restent dans la langue d origine. Installe "
                     "deep-translator ou configure une cle API pour une "
                     "traduction complete."])
