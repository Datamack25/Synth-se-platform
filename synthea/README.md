# SYNTHEA — Document Intelligence Suite

Plateforme Streamlit de synthèse documentaire multi-agents : elle lit un document
de **1 à 2 000 pages** dans n'importe quel format, le résume à trois niveaux,
le restitue dans **12 contextes de présentation**, le traduit en **5 langues**,
l'illustre, répond aux questions posées dessus, et **vérifie elle-même**
qu'aucune page n'a été oubliée.

La plateforme fonctionne **sans internet**. Sa connaissance métier vit dans
**57 fichiers CSV** (1 762 entrées, 134 métiers, 37 secteurs) livrés avec le dépôt.

---

## 1. Démarrage

```bash
git clone <votre-dépôt> synthea
cd synthea
pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre sur `http://localhost:8501`.

### Déploiement sur Streamlit Community Cloud

1. Pousser ce dossier sur GitHub.
2. Sur share.streamlit.io : *New app* → choisir le dépôt → fichier principal `app.py`.
3. `requirements.txt` et `packages.txt` sont lus automatiquement
   (`packages.txt` installe `tesseract-ocr` pour l'OCR des PDF scannés et des JPEG).

Options facultatives :

```bash
pip install -r requirements-optional.txt   # OCR, traduction neuronale, LLM
```

Pour activer la reformulation abstractive, créer `.streamlit/secrets.toml` :

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
```

Sans cette clé, SYNTHEA reste en **mode extractif** : chaque phrase de la synthèse
provient littéralement du document, ce qui garantit la traçabilité et interdit
l'invention de contenu.

---

## 2. Dimensionnement intelligent des synthèses

La taille de la synthèse n'est pas fixe : elle se déduit du **volume du document**
et de l'**objectif** choisi dans le panneau de gauche.

```
pages_de_synthèse = 0,85 × (pages_équivalentes ^ 0,38) × densité_objectif
```

| Document | Lecture rapide | Restitution fidèle | Étude approfondie |
|---|---|---|---|
| 10 pages | 1 p. | 2 p. | 4 p. |
| 100 pages | 2 p. | 5 p. | 9 p. |
| 500 pages | 4 p. | 9 p. | 17 p. |
| **1 000 pages** | **5 p.** | **12 p.** | **22 p.** |
| 2 000 pages | 7 p. | 15 p. | 29 p. |

Un livre de 1 000 pages donne donc une synthèse de 5 à 22 pages selon ce que
vous voulez en faire — la fourchette de bon sens, jamais trois puces ni
200 pages.

Six objectifs : *lecture rapide*, *restitution fidèle*, *étude approfondie*,
*présentation orale*, *aide à la décision*, *enseignement*. Chacun fixe la
densité, la profondeur d'analyse, le contexte de restitution conseillé et le
format de sortie.

Tout le reste en découle automatiquement : nombre de sections, constats par
section, taille du résumé exécutif, **nombre de diapositives du PowerPoint**,
nombre de visuels. Un curseur « Longueur de la synthèse » (×0,4 à ×2,0) permet
d'ajuster finement.

Deux garde-fous :

- **Rattrapage** : si la première passe reste loin sous la cible (document très
  répétitif), SCRIBE complète avec les constats écartés, en choisissant les plus
  *différents* de ce qui a déjà été dit plutôt que les mieux notés.
- **Contrôle C10 d'ARGUS** : le livrable réellement produit est mesuré et comparé
  à la cible. S'il est trop court ou trop long, c'est écrit noir sur blanc.

---

## 3. Les seize agents

| # | Agent | Rôle | Technologies |
|---|-------|------|--------------|
| A01 | **ATLAS** | Ingestion et extraction multi-format | pypdf, pdfplumber, python-docx, python-pptx, openpyxl, BeautifulSoup, Pillow, OCR |
| A02 | **BOUSSOLE** | Segmentation page-aware, détection de l'ossature | regex de titres, fenêtre glissante avec recouvrement verbatim |
| A03 | **PRISME** | Analyse sémantique et apprentissage | TF-IDF, NMF, KMeans, Naive Bayes, c-TF-IDF |
| A04 | **SCRIBE** | Synthèse hiérarchique page / section / exécutif | TextRank, régression logistique supervisée, sélection MMR |
| A05 | **LEXIS** | Terminologie métier | 57 CSV, 134 métiers, 37 secteurs |
| A06 | **CAMÉLÉON** | Restitution selon 12 contextes | affinités lexicales, banques de formules multilingues |
| A07 | **BABEL** | Traduction fr / en / es / pt / ht | glossaire hors ligne, deep-translator, LLM |
| A08 | **ATELIER** | Illustrations, schémas, infographies, retouche | Pillow, matplotlib, wordcloud |
| A09 | **ARGUS** | Autovérification en 9 contrôles | couverture, fidélité numérique et littérale, empreintes |
| A10 | **VIGIE** | Recherche ciblée, base locale d'abord | index CSV + requêtes `site:` sur domaines officiels |
| A11 | **ÉCHO** | Dialogue avec le document | BM25 maison + similarité cosinus TF-IDF |
| T01 | **FORGE** | Conversion de format (12 outils) | pypdf, pdf2docx, python-docx/pptx, LibreOffice, pypdfium2 |
| T02 | **MOSAÏQUE** | Organisation des pages (7 outils) | pypdf, pikepdf, reportlab |
| T03 | **ATOME** | Optimisation et lisibilité (4 outils) | pikepdf, qpdf, Pillow, tesseract |
| T04 | **SCEAU** | Sécurité et édition (6 outils) | AES-256, rastérisation, overlays reportlab |
| T05 | **COLLATEUR** | Intelligence documentaire (7 outils) | difflib, pdfplumber, chaîne SYNTHEA |

L'orchestrateur (`core/agents.py`) les enchaîne et consigne chaque action dans un
journal horodaté, consultable dans l'onglet **Agents**.

---

## 4. Les treize onglets

1. **Accueil** — état du moteur, briques disponibles, fiches des agents.
2. **Import** — fichiers importés, ossature détectée, explorateur page par page.
3. **Agents** — fiches de rôle, journal d'exécution, temps par agent.
4. **Analyse** — thèmes, mots-clés, entités, lisibilité, graphiques.
5. **Synthèses** — résumé exécutif, restitution par contexte, digests de page.
6. **Traductions** — comparaison source/cible, glossaire du document en 5 langues.
7. **Lexiques** — recherche dans les 57 CSV, métiers, secteurs, inventaire.
8. **Studio** — jeu de visuels, cartons de citation, retouche d'images importées.
9. **ARGUS** — score, 9 contrôles, tableau de contrôle page par page.
10. **Dialogue** — questions-réponses sourcées, suggestions, export.
11. **Veille** — base locale puis recherche web ciblée, archivage hors ligne.
12. **Exports** — PowerPoint, Word, PDF, Excel, HTML, Markdown, archive ZIP.
13. **Transforme docs** — les 36 outils documentaires (voir ci-dessous).

---

## 5. Transforme docs : 36 outils

Tout s'exécute **localement** : aucun fichier n'est envoyé à un service tiers.

| Famille | Outils |
|---|---|
| **Organiser** (MOSAÏQUE) | Fusionner · Diviser · Extraire ou supprimer des pages · Réorganiser · Pivoter · Recadrer · Numéros de page |
| **Optimiser** (ATOME) | Compresser · Réparer · OCR (rendre cherchable) · Scan vers PDF |
| **Convertir** (FORGE) | PDF→Word · PDF→PowerPoint · PDF→Excel · PDF→JPG · PDF→Markdown · PDF→texte · PDF→PDF/A · Word→PDF · PowerPoint→PDF · Excel→PDF · JPG→PDF · HTML→PDF |
| **Sécuriser** (SCEAU) | Protéger par mot de passe · Déverrouiller · Filigrane · Caviarder · Signer · Éditer (texte, formes, images) |
| **Intelligence** (COLLATEUR) | Comparer deux versions · Extraire les tableaux · Formulaires (détecter et remplir) · Inspecter · Métadonnées · Résumer · Traduire |
| **Enchaînements** | Plusieurs opérations à la suite sur un même document |
| **Lot** | La même suite d'opérations sur plusieurs documents, rendue en archive ZIP |

Trois choix d'ingénierie à connaître :

- **Caviardage réel** : les pages concernées sont rastérisées, le texte masqué
  disparaît physiquement du fichier au lieu d'être recouvert d'un rectangle noir.
- **Signature visuelle** : elle n'a pas la valeur juridique d'une signature
  électronique qualifiée, et l'interface le dit.
- **Déverrouillage** : SYNTHEA ne casse aucune protection. Le mot de passe doit
  être connu, ou le PDF seulement protégé contre l'édition.

Chaque outil fonctionne sans brique optionnelle et l'annonce quand il bascule
sur une méthode de repli : sans LibreOffice les conversions Office passent en
mode « reconstruction » (contenu et structure préservés, mise en page
simplifiée), sans Ghostscript le PDF/A porte les métadonnées d'archivage sans
certification stricte, sans Tesseract l'OCR est indisponible plutôt que
silencieux.

---

## 6. Formats pris en charge

| Entrée | Unité logique = une « page » |
|--------|------------------------------|
| PDF | une page (OCR si la page est numérisée) |
| PowerPoint | une diapositive (notes comprises) |
| Excel / CSV | une feuille, ou un bloc de 200 lignes |
| Word / HTML / TXT / Markdown / JSON | une section d'environ 2 800 caractères |
| JPEG, PNG, TIFF, WEBP | l'image (OCR) |
| EPUB | un fichier interne du livre |
| ZIP | le contenu, fichier par fichier |

**Sorties** : `.pptx`, `.docx`, `.pdf`, `.xlsx`, `.html` autonome, `.md`, `.png`, `.zip`.

---

## 7. Les douze contextes de restitution

`pitch_entrepreneurial`, `comite_direction`, `campagne_presidentielle`,
`conseil_administration`, `note_administrative`, `note_conformite`,
`cours_magistral`, `investisseur_due_diligence`, `atelier_grand_public`,
`reunion_equipe`, `conference_inspirante`, `fiche_lecture`.

Chaque contexte définit son public, son registre, sa longueur cible, sa structure
et ses règles de style (`data/lexicons/55_contextes_restitution.csv`). CAMÉLÉON
réalloue les constats de SCRIBE dans les rubriques du contexte selon leur affinité
lexicale, puis insère les formules d'ouverture et de clôture correspondantes.

Ajouter un contexte = ajouter une ligne au CSV et ses formules dans
`47_formules_par_contexte.csv`. Aucun code à modifier.

---

## 8. La base de connaissance : 57 CSV

```
data/lexicons/
├── 00_metiers_referentiel.csv        134 métiers, 37 secteurs, 5 langues
├── 01..37_lex_<secteur>.csv          37 lexiques sectoriels (655 termes)
├── 40_langue_multilingue_core.csv    132 notions pivots fr/en/es/pt/ht
├── 41_langue_connecteurs_rhetoriques.csv
├── 42_langue_verbes_action.csv
├── 43_langue_argot_familier_fr.csv   registre familier et argot
├── 44_langue_expressions_idiomatiques.csv
├── 45_langue_sigles_abreviations.csv 50 sigles développés automatiquement
├── 46_langue_creole_haitien.csv      glossaire kreyòl
├── 47_formules_par_contexte.csv      48 formules par contexte, en 5 langues
├── 50..54_stopwords_<langue>.csv
├── 55_contextes_restitution.csv      12 contextes
├── 56_trames_narratives.csv          10 trames
├── 57_registres_langue.csv
├── 58_sources_veille.csv             36 sources officielles
├── 59_pays_institutions.csv          38 pays et corridors
└── 60_faux_amis_traduction.csv
```

Secteurs couverts : finance de marché, banque, conformité LCB-FT, assurance,
comptabilité, fiscalité, droit, développement, cybersécurité, data/IA, télécoms,
santé, pharmacie, BTP, immobilier, logistique, maritime, aéronautique, énergie,
agriculture, industrie, commerce, marketing, RH, éducation, hôtellerie, médias,
culture, sport, administration, politique, startup, ONG, sécurité, mode,
automobile, artisanat.

**Enrichir la base** : ajouter des entrées dans `scripts/build_0*.py`, puis

```bash
python scripts/build_all_lexicons.py
```

---

## 9. ARGUS : comment la plateforme se vérifie

Neuf contrôles indépendants répondent à : *tout le document a-t-il été lu, analysé
et résumé ?*

| Code | Contrôle | Ce qu'il garantit |
|------|----------|-------------------|
| C1 | Inventaire de l'extraction | nombre d'unités, pages vides, avertissements, troncature |
| C2 | Couverture par la segmentation | chaque page appartient à au moins un bloc |
| C3 | Couverture par la synthèse | chaque page a un digest ou appartient à une section |
| C4 | Pages non résumées | liste nominative des pages manquantes et de leur cause |
| C5 | Fidélité numérique | aucun chiffre de la synthèse absent du document source |
| C6 | Fidélité littérale | chaque constat est retrouvé mot pour mot dans le texte |
| C7 | Traçabilité | chaque constat porte sa référence de page |
| C8 | Redondance interne | mesure des constats trop proches entre eux |
| C9 | Compression et équilibre | taux de compression rapporté à la taille du corpus |

Le score global est pondéré (couverture 30 %, segmentation 18 %, fidélité
numérique 18 %, fidélité littérale 14 %, traçabilité 10 %, non-redondance 10 %)
et pénalisé de 15 % si le corpus a été tronqué. Le tableau de contrôle page par
page est exportable en CSV et en Excel ; le rapport complet en JSON.

**Résultats mesurés** (corpus de test synthétique, `scripts/smoke_test.py`) :

| Corpus | Pages | Temps | Score ARGUS | Couverture | Fidélité num. | Fidélité litt. |
|--------|-------|-------|-------------|------------|---------------|----------------|
| 7 fichiers mixtes (PDF, DOCX, PPTX, XLSX, HTML, JPEG, TXT) | 79 | ~65 s* | **100/100** | 100 % | 100 % | 100 % |
| PDF 900 p. + texte long | 1 782 | 11 s | **100/100** | 100 % | 100 % | 100 % |

\* dont la majeure partie en tentatives de traduction en ligne ; le second test
est exécuté sans traduction.

Toute page non résumée est **nommée** dans le contrôle C4, avec sa cause
(page vide, scan sans OCR, troncature). Un constat repris par plusieurs sections
n'est jamais recopié : sa référence s'enrichit (`p. 27, 39, 53, 61`).

---

## 10. Honnêteté du moteur

- **Mode extractif par défaut.** Sans clé LLM, aucune phrase n'est générée :
  elles sont sélectionnées dans le document. C5 et C6 le vérifient.
- **Traduction.** Le moteur hors ligne annonce son **taux de couverture réel**
  (part des termes porteurs effectivement convertis) et indique le moteur
  *réellement* utilisé, y compris en cas de repli automatique quand le réseau
  est indisponible.
- **OCR.** Si `pytesseract` ou le binaire `tesseract` manque, les pages scannées
  sont signalées comme non extractibles plutôt que silencieusement ignorées.
- **Internet.** VIGIE interroge toujours la base locale en premier, restreint ses
  requêtes web aux domaines officiels, et le dit clairement quand le réseau est
  inaccessible — sans jamais fabriquer de résultat.

---

## 11. Architecture

```
synthea/
├── app.py                    interface Streamlit (12 onglets)
├── core/
│   ├── models.py             Page, Document, Chunk, Claim, SummaryTree, Rendition
│   ├── utils.py              texte, phrases, références de page, empreintes
│   ├── lexicons.py           chargement et interrogation des 57 CSV
│   ├── extraction.py         ATLAS
│   ├── chunking.py           BOUSSOLE
│   ├── ml.py                 PRISME
│   ├── summarizer.py         SCRIBE
│   ├── contexts.py           CAMÉLÉON
│   ├── translation.py        BABEL
│   ├── imaging.py            ATELIER
│   ├── verification.py       ARGUS
│   ├── websearch.py          VIGIE
│   ├── qa.py                 ÉCHO
│   ├── budget.py             dimensionnement des syntheses
│   ├── doctools.py           socle commun de la boite a outils
│   ├── pdfops.py             MOSAIQUE + ATOME + SCEAU (organiser, optimiser, securiser)
│   ├── convert.py            FORGE (12 conversions)
│   ├── pdfintel.py           COLLATEUR (comparer, tableaux, formulaires, resumer, traduire)
│   ├── workflows.py          catalogue des 36 outils, enchainements, traitement par lot
│   ├── tab_transform.py      interface de l onglet Transforme docs
│   ├── ui.py                 fragments d interface partages
│   ├── exporters.py          pptx, docx, pdf, xlsx, html, zip
│   ├── html_report.py        rendu HTML professionnel
│   └── llm.py                adaptateur LLM optionnel
├── data/lexicons/            57 CSV
├── data/corpora/             archives de veille hors ligne
├── scripts/                  générateurs de lexiques + test de bout en bout
├── assets/style.css
├── requirements.txt / requirements-optional.txt / packages.txt
└── .streamlit/config.toml
```

### Test de bout en bout

```bash
python scripts/smoke_test.py          # corpus mixte ~80 pages, 11 agents
python scripts/smoke_test.py --big    # test de charge ~740 pages
python scripts/test_transform.py      # les 36 outils documentaires + dimensionnement
```

Le script génère un corpus synthétique dans sept formats, exécute les onze
agents, affiche le rapport ARGUS et produit tous les exports dans `exports/`.

---

## 12. Réglages utiles

| Réglage | Où | Effet |
|---------|----|-------|
| Profondeur | panneau latéral | `rapide` (blocs), `standard` (toutes les pages), `exhaustif` (analyse fine) |
| Limite de pages | panneau latéral | garde-fou, 2 000 par défaut |
| Sections de synthèse | panneau latéral | 4 à 24 |
| Taille des blocs | `core/agents.py` → `DEFAULTS["target_words"]` | 900 mots par défaut |
| Seuils ARGUS | `core/verification.py` → `SEUILS` | couverture, fidélité, redondance |
| Palettes | `core/imaging.py` → `PALETTES` | 7 palettes pour visuels et PowerPoint |

---

## 13. Limites connues

- L'OCR dépend du binaire `tesseract` ; sur un PDF entièrement numérisé sans OCR,
  ARGUS signalera les pages comme non extractibles (c'est le comportement voulu).
- La traduction hors ligne est une **traduction assistée par glossaire**, pas une
  traduction neuronale : sa couverture typique est de 20 à 45 % des termes
  porteurs. Installer `deep-translator` ou configurer une clé LLM pour une
  traduction complète.
- Les thèmes NMF sont descriptifs, pas interprétatifs : ils donnent les champs
  lexicaux dominants, à relire avant publication.
- Un document très répétitif fera monter C8 (redondance) : c'est une
  caractéristique de la source, pas un défaut de la synthèse.
