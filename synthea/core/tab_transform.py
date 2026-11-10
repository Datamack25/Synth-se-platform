"""SYNTHEA - onglet « Transforme docs ».

Interface des 36 outils documentaires portes par les cinq agents FORGE,
MOSAIQUE, ATOME, SCEAU et COLLATEUR, plus les enchainements (workflows) et le
traitement par lot.
"""
from __future__ import annotations

import streamlit as st

from . import convert, doctools as dt, pdfintel, pdfops, ui, utils, workflows
from . import budget as bud_mod
from . import lexicons

FAMILLES = ["Organiser", "Optimiser", "Convertir", "Securiser", "Intelligence"]
ICONES = {"Organiser": "\U0001F9F1", "Optimiser": "⚙️",
          "Convertir": "\U0001F504", "Securiser": "\U0001F512",
          "Intelligence": "\U0001F9E0"}

SS = st.session_state


# ---------------------------------------------------------------- helpers
def _up(label: str, types: list[str], key: str, multi: bool = False):
    return st.file_uploader(label, type=types, key=key,
                            accept_multiple_files=multi)


def _one(outil, key: str):
    """Uploader adapte au type d entree de l outil. Retourne (nom, data) ou None."""
    e = outil.entree
    if e == "pdf":
        f = _up("Document PDF", ["pdf"], f"u_{key}")
        return (f.name, f.getvalue()) if f else None
    if e == "docx":
        f = _up("Document Word (.docx)", ["docx", "doc"], f"u_{key}")
        return (f.name, f.getvalue()) if f else None
    if e == "pptx":
        f = _up("Presentation PowerPoint (.pptx)", ["pptx", "ppt"], f"u_{key}")
        return (f.name, f.getvalue()) if f else None
    if e == "xlsx":
        f = _up("Classeur Excel (.xlsx)", ["xlsx", "xlsm", "csv"], f"u_{key}")
        return (f.name, f.getvalue()) if f else None
    return None


def _plages(key: str, aide: str = "vide = tout le document") -> str:
    return st.text_input("Pages", "", key=f"pg_{key}",
                         placeholder="ex. 1-5, 8, 12-fin", help=aide)


def _run(label: str, key: str, fn, *a, **k) -> None:
    if st.button(label, type="primary", key=f"go_{key}", use_container_width=True):
        with st.spinner("traitement en cours…"):
            SS[f"res_{key}"] = fn(*a, **k)
    ui.resultat(SS.get(f"res_{key}"), key)


# ---------------------------------------------------------------- formulaires
def _form(outil, key: str) -> None:
    oid = outil.id
    st.caption(outil.description)

    # ---------------- entrees multiples ----------------
    if oid == "merge":
        ups = _up("Documents PDF a fusionner (l ordre d import fait foi)",
                  ["pdf"], f"u_{key}", multi=True)
        fichiers = ui.fichiers_streamlit(ups)
        if fichiers:
            ui.df([{"#": i + 1, "fichier": n, "pages": dt.page_count(d),
                    "Ko": round(len(d) / 1024)} for i, (n, d) in enumerate(fichiers)])
            ordre_txt = st.text_input("Ordre (optionnel)", "",
                                      placeholder="ex. 3,1,2", key=f"o_{key}")
            nom = st.text_input("Nom du fichier produit", "fusion.pdf", key=f"n_{key}")
            ordre = None
            if ordre_txt.strip():
                try:
                    ordre = [int(x) - 1 for x in ordre_txt.replace(";", ",").split(",")]
                except ValueError:
                    st.warning("Ordre illisible : les fichiers seront pris dans "
                               "l ordre d import.")
            _run("Fusionner", key, pdfops.merge_pdf, fichiers, ordre, nom)
        return

    if oid in ("jpg2pdf", "scan"):
        ups = _up("Images (JPEG, PNG, TIFF)", ["jpg", "jpeg", "png", "tif", "tiff", "webp"],
                  f"u_{key}", multi=True)
        fichiers = ui.fichiers_streamlit(ups)
        if fichiers:
            cols = st.columns(min(4, len(fichiers)))
            for c, (n, d) in zip(cols, fichiers[:4]):
                with c:
                    st.image(d, caption=utils.truncate(n, 22), use_container_width=True)
            if oid == "jpg2pdf":
                c1, c2, c3 = st.columns(3)
                with c1:
                    fmt = st.selectbox("Format de page", ["A4", "Letter", "auto"],
                                       key=f"f_{key}")
                with c2:
                    orient = st.selectbox("Orientation",
                                          ["auto", "portrait", "paysage"], key=f"or_{key}")
                with c3:
                    marge = st.slider("Marge (mm)", 0.0, 30.0, 8.0, key=f"m_{key}")
                _run("Convertir en PDF", key, convert.jpg_to_pdf, fichiers, fmt,
                     orient, marge)
            else:
                c1, c2, c3 = st.columns(3)
                with c1:
                    amel = st.toggle("Ameliorer le contraste", True, key=f"a_{key}")
                with c2:
                    gris = st.toggle("Niveaux de gris", True, key=f"g_{key}")
                with c3:
                    redr = st.toggle("Redresser", True, key=f"r_{key}")
                _run("Assembler en PDF", key, pdfops.scan_to_pdf, fichiers,
                     amel, gris, redr)
        return

    if oid == "compare":
        c1, c2 = st.columns(2)
        with c1:
            fa = _up("Version A", ["pdf"], f"ua_{key}")
        with c2:
            fb = _up("Version B", ["pdf"], f"ub_{key}")
        gran = st.radio("Granularite", ["phrase", "ligne", "mot"],
                        horizontal=True, key=f"gr_{key}")
        if fa and fb:
            _run("Comparer", key, pdfintel.compare_pdf, fa.name, fa.getvalue(),
                 fb.name, fb.getvalue(), gran)
            res = SS.get(f"res_{key}")
            if res is not None and res.ok:
                html = next((d for n, d in res.fichiers if n.endswith(".html")), None)
                if html:
                    with st.expander("Rapport de comparaison", expanded=True):
                        st.components.v1.html(html.decode("utf-8"), height=620,
                                              scrolling=True)
        return

    if oid == "html2pdf":
        mode = st.radio("Source", ["Adresse web", "Fichier HTML"],
                        horizontal=True, key=f"md_{key}")
        titre = st.text_input("Titre du document", "", key=f"t_{key}")
        if mode == "Adresse web":
            url = st.text_input("Adresse", "", placeholder="https://…",
                                key=f"url_{key}")
            if url.strip():
                _run("Convertir en PDF", key, convert.html_to_pdf, url.strip(),
                     "page.html", None, titre)
        else:
            f = _up("Fichier HTML", ["html", "htm"], f"u_{key}")
            if f:
                _run("Convertir en PDF", key, convert.html_to_pdf, "", f.name,
                     f.getvalue(), titre)
        return

    # ---------------- entree unique ----------------
    src = _one(outil, key)
    if not src:
        st.info("Importe un fichier pour activer l outil.")
        return
    nom, data = src

    if outil.entree == "pdf":
        try:
            n_pages = dt.page_count(data)
            chiffre = f"{n_pages} page(s)"
        except Exception:
            n_pages, chiffre = 0, "document illisible"
        st.caption(f"{nom} — {chiffre}, {len(data) / 1024:.0f} Ko"
                   + (" — protege par mot de passe" if dt.is_encrypted(data) else ""))
    else:
        n_pages = 0
        st.caption(f"{nom} — {len(data) / 1024:.0f} Ko")

    # ---- Organiser -------------------------------------------------
    if oid == "split":
        mode = st.radio("Mode", ["plages", "toutes_les", "une_par_page"],
                        horizontal=True, key=f"md_{key}",
                        format_func=lambda m: {"plages": "Par plages",
                                               "toutes_les": "Toutes les N pages",
                                               "une_par_page": "Une page par fichier"}[m])
        plages = toutes = ""
        if mode == "plages":
            plages = st.text_input("Plages (une par fichier produit)", "1-5, 6-10",
                                   key=f"pl_{key}")
        elif mode == "toutes_les":
            toutes = st.number_input("Nombre de pages par fichier", 1, 500, 10,
                                     key=f"tl_{key}")
        _run("Diviser", key, pdfops.split_pdf, nom, data, mode, plages,
             int(toutes or 1))

    elif oid == "extract":
        plages = st.text_input("Pages a traiter", "1-3", key=f"pl_{key}")
        inv = st.toggle("Inverser : supprimer ces pages au lieu de les garder",
                        False, key=f"i_{key}")
        _run("Appliquer", key, pdfops.extract_pages, nom, data, plages, inv)

    elif oid == "organize":
        c1, c2 = st.columns(2)
        with c1:
            ordre = st.text_input("Nouvel ordre", "",
                                  placeholder="ex. 3,1,2,4-10", key=f"o_{key}")
        with c2:
            supp = st.text_input("Pages a supprimer", "",
                                 placeholder="ex. 2, 7-9", key=f"s_{key}")
        if n_pages:
            with st.expander("Apercu des pages"):
                rendus = dt.render_pages(data, list(range(1, min(n_pages, 8) + 1)), dpi=60)
                cols = st.columns(min(len(rendus), 4) or 1)
                for i, (no, img) in enumerate(rendus):
                    with cols[i % len(cols)]:
                        st.image(img, caption=f"p. {no}", use_container_width=True)
        _run("Reorganiser", key, pdfops.organize_pdf, nom, data, ordre, supp)

    elif oid == "rotate":
        c1, c2 = st.columns(2)
        with c1:
            angle = st.select_slider("Angle", [90, 180, 270], 90, key=f"a_{key}")
        with c2:
            plages = _plages(key)
        _run("Pivoter", key, pdfops.rotate_pdf, nom, data, int(angle), plages)

    elif oid == "crop":
        st.caption("Rognage en pourcentage de la page.")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            haut = st.slider("Haut", 0.0, 45.0, 0.0, key=f"h_{key}")
        with c2:
            bas = st.slider("Bas", 0.0, 45.0, 0.0, key=f"b_{key}")
        with c3:
            gau = st.slider("Gauche", 0.0, 45.0, 0.0, key=f"g_{key}")
        with c4:
            dro = st.slider("Droite", 0.0, 45.0, 0.0, key=f"d_{key}")
        plages = _plages(key)
        _run("Recadrer", key, pdfops.crop_pdf, nom, data, haut, bas, gau, dro, plages)

    elif oid == "numbers":
        c1, c2, c3 = st.columns(3)
        with c1:
            pos = st.selectbox("Position",
                               ["bas-centre", "bas-droite", "bas-gauche",
                                "haut-centre", "haut-droite", "haut-gauche"],
                               key=f"p_{key}")
        with c2:
            depart = st.number_input("Premier numero", 1, 9999, 1, key=f"d_{key}")
        with c3:
            taille = st.slider("Taille", 7, 24, 10, key=f"t_{key}")
        fmt = st.text_input("Format", "{n}", key=f"f_{key}",
                            help="{n} = numero, {total} = nombre de pages")
        plages = _plages(key)
        _run("Numeroter", key, pdfops.page_numbers, nom, data, pos, int(depart),
             fmt, int(taille), plages)

    # ---- Optimiser -------------------------------------------------
    elif oid == "compress":
        niveau = st.radio("Niveau", ["leger", "recommande", "fort"],
                          index=1, horizontal=True, key=f"n_{key}")
        with st.expander("Reglages avances"):
            dpi = st.slider("Resolution des images (ppp)", 72, 300, 110, key=f"dpi_{key}")
            qual = st.slider("Qualite JPEG", 30, 95, 68, key=f"q_{key}")
        _run("Compresser", key, pdfops.compress_pdf, nom, data, niveau, dpi, qual)

    elif oid == "repair":
        _run("Reparer", key, pdfops.repair_pdf, nom, data)

    elif oid == "ocr":
        caps = dt.capabilities()
        if not caps.get("tesseract"):
            st.warning("Tesseract n est pas installe : l OCR est indisponible. "
                       "Ajoute `tesseract-ocr` a packages.txt (deja prevu) ou "
                       "installe-le en local.", icon="⚠️")
        c1, c2 = st.columns(2)
        with c1:
            langues = st.text_input("Langues", "fra+eng", key=f"l_{key}",
                                    help="codes tesseract, ex. fra+eng+spa")
        with c2:
            dpi = st.slider("Resolution (ppp)", 120, 400, 220, key=f"dpi_{key}")
        plages = _plages(key)
        _run("Lancer l OCR", key, pdfops.ocr_pdf, nom, data, langues, dpi, plages)

    # ---- Convertir -------------------------------------------------
    elif oid == "pdf2word":
        mode = st.radio("Mode", ["fidelite", "texte"], horizontal=True, key=f"m_{key}",
                        format_func=lambda m: {"fidelite": "Fidelite de mise en page",
                                               "texte": "Texte et tableaux"}[m])
        plages = _plages(key)
        _run("Convertir en Word", key, convert.pdf_to_word, nom, data, plages, mode)

    elif oid == "pdf2ppt":
        c1, c2 = st.columns(2)
        with c1:
            mode = st.radio("Mode", ["image", "texte"], horizontal=True, key=f"m_{key}",
                            format_func=lambda m: {"image": "Page en image",
                                                   "texte": "Texte editable"}[m])
        with c2:
            dpi = st.slider("Resolution (ppp)", 90, 220, 130, key=f"dpi_{key}")
        plages = _plages(key)
        _run("Convertir en PowerPoint", key, convert.pdf_to_powerpoint, nom, data,
             plages, mode, dpi)

    elif oid == "pdf2excel":
        fus = st.toggle("Fusionner tous les tableaux dans une seule feuille",
                        False, key=f"f_{key}")
        plages = _plages(key)
        _run("Convertir en Excel", key, convert.pdf_to_excel, nom, data, plages, fus)

    elif oid == "pdf2jpg":
        c1, c2, c3 = st.columns(3)
        with c1:
            mode = st.radio("Mode", ["pages", "images"], horizontal=True, key=f"m_{key}",
                            format_func=lambda m: {"pages": "Une image par page",
                                                   "images": "Extraire les images"}[m])
        with c2:
            dpi = st.slider("Resolution (ppp)", 72, 300, 150, key=f"dpi_{key}")
        with c3:
            fmt = st.selectbox("Format", ["JPEG", "PNG"], key=f"f_{key}")
        plages = _plages(key)
        _run("Convertir", key, convert.pdf_to_jpg, nom, data, plages, dpi, fmt, 90, mode)

    elif oid == "pdf2md":
        titres = st.toggle("Detecter les titres", True, key=f"t_{key}")
        plages = _plages(key)
        _run("Convertir en Markdown", key, convert.pdf_to_markdown, nom, data,
             plages, titres)

    elif oid == "pdf2txt":
        plages = _plages(key)
        _run("Extraire le texte", key, convert.pdf_to_text, nom, data, plages)

    elif oid == "pdf2pdfa":
        if not dt.capabilities().get("ghostscript"):
            st.info("Ghostscript absent : SYNTHEA produira un PDF enrichi des "
                    "metadonnees d archivage, sans certification PDF/A stricte. "
                    "Ajoute `ghostscript` a packages.txt pour la conversion complete.")
        _run("Convertir en PDF/A", key, convert.pdf_to_pdfa, nom, data)

    elif oid in ("word2pdf", "ppt2pdf", "excel2pdf"):
        caps = dt.capabilities()
        if not caps.get("libreoffice"):
            st.info("LibreOffice absent : la conversion se fera en mode « texte » "
                    "(contenu et structure preserves, mise en page simplifiee). "
                    "Ajoute `libreoffice` a packages.txt pour la fidelite complete.")
        mode = st.radio("Mode", ["fidelite", "texte"], horizontal=True, key=f"m_{key}",
                        format_func=lambda m: {"fidelite": "Fidelite (LibreOffice)",
                                               "texte": "Texte (toujours disponible)"}[m])
        fn = {"word2pdf": convert.word_to_pdf, "ppt2pdf": convert.powerpoint_to_pdf,
              "excel2pdf": convert.excel_to_pdf}[oid]
        _run("Convertir en PDF", key, fn, nom, data, mode)

    # ---- Securiser -------------------------------------------------
    elif oid == "protect":
        c1, c2 = st.columns(2)
        with c1:
            mdp = st.text_input("Mot de passe (ouverture)", "", type="password",
                                key=f"p_{key}")
        with c2:
            mdp2 = st.text_input("Mot de passe proprietaire (optionnel)", "",
                                 type="password", key=f"p2_{key}")
        c1, c2 = st.columns(2)
        with c1:
            no_print = st.toggle("Interdire l impression", False, key=f"ni_{key}")
        with c2:
            no_copy = st.toggle("Interdire la copie de texte", True, key=f"nc_{key}")
        if mdp:
            _run("Proteger", key, pdfops.protect_pdf, nom, data, mdp, mdp2,
                 no_print, no_copy)
        else:
            st.info("Saisis un mot de passe.")

    elif oid == "unlock":
        mdp = st.text_input("Mot de passe actuel (si connu)", "", type="password",
                            key=f"p_{key}")
        st.caption("SYNTHEA ne casse pas de protection : le mot de passe doit etre "
                   "connu, ou le PDF seulement protege contre l edition.")
        _run("Deverrouiller", key, pdfops.unlock_pdf, nom, data, mdp)

    elif oid == "watermark":
        c1, c2 = st.columns([2, 1])
        with c1:
            texte = st.text_input("Texte", "CONFIDENTIEL", key=f"t_{key}")
        with c2:
            img = _up("ou image", ["png", "jpg", "jpeg"], f"im_{key}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            op = st.slider("Opacite", 0.05, 1.0, 0.18, key=f"o_{key}")
        with c2:
            taille = st.slider("Taille", 12, 120, 54, key=f"s_{key}")
        with c3:
            angle = st.slider("Angle", 0, 90, 45, key=f"a_{key}")
        with c4:
            couleur = st.color_picker("Couleur", "#A33A2E", key=f"c_{key}")
        c1, c2, c3 = st.columns(3)
        with c1:
            pos = st.selectbox("Position", ["centre", "mosaique", "bas-droite",
                                            "haut-gauche"], key=f"p_{key}")
        with c2:
            devant = st.toggle("Au-dessus du contenu", True, key=f"d_{key}")
        with c3:
            plages = _plages(key)
        _run("Appliquer le filigrane", key, pdfops.watermark_pdf, nom, data, texte,
             img.getvalue() if img else None, op, taille, angle, couleur, pos,
             plages, devant)

    elif oid == "redact":
        motifs = st.text_area("Termes a caviarder (un par ligne)", "",
                              key=f"m_{key}",
                              placeholder="nom du client\nIBAN\n06 12 34 56 78")
        c1, c2 = st.columns(2)
        with c1:
            casse = st.toggle("Respecter la casse", False, key=f"c_{key}")
        with c2:
            dpi = st.slider("Resolution de sortie (ppp)", 100, 300, 160, key=f"d_{key}")
        st.caption("Le caviardage aplatit les pages concernees en image : le texte "
                   "masque disparait reellement du fichier, il n est pas seulement "
                   "recouvert.")
        if motifs.strip():
            _run("Caviarder", key, pdfops.redact_pdf, nom, data, motifs, None,
                 dpi, casse)
        else:
            st.info("Indique au moins un terme.")

    elif oid == "sign":
        c1, c2 = st.columns(2)
        with c1:
            img = _up("Image de signature (PNG transparent conseille)",
                      ["png", "jpg", "jpeg"], f"im_{key}")
            texte = st.text_input("ou signature manuscrite (texte)", "", key=f"t_{key}")
        with c2:
            page = st.number_input("Page (0 = derniere)", 0, max(n_pages, 1), 0,
                                   key=f"p_{key}")
            mention = st.text_input("Mention", "", key=f"me_{key}",
                                    placeholder="Lu et approuve — Paris, le …")
        c1, c2, c3 = st.columns(3)
        with c1:
            x = st.slider("Position X (%)", 0.0, 95.0, 62.0, key=f"x_{key}")
        with c2:
            y = st.slider("Position Y (%)", 0.0, 95.0, 12.0, key=f"y_{key}")
        with c3:
            larg = st.slider("Largeur (%)", 8.0, 60.0, 28.0, key=f"w_{key}")
        st.caption("Signature **visuelle** : elle n a pas la valeur juridique d une "
                   "signature electronique qualifiee.")
        _run("Apposer la signature", key, pdfops.sign_pdf, nom, data,
             img.getvalue() if img else None, texte, int(page), x, y, larg, mention)

    elif oid == "annotate":
        st.caption("Ajoute du texte, un rectangle ou une image sur une page.")
        if "annots" not in SS:
            SS["annots"] = []
        c1, c2, c3 = st.columns(3)
        with c1:
            typ = st.selectbox("Element", ["texte", "rectangle", "image"], key=f"ty_{key}")
        with c2:
            page = st.number_input("Page", 1, max(n_pages, 1), 1, key=f"pa_{key}")
        with c3:
            couleur = st.color_picker("Couleur", "#17202A", key=f"co_{key}")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            x = st.slider("X (%)", 0.0, 98.0, 10.0, key=f"x_{key}")
        with c2:
            y = st.slider("Y (%)", 0.0, 98.0, 10.0, key=f"y_{key}")
        with c3:
            w = st.slider("Largeur (%)", 2.0, 90.0, 30.0, key=f"w_{key}")
        with c4:
            h = st.slider("Hauteur (%)", 2.0, 90.0, 8.0, key=f"h_{key}")
        contenu, img_bytes = "", None
        if typ == "texte":
            contenu = st.text_input("Texte", "", key=f"tx_{key}")
        elif typ == "image":
            im = _up("Image", ["png", "jpg", "jpeg"], f"im_{key}")
            img_bytes = im.getvalue() if im else None
        if st.button("Ajouter l element", key=f"add_{key}"):
            SS["annots"].append({"type": typ, "page": int(page), "x": x, "y": y,
                                 "largeur": w, "hauteur": h, "couleur": couleur,
                                 "texte": contenu, "image": img_bytes,
                                 "taille": 12})
        if SS["annots"]:
            ui.df([{k: (f"{len(v)} octets" if k == "image" and v else v)
                    for k, v in a.items() if k != "image" or v}
                   for a in SS["annots"]])
            if st.button("Vider la liste", key=f"clr_{key}"):
                SS["annots"] = []
                st.rerun()
            _run("Appliquer les elements", key, pdfops.annotate_pdf, nom, data,
                 SS["annots"])

    # ---- Intelligence ----------------------------------------------
    elif oid == "tables":
        c1, c2 = st.columns(2)
        with c1:
            fmt = st.selectbox("Format de sortie", ["xlsx", "csv"], key=f"f_{key}")
        with c2:
            plages = _plages(key)
        _run("Extraire les tableaux", key, pdfintel.extract_tables, nom, data,
             plages, fmt)

    elif oid == "forms":
        if st.button("Detecter les champs", key=f"det_{key}", use_container_width=True):
            SS[f"insp_{key}"] = pdfintel.inspect_forms(nom, data)
        insp = SS.get(f"insp_{key}")
        if insp is not None:
            ui.resultat(insp, f"i_{key}", apercu=False)
            champs = (insp.details or {}).get("champs", [])
            if champs:
                st.markdown("##### Remplir les champs")
                vals: dict[str, str] = {}
                cols = st.columns(2)
                for i, ch in enumerate(champs[:40]):
                    with cols[i % 2]:
                        vals[ch["nom"]] = st.text_input(
                            f"{ch['nom']} ({ch.get('type','texte')})", "",
                            key=f"fv_{key}_{i}")
                aplatir = st.toggle("Aplatir (champs non modifiables ensuite)",
                                    False, key=f"ap_{key}")
                _run("Remplir le formulaire", key, pdfintel.fill_forms, nom, data,
                     {k: v for k, v in vals.items() if v}, aplatir)

    elif oid == "inspect":
        _run("Inspecter", key, pdfintel.read_metadata, nom, data)

    elif oid == "metadata":
        c1, c2 = st.columns(2)
        with c1:
            titre = st.text_input("Titre", "", key=f"t_{key}")
            auteur = st.text_input("Auteur", "", key=f"a_{key}")
        with c2:
            sujet = st.text_input("Sujet", "", key=f"s_{key}")
            mots = st.text_input("Mots-cles", "", key=f"m_{key}")
        eff = st.toggle("Effacer toutes les metadonnees existantes", False,
                        key=f"e_{key}")
        _run("Ecrire les metadonnees", key, pdfintel.write_metadata, nom, data,
             titre, auteur, sujet, mots, eff)

    elif oid == "summarize":
        c1, c2, c3 = st.columns(3)
        with c1:
            obj = st.selectbox("Objectif", list(bud_mod.OBJECTIFS.keys()),
                               format_func=lambda k: bud_mod.OBJECTIFS[k]["libelle"],
                               key=f"ob_{key}")
        with c2:
            ctxs = {"": "(deduit de l objectif)", **lexicons.contextes_index()}
            ctx = st.selectbox("Contexte", list(ctxs.keys()),
                               format_func=lambda k: ("(deduit de l objectif)" if not k
                                                      else ctxs[k]["libelle"]),
                               key=f"cx_{key}")
        with c3:
            lg = st.selectbox("Langue", lexicons.LANGS,
                              format_func=lambda c: lexicons.LANG_LABELS[c],
                              key=f"lg_{key}")
        if n_pages:
            b = bud_mod.compute(n_pages, 0, obj)
            st.caption(b.resume_long())
        _run("Resumer avec la chaine SYNTHEA", key, pdfintel.summarize_pdf, nom,
             data, obj, ctx, lg)

    elif oid == "translate":
        from . import translation
        c1, c2, c3 = st.columns(3)
        with c1:
            srcl = st.selectbox("Langue source", lexicons.LANGS,
                                format_func=lambda c: lexicons.LANG_LABELS[c],
                                key=f"sl_{key}")
        with c2:
            cible = st.selectbox("Langue cible", [c for c in lexicons.LANGS],
                                 index=1,
                                 format_func=lambda c: lexicons.LANG_LABELS[c],
                                 key=f"cl_{key}")
        with c3:
            est = translation.engine_status()
            dispo = [k for k, v in est.items() if v["disponible"]]
            moteur = st.selectbox("Moteur", dispo,
                                  format_func=lambda k: translation.ENGINES[k],
                                  key=f"mo_{key}")
        _run("Traduire le document", key, pdfintel.translate_pdf, nom, data,
             cible, moteur, srcl)

    else:
        st.info("Outil non encore relie a l interface.")


# ---------------------------------------------------------------- workflows
def _workflows() -> None:
    st.markdown("#### Enchainements")
    st.caption("Applique plusieurs operations a la suite sur un meme document. "
               "Une etape dont un parametre obligatoire est vide est ignoree, "
               "sans faire echouer la chaine.")
    f = _up("Document PDF", ["pdf"], "u_wf")
    etapes_dispo = list(workflows.ETAPES.keys())
    choix = st.multiselect("Etapes, dans l ordre", etapes_dispo,
                           default=["unlock", "ocr", "compress"],
                           format_func=lambda k: workflows.ETAPES[k]["libelle"])
    params: dict[str, dict] = {}
    if choix:
        cols = st.columns(min(3, len(choix)))
        for i, c in enumerate(choix):
            with cols[i % len(cols)]:
                st.markdown(f"**{workflows.ETAPES[c]['libelle']}**")
                p: dict = {}
                if c == "protect":
                    p["mot_de_passe"] = st.text_input("Mot de passe", "",
                                                      type="password", key=f"wf_p_{c}")
                elif c == "redact":
                    p["motifs"] = st.text_area("Termes", "", key=f"wf_m_{c}")
                elif c == "watermark":
                    p["texte"] = st.text_input("Texte", "CONFIDENTIEL", key=f"wf_w_{c}")
                elif c == "extract":
                    p["plages"] = st.text_input("Pages", "1-5", key=f"wf_e_{c}")
                elif c == "rotate":
                    p["angle"] = st.select_slider("Angle", [90, 180, 270], 90,
                                                  key=f"wf_r_{c}")
                elif c == "compress":
                    p["niveau"] = st.selectbox("Niveau",
                                               ["leger", "recommande", "fort"],
                                               index=1, key=f"wf_c_{c}")
                elif c == "ocr":
                    p["langues"] = st.text_input("Langues", "fra+eng", key=f"wf_o_{c}")
                elif c == "unlock":
                    p["mot_de_passe"] = st.text_input("Mot de passe", "",
                                                      type="password", key=f"wf_u_{c}")
                else:
                    st.caption("aucun parametre")
                params[c] = p
    if f and choix:
        if st.button("Executer l enchainement", type="primary",
                     use_container_width=True, key="go_wf"):
            with st.spinner("enchainement en cours…"):
                SS["res_wf"] = workflows.run_workflow(
                    f.name, f.getvalue(), [(c, params.get(c, {})) for c in choix])
        res = SS.get("res_wf")
        ui.resultat(res, "wf")
        if res is not None and res.details.get("journal"):
            st.markdown("##### Journal de l enchainement")
            ui.df(res.details["journal"])


def _lot() -> None:
    st.markdown("#### Traitement par lot")
    st.caption("La meme suite d operations, appliquee a plusieurs documents. "
               "Le resultat est rendu sous forme d archive ZIP.")
    ups = _up("Documents PDF", ["pdf"], "u_lot", multi=True)
    fichiers = ui.fichiers_streamlit(ups)
    choix = st.multiselect("Etapes", list(workflows.ETAPES.keys()),
                           default=["compress"],
                           format_func=lambda k: workflows.ETAPES[k]["libelle"],
                           key="lot_etapes")
    params: dict[str, dict] = {}
    for c in choix:
        if c == "protect":
            params[c] = {"mot_de_passe": st.text_input("Mot de passe", "",
                                                       type="password", key="lot_p")}
        elif c == "redact":
            params[c] = {"motifs": st.text_area("Termes a caviarder", "", key="lot_m")}
        elif c == "watermark":
            params[c] = {"texte": st.text_input("Texte du filigrane", "CONFIDENTIEL",
                                                key="lot_w")}
        else:
            params[c] = {}
    if fichiers and choix:
        st.caption(f"{len(fichiers)} document(s), "
                   f"{sum(len(d) for _, d in fichiers) / 1024 / 1024:.1f} Mo")
        if st.button("Lancer le lot", type="primary", use_container_width=True,
                     key="go_lot"):
            with st.spinner(f"traitement de {len(fichiers)} documents…"):
                res, zipb = workflows.run_batch(
                    fichiers, [(c, params.get(c, {})) for c in choix])
                SS["res_lot"], SS["zip_lot"] = res, zipb
    if SS.get("res_lot"):
        ok = sum(1 for r in SS["res_lot"] if r.ok)
        st.success(f"{ok}/{len(SS['res_lot'])} document(s) traites.")
        ui.df([{"document": r.details.get("source", r.operation),
                "statut": "ok" if r.ok else "echec",
                "message": r.message, "duree_s": r.duree} for r in SS["res_lot"]])
        if SS.get("zip_lot"):
            st.download_button("⬇ Archive des resultats", SS["zip_lot"],
                               "synthea-lot.zip", "application/zip",
                               use_container_width=True)


# ---------------------------------------------------------------- rendu
def render() -> None:
    ui.hero("Agents FORGE · MOSAIQUE · ATOME · SCEAU · COLLATEUR",
            "Transforme docs",
            "Trente-six outils documentaires : fusionner, diviser, convertir, "
            "compresser, pivoter, recadrer, numeroter, proteger, deverrouiller, "
            "caviarder, signer, filigraner, OCR, comparer, extraire les tableaux, "
            "remplir les formulaires, resumer et traduire. Tout s execute "
            "localement, sans envoyer un seul fichier a un service tiers.")

    caps = dt.capability_rows()
    manquants = [c for c in caps if c.get("disponible") in ("non", False)]
    cols = st.columns(4)
    with cols[0]:
        st.metric("Outils", len(workflows.CATALOGUE))
    with cols[1]:
        st.metric("Agents", 5)
    with cols[2]:
        st.metric("Familles", len(FAMILLES))
    with cols[3]:
        st.metric("Briques optionnelles absentes", len(manquants))
    if manquants:
        with st.expander("Capacites du moteur"):
            ui.df(caps)
            st.caption("Les briques absentes n empechent rien : chaque outil "
                       "bascule sur une methode de repli et l annonce dans son "
                       "resultat.")

    onglets = st.tabs([f"{ICONES[f]} {f}" for f in FAMILLES]
                      + ["\U0001F501 Enchainements", "\U0001F4E6 Lot"])

    for tab, fam in zip(onglets, FAMILLES):
        with tab:
            outils = workflows.par_famille(fam)
            labels = {o.id: o.nom for o in outils}
            choix = st.radio("Outil", list(labels.keys()),
                             format_func=lambda k: labels[k],
                             horizontal=True, key=f"sel_{fam}")
            outil = next(o for o in outils if o.id == choix)
            st.markdown(f"### {outil.nom}")
            st.markdown(
                ui.badge(f"agent {outil.agent}", "brand") + " "
                + ui.badge(f"{outil.entree} → {outil.sortie}", "grey"),
                unsafe_allow_html=True)
            _form(outil, f"{fam}_{outil.id}")

    with onglets[len(FAMILLES)]:
        _workflows()
    with onglets[len(FAMILLES) + 1]:
        _lot()
