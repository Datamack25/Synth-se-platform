"""SYNTHEA - fragments d interface partages entre app.py et les onglets."""
from __future__ import annotations

import html
import os
import re

import pandas as pd
import streamlit as st

from . import utils


@st.cache_data(show_spinner=False)
def css() -> str:
    path = os.path.join(utils.ASSETS, "style.css")
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def hero(kicker: str, titre: str, sous: str) -> None:
    st.markdown(
        f"<div class='sx-hero'><div class='sx-kicker'>{kicker}</div>"
        f"<h1>{titre}</h1><p>{sous}</p></div>", unsafe_allow_html=True)


def kpis(items: list[tuple[str, str, str, str]]) -> None:
    cells = "".join(
        f"<div class='sx-kpi {cls}'><div class='lab'>{lab}</div>"
        f"<div class='val'>{val}</div><div class='sub'>{sub}</div></div>"
        for lab, val, sub, cls in items)
    st.markdown(f"<div class='sx-kpi-row'>{cells}</div>", unsafe_allow_html=True)


def badge(txt: str, kind: str = "grey") -> str:
    return f"<span class='sx-badge b-{kind}'>{txt}</span>"


def gauge(pct: float) -> str:
    cls = "" if pct >= 99 else ("warn" if pct >= 95 else "bad")
    return (f"<div class='sx-gauge {cls}'><i style='width:{min(pct, 100):.1f}%'></i>"
            f"</div>")


# --------------------------------------------------------------- tableaux
# st.dataframe dessine dans un canvas : aucune feuille de style ne peut en
# changer les couleurs. En theme sombre, le tableau restait donc noir au milieu
# d une page claire. Les tableaux courts sont rendus en HTML (classe .sx-table,
# entierement stylable) ; seuls les grands tableaux gardent st.dataframe, qui
# apporte le tri et le defilement.
SEUIL_TABLEAU_HTML = 80

_OUI = {"oui", "ok", "active", "actif", "conforme", "disponible", "vrai", "true"}
_NON = {"non", "ko", "absent", "indisponible", "echec", "alerte", "faux", "false",
        "desactivee", "desactive"}
_MOYEN = {"partiel", "attention", "degrade", "optionnel", "hybride"}


_NOMBRE = re.compile(r"-?[\d   .,]+\s?%?")


def _cellule(valeur) -> tuple[str, str]:
    """Retourne (texte echappe, classe css) pour une cellule."""
    if valeur is None:
        return "", ""
    txt = str(valeur)
    brut = txt.strip().lower()
    classe = ""
    if brut in _OUI:
        classe = "ok"
    elif brut in _NON or brut.startswith("non "):
        classe = "no"
    elif brut in _MOYEN:
        classe = "mid"
    elif _NOMBRE.fullmatch(txt.strip()):
        classe = "num"
    return html.escape(txt), classe


def table(rows: list[dict], note: str = "", max_lignes: int = 400) -> None:
    """Tableau HTML stylable, lisible quel que soit le theme de Streamlit."""
    if not rows:
        st.caption("aucune donnee")
        return
    colonnes: list[str] = []
    for r in rows:
        for k in r.keys():
            if k not in colonnes:
                colonnes.append(k)
    corps = []
    for r in rows[:max_lignes]:
        tds = []
        for c in colonnes:
            txt, classe = _cellule(r.get(c, ""))
            tds.append(f'<td class="{classe}">{txt}</td>' if classe else f"<td>{txt}</td>")
        corps.append("<tr>" + "".join(tds) + "</tr>")
    entete = "".join(f"<th>{html.escape(str(c))}</th>" for c in colonnes)
    st.markdown(
        f'<div class="sx-wrap"><table class="sx-table"><thead><tr>{entete}</tr>'
        f'</thead><tbody>{"".join(corps)}</tbody></table></div>',
        unsafe_allow_html=True)
    reste = len(rows) - max_lignes
    pied = note or ""
    if reste > 0:
        pied = (pied + " " if pied else "") + f"({reste} ligne(s) non affichee(s))"
    if pied:
        st.markdown(f"<div class='sx-note'>{html.escape(pied)}</div>",
                    unsafe_allow_html=True)


def df(rows: list[dict], height: int | None = None) -> None:
    """Affiche un tableau : HTML si court, composant natif si long."""
    if not rows:
        st.caption("aucune donnee")
        return
    if len(rows) <= SEUIL_TABLEAU_HTML:
        table(rows)
        return
    kw = {"height": height} if height else {}
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True, **kw)


MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "zip": "application/zip", "html": "text/html", "md": "text/markdown",
    "txt": "text/plain", "csv": "text/csv", "jpg": "image/jpeg", "png": "image/png",
    "json": "application/json",
}


def mime(nom: str) -> str:
    return MIME.get(os.path.splitext(nom)[1].lstrip(".").lower(),
                    "application/octet-stream")


def resultat(res, cle: str, apercu: bool = True) -> None:
    """Affiche le resultat d une operation de transformation."""
    if res is None:
        return
    if not res.ok:
        st.error(f"**{res.operation}** — {res.message}")
        return

    st.success(f"**{res.operation}** — {res.message}", icon="✔")
    st.caption(f"agent {res.agent} · {res.duree:.2f} s · "
               f"{res.poids_total / 1024:.0f} Ko · "
               f"{len(res.fichiers)} fichier(s)")
    for a in res.avertissements:
        st.warning(a, icon="⚠️")

    fichiers = res.fichiers
    if fichiers:
        cols = st.columns(min(3, len(fichiers)))
        for i, (nom, data) in enumerate(fichiers[:24]):
            with cols[i % len(cols)]:
                st.download_button(f"⬇ {utils.truncate(nom, 34)}", data, nom,
                                   mime(nom), key=f"dl_{cle}_{i}",
                                   use_container_width=True)
        if len(fichiers) > 24:
            st.caption(f"… et {len(fichiers) - 24} autres fichiers "
                       f"(utilise l archive ZIP)")

    if apercu:
        images = [(n, d) for n, d in fichiers
                  if n.lower().endswith((".jpg", ".jpeg", ".png"))][:4]
        if images:
            cols = st.columns(len(images))
            for c, (n, d) in zip(cols, images):
                with c:
                    st.image(d, caption=n, use_container_width=True)
        pdfs = [(n, d) for n, d in fichiers if n.lower().endswith(".pdf")]
        if pdfs and len(pdfs) == 1:
            _apercu_pdf(pdfs[0][1], cle)

    if res.details:
        with st.expander("Detail technique"):
            plats = {k: v for k, v in res.details.items()
                     if not isinstance(v, (list, dict))}
            if plats:
                df([{"element": k, "valeur": str(v)} for k, v in plats.items()])
            for k, v in res.details.items():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    st.markdown(f"**{k}**")
                    df(v[:150])
                elif isinstance(v, list) and v:
                    st.markdown(f"**{k}** : " + ", ".join(str(x) for x in v[:60]))


def _apercu_pdf(data: bytes, cle: str, pages: int = 2) -> None:
    """Miniatures des premieres pages d un PDF produit."""
    try:
        from . import doctools as dt
        rendus = dt.render_pages(data, list(range(1, pages + 1)), dpi=70)
    except Exception:
        return
    if not rendus:
        return
    with st.expander("Apercu", expanded=True):
        cols = st.columns(len(rendus))
        for c, (no, img) in zip(cols, rendus):
            with c:
                st.image(img, caption=f"page {no}", use_container_width=True)


def fichiers_streamlit(uploads) -> list[tuple[str, bytes]]:
    """Convertit des UploadedFile Streamlit en couples (nom, octets)."""
    if not uploads:
        return []
    if not isinstance(uploads, list):
        uploads = [uploads]
    return [(u.name, u.getvalue()) for u in uploads]
