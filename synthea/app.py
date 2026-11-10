"""SYNTHEA - Document Intelligence Suite
=========================================
Plateforme Streamlit de synthese documentaire multi-agents.

Lancer en local :  streamlit run app.py
"""
from __future__ import annotations

import os

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from core import (agents, budget, contexts, exporters, extraction, html_report,
                  imaging, lexicons, llm, ml, qa, summarizer, tab_transform,
                  translation, ui, utils, websearch)

# =====================================================================
# Configuration
# =====================================================================
st.set_page_config(
    page_title="SYNTHEA — Document Intelligence Suite",
    page_icon="◆",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data(show_spinner=False)
def _css() -> str:
    path = os.path.join(utils.ASSETS, "style.css")
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


st.markdown(f"<style>{_css()}</style>", unsafe_allow_html=True)

SS = st.session_state
SS.setdefault("state", None)
SS.setdefault("chat", [])
SS.setdefault("custom_images", {})
SS.setdefault("veille_manuelle", None)


# =====================================================================
# Fragments d interface
# =====================================================================
def hero(kicker: str, titre: str, sous: str) -> None:
    st.markdown(
        f"<div class='sx-hero'><div class='sx-kicker'>{kicker}</div>"
        f"<h1>{titre}</h1><p>{sous}</p></div>", unsafe_allow_html=True)


def kpis(items: list[tuple[str, str, str, str]]) -> None:
    """items = [(libelle, valeur, sous-titre, classe)]"""
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


def need_doc() -> bool:
    if SS["state"] and SS["state"].get("doc"):
        return False
    st.info("Importe un ou plusieurs documents dans le panneau de gauche, "
            "puis lance l analyse. Les onglets se remplissent ensuite.", icon="ℹ️")
    return True


def df(rows: list[dict], height: int | None = None) -> None:
    """Rendu unique pour toute l application (cf. core.ui.df) : tableau HTML
    stylable pour les listes courtes, composant natif au-dela."""
    ui.df(rows, height)


def table(rows: list[dict], note: str = "") -> None:
    ui.table(rows, note)


# =====================================================================
# Panneau lateral
# =====================================================================
def sidebar() -> None:
    st.sidebar.markdown(
        "<div class='sx-logo'><div class='mark'></div>"
        "<div class='word'><b>SYNTHEA</b><i>document intelligence</i></div></div>"
        "<div class='sx-logo-sub'>Synthese documentaire multi-agents — "
        "jusqu a 2000 pages</div>",
        unsafe_allow_html=True)

    files = st.sidebar.file_uploader(
        "Documents a analyser",
        type=["pdf", "docx", "pptx", "xlsx", "xlsm", "csv", "tsv", "html", "htm",
              "txt", "md", "json", "jpg", "jpeg", "png", "tif", "tiff", "webp",
              "epub", "zip", "rtf"],
        accept_multiple_files=True,
        help="PDF, Word, PowerPoint, Excel, HTML, JPEG, CSV, EPUB, ZIP. "
             "Plusieurs fichiers sont fusionnes en un seul corpus pagine.",
    )

    with st.sidebar.expander("Objectif et format", expanded=True):
        objectif = st.selectbox(
            "Que veux-tu faire de ce document ?", list(budget.OBJECTIFS.keys()),
            index=list(budget.OBJECTIFS.keys()).index("restitution_fidele"),
            format_func=lambda k: budget.OBJECTIFS[k]["libelle"])
        st.caption(budget.OBJECTIFS[objectif]["description"])
        ajustement = st.slider(
            "Longueur de la synthese", 0.4, 2.0, 1.0, 0.1,
            help="1,0 = taille calculee automatiquement d apres le volume du "
                 "document. En dessous : plus court. Au-dessus : plus detaille.")
        st.caption("La taille est deduite du volume : un livre de 1 000 pages "
                   "donne une synthese de 5 a 22 pages selon l objectif.")

    with st.sidebar.expander("Analyse", expanded=False):
        profondeur = st.select_slider(
            "Profondeur", options=["auto"] + list(summarizer.DEPTHS.keys()),
            value="auto",
            format_func=lambda k: ("Deduite de l objectif" if k == "auto"
                                   else summarizer.DEPTHS[k]["libelle"].split(" (")[0]))
        if profondeur != "auto":
            st.caption(summarizer.DEPTHS[profondeur]["libelle"])
        max_pages = st.number_input("Limite de pages", 10, 5000, 2000, step=50)
        max_sections = st.slider("Sections de synthese", 4, 24, 12)
        ocr = st.toggle("OCR des images et PDF scannes", value=True)
        caps = extraction.capabilities()
        diag = extraction.ocr_diagnostic()
        if ocr and not diag["actif"]:
            st.caption(f"\u26a0 {diag['message']}")
            with st.popover("Comment l activer"):
                st.markdown(f"**{diag['message']}**\n\n{diag['remede']}")
        elif ocr:
            st.caption(f"\u2714 {diag['message']}")

    with st.sidebar.expander("Restitution", expanded=True):
        labels = contexts.context_labels()
        ctx_keys = st.multiselect(
            "Contextes de presentation", options=list(labels.keys()),
            default=["comite_direction", "pitch_entrepreneurial"],
            format_func=lambda k: labels[k])
        langue = st.selectbox("Langue du document", lexicons.LANGS, index=0,
                              format_func=lambda c: lexicons.LANG_LABELS[c])
        cibles = st.multiselect(
            "Traduire vers", [c for c in lexicons.LANGS],
            default=["en", "ht"],
            format_func=lambda c: lexicons.LANG_LABELS[c])

    with st.sidebar.expander("Visuels et veille", expanded=False):
        visuels = st.toggle("Generer les illustrations", value=True)
        palette = st.selectbox("Palette", list(imaging.PALETTES.keys()), index=1)
        veille = st.toggle("Recherche ciblee sur internet", value=False,
                           help="La plateforme fonctionne sans internet : la base "
                                "locale de 57 CSV est toujours interrogee d abord.")
        thematique = st.text_input("Thematique de veille", "",
                                   placeholder="ex. LCB-FT, sanctions, fiscalite")

    with st.sidebar.expander("Modele de langue (optionnel)", expanded=False):
        stt = llm.status()
        st.caption(f"module anthropic : {'oui' if stt['module_anthropic'] else 'non'} "
                   f"· cle API : {'presente' if stt['cle_presente'] else 'absente'}")
        use_llm = st.toggle("Reformulation abstractive", value=False,
                            disabled=not stt["actif"],
                            help="Sans cle API, SYNTHEA reste en mode extractif : "
                                 "chaque phrase provient litteralement du document.")

    go = st.sidebar.button("Lancer les 11 agents d analyse", type="primary",
                           use_container_width=True, disabled=not files)

    if SS["state"]:
        st.sidebar.divider()
        d = SS["state"]["doc"]
        a = SS["state"].get("audit") or {}
        st.sidebar.success(f"**{utils.truncate(d.title, 34)}**\n\n"
                           f"{utils.human_int(d.n_pages)} pages · "
                           f"{utils.human_int(d.n_words)} mots\n\n"
                           f"ARGUS {a.get('score', 0):.1f}/100")
        if st.sidebar.button("Reinitialiser la session", use_container_width=True):
            SS["state"] = None
            SS["chat"] = []
            SS["custom_images"] = {}
            st.rerun()

    if go and files:
        run_pipeline(files, {
            "profondeur": profondeur, "max_pages": int(max_pages),
            "objectif": objectif, "ajustement_longueur": float(ajustement),
            "max_sections": max_sections, "ocr": ocr, "langue": langue,
            "contextes": ctx_keys or ["comite_direction"],
            "langues_cibles": cibles, "visuels": visuels, "palette": palette,
            "veille": veille, "veille_thematique": thematique,
            "use_llm": use_llm,
        })


def run_pipeline(files, options: dict) -> None:
    payload = [(f.name, f.getvalue()) for f in files]
    bar = st.progress(0.0, text="initialisation…")
    orch = agents.Orchestrator(options)

    def prog(frac: float, msg: str) -> None:
        bar.progress(min(max(frac, 0.0), 1.0), text=msg)

    with st.spinner("Les agents travaillent…"):
        state = orch.run(payload, progress=prog)
    bar.empty()
    if not state.get("doc"):
        st.error("Aucun contenu exploitable n a pu etre extrait. "
                 "Verifie le format des fichiers ou active l OCR.")
        return
    SS["state"] = state
    SS["chat"] = []
    st.rerun()


# =====================================================================
# Onglet 1 - Accueil
# =====================================================================
def tab_accueil() -> None:
    hero("Document intelligence suite",
         "SYNTHEA",
         "Seize agents lisent un document de 1 a 2000 pages, le resument a trois "
         "niveaux, le restituent dans douze contextes de presentation, le "
         "traduisent en cinq langues, l illustrent, repondent a tes questions et "
         "verifient eux-memes que rien n a ete oublie.")

    lx = lexicons.stats()
    caps = extraction.capabilities()
    net = websearch.status()

    if SS["state"]:
        d, t = SS["state"]["doc"], SS["state"]["tree"]
        a = SS["state"].get("audit") or {}
        kpis([
            ("Pages analysees", utils.human_int(d.n_pages), d.title[:28], "brand"),
            ("Mots", utils.human_int(d.n_words), t.doc_type[:28], "brand"),
            ("Constats tracables", str(len(t.all_claims)),
             f"{len(t.sections)} sections", "ok"),
            ("Score ARGUS", f"{a.get('score', 0):.1f}", a.get("verdict", "")[:30],
             "ok" if a.get("score", 0) >= 97 else "warn"),
        ])
    else:
        kpis([
            ("Fichiers CSV", str(lx["fichiers_csv"]), "base de connaissance locale", "brand"),
            ("Metiers", str(lx["metiers"]), f"{lx['secteurs']} secteurs", "brand"),
            ("Entrees de vocabulaire", utils.human_int(lx["lignes_totales"]),
             "termes, sigles, formules", "brand"),
            ("Langues", str(lx["langues"]), "fr · en · es · pt · ht", "brand"),
        ])

    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown("#### Ce que fait la plateforme")
        st.markdown("""
- **Lire tous les formats** : PDF (texte et scanne), Word, PowerPoint, Excel,
  HTML, JPEG, CSV, EPUB, archives ZIP. Chaque unite logique devient une page
  numerotee, avec son empreinte.
- **Resumer a trois niveaux** : un digest par page, une synthese par section,
  un resume executif. Chaque phrase garde sa reference de page.
- **Restituer selon le contexte** : pitch entrepreneurial, comite de direction,
  discours de campagne, conseil d administration, note administrative, cours
  magistral, memo de due diligence, fiche de lecture, atelier grand public,
  point d equipe, conference, note de conformite.
- **Traduire** en francais, anglais, espagnol, portugais et creole haitien.
- **Illustrer** : couvertures, schemas, nuages de mots, graphiques,
  infographies, cartons de citation, retouche des images importees.
- **Se verifier** : neuf controles de couverture et de fidelite, page par page.
- **Dialoguer** : questions-reponses sourcees sur le contenu du document.
- **Chercher** : base locale de 57 CSV d abord, internet en complement ciblé.
        """)
    with c2:
        st.markdown("#### Etat du moteur")
        rows = [
            {"brique": "Extraction PDF", "etat": "oui" if caps["pdf"] else "non"},
            {"brique": "Word / PowerPoint / Excel",
             "etat": "oui" if (caps["docx"] and caps["pptx"] and caps["xlsx"]) else "partiel"},
            {"brique": "OCR images et scans",
             "etat": "oui" if extraction.ocr_diagnostic()["actif"]
                     else "non \u2014 voir ci-dessous"},
            {"brique": "Apprentissage automatique",
             "etat": "scikit-learn" if ml.SKLEARN else "indisponible"},
            {"brique": "Traduction", "etat": translation.ENGINES[translation.best_engine()]},
            {"brique": "Recherche internet", "etat": net["mode"]},
            {"brique": "Reformulation abstractive",
             "etat": "active" if llm.available() else "desactivee (mode extractif)"},
        ]
        df(rows)
        st.caption("Aucune brique optionnelle n est necessaire : sans OCR, sans "
                   "internet et sans modele de langue, la plateforme reste "
                   "pleinement fonctionnelle.")
        diag = extraction.ocr_diagnostic()
        if not diag["actif"]:
            with st.expander("Activer l OCR"):
                st.markdown(
                    f"**{diag['message']}**\n\n"
                    "L OCR repose sur deux briques distinctes :\n\n"
                    f"- le paquet Python `pytesseract` : "
                    f"{'installe' if diag['module_python'] else 'absent'} ;\n"
                    f"- le moteur `tesseract` (binaire systeme) : "
                    f"{'installe' if diag['binaire'] else 'absent'}.\n\n"
                    f"{diag['remede']}")
        elif diag["langues"]:
            st.caption(f"OCR : tesseract {diag['version']}, langues disponibles — "
                       + ", ".join(diag["langues"][:12]))

    st.divider()
    st.markdown("#### Les seize agents")
    st.markdown(agents.agent_cards_html(), unsafe_allow_html=True)


# =====================================================================
# Onglet 2 - Import et extraction
# =====================================================================
def tab_import() -> None:
    hero("Agent ATLAS", "Import et extraction",
         "Chaque fichier est decoupe en unites logiques : une page de PDF, une "
         "diapositive, une feuille de calcul, une section de document long. "
         "Chaque unite porte son numero, son fichier d origine et son empreinte.")
    if need_doc():
        caps = extraction.capabilities()
        df([{"capacite": k, "disponible": "oui" if v else "non"}
            for k, v in caps.items()])
        return

    s = SS["state"]
    d = s["doc"]
    kpis([
        ("Fichiers", str(len(d.files)), "corpus fusionne", "brand"),
        ("Unites extraites", utils.human_int(d.n_pages),
         f"limite {d.meta.get('max_pages')}", "brand"),
        ("Mots", utils.human_int(d.n_words), f"{utils.human_int(d.n_chars)} caracteres", "brand"),
        ("Pages sans texte", str(len(d.empty_pages)),
         "OCR recommande" if d.empty_pages else "aucune",
         "ok" if not d.empty_pages else "warn"),
    ])

    st.markdown("#### Fichiers importes")
    df([{**f, "octets": utils.human_int(f["octets"])} for f in d.files])

    if d.meta.get("tronque"):
        st.warning(f"Le corpus a ete tronque a {d.meta.get('max_pages')} unites. "
                   f"Augmente la limite dans le panneau de gauche ou scinde le document.")

    st.markdown("#### Ossature detectee")
    outline = s.get("outline") or []
    if outline:
        df(outline[:300], height=240)
    else:
        st.caption("aucun titre apparent : le document a ete decoupe par volume de texte")

    st.markdown("#### Explorateur de pages")
    c1, c2 = st.columns([1, 3])
    with c1:
        idx = st.number_input("Page", 1, d.n_pages, 1, step=1)
        page = d.page(int(idx))
        if page:
            st.markdown(
                badge(page.unit, "brand") + " " +
                badge(f"{page.word_count} mots", "grey") + " " +
                (badge("OCR", "amber") if page.ocr else "") + " " +
                (badge("vide", "red") if page.is_empty else badge("ok", "green")),
                unsafe_allow_html=True)
            st.caption(f"fichier : {page.source_file}\n\nempreinte : {page.sha1}")
            if page.warning:
                st.warning(page.warning)
    with c2:
        if page:
            dig = s["tree"].page_digests.get(page.index, "")
            if dig:
                st.markdown(f"**Digest de page** — {dig}")
            st.text_area("Texte extrait", page.text or "(aucun texte)", height=320,
                         label_visibility="collapsed")


# =====================================================================
# Onglet 3 - Agents
# =====================================================================
def tab_agents() -> None:
    hero("Orchestration", "Les seize agents",
         "Chaque agent a un role unique, des entrees et des sorties explicites. "
         "Le journal ci-dessous trace chacune de leurs actions, avec sa duree.")

    st.markdown(agents.agent_cards_html(), unsafe_allow_html=True)

    if not SS["state"]:
        st.caption("Le journal apparait apres la premiere analyse.")
        return
    s = SS["state"]
    st.divider()
    c1, c2 = st.columns([3, 2], gap="large")
    with c1:
        st.markdown("#### Journal d execution")
        st.markdown(s["journal"].to_html(), unsafe_allow_html=True)
    with c2:
        st.markdown("#### Temps par agent")
        rows = [{"agent": k, "duree_s": round(v, 2)}
                for k, v in sorted(s["timings"].items(), key=lambda kv: -kv[1])]
        df(rows)
        st.markdown("#### Options de la session")
        df([{"parametre": k, "valeur": str(v)} for k, v in s["options"].items()])

    with st.expander("Exporter le journal"):
        st.download_button("journal-agents.csv",
                           pd.DataFrame(s["journal"].to_rows()).to_csv(index=False)
                           .encode("utf-8"),
                           "journal-agents.csv", "text/csv")


# =====================================================================
# Onglet 4 - Analyse et ML
# =====================================================================
def tab_analyse() -> None:
    hero("Agent PRISME", "Analyse semantique et apprentissage",
         "TF-IDF pour les mots-cles, factorisation NMF pour les themes, KMeans "
         "pour le regroupement des blocs, Naive Bayes pour la typologie, "
         "regression logistique pour le classement des phrases.")
    if need_doc():
        return
    s = SS["state"]
    t, d = s["tree"], s["doc"]
    stt = t.stats or {}
    lis = stt.get("lisibilite") or {}

    kpis([
        ("Type de document", t.doc_type[:24], "Naive Bayes", "brand"),
        ("Themes", str(len(t.topics)), "factorisation NMF", "brand"),
        ("Classement des phrases",
         "supervise" if stt.get("modele_supervise") else "heuristique",
         f"{stt.get('echantillon_entrainement', 0)} phrases d entrainement", "brand"),
        ("Lisibilite", str(lis.get("indice_lisibilite", "n/a")),
         lis.get("niveau", ""), "brand"),
    ])

    c1, c2 = st.columns(2, gap="large")
    with c1:
        st.markdown("#### Themes identifies")
        if t.topics:
            st.image(imaging.chart_topics(t.topics, s["options"]["palette"]),
                     use_container_width=True)
            df([{"theme": tp["libelle"], "poids": f"{tp['poids']:.1%}",
                 "termes": ", ".join(tp["termes"][:7])} for tp in t.topics])
        else:
            st.caption("corpus trop court pour une decouverte de themes")
    with c2:
        st.markdown("#### Densite de texte par page")
        st.image(imaging.chart_page_density(
            [(p.index, p.word_count) for p in d.pages], s["options"]["palette"]),
            use_container_width=True)
        st.markdown("#### Decoupage en sections")
        st.image(imaging.chart_sections(
            [(x.title, x.page_start, x.page_end) for x in t.sections],
            s["options"]["palette"]), use_container_width=True)

    st.divider()
    c1, c2 = st.columns([2, 3], gap="large")
    with c1:
        st.markdown("#### Mots-cles (TF-IDF)")
        df([{"terme": k, "poids": round(v, 4)} for k, v in t.keywords[:40]], height=360)
    with c2:
        st.markdown("#### Entites reperees")
        tabs = st.tabs(["Montants", "Pourcentages", "Dates", "Organisations",
                        "Sigles", "Noms propres", "Pays"])
        keys = ["montants", "pourcentages", "dates", "organisations",
                "sigles_connus", "noms_propres", "pays"]
        for tb, k in zip(tabs, keys):
            with tb:
                vals = (t.entities or {}).get(k, [])
                if k == "sigles_connus":
                    conn = {s_["sigle"]: s_["signification"] for s_ in lexicons.sigles()}
                    df([{"sigle": v, "signification": conn.get(v, "")} for v in vals])
                    inc = (t.entities or {}).get("sigles_inconnus", [])
                    if inc:
                        st.caption("sigles non repertories : " + ", ".join(inc[:18]))
                else:
                    df([{k: v} for v in vals])

    with st.expander("Lisibilite et statistiques detaillees"):
        df([{"indicateur": k, "valeur": v} for k, v in lis.items()])
        df([{"indicateur": k, "valeur": str(v)} for k, v in stt.items()
            if k not in ("lisibilite", "secteurs_detectes")])


# =====================================================================
# Onglet 5 - Syntheses
# =====================================================================
def tab_syntheses() -> None:
    hero("Agents SCRIBE et CAMELEON", "Syntheses par contexte",
         "La meme analyse, restituee selon douze contextes de presentation. "
         "Chaque constat conserve sa reference de page, ce qui rend la synthese "
         "verifiable ligne a ligne.")
    if need_doc():
        return
    s = SS["state"]
    t, d = s["tree"], s["doc"]

    bud = s.get("budget")
    ctrl = s.get("controle_budget") or {}
    if bud is not None:
        cls = {"conforme": "ok", "trop court": "warn",
               "trop long": "warn"}.get(ctrl.get("statut", ""), "brand")
        kpis([
            ("Objectif", bud.objectif_libelle, bud.mode[:34], "brand"),
            ("Format vise", f"{bud.pages_cible:.0f} pages",
             f"{bud.mots_cible} mots · {bud.sections} sections", "brand"),
            ("Synthese produite",
             f"{ctrl.get('pages_produites', '—')} pages",
             f"{ctrl.get('mots_produits', 0)} mots", cls),
            ("Compression", f"{bud.compression_visee:.2f} %",
             f"depuis {utils.human_int(d.n_words)} mots", "brand"),
        ])
        st.caption(bud.resume_long())
        with st.expander("Comment la taille est calculee"):
            st.markdown(
                "La synthese croit comme une racine du volume : "
                "`pages = 0,85 x volume^0,38 x densite_objectif`. "
                "C est ce qui donne 5 a 22 pages pour un livre de 1 000 pages "
                "selon ce que tu veux en faire, au lieu d une longueur fixe.")
            df(budget.previsions(d.n_pages, d.n_words))
            st.markdown("**Loi d echelle appliquee**")
            df(budget.exemples_echelle())

    st.markdown("#### Resume executif")
    st.markdown(f"<div class='sx-card'>{summarizer.quick_abstract(t, 190)}</div>",
                unsafe_allow_html=True)
    for b in summarizer.bullet_points(t, 8):
        st.markdown(f"- {b}")

    st.divider()
    labels = contexts.context_labels()
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        key = st.selectbox("Contexte de restitution", list(labels.keys()),
                           format_func=lambda k: labels[k],
                           index=list(labels.keys()).index(
                               s["options"]["contextes"][0]
                               if s["options"]["contextes"] else "comite_direction"))
    with c2:
        lf = st.slider("Longueur", 0.4, 1.8, 1.0, 0.1,
                       help="facteur applique a la longueur cible du contexte")
    with c3:
        refs = st.toggle("Afficher les references de page", value=True)

    ctx = lexicons.contextes_index().get(key, {})
    st.caption(f"**Public** : {ctx.get('public','')} · **registre** : "
               f"{ctx.get('registre','')} · **ton** : {ctx.get('ton','')} · "
               f"**cible** : {ctx.get('longueur_cible_mots','')} mots")
    with st.expander("Regles de style appliquees par CAMELEON"):
        for r in (ctx.get("regles", "") or "").split(";"):
            if r.strip():
                st.markdown(f"- {r.strip()}")
        st.markdown("**Trames narratives disponibles**")
        df(lexicons.trames())

    rend = contexts.render(t, key, d.title, lang=s["options"]["langue"],
                           with_refs=refs, length_factor=lf,
                           use_llm=s["options"].get("use_llm", False))
    SS["rendition"] = rend

    v1, v2 = st.tabs(["Rendu professionnel", "Markdown"])
    with v1:
        st.markdown(html_report.render_fragment(rend), unsafe_allow_html=True)
        if rend.meta.get("version_abstractive"):
            with st.expander("Version reformulee (modele de langue)"):
                st.markdown(rend.meta["version_abstractive"])
    with v2:
        st.code(rend.to_markdown(refs), language="markdown")

    st.divider()
    st.markdown("#### Detail des sections")
    for sec in t.sections:
        with st.expander(f"{sec.title}  —  {sec.ref}  "
                         f"({len(sec.claims)} constats)"):
            st.caption("mots-cles : " + ", ".join(sec.keywords))
            for c in sec.claims:
                st.markdown(f"- {c.text} <span class='sx-ref'>{c.ref}</span>",
                            unsafe_allow_html=True)

    with st.expander("Digests page par page"):
        rows = [{"page": p, "digest": v} for p, v in sorted(t.page_digests.items()) if v]
        df(rows, height=400)
        if not rows:
            st.caption("profondeur « rapide » : les digests de page ne sont pas produits")


# =====================================================================
# Onglet 6 - Traductions
# =====================================================================
def tab_traductions() -> None:
    hero("Agent BABEL", "Traductions en cinq langues",
         "Francais, anglais, espagnol, portugais, creole haitien. Le moteur "
         "hors ligne s appuie sur les 57 CSV multilingues et annonce son taux de "
         "couverture : une traduction assistee honnete plutot qu une illusion.")
    if need_doc():
        return
    s = SS["state"]
    est = translation.engine_status()
    df([{"moteur": translation.ENGINES[k], "disponible": "oui" if v["disponible"] else "non",
         "detail": v["detail"]} for k, v in est.items()])

    rend = SS.get("rendition") or list(s["renditions"].values())[0]
    c1, c2 = st.columns([1, 1])
    with c1:
        cible = st.selectbox("Langue cible", [c for c in lexicons.LANGS
                                              if c != rend.language],
                             format_func=lambda c: lexicons.LANG_LABELS[c])
    with c2:
        moteur = st.selectbox(
            "Moteur", [k for k, v in est.items() if v["disponible"]],
            format_func=lambda k: translation.ENGINES[k],
            index=[k for k, v in est.items() if v["disponible"]].index(
                translation.best_engine()))

    if st.button("Traduire la restitution affichee", type="primary"):
        with st.spinner("BABEL traduit…"):
            SS["trad"] = translation.translate_rendition(rend, cible, moteur)

    tr = SS.get("trad")
    if tr:
        m = tr.meta
        st.markdown(
            badge(f"moteur reellement utilise : {m.get('traduction_moteur')}", "brand")
            + " " + badge(f"couverture {m.get('traduction_couverture', 0):.0%}",
                          "green" if m.get("traduction_couverture", 0) > 0.8 else "amber")
            + (" " + badge("repli automatique", "amber") if m.get("traduction_repli") else ""),
            unsafe_allow_html=True)
        if m.get("traduction_notes"):
            st.caption(m["traduction_notes"])
        a, b = st.columns(2, gap="large")
        with a:
            st.markdown(f"##### {lexicons.LANG_LABELS[rend.language]} (source)")
            st.markdown(html_report.render_fragment(rend), unsafe_allow_html=True)
        with b:
            st.markdown(f"##### {lexicons.LANG_LABELS[tr.language]}")
            st.markdown(html_report.render_fragment(tr), unsafe_allow_html=True)
        st.download_button(f"synthese-{tr.language}.md",
                           tr.to_markdown().encode("utf-8"),
                           f"synthese-{tr.language}.md", "text/markdown")

    st.divider()
    st.markdown("#### Traductions produites par le pipeline")
    rows = []
    for ckey, per_lang in (s.get("traductions") or {}).items():
        for lg, r in per_lang.items():
            rows.append({"contexte": ckey, "langue": lexicons.LANG_LABELS[lg],
                         "moteur": r.meta.get("traduction_moteur"),
                         "couverture": f"{r.meta.get('traduction_couverture', 0):.0%}"})
    df(rows)

    st.markdown("#### Glossaire du document en cinq langues")
    gl = translation.document_glossary(s["doc"].full_text()[:300000], cible, limit=80)
    df(gl, height=400)
    if gl:
        st.download_button("glossaire-document.csv",
                           pd.DataFrame(gl).to_csv(index=False).encode("utf-8"),
                           "glossaire-document.csv", "text/csv")


# =====================================================================
# Onglet 7 - Lexiques metiers
# =====================================================================
def tab_lexiques() -> None:
    lx = lexicons.stats()
    hero("Agent LEXIS", "Lexiques metiers hors ligne",
         f"{lx['fichiers_csv']} fichiers CSV, {utils.human_int(lx['lignes_totales'])} "
         f"entrees, {lx['metiers']} metiers repartis sur {lx['secteurs']} secteurs, "
         f"du vocabulaire technique au registre familier. C est cette base qui "
         f"permet a la plateforme de fonctionner sans internet.")

    kpis([
        ("Fichiers CSV", str(lx["fichiers_csv"]), "data/lexicons/", "brand"),
        ("Termes sectoriels", utils.human_int(lx["termes_sectoriels"]),
         f"{lx['secteurs']} secteurs", "brand"),
        ("Sigles", str(lx["sigles"]), "developpes automatiquement", "brand"),
        ("Expressions familieres", str(lx["expressions_familieres"]),
         "argot, idiomes, registre courant", "brand"),
    ])

    t1, t2, t3, t4, t5, t6 = st.tabs(["Recherche", "Metiers", "Secteurs",
                                      "Inventaire des CSV", "Dans ce document",
                                      "➕ Enrichir la base"])
    with t1:
        c1, c2 = st.columns([3, 2])
        with c1:
            q = st.text_input("Terme, definition ou traduction", "",
                              placeholder="ex. beneficiaire effectif, covenant, levain")
        with c2:
            sect = st.selectbox("Limiter a un secteur", ["(tous)"] + lexicons.secteurs())
        res = lexicons.chercher_terme(q, limit=120,
                                      secteur=None if sect == "(tous)" else sect)
        st.caption(f"{len(res)} resultat(s)")
        df([{"terme": r["terme_fr"], "registre": r["registre"],
             "definition": r["definition_fr"], "en": r["en"], "es": r["es"],
             "pt": r["pt"], "ht": r["ht"], "secteur": r["secteur"]} for r in res],
           height=430)
    with t2:
        q = st.text_input("Chercher un metier", "", placeholder="ex. analyste, macon, pilote")
        rows = lexicons.chercher_metier(q, limit=200) if q else lexicons.metiers()
        df([{"code": m["code"], "metier": m["metier_fr"], "secteur": m["secteur"],
             "famille": m["famille"], "en": m["en"], "es": m["es"], "pt": m["pt"],
             "ht": m["ht"], "mots-cles": m["mots_cles"]} for m in rows], height=470)
    with t3:
        tps = lexicons.termes_par_secteur()
        rows = [{"secteur": k, "termes": len(v),
                 "metiers": len(lexicons.metiers_du_secteur(k)),
                 "exemples": ", ".join(r["terme_fr"] for r in v[:6])}
                for k, v in sorted(tps.items())]
        df(rows, height=470)
    with t4:
        df(lexicons.inventory(), height=470)
        st.caption("Les CSV sont regenerables : `python scripts/build_all_lexicons.py`. "
                   "Ajoute tes propres termes dans les listes des scripts build_0*.py.")
    with t5:
        if not SS["state"]:
            st.caption("Lance une analyse pour voir le vocabulaire detecte.")
        else:
            lex = SS["state"].get("lexis") or {}
            st.markdown("##### Secteurs detectes dans le document")
            df([{"secteur": s_, "termes trouves": n,
                 "exemples": ", ".join(ex)} for s_, n, ex in lex.get("secteurs", [])])
            st.markdown("##### Vocabulaire metier present")
            df([{"terme": r.get("terme_fr"), "registre": r.get("registre"),
                 "secteur": r.get("secteur"), "definition": r.get("definition_fr")}
                for r in lex.get("jargon", [])], height=330)
            st.markdown("##### Sigles rencontres")
            df(lex.get("sigles", []))
    with t6:
        tab_enrichir()


# =====================================================================
# Onglet 7 bis - Enrichir la base de lexiques
# =====================================================================
def _res_enrichir(res: dict) -> None:
    if not res:
        return
    if res.get("ok"):
        st.success(res.get("message", "enregistre"), icon="✔")
        if res.get("sauvegarde"):
            st.caption(f"copie de securite : {res['sauvegarde']}")
    else:
        st.warning(res.get("message", "rien a enregistrer"), icon="⚠️")


def tab_enrichir() -> None:
    from core import lexicon_edit as led

    st.caption("Tous les fichiers de la base sont modifiables ici. Chaque "
               "enregistrement cree d abord une copie de securite, puis recharge "
               "la base : les nouvelles entrees sont utilisables immediatement "
               "par LEXIS, BABEL et la recherche.")

    a, b, c, d_, e = st.tabs(["Un terme", "Un metier", "Importer un CSV",
                              "Nouveau lexique", "Sauvegardes"])

    # ---------------- un terme --------------------------------------
    with a:
        sect = led.fichiers_sectoriels()
        c1, c2 = st.columns([2, 1])
        with c1:
            fich = st.selectbox("Lexique a enrichir", sect,
                                format_func=lambda f: f.replace(".csv", "")
                                .split("_lex_")[-1].replace("_", " "),
                                key="enr_f")
        with c2:
            registre = st.selectbox("Registre",
                                    ["technique", "courant", "familier", "sigle"],
                                    key="enr_r")
        terme = st.text_input("Terme en francais", "", key="enr_t",
                              placeholder="ex. gel des avoirs")
        definition = st.text_area("Definition", "", key="enr_d", height=80,
                                  placeholder="une phrase, sans jargon inutile")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            en = st.text_input("English", "", key="enr_en")
        with c2:
            es = st.text_input("Espanol", "", key="enr_es")
        with c3:
            pt = st.text_input("Portugues", "", key="enr_pt")
        with c4:
            ht = st.text_input("Kreyol", "", key="enr_ht")
        if st.button("Ajouter ce terme", type="primary", key="enr_go",
                     use_container_width=True):
            if not terme.strip():
                st.warning("Indique au moins le terme.", icon="⚠️")
            else:
                _res_enrichir(led.ajouter_terme(fich, terme, registre, definition,
                                                en, es, pt, ht))
        with st.expander("Contenu actuel de ce lexique"):
            _, lignes = led.lire(fich)
            df([{k: v for k, v in l.items() if k != "metiers"} for l in lignes])

    # ---------------- un metier -------------------------------------
    with b:
        c1, c2 = st.columns(2)
        with c1:
            met = st.text_input("Intitule du metier", "", key="met_n",
                                placeholder="ex. Analyste fraude moyens de paiement")
            secteur = st.selectbox("Secteur", lexicons.secteurs(), key="met_s")
        with c2:
            famille = st.text_input("Famille", "", key="met_f",
                                    placeholder="ex. Conformite")
            mots = st.text_input("Mots-cles (separes par ;)", "", key="met_k")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            men = st.text_input("English", "", key="met_en")
        with c2:
            mes = st.text_input("Espanol", "", key="met_es")
        with c3:
            mpt = st.text_input("Portugues", "", key="met_pt")
        with c4:
            mht = st.text_input("Kreyol", "", key="met_ht")
        if st.button("Ajouter ce metier", type="primary", key="met_go",
                     use_container_width=True):
            if not met.strip():
                st.warning("Indique l intitule du metier.", icon="⚠️")
            else:
                _res_enrichir(led.ajouter_metier(met, secteur, famille,
                                                 men, mes, mpt, mht, mots))
        st.caption(f"Le referentiel compte actuellement "
                   f"{len(lexicons.metiers())} metiers.")

    # ---------------- import CSV ------------------------------------
    with c:
        st.caption("Le fichier importe doit partager au moins une colonne avec "
                   "le fichier cible. Les colonnes inconnues sont ignorees, les "
                   "doublons aussi.")
        cible = st.selectbox("Fichier cible", led.fichiers(), key="imp_c")
        st.caption("colonnes attendues : " + ", ".join(led.colonnes(cible)))
        remplacer = st.toggle("Mettre a jour les lignes deja presentes", False,
                              key="imp_r")
        up = st.file_uploader("Fichier CSV", type=["csv"], key="imp_f")
        if up and st.button("Fusionner dans la base", type="primary", key="imp_go",
                            use_container_width=True):
            res = led.importer(cible, up.getvalue(), remplacer)
            _res_enrichir(res)
            if res.get("colonnes_ignorees"):
                st.caption("colonnes ignorees : " + ", ".join(res["colonnes_ignorees"]))

    # ---------------- nouveau lexique -------------------------------
    with d_:
        st.caption("Cree un lexique sectoriel vide, pret a recevoir tes termes. "
                   "Il sera pris en compte par la detection de secteurs et par "
                   "le glossaire multilingue.")
        nom = st.text_input("Nom du secteur", "", key="new_s",
                            placeholder="ex. assurance maritime")
        if st.button("Creer le lexique", type="primary", key="new_go",
                     use_container_width=True):
            _res_enrichir(led.creer_lexique(nom))

        st.divider()
        st.markdown("##### Regenerer toute la base")
        st.caption("Relance les scripts livres avec la plateforme. Utile apres "
                   "avoir modifie les fichiers build_0*.py. Attention : les "
                   "ajouts faits ici dans les fichiers de reference seront "
                   "remplaces — une archive complete est conservee avant.")
        if st.button("Regenerer les 57 fichiers", key="reg_go",
                     use_container_width=True):
            with st.spinner("regeneration en cours…"):
                _res_enrichir(led.regenerer())

    # ---------------- sauvegardes -----------------------------------
    with e:
        st.download_button("⬇ Telecharger toute la base (ZIP)",
                           led.archiver(),
                           f"synthea-lexiques-{utils.stamp()}.zip",
                           "application/zip", use_container_width=True)
        st.markdown("##### Copies de securite")
        sv = led.sauvegardes()
        df(sv)
        if sv:
            choix = st.selectbox("Restaurer une version",
                                 [s["fichier"] for s in sv], key="res_c")
            if st.button("Restaurer", key="res_go"):
                _res_enrichir(led.restaurer(choix))


# =====================================================================
# Onglet 8 - Studio visuel
# =====================================================================
def tab_studio() -> None:
    hero("Agent ATELIER", "Studio visuel",
         "Couvertures, schemas de themes, nuages de mots, graphiques, "
         "infographies et cartons de citation generes a partir du document. "
         "Les images importees peuvent etre retouchees et legendees.")
    if need_doc():
        return
    s = SS["state"]
    t, d = s["tree"], s["doc"]
    images = dict(s.get("images") or {})
    images.update(SS["custom_images"])

    c1, c2 = st.columns([1, 3])
    with c1:
        pal = st.selectbox("Palette", list(imaging.PALETTES.keys()),
                           index=list(imaging.PALETTES.keys()).index(
                               s["options"]["palette"]))
        if st.button("Regenerer le jeu de visuels", use_container_width=True):
            with st.spinner("ATELIER travaille…"):
                s["images"] = imaging.illustration_pack(d.title, t, d, pal)
                s["options"]["palette"] = pal
            st.rerun()
        st.caption("Palette appliquee aux visuels et aux exports PowerPoint.")
    with c2:
        if images:
            st.download_button("Telecharger tous les visuels (ZIP)",
                               exporters.export_images_zip(images),
                               f"visuels-{utils.slugify(d.title)}.zip", "application/zip",
                               type="primary")

    cols = st.columns(2, gap="large")
    for i, (name, data) in enumerate(sorted(images.items())):
        with cols[i % 2]:
            st.image(data, caption=name, use_container_width=True)
            st.download_button(f"PNG — {name}", data, name, "image/png",
                               key=f"dl_{name}")

    st.divider()
    st.markdown("#### Carton de citation")
    claims = t.all_claims
    if claims:
        opts = {f"{utils.truncate(c.text, 90)} ({c.ref})": c for c in claims[:60]}
        pick = st.selectbox("Constat a mettre en image", list(opts.keys()))
        if st.button("Generer le carton"):
            c = opts[pick]
            img = imaging.quote_card(utils.truncate(c.text, 300), c.ref,
                                     s["options"]["palette"])
            SS["custom_images"]["90-citation-personnalisee.png"] = imaging.to_png(img)
            st.rerun()

    st.divider()
    st.markdown("#### Retouche d une image importee")
    up = st.file_uploader("Image JPEG ou PNG", type=["jpg", "jpeg", "png", "webp", "tif"],
                          key="retouche")
    if up:
        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            filt = st.selectbox("Traitement", imaging.FILTERS)
        with c2:
            inten = st.slider("Intensite", 0.0, 1.0, 0.6, 0.1)
        with c3:
            legende = st.text_input("Legende", "", placeholder="legende de la figure")
        out = imaging.apply_filter(up.getvalue(), filt, s["options"]["palette"], inten)
        if legende:
            out = imaging.caption_image(out, legende, s["options"]["palette"],
                                        f"source : {up.name}")
        st.image(out, use_container_width=True)
        png = imaging.to_png(out)
        cA, cB = st.columns(2)
        with cA:
            st.download_button("Telecharger en PNG", png,
                               f"retouche-{utils.slugify(up.name)}.png", "image/png")
        with cB:
            if st.button("Ajouter au jeu de visuels"):
                SS["custom_images"][f"91-{utils.slugify(up.name)}.png"] = png
                st.rerun()


# =====================================================================
# Onglet 9 - Verification ARGUS
# =====================================================================
def tab_argus() -> None:
    hero("Agent ARGUS", "Autoverification",
         "Neuf controles independants repondent a une seule question : tout le "
         "document a-t-il ete extrait, segmente, analyse et resume, sans qu aucun "
         "chiffre ni aucune phrase n ait ete invente ?")
    if need_doc():
        return
    s = SS["state"]
    a = s.get("audit")
    if not a:
        st.error("Audit indisponible.")
        return

    cls = "ok" if a["score"] >= 97 else ("warn" if a["score"] >= 90 else "bad")
    kpis([
        ("Score global", f"{a['score']:.1f}/100", a["verdict"], cls),
        ("Couverture de synthese", f"{a['controles']['C3']['taux']:.1f} %",
         f"{a['controles']['C3']['pages_couvertes']} pages couvertes",
         "ok" if a["controles"]["C3"]["statut"] == "ok" else "warn"),
        ("Fidelite numerique", f"{a['controles']['C5']['taux']:.1f} %",
         f"{a['controles']['C5']['valeurs_verifiees']} valeurs verifiees",
         "ok" if a["controles"]["C5"]["statut"] == "ok" else "bad"),
        ("Pages non resumees", str(a["controles"]["C4"]["n"]),
         "detail ci-dessous" if a["controles"]["C4"]["n"] else "aucune",
         "ok" if not a["controles"]["C4"]["n"] else "warn"),
    ])
    st.markdown(gauge(a["score"]), unsafe_allow_html=True)
    st.image(imaging.chart_coverage(a, s["options"]["palette"]), width=620)

    ctrl = s.get("controle_budget") or {}
    if ctrl:
        st.markdown("#### C10 — Respect du format cible")
        icone = "✔" if ctrl["statut"] == "conforme" else "▲"
        st.markdown(f"{icone} **{ctrl['message']}**")
        df([{"element": k, "valeur": str(v)} for k, v in ctrl.items()
            if k not in ("libelle", "message")])

    st.markdown("#### Recommandations")
    for r in a["recommandations"]:
        st.markdown(f"- {r}")
    if ctrl and ctrl["statut"] != "conforme":
        st.markdown(f"- Dimensionnement {ctrl['statut']} : ajuste le curseur "
                    f"« Longueur de la synthese » ou change d objectif dans le "
                    f"panneau de gauche.")

    st.divider()
    st.markdown("#### Les neuf controles")
    for code, c in a["controles"].items():
        icon = {"ok": "✔", "attention": "▲", "alerte": "✖"}[c["statut"]]
        with st.expander(f"{icon}  {code} — {c['libelle']}  "
                         f"({c['statut']})"):
            rows = []
            for k, v in c.items():
                if k in ("libelle", "statut"):
                    continue
                if isinstance(v, list):
                    if v and isinstance(v[0], dict):
                        st.markdown(f"**{k}**")
                        df(v[:120], height=220)
                        continue
                    v = ", ".join(map(str, v[:60])) + ("…" if len(v) > 60 else "")
                rows.append({"element": k, "valeur": str(v)})
            df(rows)

    st.divider()
    st.markdown("#### Controle page par page")
    rows = s.get("page_rows") or []
    c1, c2 = st.columns([1, 3])
    with c1:
        filt = st.radio("Filtrer", ["toutes", "non resumees", "vides", "OCR",
                                    "avec avertissement"])
    sel = rows
    if filt == "non resumees":
        sel = [r for r in rows if r["resumee"] == "NON"]
    elif filt == "vides":
        sel = [r for r in rows if r["resumee"] == "vide"]
    elif filt == "OCR":
        sel = [r for r in rows if r["ocr"]]
    elif filt == "avec avertissement":
        sel = [r for r in rows if r["avertissement"]]
    with c2:
        st.caption(f"{len(sel)} ligne(s) sur {len(rows)}")
    df(sel, height=430)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.download_button("controle-pages.csv",
                           pd.DataFrame(rows).to_csv(index=False).encode("utf-8"),
                           "controle-pages.csv", "text/csv")
    with c2:
        import json
        st.download_button("rapport-argus.json",
                           json.dumps(a, ensure_ascii=False, indent=2).encode("utf-8"),
                           "rapport-argus.json", "application/json")
    with c3:
        st.caption(f"empreinte corpus : {a['empreinte']['sha1_corpus']}  \n"
                   f"empreinte synthese : {a['empreinte']['sha1_synthese']}")


# =====================================================================
# Onglet 10 - Dialogue
# =====================================================================
def tab_dialogue() -> None:
    hero("Agent ECHO", "Dialogue avec le document",
         "Recherche hybride BM25 et TF-IDF sur les blocs, puis selection des "
         "phrases qui repondent. Chaque reponse cite ses pages et ne sort jamais "
         "du document charge.")
    if need_doc():
        return
    s = SS["state"]
    retr, t, d = s.get("retriever"), s["tree"], s["doc"]
    if retr is None:
        st.error("Index de dialogue indisponible.")
        return

    sug = qa.suggest_questions(t)
    st.markdown("##### Suggestions")
    cols = st.columns(3)
    for i, q in enumerate(sug[:6]):
        with cols[i % 3]:
            if st.button(utils.truncate(q, 54), key=f"sug{i}",
                         use_container_width=True):
                SS["pending_q"] = q

    for m in SS["chat"]:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
            if m.get("extraits"):
                with st.expander(f"Extraits sources — {m.get('refs','')}"):
                    df(m["extraits"])

    question = st.chat_input("Pose ta question sur le document…")
    if SS.get("pending_q"):
        question = SS.pop("pending_q")

    if question:
        SS["chat"].append({"role": "user", "content": question})
        with st.spinner("ECHO cherche dans le document…"):
            ans = qa.ask(question, d, retr, t, lang=s["options"]["langue"],
                         use_llm=s["options"].get("use_llm", False))
        SS["chat"].append({
            "role": "assistant",
            "content": f"{ans['reponse']}\n\n*{ans['moteur']} · "
                       f"{ans['refs'] or 'sans reference'}*",
            "extraits": ans["extraits"], "refs": ans["refs"],
        })
        st.rerun()

    if SS["chat"]:
        md = "\n\n".join(f"**{m['role']}** : {m['content']}" for m in SS["chat"])
        st.download_button("Exporter la conversation", md.encode("utf-8"),
                           "dialogue-synthea.md", "text/markdown")


# =====================================================================
# Onglet 11 - Veille ciblee
# =====================================================================
def tab_veille() -> None:
    net = websearch.status()
    hero("Agent VIGIE", "Recherche ciblee",
         "La base locale de 57 CSV est interrogee en premier. Si le reseau est "
         "disponible, la recherche web est restreinte aux domaines officiels "
         "listes dans le referentiel des sources.")

    kpis([
        ("Mode", net["mode"], "reseau detecte automatiquement",
         "ok" if net["reseau"] else "warn"),
        ("Sources de reference", str(net["sources_locales"]),
         "institutions et bases officielles", "brand"),
        ("Termes locaux", utils.human_int(net["termes_locaux"]),
         "interrogeables hors ligne", "brand"),
        ("Pays references", str(net["pays_references"]),
         "corridors et institutions", "brand"),
    ])

    kws = []
    if SS["state"]:
        kws = [k for k, _ in SS["state"]["tree"].keywords[:5]]
    c1, c2, c3 = st.columns([3, 2, 1])
    with c1:
        q = st.text_input("Recherche", " ".join(kws),
                          placeholder="mots-cles ou question")
    with c2:
        them = st.text_input("Thematique", SS["state"]["options"]["veille_thematique"]
                             if SS["state"] else "",
                             placeholder="ex. sanctions, fiscalite, agriculture")
    with c3:
        officiel = st.toggle("Sources officielles", value=True)

    if st.button("Lancer la recherche", type="primary"):
        with st.spinner("VIGIE interroge la base locale puis le web…"):
            SS["veille_manuelle"] = websearch.targeted_search(
                q.split(), them, official_only=officiel)

    res = SS.get("veille_manuelle") or (SS["state"] or {}).get("veille")
    if res:
        st.caption(f"requete : `{res['requete']}` · mode : {res['mode']}")
        a, b = st.tabs(["Base locale (hors ligne)", "Resultats web"])
        with a:
            loc = res["local"]
            st.markdown("##### Termes du referentiel")
            df([{"terme": r["terme_fr"], "definition": r["definition_fr"],
                 "secteur": r["secteur"], "en": r["en"], "ht": r["ht"]}
                for r in loc["termes"]], height=240)
            st.markdown("##### Metiers concernes")
            df([{"metier": m["metier_fr"], "secteur": m["secteur"]}
                for m in loc["metiers"]])
            st.markdown("##### Sources recommandees")
            df(loc["sources_recommandees"])
        with b:
            web = res["web"]
            if web["statut"] != "ok":
                st.warning(f"{web['statut']} — {web.get('note','')}. "
                           f"La base locale ci-contre reste exploitable.")
            for r in web["resultats"]:
                st.markdown(f"**[{r['titre']}]({r['url']})**  \n"
                            f"<span class='sx-badge b-grey'>{r['domaine']}</span> "
                            f"{r['extrait']}", unsafe_allow_html=True)
            if web["resultats"]:
                st.caption("domaines cibles : " + ", ".join(res["sites_cibles"][:8]))
                url = st.selectbox("Archiver une page pour consultation hors ligne",
                                   [r["url"] for r in web["resultats"]])
                if st.button("Recuperer et archiver"):
                    page = websearch.fetch_page(url)
                    if page["statut"] == "ok":
                        p = websearch.add_to_corpus(url, page["texte"])
                        st.success(f"{page['mots']} mots archives dans {p}")
                    else:
                        st.error(f"echec : {page['statut']}")

    st.divider()
    st.markdown("#### Referentiel des sources de veille")
    df(lexicons.sources_veille(), height=320)
    st.markdown("#### Pays, institutions et corridors")
    df(lexicons.pays(), height=320)


# =====================================================================
# Onglet 12 - Exports
# =====================================================================
def tab_exports() -> None:
    hero("Livrables", "Exports",
         "PowerPoint, Word, PDF, Excel, HTML autonome, Markdown et archive "
         "complete. Les exports reprennent la restitution selectionnee dans "
         "l onglet Syntheses, les visuels et le rapport de verification.")
    if need_doc():
        return
    s = SS["state"]
    t, d = s["tree"], s["doc"]
    a = s.get("audit")
    rend = SS.get("rendition") or list(s["renditions"].values())[0]
    images = dict(s.get("images") or {})
    images.update(SS["custom_images"])

    c1, c2, c3 = st.columns(3)
    with c1:
        inc_img = st.toggle("Inclure les visuels", value=True)
    with c2:
        inc_audit = st.toggle("Inclure le rapport ARGUS", value=True)
    with c3:
        st.caption(f"restitution : **{rend.context_label}** · "
                   f"langue : {lexicons.LANG_LABELS.get(rend.language, rend.language)}")

    imgs = images if inc_img else {}
    aud = a if inc_audit else None
    base = utils.slugify(d.title)
    bud = s.get("budget")
    n_diapos = bud.diapositives if bud is not None else 45
    if bud is not None:
        st.caption(f"Le deck est plafonne a **{n_diapos} diapositives** et la "
                   f"synthese visee a **{bud.pages_cible:.0f} pages** "
                   f"({bud.objectif_libelle.lower()}).")

    st.markdown("#### Telechargements")
    g1, g2, g3, g4 = st.columns(4)
    with g1:
        if st.button("Preparer le PowerPoint", use_container_width=True):
            SS["x_pptx"] = exporters.export_pptx(rend, t, d, imgs,
                                                 s["options"]["palette"],
                                                 max_slides=n_diapos)
        if SS.get("x_pptx"):
            st.download_button("⬇ .pptx", SS["x_pptx"], f"{base}-synthese.pptx",
                               "application/vnd.openxmlformats-officedocument."
                               "presentationml.presentation", use_container_width=True)
    with g2:
        if st.button("Preparer le Word", use_container_width=True):
            SS["x_docx"] = exporters.export_docx(rend, t, d, aud, imgs)
        if SS.get("x_docx"):
            st.download_button("⬇ .docx", SS["x_docx"], f"{base}-synthese.docx",
                               "application/vnd.openxmlformats-officedocument."
                               "wordprocessingml.document", use_container_width=True)
    with g3:
        if st.button("Preparer le PDF", use_container_width=True):
            SS["x_pdf"] = exporters.export_pdf(rend, t, d, aud, imgs)
        if SS.get("x_pdf"):
            st.download_button("⬇ .pdf", SS["x_pdf"], f"{base}-synthese.pdf",
                               "application/pdf", use_container_width=True)
    with g4:
        if st.button("Preparer l Excel", use_container_width=True):
            SS["x_xlsx"] = exporters.export_xlsx(
                d, s["chunks"], t, aud, s.get("page_rows"),
                translation.document_glossary(d.full_text()[:200000], "en", 120))
        if SS.get("x_xlsx"):
            st.download_button("⬇ .xlsx", SS["x_xlsx"], f"{base}-analyse.xlsx",
                               "application/vnd.openxmlformats-officedocument."
                               "spreadsheetml.sheet", use_container_width=True)

    h1, h2, h3 = st.columns(3)
    with h1:
        html_bytes = exporters.export_html(rend, t, d, aud, imgs)
        st.download_button("⬇ rapport HTML autonome", html_bytes,
                           f"{base}-rapport.html", "text/html",
                           use_container_width=True)
    with h2:
        st.download_button("⬇ synthese Markdown", exporters.export_markdown(rend),
                           f"{base}-synthese.md", "text/markdown",
                           use_container_width=True)
    with h3:
        if st.button("Preparer l archive complete", type="primary",
                     use_container_width=True):
            bundle = {
                f"{base}-synthese.pptx": exporters.export_pptx(
                    rend, t, d, imgs, s["options"]["palette"],
                    max_slides=n_diapos),
                f"{base}-synthese.docx": exporters.export_docx(rend, t, d, aud, imgs),
                f"{base}-synthese.pdf": exporters.export_pdf(rend, t, d, aud, imgs),
                f"{base}-analyse.xlsx": exporters.export_xlsx(
                    d, s["chunks"], t, aud, s.get("page_rows")),
                f"{base}-rapport.html": html_bytes,
                f"{base}-synthese.md": exporters.export_markdown(rend),
            }
            for n, data in imgs.items():
                bundle[f"visuels/{n}"] = data
            for ckey, per_lang in (s.get("traductions") or {}).items():
                for lg, r in per_lang.items():
                    bundle[f"traductions/{ckey}-{lg}.md"] = r.to_markdown().encode("utf-8")
            SS["x_zip"] = exporters.export_bundle(bundle)
        if SS.get("x_zip"):
            st.download_button("⬇ archive ZIP", SS["x_zip"], f"{base}-synthea.zip",
                               "application/zip", use_container_width=True)

    st.divider()
    st.markdown("#### Apercu du rapport HTML")
    components.html(html_bytes.decode("utf-8"), height=760, scrolling=True)


# =====================================================================
# Assemblage
# =====================================================================
def main() -> None:
    sidebar()
    tabs = st.tabs([
        "\U0001F3E0 Accueil", "\U0001F4E5 Import", "\U0001F916 Agents",
        "\U0001F9E0 Analyse", "\U0001F4DD Syntheses", "\U0001F30D Traductions",
        "\U0001F4DA Lexiques", "\U0001F3A8 Studio", "✅ ARGUS",
        "\U0001F4AC Dialogue", "\U0001F50E Veille", "\U0001F4E4 Exports",
        "\U0001F9F0 Transforme docs",
    ])
    renderers = [tab_accueil, tab_import, tab_agents, tab_analyse, tab_syntheses,
                 tab_traductions, tab_lexiques, tab_studio, tab_argus,
                 tab_dialogue, tab_veille, tab_exports, tab_transform.render]
    for tab, fn in zip(tabs, renderers):
        with tab:
            fn()

    st.markdown(
        "<div class='sx-foot'>SYNTHEA — Document Intelligence Suite · "
        "synthese extractive tracable a la page · "
        "fonctionne sans internet grace a 57 referentiels CSV</div>",
        unsafe_allow_html=True)


main()
