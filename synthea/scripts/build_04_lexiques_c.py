"""SYNTHEA - Lexiques sectoriels (serie C) : commerce, marketing, RH, education,
hotellerie, medias, culture, sport, public, politique, startup, ONG, securite,
mode, automobile, artisanat."""
from __future__ import annotations

from _csvutil import write_sector

COMMERCE = [
    ("lineaire", "technique", "Longueur de presentation accordee a un produit en rayon.", "shelf space", "lineal", "linear", "lineyè"),
    ("facing", "technique", "Nombre de faces visibles d un produit en rayon.", "facing", "frente de lineal", "frente de prateleira", "fasing"),
    ("demarque inconnue", "technique", "Perte de stock sans cause identifiee, vol compris.", "unknown shrinkage", "desconocido", "quebra desconhecida", "demak enkoni"),
    ("casse", "courant", "Marchandise detruite ou perimee, retiree de la vente.", "wastage", "merma", "quebra", "kas"),
    ("panier moyen", "technique", "Montant moyen depense par transaction.", "average basket", "ticket medio", "ticket medio", "panyen mwayen"),
    ("taux de conversion", "technique", "Part des visiteurs qui achetent.", "conversion rate", "tasa de conversion", "taxa de conversao", "to konvèsyon"),
    ("marge arriere", "technique", "Remunerations obtenues du fournisseur hors prix d achat.", "back margin", "margen trasero", "margem traseira", "marj dèyè"),
    ("appel d offres", "technique", "Procedure de mise en concurrence des fournisseurs.", "tender", "licitacion", "concurso", "apèl dòf"),
    ("referencement fournisseur", "technique", "Admission d un fournisseur au panel autorise.", "supplier listing", "homologacion de proveedor", "homologacao de fornecedor", "referansman founisè"),
    ("rupture en rayon", "courant", "Absence du produit a l emplacement prevu.", "out of stock", "rotura de stock", "rutura de stock", "ripti nan reyon"),
    ("tete de gondole", "courant", "Emplacement promotionnel en bout de rayon.", "end cap", "cabecera de gondola", "ponta de gondola", "tèt gondòl"),
    ("argumentaire de vente", "courant", "Discours structure justifiant l achat.", "sales pitch", "argumentario", "argumentario", "agimantè vant"),
    ("service apres-vente", "courant", "Prise en charge du produit apres l achat.", "after-sales service", "servicio posventa", "servico pos-venda", "sèvis apre vant"),
    ("fiche produit", "courant", "Description commerciale et technique d un article en ligne.", "product page", "ficha de producto", "ficha de produto", "fich pwodwi"),
    ("abandon de panier", "technique", "Visite se terminant sans finaliser la commande.", "cart abandonment", "abandono de carrito", "abandono de carrinho", "abandon panyen"),
    ("faire du chiffre", "familier", "Realiser du volume de ventes.", "to drive sales", "hacer caja", "fazer caixa", "fè chif"),
]

MARKETING = [
    ("positionnement", "technique", "Place distinctive occupee dans l esprit du client.", "positioning", "posicionamiento", "posicionamento", "pozisyonman"),
    ("proposition de valeur", "technique", "Benefice central promis a un segment precis.", "value proposition", "propuesta de valor", "proposta de valor", "pwopozisyon valè"),
    ("cible", "courant", "Groupe de clients prioritairement visee.", "target audience", "publico objetivo", "publico-alvo", "sib"),
    ("persona", "technique", "Portrait type d un client representatif.", "persona", "perfil tipo", "persona", "pèsona"),
    ("parcours client", "technique", "Suite des interactions du client avec la marque.", "customer journey", "viaje del cliente", "jornada do cliente", "pakou kliyan"),
    ("point de contact", "technique", "Occasion d interaction entre la marque et le public.", "touchpoint", "punto de contacto", "ponto de contacto", "pwen kontak"),
    ("notoriete", "technique", "Part du public capable de citer la marque.", "brand awareness", "notoriedad", "notoriedade", "notoriyete"),
    ("retombee media", "technique", "Mention obtenue dans la presse ou en ligne.", "media coverage", "repercusion mediatica", "retorno mediatico", "retonbe medya"),
    ("message cle", "courant", "Idee centrale a faire retenir du public.", "key message", "mensaje clave", "mensagem-chave", "mesaj kle"),
    ("plan media", "technique", "Repartition planifiee des achats d espace.", "media plan", "plan de medios", "plano de meios", "plan medya"),
    ("ligne editoriale", "courant", "Regles de ton et de sujets d une publication.", "editorial line", "linea editorial", "linha editorial", "liy editoryal"),
    ("taux d engagement", "technique", "Interactions rapportees a l audience atteinte.", "engagement rate", "tasa de interaccion", "taxa de interacao", "to angajman"),
    ("charte graphique", "technique", "Regles d usage de l identite visuelle.", "brand guidelines", "manual de marca", "manual de marca", "chat grafik"),
    ("maquette", "courant", "Representation visuelle avant production finale.", "mockup", "maqueta", "maquete", "maket"),
    ("appel a l action", "technique", "Invitation explicite a realiser une etape.", "call to action", "llamada a la accion", "chamada para acao", "apèl a aksyon"),
    ("faire du bruit", "familier", "Obtenir une forte visibilite rapidement.", "to make noise", "hacer ruido", "fazer barulho", "fè bri"),
]

RH = [
    ("fiche de poste", "technique", "Document decrivant missions, competences et rattachement.", "job description", "descripcion del puesto", "descricao de funcao", "fich pòs"),
    ("sourcing", "technique", "Recherche active de candidats non declares.", "sourcing", "sourcing", "sourcing", "sousing"),
    ("vivier de candidats", "courant", "Reserve de profils interessants deja identifies.", "talent pool", "cantera de candidatos", "banco de candidatos", "rezèv kandida"),
    ("entretien structure", "technique", "Entretien conduit avec une grille identique pour tous.", "structured interview", "entrevista estructurada", "entrevista estruturada", "entretyen estriktire"),
    ("periode d essai", "technique", "Phase initiale permettant la rupture simplifiee du contrat.", "probation period", "periodo de prueba", "periodo experimental", "peryòd esè"),
    ("integration", "courant", "Accompagnement du nouvel arrivant dans ses premieres semaines.", "onboarding", "incorporacion", "integracao", "entegrasyon"),
    ("entretien annuel", "courant", "Echange formel sur la performance et les objectifs.", "annual review", "evaluacion anual", "avaliacao anual", "entretyen anyèl"),
    ("gestion previsionnelle des emplois", "technique", "Anticipation des besoins en competences.", "workforce planning", "planificacion de plantilla", "planeamento de efetivos", "jesyon prevwa anplwa"),
    ("masse salariale", "technique", "Total des remunerations et charges associees.", "payroll cost", "masa salarial", "massa salarial", "mas salaryal"),
    ("variable de paie", "technique", "Element de remuneration changeant chaque mois.", "payroll variable", "variable de nomina", "variavel de salario", "varyab pay"),
    ("dialogue social", "courant", "Relations organisees avec les representants du personnel.", "social dialogue", "dialogo social", "dialogo social", "dyalòg sosyal"),
    ("plan de developpement des competences", "technique", "Programme de formation annuel de l entreprise.", "training plan", "plan de formacion", "plano de formacao", "plan devlopman konpetans"),
    ("mobilite interne", "courant", "Changement de poste au sein de l organisation.", "internal mobility", "movilidad interna", "mobilidade interna", "mobilite entèn"),
    ("turnover", "courant", "Taux de rotation des effectifs.", "staff turnover", "rotacion de personal", "rotatividade", "tounòvè"),
    ("marque employeur", "technique", "Image de l entreprise aupres des candidats.", "employer brand", "marca empleadora", "marca empregadora", "mak anplwayè"),
    ("passer en CDI", "familier", "Etre embauche en contrat a duree indeterminee.", "to go permanent", "pasar a fijo", "passar a efetivo", "pase an CDI"),
]

EDUCATION = [
    ("referentiel de competences", "technique", "Liste structuree des acquis attendus.", "competency framework", "marco de competencias", "referencial de competencias", "referansyèl konpetans"),
    ("objectif pedagogique", "technique", "Resultat d apprentissage vise et observable.", "learning objective", "objetivo de aprendizaje", "objetivo de aprendizagem", "objektif pedagojik"),
    ("progression pedagogique", "technique", "Ordonnancement des apprentissages dans le temps.", "learning progression", "progresion didactica", "progressao pedagogica", "pwogresyon pedagojik"),
    ("sequence", "technique", "Ensemble coherent de seances autour d un objectif.", "teaching sequence", "secuencia didactica", "sequencia didatica", "sekans"),
    ("differenciation", "technique", "Adaptation des activites aux besoins de chaque apprenant.", "differentiation", "diferenciacion", "diferenciacao", "diferansyasyon"),
    ("evaluation formative", "technique", "Evaluation en cours d apprentissage pour reguler.", "formative assessment", "evaluacion formativa", "avaliacao formativa", "evalyasyon fòmatif"),
    ("evaluation sommative", "technique", "Evaluation finale certifiant un niveau atteint.", "summative assessment", "evaluacion sumativa", "avaliacao sumativa", "evalyasyon somatif"),
    ("grille criteriee", "technique", "Outil de notation detaillant les criteres.", "scoring rubric", "rubrica", "rubrica", "griy kritè"),
    ("mise en situation", "technique", "Exercice reproduisant une situation professionnelle.", "role play exercise", "simulacion practica", "simulacao pratica", "mete nan sitiyasyon"),
    ("classe inversee", "courant", "Apport theorique en amont, pratique en presence.", "flipped classroom", "clase invertida", "sala de aula invertida", "klas envèse"),
    ("remediation", "technique", "Dispositif de reprise des notions non acquises.", "remedial support", "refuerzo", "apoio de recuperacao", "remedyasyon"),
    ("plateforme de formation", "courant", "Outil en ligne hebergeant parcours et ressources.", "learning management system", "plataforma de formacion", "plataforma de formacao", "platfòm fòmasyon"),
    ("granule pedagogique", "technique", "Unite minimale de contenu reutilisable.", "learning object", "objeto de aprendizaje", "objeto de aprendizagem", "granil pedagojik"),
    ("acquis de l experience", "technique", "Competences reconnues hors parcours scolaire.", "prior learning", "experiencia acreditada", "experiencia acreditada", "akiz eksperyans"),
    ("decrochage", "courant", "Desengagement progressif conduisant a l abandon.", "dropping out", "abandono escolar", "abandono escolar", "dekwochaj"),
    ("faire passer le message", "familier", "Reussir a rendre une notion comprehensible.", "to get it across", "hacer llegar el mensaje", "fazer passar a mensagem", "fè mesaj la pase"),
]

HOTEL = [
    ("taux d occupation", "technique", "Part des chambres vendues sur les chambres disponibles.", "occupancy rate", "tasa de ocupacion", "taxa de ocupacao", "to okipasyon"),
    ("prix moyen par chambre", "technique", "Recette moyenne par chambre louee.", "average daily rate", "precio medio por habitacion", "preco medio por quarto", "pri mwayen pa chanm"),
    ("revenu par chambre disponible", "technique", "Indicateur combinant occupation et prix moyen.", "revenue per available room", "ingreso por habitacion disponible", "receita por quarto disponivel", "revni pa chanm disponib"),
    ("surreservation", "technique", "Vente volontaire au-dela de la capacite reelle.", "overbooking", "sobreventa", "overbooking", "sireservasyon"),
    ("non-presentation", "technique", "Client reserve qui ne se presente pas.", "no-show", "no show", "no-show", "pa prezante"),
    ("montee en gamme", "courant", "Vente d une prestation superieure au moment de l accueil.", "upselling", "venta cruzada superior", "upselling", "monte an gam"),
    ("mise en place", "technique", "Preparation des postes avant le service.", "mise en place", "puesta a punto", "mise en place", "mete an plas"),
    ("fiche technique de plat", "technique", "Document fixant grammages, cout et dressage.", "recipe card", "ficha tecnica de plato", "ficha tecnica de prato", "fich teknik pla"),
    ("cout matiere", "technique", "Part du cout des denrees dans le prix de vente.", "food cost", "coste de materia", "custo de materia", "kou matyè"),
    ("coup de feu", "familier", "Pic d activite au coeur du service.", "rush", "hora punta", "pico de servico", "kou dife"),
    ("couvert", "courant", "Unite comptant un client servi a table.", "cover", "cubierto", "couvert", "kouvè"),
    ("circuit touristique", "courant", "Itineraire organise de visites.", "tour itinerary", "circuito turistico", "circuito turistico", "sikwi touris"),
    ("saisonnalite", "technique", "Variation reguliere de l activite selon la periode.", "seasonality", "estacionalidad", "sazonalidade", "sezonalite"),
    ("capacite d accueil", "technique", "Nombre maximal de personnes pouvant etre recues.", "carrying capacity", "capacidad de acogida", "capacidade de acolhimento", "kapasite akèy"),
    ("avis client", "courant", "Appreciation publiee par un client apres son sejour.", "guest review", "resena de cliente", "avaliacao de cliente", "avi kliyan"),
    ("etre complet", "familier", "Ne plus avoir de disponibilite a la vente.", "to be fully booked", "estar completo", "estar lotado", "konplè"),
]

MEDIA = [
    ("angle", "technique", "Point de vue retenu pour traiter un sujet.", "angle", "enfoque", "angulo", "ang"),
    ("accroche", "technique", "Premiere phrase destinee a capter l attention.", "lead", "entradilla", "lead", "akroch"),
    ("chapeau", "technique", "Court texte introductif resumant l essentiel.", "standfirst", "sumario", "antetitulo", "chapo"),
    ("source", "courant", "Personne ou document a l origine d une information.", "source", "fuente", "fonte", "sous"),
    ("recoupement", "technique", "Verification d une information par plusieurs sources.", "cross-checking", "contrastacion", "verificacao cruzada", "rekoupman"),
    ("off", "technique", "Information communiquee sans attribution possible.", "off the record", "off the record", "off", "òf"),
    ("embargo", "technique", "Interdiction de publier avant une date convenue.", "embargo", "embargo", "embargo", "anbago"),
    ("bouclage", "courant", "Phase finale avant impression ou diffusion.", "deadline close", "cierre de edicion", "fecho de edicao", "bouklaj"),
    ("une", "courant", "Page de couverture d un journal.", "front page", "portada", "primeira pagina", "paj devan"),
    ("brut", "technique", "Images ou sons non montes.", "rushes", "material bruto", "material bruto", "brit"),
    ("montage", "courant", "Assemblage ordonne des sequences.", "editing", "montaje", "montagem", "montaj"),
    ("plateau", "courant", "Espace de tournage ou d emission.", "studio floor", "plato", "estudio", "plato"),
    ("communique de presse", "technique", "Document officiel adresse aux redactions.", "press release", "comunicado de prensa", "comunicado de imprensa", "kominike laprès"),
    ("mediatraining", "courant", "Preparation d un porte-parole a l interview.", "media training", "media training", "media training", "medyatrening"),
    ("droit de reponse", "technique", "Faculte pour une personne citee de faire publier sa reponse.", "right of reply", "derecho de replica", "direito de resposta", "dwa repons"),
    ("faire la une", "familier", "Occuper la place principale de l actualite.", "to make headlines", "ser portada", "ser manchete", "fè paj devan"),
]

CULTURE = [
    ("fiche technique", "technique", "Document decrivant les besoins scenographiques et techniques.", "technical rider", "ficha tecnica", "ficha tecnica", "fich teknik"),
    ("conduite", "technique", "Document minute par minute des effets d un spectacle.", "cue sheet", "guion tecnico", "guiao tecnico", "kondwit"),
    ("raccord", "technique", "Reprise partielle pour ajuster un passage.", "touch-up rehearsal", "repaso", "ensaio de ajuste", "rakò"),
    ("residence de creation", "courant", "Periode d accueil d une equipe pour creer une oeuvre.", "creative residency", "residencia de creacion", "residencia de criacao", "rezidans kreyasyon"),
    ("diffusion", "courant", "Circulation d un spectacle dans plusieurs lieux.", "touring", "distribucion", "circulacao", "difizyon"),
    ("cachet", "courant", "Remuneration d un artiste pour une prestation.", "performance fee", "cache", "cache", "kache"),
    ("coproduction", "technique", "Financement partage entre plusieurs structures.", "co-production", "coproduccion", "coproducao", "kopwodiksyon"),
    ("mediation culturelle", "technique", "Actions facilitant la rencontre entre oeuvre et public.", "cultural mediation", "mediacion cultural", "mediacao cultural", "medyasyon kiltirèl"),
    ("scenographie", "technique", "Conception de l espace scenique.", "stage design", "escenografia", "cenografia", "senografi"),
    ("regie", "courant", "Poste de pilotage technique du spectacle.", "control booth", "cabina tecnica", "regia", "reji"),
    ("jauge", "technique", "Nombre de spectateurs que peut accueillir la salle.", "venue capacity", "aforo", "lotacao", "joj"),
    ("billetterie", "courant", "Systeme de vente et de controle des entrees.", "ticketing", "taquilla", "bilheteira", "biyetri"),
    ("droits d auteur", "technique", "Droits patrimoniaux et moraux du createur.", "copyright", "derechos de autor", "direitos de autor", "dwa otè"),
    ("patrimoine immateriel", "technique", "Pratiques et savoir-faire transmis au sein d une communaute.", "intangible heritage", "patrimonio inmaterial", "patrimonio imaterial", "patrimwàn imateryèl"),
    ("faire salle comble", "familier", "Remplir entierement la salle.", "to sell out", "llenar la sala", "esgotar a sala", "fè sal la plen"),
]

SPORT = [
    ("charge d entrainement", "technique", "Volume et intensite cumules du travail realise.", "training load", "carga de entrenamiento", "carga de treino", "chaj antrènman"),
    ("periodisation", "technique", "Organisation du calendrier d entrainement par cycles.", "periodisation", "periodizacion", "periodizacao", "peryodizasyon"),
    ("surcompensation", "technique", "Gain de performance obtenu apres recuperation.", "supercompensation", "supercompensacion", "supercompensacao", "sikonpansasyon"),
    ("recuperation active", "technique", "Effort leger favorisant le retour a l etat de base.", "active recovery", "recuperacion activa", "recuperacao ativa", "rekiperasyon aktif"),
    ("preparation physique generale", "technique", "Travail de base avant la specialisation.", "general conditioning", "preparacion fisica general", "preparacao fisica geral", "preparasyon fizik jeneral"),
    ("vitesse maximale aerobie", "technique", "Allure a laquelle la consommation d oxygene est maximale.", "maximal aerobic speed", "velocidad aerobica maxima", "velocidade aerobia maxima", "vitès maksimal aerobi"),
    ("seance a haute intensite", "courant", "Entrainement fractionne court et exigeant.", "high intensity session", "sesion de alta intensidad", "sessao de alta intensidade", "seyans gwo entansite"),
    ("tactique", "courant", "Organisation collective choisie pour un match.", "tactics", "tactica", "tatica", "taktik"),
    ("effectif", "courant", "Ensemble des joueurs disponibles.", "squad", "plantilla", "plantel", "efektif"),
    ("blessure musculaire", "courant", "Lesion limitant la pratique sportive.", "muscle injury", "lesion muscular", "lesao muscular", "blesi miskilè"),
    ("retour au jeu", "technique", "Processus encadre de reprise apres blessure.", "return to play", "vuelta a la competicion", "regresso a competicao", "retou nan jwèt"),
    ("detection", "courant", "Repérage de jeunes a fort potentiel.", "talent identification", "deteccion de talento", "detecao de talento", "deteksyon"),
    ("mental de competiteur", "courant", "Capacite a performer sous pression.", "competitive mindset", "mentalidad competitiva", "mentalidade competitiva", "mantal konpetitè"),
    ("fair-play", "courant", "Respect de l adversaire et des regles.", "fair play", "juego limpio", "fair play", "fè-plè"),
    ("etre dans le dur", "familier", "Traverser une phase de difficulte physique ou de resultats.", "to be struggling", "estar en horas bajas", "estar numa fase dificil", "nan di a"),
]

PUBLIC = [
    ("deliberation", "technique", "Decision formelle prise par une assemblee locale.", "council resolution", "acuerdo plenario", "deliberacao", "deliberasyon"),
    ("arrete", "technique", "Decision executoire prise par une autorite administrative.", "administrative order", "resolucion", "despacho", "arete"),
    ("marche public", "technique", "Contrat d achat passe par une personne publique.", "public procurement", "contrato publico", "contrato publico", "mache piblik"),
    ("subvention", "courant", "Aide financiere accordee a un tiers pour un projet.", "grant", "subvencion", "subsidio", "sibvansyon"),
    ("service public", "courant", "Activite d interet general assuree sous controle public.", "public service", "servicio publico", "servico publico", "sèvis piblik"),
    ("interet general", "technique", "Finalite collective justifiant l action publique.", "public interest", "interes general", "interesse publico", "enterè jeneral"),
    ("note de synthese", "technique", "Document court presentant un dossier et des options.", "briefing note", "nota de sintesis", "nota de sintese", "nòt sentèz"),
    ("arbitrage", "courant", "Choix tranche entre plusieurs options par l autorite.", "decision arbitration", "arbitraje", "arbitragem", "abitraj"),
    ("instruction du dossier", "technique", "Examen administratif prealable a la decision.", "case processing", "instruccion del expediente", "instrucao do processo", "enstriksyon dosye"),
    ("recours gracieux", "technique", "Demande de reexamen adressee a l autorite elle-meme.", "administrative appeal", "recurso de reposicion", "reclamacao graciosa", "rekou grasye"),
    ("transparence", "courant", "Acces du public aux informations administratives.", "transparency", "transparencia", "transparencia", "transparans"),
    ("redevabilite", "technique", "Obligation de rendre compte de son action.", "accountability", "rendicion de cuentas", "responsabilizacao", "redevabilite"),
    ("evaluation des politiques publiques", "technique", "Mesure des effets reels d une politique.", "policy evaluation", "evaluacion de politicas", "avaliacao de politicas", "evalyasyon politik piblik"),
    ("etat civil", "courant", "Service enregistrant naissances, mariages et deces.", "civil registry", "registro civil", "registo civil", "eta sivil"),
    ("continuite du service", "technique", "Principe de fonctionnement sans interruption.", "service continuity", "continuidad del servicio", "continuidade do servico", "kontinwite sèvis"),
    ("monter un dossier", "familier", "Constituer l ensemble des pieces d une demande.", "to build a case file", "preparar un expediente", "montar um processo", "monte yon dosye"),
]

POLITIQUE = [
    ("programme", "courant", "Ensemble des engagements proposes aux electeurs.", "manifesto", "programa", "programa", "pwogram"),
    ("profession de foi", "technique", "Document officiel de campagne adresse aux electeurs.", "election address", "profesion de fe", "profissao de fe", "pwofesyon de fwa"),
    ("mobilisation", "courant", "Effort pour amener ses soutiens a voter.", "turnout drive", "movilizacion", "mobilizacao", "mobilizasyon"),
    ("porte-a-porte", "courant", "Rencontre directe des electeurs a domicile.", "door-to-door canvassing", "puerta a puerta", "porta a porta", "pòt an pòt"),
    ("militant de terrain", "courant", "Benevole assurant la presence locale de la campagne.", "field activist", "militante de base", "militante de base", "militan teren"),
    ("meeting", "courant", "Grand rassemblement public de campagne.", "rally", "mitin", "comicio", "miting"),
    ("sequence de campagne", "technique", "Periode dediee a un theme et a un objectif precis.", "campaign sequence", "secuencia de campana", "sequencia de campanha", "sekans kanpay"),
    ("petite phrase", "familier", "Formule courte destinee a etre reprise par les medias.", "soundbite", "frase lapidaria", "frase de efeito", "ti fraz"),
    ("socle electoral", "technique", "Part de l electorat acquise et stable.", "electoral base", "base electoral", "base eleitoral", "sòk elektoral"),
    ("report de voix", "technique", "Transfert des suffrages d un tour a l autre.", "vote transfer", "trasvase de votos", "transferencia de votos", "repò vwa"),
    ("abstention", "courant", "Part des inscrits qui ne votent pas.", "abstention", "abstencion", "abstencao", "abstansyon"),
    ("sondage d intentions de vote", "technique", "Enquete estimant les rapports de force.", "voting intention poll", "encuesta de intencion de voto", "sondagem de intencao de voto", "sondaj entansyon vòt"),
    ("marge d erreur", "technique", "Intervalle d incertitude d un sondage.", "margin of error", "margen de error", "margem de erro", "marj erè"),
    ("coalition", "courant", "Alliance de forces politiques autour d un accord.", "coalition", "coalicion", "coligacao", "kowalisyon"),
    ("clivage", "technique", "Ligne de partage structurant l opinion.", "political cleavage", "fractura politica", "clivagem", "klivaj"),
    ("recit de campagne", "technique", "Fil narratif donnant un sens a la candidature.", "campaign narrative", "relato de campana", "narrativa de campanha", "resi kanpay"),
    ("tenir le terrain", "familier", "Maintenir une presence militante constante.", "to hold the ground", "pisar el terreno", "manter o terreno", "kenbe teren an"),
]

STARTUP = [
    ("amorcage", "technique", "Premier tour de financement d une jeune entreprise.", "seed funding", "capital semilla", "capital semente", "amòsaj"),
    ("tour de table", "courant", "Ensemble des investisseurs reunis sur une levee.", "funding round", "ronda de financiacion", "ronda de financiamento", "tou tab"),
    ("valorisation pre-money", "technique", "Valeur de la societe avant l entree des nouveaux fonds.", "pre-money valuation", "valoracion pre-money", "avaliacao pre-money", "valorizasyon pre-money"),
    ("dilution", "technique", "Reduction du pourcentage detenu apres emission de titres.", "dilution", "dilucion", "diluicao", "dilisyon"),
    ("table de capitalisation", "technique", "Tableau de repartition du capital entre associes.", "cap table", "tabla de capital", "cap table", "tab kapitalizasyon"),
    ("duree d autonomie financiere", "technique", "Nombre de mois tenables avec la tresorerie disponible.", "runway", "pista financiera", "runway", "dire otonomi finansye"),
    ("seuil de rentabilite", "technique", "Niveau d activite ou le resultat devient positif.", "break-even point", "umbral de rentabilidad", "ponto de equilibrio", "sèy rantabilite"),
    ("cout d acquisition client", "technique", "Depense moyenne pour gagner un client.", "customer acquisition cost", "coste de adquisicion", "custo de aquisicao", "kou akizisyon kliyan"),
    ("valeur vie client", "technique", "Marge totale esperee sur la duree de la relation.", "customer lifetime value", "valor de vida del cliente", "valor do ciclo de vida", "valè lavi kliyan"),
    ("taux d attrition", "technique", "Part de clients perdus sur une periode.", "churn rate", "tasa de abandono", "taxa de rotatividade", "to atrisyon"),
    ("produit minimum viable", "technique", "Version minimale permettant de tester la demande.", "minimum viable product", "producto minimo viable", "produto minimo viavel", "pwodwi minimòm vyab"),
    ("adequation produit-marche", "technique", "Preuve que le produit repond a un besoin solvable.", "product-market fit", "ajuste producto-mercado", "ajuste produto-mercado", "adekwasyon pwodwi-mache"),
    ("traction", "courant", "Preuve chiffree d adoption par le marche.", "traction", "traccion", "tracao", "traksyon"),
    ("passage a l echelle", "technique", "Croissance sans augmentation proportionnelle des couts.", "scaling", "escalado", "escalagem", "pase nan echèl"),
    ("pivot", "courant", "Changement de modele apres apprentissage du marche.", "pivot", "pivote", "pivot", "pivo"),
    ("argumentaire eclair", "courant", "Presentation du projet en moins de deux minutes.", "elevator pitch", "discurso de ascensor", "pitch de elevador", "agimantè rapid"),
    ("etre a sec", "familier", "Ne plus avoir de tresorerie disponible.", "to run out of cash", "quedarse sin caja", "ficar sem caixa", "sèk nan lajan"),
]

ONG = [
    ("cadre logique", "technique", "Matrice reliant objectifs, activites et indicateurs.", "logical framework", "marco logico", "quadro logico", "kad lojik"),
    ("theorie du changement", "technique", "Explicitation du chemin entre actions et impact.", "theory of change", "teoria del cambio", "teoria da mudanca", "teyori chanjman"),
    ("bailleur de fonds", "courant", "Organisme qui finance un programme.", "donor", "donante", "doador", "bayè fon"),
    ("beneficiaire", "courant", "Personne visee par une action d aide.", "beneficiary", "beneficiario", "beneficiario", "benefisyè"),
    ("redevabilite envers les populations", "technique", "Obligation de rendre compte aux personnes aidees.", "accountability to affected populations", "rendicion de cuentas a la poblacion", "responsabilizacao as populacoes", "redevabilite anvè popilasyon"),
    ("ne pas nuire", "technique", "Principe d evitement des effets negatifs de l aide.", "do no harm", "no causar dano", "nao causar dano", "pa fè mal"),
    ("evaluation des besoins", "technique", "Diagnostic initial de la situation et des priorites.", "needs assessment", "evaluacion de necesidades", "avaliacao de necessidades", "evalyasyon bezwen"),
    ("indicateur de resultat", "technique", "Mesure du changement obtenu par le projet.", "outcome indicator", "indicador de resultado", "indicador de resultado", "endikatè rezilta"),
    ("suivi-evaluation", "technique", "Dispositif de mesure continue et de bilan.", "monitoring and evaluation", "seguimiento y evaluacion", "monitorizacao e avaliacao", "swivi-evalyasyon"),
    ("plaidoyer", "courant", "Action visant a faire evoluer une politique.", "advocacy", "incidencia", "advocacia", "plede kòz"),
    ("note de position", "technique", "Document exposant la ligne defendue par une organisation.", "position paper", "documento de posicion", "documento de posicao", "nòt pozisyon"),
    ("acces humanitaire", "technique", "Possibilite d atteindre les populations dans le besoin.", "humanitarian access", "acceso humanitario", "acesso humanitario", "aksè imanitè"),
    ("resilience", "courant", "Capacite d une population a absorber un choc et a se relever.", "resilience", "resiliencia", "resiliencia", "rezilyans"),
    ("renforcement de capacites", "technique", "Appui au developpement des competences locales.", "capacity building", "fortalecimiento de capacidades", "reforco de capacidades", "ranfòsman kapasite"),
    ("appropriation locale", "technique", "Prise en main du projet par les acteurs du territoire.", "local ownership", "apropiacion local", "apropriacao local", "apwopriyasyon lokal"),
    ("faire du terrain", "familier", "Travailler directement au contact des populations.", "to do fieldwork", "hacer campo", "fazer trabalho de campo", "fè teren"),
]

SECURITE = [
    ("main courante", "technique", "Registre chronologique des evenements d un site.", "incident log", "libro de registro", "livro de ocorrencias", "men kouran"),
    ("consigne de poste", "technique", "Instruction ecrite propre a un emplacement de garde.", "post order", "consigna", "ordem de servico", "konsiy pòs"),
    ("ronde", "courant", "Parcours de surveillance effectue a intervalles.", "patrol round", "ronda", "ronda", "ronn"),
    ("levee de doute", "technique", "Verification sur place du caractere reel d une alarme.", "alarm verification", "verificacion de alarma", "verificacao de alarme", "leve dout"),
    ("perimetre de securite", "technique", "Zone delimitee et controlee autour d un point sensible.", "security perimeter", "perimetro de seguridad", "perimetro de seguranca", "perimèt sekirite"),
    ("plan de sauvegarde", "technique", "Organisation prevue pour proteger les personnes.", "contingency plan", "plan de emergencia", "plano de emergencia", "plan sovgad"),
    ("procedure", "courant", "Suite d actes juridiques encadrant une enquete.", "legal proceedings", "procedimiento", "processo", "pwosedi"),
    ("garde a vue", "technique", "Mesure privative de liberte durant une enquete.", "police custody", "detencion preventiva", "detencao", "gad a vi"),
    ("commission rogatoire", "technique", "Delegation d actes d enquete par un juge.", "letter of request", "comision rogatoria", "carta precatoria", "komisyon rogatwa"),
    ("flagrance", "technique", "Infraction en train de se commettre ou tout juste commise.", "flagrante delicto", "flagrancia", "flagrante", "flagrans"),
    ("chaine de preuve", "technique", "Tracabilite ininterrompue des elements saisis.", "chain of custody", "cadena de custodia", "cadeia de custodia", "chèn prèv"),
    ("renseignement d interet", "technique", "Information utile a la prevention d une menace.", "actionable intelligence", "informacion de interes", "informacao de interesse", "ransèyman enterè"),
    ("posture de vigilance", "courant", "Niveau d attention impose a un dispositif.", "alert posture", "nivel de alerta", "nivel de alerta", "pòs vijilans"),
    ("retour d experience", "technique", "Analyse apres evenement pour corriger le dispositif.", "after-action review", "leccion aprendida", "licao aprendida", "retou eksperyans"),
    ("faire un rapport", "familier", "Consigner par ecrit un evenement constate.", "to file a report", "redactar un parte", "fazer um relatorio", "fè yon rapò"),
]

MODE = [
    ("collection", "courant", "Ensemble coherent de pieces presente pour une saison.", "collection", "coleccion", "colecao", "koleksyon"),
    ("patronage", "technique", "Trace servant a couper les pieces du vetement.", "pattern making", "patronaje", "modelagem", "patwonaj"),
    ("toile de prototype", "technique", "Premiere version en tissu economique pour valider la forme.", "toile", "lienzo de prueba", "tela de prova", "twal pwototip"),
    ("gradation", "technique", "Declinaison d un patron dans toutes les tailles.", "pattern grading", "escalado de patrones", "escalonamento", "gradasyon"),
    ("metrage", "technique", "Quantite de tissu necessaire par piece.", "fabric consumption", "metraje", "metragem", "mètraj"),
    ("tombe du vetement", "technique", "Maniere dont le tissu se place sur le corps.", "drape", "caida", "caimento", "tonbe rad"),
    ("finition", "courant", "Traitement des bords et des details.", "finishing", "acabado", "acabamento", "finisyon"),
    ("sourcing matieres", "technique", "Recherche et selection des fournisseurs de tissus.", "material sourcing", "aprovisionamiento de materiales", "sourcing de materiais", "sousing matyè"),
    ("tendance", "courant", "Orientation esthetique dominante d une saison.", "trend", "tendencia", "tendencia", "tandans"),
    ("defile", "courant", "Presentation publique d une collection.", "runway show", "desfile", "desfile", "defile"),
    ("serie limitee", "courant", "Production volontairement restreinte en quantite.", "limited run", "serie limitada", "serie limitada", "seri limite"),
    ("mode circulaire", "courant", "Conception integrant reemploi et recyclage.", "circular fashion", "moda circular", "moda circular", "mòd sikilè"),
    ("tracabilite de la chaine", "technique", "Connaissance de chaque etape de fabrication.", "supply chain traceability", "trazabilidad de la cadena", "rastreabilidade da cadeia", "trasabilite chèn"),
    ("piece maitresse", "courant", "Vetement central d une collection ou d une tenue.", "statement piece", "prenda clave", "peca-chave", "pyès mèt"),
    ("retoucher une piece", "familier", "Ajuster un vetement apres essai.", "to alter a garment", "arreglar una prenda", "ajustar uma peca", "retouche yon pyès"),
]

AUTO = [
    ("diagnostic electronique", "technique", "Lecture des defauts memorises par les calculateurs.", "electronic diagnostics", "diagnostico electronico", "diagnostico eletronico", "dyagnostik elektwonik"),
    ("courroie de distribution", "technique", "Organe synchronisant vilebrequin et arbre a cames.", "timing belt", "correa de distribucion", "correia de distribuicao", "kouwa distribisyon"),
    ("revision periodique", "courant", "Entretien programme selon le kilometrage.", "scheduled service", "revision periodica", "revisao periodica", "revizyon peryodik"),
    ("controle technique", "courant", "Verification obligatoire de l etat du vehicule.", "roadworthiness test", "inspeccion tecnica", "inspecao periodica", "kontwòl teknik"),
    ("couple moteur", "technique", "Force de rotation delivree par le moteur.", "engine torque", "par motor", "binario do motor", "koup motè"),
    ("consommation mixte", "technique", "Moyenne normalisee de consommation de carburant.", "combined consumption", "consumo mixto", "consumo combinado", "konsomasyon mikst"),
    ("autonomie", "courant", "Distance parcourable avec une charge ou un plein.", "range", "autonomia", "autonomia", "otonomi"),
    ("borne de recharge", "courant", "Equipement delivrant de l energie a un vehicule electrique.", "charging point", "punto de recarga", "ponto de carregamento", "bòn rechaj"),
    ("recharge rapide", "courant", "Charge a forte puissance en un temps court.", "fast charging", "carga rapida", "carregamento rapido", "rechaj rapid"),
    ("aide a la conduite", "technique", "Systeme assistant le conducteur dans sa tache.", "driver assistance", "ayuda a la conduccion", "assistencia a conducao", "èd kondwit"),
    ("valeur residuelle", "technique", "Valeur estimee du vehicule en fin de contrat.", "residual value", "valor residual", "valor residual", "valè rezidyèl"),
    ("location longue duree", "courant", "Mise a disposition d un vehicule contre loyer mensuel.", "long-term lease", "renting", "aluguer de longa duracao", "lokasyon long dire"),
    ("mobilite partagee", "courant", "Usage collectif de vehicules plutot que propriete.", "shared mobility", "movilidad compartida", "mobilidade partilhada", "mobilite pataje"),
    ("piece d occasion reconditionnee", "courant", "Composant reutilise apres remise en etat controlee.", "refurbished part", "pieza reacondicionada", "peca recondicionada", "pyès rekondisyone"),
    ("tomber en panne", "familier", "Cesser de fonctionner en cours de route.", "to break down", "averiarse", "avariar", "tonbe an pàn"),
]

ARTISANAT = [
    ("savoir-faire", "courant", "Competence pratique acquise par l experience.", "craftsmanship", "oficio", "saber-fazer", "konesans pratik"),
    ("geste technique", "technique", "Mouvement precis au coeur du metier.", "technical gesture", "gesto tecnico", "gesto tecnico", "jès teknik"),
    ("essence de bois", "technique", "Variete de bois utilisee et ses proprietes.", "wood species", "especie de madera", "especie de madeira", "esans bwa"),
    ("assemblage", "technique", "Liaison de deux pieces sans fixation visible.", "joinery", "ensamblaje", "ligacao", "asanblaj"),
    ("finition a la cire", "technique", "Protection de surface donnant un aspect satine.", "wax finish", "acabado a la cera", "acabamento a cera", "finisyon ak si"),
    ("gabarit", "technique", "Modele servant a reproduire une forme.", "jig", "plantilla", "molde", "gabari"),
    ("devis", "courant", "Estimation ecrite du prix d une prestation.", "quote", "presupuesto", "orcamento", "deviz"),
    ("prestation sur mesure", "courant", "Realisation adaptee a la demande precise du client.", "bespoke work", "trabajo a medida", "trabalho por medida", "pwestasyon sou mezi"),
    ("atelier", "courant", "Lieu equipe ou s exerce le metier.", "workshop", "taller", "oficina", "atelye"),
    ("apprentissage", "courant", "Formation en alternance aupres d un professionnel.", "apprenticeship", "aprendizaje", "aprendizagem", "aprantisaj"),
    ("coupe", "courant", "Mise en forme des cheveux selon une technique.", "haircut", "corte", "corte", "koup"),
    ("coloration", "courant", "Modification de la couleur des cheveux.", "hair colouring", "coloracion", "coloracao", "kolorasyon"),
    ("petrissage", "technique", "Travail de la pate pour developper le reseau glutineux.", "kneading", "amasado", "amassadura", "petrisaj"),
    ("levain", "technique", "Culture naturelle assurant la fermentation du pain.", "sourdough starter", "masa madre", "massa mae", "leven"),
    ("fournee", "courant", "Quantite cuite en une seule fois.", "batch bake", "hornada", "fornada", "founen"),
    ("travailler a l oeil", "familier", "Operer par experience, sans mesure precise.", "to work by eye", "trabajar a ojo", "trabalhar a vista", "travay ak zye"),
]

if __name__ == "__main__":
    print("[SYNTHEA] Lexiques sectoriels - serie C")
    write_sector("22_lex_commerce_retail.csv", "commerce_retail", "MET090;MET091;MET092;MET093", COMMERCE)
    write_sector("23_lex_marketing_communication.csv", "marketing_communication", "MET094;MET095;MET096;MET097", MARKETING)
    write_sector("24_lex_ressources_humaines.csv", "ressources_humaines", "MET098;MET099;MET100;MET101", RH)
    write_sector("25_lex_education_formation.csv", "education_formation", "MET102;MET103;MET104;MET105", EDUCATION)
    write_sector("26_lex_hotellerie_tourisme.csv", "hotellerie_restauration_tourisme", "MET106;MET107;MET108", HOTEL)
    write_sector("27_lex_media_journalisme.csv", "media_journalisme", "MET109;MET110;MET111", MEDIA)
    write_sector("28_lex_art_culture_spectacle.csv", "art_culture_spectacle", "MET112;MET113;MET114", CULTURE)
    write_sector("29_lex_sport_performance.csv", "sport_performance", "MET115;MET116", SPORT)
    write_sector("30_lex_administration_publique.csv", "administration_publique", "MET117;MET118;MET119", PUBLIC)
    write_sector("31_lex_politique_campagne.csv", "politique_campagne", "MET120;MET121;MET122", POLITIQUE)
    write_sector("32_lex_entrepreneuriat_startup.csv", "entrepreneuriat_startup", "MET130;MET131", STARTUP)
    write_sector("33_lex_ong_humanitaire.csv", "ong_humanitaire_developpement", "MET123;MET124;MET125", ONG)
    write_sector("34_lex_securite_defense.csv", "securite_defense", "MET126;MET127", SECURITE)
    write_sector("35_lex_mode_textile.csv", "mode_textile", "MET128", MODE)
    write_sector("36_lex_automobile_mobilite.csv", "automobile_mobilite", "MET129", AUTO)
    write_sector("37_lex_artisanat_metiers_manuels.csv", "artisanat_metiers_manuels", "MET132;MET133;MET134", ARTISANAT)
