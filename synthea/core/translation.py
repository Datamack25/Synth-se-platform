"""SYNTHEA - Agent BABEL : traduction en cinq langues.

Trois moteurs, du plus autonome au plus precis :

  1. glossaire  (toujours disponible, 100 % hors ligne)
     Traduction des titres, rubriques, connecteurs et termes metier a partir des
     CSV multilingues. Le taux de couverture est mesure et affiche : c est une
     traduction assistee, honnete sur ses limites, pas une traduction neuronale.

  2. deep_translator  (si le module est installe et le reseau accessible)
     Traduction automatique phrase par phrase, glossaire applique en post-edition.

  3. llm  (si ANTHROPIC_API_KEY est configuree)
     Traduction contextuelle avec glossaire impose et conservation des references.

Langues : francais, anglais, espagnol, portugais, creole haitien.
"""
from __future__ import annotations

import copy
import re

from . import lexicons, llm, utils
from .models import Rendition

ENGINES = {
    "glossaire": "Glossaire hors ligne (57 CSV)",
    "deep_translator": "Traduction automatique en ligne",
    "llm": "Modele de langue (abstractif)",
}

_TOKEN = re.compile(r"(\W+)", re.UNICODE)
_DT_CODES = {"fr": "fr", "en": "en", "es": "es", "pt": "pt", "ht": "ht"}


# ------------------------------------------------------------ disponibilite
def engine_status() -> dict[str, dict]:
    dt = utils.has_module("deep_translator")
    from . import websearch
    reseau = websearch.online_available()
    st_llm = llm.status()

    if dt and reseau:
        detail_dt = "module installe, reseau accessible"
    elif dt:
        detail_dt = ("module installe, mais aucun reseau detecte : BABEL bascule "
                     "sur le glossaire hors ligne")
    else:
        detail_dt = ("paquet absent de l environnement — il figure pourtant dans "
                     "requirements.txt : relance l installation des dependances")

    if st_llm["actif"]:
        detail_llm = f"cle API presente, modele {st_llm['modele']}"
    elif st_llm["module_anthropic"]:
        detail_llm = ("paquet installe, mais aucune cle : ajoute ANTHROPIC_API_KEY "
                      "dans .streamlit/secrets.toml")
    else:
        detail_llm = ("paquet absent — il figure dans requirements.txt : "
                      "relance l installation des dependances")

    return {
        "glossaire": {"disponible": True,
                      "detail": f"{len(lexicons.multilingue())} entrees pivots + "
                                f"{len(lexicons.lexique_sectoriel())} termes metier, "
                                f"sans reseau ni cle"},
        "deep_translator": {"disponible": dt and reseau, "detail": detail_dt},
        "llm": {"disponible": st_llm["actif"], "detail": detail_llm},
    }


def best_engine() -> str:
    st = engine_status()
    if st["llm"]["disponible"]:
        return "llm"
    if st["deep_translator"]["disponible"]:
        return "deep_translator"
    return "glossaire"


# --------------------------------------------------------- moteur glossaire
def _glossary_sentence(text: str, gloss: dict[str, str],
                       sw: frozenset[str]) -> tuple[str, int, int]:
    """Substitution terme a terme, expressions longues d abord."""
    parts = _TOKEN.split(text)
    words_idx = [i for i, p in enumerate(parts) if p and not _TOKEN.fullmatch(p)]
    out = list(parts)
    done = [False] * len(parts)
    translated = content = 0

    for span in (4, 3, 2, 1):
        for k in range(len(words_idx) - span + 1):
            idxs = words_idx[k:k + span]
            if any(done[i] for i in idxs):
                continue
            if idxs[-1] - idxs[0] > span * 2:        # mots non contigus
                continue
            phrase = "".join(parts[idxs[0]:idxs[-1] + 1])
            hit = gloss.get(utils.normalize(phrase))
            if not hit:
                continue
            out[idxs[0]] = _match_case(phrase, hit)
            for i in idxs[1:]:
                out[i] = ""
            for i in range(idxs[0] + 1, idxs[-1] + 1):
                if _TOKEN.fullmatch(parts[i] or ""):
                    out[i] = ""
            for i in idxs:
                done[i] = True
            translated += span

    for i in words_idx:
        w = parts[i]
        if len(w) > 3 and w.lower() not in sw:
            content += 1
    return re.sub(r"\s{2,}", " ", "".join(out)).strip(), translated, max(content, 1)


def _match_case(src: str, dst: str) -> str:
    if src.isupper() and len(src) > 3:
        return dst.upper()
    if src[:1].isupper():
        return dst[:1].upper() + dst[1:]
    return dst


def translate_text(text: str, target: str, source: str = "fr",
                   engine: str = "glossaire") -> dict:
    """Retourne {texte, moteur, couverture, note}."""
    if not text or target == source:
        return {"texte": text, "moteur": "aucun", "couverture": 1.0, "note": ""}

    if engine == "llm" and llm.available():
        gl = _glossary_prompt(target, source)
        out = llm.translate(text, lexicons.LANG_LABELS.get(target, target), gl)
        if out and not out.startswith("[llm"):
            return {"texte": out, "moteur": "llm", "couverture": 1.0,
                    "note": "traduction par modele de langue, glossaire impose"}

    if engine == "deep_translator" and utils.has_module("deep_translator"):
        try:
            from deep_translator import GoogleTranslator
            tr = GoogleTranslator(source=_DT_CODES.get(source, "auto"),
                                  target=_DT_CODES.get(target, target))
            chunks = _split_for_api(text, 4500)
            out = " ".join(tr.translate(c) or "" for c in chunks)
            if out.strip():
                gloss = lexicons.glossaire(source, target)
                return {"texte": out, "moteur": "deep_translator", "couverture": 1.0,
                        "note": f"traduction automatique, {len(gloss)} termes metier "
                                f"disponibles en post-edition"}
        except Exception as exc:
            return _glossary_only(text, target, source,
                                  f"reseau indisponible ({exc.__class__.__name__}), "
                                  f"repli sur le glossaire")

    return _glossary_only(text, target, source)


def _glossary_only(text: str, target: str, source: str, note: str = "") -> dict:
    gloss = lexicons.glossaire(source, target)
    sw = lexicons.stopwords(source)
    done = tot = 0
    out_lines = []
    for line in text.split("\n"):
        if not line.strip():
            out_lines.append(line)
            continue
        keep_prefix = re.match(r"^(\s*(?:#{1,6}\s*|[-*]\s+|\d+\.\s+)?)", line).group(1)
        body = line[len(keep_prefix):]
        tr, d, t = _glossary_sentence(body, gloss, sw)
        done += d
        tot += t
        out_lines.append(keep_prefix + tr)
    cov = min(1.0, utils.safe_div(done, tot))
    return {
        "texte": "\n".join(out_lines),
        "moteur": "glossaire",
        "couverture": round(cov, 3),
        "note": note or (f"traduction assistee par glossaire : {int(cov * 100)} % "
                         f"des termes porteurs convertis, le reste conserve en "
                         f"{lexicons.LANG_LABELS.get(source, source)}"),
    }


def _split_for_api(text: str, size: int) -> list[str]:
    out, cur = [], ""
    for para in text.split("\n"):
        if len(cur) + len(para) + 1 > size:
            out.append(cur)
            cur = para
        else:
            cur = f"{cur}\n{para}" if cur else para
    if cur:
        out.append(cur)
    return out


def _glossary_prompt(target: str, source: str = "fr", limit: int = 70) -> str:
    gl = lexicons.glossaire(source, target)
    items = list(gl.items())[:limit]
    return "\n".join(f"- {s} = {d}" for s, d in items)


# ------------------------------------------------------- traduction de rendu
def translate_rendition(rend: Rendition, target: str,
                        engine: str | None = None) -> Rendition:
    """Traduit une restitution complete en conservant sa structure."""
    engine = engine or best_engine()
    src = rend.language
    out = copy.deepcopy(rend)
    out.language = target

    covs: list[float] = []
    notes: set[str] = set()
    used: set[str] = set()

    def tr(txt: str) -> str:
        if not txt or not txt.strip():
            return txt
        r = translate_text(txt, target, src, engine)
        covs.append(r["couverture"])
        used.add(r["moteur"])
        if r["note"]:
            notes.add(r["note"])
        return r["texte"]

    out.title = tr(rend.title)
    for s in out.sections:
        s["heading"] = tr(s["heading"])
        s["paragraphs"] = [tr(p) for p in s.get("paragraphs", [])]
        s["bullets"] = [tr(b) for b in s.get("bullets", [])]
        # les references de page restent lisibles telles quelles
    used.discard("aucun")
    effectif = ("+".join(sorted(used)) if used else "aucun")
    out.meta = dict(rend.meta)
    out.meta.update({
        "traduction_moteur": effectif,          # moteur reellement utilise
        "traduction_moteur_demande": engine,
        "traduction_repli": effectif != engine,
        "traduction_langue_source": src,
        "traduction_couverture": round(sum(covs) / len(covs), 3) if covs else 0.0,
        "traduction_notes": " | ".join(sorted(notes)),
    })
    return out


def translate_claims(claims, target: str, source: str = "fr",
                     engine: str | None = None) -> list[dict]:
    engine = engine or best_engine()
    out = []
    for c in claims:
        r = translate_text(c.text, target, source, engine)
        out.append({"source": c.text, "traduction": r["texte"], "ref": c.ref,
                    "moteur": r["moteur"], "couverture": r["couverture"]})
    return out


# ------------------------------------------------------------ glossaire doc
def document_glossary(text: str, target: str, limit: int = 60) -> list[dict]:
    """Glossaire cible : termes metier presents dans le document, en 5 langues."""
    rows = lexicons.jargon_present(text, limit=limit)
    out = []
    for r in rows:
        out.append({
            "terme (fr)": r.get("terme_fr", ""),
            "registre": r.get("registre", ""),
            "definition": r.get("definition_fr", ""),
            "en": r.get("en", ""), "es": r.get("es", ""),
            "pt": r.get("pt", ""), "ht": r.get("ht", ""),
            "secteur": r.get("secteur", ""),
            "cible": r.get(target, "") if target in ("en", "es", "pt", "ht")
                     else r.get("terme_fr", ""),
        })
    return out
