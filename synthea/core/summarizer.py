"""SYNTHEA - Agent SCRIBE : synthese hierarchique (map-reduce) jusqu a 2000 pages.

Trois niveaux, tous tracables a la page :
  1. digest de page      : la phrase la plus informative de chaque page
  2. synthese de section : les phrases centrales d un groupe de blocs
  3. resume executif     : re-classement des phrases de section

Le classement combine un modele supervise (regression logistique entrainee sur
des etiquettes TextRank) et, si disponible, une reformulation abstractive par
modele de langue (core.llm). Sans modele de langue, la synthese reste
extractive : chaque phrase provient litteralement du document, ce qui garantit
la fidelite et la tracabilite.
"""
from __future__ import annotations

import numpy as np

from . import budget as budget_mod
from . import lexicons, llm, ml, utils
from .models import Chunk, Claim, Document, SectionSummary, SummaryTree

# Seuils de dedoublonnage (indice de Jaccard sur les mots).
# SEUIL_LOCAL  : deux constats d une meme section trop proches.
# SEUIL_GLOBAL : un constat deja formule dans une autre section ; il n est pas
#   recopie, sa reference de page est enrichie. Il est cale juste au-dessus du
#   seuil de redondance d ARGUS (0,60) pour que tout ce qu ARGUS compterait
#   comme doublon soit effectivement fusionne, sans sur-filtrer les documents
#   au style formulaire (rapports, contrats, procedures) ou les phrases
#   partagent beaucoup de vocabulaire sans dire la meme chose.
SEUIL_LOCAL = 0.45
SEUIL_GLOBAL = 0.62

DEPTHS = {
    "rapide": {"page_digests": False, "claims_par_section": 3, "exec": 6,
               "libelle": "Rapide (blocs seulement)"},
    "standard": {"page_digests": True, "claims_par_section": 5, "exec": 8,
                 "libelle": "Standard (toutes les pages + sections)"},
    "exhaustif": {"page_digests": True, "claims_par_section": 8, "exec": 12,
                  "libelle": "Exhaustif (analyse fine page par page)"},
}


# ------------------------------------------------------------------ outils
def _page_index(doc: Document) -> list[tuple[int, str]]:
    return [(p.index, utils.normalize(p.text)) for p in doc.pages if p.text]


def _attribute(sentence: str, chunk: Chunk, pidx: list[tuple[int, str]]) -> list[int]:
    """Retrouve la ou les pages d origine d une phrase."""
    probe = utils.normalize(sentence)[:70]
    if probe:
        for pg, body in pidx:
            if chunk.page_start <= pg <= chunk.page_end and probe in body:
                return [pg]
        for pg, body in pidx:            # phrase a cheval sur deux pages
            if probe[:40] and probe[:40] in body:
                return [pg]
    return chunk.pages[:2]


def make_sections(doc: Document, chunks: list[Chunk],
                  max_sections: int = 12) -> list[list[Chunk]]:
    """Groupe les blocs en sections contigues, en coupant sur l ossature."""
    if not chunks:
        return []
    if len(chunks) <= max_sections:
        return [[c] for c in chunks]

    from .chunking import detect_outline
    titles = detect_outline(doc)
    breaks = sorted({o["page"] for o in titles if o["niveau"] == 1})

    groups: list[list[Chunk]] = []
    cur: list[Chunk] = []
    target = max(1, len(chunks) // max_sections)
    for ch in chunks:
        cur.append(ch)
        hit_break = any(ch.page_start <= b <= ch.page_end for b in breaks)
        if (hit_break and len(cur) >= max(2, target // 2)) or len(cur) >= target:
            groups.append(cur)
            cur = []
    if cur:
        if groups and len(cur) < max(1, target // 3):
            groups[-1].extend(cur)
        else:
            groups.append(cur)

    while len(groups) > max_sections:        # fusionne les plus petits voisins
        sizes = [sum(c.word_count for c in g) for g in groups]
        i = int(np.argmin(sizes[:-1])) if len(sizes) > 1 else 0
        groups[i].extend(groups.pop(i + 1))
    return groups


def _section_title(group: list[Chunk], keywords: list[str]) -> str:
    raw = (group[0].title or "").strip(" .:-")
    if 8 <= len(raw) <= 90 and not raw.lower().startswith("bloc "):
        return raw[:90]
    if keywords:
        return " / ".join(keywords[:3]).capitalize()
    return f"Pages {group[0].page_start}-{group[-1].page_end}"


# ------------------------------------------------------------------ moteur
SEUIL_RATTRAPAGE = 0.68      # tolerance de proximite pendant le rattrapage


def _completer(tree: SummaryTree, budget, reserves, global_claims, pidx) -> int:
    """Complete la synthese quand elle reste loin sous le format cible.

    La premiere passe privilegie la non-redondance : sur un document au style
    tres repetitif, elle peut s arreter bien en dessous de la taille demandee.
    Ce rattrapage reprend alors les meilleurs constats ecartes, par tours
    successifs sur toutes les sections, avec un seuil de proximite relache.
    Il s arrete des que la cible est atteinte : il n allonge jamais une
    synthese deja conforme.
    """
    def _jacc(a: set, b: set) -> float:
        return len(a & b) / max(len(a | b), 1)

    def total_mots() -> int:
        vus, n = set(), 0
        for s in tree.sections:
            for c in s.claims:
                if id(c) not in vus:
                    vus.add(id(c))
                    n += utils.word_count(c.text)
        return n

    cible = int(budget.mots_cible)
    if total_mots() >= 0.9 * cible:
        return 0

    curseurs = {id(sec): 0 for sec, _, _, _ in reserves}
    ajoutes = 0
    for _tour in range(14):
        progresse = False
        for sec, reserve, texts, sents in reserves:
            if total_mots() >= cible:
                return ajoutes
            restants = reserve[curseurs[id(sec)]:]
            if not restants:
                continue
            # on ne prend pas le mieux note mais le plus different de ce qui a
            # deja ete dit : c est ce qui evite de gonfler la redondance (C8)
            # en allongeant la synthese
            meilleur = None
            for rang, (sc, i) in enumerate(restants[:30]):
                toks = set(utils.normalize(texts[i]).split())
                propre = max((_jacc(toks, tk) for tk, _ in global_claims),
                             default=0.0)
                if propre > SEUIL_RATTRAPAGE:
                    continue
                note = (1.0 - propre) * 0.75 + float(sc) * 0.25
                if meilleur is None or note > meilleur[0]:
                    meilleur = (note, rang, i, toks)
            if meilleur is None:
                curseurs[id(sec)] = len(reserve)
                continue
            _note, rang, i, toks = meilleur
            ch = sents[i][1]
            claim = Claim(text=texts[i].strip(),
                          pages=_attribute(texts[i], ch, pidx),
                          score=float(restants[rang][0]), chunk_id=ch.cid)
            global_claims.append((toks, claim))
            sec.claims.append(claim)
            sec.claims.sort(key=lambda c: (c.pages[0] if c.pages else 0))
            curseurs[id(sec)] += rang + 1
            ajoutes += 1
            progresse = True
        if not progresse:
            break
    return ajoutes


def build_summary(doc: Document, chunks: list[Chunk], depth: str = "standard",
                  lang: str = "fr", max_sections: int = 12,
                  use_llm: bool = False, budget=None, progress=None) -> SummaryTree:
    cfg = dict(DEPTHS.get(depth, DEPTHS["standard"]))
    # le budget (core.budget) impose la taille sensee du livrable : il prime
    # sur les valeurs par defaut de la profondeur
    if budget is not None:
        cfg["claims_par_section"] = budget.constats_par_section
        cfg["exec"] = budget.constats_executif
        max_sections = budget.sections
    tree = SummaryTree(doc_id=doc.doc_id)
    if not chunks:
        return tree

    def step(frac: float, msg: str) -> None:
        if progress:
            progress(max(0.0, min(1.0, frac)), msg)

    chunk_texts = [c.text for c in chunks]

    # --- 1. mots-cles, themes, typologie -----------------------------
    step(0.05, "mots-cles et themes")
    tree.keywords = ml.keyphrases(chunk_texts, top=40, lang=lang)
    keyterms = [k for k, _ in tree.keywords]
    tree.topics = ml.topics(chunk_texts, n_topics=min(8, max(3, len(chunks) // 6)), lang=lang)
    tree.doc_type = ml.classify_document(doc.full_text()[:80000])[0][0]

    # --- 2. entrainement du classeur de phrases ----------------------
    step(0.14, "entrainement du modele de classement")
    sample: list[str] = []
    stride = max(1, len(chunks) // 22)
    for ch in chunks[::stride]:
        sample.extend(utils.split_sentences(ch.text)[:8])
    ranker = ml.SentenceRanker(lang).fit(sample[:360], keyterms)

    # --- 3. regroupement en sections ---------------------------------
    step(0.22, "regroupement thematique")
    labels, cluster_kw = ml.cluster_texts(chunk_texts, lang=lang)
    for ch, lb in zip(chunks, labels):
        ch.cluster = lb
    groups = make_sections(doc, chunks, max_sections=max_sections)

    pidx = _page_index(doc)

    # --- 4. digests de page ------------------------------------------
    if cfg["page_digests"]:
        step(0.30, f"analyse des {doc.n_pages} pages")
        total = max(doc.n_pages, 1)
        for i, p in enumerate(doc.pages):
            if i % 150 == 0:
                step(0.30 + 0.25 * i / total, f"page {p.index}/{total}")
            if p.is_empty:
                tree.page_digests[p.index] = ""
                continue
            if utils.is_tabular(p.text):
                n_rows = sum(1 for ln in p.text.split("\n") if "|" in ln)
                tree.page_digests[p.index] = (
                    f"Donnees tabulaires ({n_rows} lignes) — "
                    f"{utils.tabular_digest(p.text)}")
                continue
            sents = utils.split_sentences(p.text, min_len=30)
            if not sents:
                tree.page_digests[p.index] = utils.truncate(p.text, 220)
                continue
            sc = ranker.score(sents, keyterms)
            best = int(np.argmax(sc))
            tree.page_digests[p.index] = utils.truncate(sents[best], 320)

    # --- 5. syntheses de section -------------------------------------
    step(0.58, "synthese des sections")
    n_groups = max(len(groups), 1)
    # anti-doublon entre sections : jeton -> constat deja retenu
    global_claims: list[tuple[set[str], Claim]] = []
    # reserve par section, utilisee par le rattrapage de dimensionnement
    reserves: list[tuple[SectionSummary, list[tuple[float, int]], list[str], list]] = []
    for gi, group in enumerate(groups):
        step(0.58 + 0.28 * gi / n_groups, f"section {gi + 1}/{n_groups}")
        sents: list[tuple[str, Chunk]] = []
        for ch in group:
            for s in utils.split_sentences(ch.text, min_len=45):
                sents.append((s, ch))
        if not sents:
            continue
        # un bloc de donnees chiffrees est resume par son entete, pas recopie
        texts = [utils.tabular_digest(s) if utils.is_tabular(s) else s
                 for s, _ in sents]
        scores = ranker.score(texts, keyterms)
        for i, s in enumerate(texts):
            if utils.is_tabular(sents[i][0]):
                scores[i] *= 0.45          # le texte redige prime sur les tableaux

        k = min(cfg["claims_par_section"], len(texts))
        # selection avec penalite de redondance (MMR simplifie), locale ET globale.
        # Un constat deja retenu ailleurs n est pas repete : sa reference de page
        # est enrichie, ce qui donne « (p. 24, 38, 52) » au lieu de trois puces
        # identiques.
        chosen: list[int] = []
        taken_tokens: list[set[str]] = []
        claims: list[Claim] = []

        def _jacc(a: set, b: set) -> float:
            return len(a & b) / max(len(a | b), 1)

        for idx in np.argsort(-scores):
            i = int(idx)
            if texts[i].lstrip().startswith("#"):        # titre balise
                continue
            toks = set(utils.normalize(texts[i]).split())
            if len(toks) < 5:
                continue
            if any(_jacc(toks, t) > SEUIL_LOCAL for t in taken_tokens):
                continue
            jumeau = next((c for tk, c in global_claims if _jacc(toks, tk) > SEUIL_GLOBAL), None)
            if jumeau is not None:
                extra_pages = _attribute(texts[i], sents[i][1], pidx)
                jumeau.pages = sorted(set(jumeau.pages) | set(extra_pages))
                continue
            ch = sents[i][1]
            claim = Claim(text=texts[i].strip(),
                          pages=_attribute(texts[i], ch, pidx),
                          score=float(scores[i]), chunk_id=ch.cid)
            chosen.append(i)
            taken_tokens.append(toks)
            global_claims.append((toks, claim))
            claims.append(claim)
            if len(chosen) >= k:
                break

        # reserve de rattrapage : les meilleurs candidats ecartes de cette
        # section, gardes au cas ou la synthese finale serait trop courte
        reserve: list[tuple[float, int]] = []
        pris = set(chosen)
        for idx in np.argsort(-scores):
            i = int(idx)
            if i in pris or texts[i].lstrip().startswith("#"):
                continue
            if len(set(utils.normalize(texts[i]).split())) < 5:
                continue
            reserve.append((float(scores[i]), i))
            if len(reserve) >= 30:
                break

        if not claims:
            # section dont tout le contenu a deja ete dit ailleurs : on retient
            # la phrase la moins proche de ce qui precede, pour que la section
            # ne soit pas vide dans la restitution
            def _novelty(i: int) -> float:
                tk = set(utils.normalize(texts[i]).split())
                if not tk or not global_claims:
                    return 1.0
                return 1.0 - max(_jacc(tk, g) for g, _ in global_claims)
            best = sorted(range(len(texts)),
                          key=lambda i: (-_novelty(i), -scores[i]))[0]
            ch = sents[best][1]
            toks = set(utils.normalize(texts[best]).split())
            pages = _attribute(texts[best], ch, pidx)
            jumeau = next((c for tk, c in global_claims if _jacc(toks, tk) > SEUIL_GLOBAL), None)
            if jumeau is not None:
                # on ne recopie pas : la section renvoie au constat deja formule,
                # dont la reference de page s enrichit
                jumeau.pages = sorted(set(jumeau.pages) | set(pages))
                claims = [jumeau]
            else:
                claim = Claim(text=texts[best].strip(), pages=pages,
                              score=float(scores[best]), chunk_id=ch.cid)
                global_claims.append((toks, claim))
                claims = [claim]

        claims.sort(key=lambda c: (c.pages[0] if c.pages else 0))

        kw = cluster_kw.get(group[0].cluster, []) if cluster_kw else []
        if not kw:
            kw = [k for k, _ in ml.keyphrases([" ".join(texts)], top=6, lang=lang)]
        section = SectionSummary(
            title=_section_title(group, kw),
            page_start=group[0].page_start,
            page_end=group[-1].page_end,
            claims=claims,
            keywords=kw[:8],
        )
        tree.sections.append(section)
        reserves.append((section, reserve, texts, sents))

    # --- 5 bis. rattrapage si la synthese est loin sous la cible ------
    if budget is not None and reserves:
        ajoutes = _completer(tree, budget, reserves, global_claims, pidx)
        if ajoutes:
            step(0.88, f"rattrapage : {ajoutes} constats ajoutes")

    # --- 6. resume executif ------------------------------------------
    step(0.90, "resume executif")
    pool = [c for s in tree.sections for c in s.claims]
    if pool:
        texts = [c.text for c in pool]
        ranked = ml.textrank(texts, lang, top=min(cfg["exec"], len(texts)))
        picked = [pool[i] for i, _ in ranked] if ranked else pool[: cfg["exec"]]
        picked.sort(key=lambda c: (c.pages[0] if c.pages else 0))
        tree.executive = picked

    # --- 7. entites et statistiques ----------------------------------
    step(0.96, "entites et indicateurs")
    tree.entities = ml.extract_entities(doc.full_text()[:400000])
    secteurs = lexicons.detecter_secteurs(doc.full_text()[:300000])
    tree.stats = {
        "pages": doc.n_pages,
        "mots": doc.n_words,
        "blocs": len(chunks),
        "sections": len(tree.sections),
        "pages_resumees": sum(1 for v in tree.page_digests.values() if v),
        "profondeur": depth,
        "modele_supervise": ranker.trained,
        "echantillon_entrainement": ranker.n_train,
        "secteurs_detectes": [{"secteur": s, "termes": n, "exemples": ex}
                              for s, n, ex in secteurs],
        "lisibilite": ml.readability(doc.full_text()[:120000]),
    }
    if budget is not None:
        # le budget porte sur le livrable lu par l utilisateur (la restitution),
        # pas sur les digests de page qui sont un artefact interne de tracabilite
        tree.stats["budget"] = budget.to_dict()
        tree.stats["mots_constats"] = sum(
            utils.word_count(c.text) for c in {id(c): c for c in tree.all_claims}.values())
        tree.stats["mots_digests"] = sum(
            utils.word_count(v) for v in tree.page_digests.values())

    # --- 8. reformulation abstractive optionnelle --------------------
    if use_llm and llm.available():
        step(0.98, "reformulation abstractive")
        tree.stats["llm"] = llm.polish_summary(tree, lang=lang)

    step(1.0, "synthese terminee")
    return tree


# --------------------------------------------------------------- resumes courts
def quick_abstract(tree: SummaryTree, max_words: int = 160) -> str:
    """Paragraphe d accroche a partir du resume executif."""
    out, n = [], 0
    for c in tree.executive:
        w = utils.word_count(c.text)
        if n + w > max_words and out:
            break
        out.append(c.text.rstrip(" ."))
        n += w
    return ". ".join(out) + ("." if out else "")


def bullet_points(tree: SummaryTree, n: int = 8, with_refs: bool = True) -> list[str]:
    out = []
    for c in tree.executive[:n]:
        txt = utils.truncate(c.text, 260)
        out.append(f"{txt} ({c.ref})" if with_refs and c.ref else txt)
    return out
