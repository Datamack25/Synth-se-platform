"""SYNTHEA - Agent BOUSSOLE : segmentation et cartographie du document."""
from __future__ import annotations

import re

from . import utils
from .models import Chunk, Document

HEADING = re.compile(
    r"^(?:###\s*(?P<h1>.{3,120})|"
    r"(?P<num>(?:chapitre|chapter|partie|titre|section|annexe|capitulo)\s+[0-9IVXLC]+[\.\)\s:-]*.{0,110})|"
    r"(?P<caps>[A-ZÀ-Þ][A-ZÀ-Þ0-9 ,'’\-/()]{8,90})|"
    r"(?P<dec>\d{1,2}(?:\.\d{1,2}){0,3}[\.\)]\s+.{3,110}))$",
    re.MULTILINE | re.IGNORECASE,
)


def detect_outline(doc: Document, limit: int = 400) -> list[dict]:
    """Repere les titres apparents du corpus avec leur page."""
    out: list[dict] = []
    for p in doc.pages:
        for line in (p.text or "").split("\n"):
            s = line.strip()
            if not (6 <= len(s) <= 130):
                continue
            m = HEADING.match(s)
            if not m:
                continue
            label = next((v for v in m.groupdict().values() if v), s)
            label = re.sub(r"\s+", " ", label).strip(" .:-")
            if len(label) < 4:
                continue
            level = 1 if (m.group("h1") or m.group("num")) else 2
            out.append({"titre": label, "page": p.index, "niveau": level})
            if len(out) >= limit:
                return out
    return out


def make_chunks(doc: Document, target_words: int = 900,
                overlap_sentences: int = 2) -> list[Chunk]:
    """Decoupe le corpus en blocs page-aware exploitables par les agents.

    Un bloc ne traverse jamais la frontiere d un fichier et conserve toujours
    l intervalle de pages d origine. Le recouvrement entre blocs consecutifs
    reprend les dernieres phrases *a l identique* (jamais une reconstruction a
    partir de tokens) : c est ce qui permet a ARGUS de verifier que chaque
    constat existe litteralement dans le document source.
    """
    chunks: list[Chunk] = []
    cid = 0
    cur_pages: list[int] = []
    cur_text: list[str] = []
    cur_words = 0
    cur_file = None
    tail = ""

    def flush() -> None:
        nonlocal cid, cur_pages, cur_text, cur_words, tail
        if not cur_pages or not cur_words:
            cur_pages, cur_text, cur_words = [], [], 0
            return
        cid += 1
        core = "\n\n".join(cur_text)
        body = utils.clean_text((tail + "\n\n" + core) if tail else core)
        chunks.append(Chunk(cid=cid, page_start=min(cur_pages),
                            page_end=max(cur_pages), text=body))
        # recouvrement : les dernieres phrases, verbatim
        tail = ""
        if overlap_sentences:
            keep: list[str] = []
            for s in reversed(utils.split_sentences(core, min_len=30)):
                if len(keep) >= overlap_sentences or sum(map(len, keep)) > 600:
                    break
                keep.insert(0, s)
            tail = " ".join(keep)
        cur_pages, cur_text, cur_words = [], [], 0

    for p in doc.pages:
        if cur_file is not None and p.source_file != cur_file:
            flush()
            tail = ""
        cur_file = p.source_file
        if p.is_empty:
            # page vide : on la rattache quand meme pour la tracabilite
            if cur_pages:
                cur_pages.append(p.index)
            else:
                cur_pages = [p.index]
                cur_text, cur_words = [], 0
            continue
        cur_pages.append(p.index)
        cur_text.append(p.text)
        cur_words += p.word_count
        if cur_words >= target_words:
            flush()

    flush()

    # titrage des blocs a partir de l ossature detectee
    outline = detect_outline(doc)
    for ch in chunks:
        cands = [o["titre"] for o in outline
                 if ch.page_start <= o["page"] <= ch.page_end]
        ch.title = (cands[0] if cands
                    else utils.truncate(ch.text.split("\n")[0], 70) or f"Bloc {ch.cid}")
    return chunks


def coverage_map(doc: Document, chunks: list[Chunk]) -> dict[int, list[int]]:
    """page -> liste des blocs qui la couvrent (utilise par ARGUS)."""
    cov: dict[int, list[int]] = {p.index: [] for p in doc.pages}
    for ch in chunks:
        for pg in ch.pages:
            if pg in cov:
                cov[pg].append(ch.cid)
    return cov


def structure_stats(doc: Document, chunks: list[Chunk]) -> dict:
    sizes = [c.word_count for c in chunks] or [0]
    return {
        "n_blocs": len(chunks),
        "mots_par_bloc_moyen": round(sum(sizes) / len(sizes), 1),
        "bloc_min": min(sizes),
        "bloc_max": max(sizes),
        "titres_detectes": len(detect_outline(doc)),
        "pages_vides": len(doc.empty_pages),
        "pages_ocr": len(doc.ocr_pages),
    }
