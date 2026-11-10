"""SYNTHEA - Agent ATELIER : production de visuels a partir du document.

Tout est genere localement (Pillow + matplotlib), sans service externe :
  - couvertures et cartons de citation
  - schemas de concepts (themes relies au document)
  - nuages de mots
  - graphiques : poids des themes, densite des pages, equilibre des sections
  - infographie de synthese prete a etre inseree dans un PowerPoint
  - retouches facon banc d essai : niveaux de gris, duotone, sepia, flou,
    posterisation, contraste, vignette (appliquees aux JPEG importes)
"""
from __future__ import annotations

import io
import math
import os
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt                                   # noqa: E402
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont  # noqa: E402

from . import utils                                               # noqa: E402

# --------------------------------------------------------------- palettes
PALETTES: dict[str, dict] = {
    "encre": {"bg": "#17202A", "fg": "#F7F5EF", "accent": "#1F6F6B",
              "accent2": "#B07D2B", "muted": "#8A97A3"},
    "sable": {"bg": "#FBFAF7", "fg": "#17202A", "accent": "#1F6F6B",
              "accent2": "#A33A2E", "muted": "#8C8577"},
    "institution": {"bg": "#0E2A47", "fg": "#FFFFFF", "accent": "#C9A227",
                    "accent2": "#5B8DB8", "muted": "#9FB3C8"},
    "campagne": {"bg": "#8E1B1B", "fg": "#FFFFFF", "accent": "#F2C14E",
                 "accent2": "#2B4C7E", "muted": "#E0B8B8"},
    "startup": {"bg": "#10131A", "fg": "#F2F4F8", "accent": "#5BE3C3",
                "accent2": "#7A5CFF", "muted": "#7C8698"},
    "tropique": {"bg": "#063B3A", "fg": "#FDFBF4", "accent": "#F4A259",
                 "accent2": "#5CC8A7", "muted": "#9EC5BF"},
    "academique": {"bg": "#FFFFFF", "fg": "#1A1A1A", "accent": "#3A5A98",
                   "accent2": "#8C2F39", "muted": "#777777"},
}
FILTERS = ["aucun", "niveaux de gris", "duotone", "sepia", "contraste",
           "flou artistique", "posterisation", "vignette", "nettete"]


# ------------------------------------------------------------------ polices
def _font_path(bold: bool = False) -> str | None:
    try:
        from matplotlib import font_manager
        name = "DejaVu Sans:bold" if bold else "DejaVu Sans"
        p = font_manager.findfont(font_manager.FontProperties(
            family="DejaVu Sans", weight="bold" if bold else "normal"))
        return p if p and os.path.exists(p) else None
    except Exception:
        return None


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    p = _font_path(bold)
    if p:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        test = f"{cur} {w}".strip()
        try:
            width = draw.textlength(test, font=font)
        except Exception:
            width = len(test) * font.size * 0.55
        if width <= max_w or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def to_png(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def to_jpeg(img: Image.Image, quality: int = 92) -> bytes:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()


# ------------------------------------------------------------------ visuels
def cover(title: str, subtitle: str = "", footer: str = "",
          palette: str = "encre", size: tuple[int, int] = (1600, 900)) -> Image.Image:
    pal = PALETTES.get(palette, PALETTES["encre"])
    img = Image.new("RGB", size, pal["bg"])
    d = ImageDraw.Draw(img)
    W, H = size

    # trame geometrique discrete
    for i in range(0, W, 48):
        d.line([(i, 0), (i - 180, H)], fill=pal["accent"], width=1)
    veil = Image.new("RGBA", size, (0, 0, 0, 0))
    ImageDraw.Draw(veil).rectangle([0, 0, W, H], fill=(*_hex(pal["bg"]), 205))
    img = Image.alpha_composite(img.convert("RGBA"), veil).convert("RGB")
    d = ImageDraw.Draw(img)

    d.rectangle([0, 0, 14, H], fill=pal["accent"])
    f_t = _font(int(H * 0.085), True)
    f_s = _font(int(H * 0.040))
    f_f = _font(int(H * 0.026))

    y = int(H * 0.24)
    for line in _wrap(d, title, f_t, int(W * 0.78))[:4]:
        d.text((int(W * 0.08), y), line, font=f_t, fill=pal["fg"])
        y += int(f_t.size * 1.18)

    d.line([(int(W * 0.08), y + 18), (int(W * 0.30), y + 18)],
           fill=pal["accent2"], width=5)
    y += 48
    for line in _wrap(d, subtitle, f_s, int(W * 0.74))[:3]:
        d.text((int(W * 0.08), y), line, font=f_s, fill=pal["muted"])
        y += int(f_s.size * 1.35)

    if footer:
        d.text((int(W * 0.08), H - int(H * 0.09)), footer, font=f_f, fill=pal["muted"])
    return img


def quote_card(text: str, reference: str = "", palette: str = "sable",
               size: tuple[int, int] = (1200, 1200)) -> Image.Image:
    pal = PALETTES.get(palette, PALETTES["sable"])
    img = Image.new("RGB", size, pal["bg"])
    d = ImageDraw.Draw(img)
    W, H = size
    d.rectangle([60, 60, W - 60, H - 60], outline=pal["accent"], width=3)
    f_q = _font(int(W * 0.055), True)
    f_r = _font(int(W * 0.030))
    d.text((100, 110), "“", font=_font(int(W * 0.18), True), fill=pal["accent"])
    lines = _wrap(d, text, f_q, W - 220)[:11]
    y = max(260, (H - len(lines) * int(f_q.size * 1.35)) // 2)
    for ln in lines:
        d.text((110, y), ln, font=f_q, fill=pal["fg"])
        y += int(f_q.size * 1.35)
    if reference:
        d.text((110, H - 150), f"— {reference}", font=f_r, fill=pal["accent2"])
    return img


def concept_diagram(title: str, nodes: list[str], palette: str = "sable",
                    size: tuple[int, int] = (1600, 900)) -> Image.Image:
    """Schema radial : le document au centre, ses themes autour."""
    pal = PALETTES.get(palette, PALETTES["sable"])
    img = Image.new("RGB", size, pal["bg"])
    d = ImageDraw.Draw(img)
    W, H = size
    cx, cy = W // 2, H // 2 + 20
    f_c = _font(28, True)
    f_n = _font(22)

    nodes = [n for n in nodes if n][:8] or ["theme"]
    R = int(min(W, H) * 0.34)
    bw, bh = int(W * 0.21), int(H * 0.115)

    d.text((50, 40), utils.truncate(title, 90), font=_font(34, True), fill=pal["fg"])
    d.line([(50, 92), (260, 92)], fill=pal["accent"], width=4)

    for i, n in enumerate(nodes):
        ang = -math.pi / 2 + 2 * math.pi * i / len(nodes)
        x, y = cx + int(R * math.cos(ang)), cy + int(R * 0.80 * math.sin(ang))
        d.line([(cx, cy), (x, y)], fill=pal["muted"], width=2)
        box = [x - bw // 2, y - bh // 2, x + bw // 2, y + bh // 2]
        d.rounded_rectangle(box, radius=12, fill=pal["fg"], outline=pal["accent"], width=2)
        for j, ln in enumerate(_wrap(d, n, f_n, bw - 24)[:2]):
            d.text((box[0] + 14, box[1] + 14 + j * 26), ln, font=f_n, fill=pal["bg"])

    r = int(min(W, H) * 0.115)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=pal["accent"], outline=pal["accent2"], width=4)
    for j, ln in enumerate(_wrap(d, "Document", f_c, 2 * r - 30)[:2]):
        d.text((cx - r + 18, cy - 14 + j * 30), ln, font=f_c, fill=pal["bg"])
    return img


def wordcloud_image(keywords: list[tuple[str, float]], palette: str = "sable",
                    size: tuple[int, int] = (1400, 800)) -> Image.Image:
    pal = PALETTES.get(palette, PALETTES["sable"])
    if utils.has_module("wordcloud") and keywords:
        try:
            from wordcloud import WordCloud
            freq = {k: max(float(v), 0.01) for k, v in keywords[:120]}
            wc = WordCloud(width=size[0], height=size[1],
                           background_color=pal["bg"], prefer_horizontal=0.85,
                           colormap="viridis", font_path=_font_path(False),
                           max_words=110, margin=6).generate_from_frequencies(freq)
            return wc.to_image()
        except Exception:
            pass
    # repli : disposition en lignes ponderees
    img = Image.new("RGB", size, pal["bg"])
    d = ImageDraw.Draw(img)
    if not keywords:
        return img
    mx = max(v for _, v in keywords) or 1.0
    x, y, rowh = 30, 30, 0
    for term, val in keywords[:48]:
        sz = int(20 + 46 * (val / mx) ** 0.6)
        f = _font(sz, val > mx * 0.5)
        w = int(d.textlength(term, font=f)) + 24
        if x + w > size[0] - 30:
            x, y = 30, y + rowh + 14
            rowh = 0
        if y + sz > size[1] - 30:
            break
        col = pal["accent"] if val > mx * 0.55 else (
            pal["accent2"] if val > mx * 0.3 else pal["fg"])
        d.text((x, y), term, font=f, fill=col)
        x += w
        rowh = max(rowh, sz)
    return img


# ------------------------------------------------------------- graphiques
def _fig_to_png(fig) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight",
                facecolor=fig.get_facecolor())
    plt.close(fig)
    return buf.getvalue()


def _style(palette: str):
    pal = PALETTES.get(palette, PALETTES["sable"])
    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor(pal["bg"])
    ax.set_facecolor(pal["bg"])
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(pal["muted"])
    ax.tick_params(colors=pal["fg"], labelsize=9)
    ax.yaxis.label.set_color(pal["fg"])
    ax.xaxis.label.set_color(pal["fg"])
    ax.title.set_color(pal["fg"])
    ax.grid(axis="y", color=pal["muted"], alpha=0.22, linewidth=0.7)
    return fig, ax, pal


def chart_topics(topics: list[dict], palette: str = "sable") -> bytes:
    fig, ax, pal = _style(palette)
    if not topics:
        ax.text(0.5, 0.5, "aucun theme detecte", ha="center", color=pal["muted"])
        ax.axis("off")
        return _fig_to_png(fig)
    labels = [utils.truncate(t["libelle"], 38) for t in topics][::-1]
    vals = [t["poids"] * 100 for t in topics][::-1]
    ax.barh(labels, vals, color=pal["accent"], height=0.62)
    for i, v in enumerate(vals):
        ax.text(v + 0.5, i, f"{v:.1f} %", va="center", color=pal["fg"], fontsize=9)
    ax.set_title("Poids des themes dans le corpus", fontsize=12, loc="left")
    ax.set_xlabel("part du corpus (%)")
    return _fig_to_png(fig)


def chart_page_density(pages_words: list[tuple[int, int]], palette: str = "sable") -> bytes:
    fig, ax, pal = _style(palette)
    if not pages_words:
        ax.axis("off")
        return _fig_to_png(fig)
    xs = [p for p, _ in pages_words]
    ys = [w for _, w in pages_words]
    ax.fill_between(xs, ys, color=pal["accent"], alpha=0.35)
    ax.plot(xs, ys, color=pal["accent"], linewidth=1.2)
    empties = [x for x, y in pages_words if y < 5]
    if empties:
        ax.scatter(empties, [0] * len(empties), color=pal["accent2"], s=14,
                   zorder=3, label="pages sans texte")
        ax.legend(facecolor=pal["bg"], edgecolor=pal["muted"],
                  labelcolor=pal["fg"], fontsize=8)
    ax.set_title("Densite de texte par page", fontsize=12, loc="left")
    ax.set_xlabel("page")
    ax.set_ylabel("mots")
    return _fig_to_png(fig)


def chart_sections(sections: list[tuple[str, int, int]], palette: str = "sable") -> bytes:
    """sections = [(titre, page_debut, page_fin)]"""
    fig, ax, pal = _style(palette)
    if not sections:
        ax.axis("off")
        return _fig_to_png(fig)
    labels = [utils.truncate(t, 34) for t, _, _ in sections][::-1]
    spans = [max(1, b - a + 1) for _, a, b in sections][::-1]
    starts = [a for _, a, _ in sections][::-1]
    ax.barh(labels, spans, left=starts, color=pal["accent2"], height=0.6)
    ax.set_title("Decoupage du document en sections", fontsize=12, loc="left")
    ax.set_xlabel("pages")
    return _fig_to_png(fig)


def chart_coverage(report: dict, palette: str = "sable") -> bytes:
    fig, ax, pal = _style(palette)
    c = report.get("controles", {})
    labels = ["Segmentation", "Synthese", "Fidelite num.", "Fidelite litt.", "Tracabilite"]
    vals = [c.get("C2", {}).get("taux", 0), c.get("C3", {}).get("taux", 0),
            c.get("C5", {}).get("taux", 0), c.get("C6", {}).get("taux", 0),
            c.get("C7", {}).get("taux", 0)]
    cols = [pal["accent"] if v >= 99 else (pal["accent2"] if v >= 95 else "#A33A2E")
            for v in vals]
    ax.bar(labels, vals, color=cols, width=0.55)
    ax.set_ylim(0, 105)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v:.1f}", ha="center", color=pal["fg"], fontsize=9)
    ax.set_title("Controles ARGUS (%)", fontsize=12, loc="left")
    plt.setp(ax.get_xticklabels(), rotation=12, ha="right")
    return _fig_to_png(fig)


# ------------------------------------------------------------ infographie
def infographic(title: str, kpis: list[tuple[str, str]], bullets: list[str],
                palette: str = "institution",
                size: tuple[int, int] = (1600, 900)) -> Image.Image:
    pal = PALETTES.get(palette, PALETTES["institution"])
    img = Image.new("RGB", size, pal["bg"])
    d = ImageDraw.Draw(img)
    W, H = size
    d.rectangle([0, 0, W, 10], fill=pal["accent"])

    f_t = _font(46, True)
    for i, ln in enumerate(_wrap(d, title, f_t, W - 120)[:2]):
        d.text((60, 54 + i * 56), ln, font=f_t, fill=pal["fg"])

    # tuiles d indicateurs
    top = 190
    n = max(len(kpis), 1)
    bw = (W - 120 - (n - 1) * 20) // n
    f_l, f_v = _font(18), _font(42, True)
    for i, (lab, val) in enumerate(kpis):
        x = 60 + i * (bw + 20)
        d.rounded_rectangle([x, top, x + bw, top + 140], radius=12,
                            fill=pal["fg"], outline=pal["accent"], width=2)
        d.text((x + 18, top + 18), lab.upper()[:26], font=f_l, fill=pal["muted"])
        d.text((x + 18, top + 56), str(val)[:14], font=f_v, fill=pal["bg"])

    f_b = _font(24)
    y = top + 190
    for b in bullets[:7]:
        d.ellipse([60, y + 9, 72, y + 21], fill=pal["accent"])
        for j, ln in enumerate(_wrap(d, b, f_b, W - 180)[:2]):
            d.text((92, y + j * 32), ln, font=f_b, fill=pal["fg"])
            y_last = j
        y += 34 * (y_last + 1) + 12
        if y > H - 70:
            break
    return img


# --------------------------------------------------------------- retouches
def _hex(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))        # type: ignore[return-value]


def apply_filter(data: bytes, kind: str = "aucun", palette: str = "encre",
                 intensity: float = 1.0) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img.load()
    img = img.convert("RGB")
    pal = PALETTES.get(palette, PALETTES["encre"])
    k = (kind or "aucun").lower()

    if k == "niveaux de gris":
        return img.convert("L").convert("RGB")
    if k == "duotone":
        g = img.convert("L")
        dark, light = _hex(pal["bg"]), _hex(pal["accent"])
        lut = []
        for c in range(3):
            lut += [int(dark[c] + (light[c] - dark[c]) * (i / 255)) for i in range(256)]
        return g.convert("RGB").point(lut)
    if k == "sepia":
        g = img.convert("L")
        lut: list[int] = []
        for mult, base in ((1.07, 18), (0.94, 10), (0.74, 4)):
            lut += [min(255, int(i * mult) + base) for i in range(256)]
        return g.convert("RGB").point(lut)
    if k == "contraste":
        return ImageEnhance.Contrast(img).enhance(1.0 + 0.8 * intensity)
    if k == "flou artistique":
        return img.filter(ImageFilter.GaussianBlur(radius=2.0 + 4.0 * intensity))
    if k == "posterisation":
        from PIL import ImageOps
        return ImageOps.posterize(img, max(2, 6 - int(4 * intensity)))
    if k == "nettete":
        return ImageEnhance.Sharpness(img).enhance(1.0 + 2.2 * intensity)
    if k == "vignette":
        W, H = img.size
        mask = Image.new("L", (W, H), 0)
        md = ImageDraw.Draw(mask)
        md.ellipse([-int(W * 0.12), -int(H * 0.12), int(W * 1.12), int(H * 1.12)], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(radius=min(W, H) * 0.12))
        dark = Image.new("RGB", (W, H), pal["bg"])
        return Image.composite(img, dark, mask)
    return img


def caption_image(data_or_img, caption: str, palette: str = "encre",
                  reference: str = "") -> Image.Image:
    """Ajoute un bandeau de legende sous une image (illustration sourcee)."""
    img = (data_or_img if isinstance(data_or_img, Image.Image)
           else Image.open(io.BytesIO(data_or_img)).convert("RGB"))
    pal = PALETTES.get(palette, PALETTES["encre"])
    W, H = img.size
    band = max(90, int(H * 0.14))
    out = Image.new("RGB", (W, H + band), pal["bg"])
    out.paste(img.convert("RGB"), (0, 0))
    d = ImageDraw.Draw(out)
    f_c, f_r = _font(max(18, int(W * 0.022)), True), _font(max(14, int(W * 0.016)))
    y = H + 16
    for ln in _wrap(d, caption, f_c, W - 60)[:2]:
        d.text((30, y), ln, font=f_c, fill=pal["fg"])
        y += int(f_c.size * 1.3)
    if reference:
        d.text((30, H + band - int(f_r.size * 1.8)), reference, font=f_r,
               fill=pal["accent"])
    return out


# -------------------------------------------------------- lot d illustrations
def illustration_pack(doc_title: str, tree, doc, palette: str = "sable") -> dict[str, bytes]:
    """Jeu complet de visuels prets a inserer dans un deck ou un rapport."""
    from . import summarizer
    pack: dict[str, bytes] = {}
    st = tree.stats or {}

    pack["01-couverture.png"] = to_png(cover(
        doc_title,
        f"{tree.doc_type} — {utils.human_int(st.get('pages', doc.n_pages))} pages analysees",
        f"SYNTHEA — {utils.now_fr()}", palette))

    pack["02-schema-themes.png"] = to_png(concept_diagram(
        doc_title, [t["libelle"] for t in tree.topics], palette))

    pack["03-nuage-mots.png"] = to_png(wordcloud_image(tree.keywords, palette))
    pack["04-themes.png"] = chart_topics(tree.topics, palette)
    pack["05-densite-pages.png"] = chart_page_density(
        [(p.index, p.word_count) for p in doc.pages], palette)
    pack["06-sections.png"] = chart_sections(
        [(s.title, s.page_start, s.page_end) for s in tree.sections], palette)

    kpis = [("Pages", utils.human_int(doc.n_pages)),
            ("Mots", utils.human_int(doc.n_words)),
            ("Sections", str(len(tree.sections))),
            ("Themes", str(len(tree.topics)))]
    pack["07-infographie.png"] = to_png(infographic(
        doc_title, kpis, summarizer.bullet_points(tree, 6), "institution"))

    if tree.executive:
        c = tree.executive[0]
        pack["08-citation.png"] = to_png(quote_card(
            utils.truncate(c.text, 260), c.ref, palette))
    return pack
