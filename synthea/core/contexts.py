"""SYNTHEA - Agent CAMELEON : restitution de la synthese selon le contexte.

Un meme document se presente differemment devant un jury d investisseurs, un
comite de direction, un meeting de campagne ou un amphitheatre. CAMELEON
reorganise les constats de SCRIBE selon la structure, le registre et les regles
de style du contexte choisi (12 contextes decrits dans
data/lexicons/55_contextes_restitution.csv).
"""
from __future__ import annotations

import re

import numpy as np

from . import lexicons, llm, utils
from .models import Claim, Rendition, SummaryTree

# champs lexicaux associes aux rubriques les plus courantes
CUES: dict[str, list[str]] = {
    "accroche": ["enjeu", "aujourd hui", "chaque annee", "constat", "probleme", "crise"],
    "ouverture": ["objet", "contexte", "present", "rapport", "document"],
    "adresse": ["nous", "ensemble", "vous", "pays", "citoyen"],
    "probleme": ["probleme", "difficulte", "obstacle", "echec", "insuffisance",
                 "retard", "manque", "defaillance", "risque", "faiblesse"],
    "diagnostic": ["constat", "situation", "etat des lieux", "donnees", "chiffre",
                   "evolution", "tendance", "degradation"],
    "contexte": ["contexte", "cadre", "historique", "origine", "depuis", "annee"],
    "constat": ["constate", "observe", "resultat", "donnees", "mesure", "niveau"],
    "analyse": ["analyse", "explique", "cause", "facteur", "mecanisme", "raison",
                "consequence", "correlation"],
    "solution": ["solution", "dispositif", "outil", "methode", "plateforme",
                 "reponse", "propose", "permet"],
    "rupture": ["changer", "rupture", "transformer", "reforme", "nouveau", "refonder"],
    "marche": ["marche", "client", "demande", "volume", "segment", "croissance",
               "concurrence", "part"],
    "preuve": ["resultat", "mesure", "test", "pilote", "experimentation", "donnees",
               "chiffre", "pourcentage", "etude", "evaluation"],
    "traction": ["croissance", "client", "utilisateur", "adoption", "revenu", "signe"],
    "modele": ["modele", "revenu", "prix", "marge", "cout", "financement",
               "rentabilite", "economique"],
    "performance": ["resultat", "performance", "chiffre", "marge", "indicateur",
                    "exercice", "evolution"],
    "equipe": ["equipe", "fondateur", "competence", "experience", "profil",
               "gouvernance", "direction"],
    "option": ["option", "scenario", "alternative", "hypothese", "variante", "choix"],
    "recommandation": ["recommande", "propose", "convient", "faut", "devrait",
                       "preconise", "priorite"],
    "engagement": ["engagement", "promesse", "nous ferons", "objectif", "garantir",
                   "assurer", "mettre en place"],
    "financement": ["financement", "budget", "cout", "ressource", "euro", "credit",
                    "investissement", "economie"],
    "risque": ["risque", "menace", "vigilance", "limite", "incertitude", "alea",
               "fragilite", "exposition"],
    "limite": ["limite", "incertitude", "biais", "lacune", "reserve", "faiblesse"],
    "gouvernance": ["gouvernance", "controle", "procedure", "conformite", "audit",
                    "responsabilite", "dispositif"],
    "calendrier": ["calendrier", "delai", "echeance", "mois", "trimestre", "annee",
                   "etape", "planning"],
    "moyen": ["moyen", "ressource", "effectif", "outil", "budget", "equipe"],
    "demande": ["cherche", "besoin", "demande", "leve", "souhaite", "solliciter"],
    "appel": ["ensemble", "mobilisation", "agir", "rejoignez", "avec vous", "maintenant"],
    "decision": ["decision", "arbitrage", "valider", "approuver", "trancher",
                 "autoriser", "soumis"],
    "resolution": ["approuver", "autoriser", "resolution", "mandat", "quitus"],
    "objectif": ["objectif", "but", "vise", "cible", "ambition", "finalite"],
    "definition": ["est defini", "designe", "signifie", "appelle", "notion",
                   "concept", "au sens"],
    "developpement": ["ainsi", "donc", "ensuite", "mecanisme", "principe", "regle"],
    "illustration": ["exemple", "cas", "illustration", "concretement", "ainsi",
                     "pratique", "terrain"],
    "erreur": ["erreur", "confusion", "attention", "piege", "faux", "contrairement"],
    "synthese": ["en resume", "au total", "essentiel", "retenir", "conclusion",
                 "globalement"],
    "perspective": ["perspective", "avenir", "prochain", "futur", "horizon",
                    "anticipe", "prevision"],
    "these": ["these", "auteur", "soutient", "demontre", "affirme", "idee centrale"],
    "architecture": ["chapitre", "partie", "structure", "plan", "demarche", "progression"],
    "apport": ["apport", "contribution", "interet", "original", "eclaire", "utile"],
    "citation": ["\"", "«", "selon", "ecrit", "affirme"],
    "mots-cles": [],
    "avancement": ["avance", "realise", "termine", "en cours", "livre", "etape"],
    "blocage": ["bloque", "blocage", "retard", "attente", "difficulte", "probleme"],
    "qui fait quoi": ["responsable", "charge", "pilote", "equipe", "affecte"],
    "echeance": ["echeance", "delai", "date", "semaine", "prochaine"],
    "recit": ["histoire", "annee", "jour", "personne", "decide", "commence"],
    "tension": ["mais", "pourtant", "difficulte", "obstacle", "echec", "doute"],
    "basculement": ["alors", "soudain", "change", "decide", "tourne", "bascule"],
    "enseignement": ["lecon", "enseigne", "montre", "comprendre", "retenir"],
    "diligence": ["verifie", "controle", "analyse", "examine", "collecte", "piece"],
    "typologie": ["typologie", "schema", "montage", "flux", "operation", "espece"],
    "conclusion": ["conclusion", "donc", "en definitive", "au total", "il ressort"],
    "suite": ["suite", "prochaine", "transmettre", "proposer", "poursuivre"],
    "rappel": ["rappel", "pour memoire", "anterieur", "precedent", "deja"],
    "proposition": ["propose", "suggere", "recommande", "il convient"],
    "chiffre": ["%", "euro", "million", "milliard", "taux", "montant", "volume"],
    "hypothese": ["hypothese", "suppose", "si", "scenario", "estimation", "projection"],
    "verifier": ["verifier", "confirmer", "controler", "valider", "completer"],
}


# ------------------------------------------------------------------ outils
def available_contexts() -> list[dict]:
    return lexicons.contextes()


def context_labels() -> dict[str, str]:
    return {c["cle"]: c["libelle"] for c in lexicons.contextes()}


def _cue_words(heading: str) -> list[str]:
    hn = utils.normalize(heading)
    cues: list[str] = []
    for key, words in CUES.items():
        if key in hn or hn in key:
            cues.extend(words)
    if not cues:                      # heuristique : les mots du titre lui-meme
        cues = [w for w in hn.split() if len(w) > 4]
    return cues


def _affinity(claim_text: str, cues: list[str]) -> float:
    cn = utils.normalize(claim_text)
    if not cues:
        return 0.0
    hits = sum(1 for c in cues if c and utils.normalize(c) in cn)
    bonus = 0.25 if re.search(r"\d", claim_text) and any(
        c in ("%", "euro", "million", "chiffre") for c in cues) else 0.0
    return hits / len(cues) + bonus


def _allocate(claims: list[Claim], headings: list[str],
              per_heading: int) -> dict[str, list[Claim]]:
    """Repartit les constats entre les rubriques, sans doublon."""
    if not claims:
        return {h: [] for h in headings}
    cues = {h: _cue_words(h) for h in headings}
    score = np.zeros((len(headings), len(claims)))
    for i, h in enumerate(headings):
        for j, c in enumerate(claims):
            score[i, j] = _affinity(c.text, cues[h]) + 0.001 * c.score

    alloc: dict[str, list[Claim]] = {h: [] for h in headings}
    used: set[int] = set()

    # premier tour : la meilleure phrase pour chaque rubrique
    for i, h in enumerate(headings):
        order = np.argsort(-score[i])
        for j in order:
            if int(j) not in used:
                alloc[h].append(claims[int(j)])
                used.add(int(j))
                break

    # tours suivants : on complete par affinite decroissante
    for _ in range(per_heading - 1):
        for i, h in enumerate(headings):
            order = np.argsort(-score[i])
            for j in order:
                jj = int(j)
                if jj in used:
                    continue
                if score[i, jj] <= 0 and len(alloc[h]) >= 2:
                    break
                alloc[h].append(claims[jj])
                used.add(jj)
                break

    # reste : reparti sur les rubriques les moins garnies, dans l ordre du document
    leftovers = [c for j, c in enumerate(claims) if j not in used]
    leftovers.sort(key=lambda c: (c.pages[0] if c.pages else 0))
    for c in leftovers:
        if all(len(v) >= per_heading for v in alloc.values()):
            break
        h = min(headings, key=lambda x: len(alloc[x]))
        alloc[h].append(c)

    for h in headings:
        alloc[h].sort(key=lambda c: (c.pages[0] if c.pages else 0))
    return alloc


def _as_bullet(claim: Claim, with_refs: bool, max_chars: int) -> str:
    txt = utils.truncate(claim.text.strip(), max_chars)
    return f"{txt} ({claim.ref})" if with_refs and claim.ref else txt


# ------------------------------------------------------------------ rendu
def render(tree: SummaryTree, context_key: str, doc_title: str,
           lang: str = "fr", with_refs: bool = True,
           length_factor: float = 1.0, use_llm: bool = False,
           extra: dict | None = None, target_words: int | None = None) -> Rendition:
    """target_words : impose la longueur calculee par core.budget ; sinon on
    retombe sur la longueur cible propre au contexte."""
    ctx = lexicons.contextes_index().get(context_key)
    if ctx is None:
        ctx = lexicons.contextes()[0]
        context_key = ctx["cle"]

    headings = [h.strip() for h in ctx["structure"].split("|") if h.strip()]
    base_words = float(target_words or ctx.get("longueur_cible_mots", 600))
    target_words = int(base_words * max(0.3, length_factor))
    # un constat fait environ 32 mots : on en met juste assez par rubrique pour
    # atteindre la longueur visee, sans jamais depasser 12
    max_chars = 300 if ctx["registre"] in ("oratoire", "accessible") else 400

    # un constat partage par plusieurs sections ne doit apparaitre qu une fois
    claims = list({id(c): c for c in tree.all_claims}.values())
    # nombre de constats par rubrique deduit de la longueur reelle des constats,
    # pour atteindre la cible de core.budget sans la depasser
    echantillon = claims[:60] or []
    moy = (sum(utils.word_count(c.text) for c in echantillon) / len(echantillon)
           if echantillon else 30.0)
    moy = max(10.0, moy)
    per_heading = max(1, min(24, round(target_words / max(len(headings), 1) / moy)))
    alloc = _allocate(claims, headings, per_heading)
    forms = lexicons.formules_du_contexte(context_key, lang)
    extra = {**auto_variables(tree, doc_title), **(extra or {})}

    rend = Rendition(
        context_key=context_key,
        context_label=ctx["libelle"],
        language=lang,
        title=f"{ctx['libelle']} — {doc_title}",
        meta={
            "public": ctx.get("public", ""),
            "registre": ctx.get("registre", ""),
            "ton": ctx.get("ton", ""),
            "regles": ctx.get("regles", ""),
            "longueur_cible": target_words,
            "type_document": tree.doc_type,
            "refs": with_refs,
        },
    )

    # ouverture : formule du contexte + accroche
    opening = forms.get("accroche") or forms.get("ouverture") or forms.get("objet", "")
    for i, h in enumerate(headings):
        bullets = [_as_bullet(c, with_refs, max_chars) for c in alloc.get(h, [])]
        paragraphs: list[str] = []
        pages = sorted({p for c in alloc.get(h, []) for p in c.pages})

        if i == 0 and opening:
            txt = _fill(opening, extra)
            if txt:
                paragraphs.append(txt)
        if i == len(headings) - 1:
            closing = forms.get("cloture") or forms.get("appel", "")
            txt = _fill(closing, extra) if closing else None
            if txt:
                paragraphs.append(txt)

        # registres oratoire / narratif : phrases en continu plutot qu en puces
        if ctx["registre"] in ("oratoire", "narratif") and bullets:
            paragraphs.append(" ".join(b.rstrip(".") + "." for b in bullets))
            bullets = []

        rend.sections.append({
            "heading": h,
            "paragraphs": paragraphs,
            "bullets": bullets,
            "ref": utils.page_ref(pages) if with_refs else "",
        })

    # rubriques speciales
    _enrich(rend, tree, ctx, with_refs)

    if use_llm and llm.available():
        polished = llm.rewrite_for_context(
            rend.to_markdown(with_refs), ctx["libelle"], ctx.get("regles", ""),
            lexicons.LANG_LABELS.get(lang, "francais"))
        if polished and not polished.startswith("[llm"):
            rend.meta["version_abstractive"] = polished
    return rend


def _fill(template: str, extra: dict) -> str | None:
    """Remplit les variables {xxx} d une formule.

    Une formule dont une variable reste inconnue est ecartee : mieux vaut une
    rubrique sans phrase d accroche qu un texte parseme de marqueurs vides.
    """
    missing = [k for k in re.findall(r"\{(\w+)\}", template)
               if not str(extra.get(k, "")).strip()]
    if missing:
        return None
    return re.sub(r"\{(\w+)\}", lambda m: str(extra[m.group(1)]), template)


def auto_variables(tree: SummaryTree, doc_title: str) -> dict:
    """Variables deduites du document pour alimenter les formules."""
    ent = tree.entities or {}
    annees = [d for d in ent.get("dates", []) if re.fullmatch(r"(19|20)\d{2}", d)]
    out: dict[str, str] = {"objet": doc_title, "reference": doc_title}
    if annees:
        out["periode"] = max(annees)
    if ent.get("montants"):
        out["volume"] = ent["montants"][0]
    if tree.executive:
        out["these"] = utils.truncate(tree.executive[0].text.rstrip("."), 150)
        out["conclusion"] = utils.truncate(tree.executive[-1].text.rstrip("."), 150)
    if tree.topics:
        out["facteur"] = tree.topics[0]["libelle"]
    return out


def _enrich(rend: Rendition, tree: SummaryTree, ctx: dict, with_refs: bool) -> None:
    """Ajoute les rubriques factuelles attendues par certains contextes."""
    key = rend.context_key
    for s in rend.sections:
        hn = utils.normalize(s["heading"])

        if "mots-cles" in hn or "mots cles" in hn:
            s["bullets"] = [k for k, _ in tree.keywords[:14]]

        if "citation" in hn:
            cites = [c for c in tree.all_claims
                     if '"' in c.text or "«" in c.text][:5]
            if cites:
                s["bullets"] = [f"« {utils.truncate(c.text, 240)} » ({c.ref})"
                                for c in cites]

        if "chiffre" in hn and tree.entities:
            vals = (tree.entities.get("montants", [])[:6]
                    + tree.entities.get("pourcentages", [])[:6])
            if vals:
                s["bullets"] = (s["bullets"] or []) + [
                    "Donnees relevees dans le document : " + ", ".join(vals)]

        if "reference" in hn and key == "fiche_lecture":
            st = tree.stats
            s["paragraphs"] = [
                f"Type identifie : {tree.doc_type}. "
                f"{utils.human_int(st.get('pages', 0))} pages, "
                f"{utils.human_int(st.get('mots', 0))} mots, "
                f"{st.get('sections', 0)} sections analysees."
            ]

        if ("qui fait quoi" in hn or "moyens" in hn) and not s["bullets"]:
            s["bullets"] = ["Responsable a designer — action issue des constats ci-dessus"]

        if "perspective" in hn and not s["bullets"] and tree.topics:
            s["bullets"] = [f"Theme a approfondir : {t['libelle']} "
                            f"({int(t['poids'] * 100)} % du corpus)"
                            for t in tree.topics[:4]]


# ------------------------------------------------------- restitution multiple
def render_all(tree: SummaryTree, doc_title: str, keys: list[str],
               lang: str = "fr", with_refs: bool = True) -> dict[str, Rendition]:
    return {k: render(tree, k, doc_title, lang, with_refs) for k in keys}
