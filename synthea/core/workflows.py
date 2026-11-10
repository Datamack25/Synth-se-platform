"""SYNTHEA - catalogue des outils de transformation et atelier de workflows.

Le catalogue decrit les 35 outils des cinq agents (pour l affichage et la
recherche). L atelier permet d enchainer plusieurs operations PDF vers PDF en
une seule passe : par exemple « deverrouiller, puis pivoter, puis filigraner,
puis compresser », applique a un lot de fichiers.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from . import convert, doctools as dt, pdfintel, pdfops
from .doctools import Resultat


# ===================================================================
# Catalogue
# ===================================================================
@dataclass
class Outil:
    id: str
    nom: str
    famille: str
    agent: str
    entree: str          # pdf | pdfs | deux_pdf | images | docx | pptx | xlsx | html
    sortie: str
    description: str


CATALOGUE: list[Outil] = [
    # ---------------- MOSAIQUE : organiser ----------------
    Outil("merge", "Fusionner des PDF", "Organiser", "MOSAIQUE", "pdfs", "pdf",
          "Combine plusieurs PDF dans l ordre que tu choisis."),
    Outil("split", "Diviser un PDF", "Organiser", "MOSAIQUE", "pdf", "pdf(s)",
          "Separe une page, des plages, ou decoupe tous les N pages."),
    Outil("extract", "Extraire ou supprimer des pages", "Organiser", "MOSAIQUE",
          "pdf", "pdf", "Garde les pages voulues, ou retire celles dont tu ne veux pas."),
    Outil("organize", "Reorganiser les pages", "Organiser", "MOSAIQUE", "pdf", "pdf",
          "Change l ordre des pages et supprime celles qui sont inutiles."),
    Outil("rotate", "Pivoter", "Organiser", "MOSAIQUE", "pdf", "pdf",
          "Fait pivoter tout le document ou seulement certaines pages."),
    Outil("crop", "Recadrer", "Organiser", "MOSAIQUE", "pdf", "pdf",
          "Rogne les marges, en pourcentage de la page."),
    Outil("numbers", "Numeros de page", "Organiser", "MOSAIQUE", "pdf", "pdf",
          "Ajoute une numerotation, avec position, format et point de depart."),
    # ---------------- ATOME : optimiser ----------------
    Outil("compress", "Compresser", "Optimiser", "ATOME", "pdf", "pdf",
          "Reduit le poids, sans perte ou par reechantillonnage des images."),
    Outil("repair", "Reparer", "Optimiser", "ATOME", "pdf", "pdf",
          "Reconstruit un PDF endommage et recupere ce qui peut l etre."),
    Outil("ocr", "OCR : rendre cherchable", "Optimiser", "ATOME", "pdf", "pdf",
          "Ajoute une couche de texte sur un document scanne."),
    Outil("scan", "Scan vers PDF", "Optimiser", "ATOME", "images", "pdf",
          "Transforme des photos de documents en PDF propre et contraste."),
    # ---------------- FORGE : convertir ----------------
    Outil("pdf2word", "PDF vers Word", "Convertir", "FORGE", "pdf", "docx",
          "Produit un document Word editable."),
    Outil("pdf2ppt", "PDF vers PowerPoint", "Convertir", "FORGE", "pdf", "pptx",
          "Une diapositive par page, en image fidele ou en texte editable."),
    Outil("pdf2excel", "PDF vers Excel", "Convertir", "FORGE", "pdf", "xlsx",
          "Recupere les tableaux dans un classeur."),
    Outil("pdf2jpg", "PDF vers JPG", "Convertir", "FORGE", "pdf", "images",
          "Rend chaque page en image, ou extrait les images incorporees."),
    Outil("pdf2md", "PDF vers Markdown", "Convertir", "FORGE", "pdf", "md",
          "Markdown propre, titres et tableaux preserves."),
    Outil("pdf2txt", "PDF vers texte", "Convertir", "FORGE", "pdf", "txt",
          "Texte brut, page par page."),
    Outil("pdf2pdfa", "PDF vers PDF/A", "Convertir", "FORGE", "pdf", "pdf",
          "Version archivable a long terme, normalisee ISO."),
    Outil("word2pdf", "Word vers PDF", "Convertir", "FORGE", "docx", "pdf",
          "Transforme un .docx en PDF."),
    Outil("ppt2pdf", "PowerPoint vers PDF", "Convertir", "FORGE", "pptx", "pdf",
          "Transforme un .pptx en PDF."),
    Outil("excel2pdf", "Excel vers PDF", "Convertir", "FORGE", "xlsx", "pdf",
          "Transforme un classeur en PDF lisible."),
    Outil("jpg2pdf", "JPG vers PDF", "Convertir", "FORGE", "images", "pdf",
          "Assemble des images en PDF, avec format et marges au choix."),
    Outil("html2pdf", "HTML vers PDF", "Convertir", "FORGE", "html", "pdf",
          "Convertit une page web (URL) ou un fichier HTML."),
    # ---------------- SCEAU : securiser et editer ----------------
    Outil("protect", "Proteger par mot de passe", "Securiser", "SCEAU", "pdf", "pdf",
          "Chiffre le document en AES-256 et restreint les droits."),
    Outil("unlock", "Deverrouiller", "Securiser", "SCEAU", "pdf", "pdf",
          "Retire la protection d un PDF dont tu connais le mot de passe."),
    Outil("watermark", "Filigrane", "Securiser", "SCEAU", "pdf", "pdf",
          "Appose un texte ou un logo, avec opacite, angle et position."),
    Outil("redact", "Caviarder", "Securiser", "SCEAU", "pdf", "pdf",
          "Supprime reellement des informations sensibles, sans retour possible."),
    Outil("sign", "Signer", "Securiser", "SCEAU", "pdf", "pdf",
          "Appose une signature visuelle, image ou texte, avec mention."),
    Outil("annotate", "Editer : texte, formes, images", "Securiser", "SCEAU",
          "pdf", "pdf", "Ajoute du texte, des rectangles, des surlignages, des images."),
    # ---------------- COLLATEUR : intelligence ----------------
    Outil("compare", "Comparer deux versions", "Intelligence", "COLLATEUR",
          "deux_pdf", "html", "Rapport cote a cote des ajouts et des suppressions."),
    Outil("tables", "Extraire les tableaux", "Intelligence", "COLLATEUR", "pdf",
          "xlsx", "Detecte les tableaux et les exporte en Excel ou en CSV."),
    Outil("forms", "Formulaires : detecter et remplir", "Intelligence", "COLLATEUR",
          "pdf", "pdf", "Liste les champs interactifs, les remplit, les aplatit."),
    Outil("inspect", "Inspecter le document", "Intelligence", "COLLATEUR", "pdf",
          "rapport", "Pages, poids, version, chiffrement, texte extractible."),
    Outil("metadata", "Metadonnees", "Intelligence", "COLLATEUR", "pdf", "pdf",
          "Lit, corrige ou efface titre, auteur, sujet et mots-cles."),
    Outil("summarize", "Resumer (chaine SYNTHEA)", "Intelligence", "COLLATEUR",
          "pdf", "md", "Branche les onze agents d analyse sur le PDF."),
    Outil("translate", "Traduire le PDF", "Intelligence", "COLLATEUR", "pdf", "pdf",
          "Traduit page par page vers l une des cinq langues."),
]

FAMILLES = ["Organiser", "Optimiser", "Convertir", "Securiser", "Intelligence"]


def catalogue_rows() -> list[dict]:
    return [{"outil": o.nom, "famille": o.famille, "agent": o.agent,
             "entree": o.entree, "sortie": o.sortie, "description": o.description}
            for o in CATALOGUE]


def par_famille(famille: str) -> list[Outil]:
    return [o for o in CATALOGUE if o.famille == famille]


def chercher(q: str) -> list[Outil]:
    from . import utils
    qn = utils.normalize(q)
    if not qn:
        return CATALOGUE
    return [o for o in CATALOGUE
            if qn in utils.normalize(f"{o.nom} {o.description} {o.famille} {o.agent}")]


# ===================================================================
# Atelier de workflows : enchainement PDF -> PDF
# ===================================================================
@dataclass
class Etape:
    cle: str
    libelle: str
    params: dict = field(default_factory=dict)


ETAPES = {
    "unlock": {
        "libelle": "Deverrouiller",
        "params": {"mot_de_passe": ""},
        "fn": lambda nom, data, p: pdfops.unlock_pdf(nom, data, p.get("mot_de_passe", "")),
    },
    "repair": {
        "libelle": "Reparer",
        "params": {},
        "fn": lambda nom, data, p: pdfops.repair_pdf(nom, data),
    },
    "ocr": {
        "libelle": "OCR",
        "params": {"langues": "fra+eng", "dpi": 200},
        "fn": lambda nom, data, p: pdfops.ocr_pdf(nom, data, p.get("langues", "fra+eng"),
                                                  int(p.get("dpi", 200))),
    },
    "extract": {
        "libelle": "Extraire des pages",
        "params": {"plages": "1-", "inverser": False},
        "fn": lambda nom, data, p: pdfops.extract_pages(nom, data, p.get("plages", "1-"),
                                                        bool(p.get("inverser"))),
    },
    "rotate": {
        "libelle": "Pivoter",
        "params": {"angle": 90, "plages": ""},
        "fn": lambda nom, data, p: pdfops.rotate_pdf(nom, data, int(p.get("angle", 90)),
                                                     p.get("plages", "")),
    },
    "crop": {
        "libelle": "Recadrer",
        "params": {"haut": 0, "bas": 0, "gauche": 0, "droite": 0},
        "fn": lambda nom, data, p: pdfops.crop_pdf(
            nom, data, float(p.get("haut", 0)), float(p.get("bas", 0)),
            float(p.get("gauche", 0)), float(p.get("droite", 0))),
    },
    "watermark": {
        "libelle": "Filigrane",
        "params": {"texte": "CONFIDENTIEL", "opacite": 0.18, "angle": 45},
        "fn": lambda nom, data, p: pdfops.watermark_pdf(
            nom, data, texte=p.get("texte", "CONFIDENTIEL"),
            opacite=float(p.get("opacite", 0.18)), angle=int(p.get("angle", 45))),
    },
    "numbers": {
        "libelle": "Numeros de page",
        "params": {"position": "bas-centre", "format_txt": "{n} / {total}"},
        "fn": lambda nom, data, p: pdfops.page_numbers(
            nom, data, position=p.get("position", "bas-centre"),
            format_txt=p.get("format_txt", "{n} / {total}")),
    },
    "redact": {
        "libelle": "Caviarder des termes",
        "params": {"motifs": ""},
        "requis": ["motifs"],
        "fn": lambda nom, data, p: pdfops.redact_pdf(nom, data, p.get("motifs", "")),
    },
    "compress": {
        "libelle": "Compresser",
        "params": {"niveau": "recommande", "dpi": 110},
        "fn": lambda nom, data, p: pdfops.compress_pdf(
            nom, data, p.get("niveau", "recommande"), int(p.get("dpi", 110))),
    },
    "protect": {
        "libelle": "Proteger par mot de passe",
        "params": {"mot_de_passe": ""},
        "requis": ["mot_de_passe"],
        "fn": lambda nom, data, p: pdfops.protect_pdf(nom, data,
                                                      p.get("mot_de_passe", "")),
    },
    "pdfa": {
        "libelle": "Convertir en PDF/A",
        "params": {},
        "fn": lambda nom, data, p: convert.pdf_to_pdfa(nom, data),
    },
}

MODELES = {
    "Archivage conforme": [("repair", {}), ("ocr", {"langues": "fra+eng"}),
                           ("numbers", {"format_txt": "{n} / {total}"}),
                           ("pdfa", {})],
    "Diffusion externe": [("redact", {"motifs": ""}),
                          ("watermark", {"texte": "DIFFUSION RESTREINTE"}),
                          ("compress", {"niveau": "recommande"})],
    "Envoi par courriel": [("compress", {"niveau": "fort", "dpi": 100})],
    "Dossier confidentiel": [("watermark", {"texte": "CONFIDENTIEL"}),
                             ("protect", {"mot_de_passe": ""})],
    "Scan exploitable": [("ocr", {"langues": "fra+eng", "dpi": 220}),
                         ("compress", {"niveau": "recommande"})],
}


def run_workflow(nom: str, data: bytes, etapes: list[tuple[str, dict]]) -> Resultat:
    """Applique les etapes dans l ordre ; s arrete a la premiere qui echoue."""
    t0 = time.time()
    courant = data
    journal: list[dict] = []
    avert: list[str] = []
    for cle, params in etapes:
        spec = ETAPES.get(cle)
        if not spec:
            journal.append({"etape": cle, "statut": "inconnue", "message": ""})
            continue
        # une etape dont un parametre indispensable est vide est ignoree :
        # elle ne doit pas faire echouer tout le workflow
        manquants = [k for k in spec.get("requis", [])
                     if not str((params or {}).get(k, "")).strip()]
        if manquants:
            journal.append({"etape": spec["libelle"], "statut": "ignoree",
                            "message": f"parametre non renseigne : "
                                       f"{', '.join(manquants)}",
                            "duree_s": 0.0, "poids_ko": 0})
            avert.append(f"Etape « {spec['libelle'] } » ignoree : "
                         f"{', '.join(manquants)} a renseigner.")
            continue
        res: Resultat = spec["fn"](nom, courant, params or {})
        journal.append({
            "etape": spec["libelle"],
            "statut": "ok" if res.ok else "echec",
            "message": res.message,
            "duree_s": res.duree,
            "poids_ko": round(res.poids_total / 1024, 1) if res.ok else 0,
        })
        avert.extend(res.avertissements)
        if not res.ok:
            return Resultat(False, "ATELIER", "Workflow", [],
                            f"Arret a l etape « {spec['libelle']} » : {res.message}",
                            {"journal": journal}, avert,
                            round(time.time() - t0, 2))
        pdfs = [f for f in res.fichiers if f[0].lower().endswith(".pdf")]
        if not pdfs:
            return Resultat(False, "ATELIER", "Workflow", [],
                            f"L etape « {spec['libelle']} » ne produit pas de PDF : "
                            f"elle ne peut pas etre chainee.",
                            {"journal": journal}, avert,
                            round(time.time() - t0, 2))
        courant = pdfs[0][1]

    return Resultat(True, "ATELIER", "Workflow",
                    [(dt.safe_name(nom, "workflow", "pdf"), courant)],
                    f"{len(etapes)} etape(s) appliquees, "
                    f"{dt.page_count(courant)} page(s), "
                    f"{len(courant) / 1024:.0f} Ko.",
                    {"journal": journal}, avert, round(time.time() - t0, 2))


def run_batch(fichiers: list[tuple[str, bytes]],
              etapes: list[tuple[str, dict]]) -> tuple[list[Resultat], bytes]:
    """Applique le meme workflow a un lot et renvoie aussi une archive ZIP."""
    import io
    import zipfile
    resultats = [run_workflow(n, d, etapes) for n, d in fichiers]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for r in resultats:
            for n, d in r.fichiers:
                z.writestr(n, d)
    return resultats, buf.getvalue()
