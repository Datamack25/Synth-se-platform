"""SYNTHEA - dimensionnement de la synthese.

Un livre de 1 000 pages ne se resume ni en trois puces ni en 200 pages. Ce
module calcule un **format cible** a partir de deux choses seulement : le
volume reel du document et l objectif de l utilisateur.

Loi d echelle retenue : la synthese croit comme une racine du volume.

    pages_de_synthese = 0,85 x (pages_equivalentes ^ 0,38) x densite_objectif

Pour l objectif « restituer fidelement » :

    | document |  10 p. |  50 p. | 100 p. | 500 p. | 1 000 p. | 2 000 p. |
    | synthese |   2 p. |   4 p. |   5 p. |   9 p. |   12 p.  |   15 p.  |

soit, pour 1 000 pages, de 5 pages en « lecture rapide » a 22 pages en
« etude approfondie » : la fourchette de bon sens demandee.

Tout le reste en decoule : nombre de sections, constats par section, taille du
resume executif, nombre de diapositives et de visuels, profondeur d analyse.
CAMELEON s en sert pour calibrer la restitution, exporters.export_pptx pour
plafonner le deck, et ARGUS pour verifier que le livrable respecte le format.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

MOTS_PAR_PAGE = 420          # page A4 de texte redige
MOTS_PAR_CONSTAT = 32        # longueur moyenne d une puce

# --------------------------------------------------------------------
# Objectifs utilisateur
# --------------------------------------------------------------------
OBJECTIFS: dict[str, dict] = {
    "lecture_rapide": {
        "libelle": "Lecture rapide",
        "description": "L essentiel en quelques minutes.",
        "densite": 0.45,
        "profondeur": "standard",
        "sortie": "note",
        "contexte": "atelier_grand_public",
    },
    "restitution_fidele": {
        "libelle": "Restitution fidele",
        "description": "Synthese equilibree, fidele au plan de l ouvrage.",
        "densite": 1.00,
        "profondeur": "standard",
        "sortie": "document",
        "contexte": "comite_direction",
    },
    "etude_approfondie": {
        "libelle": "Etude approfondie",
        "description": "Analyse detaillee, section par section.",
        "densite": 1.90,
        "profondeur": "exhaustif",
        "sortie": "document",
        "contexte": "fiche_lecture",
    },
    "presentation_orale": {
        "libelle": "Presentation orale",
        "description": "Support de presentation : peu de texte, beaucoup de structure.",
        "densite": 0.80,
        "profondeur": "standard",
        "sortie": "diaporama",
        "contexte": "pitch_entrepreneurial",
    },
    "aide_a_la_decision": {
        "libelle": "Aide a la decision",
        "description": "Note courte : constat, options, recommandation.",
        "densite": 0.50,
        "profondeur": "standard",
        "sortie": "note",
        "contexte": "comite_direction",
    },
    "enseignement": {
        "libelle": "Enseignement et formation",
        "description": "Support pedagogique progressif, definitions et exemples.",
        "densite": 1.50,
        "profondeur": "standard",
        "sortie": "document",
        "contexte": "cours_magistral",
    },
}
DEFAUT = "lecture_rapide"


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def pages_equivalentes(n_pages: int, n_words: int) -> float:
    """Un classeur de 3 feuilles et un livre de 300 pages n ont pas le meme
    volume : on retient le maximum entre le nombre d unites extraites et le
    volume de texte ramene en pages."""
    return max(float(n_pages or 0), (n_words or 0) / MOTS_PAR_PAGE, 1.0)


# --------------------------------------------------------------------
# Format cible
# --------------------------------------------------------------------
@dataclass
class Budget:
    """Format cible de la synthese, calcule une fois par document."""
    objectif: str
    objectif_libelle: str
    description: str
    mode: str
    profondeur: str
    sortie: str
    contexte_conseille: str

    pages_source: int
    mots_source: int
    pages_equivalentes: float

    pages_cible: float
    mots_cible: int
    mots_min: int
    mots_max: int

    sections: int
    constats_par_section: int
    constats_executif: int
    diapositives: int
    visuels: int
    compression_visee: float
    ajustement: float = 1.0
    fourchette_pages: tuple[float, float] = field(default=(0.0, 0.0))

    # ---------------------------------------------------------- rendu
    def resume_court(self) -> str:
        return (f"{self.pages_source} page(s) → "
                f"~{self.pages_cible:.0f} page(s) de synthese "
                f"({self.mots_cible} mots), {self.sections} sections, "
                f"{self.diapositives} diapositives")

    def resume_long(self) -> str:
        return (f"Objectif « {self.objectif_libelle} » : "
                f"{self.pages_source} page(s) source → une synthese de "
                f"{self.fourchette_pages[0]:.0f} a {self.fourchette_pages[1]:.0f} "
                f"pages (cible {self.pages_cible:.0f}, soit {self.mots_cible} mots), "
                f"repartie en {self.sections} sections de "
                f"{self.constats_par_section} constats, un resume executif de "
                f"{self.constats_executif} points, {self.diapositives} diapositives "
                f"et {self.visuels} visuels. Profondeur d analyse : {self.profondeur}.")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["fourchette_pages"] = list(self.fourchette_pages)
        d["resume"] = self.resume_court()
        return d


def compute(n_pages: int, n_words: int, objectif: str = DEFAUT,
            ajustement: float = 1.0, pages_imposees: float | None = None) -> Budget:
    """Calcule le format cible.

    ajustement      : curseur utilisateur (0,4 = plus court, 2,0 = plus long)
    pages_imposees  : impose directement un nombre de pages de synthese
    """
    obj = OBJECTIFS.get(objectif, OBJECTIFS[DEFAUT])
    peq = pages_equivalentes(n_pages, n_words)
    ajustement = float(_clamp(ajustement or 1.0, 0.3, 3.0))

    if pages_imposees and pages_imposees > 0:
        pages_cible = _clamp(float(pages_imposees), 0.5, 60)
        mode = "impose par l utilisateur"
    else:
        pages_cible = _clamp(0.85 * (peq ** 0.38) * obj["densite"] * ajustement,
                             1.0, 40.0)
        mode = f"calcule — {obj['libelle'].lower()}"
        if ajustement != 1.0:
            mode += f", ajustement x{ajustement:g}"

    mots_cible = int(round(pages_cible * MOTS_PAR_PAGE))
    sections = int(_clamp(round(mots_cible / 340), 4, 24))
    par_section = int(_clamp(round(mots_cible / max(sections * MOTS_PAR_CONSTAT, 1)),
                             2, 10))
    executif = int(_clamp(round(mots_cible / 260), 5, 14))
    diapositives = int(_clamp(round(pages_cible * 1.5) + 3, 6, 45))
    visuels = int(_clamp(round(pages_cible / 3) + 4, 5, 16))

    # la profondeur vient de l objectif, mais on n impose pas l analyse fine
    # page par page sur un corpus enorme : le temps de traitement exploserait
    profondeur = obj["profondeur"]
    if peq > 2500 and profondeur == "exhaustif":
        profondeur = "standard"

    return Budget(
        objectif=objectif if objectif in OBJECTIFS else DEFAUT,
        objectif_libelle=obj["libelle"],
        description=obj["description"],
        mode=mode,
        profondeur=profondeur,
        sortie=obj["sortie"],
        contexte_conseille=obj["contexte"],
        pages_source=int(n_pages or 0),
        mots_source=int(n_words or 0),
        pages_equivalentes=round(peq, 1),
        pages_cible=round(pages_cible, 1),
        mots_cible=mots_cible,
        mots_min=int(mots_cible * 0.55),
        mots_max=int(mots_cible * 1.55),
        sections=sections,
        constats_par_section=par_section,
        constats_executif=executif,
        diapositives=diapositives,
        visuels=visuels,
        compression_visee=round(100 * mots_cible / max(n_words or 1, 1), 2),
        ajustement=ajustement,
        fourchette_pages=(round(pages_cible * 0.55, 1), round(pages_cible * 1.55, 1)),
    )


# --------------------------------------------------------------------
# Controle du livrable produit
# --------------------------------------------------------------------
def controle(bud: Budget, mots_produits: int, n_constats: int = 0,
             mots_moyens_par_constat: float = 0.0) -> dict:
    """Le livrable respecte-t-il le format vise ? (controle C10 d ARGUS)"""
    mots_produits = int(mots_produits or 0)
    pages = mots_produits / MOTS_PAR_PAGE

    if mots_produits < bud.mots_min:
        statut, ecart = "trop court", "en dessous de la fourchette"
    elif mots_produits > bud.mots_max:
        statut, ecart = "trop long", "au dessus de la fourchette"
    else:
        statut, ecart = "conforme", "dans la fourchette"

    centre = max(bud.mots_cible, 1)
    score = max(0.0, 1.0 - abs(mots_produits - centre) / (centre * 1.55))

    message = (f"{bud.pages_source} page(s) → {pages:.1f} page(s) de synthese "
               f"({mots_produits} mots pour une cible de {bud.mots_cible}, "
               f"fourchette {bud.mots_min}–{bud.mots_max}) : {statut}")

    return {
        "libelle": "Respect du format cible",
        "objectif": bud.objectif_libelle,
        "mots_cible": bud.mots_cible,
        "fourchette_mots": f"{bud.mots_min}–{bud.mots_max}",
        "mots_produits": mots_produits,
        "pages_cible": bud.pages_cible,
        "pages_produites": round(pages, 1),
        "constats": int(n_constats or 0),
        "mots_par_constat": round(float(mots_moyens_par_constat or 0.0), 1),
        "ecart": ecart,
        "statut": statut,
        "taux": round(100 * score, 2),
        "message": message,
    }


def previsions(n_pages: int, n_words: int = 0) -> list[dict]:
    """Tableau comparatif des six objectifs pour ce document precis."""
    out = []
    for key, obj in OBJECTIFS.items():
        b = compute(n_pages, n_words, key)
        out.append({
            "objectif": obj["libelle"],
            "pages de synthese": f"{b.pages_cible:.0f}",
            "mots": f"{b.mots_cible}",
            "sections": b.sections,
            "diapositives": b.diapositives,
            "sortie": obj["sortie"],
            "pour quoi faire": obj["description"],
        })
    return out


def exemples_echelle() -> list[dict]:
    """Illustration de la loi d echelle, affichee dans l interface."""
    out = []
    for n in (10, 50, 100, 250, 500, 1000, 2000):
        row = {"document (pages)": n}
        for key in ("lecture_rapide", "restitution_fidele", "etude_approfondie"):
            b = compute(n, n * 400, key)
            row[OBJECTIFS[key]["libelle"]] = f"{b.pages_cible:.0f} p."
        out.append(row)
    return out
