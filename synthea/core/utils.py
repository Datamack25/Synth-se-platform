"""SYNTHEA - utilitaires transversaux."""
from __future__ import annotations

import hashlib
import os
import re
import unicodedata
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
LEXICONS = os.path.join(DATA, "lexicons")
CORPORA = os.path.join(DATA, "corpora")
EXPORTS = os.path.join(ROOT, "exports")
ASSETS = os.path.join(ROOT, "assets")

for _d in (EXPORTS, CORPORA):
    os.makedirs(_d, exist_ok=True)


# --------------------------------------------------------------- texte
_WS = re.compile(r"[ \t ]+")
_NL = re.compile(r"\n{3,}")
_SENT = re.compile(
    r"(?<=[.!?…])\s+(?=[\"'(\[«]?#{0,6}\s*[A-ZÀ-ÖØ-Þ0-9])")
_WORD = re.compile(r"[0-9A-Za-zÀ-ÖØ-öø-ÿ'’\-]+")
_ABBR = re.compile(
    r"(?<![0-9A-Za-zÀ-ÖØ-öø-ÿ])"
    r"(M|MM|Mme|Mlle|Dr|Pr|Me|art|al|cf|etc|p|pp|ex|fig|ed|éd|vol|chap|No|no|"
    r"Inc|Ltd|St|Ste|av|J\.-C|réf|ref|tel|tél|env)\.",
    re.UNICODE)


# lignes qui sont des titres : elles doivent etre closes par un point, sinon le
# titre se colle a la premiere phrase du paragraphe suivant
_HEAD_KW = re.compile(
    r"^(?:#{1,6}\s*)?(?:chapitre|chapter|partie|section|annexe|titre|article|"
    r"capitulo|parte|livre|tome|introduction|conclusion|sommaire|preambule)"
    r"\b[^.!?]{0,90}$", re.I)
_HEAD_NUM = re.compile(r"^\d{1,2}(?:\.\d{1,2}){0,3}[\).]?\s+[^.!?]{3,80}$")
_HEAD_CAPS = re.compile(r"^[A-ZÀ-Þ0-9][A-ZÀ-Þ0-9 ,'’\-/()]{7,80}$")


def close_headings(txt: str) -> str:
    """Ajoute un point final aux lignes de titre.

    Ne touche qu aux lignes reconnues comme titres (mot-cle d ossature,
    numerotation, ligne capitalisee) : une ligne de paragraphe coupee par la
    mise en page n est jamais modifiee. Le point ajoute est ignore par
    normalize(), donc les controles de fidelite d ARGUS restent valides.
    """
    lines = txt.split("\n")
    out = []
    for i, raw in enumerate(lines):
        s = raw.rstrip()
        nxt = lines[i + 1].lstrip() if i + 1 < len(lines) else ""
        marked = s.startswith("#")          # titre balise a l extraction
        looks_like_head = bool(
            (nxt[:1].isupper() or nxt[:1].isdigit())
            and (_HEAD_KW.match(s) or _HEAD_NUM.match(s) or _HEAD_CAPS.match(s)))
        if (s and "|" not in s and not s.startswith("[")
                and not s.endswith((".", "!", "?", ":", ";", ",", "…", "-"))
                and (marked or looks_like_head)):
            s += "."
        out.append(s)
    return "\n".join(out)


def clean_text(txt: str) -> str:
    """Normalise les espaces sans detruire la structure en paragraphes."""
    if not txt:
        return ""
    txt = txt.replace("\r\n", "\n").replace("\r", "\n")
    txt = txt.replace("­", "")               # cesure invisible
    txt = re.sub(r"(\w)-\n(\w)", r"\1\2", txt)    # mot coupe en fin de ligne
    txt = _WS.sub(" ", txt)
    txt = _NL.sub("\n\n", txt)
    txt = close_headings(txt)
    return txt.strip()


def split_sentences(txt: str, min_len: int = 25) -> list[str]:
    """Decoupage en phrases, robuste aux abreviations courantes."""
    if not txt:
        return []
    # protection des abreviations : uniquement sur un mot entier, sinon
    # « capital. » serait ampute de son point par l abreviation « al. »
    protected = _ABBR.sub(lambda m: m.group(1) + "\u0001", txt)
    parts = _SENT.split(protected)
    out = []
    for p in parts:
        p = p.replace("\u0001", ".").strip()
        if len(p) >= min_len:
            out.append(p)
            continue
        if not p:
            continue
        # un titre isole n est pas un constat : il est deja dans l ossature
        bare = p.rstrip(".")
        if (bare.startswith("#") or _HEAD_KW.match(bare) or _HEAD_NUM.match(bare)
                or _HEAD_CAPS.match(bare)):
            continue
        if out:
            out[-1] = out[-1] + " " + p
    return out


def words(txt: str) -> list[str]:
    return _WORD.findall(txt or "")


def word_count(txt: str) -> int:
    return len(words(txt))


def strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def normalize(s: str) -> str:
    """Forme canonique pour comparaison : minuscules, sans accents ni
    ponctuation, espaces normalises. Deux textes qui ne different que par la
    mise en forme deviennent identiques, ce qui rend les controles de fidelite
    d ARGUS robustes aux sauts de ligne et aux separateurs de tableau."""
    s = re.sub(r"[^a-z0-9 ]+", " ", strip_accents((s or "").lower()))
    return re.sub(r"\s+", " ", s).strip()


TABLE_MARKS = ("[feuille", "[tableau", "[donnees tabulaires")


def is_tabular(txt: str) -> bool:
    """Detecte un bloc de donnees tabulaires plutot qu un texte redige."""
    t = (txt or "").lstrip().lower()
    return t.startswith(TABLE_MARKS) or txt.count("|") >= 3


def tabular_digest(txt: str, max_rows: int = 2) -> str:
    """Resume d un bloc tabulaire : entete et premiere ligne, verbatim."""
    lines = [ln.strip() for ln in (txt or "").split("\n") if ln.strip()]
    lines = [ln for ln in lines if not ln.lower().startswith(TABLE_MARKS)]
    return truncate(" / ".join(lines[:max_rows]), 300)


def sha1(txt: str) -> str:
    return hashlib.sha1((txt or "").encode("utf-8", "replace")).hexdigest()


def short_sha(txt: str, n: int = 10) -> str:
    return sha1(txt)[:n]


def truncate(txt: str, n: int) -> str:
    txt = (txt or "").strip()
    return txt if len(txt) <= n else txt[: n - 1].rsplit(" ", 1)[0] + "…"


def slugify(s: str, maxlen: int = 60) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", strip_accents((s or "").lower())).strip("-")
    return (s or "document")[:maxlen]


def human_int(n: int | float) -> str:
    try:
        return f"{int(n):,}".replace(",", " ")
    except Exception:
        return str(n)


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def now_fr() -> str:
    return datetime.now().strftime("%d/%m/%Y a %H:%M")


# ------------------------------------------------------- numeros de page
def page_ref(pages: list[int]) -> str:
    """Formate une liste de pages : [3,4,5,9] -> 'p. 3-5, 9'."""
    if not pages:
        return ""
    pages = sorted(set(int(p) for p in pages))
    runs, start, prev = [], pages[0], pages[0]
    for p in pages[1:]:
        if p == prev + 1:
            prev = p
            continue
        runs.append((start, prev))
        start = prev = p
    runs.append((start, prev))
    parts = [f"{a}" if a == b else (f"{a}-{b}" if b > a + 1 else f"{a}, {b}")
             for a, b in runs]
    return "p. " + ", ".join(parts)


# --------------------------------------------------------------- divers
def chunked(seq, size: int):
    for i in range(0, len(seq), size):
        yield seq[i:i + size]


def safe_div(a: float, b: float, default: float = 0.0) -> float:
    try:
        return a / b if b else default
    except Exception:
        return default


def has_module(name: str) -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False
