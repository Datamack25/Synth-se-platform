"""SYNTHEA - agents MOSAIQUE, ATOME et SCEAU.

MOSAIQUE  organiser : fusionner, diviser, extraire, reordonner, pivoter,
                      recadrer, numeroter.
ATOME     optimiser : compresser, reparer, OCR, scan vers PDF.
SCEAU     securiser : proteger, deverrouiller, filigraner, caviarder, signer,
                      annoter.
"""
from __future__ import annotations

import io
import time

from . import doctools as dt
from . import utils
from .doctools import Resultat, echec


def _t(fn):
    """Mesure la duree d une operation et la place dans le resultat."""
    def wrap(*a, **k) -> Resultat:
        t0 = time.time()
        try:
            r = fn(*a, **k)
        except Exception as exc:                       # pragma: no cover
            r = echec("?", fn.__name__, f"{exc.__class__.__name__}: {exc}")
        r.duree = round(time.time() - t0, 2)
        return r
    return wrap


# ===================================================================
# MOSAIQUE - organiser
# ===================================================================
AG = "MOSAIQUE"


@_t
def merge_pdf(fichiers: list[tuple[str, bytes]], ordre: list[int] | None = None,
              nom_sortie: str = "fusion.pdf") -> Resultat:
    """Fusionne plusieurs PDF dans l ordre indique."""
    from pypdf import PdfWriter
    if len(fichiers) < 2:
        return echec(AG, "Fusionner", "il faut au moins deux fichiers PDF")
    seq = [fichiers[i] for i in ordre] if ordre else fichiers
    w = PdfWriter()
    detail = []
    for nom, data in seq:
        try:
            r = dt.reader(data)
        except Exception as exc:
            return echec(AG, "Fusionner", f"« {nom} » illisible : {exc}")
        for p in r.pages:
            w.add_page(p)
        detail.append({"fichier": nom, "pages": len(r.pages)})
    out = dt.writer_bytes(w)
    return Resultat(True, AG, "Fusionner", [(nom_sortie, out)],
                    f"{len(seq)} documents fusionnes, "
                    f"{dt.page_count(out)} pages au total.",
                    {"ordre": [n for n, _ in seq], "detail": detail})


@_t
def split_pdf(nom: str, data: bytes, mode: str = "plages",
              plages: str = "", toutes_les: int = 1) -> Resultat:
    """mode : 'plages' (1-3,7), 'une_par_page', 'par_paquet' (toutes_les N)."""
    from pypdf import PdfWriter
    total = dt.page_count(data)
    if not total:
        return echec(AG, "Diviser", "PDF illisible ou vide")
    r = dt.reader(data)
    sorties: list[tuple[str, bytes]] = []

    if mode == "une_par_page":
        groupes = [[p] for p in range(1, total + 1)]
    elif mode == "par_paquet":
        n = max(1, int(toutes_les))
        groupes = [list(range(i, min(i + n, total) + 1))
                   for i in range(1, total + 1, n)]
    else:
        groupes = []
        for part in (plages or "").replace(";", ",").split(","):
            pages = dt.parse_pages(part, total)
            if pages:
                groupes.append(pages)
        if not groupes:
            return echec(AG, "Diviser", "aucune plage valide "
                                        "(exemple attendu : 1-5, 8, 12-20)")

    for i, pages in enumerate(groupes, start=1):
        w = PdfWriter()
        for p in pages:
            w.add_page(r.pages[p - 1])
        label = f"{pages[0]}" if len(pages) == 1 else f"{pages[0]}-{pages[-1]}"
        sorties.append((dt.safe_name(nom, f"p{label}", "pdf"), dt.writer_bytes(w)))

    return Resultat(True, AG, "Diviser", sorties,
                    f"{total} pages reparties en {len(sorties)} fichier(s).",
                    {"mode": mode, "groupes": [len(g) for g in groupes]})


@_t
def extract_pages(nom: str, data: bytes, plages: str,
                  inverser: bool = False) -> Resultat:
    """Extrait (ou supprime si inverser=True) les pages indiquees."""
    from pypdf import PdfWriter
    total = dt.page_count(data)
    sel = dt.parse_pages(plages, total)
    if not sel:
        return echec(AG, "Extraire des pages", "selection de pages vide")
    garder = [p for p in range(1, total + 1) if (p not in sel) if inverser] or sel
    if inverser:
        garder = [p for p in range(1, total + 1) if p not in sel]
    if not garder:
        return echec(AG, "Extraire des pages", "la selection retirerait toutes les pages")
    r = dt.reader(data)
    w = PdfWriter()
    for p in garder:
        w.add_page(r.pages[p - 1])
    verbe = "supprimees" if inverser else "extraites"
    return Resultat(True, AG, "Extraire des pages",
                    [(dt.safe_name(nom, "pages", "pdf"), dt.writer_bytes(w))],
                    f"{len(sel)} page(s) {verbe}, {len(garder)} page(s) conservee(s).",
                    {"selection": sel[:80], "conservees": len(garder)})


@_t
def organize_pdf(nom: str, data: bytes, ordre: str = "",
                 supprimer: str = "") -> Resultat:
    """Reordonne les pages (« 3,1,2,5- ») et supprime celles indiquees."""
    from pypdf import PdfWriter
    total = dt.page_count(data)
    retirer = set(dt.parse_pages(supprimer, total)) if supprimer.strip() else set()
    sequence = (dt.parse_pages(ordre, total) if not ordre.strip()
                else _ordre_libre(ordre, total))
    sequence = [p for p in sequence if p not in retirer]
    if not sequence:
        return echec(AG, "Organiser", "l ordre demande ne laisse aucune page")
    r = dt.reader(data)
    w = PdfWriter()
    for p in sequence:
        w.add_page(r.pages[p - 1])
    return Resultat(True, AG, "Organiser",
                    [(dt.safe_name(nom, "organise", "pdf"), dt.writer_bytes(w))],
                    f"{len(sequence)} pages dans le nouvel ordre"
                    + (f", {len(retirer)} supprimee(s)." if retirer else "."),
                    {"sequence": sequence[:80]})


def _ordre_libre(spec: str, total: int) -> list[int]:
    """Comme parse_pages mais conserve l ordre donne et autorise les repetitions."""
    out: list[int] = []
    for part in (spec or "").replace(";", ",").split(","):
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
            step = 1 if end >= start else -1
            out.extend([p for p in range(start, end + step, step)
                        if 1 <= p <= total])
        else:
            try:
                p = int(part)
            except ValueError:
                continue
            if 1 <= p <= total:
                out.append(p)
    return out or list(range(1, total + 1))


@_t
def rotate_pdf(nom: str, data: bytes, angle: int = 90,
               plages: str = "") -> Resultat:
    from pypdf import PdfWriter
    total = dt.page_count(data)
    cibles = set(dt.parse_pages(plages, total))
    r = dt.reader(data)
    w = PdfWriter()
    for i, page in enumerate(r.pages, start=1):
        if i in cibles:
            page.rotate(int(angle) % 360)
        w.add_page(page)
    return Resultat(True, AG, "Pivoter",
                    [(dt.safe_name(nom, f"rot{angle}", "pdf"), dt.writer_bytes(w))],
                    f"{len(cibles)} page(s) pivotee(s) de {angle}°.",
                    {"angle": angle, "pages": len(cibles)})


@_t
def crop_pdf(nom: str, data: bytes, haut: float = 0, bas: float = 0,
             gauche: float = 0, droite: float = 0, plages: str = "") -> Resultat:
    """Rogne les marges, en pourcentage de la dimension de la page."""
    from pypdf import PdfWriter
    total = dt.page_count(data)
    cibles = set(dt.parse_pages(plages, total))
    r = dt.reader(data)
    w = PdfWriter()
    for i, page in enumerate(r.pages, start=1):
        if i in cibles:
            box = page.mediabox
            W, H = float(box.width), float(box.height)
            x0 = float(box.left) + W * gauche / 100.0
            x1 = float(box.right) - W * droite / 100.0
            y0 = float(box.bottom) + H * bas / 100.0
            y1 = float(box.top) - H * haut / 100.0
            if x1 - x0 > 20 and y1 - y0 > 20:
                page.mediabox.lower_left = (x0, y0)
                page.mediabox.upper_right = (x1, y1)
                page.cropbox = page.mediabox
        w.add_page(page)
    return Resultat(True, AG, "Recadrer",
                    [(dt.safe_name(nom, "recadre", "pdf"), dt.writer_bytes(w))],
                    f"Marges rognees sur {len(cibles)} page(s) "
                    f"(h{haut}% b{bas}% g{gauche}% d{droite}%).",
                    {"pages": len(cibles)})


@_t
def page_numbers(nom: str, data: bytes, position: str = "bas-centre",
                 depart: int = 1, format_txt: str = "{n}",
                 taille: int = 10, plages: str = "",
                 marge: float = 24.0) -> Resultat:
    """Ajoute des numeros de page. format_txt accepte {n} et {total}."""
    total = dt.page_count(data)
    cibles = dt.parse_pages(plages, total)
    tailles = dt.page_sizes(data)
    calques = []
    from pypdf import PdfWriter
    r = dt.reader(data)
    w = PdfWriter()
    num = int(depart)
    for i, page in enumerate(r.pages, start=1):
        if i in cibles:
            W, H = tailles[i - 1]
            txt = format_txt.replace("{n}", str(num)).replace("{total}", str(total))
            num += 1

            def draw(c, W=W, H=H, txt=txt):
                c.setFont("Helvetica", taille)
                c.setFillGray(0.25)
                y = marge if position.startswith("bas") else H - marge
                if position.endswith("gauche"):
                    c.drawString(marge, y, txt)
                elif position.endswith("droite"):
                    c.drawRightString(W - marge, y, txt)
                else:
                    c.drawCentredString(W / 2, y, txt)

            page.merge_page(dt.reader(dt.blank_layer(W, H, draw)).pages[0])
        w.add_page(page)
        calques.append(i)
    return Resultat(True, AG, "Numeros de page",
                    [(dt.safe_name(nom, "numerote", "pdf"), dt.writer_bytes(w))],
                    f"Numerotation appliquee a {len(cibles)} page(s), "
                    f"depart {depart}, position {position}.",
                    {"pages": len(cibles)})


# ===================================================================
# ATOME - optimiser
# ===================================================================
AG2 = "ATOME"


@_t
def compress_pdf(nom: str, data: bytes, niveau: str = "recommande",
                 dpi: int = 110, qualite: int = 68) -> Resultat:
    """niveau : 'leger' (sans perte), 'recommande', 'fort' (rasterisation)."""
    avant = len(data)
    avert: list[str] = []

    if niveau in ("leger", "recommande"):
        try:
            import pikepdf
            with pikepdf.open(io.BytesIO(data)) as pdf:
                buf = io.BytesIO()
                pdf.save(buf, compress_streams=True, recompress_flate=True,
                         object_stream_mode=pikepdf.ObjectStreamMode.generate,
                         linearize=(niveau == "recommande"))
                out = buf.getvalue()
        except Exception as exc:
            return echec(AG2, "Compresser", f"pikepdf : {exc}")
        gain = 1 - len(out) / max(avant, 1)
        if niveau == "recommande" and gain < 0.06:
            avert.append("Le gain sans perte est faible : ce PDF est surtout "
                         "compose d images. Le niveau « fort » les reechantillonne.")
        return Resultat(True, AG2, "Compresser",
                        [(dt.safe_name(nom, "compresse", "pdf"), out)],
                        f"{avant / 1024:.0f} Ko → {len(out) / 1024:.0f} Ko "
                        f"({gain:.1%} de gain, sans perte).",
                        {"avant": avant, "apres": len(out), "gain": round(gain, 4),
                         "niveau": niveau}, avert)

    # niveau fort : rasterisation
    total = dt.page_count(data)
    if total > dt.MAX_RENDER_PAGES:
        avert.append(f"Document de {total} pages : seules les "
                     f"{dt.MAX_RENDER_PAGES} premieres sont reechantillonnees.")
    imgs = [im for _, im in dt.render_pages(data, dpi=dpi)]
    if not imgs:
        return echec(AG2, "Compresser", "rendu des pages impossible")
    out = dt.images_to_pdf(imgs, quality=qualite)
    gain = 1 - len(out) / max(avant, 1)

    # un PDF majoritairement textuel GROSSIT quand on le rasterise :
    # dans ce cas la compression forte est contre-productive, on la refuse
    if len(out) >= avant * 0.95:
        try:
            import pikepdf
            with pikepdf.open(io.BytesIO(data)) as pdf:
                buf = io.BytesIO()
                pdf.save(buf, compress_streams=True, recompress_flate=True,
                         object_stream_mode=pikepdf.ObjectStreamMode.generate,
                         linearize=True)
                sans_perte = buf.getvalue()
        except Exception:
            sans_perte = data
        gl = 1 - len(sans_perte) / max(avant, 1)
        return Resultat(
            True, AG2, "Compresser",
            [(dt.safe_name(nom, "compresse", "pdf"), sans_perte)],
            f"{avant / 1024:.0f} Ko → {len(sans_perte) / 1024:.0f} Ko "
            f"({gl:.1%} de gain, sans perte).",
            {"avant": avant, "apres": len(sans_perte), "gain": round(gl, 4),
             "niveau": "recommande (repli)", "raster_ko": round(len(out) / 1024)},
            ["La compression forte a ete ecartee : ce document est surtout du "
             f"texte, le rasteriser l aurait fait passer a "
             f"{len(out) / 1024:.0f} Ko. La version sans perte est renvoyee."])

    avert.append("Compression avec perte : le texte devient une image, "
                 "il n est plus selectionnable. Passe par « OCR » pour le "
                 "rendre a nouveau cherchable.")
    return Resultat(True, AG2, "Compresser",
                    [(dt.safe_name(nom, "compresse-fort", "pdf"), out)],
                    f"{avant / 1024:.0f} Ko → {len(out) / 1024:.0f} Ko "
                    f"({gain:.1%} de gain, {dpi} ppp).",
                    {"avant": avant, "apres": len(out), "gain": round(gain, 4),
                     "niveau": niveau, "dpi": dpi}, avert)


@_t
def repair_pdf(nom: str, data: bytes) -> Resultat:
    """Repare un PDF dont la structure est endommagee."""
    avant = dt.page_count(data)
    methodes = []
    out = None
    try:
        import pikepdf
        with pikepdf.open(io.BytesIO(data), attempt_recovery=True) as pdf:
            buf = io.BytesIO()
            pdf.save(buf, fix_metadata_version=True, compress_streams=True)
            out = buf.getvalue()
        methodes.append("pikepdf (reconstruction de la table des objets)")
    except Exception as exc:
        methodes.append(f"pikepdf en echec ({exc.__class__.__name__})")

    if out is None and dt._bin("qpdf"):
        import os
        import subprocess
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            src, dst = os.path.join(td, "in.pdf"), os.path.join(td, "out.pdf")
            open(src, "wb").write(data)
            try:
                subprocess.run(["qpdf", "--replace-input", "--qdf", src, dst],
                               check=False, timeout=120,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if os.path.exists(dst):
                    out = open(dst, "rb").read()
                    methodes.append("qpdf")
            except Exception:
                pass

    if out is None:
        return echec(AG2, "Reparer", "le fichier n a pas pu etre reconstruit ; "
                                     "il est probablement tronque au-dela du "
                                     "recuperable")
    apres = dt.page_count(out)
    avert = ([] if apres >= avant else
             [f"{avant - apres} page(s) n ont pas pu etre recuperees."])
    return Resultat(True, AG2, "Reparer",
                    [(dt.safe_name(nom, "repare", "pdf"), out)],
                    f"Document reconstruit : {apres} page(s) lisibles.",
                    {"pages_avant": avant, "pages_apres": apres,
                     "methodes": methodes}, avert)


@_t
def ocr_pdf(nom: str, data: bytes, langues: str = "fra+eng", dpi: int = 220,
            plages: str = "") -> Resultat:
    """Rend un PDF scanne cherchable (couche de texte invisible)."""
    caps = dt.capabilities()
    if not caps["ocr"]:
        return echec(AG2, "OCR", "tesseract n est pas installe. Ajoute "
                                 "« tesseract-ocr » a packages.txt et "
                                 "« pytesseract » a requirements.txt.")
    import pytesseract
    from pypdf import PdfWriter
    total = dt.page_count(data)
    cibles = dt.parse_pages(plages, total)
    rendus = dt.render_pages(data, cibles, dpi=dpi)
    if not rendus:
        return echec(AG2, "OCR", "rendu des pages impossible")

    w = PdfWriter()
    mots = 0
    for _, img in rendus:
        try:
            pdf_page = pytesseract.image_to_pdf_or_hocr(img, lang=langues,
                                                        extension="pdf")
            r = dt.reader(pdf_page)
            w.add_page(r.pages[0])
            mots += utils.word_count(pytesseract.image_to_string(img, lang=langues))
        except Exception as exc:
            return echec(AG2, "OCR", f"tesseract : {exc}")
    out = dt.writer_bytes(w)
    avert = ([] if len(rendus) == total else
             [f"{total - len(rendus)} page(s) hors selection n ont pas ete traitees."])
    return Resultat(True, AG2, "OCR",
                    [(dt.safe_name(nom, "ocr", "pdf"), out)],
                    f"{len(rendus)} page(s) rendues cherchables, "
                    f"environ {utils.human_int(mots)} mots reconnus ({langues}).",
                    {"pages": len(rendus), "mots": mots, "dpi": dpi,
                     "langues": langues}, avert)


@_t
def scan_to_pdf(fichiers: list[tuple[str, bytes]], ameliorer: bool = True,
                niveaux_gris: bool = True, redresser: bool = True,
                nom_sortie: str = "numerisation.pdf") -> Resultat:
    """Transforme des photos de documents en PDF propre."""
    from PIL import Image, ImageEnhance, ImageFilter, ImageOps
    imgs = []
    for nom, data in fichiers:
        try:
            im = Image.open(io.BytesIO(data))
            im.load()
            im = im.convert("RGB")
        except Exception:
            continue
        if redresser:
            try:
                im = ImageOps.exif_transpose(im)
            except Exception:
                pass
        if niveaux_gris:
            im = im.convert("L")
        if ameliorer:
            im = ImageOps.autocontrast(im, cutoff=1)
            im = ImageEnhance.Contrast(im).enhance(1.35)
            im = im.filter(ImageFilter.SHARPEN)
        imgs.append(im.convert("RGB"))
    if not imgs:
        return echec(AG2, "Scan vers PDF", "aucune image exploitable")
    out = dt.images_to_pdf(imgs, page_size="A4", margin_mm=6, quality=88)
    return Resultat(True, AG2, "Scan vers PDF", [(nom_sortie, out)],
                    f"{len(imgs)} image(s) assemblees en PDF A4"
                    + (", contraste et nettete renforces." if ameliorer else "."),
                    {"images": len(imgs)})


# ===================================================================
# SCEAU - securiser et annoter
# ===================================================================
AG3 = "SCEAU"


@_t
def protect_pdf(nom: str, data: bytes, mot_de_passe: str,
                mdp_proprietaire: str = "", interdire_impression: bool = False,
                interdire_copie: bool = True) -> Resultat:
    if not mot_de_passe:
        return echec(AG3, "Proteger", "mot de passe vide")
    try:
        import pikepdf
        perms = pikepdf.Permissions(
            extract=not interdire_copie,
            print_lowres=not interdire_impression,
            print_highres=not interdire_impression,
            modify_annotation=False, modify_assembly=False,
            modify_form=False, modify_other=False)
        with pikepdf.open(io.BytesIO(data)) as pdf:
            buf = io.BytesIO()
            pdf.save(buf, encryption=pikepdf.Encryption(
                user=mot_de_passe, owner=mdp_proprietaire or mot_de_passe,
                R=6, allow=perms))
            out = buf.getvalue()
    except Exception as exc:
        return echec(AG3, "Proteger", f"chiffrement impossible : {exc}")
    return Resultat(True, AG3, "Proteger",
                    [(dt.safe_name(nom, "protege", "pdf"), out)],
                    "PDF chiffre en AES-256. Le mot de passe est demande a "
                    "l ouverture.",
                    {"impression": not interdire_impression,
                     "copie": not interdire_copie},
                    ["Le mot de passe n est stocke nulle part : s il est perdu, "
                     "le fichier est irrecuperable."])


@_t
def unlock_pdf(nom: str, data: bytes, mot_de_passe: str = "") -> Resultat:
    """Retire la protection d un PDF dont on possede le mot de passe."""
    try:
        import pikepdf
        with pikepdf.open(io.BytesIO(data), password=mot_de_passe) as pdf:
            buf = io.BytesIO()
            pdf.save(buf)
            out = buf.getvalue()
    except Exception as exc:
        msg = str(exc)
        if "password" in msg.lower():
            return echec(AG3, "Deverrouiller",
                         "mot de passe incorrect. SYNTHEA ne casse pas le "
                         "chiffrement d un document : il faut connaitre le "
                         "mot de passe.")
        return echec(AG3, "Deverrouiller", f"{exc}")
    return Resultat(True, AG3, "Deverrouiller",
                    [(dt.safe_name(nom, "deverrouille", "pdf"), out)],
                    "Protection retiree ; le document s ouvre desormais sans "
                    "mot de passe.", {})


@_t
def watermark_pdf(nom: str, data: bytes, texte: str = "CONFIDENTIEL",
                  image: bytes | None = None, opacite: float = 0.18,
                  taille: int = 54, angle: int = 45, couleur: str = "#A33A2E",
                  position: str = "centre", plages: str = "",
                  devant: bool = True) -> Resultat:
    total = dt.page_count(data)
    cibles = set(dt.parse_pages(plages, total))
    tailles = dt.page_sizes(data)
    from pypdf import PdfWriter
    r = dt.reader(data)
    w = PdfWriter()
    rgb = tuple(int(couleur.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))

    for i, page in enumerate(r.pages, start=1):
        if i in cibles:
            W, H = tailles[i - 1]

            def draw(c, W=W, H=H):
                c.saveState()
                try:
                    c.setFillAlpha(opacite)
                    c.setStrokeAlpha(opacite)
                except Exception:
                    pass
                if image:
                    from reportlab.lib.utils import ImageReader
                    try:
                        img = ImageReader(io.BytesIO(image))
                        iw, ih = img.getSize()
                        sc = min(W * 0.6 / iw, H * 0.6 / ih)
                        c.translate(W / 2, H / 2)
                        c.rotate(angle)
                        c.drawImage(img, -iw * sc / 2, -ih * sc / 2,
                                    iw * sc, ih * sc, mask="auto")
                    except Exception:
                        pass
                else:
                    c.setFillColorRGB(*rgb)
                    c.setFont("Helvetica-Bold", taille)
                    x, y = W / 2, H / 2
                    if position == "haut":
                        y = H * 0.82
                    elif position == "bas":
                        y = H * 0.14
                    c.translate(x, y)
                    c.rotate(angle)
                    c.drawCentredString(0, 0, texte)
                c.restoreState()

            layer = dt.reader(dt.blank_layer(W, H, draw)).pages[0]
            if devant:
                page.merge_page(layer)
            else:
                base = layer
                base.merge_page(page)
                page = base
        w.add_page(page)
    return Resultat(True, AG3, "Filigrane",
                    [(dt.safe_name(nom, "filigrane", "pdf"), dt.writer_bytes(w))],
                    f"Filigrane applique a {len(cibles)} page(s).",
                    {"texte": texte if not image else "(image)",
                     "opacite": opacite, "pages": len(cibles)})


@_t
def redact_pdf(nom: str, data: bytes, motifs: str = "",
               zones: list[dict] | None = None, dpi: int = 160,
               sensible_casse: bool = False) -> Resultat:
    """Caviardage reel : les pages sont rasterisees, le texte masque disparait.

    motifs : termes a masquer, un par ligne ou separes par des virgules ou des
    points-virgules (recherche dans le texte extrait, avec localisation exacte
    par pdfplumber).
    zones  : rectangles manuels [{page, x0, y0, x1, y1}] en pourcentage.
    """
    import re as _re
    from PIL import ImageDraw
    termes = [m.strip() for m in _re.split(r"[\n;,]+", motifs or "") if m.strip()]
    if not termes and not zones:
        return echec(AG3, "Caviarder", "indique au moins un terme a masquer "
                                       "ou une zone")
    total = dt.page_count(data)
    if total > dt.MAX_RENDER_PAGES:
        return echec(AG3, "Caviarder",
                     f"document de {total} pages : limite a "
                     f"{dt.MAX_RENDER_PAGES} pages pour le caviardage")

    # localisation des termes
    boites: dict[int, list[tuple[float, float, float, float]]] = {}
    occurrences = 0
    if termes and utils.has_module("pdfplumber"):
        import pdfplumber
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            for pno, page in enumerate(pdf.pages, start=1):
                try:
                    mots = page.extract_words() or []
                except Exception:
                    continue
                for mot in mots:
                    txt = mot.get("text", "")
                    cible = txt if sensible_casse else txt.lower()
                    for t in termes:
                        tt = t if sensible_casse else t.lower()
                        if tt and tt in cible:
                            boites.setdefault(pno, []).append(
                                (mot["x0"] / page.width, mot["top"] / page.height,
                                 mot["x1"] / page.width, mot["bottom"] / page.height))
                            occurrences += 1
                            break
    for z in (zones or []):
        boites.setdefault(int(z["page"]), []).append(
            (z["x0"] / 100, z["y0"] / 100, z["x1"] / 100, z["y1"] / 100))

    if not boites:
        return echec(AG3, "Caviarder",
                     "aucune occurrence trouvee : verifie l orthographe, ou le "
                     "PDF est une image (passe-le d abord par l OCR)")

    rendus = dt.render_pages(data, dpi=dpi)
    images = []
    for pno, img in rendus:
        if pno in boites:
            d = ImageDraw.Draw(img)
            W, H = img.size
            for (x0, y0, x1, y1) in boites[pno]:
                d.rectangle([x0 * W - 2, y0 * H - 2, x1 * W + 2, y1 * H + 2],
                            fill="black")
        images.append(img)
    out = dt.images_to_pdf(images, quality=90)
    return Resultat(True, AG3, "Caviarder",
                    [(dt.safe_name(nom, "caviarde", "pdf"), out)],
                    f"{occurrences} occurrence(s) masquee(s) sur "
                    f"{len(boites)} page(s). Le texte est reellement supprime : "
                    f"les pages ont ete rasterisees.",
                    {"occurrences": occurrences, "pages": sorted(boites)},
                    ["Le document caviarde n est plus selectionnable. "
                     "C est le prix d un caviardage irreversible."])


@_t
def sign_pdf(nom: str, data: bytes, signature_img: bytes | None = None,
             texte: str = "", page: int = 0, x: float = 62.0, y: float = 12.0,
             largeur: float = 28.0, mention: str = "") -> Resultat:
    """Appose une signature visuelle (image ou texte) a la position voulue.

    x, y, largeur sont exprimes en pourcentage de la page.
    """
    total = dt.page_count(data)
    cible = total if page in (0, -1) else max(1, min(page, total))
    tailles = dt.page_sizes(data)
    W, H = tailles[cible - 1]

    def draw(c):
        px, py, pw = W * x / 100, H * y / 100, W * largeur / 100
        if signature_img:
            from reportlab.lib.utils import ImageReader
            try:
                img = ImageReader(io.BytesIO(signature_img))
                iw, ih = img.getSize()
                c.drawImage(img, px, py, pw, pw * ih / iw, mask="auto")
                py -= 12
            except Exception:
                pass
        if texte:
            c.setFont("Helvetica-Bold", 11)
            c.setFillGray(0.1)
            c.drawString(px, py, texte)
        if mention:
            c.setFont("Helvetica", 7.5)
            c.setFillGray(0.45)
            c.drawString(px, py - 11, mention)

    layer = dt.blank_layer(W, H, draw)
    out = dt.overlay(data, layer, pages=[cible])
    return Resultat(True, AG3, "Signer",
                    [(dt.safe_name(nom, "signe", "pdf"), out)],
                    f"Signature apposee sur la page {cible}.",
                    {"page": cible},
                    ["Il s agit d une signature *visuelle*. Elle n a pas la "
                     "valeur d une signature electronique qualifiee : aucun "
                     "certificat n est appose et l integrite du fichier n est "
                     "pas scellee cryptographiquement."])


@_t
def annotate_pdf(nom: str, data: bytes, elements: list[dict]) -> Resultat:
    """Ajoute textes, rectangles et images.

    elements : [{type: texte|rectangle|surlignage|image, page, x, y, ...}]
    coordonnees en pourcentage, origine en bas a gauche.
    """
    if not elements:
        return echec(AG3, "Editer", "aucun element a ajouter")
    total = dt.page_count(data)
    tailles = dt.page_sizes(data)
    from pypdf import PdfWriter
    r = dt.reader(data)
    w = PdfWriter()
    par_page: dict[int, list[dict]] = {}
    for el in elements:
        p = max(1, min(int(el.get("page", 1)), total))
        par_page.setdefault(p, []).append(el)

    for i, page in enumerate(r.pages, start=1):
        if i in par_page:
            W, H = tailles[i - 1]

            def draw(c, items=par_page[i], W=W, H=H):
                for el in items:
                    x, y = W * float(el.get("x", 10)) / 100, H * float(el.get("y", 10)) / 100
                    coul = el.get("couleur", "#17202A").lstrip("#")
                    rgb = tuple(int(coul[k:k + 2], 16) / 255 for k in (0, 2, 4))
                    kind = el.get("type", "texte")
                    if kind == "texte":
                        c.setFillColorRGB(*rgb)
                        c.setFont("Helvetica" if not el.get("gras") else "Helvetica-Bold",
                                  float(el.get("taille", 12)))
                        c.drawString(x, y, str(el.get("texte", "")))
                    elif kind in ("rectangle", "surlignage"):
                        ww = W * float(el.get("largeur", 20)) / 100
                        hh = H * float(el.get("hauteur", 4)) / 100
                        c.saveState()
                        if kind == "surlignage":
                            try:
                                c.setFillAlpha(float(el.get("opacite", 0.35)))
                            except Exception:
                                pass
                        c.setFillColorRGB(*rgb)
                        c.rect(x, y, ww, hh, stroke=0, fill=1)
                        c.restoreState()
                    elif kind == "image" and el.get("donnees"):
                        from reportlab.lib.utils import ImageReader
                        try:
                            img = ImageReader(io.BytesIO(el["donnees"]))
                            iw, ih = img.getSize()
                            ww = W * float(el.get("largeur", 20)) / 100
                            c.drawImage(img, x, y, ww, ww * ih / iw, mask="auto")
                        except Exception:
                            pass

            page.merge_page(dt.reader(dt.blank_layer(W, H, draw)).pages[0])
        w.add_page(page)
    return Resultat(True, AG3, "Editer",
                    [(dt.safe_name(nom, "edite", "pdf"), dt.writer_bytes(w))],
                    f"{len(elements)} element(s) ajoute(s) sur "
                    f"{len(par_page)} page(s).",
                    {"elements": len(elements)})
