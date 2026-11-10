"""SYNTHEA - Agent VIGIE : recherche ciblee, base locale d abord.

Principe : la plateforme ne depend jamais d internet pour fonctionner.
  1. VIGIE interroge d abord la base locale (57 CSV : definitions metier,
     sigles, pays et institutions, sources de reference).
  2. Si le reseau est disponible, il complete par une recherche *ciblee* :
     les requetes sont restreintes aux domaines officiels listes dans
     data/lexicons/58_sources_veille.csv (site:legifrance.gouv.fr, etc.).
  3. Si le reseau est absent ou bloque, il le dit et rend la main a la base
     locale, sans jamais inventer de resultat.
"""
from __future__ import annotations

import html
import re
import time
import urllib.parse

from . import lexicons, utils

_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_PROBE_CACHE: dict[str, tuple[float, bool]] = {}
_PROBE_TTL = 120.0


# -------------------------------------------------------------- disponibilite
def online_available(timeout: float = 4.0) -> bool:
    now = time.time()
    hit = _PROBE_CACHE.get("net")
    if hit and now - hit[0] < _PROBE_TTL:
        return hit[1]
    ok = False
    if utils.has_module("requests"):
        try:
            import requests
            r = requests.get("https://duckduckgo.com/", timeout=timeout,
                             headers={"User-Agent": _UA})
            ok = r.status_code < 400
        except Exception:
            ok = False
    _PROBE_CACHE["net"] = (now, ok)
    return ok


def status() -> dict:
    return {
        "reseau": online_available(),
        "sources_locales": len(lexicons.sources_veille()),
        "termes_locaux": len(lexicons.lexique_sectoriel()),
        "pays_references": len(lexicons.pays()),
        "mode": "hybride" if online_available() else "hors ligne (base CSV)",
    }


# ----------------------------------------------------------- base locale
def local_knowledge(query: str, limit: int = 12) -> dict:
    """Ce que SYNTHEA sait deja, sans reseau."""
    q = (query or "").strip()
    termes = lexicons.chercher_terme(q, limit=limit)
    metiers = lexicons.chercher_metier(q, limit=8)
    sig = [s for s in lexicons.sigles()
           if utils.normalize(q) and (
               utils.normalize(q) in utils.normalize(s["sigle"])
               or utils.normalize(q) in utils.normalize(s["signification"]))][:8]
    pays = [p for p in lexicons.pays()
            if utils.normalize(q) and utils.normalize(q) in utils.normalize(p["pays"])][:6]
    return {
        "termes": termes,
        "metiers": metiers,
        "sigles": sig,
        "pays": pays,
        "sources_recommandees": lexicons.sources_pour(q or "reglementation"),
        "n_total": len(termes) + len(metiers) + len(sig) + len(pays),
    }


# ------------------------------------------------------------ recherche web
_RES = re.compile(
    r'<a[^>]*class="result__a"[^>]*href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>'
    r'.*?(?:class="result__snippet"[^>]*>(?P<snip>.*?)</a>)?',
    re.S | re.I)


def _clean(frag: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", frag or "")).strip()


def _ddg_url(href: str) -> str:
    if href.startswith("//duckduckgo.com/l/") or "uddg=" in href:
        q = urllib.parse.urlparse(href if href.startswith("http") else "https:" + href)
        params = urllib.parse.parse_qs(q.query)
        if "uddg" in params:
            return urllib.parse.unquote(params["uddg"][0])
    return href if href.startswith("http") else "https:" + href


def search_web(query: str, sites: list[str] | None = None,
               max_results: int = 8, timeout: float = 12.0) -> dict:
    """Recherche ciblee. Retourne {statut, resultats, requete, note}."""
    if not utils.has_module("requests"):
        return {"statut": "indisponible", "resultats": [], "requete": query,
                "note": "module requests absent"}
    q = query.strip()
    if sites:
        q += " (" + " OR ".join(f"site:{s}" for s in sites[:6]) + ")"
    try:
        import requests
        r = requests.post(
            "https://html.duckduckgo.com/html/",
            data={"q": q, "kl": "fr-fr"},
            headers={"User-Agent": _UA, "Accept-Language": "fr,en;q=0.8"},
            timeout=timeout,
        )
        if r.status_code >= 400:
            return {"statut": "erreur", "resultats": [], "requete": q,
                    "note": f"reponse HTTP {r.status_code}"}
        out = []
        for m in _RES.finditer(r.text):
            url = _ddg_url(m.group("url") or "")
            title = _clean(m.group("title"))
            snip = _clean(m.group("snip") or "")
            if not url or not title:
                continue
            out.append({"titre": title, "url": url, "extrait": snip,
                        "domaine": urllib.parse.urlparse(url).netloc})
            if len(out) >= max_results:
                break
        return {"statut": "ok" if out else "vide", "resultats": out,
                "requete": q, "note": "" if out else "aucun resultat"}
    except Exception as exc:
        return {"statut": "hors ligne", "resultats": [], "requete": q,
                "note": f"reseau inaccessible ({exc.__class__.__name__}) : "
                        f"la base locale CSV reste utilisable"}


def targeted_search(keywords: list[str], thematique: str = "",
                    official_only: bool = True, max_results: int = 8) -> dict:
    """Construit une requete a partir des mots-cles du document."""
    kws = [k for k in keywords if k][:5]
    query = " ".join(f'"{k}"' if " " in k else k for k in kws)
    if thematique:
        query = f"{query} {thematique}".strip()
    srcs = lexicons.sources_pour(thematique or " ".join(kws))
    if official_only:
        srcs = [s for s in srcs if s.get("fiabilite") == "officielle"] or srcs
    sites = [s["domaine"] for s in srcs]

    local = local_knowledge(" ".join(kws))
    if not online_available():
        return {"mode": "hors ligne", "web": {"statut": "hors ligne", "resultats": [],
                                              "requete": query,
                                              "note": "reseau indisponible"},
                "local": local, "sites_cibles": sites, "requete": query}
    web = search_web(query, sites, max_results=max_results)
    return {"mode": "hybride", "web": web, "local": local,
            "sites_cibles": sites, "requete": query}


def fetch_page(url: str, timeout: float = 15.0, max_chars: int = 20000) -> dict:
    """Recupere le texte d une page pour confrontation avec le document."""
    if not utils.has_module("requests"):
        return {"statut": "indisponible", "texte": "", "url": url}
    try:
        import requests
        r = requests.get(url, timeout=timeout, headers={"User-Agent": _UA})
        if r.status_code >= 400:
            return {"statut": f"HTTP {r.status_code}", "texte": "", "url": url}
        raw = r.content
        from .extraction import _from_html
        pages = _from_html(raw)
        txt = "\n\n".join(p.get("text", "") for p in pages)[:max_chars]
        return {"statut": "ok", "texte": txt, "url": url,
                "mots": utils.word_count(txt)}
    except Exception as exc:
        return {"statut": f"echec ({exc.__class__.__name__})", "texte": "", "url": url}


# --------------------------------------------------------- corpus local
def add_to_corpus(name: str, text: str) -> str:
    """Archive un contenu dans data/corpora pour consultation hors ligne."""
    import os
    os.makedirs(utils.CORPORA, exist_ok=True)
    path = os.path.join(utils.CORPORA, f"{utils.slugify(name)}-{utils.stamp()}.txt")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


def search_corpus(query: str, limit: int = 8) -> list[dict]:
    """Recherche plein texte dans les contenus archives localement."""
    import os
    if not os.path.isdir(utils.CORPORA):
        return []
    qn = utils.normalize(query)
    out = []
    for f in sorted(os.listdir(utils.CORPORA)):
        if not f.endswith(".txt"):
            continue
        try:
            with open(os.path.join(utils.CORPORA, f), encoding="utf-8") as fh:
                body = fh.read()
        except Exception:
            continue
        bn = utils.normalize(body)
        if qn and qn in bn:
            pos = bn.find(qn)
            out.append({"fichier": f, "extrait": utils.truncate(body[max(0, pos - 200):pos + 400], 500)})
        if len(out) >= limit:
            break
    return out
