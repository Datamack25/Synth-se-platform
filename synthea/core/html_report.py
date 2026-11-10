"""SYNTHEA - rendu HTML professionnel (affichage dans l application et export)."""
from __future__ import annotations

import base64
import html

from . import utils
from .models import Rendition, SummaryTree

CSS = """
:root{--ink:#17202A;--soft:#44525F;--line:#DDD7CC;--paper:#FBFAF7;--paper2:#F1EEE8;
--brand:#1F6F6B;--brandd:#14504D;--brandl:#E6F0EF;--gold:#B07D2B;--red:#A33A2E;
--green:#2E7D4F;--amber:#C08A1E}
*{box-sizing:border-box}
body{margin:0;background:var(--paper2);color:var(--ink);
font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
font-feature-settings:"kern" 1,"liga" 1,"tnum" 1;line-height:1.62}
.wrap{max-width:900px;margin:32px auto 64px;background:#fff;border:1px solid var(--line);
border-radius:12px;box-shadow:0 1px 2px rgba(23,32,42,.06),0 10px 34px rgba(23,32,42,.07);
overflow:hidden}
header{padding:34px 48px 26px;border-bottom:1px solid var(--line);
background:linear-gradient(180deg,#fff,var(--paper))}
header .kicker{font-size:.68rem;letter-spacing:.17em;text-transform:uppercase;
color:var(--brandd);font-weight:700}
header h1{margin:8px 0 6px;font-size:1.72rem;letter-spacing:-.015em;line-height:1.22}
header .sub{color:var(--soft);font-size:.88rem}
.meta{display:flex;flex-wrap:wrap;gap:8px;margin-top:16px}
.tag{font-size:.70rem;font-weight:650;padding:3px 10px;border-radius:999px;
background:var(--brandl);color:var(--brandd);border:1px solid #CBE0DE}
.tag.grey{background:var(--paper2);color:var(--soft);border-color:var(--line)}
.kpis{display:flex;flex-wrap:wrap;gap:12px;padding:24px 48px 4px}
.kpi{flex:1 1 140px;border:1px solid var(--line);border-top:3px solid var(--brand);
border-radius:10px;padding:12px 14px;background:var(--paper)}
.kpi .l{font-size:.66rem;text-transform:uppercase;letter-spacing:.1em;color:var(--soft)}
.kpi .v{font-size:1.4rem;font-weight:660;margin-top:3px}
main{padding:14px 48px 40px}
h2{font-size:1.04rem;margin:30px 0 10px;color:var(--brandd);
border-bottom:1px solid var(--paper2);padding-bottom:5px}
p{margin:0 0 12px}
ul{margin:0 0 14px;padding-left:20px}
li{margin:0 0 7px}
.ref{display:inline-block;font-size:.70rem;color:var(--brandd);background:var(--brandl);
padding:1px 6px;border-radius:4px;margin-left:4px;white-space:nowrap}
.srcline{font-size:.72rem;color:var(--soft);font-style:italic;margin:-6px 0 18px}
blockquote{margin:16px 0;padding:8px 18px;border-left:3px solid var(--gold);
background:#FDFBF6;color:var(--soft);font-style:italic}
figure{margin:20px 0}
figure img{width:100%;border:1px solid var(--line);border-radius:10px;display:block}
figcaption{font-size:.74rem;color:var(--soft);margin-top:6px}
table{width:100%;border-collapse:collapse;font-size:.82rem;margin:8px 0 18px}
th{text-align:left;font-size:.66rem;text-transform:uppercase;letter-spacing:.09em;
color:var(--soft);background:var(--paper2);padding:8px 10px;border-bottom:1px solid var(--line)}
td{padding:7px 10px;border-bottom:1px solid var(--paper2);vertical-align:top}
.audit{display:flex;gap:10px;flex-wrap:wrap;margin:10px 0 18px}
.ck{flex:1 1 170px;border:1px solid var(--line);border-radius:9px;padding:10px 12px;
background:var(--paper)}
.ck .n{font-size:.68rem;color:var(--soft);text-transform:uppercase;letter-spacing:.08em}
.ck .s{font-weight:660;font-size:1.02rem;margin-top:2px}
.ok{color:var(--green)}.att{color:var(--amber)}.al{color:var(--red)}
.gauge{height:8px;border-radius:999px;background:var(--paper2);overflow:hidden;margin-top:7px}
.gauge>i{display:block;height:100%;background:var(--brand)}
footer{padding:18px 48px 26px;border-top:1px solid var(--line);color:var(--soft);
font-size:.74rem;background:var(--paper)}
@media print{body{background:#fff}.wrap{box-shadow:none;border:0;margin:0;max-width:none}
header,main,footer{padding-left:0;padding-right:0}}
@media(max-width:640px){header,main,footer,.kpis{padding-left:18px;padding-right:18px}}
"""


def _e(s: str) -> str:
    return html.escape(str(s or ""))


def _refspan(text: str) -> str:
    """Transforme ' (p. 12-14)' en pastille de reference."""
    import re
    return re.sub(r"\((p\.\s[^)]+)\)",
                  lambda m: f'<span class="ref">{_e(m.group(1))}</span>', _e(text))


def _img_tag(data: bytes, caption: str = "") -> str:
    b64 = base64.b64encode(data).decode("ascii")
    cap = f"<figcaption>{_e(caption)}</figcaption>" if caption else ""
    return (f'<figure><img alt="{_e(caption)}" '
            f'src="data:image/png;base64,{b64}">{cap}</figure>')


def _status_class(st: str) -> str:
    return {"ok": "ok", "attention": "att", "alerte": "al"}.get(st, "")


def render_report(rend: Rendition, tree: SummaryTree, doc_title: str,
                  audit: dict | None = None, images: dict[str, bytes] | None = None,
                  include_audit: bool = True, include_sources: bool = True) -> str:
    st = tree.stats or {}
    kpis = [
        ("Pages analysees", utils.human_int(st.get("pages", 0))),
        ("Mots", utils.human_int(st.get("mots", 0))),
        ("Sections", st.get("sections", 0)),
        ("Themes", len(tree.topics)),
    ]
    if audit:
        kpis.append(("Couverture", f"{audit['controles']['C3']['taux']:.1f} %"))

    parts = [
        "<!doctype html><html lang='fr'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width,initial-scale=1'>",
        f"<title>{_e(rend.title)}</title><style>{CSS}</style></head><body>",
        "<div class='wrap'>",
        "<header>",
        f"<div class='kicker'>SYNTHEA · {_e(rend.context_label)}</div>",
        f"<h1>{_e(rend.title)}</h1>",
        f"<div class='sub'>{_e(doc_title)} — {_e(tree.doc_type)} — "
        f"genere le {utils.now_fr()}</div>",
        "<div class='meta'>",
        f"<span class='tag'>{_e(rend.meta.get('public',''))}</span>",
        f"<span class='tag grey'>registre : {_e(rend.meta.get('registre',''))}</span>",
        f"<span class='tag grey'>langue : {_e(rend.language)}</span>",
    ]
    if rend.meta.get("traduction_moteur"):
        cov = rend.meta.get("traduction_couverture", 0)
        parts.append(f"<span class='tag grey'>traduction : "
                     f"{_e(rend.meta['traduction_moteur'])} "
                     f"({cov:.0%})</span>")
    parts.append("</div></header>")

    parts.append("<div class='kpis'>")
    for lab, val in kpis:
        parts.append(f"<div class='kpi'><div class='l'>{_e(lab)}</div>"
                     f"<div class='v'>{_e(val)}</div></div>")
    parts.append("</div><main>")

    if images and "01-couverture.png" in images:
        parts.append(_img_tag(images["01-couverture.png"], "Couverture generee"))

    for s in rend.sections:
        parts.append(f"<h2>{_e(s.get('heading',''))}</h2>")
        for p in s.get("paragraphs", []):
            parts.append(f"<p>{_refspan(p)}</p>")
        if s.get("bullets"):
            parts.append("<ul>" + "".join(f"<li>{_refspan(b)}</li>"
                                          for b in s["bullets"]) + "</ul>")
        if s.get("ref"):
            parts.append(f"<div class='srcline'>source : {_e(s['ref'])}</div>")

    if images:
        for key, cap in (("04-themes.png", "Poids des themes dans le corpus"),
                         ("05-densite-pages.png", "Densite de texte page par page"),
                         ("06-sections.png", "Decoupage en sections")):
            if key in images:
                parts.append(_img_tag(images[key], cap))

    if tree.keywords:
        parts.append("<h2>Mots-cles du corpus</h2><p>" +
                     ", ".join(_e(k) for k, _ in tree.keywords[:24]) + "</p>")

    if include_sources and tree.topics:
        parts.append("<h2>Themes identifies</h2><table><tr><th>Theme</th>"
                     "<th>Poids</th><th>Termes caracteristiques</th></tr>")
        for t in tree.topics:
            parts.append(f"<tr><td>{_e(t['libelle'])}</td>"
                         f"<td>{t['poids']:.1%}</td>"
                         f"<td>{_e(', '.join(t['termes'][:6]))}</td></tr>")
        parts.append("</table>")

    if include_audit and audit:
        parts.append("<h2>Verification de couverture (ARGUS)</h2>")
        parts.append(f"<p><strong>{_e(audit['verdict'])}</strong> — "
                     f"score global {audit['score']:.1f} / 100</p>")
        parts.append(f"<div class='gauge'><i style='width:{min(audit['score'],100):.1f}%'>"
                     f"</i></div><div class='audit'>")
        for code, c in audit["controles"].items():
            val = c.get("taux", c.get("n", c.get("unites_extraites", "")))
            val = f"{val:.1f} %" if isinstance(val, float) else str(val)
            parts.append(
                f"<div class='ck'><div class='n'>{code} · {_e(c['libelle'])}</div>"
                f"<div class='s {_status_class(c['statut'])}'>{_e(val)}</div></div>")
        parts.append("</div><ul>" + "".join(f"<li>{_e(r)}</li>"
                                            for r in audit["recommandations"]) + "</ul>")

    parts.append("</main><footer>")
    parts.append(f"Document genere par SYNTHEA — Document Intelligence Suite. "
                 f"Synthese {'extractive' if not rend.meta.get('version_abstractive') else 'extractive + reformulation'} "
                 f"tracable a la page. Empreinte corpus : "
                 f"{_e((audit or {}).get('empreinte', {}).get('sha1_corpus', 'n/a'))}.")
    parts.append("</footer></div></body></html>")
    return "".join(parts)


def render_fragment(rend: Rendition) -> str:
    """Rendu compact pour l affichage dans Streamlit (sans <html>)."""
    out = [f"<div class='sx-doc'><h1>{_e(rend.title)}</h1>",
           f"<div class='sx-sub'>{_e(rend.context_label)} · "
           f"{_e(rend.meta.get('public',''))} · registre "
           f"{_e(rend.meta.get('registre',''))}</div>"]
    for s in rend.sections:
        out.append(f"<h2>{_e(s.get('heading',''))}</h2>")
        for p in s.get("paragraphs", []):
            out.append(f"<p>{_refspan(p)}</p>")
        if s.get("bullets"):
            out.append("<ul>" + "".join(f"<li>{_refspan(b)}</li>"
                                        for b in s["bullets"]) + "</ul>")
    out.append("</div>")
    return "".join(out)
