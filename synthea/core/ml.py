"""SYNTHEA - Agent PRISME : apprentissage automatique et analyse semantique.

Tout tourne hors ligne avec scikit-learn :
  - TF-IDF + c-TF-IDF pour les mots-cles
  - TextRank (graphe de similarite + power iteration) pour l extraction
  - NMF pour la decouverte de themes
  - KMeans pour le regroupement des blocs
  - Regression logistique pour le classement supervise des phrases
  - Naive Bayes pour la typologie du document
  - Extraction d entites par regles (dates, montants, organisations, pays)
"""
from __future__ import annotations

import functools
import re

import numpy as np

from . import lexicons, utils

try:
    from sklearn.cluster import KMeans
    from sklearn.decomposition import NMF, TruncatedSVD
    from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.naive_bayes import MultinomialNB
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.pipeline import make_pipeline
    SKLEARN = True
except Exception:                                        # pragma: no cover
    SKLEARN = False


# ====================================================================
# Vectorisation et mots-cles
# ====================================================================
def _stop_list(lang: str = "fr") -> list[str]:
    sw = set(lexicons.stopwords(lang)) | set(lexicons.stopwords("en"))
    return sorted(sw)


def tfidf_matrix(texts: list[str], lang: str = "fr", max_features: int = 40000,
                 ngram: tuple[int, int] = (1, 2)):
    """Retourne (matrice, vectoriseur). Vide si sklearn absent."""
    if not SKLEARN or not texts:
        return None, None
    vec = TfidfVectorizer(
        lowercase=True, stop_words=_stop_list(lang), ngram_range=ngram,
        max_features=max_features, min_df=1, sublinear_tf=True,
        strip_accents="unicode", token_pattern=r"(?u)\b[0-9A-Za-zÀ-ÖØ-öø-ÿ'\-]{3,}\b",
    )
    try:
        return vec.fit_transform(texts), vec
    except ValueError:
        return None, None


def keyphrases(texts: list[str], top: int = 30, lang: str = "fr",
               ngram: tuple[int, int] = (1, 3)) -> list[tuple[str, float]]:
    """Mots-cles du corpus, ponderes TF-IDF et dedoublonnes."""
    mat, vec = tfidf_matrix(texts, lang, ngram=ngram)
    if mat is None:
        return _keyphrases_fallback(texts, top, lang)
    scores = np.asarray(mat.sum(axis=0)).ravel()
    names = vec.get_feature_names_out()
    order = np.argsort(-scores)
    out: list[tuple[str, float]] = []
    seen: set[str] = set()
    for i in order:
        term = names[i]
        norm = utils.normalize(term)
        if not norm or norm in seen:
            continue
        # evite "risque" si "risque de credit" deja retenu (et l inverse)
        if any(norm in s or s in norm for s in seen):
            continue
        seen.add(norm)
        out.append((term, float(scores[i])))
        if len(out) >= top:
            break
    return out


def _keyphrases_fallback(texts: list[str], top: int, lang: str) -> list[tuple[str, float]]:
    sw = lexicons.stopwords(lang)
    freq: dict[str, int] = {}
    for t in texts:
        for w in utils.words(t.lower()):
            if len(w) > 3 and w not in sw:
                freq[w] = freq.get(w, 0) + 1
    return sorted(freq.items(), key=lambda kv: -kv[1])[:top]


def class_keywords(texts: list[str], labels: list[int], top: int = 8,
                   lang: str = "fr") -> dict[int, list[str]]:
    """c-TF-IDF : mots les plus distinctifs de chaque groupe."""
    if not SKLEARN or not texts:
        return {}
    groups: dict[int, list[str]] = {}
    for t, l in zip(texts, labels):
        groups.setdefault(l, []).append(t)
    docs = {k: " ".join(v) for k, v in groups.items()}
    keys = list(docs.keys())
    cv = CountVectorizer(stop_words=_stop_list(lang), strip_accents="unicode",
                         token_pattern=r"(?u)\b[0-9A-Za-zÀ-ÖØ-öø-ÿ'\-]{4,}\b")
    try:
        counts = cv.fit_transform([docs[k] for k in keys]).toarray().astype(float)
    except ValueError:
        return {}
    names = cv.get_feature_names_out()
    tf = counts / np.maximum(counts.sum(axis=1, keepdims=True), 1)
    total = counts.sum(axis=0)
    idf = np.log(1 + (total.sum() / np.maximum(total, 1)))
    ctf = tf * idf
    return {keys[i]: [names[j] for j in np.argsort(-ctf[i])[:top]]
            for i in range(len(keys))}


# ====================================================================
# TextRank
# ====================================================================
def textrank(sentences: list[str], lang: str = "fr", top: int = 5,
             damping: float = 0.85, iters: int = 30) -> list[tuple[int, float]]:
    """Classe les phrases par centralite dans le graphe de similarite."""
    n = len(sentences)
    if n == 0:
        return []
    if n <= top:
        return [(i, 1.0) for i in range(n)]
    mat, _ = tfidf_matrix(sentences, lang, max_features=20000, ngram=(1, 2))
    if mat is None:
        return [(i, 1.0 / (i + 1)) for i in range(min(top, n))]
    sim = cosine_similarity(mat)
    np.fill_diagonal(sim, 0.0)
    rsum = sim.sum(axis=1, keepdims=True)
    rsum[rsum == 0] = 1.0
    trans = sim / rsum
    rank = np.full(n, 1.0 / n)
    for _ in range(iters):
        new = (1 - damping) / n + damping * (trans.T @ rank)
        if np.allclose(new, rank, atol=1e-7):
            rank = new
            break
        rank = new
    order = np.argsort(-rank)
    return [(int(i), float(rank[i])) for i in order[:top]]


# ====================================================================
# Themes et regroupements
# ====================================================================
def topics(texts: list[str], n_topics: int = 6, lang: str = "fr",
           n_terms: int = 9) -> list[dict]:
    """Decouverte de themes par factorisation en matrices non negatives."""
    if not SKLEARN or len(texts) < 3:
        return []
    mat, vec = tfidf_matrix(texts, lang, ngram=(1, 2))
    if mat is None:
        return []
    k = max(2, min(n_topics, mat.shape[0] - 1, 14))
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model = NMF(n_components=k, init="nndsvda", random_state=42,
                        max_iter=800, tol=5e-4, l1_ratio=0.1, alpha_W=0.0)
            W = model.fit_transform(mat)
        H = model.components_
    except Exception:
        try:
            model = TruncatedSVD(n_components=k, random_state=42)
            W = model.fit_transform(mat)
            H = np.abs(model.components_)
        except Exception:
            return []
    names = vec.get_feature_names_out()
    mass = W.sum(axis=0)
    total = mass.sum() or 1.0
    out = []
    for i in range(k):
        terms = [names[j] for j in np.argsort(-H[i])[:n_terms]]
        members = [int(d) for d in np.argsort(-W[:, i])[:8] if W[d, i] > 0]
        out.append({
            "id": i,
            "poids": round(float(mass[i] / total), 4),
            "termes": terms,
            "libelle": " / ".join(terms[:3]),
            "blocs": members,
        })
    return sorted(out, key=lambda t: -t["poids"])


def assign_topics(texts: list[str], n_topics: int = 6, lang: str = "fr") -> list[int]:
    if not SKLEARN or len(texts) < 3:
        return [-1] * len(texts)
    mat, _ = tfidf_matrix(texts, lang)
    if mat is None:
        return [-1] * len(texts)
    k = max(2, min(n_topics, mat.shape[0] - 1, 14))
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            W = NMF(n_components=k, init="nndsvda", random_state=42,
                    max_iter=600, tol=5e-4).fit_transform(mat)
        return [int(i) for i in np.argmax(W, axis=1)]
    except Exception:
        return [-1] * len(texts)


def cluster_texts(texts: list[str], k: int = 0, lang: str = "fr") -> tuple[list[int], dict]:
    """Regroupe les blocs en sections thematiques homogenes."""
    if not SKLEARN or len(texts) < 4:
        return [0] * len(texts), {}
    mat, _ = tfidf_matrix(texts, lang)
    if mat is None:
        return [0] * len(texts), {}
    if k <= 0:
        k = int(max(3, min(12, round(len(texts) ** 0.5))))
    k = min(k, mat.shape[0])
    try:
        km = KMeans(n_clusters=k, n_init=8, random_state=42)
        labels = [int(x) for x in km.fit_predict(mat)]
    except Exception:
        return [0] * len(texts), {}
    return labels, class_keywords(texts, labels, lang=lang)


# ====================================================================
# Classement supervise des phrases (ranker)
# ====================================================================_
_NUM = re.compile(r"\d")
_MONEY = re.compile(r"(?:[€$£]|\b(?:eur|usd|htg|xof|xaf|mds?|millions?|milliards?|k€|m€)\b)", re.I)


def sentence_features(sentences: list[str], lang: str = "fr",
                      keyterms: list[str] | None = None) -> np.ndarray:
    """Caracteristiques interpretables d une phrase."""
    sw = lexicons.stopwords(lang)
    kt = [utils.normalize(k) for k in (keyterms or [])][:40]
    n = max(len(sentences), 1)
    feats = []
    for i, s in enumerate(sentences):
        ws = utils.words(s.lower())
        L = len(ws) or 1
        content = [w for w in ws if w not in sw and len(w) > 3]
        sn = utils.normalize(s)
        feats.append([
            1.0 - i / n,                                        # position relative
            min(L / 40.0, 2.0),                                 # longueur
            len(content) / L,                                   # densite lexicale
            1.0 if _NUM.search(s) else 0.0,                     # presence de chiffres
            1.0 if _MONEY.search(s) else 0.0,                   # montant
            1.0 if "%" in s else 0.0,                           # pourcentage
            sum(1 for k in kt if k and k in sn) / 4.0,           # mots-cles du corpus
            1.0 if re.match(r"^(?:en conclusion|en resume|ainsi|donc|il en resulte|"
                            r"au total|en definitive)", s.strip(), re.I) else 0.0,
            1.0 if s.strip().endswith("?") else 0.0,
            len(set(content)) / L,                              # richesse
        ])
    return np.asarray(feats, dtype=float)


class SentenceRanker:
    """Regression logistique entrainee sur les etiquettes issues de TextRank.

    TextRank est precis mais couteux (matrice de similarite). On l applique a un
    echantillon du corpus pour fabriquer des etiquettes, puis le modele lineaire
    note les centaines de milliers de phrases restantes en temps constant.
    """

    def __init__(self, lang: str = "fr") -> None:
        self.lang = lang
        self.model = None
        self.trained = False
        self.n_train = 0

    def fit(self, sample_sentences: list[str], keyterms: list[str] | None = None,
            positive_ratio: float = 0.30) -> "SentenceRanker":
        if not SKLEARN or len(sample_sentences) < 24:
            return self
        ranked = textrank(sample_sentences, self.lang,
                          top=len(sample_sentences))
        if not ranked:
            return self
        n_pos = max(4, int(len(sample_sentences) * positive_ratio))
        pos = {i for i, _ in ranked[:n_pos]}
        X = sentence_features(sample_sentences, self.lang, keyterms)
        y = np.array([1 if i in pos else 0 for i in range(len(sample_sentences))])
        if y.sum() in (0, len(y)):
            return self
        try:
            self.model = make_pipeline(
                LogisticRegression(max_iter=600, C=1.2, class_weight="balanced")
            ).fit(X, y)
            self.trained = True
            self.n_train = len(sample_sentences)
        except Exception:
            self.model = None
        return self

    def score(self, sentences: list[str], keyterms: list[str] | None = None) -> np.ndarray:
        if not sentences:
            return np.zeros(0)
        X = sentence_features(sentences, self.lang, keyterms)
        if self.trained and self.model is not None:
            try:
                return self.model.predict_proba(X)[:, 1]
            except Exception:
                pass
        # repli heuristique : combinaison lineaire des caracteristiques
        w = np.array([0.22, 0.10, 0.16, 0.10, 0.08, 0.06, 0.20, 0.05, -0.04, 0.07])
        raw = X @ w
        rng = raw.max() - raw.min()
        return (raw - raw.min()) / rng if rng > 1e-9 else np.full(len(raw), 0.5)


# ====================================================================
# Typologie du document
# ====================================================================
_SEEDS: dict[str, str] = {
    "essai / ouvrage theorique":
        "chapitre these auteur these centrale argumentation concept notion philosophie "
        "critique reflexion ouvrage demonstration lecteur discours pensee essai postface",
    "rapport institutionnel":
        "rapport annuel exercice comite direction gouvernance indicateurs resultats "
        "recommandations perimetre controle interne conformite audit annexes tableau bord",
    "document reglementaire":
        "article alinea reglement directive loi decret arrete obligations sanctions "
        "autorite competente entree en vigueur dispositions transitoires considerant",
    "etude de marche":
        "marche segment concurrence part de marche croissance clients tendance "
        "enquete panel prix offre demande positionnement benchmark previsions",
    "etats financiers":
        "bilan actif passif compte de resultat produits charges amortissement "
        "provision tresorerie capitaux propres annexe exercice chiffre affaires ebitda",
    "memoire academique":
        "introduction problematique hypothese methodologie revue de litterature "
        "echantillon resultats discussion limites conclusion bibliographie annexe",
    "manuel / support de formation":
        "objectifs pedagogiques exercice chapitre notion definition exemple corrige "
        "apprenant module evaluation quiz synthese pour aller plus loin seance",
    "presentation / deck":
        "diapositive agenda contexte solution marche traction equipe roadmap "
        "demande merci questions notre vision nos chiffres cles prochaines etapes",
    "procedure interne":
        "procedure objet champ application acteurs roles etapes controle "
        "tracabilite document de reference version historique validation diffusion",
    "contrat / acte juridique":
        "entre les soussignes article objet duree obligations clause resiliation "
        "confidentialite responsabilite litige juridiction signature parties annexes",
}


@functools.lru_cache(maxsize=1)
def _doc_classifier():
    if not SKLEARN:
        return None, []
    labels = list(_SEEDS.keys())
    try:
        pipe = make_pipeline(
            TfidfVectorizer(stop_words=_stop_list("fr"), strip_accents="unicode",
                            ngram_range=(1, 2), sublinear_tf=True),
            MultinomialNB(alpha=0.25),
        ).fit([_SEEDS[k] for k in labels], labels)
        return pipe, labels
    except Exception:
        return None, labels


def classify_document(text: str, top: int = 3) -> list[tuple[str, float]]:
    """Typologie probable du document (Naive Bayes sur amorces de reference)."""
    pipe, labels = _doc_classifier()
    sample = (text or "")[:60000]
    if pipe is None or not sample.strip():
        return [("document non classe", 0.0)]
    try:
        proba = pipe.predict_proba([sample])[0]
        classes = list(pipe.classes_)
        order = np.argsort(-proba)[:top]
        return [(classes[i], round(float(proba[i]), 4)) for i in order]
    except Exception:
        return [("document non classe", 0.0)]


# ====================================================================
# Entites
# ====================================================================
RE_DATE = re.compile(
    r"\b(?:\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4}"
    r"|\d{1,2}(?:er)?\s+(?:janvier|fevrier|février|mars|avril|mai|juin|juillet|aout|août|"
    r"septembre|octobre|novembre|decembre|décembre)\s+\d{4}"
    r"|(?:19|20)\d{2})\b", re.I)
RE_MONEY = re.compile(
    r"\b\d[\d   .,]{0,15}\s?(?:€|\$|£|euros?|dollars?|millions?|milliards?|"
    r"k€|m€|mds?|HTG|XOF|XAF|USD|EUR)\b", re.I)
RE_PCT = re.compile(r"\b\d+(?:[.,]\d+)?\s?%")
RE_ACRO = re.compile(r"\b[A-Z]{2,6}(?:-[A-Z]{2,4})?\b")
RE_ORG = re.compile(
    r"\b(?:[A-ZÀ-Þ][\wÀ-ÿ'’\-]{2,}\s){0,3}"
    r"(?:S\.?A\.?S?|SARL|SASU|GmbH|Ltd|LLC|Inc|Banque|Bank|Autorite|Autorité|Agence|"
    r"Ministere|Ministère|Commission|Conseil|Institut|Fondation|Universite|Université|"
    r"Association|Federation|Fédération|Groupe|Societe|Société)\b")
RE_PROPER = re.compile(r"\b[A-ZÀ-Þ][a-zà-ÿ'’\-]{2,}(?:\s+[A-ZÀ-Þ][a-zà-ÿ'’\-]{2,}){1,3}\b")


def _top(items: list[str], n: int) -> list[str]:
    freq: dict[str, int] = {}
    for it in items:
        k = re.sub(r"\s+", " ", it).strip(" ,.;:")
        if len(k) > 2:
            freq[k] = freq.get(k, 0) + 1
    return [k for k, _ in sorted(freq.items(), key=lambda kv: (-kv[1], kv[0]))[:n]]


def extract_entities(text: str, limit: int = 25) -> dict[str, list[str]]:
    """Extraction par regles, completee par les referentiels CSV."""
    sample = (text or "")[:400000]
    sigles_connus = {s["sigle"] for s in lexicons.sigles()}
    acro = [a for a in RE_ACRO.findall(sample) if a not in {"LES", "DES", "UNE", "POUR"}]
    return {
        "dates": _top(RE_DATE.findall(sample), limit),
        "montants": _top(RE_MONEY.findall(sample), limit),
        "pourcentages": _top(RE_PCT.findall(sample), limit),
        "organisations": _top(RE_ORG.findall(sample), limit),
        "sigles_connus": _top([a for a in acro if a in sigles_connus], limit),
        "sigles_inconnus": _top([a for a in acro if a not in sigles_connus], limit),
        "noms_propres": _top(RE_PROPER.findall(sample), limit),
        "pays": [p["pays"] for p in lexicons.pays_cites(sample)][:limit],
    }


def numeric_facts(text: str) -> set[str]:
    """Faits chiffres du texte, utilises par ARGUS pour verifier la fidelite."""
    out: set[str] = set()
    for rx in (RE_MONEY, RE_PCT):
        for m in rx.findall(text or ""):
            out.add(re.sub(r"[\s  ]", "", m).lower())
    for m in re.findall(r"\b\d{2,}(?:[.,]\d+)?\b", text or ""):
        out.add(m.replace(",", "."))
    return out


def readability(text: str) -> dict:
    """Indices de lisibilite (approximation francaise de Flesch)."""
    sents = utils.split_sentences(text, min_len=10) or [text or ""]
    ws = utils.words(text)
    if not ws:
        return {"phrases": 0, "mots": 0, "mots_par_phrase": 0.0,
                "syllabes_par_mot": 0.0, "indice_lisibilite": 0.0, "niveau": "n/a"}
    syl = sum(max(1, len(re.findall(r"[aeiouyàâäéèêëîïôöùûüœ]+", w.lower()))) for w in ws)
    wps = len(ws) / len(sents)
    spw = syl / len(ws)
    score = 207 - 1.015 * wps - 73.6 * spw          # Kandel-Moles
    score = max(0.0, min(100.0, score))
    niveau = ("tres facile" if score > 80 else "facile" if score > 65 else
              "standard" if score > 50 else "difficile" if score > 35 else "tres difficile")
    return {"phrases": len(sents), "mots": len(ws), "mots_par_phrase": round(wps, 1),
            "syllabes_par_mot": round(spw, 2), "indice_lisibilite": round(score, 1),
            "niveau": niveau}
