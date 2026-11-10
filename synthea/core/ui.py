"""SYNTHEA - fragments d interface partages entre app.py et les onglets."""
from __future__ import annotations

import os

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


def df(rows: list[dict], height: int | None = None) -> None:
    if not rows:
        st.caption("aucune donnee")
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
