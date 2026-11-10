"""SYNTHEA - les seize agents et leur orchestrateur.

Chaque agent a un role unique, des entrees et des sorties explicites. Ils se
passent le relais dans un ordre fixe et inscrivent chacune de leurs actions dans
un journal horodate, consultable dans l onglet « Agents ».

  ATLAS     ingestion et extraction multi-format
  BOUSSOLE  segmentation, pagination, ossature du document
  PRISME    analyse semantique et apprentissage automatique
  SCRIBE    synthese hierarchique page / section / executif
  LEXIS     terminologie metier (57 CSV, 134 metiers)
  CAMELEON  restitution selon le contexte (12 contextes)
  BABEL     traduction en cinq langues
  ATELIER   illustrations, schemas et infographies
  ARGUS     autoverification de couverture et de fidelite
  VIGIE     recherche ciblee, base locale d abord
  ECHO      dialogue avec le document
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

from . import (budget, chunking, contexts, extraction, imaging, lexicons, llm,
               qa, summarizer, translation, utils, verification, websearch)


# =====================================================================
# Registre
# =====================================================================
@dataclass
class AgentSpec:
    code: str
    nom: str
    role: str
    mission: str
    entrees: str
    sorties: str
    technologies: str
    sigil: str


AGENTS: list[AgentSpec] = [
    AgentSpec("A01", "ATLAS", "Ingestion et extraction",
              "Lit tous les formats (PDF, Word, PowerPoint, Excel, HTML, JPEG, CSV, "
              "EPUB, ZIP) et transforme chaque unite logique en page numerotee et "
              "horodatee, avec son empreinte et ses avertissements.",
              "fichiers importes", "corpus pagine (jusqu a 2000 pages)",
              "pypdf, pdfplumber, python-docx, python-pptx, openpyxl, BeautifulSoup, "
              "Pillow, OCR tesseract (optionnel)", "AT"),
    AgentSpec("A02", "BOUSSOLE", "Segmentation et cartographie",
              "Decoupe le corpus en blocs qui ne traversent jamais une frontiere de "
              "fichier, detecte les titres et dresse la carte de couverture page par bloc.",
              "corpus pagine", "blocs page-aware, ossature, carte de couverture",
              "regex d ossature, fenetre glissante avec recouvrement", "BO"),
    AgentSpec("A03", "PRISME", "Analyse semantique et apprentissage",
              "Extrait les mots-cles TF-IDF, decouvre les themes par factorisation "
              "NMF, regroupe les blocs par KMeans, classe le type de document et "
              "repere les entites (dates, montants, organisations, pays).",
              "blocs", "mots-cles, themes, clusters, typologie, entites",
              "scikit-learn : TF-IDF, NMF, KMeans, Naive Bayes, c-TF-IDF", "PR"),
    AgentSpec("A04", "SCRIBE", "Synthese hierarchique",
              "Produit trois niveaux de synthese : un digest par page, une synthese "
              "par section, un resume executif. Chaque phrase reste rattachee a sa "
              "page d origine.",
              "blocs, mots-cles", "arbre de synthese tracable",
              "TextRank, regression logistique supervisee, selection MMR", "SC"),
    AgentSpec("A05", "LEXIS", "Terminologie metier",
              "Identifie le vocabulaire professionnel present dans le document, "
              "detecte les secteurs concernes, developpe les sigles et constitue le "
              "glossaire cible en cinq langues.",
              "texte du corpus", "glossaire, secteurs, sigles, registres",
              "57 CSV, 134 metiers, 37 secteurs, 1763 entrees", "LE"),
    AgentSpec("A06", "CAMELEON", "Restitution contextuelle",
              "Reorganise les constats selon le contexte de presentation : pitch "
              "entrepreneurial, comite de direction, campagne presidentielle, conseil "
              "d administration, cours magistral, fiche de lecture et sept autres.",
              "arbre de synthese", "restitution structuree par contexte",
              "affinites lexicales, allocation par rubrique, banques de formules", "CA"),
    AgentSpec("A07", "BABEL", "Traduction multilingue",
              "Traduit titres, rubriques et constats en francais, anglais, espagnol, "
              "portugais et creole haitien, avec taux de couverture mesure.",
              "restitution", "restitution traduite + glossaire",
              "glossaire hors ligne, deep-translator et modele de langue en option", "BA"),
    AgentSpec("A08", "ATELIER", "Illustration et mise en image",
              "Fabrique couvertures, schemas de themes, nuages de mots, graphiques, "
              "cartons de citation et infographies, et retouche les images importees.",
              "themes, synthese, images importees", "jeu de visuels PNG",
              "Pillow, matplotlib, wordcloud", "AL"),
    AgentSpec("A09", "ARGUS", "Autoverification",
              "Verifie en neuf controles que toutes les pages ont ete extraites, "
              "segmentees, analysees et resumees, qu aucun chiffre n a ete invente et "
              "que chaque constat porte sa reference.",
              "corpus, blocs, synthese", "rapport d audit, score, recommandations",
              "controles de couverture, fidelite numerique et litterale, empreintes", "AR"),
    AgentSpec("A10", "VIGIE", "Recherche ciblee",
              "Interroge d abord la base locale de 57 CSV, puis, si le reseau est "
              "disponible, complete par une recherche restreinte aux domaines "
              "officiels (Legifrance, EUR-Lex, GAFI, ACPR, INSEE, Banque mondiale...).",
              "mots-cles du document", "resultats locaux et web, sources recommandees",
              "index CSV, requetes site: ciblees, archivage local", "VI"),
    AgentSpec("A11", "ECHO", "Dialogue avec le document",
              "Repond aux questions en citant les pages : recherche hybride BM25 et "
              "TF-IDF, puis selection des phrases repondantes. Ne sort jamais du corpus.",
              "question, blocs", "reponse sourcee + extraits",
              "BM25 maison, similarite cosinus, typage de question", "EC"),
    # ---- atelier de transformation documentaire (onglet Transforme docs) ----
    AgentSpec("T01", "FORGE", "Conversion de format",
              "Convertit dans les deux sens : PDF vers Word, PowerPoint, Excel, "
              "JPEG, Markdown, texte et PDF/A ; Word, PowerPoint, Excel, images et "
              "HTML vers PDF. Utilise LibreOffice quand il est present pour une "
              "fidelite de mise en page, et le dit quand il reconstruit.",
              "pdf, docx, pptx, xlsx, images, html, url",
              "pdf, docx, pptx, xlsx, md, txt, jpg",
              "LibreOffice, pdfplumber, pypdfium2, python-docx, python-pptx, "
              "xlsxwriter, reportlab", "FO"),
    AgentSpec("T02", "MOSAIQUE", "Organisation des pages",
              "Fusionne, divise, extrait, supprime, reordonne, pivote, recadre et "
              "numerote. Toutes les operations acceptent des plages de pages du "
              "type « 1-5, 8, 12- ».",
              "un ou plusieurs PDF", "pdf reorganise",
              "pypdf, reportlab (calques de numerotation)", "MO"),
    AgentSpec("T03", "ATOME", "Optimisation et lisibilite",
              "Compresse sans perte ou par reechantillonnage, repare les fichiers "
              "endommages, ajoute une couche de texte OCR aux scans, et transforme "
              "des photos de documents en PDF propre.",
              "pdf, images", "pdf allege, repare ou cherchable",
              "pikepdf, qpdf, tesseract, pypdfium2, Pillow", "AT"),
    AgentSpec("T04", "SCEAU", "Securite et edition",
              "Chiffre en AES-256, deverrouille avec le mot de passe, appose "
              "filigranes et signatures visuelles, caviarde reellement les "
              "informations sensibles et permet d annoter les pages.",
              "pdf", "pdf protege, filigrane, caviarde ou annote",
              "pikepdf (chiffrement), pypdf, reportlab, pdfplumber "
              "(localisation des termes)", "SC"),
    AgentSpec("T05", "COLLATEUR", "Intelligence documentaire",
              "Compare deux versions avec un rapport cote a cote, extrait les "
              "tableaux, detecte et remplit les formulaires, inspecte et corrige "
              "les metadonnees, et branche la synthese et la traduction SYNTHEA "
              "directement sur un PDF.",
              "un ou deux PDF", "rapport html, xlsx, pdf, md",
              "difflib, pdfplumber, pypdf, pikepdf, chaine SYNTHEA", "CO"),
]

AGENTS_ANALYSE = [a for a in AGENTS if a.code.startswith("A")]
AGENTS_TRANSFORMATION = [a for a in AGENTS if a.code.startswith("T")]

AGENTS_BY_NAME = {a.nom: a for a in AGENTS}


# =====================================================================
# Journal
# =====================================================================
@dataclass
class LogEntry:
    t: str
    agent: str
    level: str
    message: str
    duree: float = 0.0


@dataclass
class Journal:
    entries: list[LogEntry] = field(default_factory=list)

    def log(self, agent: str, message: str, level: str = "info",
            duree: float = 0.0) -> None:
        self.entries.append(LogEntry(
            datetime.now().strftime("%H:%M:%S"), agent, level, message, round(duree, 2)))

    def to_html(self) -> str:
        import html as _h
        rows = []
        for e in self.entries:
            cls = {"warn": "w", "error": "e"}.get(e.level, "")
            d = f" <span class='t'>[{e.duree:.2f}s]</span>" if e.duree else ""
            rows.append(f"<div><span class='t'>{e.t}</span> "
                        f"<span class='a'>{_h.escape(e.agent):>9}</span> "
                        f"<span class='{cls}'>{_h.escape(e.message)}</span>{d}</div>")
        return "<div class='sx-log'>" + "".join(rows) + "</div>"

    def to_rows(self) -> list[dict]:
        return [{"heure": e.t, "agent": e.agent, "niveau": e.level,
                 "message": e.message, "duree_s": e.duree} for e in self.entries]


# =====================================================================
# Orchestrateur
# =====================================================================
DEFAULTS = {
    "ocr": True,
    "ocr_langs": "fra+eng",
    "max_pages": 2000,
    "objectif": "lecture_rapide",
    "ajustement_longueur": 1.0,
    "profondeur": "standard",
    "langue": "fr",
    "max_sections": 12,
    "target_words": 900,
    "contextes": ["comite_direction"],
    "langues_cibles": [],
    "palette": "sable",
    "visuels": True,
    "veille": False,
    "veille_thematique": "",
    "use_llm": False,
}


class Orchestrator:
    """Execute la chaine complete et conserve l etat partage entre agents."""

    def __init__(self, options: dict | None = None) -> None:
        self.opt = {**DEFAULTS, **(options or {})}
        self.journal = Journal()
        self.state: dict[str, Any] = {}
        self.timings: dict[str, float] = {}

    # ------------------------------------------------------------- utils
    def _run(self, agent: str, label: str, fn: Callable, level_on_empty: str = "warn"):
        t0 = time.time()
        self.journal.log(agent, f"demarrage — {label}")
        try:
            res = fn()
            dt = time.time() - t0
            self.timings[agent] = self.timings.get(agent, 0.0) + dt
            self.journal.log(agent, f"termine — {label}", "info", dt)
            return res
        except Exception as exc:
            dt = time.time() - t0
            self.journal.log(agent, f"echec — {label} : "
                                    f"{exc.__class__.__name__}: {exc}", "error", dt)
            return None

    def progress_proxy(self, cb, lo: float, hi: float):
        def inner(frac: float, msg: str) -> None:
            if cb:
                cb(lo + (hi - lo) * max(0.0, min(1.0, frac)), msg)
        return inner

    # --------------------------------------------------------------- run
    def run(self, files: list[tuple[str, bytes]], progress=None) -> dict:
        o = self.opt
        self.journal.log("SYNTHEA", f"session ouverte — {len(files)} fichier(s), "
                                    f"profondeur « {o['profondeur']} », "
                                    f"limite {o['max_pages']} pages")

        # ---------------- A01 ATLAS -----------------------------------
        doc = self._run("ATLAS", "extraction multi-format", lambda: extraction.build_document(
            files, ocr=o["ocr"], ocr_langs=o["ocr_langs"], max_pages=o["max_pages"],
            progress=self.progress_proxy(progress, 0.00, 0.22)))
        if doc is None or not doc.pages:
            self.journal.log("ATLAS", "aucune page exploitable", "error")
            return self.state
        self.state["doc"] = doc
        caps = extraction.capabilities()
        self.journal.log("ATLAS", f"{doc.n_pages} unites, {utils.human_int(doc.n_words)} mots, "
                                  f"{len(doc.files)} fichier(s)")
        if doc.empty_pages:
            self.journal.log("ATLAS", f"{len(doc.empty_pages)} page(s) sans texte "
                                      f"extractible" + ("" if caps["ocr"] else
                                      " — OCR indisponible (pytesseract absent)"),
                             "warn")
        if doc.meta.get("tronque"):
            self.journal.log("ATLAS", f"corpus tronque a {o['max_pages']} unites", "warn")

        # ---------------- dimensionnement -----------------------------
        bud = budget.compute(doc.n_pages, doc.n_words, o.get("objectif", "lecture_rapide"),
                             float(o.get("ajustement_longueur", 1.0)))
        self.state["budget"] = bud
        self.journal.log("SYNTHEA", f"objectif « {bud.objectif_libelle} » — "
                                    f"{bud.resume_court()}")
        if o.get("profondeur") == "auto":
            o["profondeur"] = bud.profondeur
            self.journal.log("SYNTHEA", f"profondeur deduite de l objectif : "
                                        f"{o['profondeur']}")

        # ---------------- A02 BOUSSOLE --------------------------------
        chunks = self._run("BOUSSOLE", "segmentation page-aware", lambda: chunking.make_chunks(
            doc, target_words=o["target_words"]))
        chunks = chunks or []
        self.state["chunks"] = chunks
        self.state["outline"] = chunking.detect_outline(doc)
        self.state["structure"] = chunking.structure_stats(doc, chunks)
        self.journal.log("BOUSSOLE", f"{len(chunks)} blocs, "
                                     f"{len(self.state['outline'])} titres detectes")
        if progress:
            progress(0.26, "segmentation terminee")

        # ---------------- A03 PRISME (via SCRIBE) ---------------------
        self.journal.log("PRISME", "analyse semantique deleguee au pipeline de synthese "
                                   "(TF-IDF, NMF, KMeans, Naive Bayes)")

        # ---------------- A04 SCRIBE ----------------------------------
        tree = self._run("SCRIBE", f"synthese hierarchique ({o['profondeur']})",
                         lambda: summarizer.build_summary(
                             doc, chunks, depth=o["profondeur"], lang=o["langue"],
                             max_sections=o["max_sections"], use_llm=o["use_llm"],
                             budget=bud,
                             progress=self.progress_proxy(progress, 0.26, 0.62)))
        if tree is None:
            return self.state
        self.state["tree"] = tree
        self.journal.log("PRISME", f"{len(tree.keywords)} mots-cles, "
                                   f"{len(tree.topics)} themes, type « {tree.doc_type} »")
        self.journal.log("SCRIBE", f"{len(tree.sections)} sections, "
                                   f"{len(tree.all_claims)} constats, "
                                   f"{tree.stats.get('pages_resumees', 0)} pages resumees")
        if tree.stats.get("modele_supervise"):
            self.journal.log("SCRIBE", f"classeur supervise entraine sur "
                                       f"{tree.stats.get('echantillon_entrainement')} phrases")
        else:
            self.journal.log("SCRIBE", "classeur supervise non entraine (corpus court) : "
                                       "repli heuristique", "warn")

        # ---------------- A05 LEXIS -----------------------------------
        def _lexis():
            txt = doc.full_text()[:400000]
            return {
                "secteurs": lexicons.detecter_secteurs(txt),
                "jargon": lexicons.jargon_present(txt, limit=120),
                "sigles": lexicons.developper_sigles(doc.full_text()[:200000]),
                "pays": lexicons.pays_cites(txt),
                "stats": lexicons.stats(),
            }
        lex = self._run("LEXIS", "terminologie metier", _lexis) or {}
        self.state["lexis"] = lex
        if lex:
            secs = ", ".join(f"{s} ({n})" for s, n, _ in lex["secteurs"][:4]) or "aucun"
            self.journal.log("LEXIS", f"{len(lex['jargon'])} termes metier reperes — "
                                      f"secteurs : {secs}")
        if progress:
            progress(0.66, "terminologie analysee")

        # ---------------- A06 CAMELEON --------------------------------
        def _cam():
            cles = o["contextes"] or [bud.contexte_conseille]
            return {k: contexts.render(tree, k, doc.title, lang=o["langue"],
                                       target_words=bud.mots_cible)
                    for k in cles}
        rends = self._run("CAMELEON", "restitutions contextuelles", _cam) or {}
        self.state["renditions"] = rends
        if rends:
            self.journal.log("CAMELEON", "contextes produits : " +
                             ", ".join(r.context_label for r in rends.values()))
            # controle du dimensionnement sur le livrable reellement lu
            principal = next(iter(rends.values()))
            distincts = list({id(c): c for c in tree.all_claims}.values())
            moy = (sum(utils.word_count(c.text) for c in distincts) / len(distincts)
                   if distincts else 0.0)
            ctrl = budget.controle(bud, utils.word_count(principal.plain_text()),
                                   len(distincts), moy)
            tree.stats["controle_budget"] = ctrl
            self.state["controle_budget"] = ctrl
            self.journal.log("CAMELEON", f"dimensionnement : {ctrl['message']}",
                             "info" if ctrl["statut"] == "conforme" else "warn")
        if progress:
            progress(0.72, "restitutions produites")

        # ---------------- A07 BABEL -----------------------------------
        trads: dict[str, dict] = {}
        if o["langues_cibles"]:
            engine = translation.best_engine()
            self.journal.log("BABEL", f"moteur retenu : {translation.ENGINES[engine]}")

            def _babel():
                out: dict[str, dict] = {}
                for ckey, rend in rends.items():
                    out[ckey] = {}
                    for lg in o["langues_cibles"]:
                        if lg == o["langue"]:
                            continue
                        out[ckey][lg] = translation.translate_rendition(rend, lg, engine)
                return out
            trads = self._run("BABEL", "traduction des restitutions", _babel) or {}
            for ckey, per_lang in trads.items():
                for lg, r in per_lang.items():
                    self.journal.log("BABEL", f"{lexicons.LANG_LABELS.get(lg, lg)} : "
                                              f"couverture "
                                              f"{r.meta.get('traduction_couverture', 0):.0%}")
        self.state["traductions"] = trads
        if progress:
            progress(0.78, "traductions terminees")

        # ---------------- A08 ATELIER ---------------------------------
        images: dict[str, bytes] = {}
        if o["visuels"]:
            images = self._run("ATELIER", "production des visuels",
                               lambda: imaging.illustration_pack(
                                   doc.title, tree, doc, o["palette"])) or {}
            self.journal.log("ATELIER", f"{len(images)} visuel(s) genere(s) "
                                        f"(palette « {o['palette']} »)")
        self.state["images"] = images
        if progress:
            progress(0.86, "visuels produits")

        # ---------------- A09 ARGUS -----------------------------------
        audit = self._run("ARGUS", "autoverification en neuf controles",
                          lambda: verification.audit(doc, chunks, tree))
        self.state["audit"] = audit
        self.state["page_rows"] = verification.page_table(doc, chunks, tree)
        if audit:
            self.journal.log("ARGUS", f"score {audit['score']:.1f}/100 — {audit['verdict']}")
            for code, c in audit["controles"].items():
                if c["statut"] != "ok":
                    self.journal.log("ARGUS", f"{code} {c['libelle']} : {c['statut']}",
                                     "warn" if c["statut"] == "attention" else "error")
        if progress:
            progress(0.92, "verification terminee")

        # ---------------- A10 VIGIE -----------------------------------
        veille = None
        if o["veille"]:
            kws = [k for k, _ in tree.keywords[:5]]
            veille = self._run("VIGIE", "recherche ciblee",
                               lambda: websearch.targeted_search(
                                   kws, o["veille_thematique"]))
            if veille:
                self.journal.log("VIGIE", f"mode {veille['mode']} — "
                                          f"{len(veille['web']['resultats'])} resultat(s) web, "
                                          f"{veille['local']['n_total']} elements locaux")
        self.state["veille"] = veille

        # ---------------- A11 ECHO ------------------------------------
        retr = self._run("ECHO", "indexation pour le dialogue",
                         lambda: qa.Retriever(chunks, o["langue"]))
        self.state["retriever"] = retr
        if retr is not None:
            self.journal.log("ECHO", f"index pret sur {len(chunks)} blocs "
                                     f"(BM25 + TF-IDF)")

        self.state["journal"] = self.journal
        self.state["timings"] = self.timings
        self.state["options"] = o
        self.state["llm"] = llm.status()
        total = sum(self.timings.values())
        self.journal.log("SYNTHEA", f"pipeline complet en {total:.1f}s")
        if progress:
            progress(1.0, "pipeline termine")
        return self.state


# =====================================================================
# Fiches agents pour l interface
# =====================================================================
def agent_cards_html(agents: list[AgentSpec] | None = None) -> str:
    import html as _h
    out = []
    for a in (agents if agents is not None else AGENTS):
        out.append(
            f"<div class='sx-agent'><div class='sigil'>{a.sigil}</div><div>"
            f"<div class='nm'>{_h.escape(a.nom)} "
            f"<span class='sx-badge b-grey'>{a.code}</span></div>"
            f"<div class='ro'>{_h.escape(a.role)}</div>"
            f"<div class='ms'>{_h.escape(a.mission)}</div>"
            f"<div class='ms'><strong>entrees</strong> : {_h.escape(a.entrees)} · "
            f"<strong>sorties</strong> : {_h.escape(a.sorties)}</div>"
            f"<div class='ms' style='opacity:.75'>{_h.escape(a.technologies)}</div>"
            f"</div></div>")
    return "".join(out)


def agent_rows() -> list[dict]:
    return [{"code": a.code, "agent": a.nom, "role": a.role, "mission": a.mission,
             "entrees": a.entrees, "sorties": a.sorties,
             "technologies": a.technologies} for a in AGENTS]
