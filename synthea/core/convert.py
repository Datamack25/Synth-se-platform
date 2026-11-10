"""SYNTHEA - agent FORGE : conversions de format.

PDF vers Word, PowerPoint, Excel, JPEG, Markdown, texte, PDF/A.
Word, PowerPoint, Excel, JPEG, HTML vers PDF.

Deux moteurs :
  - LibreOffice quand il est installe (conversion haute fidelite, la mise en
    page d origine est conservee) ;
  - reconstruction native sinon (le contenu est preserve, la mise en page est
    refaite). Le resultat indique toujours quelle voie a ete empruntee.
"""
from __future__ import annotations

import io
import os
import time
import zipfile

from . import doctools as dt
from . import utils
from .doctools import Resultat, echec

AG = "FORGE"


def _raison_repli(suite: str) -> str:
    """Message de repli exact : LibreOffice absent, ou present mais en echec."""
    if not dt.capabilities()["libreoffice"]:
        return ("LibreOffice n est pas installe sur ce serveur (ajoute "
                "« libreoffice » a packages.txt pour la conversion haute "
                "fidelite). " + suite)
    return ("LibreOffice est installe mais n a pas pu traiter ce fichier. "
            + suite)


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


# ===================================================================
# PDF -> autres formats
# ===================================================================
def _pdf_pages_text(data: bytes, plages: str = "") -> list[tuple[int, str, list]]:
    """[(numero, texte, tableaux)] via pdfplumber, repli pypdf."""
    total = dt.page_count(data)
    cibles = set(dt.parse_pages(plages, total))
    out: list[tuple[int, str, list]] = []
    if utils.has_module("pdfplumber"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                if i not in cibles:
                    continue
                try:
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""
                try:
                    tabs = page.extract_tables() or []
                except Exception:
                    tabs = []
                out.append((i, utils.clean_text(txt), tabs))
        return out
    r = dt.reader(data)
    for i, page in enumerate(r.pages, start=1):
        if i in cibles:
            out.append((i, utils.clean_text(page.extract_text() or ""), []))
    return out


@_t
def pdf_to_word(nom: str, data: bytes, plages: str = "",
                mode: str = "fidelite") -> Resultat:
    """mode : 'fidelite' (LibreOffice si present) ou 'texte' (reconstruction)."""
    avert = []
    if mode == "fidelite":
        out = dt.soffice_convert(data, ".pdf", "docx")
        if out and dt.page_count(data) and len(out) > 2000:
            return Resultat(True, AG, "PDF vers Word",
                            [(dt.safe_name(nom, "converti", "docx"), out)],
                            "Conversion par LibreOffice : mise en page et images "
                            "conservees.",
                            {"moteur": "libreoffice"})
        avert.append(_raison_repli(
            "La conversion PDF vers Word passe par une reconstruction : le "
            "texte, les titres et les tableaux sont repris, la mise en page "
            "d origine est recomposee."))

    import docx
    from docx.shared import Pt
    pages = _pdf_pages_text(data, plages)
    if not pages:
        return echec(AG, "PDF vers Word", "aucun texte extractible "
                                          "(PDF scanne ? passe par l OCR)")
    d = docx.Document()
    d.styles["Normal"].font.size = Pt(11)
    vides = 0
    for no, txt, tabs in pages:
        d.add_heading(f"Page {no}", level=2)
        if not txt.strip() and not tabs:
            vides += 1
            d.add_paragraph("[page sans texte extractible]")
        for para in [p for p in txt.split("\n") if p.strip()]:
            d.add_paragraph(para)
        for tab in tabs:
            if not tab or not tab[0]:
                continue
            t = d.add_table(rows=1, cols=len(tab[0]))
            t.style = "Light Grid Accent 1"
            for j, cell in enumerate(tab[0]):
                t.rows[0].cells[j].text = str(cell or "")
            for row in tab[1:]:
                cells = t.add_row().cells
                for j, cell in enumerate(row[:len(tab[0])]):
                    cells[j].text = str(cell or "")
    buf = io.BytesIO()
    d.save(buf)
    if vides:
        avert.append(f"{vides} page(s) sans texte : elles sont signalees dans "
                     f"le document.")
    return Resultat(True, AG, "PDF vers Word",
                    [(dt.safe_name(nom, "converti", "docx"), buf.getvalue())],
                    f"{len(pages)} page(s) converties en Word editable.",
                    {"moteur": "reconstruction", "pages": len(pages)}, avert)


@_t
def pdf_to_powerpoint(nom: str, data: bytes, plages: str = "",
                      mode: str = "image", dpi: int = 130) -> Resultat:
    """mode : 'image' (rendu fidele par diapositive) ou 'texte' (zones editables)."""
    from pptx import Presentation
    from pptx.util import Inches, Pt
    total = dt.page_count(data)
    cibles = dt.parse_pages(plages, total)
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    avert = []

    if mode == "image":
        rendus = dt.render_pages(data, cibles, dpi=dpi)
        if not rendus:
            return echec(AG, "PDF vers PowerPoint", "rendu des pages impossible")
        textes = {no: t for no, t, _ in _pdf_pages_text(data, plages)}
        for no, img in rendus:
            s = prs.slides.add_slide(blank)
            b = io.BytesIO()
            img.save(b, format="PNG")
            b.seek(0)
            iw, ih = img.size
            ratio = min(13.333 / (iw / 96), 7.5 / (ih / 96))
            w_in, h_in = (iw / 96) * ratio, (ih / 96) * ratio
            s.shapes.add_picture(b, Inches((13.333 - w_in) / 2),
                                 Inches((7.5 - h_in) / 2), Inches(w_in), Inches(h_in))
            if textes.get(no):
                s.notes_slide.notes_text_frame.text = textes[no][:3000]
        avert.append("Chaque diapositive contient l image de la page ; le texte "
                     "d origine est place dans les notes du presentateur.")
    else:
        pages = _pdf_pages_text(data, plages)
        if not pages:
            return echec(AG, "PDF vers PowerPoint", "aucun texte extractible")
        for no, txt, _ in pages:
            s = prs.slides.add_slide(blank)
            tb = s.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(11.7), Inches(0.8))
            tb.text_frame.text = f"Page {no}"
            tb.text_frame.paragraphs[0].runs[0].font.size = Pt(24)
            tb.text_frame.paragraphs[0].runs[0].font.bold = True
            body = s.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(11.7), Inches(5.4))
            tf = body.text_frame
            tf.word_wrap = True
            lignes = [l for l in txt.split("\n") if l.strip()][:14]
            for j, ligne in enumerate(lignes):
                p = tf.paragraphs[0] if j == 0 else tf.add_paragraph()
                p.text = utils.truncate(ligne, 220)
                for run in p.runs:
                    run.font.size = Pt(13)
        avert.append("Mode texte : le contenu est editable mais la mise en page "
                     "d origine n est pas reproduite.")

    buf = io.BytesIO()
    prs.save(buf)
    return Resultat(True, AG, "PDF vers PowerPoint",
                    [(dt.safe_name(nom, "converti", "pptx"), buf.getvalue())],
                    f"{len(cibles)} page(s) transformees en diapositives "
                    f"(mode {mode}).",
                    {"mode": mode, "pages": len(cibles)}, avert)


@_t
def pdf_to_excel(nom: str, data: bytes, plages: str = "",
                 fusionner: bool = False) -> Resultat:
    """Extrait les tableaux vers Excel ; a defaut, le texte ligne par ligne."""
    import xlsxwriter
    pages = _pdf_pages_text(data, plages)
    if not pages:
        return echec(AG, "PDF vers Excel", "aucun contenu extractible")
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    f_head = wb.add_format({"bold": True, "bg_color": "#1F6F6B",
                            "font_color": "white", "border": 1})
    f_cell = wb.add_format({"border": 1, "text_wrap": True, "valign": "top",
                            "font_size": 9})
    n_tab = 0
    if fusionner:
        ws = wb.add_worksheet("Tableaux")
        ws.freeze_panes(1, 0)
        ligne = 0
        for no, _, tabs in pages:
            for tab in tabs:
                n_tab += 1
                ws.write(ligne, 0, f"Page {no} — tableau {n_tab}", f_head)
                ligne += 1
                for row in tab:
                    for j, cell in enumerate(row):
                        ws.write(ligne, j, str(cell or ""), f_cell)
                    ligne += 1
                ligne += 1
        ws.set_column(0, 25, 22)
    else:
        for no, txt, tabs in pages:
            if tabs:
                for k, tab in enumerate(tabs, start=1):
                    n_tab += 1
                    ws = wb.add_worksheet(f"p{no}_t{k}"[:31])
                    for i, row in enumerate(tab):
                        for j, cell in enumerate(row):
                            ws.write(i, j, str(cell or ""),
                                     f_head if i == 0 else f_cell)
                    ws.set_column(0, 25, 20)
            elif txt.strip():
                ws = wb.add_worksheet(f"p{no}_texte"[:31])
                ws.set_column(0, 0, 110)
                for i, ligne in enumerate([l for l in txt.split("\n") if l.strip()]):
                    ws.write(i, 0, ligne, f_cell)
    if n_tab == 0 and not fusionner:
        pass
    wb.close()
    avert = ([] if n_tab else
             ["Aucun tableau structure detecte : le texte a ete export tel quel, "
              "ligne par ligne. Les tableaux dessines sans bordures sont souvent "
              "invisibles pour l extraction."])
    return Resultat(True, AG, "PDF vers Excel",
                    [(dt.safe_name(nom, "converti", "xlsx"), buf.getvalue())],
                    f"{n_tab} tableau(x) extraits sur {len(pages)} page(s).",
                    {"tableaux": n_tab, "pages": len(pages)}, avert)


@_t
def pdf_to_jpg(nom: str, data: bytes, plages: str = "", dpi: int = 150,
               format_img: str = "JPEG", qualite: int = 90,
               mode: str = "pages") -> Resultat:
    """mode : 'pages' (une image par page) ou 'images' (images incorporees)."""
    ext = "jpg" if format_img.upper() == "JPEG" else "png"
    sorties: list[tuple[str, bytes]] = []

    if mode == "images":
        try:
            import pikepdf
        except Exception:
            return echec(AG, "PDF vers JPG", "pikepdf requis pour extraire "
                                             "les images incorporees")
        with pikepdf.open(io.BytesIO(data)) as pdf:
            k = 0
            for pno, page in enumerate(pdf.pages, start=1):
                for name, raw in (page.images or {}).items():
                    try:
                        pil = pikepdf.PdfImage(raw).as_pil_image().convert("RGB")
                    except Exception:
                        continue
                    k += 1
                    b = io.BytesIO()
                    pil.save(b, format=format_img.upper(),
                             **({"quality": qualite} if ext == "jpg" else {}))
                    sorties.append((f"p{pno:04d}-img{k:03d}.{ext}", b.getvalue()))
        if not sorties:
            return echec(AG, "PDF vers JPG", "aucune image incorporee trouvee ; "
                                             "utilise le mode « une image par page »")
    else:
        total = dt.page_count(data)
        cibles = dt.parse_pages(plages, total)
        rendus = dt.render_pages(data, cibles, dpi=dpi)
        if not rendus:
            return echec(AG, "PDF vers JPG", "rendu impossible")
        for pno, img in rendus:
            b = io.BytesIO()
            img.save(b, format=format_img.upper(),
                     **({"quality": qualite, "optimize": True} if ext == "jpg" else {}))
            sorties.append((f"{utils.slugify(os.path.splitext(nom)[0], 40)}"
                            f"-p{pno:04d}.{ext}", b.getvalue()))

    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, d in sorties:
            z.writestr(n, d)
    fichiers = sorties[:40] + [(dt.safe_name(nom, "images", "zip"), zbuf.getvalue())]
    return Resultat(True, AG, "PDF vers JPG", fichiers,
                    f"{len(sorties)} image(s) produites "
                    f"({'pages rendues' if mode == 'pages' else 'images incorporees'}).",
                    {"images": len(sorties), "dpi": dpi, "format": format_img})


@_t
def pdf_to_markdown(nom: str, data: bytes, plages: str = "",
                    titres: bool = True) -> Resultat:
    pages = _pdf_pages_text(data, plages)
    if not pages:
        return echec(AG, "PDF vers Markdown", "aucun texte extractible")
    out = [f"# {os.path.splitext(os.path.basename(nom))[0]}", ""]
    for no, txt, tabs in pages:
        out.append(f"\n<!-- page {no} -->\n")
        for ligne in [l.strip() for l in txt.split("\n") if l.strip()]:
            if titres and len(ligne) < 90 and not ligne.endswith((".", ",", ";", ":")):
                if ligne.isupper() or utils._HEAD_KW.match(ligne) or \
                        utils._HEAD_NUM.match(ligne):
                    out.append(f"## {ligne.rstrip('.')}")
                    continue
            out.append(ligne)
            out.append("")
        for tab in tabs:
            if not tab or not tab[0]:
                continue
            head = [str(c or "") for c in tab[0]]
            out.append("| " + " | ".join(head) + " |")
            out.append("| " + " | ".join("---" for _ in head) + " |")
            for row in tab[1:]:
                cells = [str(c or "").replace("\n", " ") for c in row[:len(head)]]
                cells += [""] * (len(head) - len(cells))
                out.append("| " + " | ".join(cells) + " |")
            out.append("")
    md = "\n".join(out)
    return Resultat(True, AG, "PDF vers Markdown",
                    [(dt.safe_name(nom, "converti", "md"), md.encode("utf-8"))],
                    f"{len(pages)} page(s) converties, "
                    f"{utils.word_count(md)} mots, tableaux preserves.",
                    {"pages": len(pages), "mots": utils.word_count(md)})


@_t
def pdf_to_text(nom: str, data: bytes, plages: str = "") -> Resultat:
    pages = _pdf_pages_text(data, plages)
    if not pages:
        return echec(AG, "PDF vers texte", "aucun texte extractible")
    txt = "\n\n".join(f"--- page {no} ---\n{t}" for no, t, _ in pages)
    return Resultat(True, AG, "PDF vers texte",
                    [(dt.safe_name(nom, "texte", "txt"), txt.encode("utf-8"))],
                    f"{len(pages)} page(s), {utils.word_count(txt)} mots.",
                    {"pages": len(pages)})


@_t
def pdf_to_pdfa(nom: str, data: bytes) -> Resultat:
    out = dt.gs_convert_pdfa(data)
    if out:
        return Resultat(True, AG, "PDF vers PDF/A",
                        [(dt.safe_name(nom, "pdfa", "pdf"), out)],
                        "Conversion PDF/A-2b par Ghostscript : polices "
                        "incorporees, couleurs independantes du peripherique.",
                        {"moteur": "ghostscript"})
    try:
        import pikepdf
        with pikepdf.open(io.BytesIO(data)) as pdf:
            with pdf.open_metadata(set_pikepdf_as_editor=False) as meta:
                meta["pdfaid:part"] = "2"
                meta["pdfaid:conformance"] = "B"
                meta["dc:title"] = os.path.splitext(os.path.basename(nom))[0]
            buf = io.BytesIO()
            pdf.save(buf, linearize=True, compress_streams=True)
            out = buf.getvalue()
    except Exception as exc:
        return echec(AG, "PDF vers PDF/A", f"{exc}")
    return Resultat(True, AG, "PDF vers PDF/A",
                    [(dt.safe_name(nom, "pdfa-metadonnees", "pdf"), out)],
                    "Metadonnees PDF/A-2b ajoutees et fichier linearise.",
                    {"moteur": "pikepdf"},
                    ["Ghostscript est absent : ce fichier porte les metadonnees "
                     "PDF/A mais n est pas une conversion certifiee (les polices "
                     "non incorporees ne l ont pas ete). Installe « ghostscript » "
                     "via packages.txt pour une conversion conforme."])


# ===================================================================
# Autres formats -> PDF
# ===================================================================
def _reconstruire_pdf(titre: str, blocs: list[tuple[str, str]],
                      tableaux: list[list] | None = None) -> bytes:
    """blocs = [(style, texte)] avec style dans titre1|titre2|normal|puce."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (ListFlowable, ListItem, Paragraph,
                                    SimpleDocTemplate, Spacer, Table, TableStyle)
    from reportlab.lib import colors

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, title=titre, leftMargin=20 * mm,
                            rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm)
    ss = getSampleStyleSheet()
    st_h1 = ParagraphStyle("h1", parent=ss["Heading1"], fontSize=15, leading=19)
    st_h2 = ParagraphStyle("h2", parent=ss["Heading2"], fontSize=12.5, leading=16)
    st_p = ParagraphStyle("p", parent=ss["BodyText"], fontSize=10, leading=14)

    def esc(s):
        return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

    flow = [Paragraph(esc(titre), st_h1), Spacer(1, 8)]
    puces: list[str] = []

    def vider_puces():
        if puces:
            flow.append(ListFlowable([ListItem(Paragraph(esc(p), st_p)) for p in puces],
                                     bulletType="bullet", start="•", leftIndent=12))
            puces.clear()

    for style, texte in blocs:
        if style == "puce":
            puces.append(texte)
            continue
        vider_puces()
        if style == "titre1":
            flow.append(Paragraph(esc(texte), st_h1))
        elif style == "titre2":
            flow.append(Paragraph(esc(texte), st_h2))
        elif style == "saut":
            flow.append(Spacer(1, 10))
        else:
            flow.append(Paragraph(esc(texte), st_p))
    vider_puces()

    for tab in (tableaux or []):
        if not tab:
            continue
        data_t = [[esc(c)[:120] for c in row] for row in tab[:60]]
        t = Table(data_t, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1EEE8")),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDD7CC")),
            ("FONTSIZE", (0, 0), (-1, -1), 7.5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        flow.append(Spacer(1, 8))
        flow.append(t)

    doc.build(flow)
    return buf.getvalue()


@_t
def word_to_pdf(nom: str, data: bytes, mode: str = "fidelite") -> Resultat:
    if mode == "fidelite":
        out = dt.soffice_convert(data, ".docx", "pdf")
        if out:
            return Resultat(True, AG, "Word vers PDF",
                            [(dt.safe_name(nom, "converti", "pdf"), out)],
                            f"Conversion haute fidelite par LibreOffice, "
                            f"{dt.page_count(out)} page(s).",
                            {"moteur": "libreoffice"})
    import docx
    try:
        d = docx.Document(io.BytesIO(data))
    except Exception as exc:
        return echec(AG, "Word vers PDF", f"fichier Word illisible : {exc}")
    blocs: list[tuple[str, str]] = []
    for p in d.paragraphs:
        txt = (p.text or "").strip()
        if not txt:
            continue
        style = (p.style.name or "").lower() if p.style is not None else ""
        if style.startswith(("heading 1", "titre 1")):
            blocs.append(("titre1", txt))
        elif style.startswith(("heading", "titre")):
            blocs.append(("titre2", txt))
        elif style.startswith(("list", "paragraphe de liste")):
            blocs.append(("puce", txt))
        else:
            blocs.append(("normal", txt))
    tableaux = [[[c.text.strip() for c in row.cells] for row in t.rows]
                for t in d.tables]
    titre = os.path.splitext(os.path.basename(nom))[0]
    out = _reconstruire_pdf(titre, blocs, tableaux)
    return Resultat(True, AG, "Word vers PDF",
                    [(dt.safe_name(nom, "converti", "pdf"), out)],
                    f"{len(blocs)} paragraphe(s) et {len(tableaux)} tableau(x) "
                    f"convertis, {dt.page_count(out)} page(s).",
                    {"moteur": "reconstruction"},
                    [_raison_repli("Le texte, les titres, les listes et les "
                                   "tableaux sont conserves ; polices, colonnes "
                                   "et images ne sont pas reprises.")]
                    if mode == "fidelite" else
                    ["Mode reconstruction demande : sortie recomposee a partir du "
                     "contenu, sans la mise en page d origine."])


@_t
def powerpoint_to_pdf(nom: str, data: bytes, mode: str = "fidelite") -> Resultat:
    if mode == "fidelite":
        out = dt.soffice_convert(data, ".pptx", "pdf")
        if out:
            return Resultat(True, AG, "PowerPoint vers PDF",
                            [(dt.safe_name(nom, "converti", "pdf"), out)],
                            f"Conversion haute fidelite par LibreOffice, "
                            f"{dt.page_count(out)} diapositive(s).",
                            {"moteur": "libreoffice"})
    from pptx import Presentation
    try:
        prs = Presentation(io.BytesIO(data))
    except Exception as exc:
        return echec(AG, "PowerPoint vers PDF", f"fichier illisible : {exc}")
    blocs: list[tuple[str, str]] = []
    n_slides = 0
    for i, slide in enumerate(prs.slides, start=1):
        n_slides = i
        blocs.append(("titre2", f"Diapositive {i}"))
        for sh in slide.shapes:
            if sh.has_text_frame:
                for p in sh.text_frame.paragraphs:
                    if p.text.strip():
                        blocs.append(("puce", p.text.strip()))
        blocs.append(("saut", ""))
    out = _reconstruire_pdf(os.path.splitext(os.path.basename(nom))[0], blocs)
    return Resultat(True, AG, "PowerPoint vers PDF",
                    [(dt.safe_name(nom, "converti", "pdf"), out)],
                    f"{n_slides} diapositive(s) converties, "
                    f"{dt.page_count(out)} page(s).",
                    {"moteur": "reconstruction"},
                    [_raison_repli("Seul le texte des diapositives est repris, "
                                   "sans les visuels ni la mise en page.")]
                    if mode == "fidelite" else
                    ["Mode reconstruction demande : seul le texte est repris."])


@_t
def excel_to_pdf(nom: str, data: bytes, mode: str = "fidelite",
                 max_lignes: int = 400) -> Resultat:
    if mode == "fidelite":
        out = dt.soffice_convert(data, ".xlsx", "pdf")
        if out:
            return Resultat(True, AG, "Excel vers PDF",
                            [(dt.safe_name(nom, "converti", "pdf"), out)],
                            f"Conversion haute fidelite par LibreOffice, "
                            f"{dt.page_count(out)} page(s).",
                            {"moteur": "libreoffice"})
    import openpyxl
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    except Exception as exc:
        return echec(AG, "Excel vers PDF", f"classeur illisible : {exc}")
    blocs: list[tuple[str, str]] = []
    tableaux = []
    for ws in wb.worksheets:
        blocs.append(("titre2", f"Feuille : {ws.title}"))
        rows = []
        for row in ws.iter_rows(values_only=True):
            vals = ["" if v is None else str(v) for v in row]
            if any(vals):
                rows.append(vals[:12])
            if len(rows) >= max_lignes:
                break
        if rows:
            tableaux.append(rows)
    try:
        wb.close()
    except Exception:
        pass
    out = _reconstruire_pdf(os.path.splitext(os.path.basename(nom))[0], blocs, tableaux)
    return Resultat(True, AG, "Excel vers PDF",
                    [(dt.safe_name(nom, "converti", "pdf"), out)],
                    f"{len(tableaux)} feuille(s) converties, "
                    f"{dt.page_count(out)} page(s).",
                    {"moteur": "reconstruction"},
                    [_raison_repli(f"Les 12 premieres colonnes et {max_lignes} "
                                   f"premieres lignes de chaque feuille sont "
                                   f"rendues, sans formules ni mise en forme "
                                   f"conditionnelle.")]
                    if mode == "fidelite" else
                    [f"Mode reconstruction : 12 colonnes et {max_lignes} lignes "
                     f"par feuille au maximum."])


@_t
def jpg_to_pdf(fichiers: list[tuple[str, bytes]], page_size: str = "A4",
               orientation: str = "auto", marge_mm: float = 8.0,
               qualite: int = 92, nom_sortie: str = "images.pdf") -> Resultat:
    from PIL import Image, ImageOps
    imgs = []
    ignores = []
    for nom, data in fichiers:
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
            im = ImageOps.exif_transpose(im).convert("RGB")
            imgs.append(im)
        except Exception:
            ignores.append(nom)
    if not imgs:
        return echec(AG, "JPG vers PDF", "aucune image exploitable")
    out = dt.images_to_pdf(imgs, page_size=page_size, margin_mm=marge_mm,
                           orientation=orientation, quality=qualite)
    avert = [f"{len(ignores)} fichier(s) ignore(s) : {', '.join(ignores[:5])}"] \
        if ignores else []
    return Resultat(True, AG, "JPG vers PDF", [(nom_sortie, out)],
                    f"{len(imgs)} image(s) assemblees, {dt.page_count(out)} page(s), "
                    f"format {page_size}.",
                    {"images": len(imgs)}, avert)


@_t
def html_to_pdf(source: str = "", nom: str = "page.html",
                data: bytes | None = None, titre: str = "") -> Resultat:
    """source : une URL ; data : un fichier HTML televerse."""
    from .extraction import _from_html
    from . import websearch

    if data is None and source:
        if not source.lower().startswith(("http://", "https://")):
            return echec(AG, "HTML vers PDF", "indique une URL complete "
                                              "(https://...) ou televerse un fichier")
        page = websearch.fetch_page(source, max_chars=400000)
        if page["statut"] != "ok":
            return echec(AG, "HTML vers PDF",
                         f"page inaccessible ({page['statut']}). Si le reseau est "
                         f"coupe, televerse le fichier HTML a la place.")
        blocs = [("normal", p) for p in page["texte"].split("\n\n") if p.strip()]
        titre = titre or source
    elif data is not None:
        pages = _from_html(data)
        blocs = []
        for p in pages:
            for ligne in (p.get("text") or "").split("\n\n"):
                ligne = ligne.strip()
                if not ligne:
                    continue
                if ligne.startswith("###"):
                    blocs.append(("titre2", ligne.lstrip("# ").strip()))
                else:
                    blocs.append(("normal", ligne))
        titre = titre or os.path.splitext(os.path.basename(nom))[0]
    else:
        return echec(AG, "HTML vers PDF", "ni URL ni fichier fourni")

    if not blocs:
        return echec(AG, "HTML vers PDF", "aucun contenu textuel trouve")
    out = _reconstruire_pdf(titre, blocs)
    return Resultat(True, AG, "HTML vers PDF",
                    [(dt.safe_name(titre or nom, "converti", "pdf"), out)],
                    f"{len(blocs)} bloc(s) de contenu convertis, "
                    f"{dt.page_count(out)} page(s).",
                    {"source": source or nom},
                    ["Le rendu reprend le contenu textuel et la structure des "
                     "titres, pas la feuille de style du site."])
