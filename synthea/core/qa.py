"""SYNTHEA - Agent ECHO : dialogue avec le document.

Recherche hybride entierement hors ligne :
  - BM25 (implementation maison, aucune dependance)
  - similarite cosinus TF-IDF (scikit-learn)
  - fusion des deux classements, puis selection des phrases repondantes

Chaque reponse cite ses pages. Si un modele de langue est configure, ECHO peut
rediger la reponse a partir des memes extraits, sans jamais sortir du document.
"""
from __future__ import annotations

import math
import re

import numpy as np

from . import lexicons, llm, ml, utils
from .models import Chunk, Document, SummaryTree

_K1, _B = 1.5, 0.75


class Retriever:
    """Index BM25 + TF-IDF sur les blocs du document."""

    def __init__(self, chunks: list[Chunk], lang: str = "fr") -> None:
        self.chunks = chunks
        self.lang = lang
        self.sw = lexicons.stopwords_all()
        self.docs: list[list[str]] = [self._tok(c.text) for c in chunks]
        self.len = np.array([len(d) or 1 for d in self.docs], dtype=float)
        self.avg = float(self.len.mean()) if len(self.len) else 1.0
        self.df: dict[str, int] = {}
        for d in self.docs:
            for t in set(d):
                self.df[t] = self.df.get(t, 0) + 1
        self.N = max(len(self.docs), 1)
        self.tf: list[dict[str, int]] = []
        for d in self.docs:
            m: dict[str, int] = {}
            for t in d:
                m[t] = m.get(t, 0) + 1
            self.tf.append(m)
        self._mat, self._vec = ml.tfidf_matrix([c.text for c in chunks], lang)

    def _tok(self, text: str) -> list[str]:
        return [w for w in utils.normalize(text).split()
                if len(w) > 2 and w not in self.sw]

    # -------------------------------------------------------------- bm25
    def bm25(self, query: str) -> np.ndarray:
        q = self._tok(query)
        scores = np.zeros(self.N)
        if not q:
            return scores
        for t in q:
            df = self.df.get(t, 0)
            if not df:
                continue
            idf = math.log(1 + (self.N - df + 0.5) / (df + 0.5))
            for i in range(self.N):
                f = self.tf[i].get(t, 0)
                if not f:
                    continue
                scores[i] += idf * (f * (_K1 + 1)) / (
                    f + _K1 * (1 - _B + _B * self.len[i] / self.avg))
        return scores

    # ------------------------------------------------------------ cosinus
    def cosine(self, query: str) -> np.ndarray:
        if self._mat is None or self._vec is None:
            return np.zeros(self.N)
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            qv = self._vec.transform([query])
            return cosine_similarity(qv, self._mat).ravel()
        except Exception:
            return np.zeros(self.N)

    # -------------------------------------------------------------- fusion
    def search(self, query: str, k: int = 6) -> list[tuple[Chunk, float, dict]]:
        b, c = self.bm25(query), self.cosine(query)
        bn = b / b.max() if b.max() > 0 else b
        cn = c / c.max() if c.max() > 0 else c
        fused = 0.6 * bn + 0.4 * cn
        order = np.argsort(-fused)[:k]
        return [(self.chunks[int(i)], float(fused[i]),
                 {"bm25": float(b[i]), "cosinus": float(c[i])})
                for i in order if fused[i] > 0]


# --------------------------------------------------------------- reponses
_QWORDS = {
    "combien": "quantite", "quel montant": "quantite", "taux": "quantite",
    "pourquoi": "cause", "comment": "methode", "qui": "acteur",
    "quand": "date", "ou": "lieu", "definition": "definition",
    "que signifie": "definition", "quelle est la these": "these",
    "resume": "synthese", "synthese": "synthese", "principaux": "synthese",
}


def question_type(q: str) -> str:
    qn = utils.normalize(q)
    for k, v in _QWORDS.items():
        if qn.startswith(k) or f" {k} " in f" {qn} ":
            return v
    return "general"


def _pick_sentences(question: str, hits: list[tuple[Chunk, float, dict]],
                    lang: str, n: int = 6) -> list[tuple[str, Chunk, float]]:
    qt = set(utils.normalize(question).split()) - set(lexicons.stopwords(lang))
    cands: list[tuple[str, Chunk, float]] = []
    for ch, w, _ in hits:
        for s in utils.split_sentences(ch.text, min_len=40):
            st = set(utils.normalize(s).split())
            inter = len(qt & st)
            if not inter:
                continue
            score = w * (inter / max(len(qt), 1)) + 0.1 * inter
            if re.search(r"\d", s) and question_type(question) == "quantite":
                score += 0.35
            cands.append((s.strip(), ch, score))
    cands.sort(key=lambda t: -t[2])
    out: list[tuple[str, Chunk, float]] = []
    seen: list[set[str]] = []
    for s, ch, sc in cands:
        toks = set(utils.normalize(s).split())
        if any(len(toks & t) / max(len(toks | t), 1) > 0.55 for t in seen):
            continue
        out.append((s, ch, sc))
        seen.append(toks)
        if len(out) >= n:
            break
    return out


def ask(question: str, doc: Document, retriever: Retriever,
        tree: SummaryTree | None = None, lang: str = "fr",
        use_llm: bool = False, k: int = 6) -> dict:
    """Retourne une reponse sourcee, avec extraits et references de page."""
    question = (question or "").strip()
    if not question:
        return {"reponse": "Pose ta question sur le document.", "extraits": [],
                "refs": "", "type": "vide", "moteur": "aucun"}

    qtype = question_type(question)

    # question de synthese : on repond avec le resume executif
    if qtype == "synthese" and tree and tree.executive:
        bullets = [f"{c.text} ({c.ref})" for c in tree.executive[:8]]
        return {
            "reponse": "D apres la synthese du document :\n\n- " + "\n- ".join(bullets),
            "extraits": [{"ref": c.ref, "texte": c.text} for c in tree.executive[:8]],
            "refs": utils.page_ref([p for c in tree.executive for p in c.pages]),
            "type": qtype, "moteur": "synthese", "scores": [],
        }

    hits = retriever.search(question, k=k)
    if not hits:
        return {
            "reponse": "Je ne trouve pas d element repondant a cette question dans "
                       "le document charge. Reformule avec des termes presents dans "
                       "le texte, ou verifie que la page concernee a bien ete extraite "
                       "(onglet Verification ARGUS).",
            "extraits": [], "refs": "", "type": qtype, "moteur": "bm25+tfidf",
            "scores": [],
        }

    picked = _pick_sentences(question, hits, lang)
    extraits = [{"ref": ch.ref, "bloc": ch.cid, "titre": ch.title,
                 "texte": utils.truncate(s, 420), "score": round(sc, 3)}
                for s, ch, sc in picked]
    if not extraits:
        extraits = [{"ref": ch.ref, "bloc": ch.cid, "titre": ch.title,
                     "texte": utils.truncate(ch.text, 420), "score": round(w, 3)}
                    for ch, w, _ in hits[:3]]

    pages = sorted({p for s, ch, _ in picked for p in ch.pages}) or \
        sorted({p for ch, _, _ in hits[:3] for p in ch.pages})
    refs = utils.page_ref(pages)

    # reponse redigee si un modele de langue est disponible
    if use_llm and llm.available():
        passages = [(e["ref"], e["texte"]) for e in extraits]
        txt = llm.answer(question, passages, lexicons.LANG_LABELS.get(lang, "francais"))
        if txt and not txt.startswith("[llm"):
            return {"reponse": txt, "extraits": extraits, "refs": refs,
                    "type": qtype, "moteur": "llm + recherche", "scores": []}

    # reponse extractive : les phrases du document, dans l ordre de pertinence
    lead = {
        "quantite": "Valeurs relevees dans le document :",
        "cause": "Elements d explication donnes par le document :",
        "methode": "Demarche decrite dans le document :",
        "acteur": "Acteurs mentionnes :",
        "date": "Reperes temporels :",
        "definition": "Definition telle qu elle figure dans le document :",
        "these": "Position defendue dans le document :",
    }.get(qtype, "Ce que dit le document :")

    body = "\n".join(f"- {e['texte']} ({e['ref']})" for e in extraits)
    return {
        "reponse": f"{lead}\n\n{body}",
        "extraits": extraits,
        "refs": refs,
        "type": qtype,
        "moteur": "bm25 + tf-idf (extractif)",
        "scores": [{"bloc": ch.cid, "score": round(w, 3), **d} for ch, w, d in hits],
    }


def suggest_questions(tree: SummaryTree, n: int = 8) -> list[str]:
    """Questions de depart construites a partir du contenu reel du document."""
    out: list[str] = []
    kws = [k for k, _ in tree.keywords[:14]]
    if tree.doc_type:
        out.append("Quelle est la these centrale du document ?")
    out.append("Resume les points principaux.")
    for k in kws[:4]:
        out.append(f"Que dit le document sur « {k} » ?")
    if tree.entities.get("montants"):
        out.append("Quels sont les montants cites et a quelles pages ?")
    if tree.entities.get("dates"):
        out.append("Quelles sont les dates cles mentionnees ?")
    for t in tree.topics[:2]:
        out.append(f"Developpe le theme « {t['libelle']} ».")
    out.append("Quelles sont les limites ou les reserves exprimees ?")
    return out[:n]
