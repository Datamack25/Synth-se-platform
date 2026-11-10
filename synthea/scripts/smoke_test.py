"""SYNTHEA - test de bout en bout sur un corpus synthetique multi-format.

Usage :
    python scripts/smoke_test.py            # corpus moyen (~160 pages)
    python scripts/smoke_test.py --big      # test de charge (~2000 pages)
"""
from __future__ import annotations

import io
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core import agents, exporters, qa, utils          # noqa: E402

BIG = "--big" in sys.argv

PARAS = [
    "Le dispositif de lutte contre le blanchiment de capitaux repose sur trois "
    "piliers : la connaissance du client, la surveillance des operations et la "
    "declaration de soupcon aupres de la cellule de renseignement financier.",
    "En 2024, les transferts d argent vers les corridors Europe-Afrique ont "
    "represente 48 milliards d euros, soit une progression de 6,3 % sur un an.",
    "La vigilance renforcee s applique aux personnes politiquement exposees ainsi "
    "qu aux relations d affaires impliquant une juridiction a risque eleve.",
    "Le beneficiaire effectif est la personne physique qui controle en dernier "
    "ressort l entite cliente, directement ou indirectement, au-dela du seuil de 25 %.",
    "Les faux positifs representent encore 82 % des alertes de criblage, ce qui "
    "mobilise une part excessive du temps des analystes.",
    "Une societe ecran se reconnait a l absence de substance economique : pas de "
    "salarie, pas de local, un objet social tres large et un prete-nom au capital.",
    "Le cout d acquisition client s eleve a 340 euros pour une valeur vie estimee "
    "a 2 100 euros, soit un ratio de 6,2 juge satisfaisant par le comite.",
    "L option retenue par le comite de direction consiste a industrialiser le "
    "criblage avant de deployer la remediation sur l ensemble du portefeuille.",
    "Nous prenons devant vous un engagement precis : reduire de moitie le delai de "
    "traitement des dossiers d ici au 31 decembre, sans augmenter les effectifs.",
    "La principale limite de cette etude tient a l echantillon : 212 dossiers "
    "seulement, tous issus d un meme segment de clientele.",
    "Chapitre 3 : les typologies de blanchiment observees dans les paiements "
    "transfrontaliers de detail.",
    "Le risque residuel est evalue a un niveau moyen apres prise en compte des "
    "mesures d atenuation decrites a la section precedente.",
    "Le plan d action comporte quatre etapes : cadrage, experimentation sur un "
    "perimetre reduit, deploiement progressif et mesure des effets.",
    "La formation des equipes operationnelles conditionne la reussite du "
    "dispositif : sans appropriation locale, aucun outil ne produit ses effets.",
]


def _text_pages(n: int, offset: int = 0) -> str:
    out = []
    for i in range(n):
        head = f"### Section {offset + i + 1}"
        body = "\n\n".join(PARAS[(offset + i + k) % len(PARAS)] for k in range(4))
        out.append(f"{head}\n\n{body}")
    return "\n\n".join(out)


# ------------------------------------------------------------ generateurs
def make_pdf(pages: int) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate
    buf = io.BytesIO()
    d = SimpleDocTemplate(buf, pagesize=A4, title="Rapport LCB-FT synthetique")
    ss = getSampleStyleSheet()
    flow = []
    for i in range(pages):
        flow.append(Paragraph(f"Chapitre {i + 1} : dispositif et typologies", ss["Heading1"]))
        for k in range(3):
            flow.append(Paragraph(PARAS[(i + k) % len(PARAS)], ss["BodyText"]))
        flow.append(PageBreak())
    d.build(flow)
    return buf.getvalue()


def make_docx() -> bytes:
    import docx
    d = docx.Document()
    d.add_heading("Note de synthese conformite", 0)
    for i, p in enumerate(PARAS):
        if i % 4 == 0:
            d.add_heading(f"Partie {i // 4 + 1}", level=1)
        d.add_paragraph(p)
    t = d.add_table(rows=1, cols=3)
    t.rows[0].cells[0].text = "Indicateur"
    t.rows[0].cells[1].text = "2023"
    t.rows[0].cells[2].text = "2024"
    for nm, a, b in (("Alertes", "12 400", "15 100"), ("Faux positifs", "84 %", "82 %")):
        c = t.add_row().cells
        c[0].text, c[1].text, c[2].text = nm, a, b
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def make_pptx() -> bytes:
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    for i in range(6):
        s = prs.slides.add_slide(prs.slide_layouts[5])
        s.shapes.title.text = f"Diapositive {i + 1} : constats"
        tb = s.shapes.add_textbox(Inches(1), Inches(2), Inches(8), Inches(4))
        tb.text_frame.text = PARAS[i % len(PARAS)]
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def make_xlsx() -> bytes:
    import xlsxwriter
    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {"in_memory": True})
    ws = wb.add_worksheet("alertes")
    ws.write_row(0, 0, ["mois", "alertes", "declarations", "taux"])
    for i in range(36):
        ws.write_row(i + 1, 0, [f"2024-{i % 12 + 1:02d}", 1000 + i * 7, 12 + i % 5,
                                f"{1.1 + i / 100:.2f} %"])
    wb.close()
    return buf.getvalue()


def make_html() -> bytes:
    body = "".join(f"<h2>Rubrique {i + 1}</h2><p>{p}</p>"
                   for i, p in enumerate(PARAS))
    return (f"<html><head><title>Veille reglementaire</title></head>"
            f"<body><h1>Veille LCB-FT</h1>{body}</body></html>").encode("utf-8")


def make_jpeg() -> bytes:
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (1200, 800), "#F1EEE8")
    d = ImageDraw.Draw(img)
    d.rectangle([40, 40, 1160, 760], outline="#1F6F6B", width=6)
    d.text((80, 120), "Schema du dispositif LCB-FT", fill="#17202A")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def make_txt(pages: int) -> bytes:
    return _text_pages(pages).encode("utf-8")


# ------------------------------------------------------------------ test
def main() -> int:
    t0 = time.time()
    n_pdf = 60 if not BIG else 400
    n_txt = 40 if not BIG else 1500

    print("[1/6] generation du corpus synthetique...")
    files = [
        ("rapport_lcbft.pdf", make_pdf(n_pdf)),
        ("note_conformite.docx", make_docx()),
        ("comite.pptx", make_pptx()),
        ("suivi_alertes.xlsx", make_xlsx()),
        ("veille.html", make_html()),
        ("schema.jpg", make_jpeg()),
        ("ouvrage.txt", make_txt(n_txt)),
    ]
    for n, d in files:
        print(f"      {n:26s} {len(d) / 1024:8.1f} Ko")

    print("[2/6] execution du pipeline (11 agents)...")
    orch = agents.Orchestrator({
        "profondeur": "standard",
        "contextes": ["pitch_entrepreneurial", "comite_direction",
                      "campagne_presidentielle", "fiche_lecture"],
        "langues_cibles": ["en", "es", "ht"],
        "visuels": True,
        "veille": False,
        "max_pages": 2000,
        "palette": "sable",
    })
    state = orch.run(files, progress=lambda f, m: None)

    doc, tree = state.get("doc"), state.get("tree")
    audit = state.get("audit")
    assert doc is not None and tree is not None, "pipeline interrompu"

    print(f"\n      pages extraites        : {doc.n_pages}")
    print(f"      mots                   : {utils.human_int(doc.n_words)}")
    print(f"      blocs                  : {len(state['chunks'])}")
    print(f"      sections               : {len(tree.sections)}")
    print(f"      constats               : {len(tree.all_claims)}")
    print(f"      pages resumees         : {tree.stats['pages_resumees']}")
    print(f"      type detecte           : {tree.doc_type}")
    print(f"      modele supervise       : {tree.stats['modele_supervise']}")
    print(f"      themes                 : {[t['libelle'] for t in tree.topics[:4]]}")

    print("\n[3/6] verification ARGUS")
    print(f"      score   : {audit['score']:.1f}/100 — {audit['verdict']}")
    for code, c in audit["controles"].items():
        val = c.get("taux", c.get("n", c.get("unites_extraites", "")))
        val = f"{val:.1f} %" if isinstance(val, float) else str(val)
        print(f"      {code} {c['libelle']:38s} {val:>10s}  [{c['statut']}]")
    for r in audit["recommandations"]:
        print(f"      -> {r}")

    print("\n[4/6] restitutions et traductions")
    for k, r in state["renditions"].items():
        md = r.to_markdown()
        print(f"      {k:28s} {len(r.sections)} rubriques, "
              f"{utils.word_count(md)} mots")
    for ckey, per_lang in (state.get("traductions") or {}).items():
        for lg, r in per_lang.items():
            print(f"      {ckey} -> {lg:3s} moteur={r.meta['traduction_moteur']:14s} "
                  f"couverture={r.meta['traduction_couverture']:.0%}")

    print("\n[5/6] dialogue ECHO")
    retr: qa.Retriever = state["retriever"]
    for q in ["Combien de faux positifs ?",
              "Qu est-ce qu un beneficiaire effectif ?",
              "Resume les points principaux.",
              "Quelles sont les limites de l etude ?"]:
        a = qa.ask(q, doc, retr, tree)
        first = a["reponse"].split("\n")[-1][:118]
        print(f"      Q: {q}\n         [{a['moteur']}] {a['refs'] or '-'} | {first}")

    print("\n[6/6] exports")
    rend = list(state["renditions"].values())[1]
    images = state.get("images") or {}
    outs = {
        "synthese.pptx": exporters.export_pptx(rend, tree, doc, images),
        "synthese.docx": exporters.export_docx(rend, tree, doc, audit, images),
        "synthese.pdf": exporters.export_pdf(rend, tree, doc, audit, images),
        "analyse.xlsx": exporters.export_xlsx(doc, state["chunks"], tree, audit,
                                              state["page_rows"]),
        "rapport.html": exporters.export_html(rend, tree, doc, audit, images),
        "synthese.md": exporters.export_markdown(rend),
        "visuels.zip": exporters.export_images_zip(images),
    }
    for name, data in outs.items():
        path = exporters.save_local(name, data)
        print(f"      {name:18s} {len(data) / 1024:9.1f} Ko  -> {path}")

    print(f"\n[OK] pipeline complet en {time.time() - t0:.1f}s "
          f"({doc.n_pages} pages)")
    print("\nJournal des agents (extrait) :")
    for e in orch.journal.entries[-14:]:
        print(f"  {e.t}  {e.agent:9s} {e.message[:92]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
