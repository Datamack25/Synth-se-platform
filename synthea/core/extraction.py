"""SYNTHEA - Agent ATLAS : extraction multi-format avec pagination fidele.

Formats pris en charge :
  PDF (texte + OCR optionnel), DOCX, PPTX, XLSX/XLSM, CSV/TSV, HTML/HTM,
  TXT/MD, JPEG/PNG/TIFF/BMP/WEBP (OCR), JSON, EPUB, ZIP (contenu).

Chaque unite logique du fichier devient une Page :
  - PDF   : une page = une page
  - PPTX  : une page = une diapositive
  - XLSX  : une page = une feuille (ou un bloc de 200 lignes)
  - DOCX  : une page = une section de ~2800 caracteres (coupe aux titres)
  - HTML  : une page = une section <h1>/<h2> ou un bloc de 2800 caracteres
  - image : une page = l image (OCR si disponible)
"""
from __future__ import annotations

import csv
import io
import json
import os
import re
import zipfile

from . import utils
from .models import Document, Page

TEXT_PAGE_CHARS = 2800

SUPPORTED = {
    ".pdf", ".docx", ".doc", ".pptx", ".ppt", ".xlsx", ".xlsm", ".xls",
    ".csv", ".tsv", ".html", ".htm", ".txt", ".md", ".markdown", ".json",
    ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".gif",
    ".epub", ".zip", ".rtf",
}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".gif"}


# ------------------------------------------------------------- capacites
def capabilities() -> dict[str, bool]:
    return {
        "pdf": utils.has_module("pypdf"),
        "pdf_avance": utils.has_module("pdfplumber"),
        "docx": utils.has_module("docx"),
        "pptx": utils.has_module("pptx"),
        "xlsx": utils.has_module("openpyxl"),
        "html": utils.has_module("bs4"),
        "image": utils.has_module("PIL"),
        "ocr": utils.has_module("pytesseract") and _tesseract_ready(),
    }


def _tesseract_ready() -> bool:
    try:
        import pytesseract
        pytesseract.get_tesseract_version()
        return True
    except Exception:
        return False


# --------------------------------------------------------------- helpers
def _paginate_text(txt: str, size: int = TEXT_PAGE_CHARS) -> list[str]:
    """Decoupe un texte long en blocs, en respectant les paragraphes."""
    txt = utils.clean_text(txt)
    if not txt:
        return []
    blocks, cur = [], []
    cur_len = 0
    for para in txt.split("\n\n"):
        p = para.strip()
        if not p:
            continue
        if cur_len + len(p) > size and cur:
            blocks.append("\n\n".join(cur))
            cur, cur_len = [], 0
        cur.append(p)
        cur_len += len(p) + 2
        # paragraphe geant : on le coupe
        while cur_len > size * 2:
            joined = "\n\n".join(cur)
            blocks.append(joined[:size])
            rest = joined[size:]
            cur, cur_len = ([rest] if rest else []), len(rest)
    if cur:
        blocks.append("\n\n".join(cur))
    return blocks


def _ocr_image(data: bytes, langs: str = "fra+eng") -> tuple[str, str]:
    """Retourne (texte, avertissement)."""
    if not utils.has_module("PIL"):
        return "", "Pillow absent : image non lue"
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception as exc:
        return "", f"image illisible ({exc.__class__.__name__})"
    if not (utils.has_module("pytesseract") and _tesseract_ready()):
        w, h = img.size
        return "", f"OCR indisponible (image {w}x{h}) : installer pytesseract + tesseract-ocr"
    try:
        import pytesseract
        if img.mode not in ("L", "RGB"):
            img = img.convert("RGB")
        txt = pytesseract.image_to_string(img, lang=langs)
        return utils.clean_text(txt), "" if txt.strip() else "OCR sans texte detecte"
    except Exception as exc:
        return "", f"echec OCR : {exc}"


# ------------------------------------------------------- extracteurs par format
def _from_pdf(data: bytes, name: str, ocr: bool, langs: str) -> list[dict]:
    out: list[dict] = []
    text_by_page: list[str] = []
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data))
        for pg in reader.pages:
            try:
                text_by_page.append(utils.clean_text(pg.extract_text() or ""))
            except Exception:
                text_by_page.append("")
    except Exception as exc:
        if utils.has_module("pdfplumber"):
            try:
                import pdfplumber
                with pdfplumber.open(io.BytesIO(data)) as pdf:
                    for pg in pdf.pages:
                        text_by_page.append(utils.clean_text(pg.extract_text() or ""))
            except Exception as exc2:
                return [{"text": "", "unit": "page", "native": 1,
                         "warning": f"PDF illisible : {exc2}"}]
        else:
            return [{"text": "", "unit": "page", "native": 1,
                     "warning": f"PDF illisible : {exc}"}]

    # pages vides : tentative d OCR si demande
    for i, txt in enumerate(text_by_page, start=1):
        warn = ""
        if not txt and ocr:
            img_txt, warn = _render_pdf_page_ocr(data, i, langs)
            if img_txt:
                out.append({"text": img_txt, "unit": "page", "native": i,
                            "ocr": True, "warning": ""})
                continue
        if not txt and not warn:
            warn = "page sans texte extractible (probablement numerisee)"
        out.append({"text": txt, "unit": "page", "native": i, "warning": warn})
    return out


def _render_pdf_page_ocr(data: bytes, page_no: int, langs: str) -> tuple[str, str]:
    """OCR d une page PDF via pdfplumber (rendu bitmap) si disponible."""
    if not utils.has_module("pdfplumber"):
        return "", "OCR PDF indisponible (pdfplumber absent)"
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            pg = pdf.pages[page_no - 1]
            im = pg.to_image(resolution=200).original
            buf = io.BytesIO()
            im.save(buf, format="PNG")
            return _ocr_image(buf.getvalue(), langs)
    except Exception as exc:
        return "", f"OCR page {page_no} impossible : {exc.__class__.__name__}"


def _from_docx(data: bytes) -> list[dict]:
    try:
        import docx
    except Exception:
        return [{"text": "", "unit": "section", "native": 1,
                 "warning": "python-docx absent"}]
    try:
        d = docx.Document(io.BytesIO(data))
    except Exception as exc:
        return [{"text": "", "unit": "section", "native": 1,
                 "warning": f"DOCX illisible : {exc}"}]

    parts: list[str] = []
    for p in d.paragraphs:
        t = (p.text or "").strip()
        if not t:
            continue
        style = (p.style.name or "").lower() if p.style is not None else ""
        if style.startswith(("heading", "titre")):
            parts.append(f"\n\n### {t}")
        else:
            parts.append(t)
    for tb in d.tables:
        rows = []
        for row in tb.rows:
            cells = [c.text.strip().replace("\n", " ") for c in row.cells]
            if any(cells):
                rows.append(" | ".join(cells))
        if rows:
            parts.append("\n\n[tableau]\n" + "\n".join(rows))

    blocks = _paginate_text("\n\n".join(parts))
    return [{"text": b, "unit": "section", "native": i}
            for i, b in enumerate(blocks, start=1)] or \
           [{"text": "", "unit": "section", "native": 1, "warning": "document vide"}]


def _from_pptx(data: bytes) -> list[dict]:
    try:
        from pptx import Presentation
    except Exception:
        return [{"text": "", "unit": "diapositive", "native": 1,
                 "warning": "python-pptx absent"}]
    try:
        prs = Presentation(io.BytesIO(data))
    except Exception as exc:
        return [{"text": "", "unit": "diapositive", "native": 1,
                 "warning": f"PPTX illisible : {exc}"}]

    out = []
    for i, slide in enumerate(prs.slides, start=1):
        chunks = []
        for sh in slide.shapes:
            if sh.has_text_frame:
                t = "\n".join(p.text for p in sh.text_frame.paragraphs if p.text)
                if t.strip():
                    chunks.append(t.strip())
            if getattr(sh, "has_table", False):
                try:
                    rows = [" | ".join(c.text.strip() for c in r.cells)
                            for r in sh.table.rows]
                    chunks.append("[tableau]\n" + "\n".join(rows))
                except Exception:
                    pass
        try:
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
                chunks.append("[notes] " + slide.notes_slide.notes_text_frame.text.strip())
        except Exception:
            pass
        txt = utils.clean_text("\n\n".join(chunks))
        out.append({"text": txt, "unit": "diapositive", "native": i,
                    "warning": "" if txt else "diapositive sans texte"})
    return out


def _from_xlsx(data: bytes) -> list[dict]:
    try:
        import openpyxl
    except Exception:
        return [{"text": "", "unit": "feuille", "native": 1,
                 "warning": "openpyxl absent"}]
    try:
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True, read_only=True)
    except Exception as exc:
        return [{"text": "", "unit": "feuille", "native": 1,
                 "warning": f"classeur illisible : {exc}"}]

    out, n = [], 0
    for ws in wb.worksheets:
        lines, buf = [], []
        for row in ws.iter_rows(values_only=True):
            vals = ["" if v is None else str(v).strip() for v in row]
            if any(vals):
                buf.append(" | ".join(vals))
            if len(buf) >= 200:
                lines.append(buf)
                buf = []
        if buf:
            lines.append(buf)
        if not lines:
            n += 1
            out.append({"text": "", "unit": "feuille", "native": n,
                        "warning": f"feuille '{ws.title}' vide"})
            continue
        for k, block in enumerate(lines, start=1):
            n += 1
            head = f"[feuille {ws.title}" + (f" - bloc {k}]" if len(lines) > 1 else "]")
            out.append({"text": head + "\n" + "\n".join(block),
                        "unit": "feuille", "native": n})
    try:
        wb.close()
    except Exception:
        pass
    return out


def _from_csv(data: bytes, delim: str | None = None) -> list[dict]:
    txt = _decode(data)
    sample = txt[:4000]
    if delim is None:
        try:
            delim = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
        except Exception:
            delim = ";" if sample.count(";") > sample.count(",") else ","
    rows = list(csv.reader(io.StringIO(txt), delimiter=delim))
    out, n = [], 0
    header = " | ".join(rows[0]) if rows else ""
    for block in utils.chunked(rows[1:] if rows else [], 200):
        n += 1
        body = "\n".join(" | ".join(r) for r in block)
        out.append({"text": f"[donnees tabulaires - bloc {n}]\n{header}\n{body}",
                    "unit": "feuille", "native": n})
    return out or [{"text": header, "unit": "feuille", "native": 1}]


def _from_html(data: bytes) -> list[dict]:
    txt = _decode(data)
    if utils.has_module("bs4"):
        from bs4 import BeautifulSoup
        try:
            soup = BeautifulSoup(txt, "lxml")
        except Exception:
            soup = BeautifulSoup(txt, "html.parser")
        for tag in soup(["script", "style", "noscript", "svg", "nav", "footer"]):
            tag.decompose()
        title = (soup.title.get_text(strip=True) if soup.title else "")
        parts, cur = [], ([f"### {title}"] if title else [])
        for el in soup.find_all(["h1", "h2", "h3", "p", "li", "td", "th",
                                 "blockquote", "pre", "caption"]):
            t = el.get_text(" ", strip=True)
            if not t:
                continue
            if el.name in ("h1", "h2"):
                if cur:
                    parts.append("\n\n".join(cur))
                cur = [f"### {t}"]
            else:
                cur.append(f"### {t}" if el.name == "h3" else t)
        if cur:
            parts.append("\n\n".join(cur))
        content = "\n\n".join(parts)
    else:
        content = re.sub(r"<[^>]+>", " ", txt)

    blocks = _paginate_text(content)
    return [{"text": b, "unit": "section", "native": i}
            for i, b in enumerate(blocks, start=1)] or \
           [{"text": "", "unit": "section", "native": 1, "warning": "page HTML vide"}]


def _from_epub(data: bytes) -> list[dict]:
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
    except Exception as exc:
        return [{"text": "", "unit": "section", "native": 1,
                 "warning": f"EPUB illisible : {exc}"}]
    names = sorted(n for n in zf.namelist()
                   if n.lower().endswith((".xhtml", ".html", ".htm")))
    out, n = [], 0
    for nm in names:
        try:
            pages = _from_html(zf.read(nm))
        except Exception:
            continue
        for p in pages:
            if p.get("text"):
                n += 1
                p["native"] = n
                out.append(p)
    return out or [{"text": "", "unit": "section", "native": 1,
                    "warning": "EPUB sans contenu textuel"}]


def _from_json(data: bytes) -> list[dict]:
    txt = _decode(data)
    try:
        obj = json.loads(txt)
        pretty = json.dumps(obj, ensure_ascii=False, indent=1)
    except Exception:
        pretty = txt
    blocks = _paginate_text(pretty)
    return [{"text": b, "unit": "section", "native": i}
            for i, b in enumerate(blocks, start=1)]


def _from_txt(data: bytes) -> list[dict]:
    blocks = _paginate_text(_decode(data))
    return [{"text": b, "unit": "page", "native": i}
            for i, b in enumerate(blocks, start=1)] or \
           [{"text": "", "unit": "page", "native": 1, "warning": "fichier vide"}]


def _from_rtf(data: bytes) -> list[dict]:
    txt = _decode(data)
    txt = re.sub(r"\\[a-zA-Z]+-?\d* ?", " ", txt)
    txt = txt.replace("{", " ").replace("}", " ")
    return _from_txt(txt.encode("utf-8"))


def _decode(data: bytes) -> str:
    if utils.has_module("chardet"):
        try:
            import chardet
            enc = chardet.detect(data[:40000]).get("encoding") or "utf-8"
            return data.decode(enc, "replace")
        except Exception:
            pass
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return data.decode(enc)
        except Exception:
            continue
    return data.decode("utf-8", "replace")


# ------------------------------------------------------------- API publique
def extract_file(data: bytes, filename: str, ocr: bool = True,
                 ocr_langs: str = "fra+eng") -> list[dict]:
    """Retourne une liste d unites logiques brutes pour un fichier."""
    ext = os.path.splitext(filename.lower())[1]
    if ext == ".pdf":
        return _from_pdf(data, filename, ocr, ocr_langs)
    if ext in (".docx", ".doc"):
        return _from_docx(data)
    if ext in (".pptx", ".ppt"):
        return _from_pptx(data)
    if ext in (".xlsx", ".xlsm", ".xls"):
        return _from_xlsx(data)
    if ext == ".csv":
        return _from_csv(data)
    if ext == ".tsv":
        return _from_csv(data, "\t")
    if ext in (".html", ".htm"):
        return _from_html(data)
    if ext == ".json":
        return _from_json(data)
    if ext == ".epub":
        return _from_epub(data)
    if ext == ".rtf":
        return _from_rtf(data)
    if ext in IMAGE_EXT:
        txt, warn = _ocr_image(data, ocr_langs) if ocr else ("", "OCR desactive")
        return [{"text": txt, "unit": "image", "native": 1, "ocr": bool(txt),
                 "warning": warn}]
    if ext == ".zip":
        out, n = [], 0
        try:
            zf = zipfile.ZipFile(io.BytesIO(data))
        except Exception as exc:
            return [{"text": "", "unit": "page", "native": 1,
                     "warning": f"archive illisible : {exc}"}]
        for nm in sorted(zf.namelist()):
            if nm.endswith("/") or os.path.splitext(nm.lower())[1] not in SUPPORTED:
                continue
            try:
                for p in extract_file(zf.read(nm), nm, ocr, ocr_langs):
                    n += 1
                    p["native"] = n
                    p["text"] = f"[{os.path.basename(nm)}]\n" + (p.get("text") or "")
                    out.append(p)
            except Exception:
                continue
        return out or [{"text": "", "unit": "page", "native": 1,
                        "warning": "archive sans fichier exploitable"}]
    # format inconnu : tentative texte
    return _from_txt(data)


def build_document(files: list[tuple[str, bytes]], title: str = "",
                   ocr: bool = True, ocr_langs: str = "fra+eng",
                   max_pages: int = 2000,
                   progress=None) -> Document:
    """Assemble un Document pagine a partir d un ou plusieurs fichiers.

    files      : liste de (nom, contenu binaire)
    max_pages  : garde-fou (2000 pages par defaut)
    progress   : callable(fraction, message)
    """
    doc = Document(
        doc_id=utils.short_sha("".join(n for n, _ in files) + utils.stamp(), 12),
        title=title or (os.path.splitext(files[0][0])[0] if files else "Document"),
    )
    index = 0
    truncated = False

    for fi, (name, data) in enumerate(files):
        if progress:
            progress(fi / max(len(files), 1), f"extraction : {name}")
        try:
            units = extract_file(data, name, ocr, ocr_langs)
        except Exception as exc:                        # pragma: no cover
            units = [{"text": "", "unit": "page", "native": 1,
                      "warning": f"echec extraction : {exc}"}]

        kept = 0
        for u in units:
            if index >= max_pages:
                truncated = True
                break
            index += 1
            kept += 1
            doc.pages.append(Page(
                index=index,
                text=u.get("text", "") or "",
                source_file=name,
                unit=u.get("unit", "page"),
                native_index=int(u.get("native", kept)),
                ocr=bool(u.get("ocr", False)),
                warning=u.get("warning", "") or "",
            ))
        doc.files.append({
            "nom": name,
            "extension": os.path.splitext(name.lower())[1],
            "octets": len(data),
            "unites": kept,
            "unite_type": units[0].get("unit", "page") if units else "page",
            "sha1": utils.short_sha(str(len(data)) + name, 10),
        })
        if truncated:
            break

    doc.meta.update({
        "extrait_le": utils.now_fr(),
        "max_pages": max_pages,
        "tronque": truncated,
        "ocr_actif": bool(ocr and capabilities()["ocr"]),
        "capacites": capabilities(),
        "n_fichiers": len(doc.files),
    })
    if progress:
        progress(1.0, f"{doc.n_pages} unites extraites")
    return doc
