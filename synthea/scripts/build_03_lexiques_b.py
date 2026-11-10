"""SYNTHEA - Lexiques sectoriels (serie B) : telecoms, sante, pharma, BTP, immobilier,
logistique, maritime, aeronautique, energie, agriculture, industrie."""
from __future__ import annotations

from _csvutil import write_sector

TELECOM = [
    ("bande passante", "technique", "Debit maximal theorique d un lien.", "bandwidth", "ancho de banda", "largura de banda", "band pasan"),
    ("latence", "technique", "Delai de transmission d un paquet entre deux points.", "latency", "latencia", "latencia", "latans"),
    ("gigue", "technique", "Variation de la latence au cours du temps.", "jitter", "fluctuacion", "jitter", "jig"),
    ("routage", "technique", "Choix du chemin suivi par les paquets.", "routing", "enrutamiento", "roteamento", "woutaj"),
    ("reseau local virtuel", "technique", "Segmentation logique d un reseau physique.", "VLAN", "VLAN", "VLAN", "rezo lokal vityèl"),
    ("boucle locale", "technique", "Dernier segment reliant l abonne au reseau.", "local loop", "bucle local", "lacete local", "boukl lokal"),
    ("fibre optique", "courant", "Support de transmission par impulsions lumineuses.", "optical fibre", "fibra optica", "fibra otica", "fib optik"),
    ("raccordement", "courant", "Operation de branchement d un client au reseau.", "connection works", "conexion", "ligacao", "rakòdman"),
    ("soudure de fibre", "technique", "Fusion de deux brins pour assurer la continuite optique.", "fibre splicing", "fusion de fibra", "fusao de fibra", "soudi fib"),
    ("taux de disponibilite", "technique", "Part du temps pendant laquelle le service fonctionne.", "availability rate", "tasa de disponibilidad", "taxa de disponibilidade", "to disponibilite"),
    ("engagement de service", "technique", "Niveau de qualite contractuellement garanti.", "service level agreement", "acuerdo de nivel de servicio", "acordo de nivel de servico", "angajman sèvis"),
    ("itinerance", "technique", "Usage du reseau d un autre operateur a l etranger.", "roaming", "itinerancia", "roaming", "itineran"),
    ("couverture reseau", "courant", "Etendue geographique du signal utilisable.", "network coverage", "cobertura de red", "cobertura de rede", "kouvèti rezo"),
    ("zone blanche", "courant", "Territoire sans couverture mobile exploitable.", "dead zone", "zona sin cobertura", "zona sem cobertura", "zòn blanch"),
    ("debit descendant", "technique", "Vitesse de reception des donnees par l abonne.", "downlink speed", "velocidad de bajada", "velocidade de download", "debi desandan"),
    ("saturation de cellule", "technique", "Depassement de la capacite d une antenne.", "cell congestion", "saturacion de celda", "saturacao de celula", "satirasyon selil"),
    ("ca pingue", "familier", "La latence est trop elevee pour un usage confortable.", "it lags", "va con lag", "esta com lag", "l ap pingue"),
]

SANTE = [
    ("anamnese", "technique", "Recueil de l histoire du patient et de ses antecedents.", "medical history taking", "anamnesis", "anamnese", "anamnèz"),
    ("diagnostic differentiel", "technique", "Liste des hypotheses a ecarter avant conclusion.", "differential diagnosis", "diagnostico diferencial", "diagnostico diferencial", "dyagnostik diferansyèl"),
    ("constantes vitales", "technique", "Parametres de surveillance tels que pouls et tension.", "vital signs", "constantes vitales", "sinais vitais", "konstant vital"),
    ("posologie", "technique", "Dose et rythme d administration d un medicament.", "dosage", "posologia", "posologia", "pozoloji"),
    ("effet indesirable", "technique", "Reaction nuisible liee a un traitement.", "adverse effect", "efecto adverso", "efeito adverso", "efè endezirab"),
    ("observance", "technique", "Respect par le patient du traitement prescrit.", "adherence", "adherencia", "adesao", "obsèvans"),
    ("pronostic", "technique", "Evolution probable de l etat du patient.", "prognosis", "pronostico", "prognostico", "pwonostik"),
    ("protocole de soins", "technique", "Sequence standardisee de prise en charge.", "care protocol", "protocolo asistencial", "protocolo de cuidados", "pwotokòl swen"),
    ("transmission infirmiere", "technique", "Information transmise entre equipes lors de la releve.", "nursing handover", "relevo de enfermeria", "passagem de plantao", "transmisyon enfimye"),
    ("triage", "technique", "Classement des patients par degre d urgence.", "triage", "triaje", "triagem", "triyaj"),
    ("consentement eclaire", "technique", "Accord donne apres information complete.", "informed consent", "consentimiento informado", "consentimento informado", "konsantman klè"),
    ("secret medical", "technique", "Obligation de confidentialite sur l etat du patient.", "medical confidentiality", "secreto medico", "sigilo medico", "sekrè medikal"),
    ("parcours de soins", "courant", "Enchainement coordonne des intervenants autour du patient.", "care pathway", "ruta asistencial", "percurso de cuidados", "pakou swen"),
    ("education therapeutique", "technique", "Apprentissage par le patient de la gestion de sa maladie.", "patient education", "educacion terapeutica", "educacao terapeutica", "edikasyon terapetik"),
    ("soins palliatifs", "technique", "Prise en charge visant le confort en phase avancee.", "palliative care", "cuidados paliativos", "cuidados paliativos", "swen palyatif"),
    ("hygiene des mains", "courant", "Geste de base de prevention des infections.", "hand hygiene", "higiene de manos", "higiene das maos", "ijyèn men"),
    ("etre de garde", "familier", "Assurer la permanence hors horaires ordinaires.", "to be on call", "estar de guardia", "estar de plantao", "ap fè gad"),
]

PHARMA = [
    ("principe actif", "technique", "Substance responsable de l effet therapeutique.", "active ingredient", "principio activo", "principio ativo", "prensip aktif"),
    ("excipient", "technique", "Substance inerte servant de support au principe actif.", "excipient", "excipiente", "excipiente", "eksipyan"),
    ("forme galenique", "technique", "Presentation du medicament, comprime, sirop ou injectable.", "dosage form", "forma galenica", "forma farmaceutica", "fòm galenik"),
    ("biodisponibilite", "technique", "Fraction de la dose atteignant la circulation generale.", "bioavailability", "biodisponibilidad", "biodisponibilidade", "biyodisponibilite"),
    ("interaction medicamenteuse", "technique", "Modification d effet due a l association de traitements.", "drug interaction", "interaccion farmacologica", "interacao medicamentosa", "entèraksyon medikaman"),
    ("essai clinique", "technique", "Etude encadree evaluant un traitement chez l humain.", "clinical trial", "ensayo clinico", "ensaio clinico", "esè klinik"),
    ("groupe temoin", "technique", "Groupe de comparaison ne recevant pas le traitement teste.", "control group", "grupo de control", "grupo de controlo", "gwoup temwen"),
    ("insu", "technique", "Dispositif empechant de savoir qui recoit quoi.", "blinding", "cegamiento", "cegamento", "ensi"),
    ("pharmacovigilance", "technique", "Surveillance des effets des medicaments apres commercialisation.", "pharmacovigilance", "farmacovigilancia", "farmacovigilancia", "famakovijilans"),
    ("autorisation de mise sur le marche", "technique", "Decision permettant la commercialisation d un medicament.", "marketing authorisation", "autorizacion de comercializacion", "autorizacao de introducao no mercado", "otorizasyon mete sou mache"),
    ("bonnes pratiques de fabrication", "technique", "Referentiel qualite obligatoire en production pharmaceutique.", "good manufacturing practice", "normas de correcta fabricacion", "boas praticas de fabrico", "bon pratik fabrikasyon"),
    ("lot de production", "technique", "Quantite fabriquee dans des conditions homogenes.", "production batch", "lote de produccion", "lote de producao", "lo pwodiksyon"),
    ("tracabilite", "technique", "Capacite a reconstituer l historique d un produit.", "traceability", "trazabilidad", "rastreabilidade", "trasabilite"),
    ("date de peremption", "courant", "Limite au-dela de laquelle le produit ne doit plus etre utilise.", "expiry date", "fecha de caducidad", "data de validade", "dat ekspirasyon"),
    ("chaine du froid", "technique", "Maintien continu d une temperature basse jusqu a l usage.", "cold chain", "cadena de frio", "cadeia de frio", "chèn fredi"),
    ("generique", "courant", "Copie d un medicament dont le brevet est expire.", "generic drug", "medicamento generico", "medicamento generico", "jenerik"),
    ("rupture de stock", "courant", "Indisponibilite temporaire d un medicament.", "stock shortage", "desabastecimiento", "falta de stock", "mank nan stòk"),
]

BTP = [
    ("maitrise d ouvrage", "technique", "Entite qui commande et finance l ouvrage.", "client body", "promotor", "dono de obra", "mètriz douvraj"),
    ("maitrise d oeuvre", "technique", "Entite qui concoit et dirige l execution.", "project supervision", "direccion de obra", "direcao de obra", "mètriz dèv"),
    ("permis de construire", "courant", "Autorisation administrative prealable aux travaux.", "building permit", "licencia de obra", "licenca de construcao", "pèmi konstwi"),
    ("coffrage", "technique", "Moule provisoire recevant le beton frais.", "formwork", "encofrado", "cofragem", "kofraj"),
    ("ferraillage", "technique", "Armature metallique noyee dans le beton.", "rebar assembly", "armadura", "armadura", "feraj"),
    ("corps d etat", "technique", "Specialite technique intervenant sur le chantier.", "trade", "oficio", "especialidade", "kò deta"),
    ("gros oeuvre", "technique", "Ouvrages porteurs assurant la stabilite.", "structural works", "obra gruesa", "estrutura", "gwo zèv"),
    ("second oeuvre", "technique", "Travaux de finition et d equipement.", "fit-out works", "acabados", "acabamentos", "segon zèv"),
    ("metre", "technique", "Quantification des ouvrages a realiser.", "quantity take-off", "medicion", "medicao", "mèt"),
    ("devis quantitatif estimatif", "technique", "Document chiffrant poste par poste les travaux.", "priced bill of quantities", "presupuesto detallado", "orcamento detalhado", "deviz kantitatif"),
    ("reception des travaux", "technique", "Acte par lequel le client accepte l ouvrage.", "handover", "recepcion de obra", "recepcao da obra", "resepsyon travay"),
    ("reserve", "technique", "Defaut releve a la reception et a reprendre.", "snag", "reserva", "reserva", "rezèv"),
    ("plan de prevention", "technique", "Document organisant la securite des intervenants.", "safety plan", "plan de prevencion", "plano de prevencao", "plan prevansyon"),
    ("penalite de retard", "technique", "Somme due en cas de depassement du delai.", "delay penalty", "penalizacion por retraso", "multa por atraso", "penalite reta"),
    ("avenant au marche", "technique", "Modification contractuelle des travaux ou du prix.", "variation order", "modificado", "aditamento", "avnan nan mache"),
    ("intemperies", "courant", "Conditions meteo justifiant l arret du chantier.", "adverse weather", "intemperie", "intemperies", "move tan"),
    ("etre dans les clous", "familier", "Respecter les delais et le budget prevus.", "to be on track", "ir en plazo", "estar nos prazos", "nan limit"),
]

IMMO = [
    ("mandat de vente", "technique", "Contrat confiant la commercialisation a un professionnel.", "sale mandate", "encargo de venta", "mandato de venda", "manda vann"),
    ("compromis de vente", "technique", "Avant-contrat engageant les deux parties.", "preliminary contract", "contrato de arras", "contrato promessa", "konpwomi vann"),
    ("condition suspensive", "technique", "Evenement dont depend la realisation de la vente.", "condition precedent", "condicion suspensiva", "condicao suspensiva", "kondisyon sispansif"),
    ("surface habitable", "technique", "Superficie de plancher utile hors annexes.", "habitable floor area", "superficie habitable", "area habitavel", "sifas abitab"),
    ("diagnostic technique", "technique", "Controle obligatoire de l etat du bien avant vente.", "survey report", "informe tecnico", "relatorio tecnico", "dyagnostik teknik"),
    ("charges de copropriete", "courant", "Depenses communes reparties entre les coproprietaires.", "service charges", "gastos de comunidad", "encargos de condominio", "chaj kopwopriyete"),
    ("bail commercial", "technique", "Location d un local destine a une activite economique.", "commercial lease", "arrendamiento comercial", "arrendamento comercial", "bay komèsyal"),
    ("depot de garantie", "courant", "Somme conservee en garantie des obligations du locataire.", "security deposit", "fianza", "caucao", "depo garanti"),
    ("quittance de loyer", "courant", "Recu attestant le paiement du loyer.", "rent receipt", "recibo de alquiler", "recibo de renda", "kitans lwaye"),
    ("etat des lieux", "technique", "Constat de l etat du logement a l entree et a la sortie.", "condition report", "acta de estado", "vistoria", "eta dè lye"),
    ("vente en etat futur d achevement", "technique", "Achat d un bien a construire, paye par appels de fonds.", "off-plan purchase", "venta sobre plano", "venda na planta", "vant anvan bati"),
    ("foncier", "technique", "Terrain considere comme assiette d un projet.", "land", "suelo", "solo", "fonsye"),
    ("bilan promoteur", "technique", "Tableau de rentabilite d une operation immobiliere.", "developer appraisal", "estudio de viabilidad", "estudo de viabilidade", "bilan pwomotè"),
    ("rendement locatif", "courant", "Loyer annuel rapporte au prix d acquisition.", "rental yield", "rentabilidad del alquiler", "rentabilidade do arrendamento", "randman lokatif"),
    ("vacance locative", "courant", "Periode sans locataire et donc sans loyer.", "rental void", "periodo sin alquilar", "periodo sem renda", "vakans lokatif"),
    ("servitude", "technique", "Charge grevant un bien au profit d un autre.", "easement", "servidumbre", "servidao", "sèvitid"),
    ("faire une offre au prix", "familier", "Proposer exactement le prix demande pour securiser le bien.", "to offer asking price", "ofertar al precio", "oferecer pelo preco pedido", "fè yon òf nan pri"),
]

LOGISTIQUE = [
    ("chaine d approvisionnement", "technique", "Ensemble des flux du fournisseur au client final.", "supply chain", "cadena de suministro", "cadeia de abastecimento", "chèn apwovizyonman"),
    ("taux de service", "technique", "Part des commandes livrees completes et a l heure.", "service level", "nivel de servicio", "nivel de servico", "to sèvis"),
    ("stock de securite", "technique", "Quantite tampon couvrant les aleas de demande.", "safety stock", "stock de seguridad", "stock de seguranca", "stòk sekirite"),
    ("rotation des stocks", "technique", "Nombre de fois ou le stock est renouvele par an.", "inventory turnover", "rotacion de inventario", "rotacao de stock", "rotasyon stòk"),
    ("preparation de commande", "courant", "Prelevement et regroupement des articles commandes.", "order picking", "preparacion de pedidos", "picking", "preparasyon kòmann"),
    ("flux tendu", "technique", "Approvisionnement au plus juste, sans stock dormant.", "just-in-time", "justo a tiempo", "just-in-time", "flo tandi"),
    ("rupture de charge", "technique", "Changement de mode ou de contenant pendant le transport.", "transhipment", "ruptura de carga", "transbordo", "ripti chaj"),
    ("incoterm", "technique", "Regle fixant le partage des frais et des risques.", "incoterm", "incoterm", "incoterm", "enkotèm"),
    ("connaissement", "technique", "Titre de transport maritime et preuve de la marchandise.", "bill of lading", "conocimiento de embarque", "conhecimento de embarque", "konesman"),
    ("declaration en douane", "technique", "Document reglementaire de passage de frontiere.", "customs declaration", "declaracion aduanera", "declaracao aduaneira", "deklarasyon ladwàn"),
    ("nomenclature douaniere", "technique", "Codification determinant les droits applicables.", "tariff classification", "nomenclatura arancelaria", "nomenclatura pautal", "nomanklati ladwàn"),
    ("groupage", "technique", "Regroupement de plusieurs envois dans un meme vehicule.", "groupage", "grupaje", "grupagem", "gwoupaj"),
    ("dernier kilometre", "courant", "Segment final de livraison jusqu au destinataire.", "last mile", "ultima milla", "ultima milha", "dènye kilomèt"),
    ("tournee de livraison", "courant", "Sequence optimisee des points de livraison.", "delivery round", "ruta de reparto", "rota de entrega", "tounen livrezon"),
    ("tachygraphe", "technique", "Appareil enregistrant les temps de conduite.", "tachograph", "tacografo", "tacografo", "takigraf"),
    ("inventaire tournant", "technique", "Comptage partiel et regulier des references.", "cycle counting", "inventario ciclico", "inventario rotativo", "envantè k ap vire"),
    ("casser une tournee", "familier", "Reorganiser en urgence un circuit de livraison.", "to break a round", "romper una ruta", "quebrar uma rota", "kase yon tounen"),
]

MARITIME = [
    ("armateur", "technique", "Proprietaire ou exploitant commercial du navire.", "shipowner", "armador", "armador", "amatè"),
    ("affretement", "technique", "Location d un navire ou d une partie de sa capacite.", "chartering", "fletamento", "afretamento", "afretman"),
    ("manifeste", "technique", "Liste officielle des marchandises embarquees.", "cargo manifest", "manifiesto de carga", "manifesto de carga", "manifès"),
    ("tirant d eau", "technique", "Hauteur immergee de la coque.", "draught", "calado", "calado", "tiran dlo"),
    ("jauge brute", "technique", "Mesure du volume interieur du navire.", "gross tonnage", "arqueo bruto", "arqueacao bruta", "joj brit"),
    ("quart", "technique", "Periode de service continue a bord.", "watch", "guardia", "quarto", "ka"),
    ("routage meteo", "technique", "Choix de route tenant compte des conditions marines.", "weather routing", "derrota meteorologica", "roteamento meteorologico", "woutaj meteyo"),
    ("escale", "courant", "Arret du navire dans un port.", "port call", "escala", "escala", "eskal"),
    ("pilotage portuaire", "technique", "Assistance obligatoire a l entree d un port.", "harbour pilotage", "practicaje", "pilotagem", "pilotaj pò"),
    ("marnage", "technique", "Amplitude entre basse et haute mer.", "tidal range", "carrera de marea", "amplitude de mare", "manaj"),
    ("engin de peche", "technique", "Materiel utilise pour capturer le poisson.", "fishing gear", "arte de pesca", "aparelho de pesca", "zouti lapèch"),
    ("quota de peche", "technique", "Volume maximal autorise par espece et par zone.", "fishing quota", "cuota de pesca", "quota de pesca", "kota lapèch"),
    ("maree", "courant", "Sortie en mer d un bateau de peche, de son depart a son retour.", "fishing trip", "marea", "mare", "mare"),
    ("criee", "courant", "Vente aux encheres du poisson debarque.", "fish auction", "lonja", "lota", "kriye"),
    ("prise accessoire", "technique", "Capture non ciblee par l engin utilise.", "bycatch", "captura accesoria", "captura acessoria", "priz akseswa"),
    ("gros temps", "familier", "Conditions de mer severes.", "heavy weather", "mal tiempo", "mau tempo", "gwo tan"),
]

AERO = [
    ("plan de vol", "technique", "Document decrivant la route et les parametres prevus.", "flight plan", "plan de vuelo", "plano de voo", "plan vòl"),
    ("clairance", "technique", "Autorisation donnee par le controle aerien.", "clearance", "autorizacion", "autorizacao", "klerans"),
    ("separation", "technique", "Distance minimale imposee entre deux aeronefs.", "separation", "separacion", "separacao", "separasyon"),
    ("liste de verification", "technique", "Suite de controles obligatoires avant une phase de vol.", "checklist", "lista de comprobacion", "lista de verificacao", "lis verifikasyon"),
    ("masse et centrage", "technique", "Calcul garantissant l equilibre de l aeronef.", "weight and balance", "peso y equilibrado", "peso e centragem", "mas ak santraj"),
    ("navigabilite", "technique", "Aptitude technique de l aeronef a voler en securite.", "airworthiness", "aeronavegabilidad", "aeronavegabilidade", "navigabilite"),
    ("potentiel restant", "technique", "Heures de vol disponibles avant visite obligatoire.", "remaining life", "potencial restante", "potencial restante", "potansyèl ki rete"),
    ("visite de maintenance", "technique", "Intervention programmee selon un referentiel.", "maintenance check", "revision programada", "revisao programada", "vizit antretyen"),
    ("creneau de decollage", "courant", "Plage horaire attribuee pour partir.", "departure slot", "franja de despegue", "slot de partida", "kreno dekolaj"),
    ("deroutement", "technique", "Changement de destination en cours de vol.", "diversion", "desvio", "divergencia", "derutman"),
    ("turbulence de sillage", "technique", "Perturbation laissee par un aeronef precedent.", "wake turbulence", "turbulencia de estela", "turbulencia de esteira", "tibilans siyaj"),
    ("compte rendu d incident", "technique", "Signalement documente d un evenement de securite.", "incident report", "informe de incidente", "relatorio de incidente", "rapò ensidan"),
    ("tour de piste", "courant", "Circuit effectue autour de l aerodrome.", "traffic pattern", "circuito de trafico", "circuito de trafego", "tou pis"),
    ("retard au roulage", "courant", "Attente avant l alignement sur la piste.", "taxi delay", "retraso en rodaje", "atraso em taxi", "reta nan woulaj"),
    ("etre en attente", "familier", "Tourner en circuit en attendant l autorisation.", "to be in holding", "estar en espera", "estar em espera", "nan tann"),
]

ENERGIE = [
    ("puissance installee", "technique", "Capacite maximale de production d une installation.", "installed capacity", "potencia instalada", "potencia instalada", "pisans enstale"),
    ("facteur de charge", "technique", "Production reelle rapportee a la production maximale possible.", "capacity factor", "factor de carga", "fator de carga", "faktè chaj"),
    ("intermittence", "technique", "Variabilite de production des sources renouvelables.", "intermittency", "intermitencia", "intermitencia", "entèmitans"),
    ("effacement de consommation", "technique", "Reduction volontaire de la demande en periode de pointe.", "demand response", "respuesta de demanda", "resposta da procura", "efasman konsomasyon"),
    ("raccordement au reseau", "technique", "Connexion physique d une installation au reseau electrique.", "grid connection", "conexion a la red", "ligacao a rede", "rakòdman nan rezo"),
    ("mix energetique", "courant", "Repartition des sources dans la production totale.", "energy mix", "mix energetico", "mix energetico", "mix enèjetik"),
    ("bilan carbone", "technique", "Comptabilisation des emissions de gaz a effet de serre.", "carbon footprint", "huella de carbono", "pegada de carbono", "bilan kabòn"),
    ("etude d impact", "technique", "Evaluation des effets d un projet sur l environnement.", "environmental impact assessment", "evaluacion de impacto ambiental", "avaliacao de impacto ambiental", "etid enpak"),
    ("mesure compensatoire", "technique", "Action corrigeant un dommage environnemental residuel.", "offset measure", "medida compensatoria", "medida compensatoria", "mezi konpansatwa"),
    ("sobriete energetique", "courant", "Reduction des usages avant recours a la technique.", "energy sufficiency", "sobriedad energetica", "sobriedade energetica", "sobriyete enèjetik"),
    ("rendement de conversion", "technique", "Part de l energie entrante restituee en energie utile.", "conversion efficiency", "rendimiento de conversion", "rendimento de conversao", "randman konvèsyon"),
    ("precarite energetique", "courant", "Difficulte a couvrir ses besoins essentiels en energie.", "energy poverty", "pobreza energetica", "pobreza energetica", "prekarite enèjetik"),
    ("economie circulaire", "courant", "Modele visant a reemployer et recycler les ressources.", "circular economy", "economia circular", "economia circular", "ekonomi sikilè"),
    ("sequestration du carbone", "technique", "Stockage durable du carbone hors de l atmosphere.", "carbon sequestration", "secuestro de carbono", "sequestro de carbono", "sekèstrasyon kabòn"),
    ("biodiversite", "courant", "Diversite des especes et des milieux naturels.", "biodiversity", "biodiversidad", "biodiversidade", "biyodivèsite"),
    ("transition juste", "courant", "Accompagnement social des mutations ecologiques.", "just transition", "transicion justa", "transicao justa", "tranzisyon jis"),
]

AGRO = [
    ("itineraire technique", "technique", "Suite des operations culturales sur une parcelle.", "crop management sequence", "itinerario tecnico", "itinerario tecnico", "itinerè teknik"),
    ("assolement", "technique", "Repartition des cultures entre les parcelles.", "crop allocation", "distribucion de cultivos", "distribuicao de culturas", "asolman"),
    ("rotation culturale", "technique", "Succession ordonnee des cultures dans le temps.", "crop rotation", "rotacion de cultivos", "rotacao de culturas", "rotasyon kilti"),
    ("intrant", "technique", "Produit apporte a la culture, engrais ou semence.", "farm input", "insumo", "insumo", "antran"),
    ("ravageur", "technique", "Organisme nuisible attaquant la culture.", "crop pest", "plaga", "praga", "ravajè"),
    ("auxiliaire de culture", "technique", "Organisme utile regulant les ravageurs.", "beneficial organism", "fauna auxiliar", "inimigo natural", "oksilyè kilti"),
    ("rendement a l hectare", "technique", "Quantite recoltee par unite de surface.", "yield per hectare", "rendimiento por hectarea", "rendimento por hectare", "randman pa ekta"),
    ("analyse de sol", "technique", "Mesure de la composition et de la fertilite du sol.", "soil analysis", "analisis de suelo", "analise de solo", "analiz tè"),
    ("agroecologie", "courant", "Pratiques agricoles s appuyant sur les regulations naturelles.", "agroecology", "agroecologia", "agroecologia", "agwoekoloji"),
    ("cheptel", "technique", "Ensemble des animaux d une exploitation.", "livestock herd", "cabana ganadera", "efetivo pecuario", "chèptèl"),
    ("ration alimentaire", "technique", "Composition journaliere de l alimentation animale.", "feed ration", "racion alimentaria", "racao alimentar", "rasyon manje"),
    ("prophylaxie", "technique", "Ensemble des mesures preventives sanitaires.", "disease prevention", "profilaxis", "profilaxia", "pwofilaksi"),
    ("analyse des dangers", "technique", "Identification des risques sanitaires d un procede.", "hazard analysis", "analisis de peligros", "analise de perigos", "analiz danje"),
    ("point critique", "technique", "Etape ou un controle est indispensable a la securite sanitaire.", "critical control point", "punto critico de control", "ponto critico de controlo", "pwen kritik"),
    ("date limite de consommation", "courant", "Date au-dela de laquelle le produit devient dangereux.", "use-by date", "fecha de caducidad", "data limite de consumo", "dat limit konsomasyon"),
    ("circuit court", "courant", "Vente directe ou avec un seul intermediaire.", "short supply chain", "circuito corto", "circuito curto", "sikwi kout"),
    ("faire la saison", "familier", "Travailler pendant la periode de recolte.", "to work the season", "hacer la campana", "fazer a campanha", "fè sezon an"),
]

INDUSTRIE = [
    ("gamme de fabrication", "technique", "Suite ordonnee des operations de production.", "routing sheet", "hoja de ruta", "roteiro de fabrico", "gam fabrikasyon"),
    ("temps de cycle", "technique", "Duree necessaire pour produire une unite.", "cycle time", "tiempo de ciclo", "tempo de ciclo", "tan sik"),
    ("cadence", "courant", "Nombre de pieces produites par unite de temps.", "throughput rate", "cadencia", "cadencia", "kadans"),
    ("taux de rebut", "technique", "Part des pieces non conformes dans la production.", "scrap rate", "tasa de rechazo", "taxa de rejeicao", "to rebi"),
    ("non-conformite", "technique", "Ecart constate par rapport a une exigence.", "non-conformity", "no conformidad", "nao conformidade", "non-konfòmite"),
    ("action corrective", "technique", "Mesure supprimant la cause d un defaut.", "corrective action", "accion correctiva", "acao corretiva", "aksyon korektif"),
    ("analyse des causes racines", "technique", "Recherche de l origine profonde d un probleme.", "root cause analysis", "analisis de causa raiz", "analise de causa raiz", "analiz kòz rasin"),
    ("maintenance preventive", "technique", "Intervention planifiee avant apparition de la panne.", "preventive maintenance", "mantenimiento preventivo", "manutencao preventiva", "antretyen prevantif"),
    ("maintenance curative", "technique", "Reparation apres defaillance constatee.", "corrective maintenance", "mantenimiento correctivo", "manutencao corretiva", "antretyen kiratif"),
    ("temps d arret", "courant", "Periode pendant laquelle la ligne ne produit pas.", "downtime", "tiempo de parada", "tempo de parada", "tan rete"),
    ("amelioration continue", "courant", "Demarche de progres par petits pas reguliers.", "continuous improvement", "mejora continua", "melhoria continua", "amelyorasyon kontinyèl"),
    ("cinq pourquoi", "technique", "Technique d interrogation successive pour remonter a la cause.", "five whys", "cinco por que", "cinco porques", "senk poukisa"),
    ("gaspillage", "courant", "Activite qui consomme des ressources sans creer de valeur.", "waste", "desperdicio", "desperdicio", "gaspiyay"),
    ("implantation d atelier", "technique", "Disposition des machines et des flux dans l espace.", "plant layout", "distribucion en planta", "implantacao fabril", "enplantasyon atelye"),
    ("reglage machine", "courant", "Ajustement des parametres avant lancement de serie.", "machine setup", "ajuste de maquina", "ajuste de maquina", "reglaj machin"),
    ("qualification de soudure", "technique", "Validation d un mode operatoire de soudage.", "weld qualification", "homologacion de soldadura", "qualificacao de soldadura", "kalifikasyon soudi"),
    ("ligne a l arret", "familier", "Production interrompue, souvent par panne.", "line is down", "linea parada", "linha parada", "liy la rete"),
]

if __name__ == "__main__":
    print("[SYNTHEA] Lexiques sectoriels - serie B")
    write_sector("11_lex_telecoms_reseaux.csv", "telecoms_reseaux", "MET049;MET050", TELECOM)
    write_sector("12_lex_sante_medical.csv", "sante_medical", "MET051;MET052;MET053;MET054;MET055", SANTE)
    write_sector("13_lex_pharmacie_biotech.csv", "pharmacie_biotech", "MET056;MET057;MET058;MET059", PHARMA)
    write_sector("14_lex_batiment_btp.csv", "batiment_btp", "MET060;MET061;MET062;MET063;MET064;MET065;MET066", BTP)
    write_sector("15_lex_immobilier.csv", "immobilier", "MET067;MET068;MET069", IMMO)
    write_sector("16_lex_logistique_transport.csv", "logistique_transport", "MET070;MET071;MET072;MET073", LOGISTIQUE)
    write_sector("17_lex_maritime_peche.csv", "maritime_peche", "MET074;MET075", MARITIME)
    write_sector("18_lex_aeronautique.csv", "aeronautique", "MET076;MET077;MET078", AERO)
    write_sector("19_lex_energie_environnement.csv", "energie_environnement", "MET079;MET080", ENERGIE)
    write_sector("20_lex_agriculture_agroalimentaire.csv", "agriculture_agroalimentaire", "MET086;MET087;MET088;MET089", AGRO)
    write_sector("21_lex_industrie_mecanique.csv", "industrie_mecanique", "MET081;MET082;MET083;MET084;MET085", INDUSTRIE)
