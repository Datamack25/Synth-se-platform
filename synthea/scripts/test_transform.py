"""SYNTHEA - test de bout en bout de la boite a outils documentaire.

Usage : python scripts/test_transform.py
"""
from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts"))

from core import budget, convert, doctools as dt, pdfintel, pdfops, workflows  # noqa: E402
from smoke_test import make_docx, make_jpeg, make_pdf, make_pptx, make_xlsx  # noqa: E402


def ligne(res, attendu_min: int = 1) -> bool:
    ok = res.ok and len(res.fichiers) >= attendu_min
    etat = "OK " if ok else "KO "
    poids = f"{res.poids_total / 1024:7.0f} Ko" if res.fichiers else "      -"
    print(f"  [{etat}] {res.agent:9s} {res.operation:34s} {poids}  "
          f"{res.duree:5.2f}s  {res.message[:58]}")
    for a in res.avertissements[:2]:
        print(f"         ⚠ {a[:96]}")
    return ok


def main() -> int:
    print("[0] capacites du moteur")
    for row in dt.capability_rows():
        print(f"      {row}")

    pdf = make_pdf(8)
    pdf2 = make_pdf(9)
    docx, pptx, xlsx, jpg = make_docx(), make_pptx(), make_xlsx(), make_jpeg()
    total = reussis = 0

    print("\n[1] MOSAIQUE — organisation")
    for res in (
        pdfops.merge_pdf([("a.pdf", pdf), ("b.pdf", pdf2)]),
        pdfops.split_pdf("a.pdf", pdf, "plages", "1-3, 4-8"),
        pdfops.split_pdf("a.pdf", pdf, "une_par_page"),
        pdfops.extract_pages("a.pdf", pdf, "2-4"),
        pdfops.extract_pages("a.pdf", pdf, "2", inverser=True),
        pdfops.organize_pdf("a.pdf", pdf, ordre="3,1,2", supprimer="8"),
        pdfops.rotate_pdf("a.pdf", pdf, 90),
        pdfops.crop_pdf("a.pdf", pdf, haut=10, bas=10),
        pdfops.page_numbers("a.pdf", pdf, "bas-centre", 1, "{n} / {total}"),
    ):
        total += 1
        reussis += ligne(res)

    print("\n[2] ATOME — optimisation")
    for res in (
        pdfops.compress_pdf("a.pdf", pdf, "recommande"),
        pdfops.repair_pdf("a.pdf", pdf),
        pdfops.scan_to_pdf([("s1.jpg", jpg), ("s2.jpg", jpg)]),
        pdfops.ocr_pdf("a.pdf", pdf, "fra+eng", 150, "1-2"),
    ):
        total += 1
        reussis += ligne(res)

    print("\n[3] FORGE — conversions")
    for res in (
        convert.pdf_to_word("a.pdf", pdf, "1-4", "texte"),
        convert.pdf_to_powerpoint("a.pdf", pdf, "1-3", "image", 100),
        convert.pdf_to_excel("a.pdf", pdf, "1-3"),
        convert.pdf_to_jpg("a.pdf", pdf, "1-2", 100, "JPEG"),
        convert.pdf_to_markdown("a.pdf", pdf, "1-3"),
        convert.pdf_to_text("a.pdf", pdf),
        convert.pdf_to_pdfa("a.pdf", pdf),
        convert.word_to_pdf("n.docx", docx, "texte"),
        convert.powerpoint_to_pdf("c.pptx", pptx, "texte"),
        convert.excel_to_pdf("s.xlsx", xlsx, "texte"),
        convert.jpg_to_pdf([("i1.jpg", jpg), ("i2.jpg", jpg)]),
        convert.html_to_pdf("", "p.html",
                            b"<h1>Titre</h1><p>Paragraphe de test.</p>"),
    ):
        total += 1
        reussis += ligne(res)

    print("\n[4] SCEAU — securite et edition")
    prot = pdfops.protect_pdf("a.pdf", pdf, "secret123")
    total += 1
    reussis += ligne(prot)
    if prot.ok:
        total += 1
        reussis += ligne(pdfops.unlock_pdf("p.pdf", prot.fichiers[0][1], "secret123"))
    for res in (
        pdfops.watermark_pdf("a.pdf", pdf, "CONFIDENTIEL"),
        pdfops.redact_pdf("a.pdf", pdf, "blanchiment\nTracfin", dpi=110),
        pdfops.sign_pdf("a.pdf", pdf, None, "J. Pierre", 0, 60, 12, 28,
                        "Lu et approuve"),
        pdfops.annotate_pdf("a.pdf", pdf, [
            {"type": "texte", "page": 1, "x": 10, "y": 80, "largeur": 40,
             "hauteur": 6, "texte": "NOTE", "couleur": "#A33A2E", "taille": 14},
            {"type": "rectangle", "page": 1, "x": 8, "y": 78, "largeur": 44,
             "hauteur": 10, "couleur": "#1F6F6B"},
        ]),
    ):
        total += 1
        reussis += ligne(res)

    print("\n[5] COLLATEUR — intelligence documentaire")
    for res in (
        pdfintel.compare_pdf("a.pdf", pdf, "b.pdf", pdf2),
        pdfintel.extract_tables("s.pdf", convert.excel_to_pdf(
            "s.xlsx", xlsx, "texte").fichiers[0][1]),
        pdfintel.read_metadata("a.pdf", pdf),
        pdfintel.write_metadata("a.pdf", pdf, "Rapport LCB-FT", "SYNTHEA"),
        pdfintel.translate_pdf("a.pdf", pdf, "en", "glossaire", "fr"),
    ):
        total += 1
        reussis += ligne(res, 0)

    # un PDF sans champ interactif doit etre refuse avec un message utile :
    # c est le comportement attendu, pas une panne
    sans_formulaire = pdfintel.inspect_forms("a.pdf", pdf)
    total += 1
    attendu = (not sans_formulaire.ok) and "champ" in sans_formulaire.message
    reussis += attendu
    print(f"  [{'OK ' if attendu else 'KO '}] COLLATEUR Formulaires : refus attendu "
          f"sur un PDF sans champ\n         → {sans_formulaire.message[:88]}")

    print("\n[6] Enchainement et lot")
    wf = workflows.run_workflow("a.pdf", pdf, [
        ("rotate", {"angle": 90}),
        ("watermark", {"texte": "BROUILLON"}),
        ("numbers", {}),
        ("compress", {"niveau": "recommande"}),
        ("protect", {}),            # parametre manquant : doit etre ignoree
    ])
    total += 1
    reussis += ligne(wf)
    for j in wf.details.get("journal", []):
        print(f"         → {j.get('etape'):26s} {j.get('statut'):9s} "
              f"{str(j.get('message',''))[:48]}")
    lot, zipb = workflows.run_batch(
        [("d1.pdf", pdf), ("d2.pdf", pdf2)], [("compress", {"niveau": "leger"})])
    total += 1
    ok_lot = all(r.ok for r in lot) and len(zipb) > 0
    reussis += ok_lot
    print(f"  [{'OK ' if ok_lot else 'KO '}] lot       {len(lot)} documents"
          f"{'':20s}{len(zipb) / 1024:7.0f} Ko")

    print("\n[7] Dimensionnement des syntheses")
    for n in (10, 100, 1000, 2000):
        ligne_txt = []
        for o in ("lecture_rapide", "restitution_fidele", "etude_approfondie"):
            b = budget.compute(n, n * 400, o)
            ligne_txt.append(f"{b.pages_cible:5.1f} p.")
        print(f"      {n:5d} pages source → rapide {ligne_txt[0]} | "
              f"fidele {ligne_txt[1]} | approfondi {ligne_txt[2]}")
    b = budget.compute(1000, 400000, "restitution_fidele")
    assert 5 <= b.pages_cible <= 20, "hors de la fourchette de bon sens"
    print(f"      controle : 1000 pages → {b.pages_cible:.0f} pages "
          f"(fourchette demandee 5-20) ✓")

    print(f"\n[OK] {reussis}/{total} operations reussies")
    return 0 if reussis == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
