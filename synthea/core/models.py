"""SYNTHEA - structures de donnees du pipeline."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

from . import utils


# ---------------------------------------------------------------- pages
@dataclass
class Page:
    index: int                 # numero de page, 1-based, continu sur tout le corpus
    text: str
    source_file: str
    unit: str = "page"         # page | diapositive | feuille | section | image
    native_index: int = 0      # numero dans le fichier d origine
    ocr: bool = False
    char_count: int = 0
    word_count: int = 0
    sha1: str = ""
    warning: str = ""

    def __post_init__(self) -> None:
        self.text = self.text or ""
        self.char_count = len(self.text)
        self.word_count = utils.word_count(self.text)
        self.sha1 = utils.short_sha(self.text, 12)

    @property
    def is_empty(self) -> bool:
        return self.word_count < 5

    @property
    def label(self) -> str:
        return f"{self.unit} {self.index}"


@dataclass
class Document:
    doc_id: str
    title: str
    pages: list[Page] = field(default_factory=list)
    files: list[dict] = field(default_factory=list)
    meta: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------- proprietes
    @property
    def n_pages(self) -> int:
        return len(self.pages)

    @property
    def n_words(self) -> int:
        return sum(p.word_count for p in self.pages)

    @property
    def n_chars(self) -> int:
        return sum(p.char_count for p in self.pages)

    @property
    def empty_pages(self) -> list[int]:
        return [p.index for p in self.pages if p.is_empty]

    @property
    def ocr_pages(self) -> list[int]:
        return [p.index for p in self.pages if p.ocr]

    def full_text(self, sep: str = "\n\n") -> str:
        return sep.join(p.text for p in self.pages if p.text)

    def page(self, index: int) -> Page | None:
        for p in self.pages:
            if p.index == index:
                return p
        return None

    def text_range(self, start: int, end: int) -> str:
        return "\n\n".join(p.text for p in self.pages if start <= p.index <= end)

    def to_dict(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------- chunks
@dataclass
class Chunk:
    cid: int
    page_start: int
    page_end: int
    text: str
    word_count: int = 0
    topic: int = -1
    cluster: int = -1
    title: str = ""

    def __post_init__(self) -> None:
        self.word_count = utils.word_count(self.text)

    @property
    def pages(self) -> list[int]:
        return list(range(self.page_start, self.page_end + 1))

    @property
    def ref(self) -> str:
        return utils.page_ref(self.pages)


# ------------------------------------------------------------ syntheses
@dataclass
class Claim:
    """Une phrase de synthese, rattachee a ses pages sources."""
    text: str
    pages: list[int] = field(default_factory=list)
    score: float = 0.0
    chunk_id: int = -1

    def __post_init__(self) -> None:
        # les sauts de ligne issus de la mise en page du PDF n ont pas de sens
        # dans une puce ; la normalisation ne change rien aux controles ARGUS,
        # qui comparent des formes sans ponctuation ni espaces multiples
        import re as _re
        self.text = _re.sub(r"\s+", " ", (self.text or "")).strip()

    @property
    def ref(self) -> str:
        return utils.page_ref(self.pages)


@dataclass
class SectionSummary:
    title: str
    page_start: int
    page_end: int
    claims: list[Claim] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return " ".join(c.text for c in self.claims)

    @property
    def ref(self) -> str:
        return utils.page_ref(list(range(self.page_start, self.page_end + 1)))


@dataclass
class SummaryTree:
    doc_id: str
    executive: list[Claim] = field(default_factory=list)
    sections: list[SectionSummary] = field(default_factory=list)
    page_digests: dict[int, str] = field(default_factory=dict)
    keywords: list[tuple[str, float]] = field(default_factory=list)
    topics: list[dict] = field(default_factory=list)
    entities: dict[str, list[str]] = field(default_factory=dict)
    doc_type: str = ""
    stats: dict[str, Any] = field(default_factory=dict)

    @property
    def covered_pages(self) -> set[int]:
        pages: set[int] = set(self.page_digests.keys())
        for s in self.sections:
            pages.update(range(s.page_start, s.page_end + 1))
        return pages

    @property
    def all_claims(self) -> list[Claim]:
        out = list(self.executive)
        for s in self.sections:
            out.extend(s.claims)
        return out


# --------------------------------------------------------- restitutions
@dataclass
class Rendition:
    """Synthese mise en forme pour un contexte de restitution donne."""
    context_key: str
    context_label: str
    language: str
    title: str
    sections: list[dict] = field(default_factory=list)   # {heading, paragraphs[], bullets[], ref}
    meta: dict[str, Any] = field(default_factory=dict)

    def to_markdown(self, with_refs: bool = True) -> str:
        out = [f"# {self.title}", ""]
        for s in self.sections:
            out.append(f"## {s.get('heading','')}")
            for p in s.get("paragraphs", []):
                out.append(p)
                out.append("")
            for b in s.get("bullets", []):
                out.append(f"- {b}")
            if s.get("bullets"):
                out.append("")
            if with_refs and s.get("ref"):
                out.append(f"*source : {s['ref']}*")
                out.append("")
        return "\n".join(out).strip()

    def plain_text(self) -> str:
        import re as _re
        return _re.sub(r"[#*`]", "", self.to_markdown(with_refs=False))
