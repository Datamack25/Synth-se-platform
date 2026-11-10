"""SYNTHEA - exports : PowerPoint, Word, PDF, Excel, HTML, images, archive ZIP."""
from __future__ import annotations

import io
import os
import zipfile

from . import html_report, imaging, utils
from .models import Chunk, Document, Rendition, SummaryTree

PPT_W, PPT_H = 13.333, 7.5          # 16:9 en pouces


# =====================================================================
# PowerPoint
# =====================================================================
def export_pptx(rend: Rendition, tree: SummaryTree, doc: Document,
                images: dict[str, bytes] | None = None,
                palette: str = "institution",
                max_bullets: int = 5, max_slides: int = 45) -> bytes:
    """max_slides : plafond issu de core.budget, pour qu un livre de 1000 pages
    ne produise pas un deck de 200 diapositives."""
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.util import Emu, Inches, Pt

    pal = imaging.PALETTES.get(palette, imaging.PALETTES["institution"])
    ink = RGBColor(*imaging._hex(pal["fg"]))
    bg = RGBColor(*imaging._hex(pal["bg"]))
    accent = RGBColor(*imaging._hex(pal["accent"]))
    muted = RGBColor(*imaging._hex(pal["muted"]))

    prs = Presentation()
    prs.slide_width = Inches(PPT_W)
    prs.slide_height = Inches(PPT_H)
    blank = prs.slide_layouts[6]

    def paint(slide, color=bg) -> None:
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = color

    def tbox(slide, x, y, w, h, text, size, bold=False, color=ink,
             align="left", spacing=1.08):
        from pptx.enum.text import PP_ALIGN
        tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = tb.text_frame
        tf.word_wrap = True
        lines = text if isinstance(text, list) else [text]
        for i, ln in enumerate(lines):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.text = str(ln)
            p.alignment = {"left": PP_ALIGN.LEFT, "center": PP_ALIGN.CENTER,
                           "right": PP_ALIGN.RIGHT}[align]
            p.line_spacing = spacing
            p.space_after = Pt(8)
            for r in p.runs:
                r.font.size = Pt(size)
                r.font.bold = bold
                r.font.color.rgb = color
        return tb

    def rule(slide, x, y, w, color=accent, h=0.045):
        from pptx.enum.shapes import MSO_SHAPE
        sh = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(y),
                                    Inches(w), Inches(h))
        sh.fill.solid()
        sh.fill.fore_color.rgb = color
        sh.line.fill.background()
        sh.shadow.inherit = False
        return sh

    # ---------------- diapositive de titre ----------------
    s = prs.slides.add_slide(blank)
    paint(s)
    if images and "01-couverture.png" in images:
        s.shapes.add_picture(io.BytesIO(images["01-couverture.png"]), 0, 0,
                            width=prs.slide_width)
    else:
        tbox(s, 0.9, 2.1, 11.5, 2.4, rend.title, 40, True, ink)
        rule(s, 0.9, 4.7, 2.6)
        tbox(s, 0.9, 4.95, 11.0, 1.2,
             [f"{rend.context_label} — {rend.meta.get('public','')}",
              f"{doc.title} · {utils.human_int(doc.n_pages)} pages · {utils.now_fr()}"],
             16, False, muted)

    # ---------------- sommaire ----------------
    s = prs.slides.add_slide(blank)
    paint(s)
    tbox(s, 0.9, 0.6, 11.5, 0.9, "Sommaire", 30, True, ink)
    rule(s, 0.9, 1.5, 1.8)
    tbox(s, 0.9, 1.9, 11.5, 5.0,
         [f"{i + 1}.  {x.get('heading','')}" for i, x in enumerate(rend.sections)],
         18, False, ink, spacing=1.5)

    # ---------------- indicateurs ----------------
    st = tree.stats or {}
    s = prs.slides.add_slide(blank)
    paint(s)
    tbox(s, 0.9, 0.6, 11.5, 0.9, "Le document en chiffres", 30, True, ink)
    rule(s, 0.9, 1.5, 1.8)
    kpis = [("Pages analysees", utils.human_int(st.get("pages", doc.n_pages))),
            ("Mots", utils.human_int(st.get("mots", doc.n_words))),
            ("Sections", str(st.get("sections", len(tree.sections)))),
            ("Themes", str(len(tree.topics)))]
    for i, (lab, val) in enumerate(kpis):
        x = 0.9 + i * 3.05
        from pptx.enum.shapes import MSO_SHAPE
        card = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x),
                                  Inches(2.1), Inches(2.75), Inches(1.75))
        card.fill.solid()
        card.fill.fore_color.rgb = ink
        card.line.color.rgb = accent
        card.shadow.inherit = False
        tbox(s, x + 0.18, 2.28, 2.4, 0.4, lab.upper(), 10, True, bg)
        tbox(s, x + 0.18, 2.75, 2.4, 0.9, val, 28, True, bg)
    if images and "04-themes.png" in images:
        s.shapes.add_picture(io.BytesIO(images["04-themes.png"]), Inches(0.9),
                             Inches(4.2), height=Inches(2.9))

    # ---------------- sections ----------------
    # 3 diapositives de tete + 4 de visuels + 1 de cloture sont reservees
    budget_sections = max(1, max_slides - 8)
    sections_rendues = rend.sections[:budget_sections]
    if len(rend.sections) > budget_sections:
        sections_rendues = rend.sections[:budget_sections]
    for sec in sections_rendues:
        bullets = (sec.get("paragraphs", []) + sec.get("bullets", []))[:max_bullets]
        if not bullets:
            continue
        s = prs.slides.add_slide(blank)
        paint(s)
        tbox(s, 0.9, 0.55, 11.5, 0.9, sec.get("heading", ""), 26, True, ink)
        rule(s, 0.9, 1.42, 1.6)
        tbox(s, 0.9, 1.75, 11.4, 4.9,
             [f"•  {utils.truncate(b, 230)}" for b in bullets], 16, False, ink,
             spacing=1.35)
        if sec.get("ref"):
            tbox(s, 0.9, 6.85, 6.0, 0.4, f"source : {sec['ref']}", 10, False, muted)

    # ---------------- visuels ----------------
    for key, title in (("02-schema-themes.png", "Cartographie des themes"),
                       ("03-nuage-mots.png", "Vocabulaire dominant"),
                       ("05-densite-pages.png", "Couverture du document"),
                       ("07-infographie.png", "Synthese visuelle")):
        if images and key in images:
            s = prs.slides.add_slide(blank)
            paint(s)
            tbox(s, 0.9, 0.5, 11.5, 0.8, title, 24, True, ink)
            pic = s.shapes.add_picture(io.BytesIO(images[key]), Inches(0.9),
                                       Inches(1.45), width=Inches(11.5))
            if pic.height > Emu(int(5.6 * 914400)):
                ratio = (5.6 * 914400) / pic.height
                pic.height = Emu(int(pic.height * ratio))
                pic.width = Emu(int(pic.width * ratio))
                pic.left = Emu(int((prs.slide_width - pic.width) / 2))

    # ---------------- cloture ----------------
    s = prs.slides.add_slide(blank)
    paint(s)
    tbox(s, 0.9, 2.6, 11.5, 1.4, "Points a retenir", 32, True, ink)
    rule(s, 0.9, 4.0, 2.2)
    from . import summarizer
    tbox(s, 0.9, 4.3, 11.4, 2.4,
         [f"•  {utils.truncate(b, 200)}" for b in summarizer.bullet_points(tree, 4)],
         15, False, muted, spacing=1.3)

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


# =====================================================================
# Word
# =====================================================================
def export_docx(rend: Rendition, tree: SummaryTree, doc: Document,
                audit: dict | None = None,
                images: dict[str, bytes] | None = None) -> bytes:
    import docx
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Inches, Pt, RGBColor

    d = docx.Document()
    for sec in d.sections:
        sec.left_margin = sec.right_margin = Inches(1.0)
        sec.top_margin = sec.bottom_margin = Inches(0.9)

    normal = d.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)

    t = d.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.LEFT
    r = t.add_run(rend.title)
    r.bold = True
    r.font.size = Pt(22)

    sub = d.add_paragraph()
    r = sub.add_run(f"{rend.context_label} — {rend.meta.get('public','')}\n"
                    f"{doc.title} · {tree.doc_type} · "
                    f"{utils.human_int(doc.n_pages)} pages · {utils.now_fr()}")
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x44, 0x52, 0x5F)

    if images and "01-couverture.png" in images:
        d.add_picture(io.BytesIO(images["01-couverture.png"]), width=Inches(6.3))

    for s in rend.sections:
        d.add_heading(s.get("heading", ""), level=1)
        for p in s.get("paragraphs", []):
            d.add_paragraph(p)
        for b in s.get("bullets", []):
            d.add_paragraph(b, style="List Bullet")
        if s.get("ref"):
            pr = d.add_paragraph()
            run = pr.add_run(f"source : {s['ref']}")
            run.italic = True
            run.font.size = Pt(8)
            run.font.color.rgb = RGBColor(0x44, 0x52, 0x5F)

    if tree.keywords:
        d.add_heading("Mots-cles du corpus", level=1)
        d.add_paragraph(", ".join(k for k, _ in tree.keywords[:26]))

    if tree.topics:
        d.add_heading("Themes identifies", level=1)
        tb = d.add_table(rows=1, cols=3)
        tb.style = "Light Grid Accent 1"
        hdr = tb.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text = "Theme", "Poids", "Termes"
        for tp in tree.topics:
            c = tb.add_row().cells
            c[0].text = tp["libelle"]
            c[1].text = f"{tp['poids']:.1%}"
            c[2].text = ", ".join(tp["termes"][:6])

    if audit:
        d.add_heading("Verification de couverture (ARGUS)", level=1)
        d.add_paragraph(f"{audit['verdict']} — score global "
                        f"{audit['score']:.1f}/100")
        tb = d.add_table(rows=1, cols=3)
        tb.style = "Light Grid Accent 1"
        hdr = tb.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text = "Controle", "Resultat", "Statut"
        for code, c in audit["controles"].items():
            val = c.get("taux", c.get("n", c.get("unites_extraites", "")))
            row = tb.add_row().cells
            row[0].text = f"{code} · {c['libelle']}"
            row[1].text = f"{val:.1f} %" if isinstance(val, float) else str(val)
            row[2].text = c["statut"]
        d.add_heading("Recommandations", level=2)
        for rec in audit["recommandations"]:
            d.add_paragraph(rec, style="List Bullet")

    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


# =====================================================================
# PDF
# =====================================================================
def export_pdf(rend: Rendition, tree: SummaryTree, doc: Document,
               audit: dict | None = None,
               images: dict[str, bytes] | None = None) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (Image as RLImage, ListFlowable, ListItem,
                                    PageBreak, Paragraph, SimpleDocTemplate,
                                    Spacer, Table, TableStyle)

    buf = io.BytesIO()
    pdf = SimpleDocTemplate(buf, pagesize=A4, title=rend.title,
                            author="SYNTHEA", leftMargin=20 * mm,
                            rightMargin=20 * mm, topMargin=18 * mm,
                            bottomMargin=18 * mm)
    ss = getSampleStyleSheet()
    brand = colors.HexColor("#14504D")
    soft = colors.HexColor("#44525F")
    st_title = ParagraphStyle("T", parent=ss["Title"], fontSize=21, leading=25,
                              alignment=TA_LEFT, textColor=colors.HexColor("#17202A"),
                              spaceAfter=4)
    st_sub = ParagraphStyle("S", parent=ss["Normal"], fontSize=8.5, leading=12,
                            textColor=soft, spaceAfter=14)
    st_h = ParagraphStyle("H", parent=ss["Heading2"], fontSize=12.5, leading=15,
                          textColor=brand, spaceBefore=14, spaceAfter=5)
    st_p = ParagraphStyle("P", parent=ss["BodyText"], fontSize=9.6, leading=14,
                          spaceAfter=6)
    st_ref = ParagraphStyle("R", parent=ss["Normal"], fontSize=7.6, leading=10,
                            textColor=soft, spaceAfter=10)

    def esc(s: str) -> str:
        return (str(s).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;"))

    flow = [Paragraph(esc(rend.title), st_title),
            Paragraph(esc(f"{rend.context_label} — {rend.meta.get('public','')} | "
                          f"{doc.title} · {tree.doc_type} · "
                          f"{utils.human_int(doc.n_pages)} pages · {utils.now_fr()}"),
                      st_sub)]

    if images and "01-couverture.png" in images:
        flow.append(_rl_img(RLImage, images["01-couverture.png"], 170 * mm))
        flow.append(Spacer(1, 8))

    for s in rend.sections:
        flow.append(Paragraph(esc(s.get("heading", "")), st_h))
        for p in s.get("paragraphs", []):
            flow.append(Paragraph(esc(p), st_p))
        if s.get("bullets"):
            flow.append(ListFlowable(
                [ListItem(Paragraph(esc(b), st_p), leftIndent=10)
                 for b in s["bullets"]],
                bulletType="bullet", bulletColor=brand, start="•",
                leftIndent=12))
        if s.get("ref"):
            flow.append(Paragraph(esc(f"source : {s['ref']}"), st_ref))

    if tree.keywords:
        flow.append(Paragraph("Mots-cles du corpus", st_h))
        flow.append(Paragraph(esc(", ".join(k for k, _ in tree.keywords[:26])), st_p))

    if images:
        for key, cap in (("04-themes.png", "Poids des themes"),
                         ("05-densite-pages.png", "Densite de texte par page")):
            if key in images:
                flow.append(Spacer(1, 6))
                flow.append(_rl_img(RLImage, images[key], 165 * mm))
                flow.append(Paragraph(esc(cap), st_ref))

    if audit:
        flow.append(PageBreak())
        flow.append(Paragraph("Verification de couverture (ARGUS)", st_h))
        flow.append(Paragraph(esc(f"{audit['verdict']} — score global "
                                  f"{audit['score']:.1f}/100"), st_p))
        data = [["Controle", "Resultat", "Statut"]]
        for code, c in audit["controles"].items():
            val = c.get("taux", c.get("n", c.get("unites_extraites", "")))
            data.append([f"{code} · {c['libelle']}",
                         f"{val:.1f} %" if isinstance(val, float) else str(val),
                         c["statut"]])
        tbl = Table(data, colWidths=[95 * mm, 35 * mm, 30 * mm])
        tbl.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F1EEE8")),
            ("TEXTCOLOR", (0, 0), (-1, 0), soft),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#DDD7CC")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        flow.append(tbl)
        flow.append(Spacer(1, 10))
        flow.append(Paragraph("Recommandations", st_h))
        flow.append(ListFlowable(
            [ListItem(Paragraph(esc(r), st_p)) for r in audit["recommandations"]],
            bulletType="bullet", bulletColor=brand, start="•", leftIndent=12))

    pdf.build(flow)
    return buf.getvalue()


def _rl_img(RLImage, data: bytes, width):
    from PIL import Image as PILImage
    im = PILImage.open(io.BytesIO(data))
    w, h = im.size
    return RLImage(io.BytesIO(data), width=width, height=width * h / w)


# =====================================================================
# Excel
# =====================================================================
def export_xlsx(doc: Document, chunks: list[Chunk], tree: SummaryTree,
                audit: dict | None = None, page_rows: list[dict] | None = None,
                glossary: list[dict] | None = None) -> bytes:
    import xlsxwriter

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True, "constant_memory": False})
    f_title = wb.add_format({"bold": True, "font_size": 15, "font_color": "#17202A"})
    f_sub = wb.add_format({"font_size": 9, "font_color": "#44525F"})
    f_head = wb.add_format({"bold": True, "bg_color": "#1F6F6B", "font_color": "white",
                            "border": 1, "text_wrap": True, "valign": "top"})
    f_cell = wb.add_format({"border": 1, "text_wrap": True, "valign": "top",
                            "font_size": 9})
    f_num = wb.add_format({"border": 1, "num_format": "#,##0", "font_size": 9})
    f_pct = wb.add_format({"border": 1, "num_format": "0.0 %", "font_size": 9})
    f_ok = wb.add_format({"border": 1, "font_size": 9, "bg_color": "#E7F3EC"})
    f_al = wb.add_format({"border": 1, "font_size": 9, "bg_color": "#F8E9E6"})

    def sheet(name: str, headers: list[str], rows: list[list], widths: list[int]):
        ws = wb.add_worksheet(name[:31])
        ws.freeze_panes(1, 0)
        for i, h in enumerate(headers):
            ws.write(0, i, h, f_head)
            ws.set_column(i, i, widths[i] if i < len(widths) else 16)
        for r, row in enumerate(rows, start=1):
            for c, v in enumerate(row):
                ws.write(r, c, v if v is not None else "",
                         f_num if isinstance(v, (int, float)) else f_cell)
        ws.autofilter(0, 0, max(len(rows), 1), len(headers) - 1)
        return ws

    # ---- synthese ----
    ws = wb.add_worksheet("Synthese")
    ws.set_column(0, 0, 22)
    ws.set_column(1, 1, 96)
    ws.write(0, 0, "SYNTHEA — synthese documentaire", f_title)
    ws.write(1, 0, f"{doc.title} · {tree.doc_type} · {utils.now_fr()}", f_sub)
    st = tree.stats or {}
    rows = [("Pages analysees", st.get("pages", doc.n_pages)),
            ("Mots", st.get("mots", doc.n_words)),
            ("Blocs", st.get("blocs", len(chunks))),
            ("Sections", st.get("sections", len(tree.sections))),
            ("Pages resumees", st.get("pages_resumees", 0)),
            ("Profondeur", st.get("profondeur", "")),
            ("Modele supervise", "oui" if st.get("modele_supervise") else "heuristique"),
            ("Lisibilite", (st.get("lisibilite") or {}).get("niveau", "")),
            ("Score ARGUS", (audit or {}).get("score", "")),
            ("Verdict ARGUS", (audit or {}).get("verdict", ""))]
    r = 3
    for k, v in rows:
        ws.write(r, 0, k, f_head)
        ws.write(r, 1, v, f_cell)
        r += 1
    r += 1
    ws.write(r, 0, "Resume executif", f_head)
    for c in tree.executive:
        r += 1
        ws.write(r, 0, c.ref, f_cell)
        ws.write(r, 1, c.text, f_cell)

    # ---- sections ----
    sheet("Sections",
          ["#", "Section", "Page debut", "Page fin", "Mots-cles", "Constats"],
          [[i + 1, s.title, s.page_start, s.page_end, ", ".join(s.keywords),
            len(s.claims)] for i, s in enumerate(tree.sections)],
          [5, 46, 12, 12, 42, 10])

    # ---- constats ----
    sheet("Constats",
          ["Reference", "Pages", "Bloc", "Score", "Constat"],
          [[c.ref, ";".join(map(str, c.pages)), c.chunk_id, round(c.score, 4), c.text]
           for c in tree.all_claims],
          [14, 14, 8, 9, 110])

    # ---- pages ----
    if page_rows:
        heads = list(page_rows[0].keys())
        sheet("Controle pages", heads,
              [[row.get(h, "") for h in heads] for row in page_rows],
              [8, 26, 11, 8, 6, 14, 30, 11, 60, 30, 14])

    # ---- themes et mots-cles ----
    sheet("Themes", ["Theme", "Poids", "Termes caracteristiques"],
          [[t["libelle"], t["poids"], ", ".join(t["termes"])] for t in tree.topics],
          [36, 10, 80])
    sheet("Mots-cles", ["Terme", "Poids TF-IDF"],
          [[k, round(v, 4)] for k, v in tree.keywords], [40, 14])

    # ---- entites ----
    ent_rows = []
    for cat, vals in (tree.entities or {}).items():
        for v in vals:
            ent_rows.append([cat, v])
    sheet("Entites", ["Categorie", "Valeur"], ent_rows, [22, 60])

    # ---- glossaire ----
    if glossary:
        heads = list(glossary[0].keys())
        sheet("Glossaire 5 langues", heads,
              [[g.get(h, "") for h in heads] for g in glossary],
              [30, 12, 60, 24, 24, 24, 24, 22, 24])

    # ---- audit ----
    if audit:
        wsa = wb.add_worksheet("ARGUS")
        wsa.set_column(0, 0, 34)
        wsa.set_column(1, 1, 18)
        wsa.set_column(2, 2, 14)
        wsa.set_column(3, 3, 70)
        wsa.write(0, 0, "Verification ARGUS", f_title)
        wsa.write(1, 0, f"{audit['verdict']} — score {audit['score']:.1f}/100", f_sub)
        for i, h in enumerate(["Controle", "Resultat", "Statut", "Detail"]):
            wsa.write(3, i, h, f_head)
        r = 4
        for code, c in audit["controles"].items():
            val = c.get("taux", c.get("n", c.get("unites_extraites", "")))
            wsa.write(r, 0, f"{code} · {c['libelle']}", f_cell)
            wsa.write(r, 1, val if isinstance(val, (int, float)) else str(val), f_cell)
            wsa.write(r, 2, c["statut"], f_ok if c["statut"] == "ok" else f_al)
            wsa.write(r, 3, c.get("commentaire", ""), f_cell)
            r += 1
        r += 1
        wsa.write(r, 0, "Recommandations", f_head)
        for rec in audit["recommandations"]:
            r += 1
            wsa.write(r, 0, "", f_cell)
            wsa.write(r, 3, rec, f_cell)

    wb.close()
    return buf.getvalue()


# =====================================================================
# HTML / images / archive
# =====================================================================
def export_html(rend: Rendition, tree: SummaryTree, doc: Document,
                audit: dict | None = None,
                images: dict[str, bytes] | None = None) -> bytes:
    return html_report.render_report(rend, tree, doc.title, audit,
                                     images).encode("utf-8")


def export_markdown(rend: Rendition) -> bytes:
    return rend.to_markdown().encode("utf-8")


def export_images_zip(images: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in images.items():
            z.writestr(name, data)
    return buf.getvalue()


def export_bundle(files: dict[str, bytes]) -> bytes:
    """Archive complete : tous les livrables en un seul telechargement."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            if data:
                z.writestr(name, data)
    return buf.getvalue()


def save_local(name: str, data: bytes) -> str:
    os.makedirs(utils.EXPORTS, exist_ok=True)
    path = os.path.join(utils.EXPORTS, name)
    with open(path, "wb") as fh:
        fh.write(data)
    return path
