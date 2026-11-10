"""SYNTHEA - socle commun des cinq agents de transformation documentaire.

Contient le type de resultat partage, la detection des capacites reelles de
l environnement, et les primitives bas niveau (ouverture, sauvegarde,
rasterisation, superposition de calques) utilisees par FORGE, MOSAIQUE,
ATOME, SCEAU et COLLATEUR.

Regle de conduite : aucune operation ne pretend avoir reussi ce qu elle n a
pas fait. Quand une brique manque (Ghostscript, LibreOffice, tesseract), le
resultat le dit et propose la voie de repli reellement empruntee.
"""
from __future__ import annotations

import io
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field

from . import utils

MAX_RENDER_PAGES = 400          # garde-fou sur les operations qui rasterisent


# ===================================================================
# Resultat d operation
# ===================================================================
@dataclass
class Resultat:
    ok: bool
    agent: str
    operation: str
    fichiers: list[tuple[str, bytes]] = field(default_factory=list)
    message: str = ""
    details: dict = field(default_factory=dict)
    avertissements: list[str] = field(default_factory=list)
    duree: float = 0.0

    @property
    def poids_total(self) -> int:
        return sum(len(d) for _, d in self.fichiers)

    def resume(self) -> str:
        if not self.ok:
            return f"✖ {self.operation} : {self.message}"
        n = len(self.fichiers)
        return (f"✔ {self.operation} — {n} fichier(s), "
                f"{self.poids_total / 1024:.0f} Ko. {self.message}")


def echec(agent: str, operation: str, message: str, **details) -> Resultat:
    return Resultat(False, agent, operation, [], message, details)


# ===================================================================
# Capacites de l environnement
# ===================================================================
def _bin(name: str) -> str | None:
    return shutil.which(name)


def capabilities() -> dict:
    return {
        "pypdf": utils.has_module("pypdf"),
        "pikepdf": utils.has_module("pikepdf"),
        "pypdfium2": utils.has_module("pypdfium2"),
        "pdfplumber": utils.has_module("pdfplumber"),
        "reportlab": utils.has_module("reportlab"),
        "docx": utils.has_module("docx"),
        "pptx": utils.has_module("pptx"),
        "openpyxl": utils.has_module("openpyxl"),
        "ocr": utils.has_module("pytesseract") and bool(_bin("tesseract")),
        "libreoffice": bool(_bin("soffice") or _bin("libreoffice")),
        "ghostscript": bool(_bin("gs")),
        "qpdf": bool(_bin("qpdf")),
    }


def capability_rows() -> list[dict]:
    libelles = {
        "pypdf": "Lecture et assemblage PDF",
        "pikepdf": "Compression, reparation, chiffrement",
        "pypdfium2": "Rendu des pages en image",
        "pdfplumber": "Extraction de texte et de tableaux",
        "reportlab": "Generation de PDF",
        "docx": "Lecture et ecriture Word",
        "pptx": "Lecture et ecriture PowerPoint",
        "openpyxl": "Lecture et ecriture Excel",
        "ocr": "OCR (tesseract)",
        "libreoffice": "Conversion bureautique haute fidelite",
        "ghostscript": "Conversion PDF/A certifiee",
        "qpdf": "Reparation de structure PDF",
    }
    caps = capabilities()
    essentiels = {"pypdf", "pikepdf", "pypdfium2", "pdfplumber", "reportlab",
                  "docx", "pptx", "openpyxl"}
    return [{"brique": libelles.get(k, k),
             "module": k,
             "etat": "disponible" if v else "absent",
             "criticite": "indispensable" if k in essentiels else "optionnel"}
            for k, v in caps.items()]


# ===================================================================
# Primitives PDF
# ===================================================================
def open_pdf(data: bytes, password: str | None = None):
    """Ouvre un PDF avec pikepdf (prioritaire) et retourne l objet."""
    import pikepdf
    return pikepdf.open(io.BytesIO(data), password=password or "",
                        allow_overwriting_input=False)


def save_pdf(pdf, **kw) -> bytes:
    buf = io.BytesIO()
    pdf.save(buf, **kw)
    return buf.getvalue()


def reader(data: bytes, password: str | None = None):
    from pypdf import PdfReader
    r = PdfReader(io.BytesIO(data))
    if r.is_encrypted:
        r.decrypt(password or "")
    return r


def writer_bytes(w) -> bytes:
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def page_count(data: bytes) -> int:
    try:
        return len(reader(data).pages)
    except Exception:
        try:
            with open_pdf(data) as pdf:
                return len(pdf.pages)
        except Exception:
            return 0


def is_encrypted(data: bytes) -> bool:
    try:
        from pypdf import PdfReader
        return PdfReader(io.BytesIO(data)).is_encrypted
    except Exception:
        return False


def render_pages(data: bytes, pages: list[int] | None = None, dpi: int = 150,
                 password: str | None = None):
    """Rend les pages demandees en images PIL. pages : 1-based, None = toutes."""
    import pypdfium2 as pdfium
    doc = pdfium.PdfDocument(io.BytesIO(data), password=password or None)
    try:
        n = len(doc)
        idx = [p - 1 for p in (pages or range(1, n + 1)) if 1 <= p <= n]
        scale = dpi / 72.0
        out = []
        for i in idx[:MAX_RENDER_PAGES]:
            page = doc[i]
            try:
                out.append((i + 1, page.render(scale=scale).to_pil().convert("RGB")))
            finally:
                page.close()
        return out
    finally:
        doc.close()


def images_to_pdf(images, page_size: str = "auto", margin_mm: float = 0.0,
                  orientation: str = "auto", quality: int = 92) -> bytes:
    """Assemble une liste d images PIL en un PDF."""
    from reportlab.lib.pagesizes import A4, letter, landscape, portrait
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    m = margin_mm * mm
    for img in images:
        iw, ih = img.size
        if page_size == "auto":
            pw, ph = iw + 2 * m, ih + 2 * m
        else:
            base = A4 if page_size == "A4" else letter
            if orientation == "paysage":
                base = landscape(base)
            elif orientation == "portrait":
                base = portrait(base)
            elif iw > ih:
                base = landscape(base)
            pw, ph = base
        c.setPageSize((pw, ph))
        aw, ah = pw - 2 * m, ph - 2 * m
        ratio = min(aw / iw, ah / ih)
        w, h = iw * ratio, ih * ratio
        tmp = io.BytesIO()
        img.convert("RGB").save(tmp, format="JPEG", quality=quality, optimize=True)
        tmp.seek(0)
        from reportlab.lib.utils import ImageReader
        c.drawImage(ImageReader(tmp), (pw - w) / 2, (ph - h) / 2, w, h)
        c.showPage()
    c.save()
    return buf.getvalue()


def overlay(base_pdf: bytes, layer_pdf: bytes, pages: list[int] | None = None,
            under: bool = False) -> bytes:
    """Superpose un calque PDF sur les pages choisies du document de base."""
    from pypdf import PdfReader, PdfWriter
    base = PdfReader(io.BytesIO(base_pdf))
    lay = PdfReader(io.BytesIO(layer_pdf))
    w = PdfWriter()
    for i, page in enumerate(base.pages, start=1):
        if pages is None or i in pages:
            stamp = lay.pages[min(i - 1, len(lay.pages) - 1)]
            if under:
                newp = stamp
                newp.merge_page(page)
                page = newp
            else:
                page.merge_page(stamp)
        w.add_page(page)
    return writer_bytes(w)


def blank_layer(width: float, height: float, draw_fn) -> bytes:
    """Cree un calque PDF d une page et laisse draw_fn(canvas) dessiner."""
    from reportlab.pdfgen import canvas
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(width, height))
    draw_fn(c)
    c.showPage()
    c.save()
    return buf.getvalue()


def page_sizes(data: bytes) -> list[tuple[float, float]]:
    r = reader(data)
    out = []
    for p in r.pages:
        box = p.mediabox
        out.append((float(box.width), float(box.height)))
    return out


# ===================================================================
# Conversion bureautique via LibreOffice (quand il est installe)
# ===================================================================
def soffice_convert(data: bytes, src_ext: str, target: str,
                    timeout: int = 180) -> bytes | None:
    """Conversion haute fidelite via LibreOffice. None si indisponible."""
    exe = _bin("soffice") or _bin("libreoffice")
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, f"entree{src_ext}")
        with open(src, "wb") as fh:
            fh.write(data)
        try:
            subprocess.run(
                [exe, "--headless", "--norestore", "--invisible",
                 "--convert-to", target, "--outdir", td, src],
                check=True, timeout=timeout,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            return None
        ext = target.split(":")[0]
        out = os.path.join(td, f"entree.{ext}")
        if not os.path.exists(out):
            cands = [f for f in os.listdir(td) if f.endswith(f".{ext}")]
            if not cands:
                return None
            out = os.path.join(td, cands[0])
        with open(out, "rb") as fh:
            return fh.read()


def gs_convert_pdfa(data: bytes, timeout: int = 180) -> bytes | None:
    """Conversion PDF/A-2b par Ghostscript. None si gs est absent."""
    exe = _bin("gs")
    if not exe:
        return None
    with tempfile.TemporaryDirectory() as td:
        src, dst = os.path.join(td, "in.pdf"), os.path.join(td, "out.pdf")
        with open(src, "wb") as fh:
            fh.write(data)
        try:
            subprocess.run(
                [exe, "-dPDFA=2", "-dBATCH", "-dNOPAUSE", "-dQUIET",
                 "-sColorConversionStrategy=UseDeviceIndependentColor",
                 "-sDEVICE=pdfwrite", "-dPDFACompatibilityPolicy=1",
                 f"-sOutputFile={dst}", src],
                check=True, timeout=timeout,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            return None
        if not os.path.exists(dst):
            return None
        with open(dst, "rb") as fh:
            return fh.read()


# ===================================================================
# Utilitaires de selection de pages
# ===================================================================
def parse_pages(spec: str, total: int) -> list[int]:
    """« 1-3, 7, 12- » -> [1,2,3,7,12,...]. Vide = toutes les pages."""
    spec = (spec or "").strip()
    if not spec:
        return list(range(1, total + 1))
    out: list[int] = []
    for part in spec.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            a, _, b = part.partition("-")
            try:
                start = int(a) if a.strip() else 1
                end = int(b) if b.strip() else total
            except ValueError:
                continue
            out.extend(range(max(1, start), min(total, end) + 1))
        else:
            try:
                p = int(part)
            except ValueError:
                continue
            if 1 <= p <= total:
                out.append(p)
    return sorted(set(out))


def safe_name(name: str, suffix: str, ext: str) -> str:
    base = os.path.splitext(os.path.basename(name or "document"))[0]
    return f"{utils.slugify(base, 50)}-{suffix}.{ext.lstrip('.')}"
