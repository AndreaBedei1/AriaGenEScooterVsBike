# Cesena test route: legal and infrastructure constraints for e-scooters and bicycles

> Desk research compiled on 2026-10-15 (status of rules as of that date). Downloaded documents were kept outside the repository. Not legal advice.


Status: as of **15 October 2026** (date of all accesses unless stated otherwise).
Purpose: input for designing a ~3.5–4.5 km loop starting and ending at Campus Ex Zuccherificio (Via dell'Università 50, Cesena) that both an e-scooter and a bicycle can ride legally, in the same direction.

Reliability tags used below:
- **[P]** primary source (Gazzetta Ufficiale / Normattiva / ministry / Comune act), read directly.
- **[S]** secondary source (press, legal commentary, operator sites).
- **[OD]** official open data (Comune di Cesena / Unione Valle Savio), read directly. Vintage may be older than the publication date.
- **[OSM]** OpenStreetMap (crowd-sourced, ODbL). Used only as a cross-check.
- **[INF]** my inference from the sources.
- **[UNVERIFIED]** not confirmed by a primary source, or needs an on-site check.

All downloaded raw files are in `<workdir>/ext/cesena/` (untrusted data; nothing was executed from there). Text extractions are in `<workdir>/pdftext/`.

---

## 1. National rules for electric kick-scooters (monopattini a propulsione prevalentemente elettrica)

### 1.1 Legal basis and text currency

- Law: art. 1, commi 75 to 75-vicies quinquies, L. 27 dicembre 2019 n. 160, as amended by **L. 25 novembre 2024 n. 177** (GU n. 280 del 29-11-2024, code 24G00199, **in force 14/12/2024**) [P].
  - Normattiva, consolidated text: https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:2019-12-27;160~art1-com75 . Page note: "Ultimo aggiornamento all'atto pubblicato il 11/08/2026".
  - I also fetched the version in force on 15/10/2026 (`...;160!vig=2026-10-15~art1-com75`, "Testo in vigore dal: 12-8-2026"). Commi 75 to 75-vicies quinquies are **word-for-word identical** to the latest version [P].
  - L. 177/2024 on Normattiva: https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:legge:2024-11-25;177 ("Entrata in vigore del provvedimento: 14/12/2024 … (GU n.280 del 29-11-2024)") [P].
- Ministry of the Interior (Polizia Stradale) operational circular **n. 38625 of 20/12/2024**, "Legge 25 novembre 2024, n. 177 … Prime disposizioni operative", Scheda illustrativa allegata 2 (PDF pp. 78–84): https://prefettura.interno.gov.it/sites/default/files/21/2024-12/circolare-legge-177-2024-modifiche-al-codice-dell_241220_133409.pdf [P].
  - The protocol number and date are confirmed by the April 2026 circular below ("circolare n. 38625 del 20 dicembre 2024").

### 1.2 What L. 177/2024 changed (Interior circular 38625/2024, Scheda 2, PDF p. 80–81) [P]

> "Le modifiche hanno interessato diversi aspetti riguardanti, in particolare: le caratteristiche tecniche; la possibilità di circolare solo nei centri abitati; la riconoscibilità attraverso l'apposizione di un contrassegno di identificazione; l'obbligo di copertura assicurativa; l'obbligo di uso del casco per tutti a prescindere dall'età; le regole più stringenti per la sosta e la circolazione; le nuove regole per i gestori di servizi di noleggio."

> "La modifica del comma 75-undecies ha eliminato la deroga al divieto di circolare contromano nelle strade con doppio senso ciclabile."

> "La modifica del comma 75-terdecies, ha limitato l'ambito di circolazione dei monopattini alle sole strade urbane aventi limite di velocità non superiore a 50 km/h. Non sarà più possibile, quindi, circolare fuori dal centro abitato neanche sulle piste ciclabili e sugli altri percorsi riservati alla circolazione dei velocipedi."

### 1.3 Contrassegno identificativo ("targhino"): mandatory since 17 May 2026; the platform is operational

Decree chain [P]:
1. **Decreto Capo Dipartimento MIT n. 210 of 27/06/2025.** It sets print criteria and the alphanumeric codes. MIT news of 03/07/2025: https://mit.gov.it/node/20823
   > "dovrà essere applicato in modo visibile sul monopattino, preferibilmente al centro del parafango posteriore, se presente l'alloggiamento specifico, oppure nella parte anteriore del piantone dello sterzo, a un'altezza compresa tra 20 centimetri e 1,20 metri dal suolo."
2. **DM MIT n. 250 of 06/10/2025.** It sets the price and the request procedure: https://mit.gov.it/nfsmitgov/files/media/normativa/2025-11/Decreto%20Ministeriale%20prot.250%20del%2006-10-2025_0.pdf
   > Art. 2: "Il prezzo di vendita di ciascun contrassegno identificativo … è stabilito in € 8,66"
   > Art. 3 c. 7 ties the obligation to "il sessantesimo giorno" after the later platform decree.
3. **Decreto Direttoriale DG Motorizzazione n. 110 of 06/03/2026.** It regulates the online platform: https://mit.gov.it/nfsmitgov/files/media/normativa/2026-03/RD%20110.26.pdf
   > Art. 14 c. 5: "l'obbligo da parte del proprietario del monopattino elettrico di dotarsi di apposito contrassegno identificativo, ai fini della circolazione stradale, trova applicazione a decorrere dal sessantesimo giorno dalla data di entrata in vigore del presente decreto"
   - It was published in GU on 17/03/2026 and entered into force on 18/03/2026. Source: Interior circular, April 2026, footnote 6.

Operational status [P]:
- MIT news of 14/05/2026: https://www.mit.gov.it/comunicazione/news/monopattini-elettrici-il-mit-50-mila-contrassegni-gia-rilasciati
  > "in vista dell'entrata in vigore dell'obbligo di circolazione con contrassegno, prevista dal 17 maggio 2026. A oggi sono state presentate oltre 40 mila richieste … e risultano già emessi circa 50 mila contrassegni. L'attività viene gestita attraverso la piattaforma telematica attiva dal 18 marzo 2026 … La richiesta del contrassegno avviene esclusivamente online … ritiro … presso l'Ufficio Motorizzazione Civile selezionato."
- Interior Ministry circular "Contrassegni di identificazione dei monopattini", digitally signed 24/04/2026 (file dated 27/04/2026): https://prefettura.interno.gov.it/sites/default/files/93/2026-04/2026-04-27-circolare-obbligo-contrassegno-di-identificazione-monopattini.pdf
  > "Quest'ultimo decreto è stato adottato il 6 marzo 2026 e ha confermato la decorrenza del suddetto obbligo dal sessantesimo giorno dalla data di entrata in vigore, cioè dal 17 maggio 2026."
- **Date discrepancy:** some secondary sources say 16/05/2026. MIT and the Interior Ministry both say **17/05/2026**.
- **Who must request it:** "I proprietari" (comma 75-vicies quater). MIMIT FAQ [P]: adults, and minors from 14 years through a parent.
- **Placement circular** n. 14178 of 15/05/2026 (Interior) [S, via circolazione-stradale.it; UNVERIFIED].

### 1.4 Compulsory RC insurance: in force since 16 July 2026 (postponed once from May)

- Comma 75-vicies quinquies [P]:
  > "I monopattini a propulsione prevalentemente elettrica non possono essere posti in circolazione se non sono coperti dall'assicurazione per la responsabilità civile verso terzi prevista dall'articolo 2054 del codice civile. Si applicano le disposizioni del titolo X del codice delle assicurazioni private …"
- The obligation depends on holding the contrassegno. Interior circular 38625/2024, PDF p. 83 [P]:
  > "si ritiene che l'obbligo assicurativo di cui al comma 75-vicies quinquies sia subordinato al possesso del contrassegno identificativo del monopattino"
- Postponement, Interior circular of April 2026, p. 2 [P]:
  > "il Ministero delle imprese e del made in Italy ed il Ministero delle infrastrutture e dei trasporti – in considerazione delle criticità di natura tecnica rappresentate dall'Associazione nazionale fra le imprese assicuratrici (ANIA) … – hanno comunicato che le compagnie di assicurazione offriranno le polizze per la copertura Rc auto dei monopattini dal 16 luglio 2026, data dalla quale deve considerarsi operativo il citato obbligo assicurativo."
  - From the same date, the Fondo di garanzia vittime della strada and Carta Verde also apply.
- MIMIT FAQ (last modified 24/04/2026): https://www.mimit.gov.it/it/assistenza/domande-frequenti/rc-auto-obbligatoria-monopattini-domande-frequenti-faq [P]
  - Minimum cover: €6.45 M for persons and €1.3 M for property.
  - The policy "deve riportare il codice del contrassegno identificativo".
  - It cites a circular of 17/04/2026 ("indicazioni sulla decorrenza dell'obbligo assicurativo") and one of 24/04/2026 (Titolo X CAP).
  - circolazione-stradale.it [S] instead cites "circolare MIMIT n. 615 del 24 aprile 2026" and "circolare dell'Interno n. 11794 del 27 aprile 2026". The circular numbers and dates are **[UNVERIFIED]**; the 16/07/2026 date is confirmed [P].
- **Further postponement after 16/07/2026: none found** as of 15/10/2026 (MIT/MIMIT searches, circolazione-stradale.it articles of 14 and 17/09/2026) [S]. Absence of evidence, so not 100% certain.
- **Sharing:** comma 75-ter a) requires the operator to have insurance "per lo svolgimento del servizio" [P]. Whether shared vehicles also need individual contrassegni or policies was **[UNVERIFIED]** and is not relevant if private scooters are used.

### 1.5 Rider and vehicle requirements (verbatim from Normattiva unless noted) [P]

| Topic | Rule |
|---|---|
| Helmet | 75-novies: "I conducenti dei monopattini hanno l'obbligo di indossare un idoneo casco protettivo conforme alle norme tecniche armonizzate UNI EN 1078 o UNI EN 1080." **All ages** since 14/12/2024 (circ. 38625: "a prescindere dall'età"). |
| Minimum age | 75-octies: only riders "che abbiano compiuto il quattordicesimo anno di età". No licence needed. |
| Vehicle | 75: (a) technical characteristics set by MIT decree; (b) "assenza di posti a sedere"; (c) "motore elettrico di potenza nominale continua non superiore a 0,50 kW"; (d) "segnalatore acustico"; (e) "regolatore di velocità configurabile in funzione dei limiti di cui al comma 75-quaterdecies"; (f) CE marking (Dir. 2006/42/CE). |
| Technical decree | Decreto dirigenziale 18/08/2022 (GU n. 202 del 30/08/2022). Interior circ. 38625, p. 80: it covers "la potenza nominale continua non superiore a 0,50 kW, il diametro delle ruote, … il regolatore di velocità configurabile a 6 km/h e 20 km/h, … l'impianto frenate su entrambe le ruote, il segnalatore acustico, gli indicatori luminosi di svolta, i dispositivi di illuminazione anteriore e posteriore, i catadiottri rossi posteriori e gialli laterali e le eventuali luci di arresto." So **brakes on both wheels are required**. |
| Turn indicators / brake lights | 75-bis: "A decorrere dal 30 settembre 2022, i monopattini … commercializzati in Italia devono essere dotati di indicatori luminosi di svolta e di freno su entrambe le ruote. I monopattini … già in circolazione prima di tale data devono essere adeguati … entro il 1° gennaio 2024." So **all scooters, now**. |
| Lights | 75-sexies: from half an hour after sunset, in darkness, and in poor visibility: front white or yellow steady light, rear red steady light, plus rear red reflectors. |
| Hi-vis | 75-septies: retro-reflective vest or braces from half an hour after sunset. |
| Hands | 75-duodecies: "reggere il manubrio sempre con entrambe le mani, salvo che sia necessario segnalare la manovra di svolta sui mezzi privi di indicatori di direzione." |
| Passengers / loads | 75-decies: "È vietato trasportare altre persone, oggetti o animali, di trainare veicoli, di condurre animali e di farsi trainare da un altro veicolo." Whether a backpack worn by the rider counts is not addressed **[UNVERIFIED]**. Do not hang anything on the handlebar. |
| Sidewalks / wrong way | 75-undecies: "È vietata la circolazione … sui marciapiedi. Sui marciapiedi è consentita esclusivamente la conduzione a mano … È altresì vietato circolare contromano." |
| Everything else | 75-quinquies: "per quanto non previsto dai commi da 75 a 75-vicies quinquies, sono equiparati ai velocipedi." So the CdS rules for bicycles apply, including art. 182 c. 9 (must use cycle tracks or lanes where they exist). |

### 1.6 Where an e-scooter may circulate [P unless marked]

- 75-terdecies: "possono circolare solo su strade urbane con limite di velocità non superiore a 50 km/h."
- **Extra-urban roads** (outside the "centro abitato" signs): forbidden, **even on cycle paths** (circ. 38625).
- **Urban roads with a limit above 50 km/h** (for example 70 km/h): forbidden on the carriageway. Whether a cycle track alongside such a road may be used is not settled **[UNVERIFIED; avoid]**.
- **Piste ciclabili, corsie ciclabili, percorsi ciclopedonali in urban areas:** allowed by the equivalence with bicycles (75-quinquies).
  - circolazione-stradale.it, 17/09/2026 [S]: the removal of the infrastructure list in 75-terdecies "non deve essere interpretata nel senso di una generale espulsione dei monopattini dalle infrastrutture ciclabili presenti all'interno dei centri abitati".
  - On shared ciclopedonali, pedestrians have priority (Biciplan p. 49; art. 182 c. 4).
- **Contraflow cycle lanes** (corsia ciclabile per doppio senso ciclabile, CdS art. 3 n. 12-ter): **NOT allowed** for e-scooters. Contraflow riding is banned and the derogation was removed (circ. 38625, p. 81). Bicycles may use them.
- **Aree pedonali:** allowed **only at ≤ 6 km/h** (75-quaterdecies), and only where bicycles are admitted.
  - CdS art. 3 n. 2: "Area pedonale: zona interdetta alla circolazione dei veicoli, salvo quelli in servizio di emergenza, i velocipedi e i veicoli al servizio di persone con limitate o impedite capacità motorie … In particolari situazioni i comuni possono introdurre, attraverso apposita segnalazione, ulteriori restrizioni alla circolazione su aree pedonali."
  - circolazione-stradale.it [S]: "la circolazione resta possibile, a 6 km/h, dove l'accesso è consentito dalla disciplina dell'area."
- **ZTL:** not addressed by the scooter rules. The ZTL restricts "l'accesso e la circolazione veicolare" for the categories set by the Comune (CdS art. 3 n. 54). In Cesena those are motor vehicles only (see §4).
- **Sidewalks:** forbidden (walk the scooter).

### 1.7 Speed limits [P]

- 75-quaterdecies: "non possono superare il limite di velocità di 6 km/h quando circolano nelle aree pedonali. Non possono superare il limite di 20 km/h in tutti gli altri casi di circolazione di cui al comma 75-terdecies."
- Any lower posted limit (Zona 30, 10 km/h streets) also applies.

### 1.8 Parking [P]

- 75-quinquiesdecies: "È vietata la sosta dei monopattini sul marciapiede."
  - Exception: areas the Comune designates by ordinance, with signs or with GPS coordinates published online.
  - "Ai monopattini … è comunque consentita la sosta negli stalli riservati ai velocipedi, ai ciclomotori e ai motoveicoli."
- Sanction: art. 158 c. 5 CdS, €41–168 (circ. 38625 footnote 6), without towing.

### 1.9 Sanctions [P]

| Violation | Amount |
|---|---|
| Commi 75-sexies to 75-quaterdecies (lights, vest, age, helmet, transport, sidewalk or contraflow, hands, roads allowed, speed) | €50–250 (75-duodevicies) |
| Non-compliant vehicle, or missing indicators (75-bis) | €200–800 (75-undevicies) |
| Missing, not visible or altered contrassegno, or **no insurance** (75-quater second sentence) | €100–400 (75-undevicies) |
| Motor >1 kW or combustion engine | Confiscation (75-vicies) |

### 1.10 Sharing services [P]

- 75-ter: services may be activated only by a Giunta deliberation.
- The deliberation must set:
  - the number of licences and devices;
  - insurance;
  - parking modes;
  - "le eventuali limitazioni alla circolazione in determinate aree della città, imponendo al gestore del servizio l'installazione obbligatoria di sistemi automatici che impediscano il funzionamento dei monopattini al di fuori di tali aree."

### 1.11 Devices while riding (relevant to wearable sensors and smart glasses) [P]

- CdS art. 173 c. 2 (in force 14/12/2024): "È vietato al conducente di far uso durante la marcia di apparecchi radiotelefonici, smartphone, computer portatili, notebook, tablet e dispositivi analoghi che comportino anche solo temporaneamente l'allontanamento delle mani dal volante ovvero di usare cuffie sonore …"
- The rule applies to all "conducenti", so cyclists and scooter riders too [INF].
- Head-worn recording glasses that need no hand interaction are not explicitly covered. Audio output through "cuffie" is banned [INF; **check with the ethics/legal office**].

---

## 2. Bicycle rules relevant to route design [P]

Source: CdS art. 182, Normattiva ("Testo in vigore dal: 14-12-2024"): https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:decreto.legislativo:1992-04-30;285~art182

- **c. 1:** "I ciclisti devono procedere su unica fila in tutti i casi in cui le condizioni della circolazione lo richiedano e, comunque, mai affiancati in numero superiore a due; quando circolano fuori dai centri abitati devono sempre procedere su unica fila …"
- **c. 1-bis:** c. 1 does not apply "sulle strade urbane ciclabili, sugli itinerari ciclopedonali e nelle zone ciclabili".
- **c. 2:** hands free; hold the handlebar "almeno con una mano". The e-scooter rule is **both** hands.
- **c. 4:** "I ciclisti devono condurre il veicolo a mano quando, per le condizioni della circolazione, siano di intralcio o di pericolo per i pedoni."
- **c. 5:** no passengers, except a child under 8 with proper equipment.
- **c. 9 (obligation to use cycle infrastructure):** "I velocipedi devono transitare sulle piste loro riservate ovvero sulle corsie ciclabili o sulle corsie ciclabili per doppio senso ciclabile, quando esistono …"
  - By 75-quinquies the same obligation applies to e-scooters [INF].
  - So both modes must use the same cycle track wherever one exists. This keeps the two conditions comparable.
- **c. 9-bis:** hi-vis vest outside built-up areas at night and in tunnels.
- **c. 9-ter:** "COMMA ABROGATO DALLA L. 25 NOVEMBRE 2024, N. 177".
- **Definitions** (CdS art. 3, in force 14/12/2024) [P]:
  - n. 12-bis corsia ciclabile (on the carriageway, right side, may be shared);
  - n. 12-ter corsia ciclabile per doppio senso ciclabile;
  - n. 39 pista ciclabile ("parte longitudinale della strada, opportunamente delimitata, riservata alla circolazione dei velocipedi");
  - n. 54 ZTL;
  - n. 54-bis zona ciclabile;
  - n. 2 area pedonale (velocipedi admitted unless the Comune restricts by signs).
- **Helmet for cyclists:** not mandatory under the CdS [INF from the absence of a provision]. For the study, use helmets for both groups for consistency and ethics.

---

## 3. Biciplan "VeloCe – la Bicipolitana di Cesena" (2021)

Source: https://static-www.comune.cesena.fc.it/wp-content/uploads/2023/12/VeloCe_Biciplan_Cesena.pdf

- 87 pages. PDF created 13/07/2021. Downloaded 15/10/2026.
- Text extracted with page markers to `<workdir>/pdftext/biciplan/biciplan_pages.txt`; page images in `<workdir>/pdftext/biciplan/img/`.
- Page numbers below are **PDF page = printed page**.
- **p. 1:** "Piano per la mobilità ciclistica (Biciplan) 2021 – Approvato dalla Giunta Comunale con Delibera 262 del 15/06/2021".
- **p. 2:** version "Definitivo", date 18/06/2021, drafted by Decisio (with Bikeconomy observatory).

**Important limitation.** The Biciplan has **no** text mentions of:
- Via dell'Università, Campus or Ex Zuccherificio;
- Via Machiavelli as a cycle path;
- Rotonda dei Mulini;
- Via Calvino or Via Quasimodo;
- Ponte Europa Unita.

The lines are metro-style diagrams with stop names only. It does not give surfaces or one-way/two-way status for specific links. The relevant information is the stops "Europa (Università)" and "Macchiavelli" on the **Linea Circolare**, plus the legend (p. 10–11):
- red dashed = infrastructure absent;
- orange = present but can be improved;
- green = present and optimal;
- red X = critical point;
- green/orange/red hatching = construction planned short/medium/long term;
- solution types A–E (see below).

### 3.1 Linea Circolare (p. 36–37; ring around the centre, 9.7 km; interchanges with lines 1, 2, 3, 4, 5, 7)

| Segment (stops in order) | 2021 status | Critical point / solution | Planning horizon |
|---|---|---|---|
| Piazza della Libertà (Centro) – Via Montanari – Sobborgo Valzania | green (present, optimal) | – | – |
| Sobborgo Valzania – Fiorenzuola – Marconi – Piemonte – Rotonda San Pietro – Cavour – Angeloni | orange (present, improvable) | Nodo Don Baronio-Costa-Fiorenzuola; Nodo Fiorenzuola-Brunelli-Verrazzano; Nodo Fiorenzuola-Marconi-Levante; Nodo Rotonda San Pietro. Solutions: side cycle rings, complete the cycle ring | – |
| **Angeloni – Europa (Università)** | orange | Critical point **"Nodo Bovio-Europa-SS9"**. Solution: "Riduzione DE rotatoria per realizzazione anello ciclabile" | **short-term** (green hatching) |
| **Europa (Università) – Macchiavelli** | **orange (present, improvable)** | – | – |
| **Macchiavelli – Risorgimento** | **red dashed: INFRASTRUCTURE ABSENT** | Critical point **"Nodo Piazzale Risorgimento"**. Solution: "Ridisegno del piazzale per conversione in piazza" | **long-term** (red hatching) |
| **Risorgimento – Cesare Battisti – Piazza della Libertà** | **green (present, optimal)** | – | – |

- Solution types applied (p. 36–37): **B, C** on the first part; **E2** from Rotonda San Pietro to Cesare Battisti.
- **[INF]** "Europa (Università)" is the Rotonda Panathlon node (Viale Bovio / Viale Europa / Via Cavalcavia).
  - The Comune reports (11/02/2025) that the Viale Bovio cycle track "da via Mario Angeloni fino ad arrivare alla rotonda Panathlon" (800 m) has been built. So the short-term Angeloni–Europa link is **now existing**.
  - Whether the roundabout ring itself was built is **[UNVERIFIED]**.

### 3.2 Other lines touching the campus–centre area

- **Linea 5 Ravennate** (p. 20–21, 9.4 km, interchange with C at "Europa (Università)").
  - Piazza della Libertà – Via Finali – Europa (Università) – Europa: **orange**; solution C.
  - Europa – Subborgo Comandini sottopasso ferrovia: **absent**, short-term.
- **Linea 7 Emilia Ovest** (p. 24–25, 6.6 km).
  - Piazza delle Libertà – Cesare Battisti – Risorgimento: **green**. Critical point "Nodo Piazzale Risorgimento"; solution "Riassetto degli spazi".
  - Risorgimento – Gramsci: **orange**. Critical point "Rotatoria Gramsci" (solution: remodelling plus cycle ring).
  - Via Emilia Ponente roundabout: "Rotatoria e salto di carreggiata".
- **Linea 6 Dismano** (p. 22–23).
  - Gramsci – Savio – Ponte Vecchio – Piazza del Popolo: **absent**.
  - Critical point at Ponte Vecchio: "Struttura del ponte non agevole al transito ciclistico". Solution: "Costruzione passerella ciclabile sul Savio" (long-term).
  - **Piazza del Popolo – Piazza delle Libertà: green.**
- **Linea 8 Romea** (p. 26–27). Savio – Ponte Vecchio – Piazza del Popolo – Piazza della Libertà is shown as **absent**, long-term.
  - **Inconsistency with Linea 6** for the Popolo–Libertà segment; field check needed.
- **Linea 9 Cesuola** (p. 28–29).
  - S. Francesco d'Assisi – Cavallotti: absent. Critical point "Immissione su Via F. d'Assisi".
  - **Cavallotti – Piazza del Popolo: orange**, labelled **"Zona Pedonale"**, so Piazza del Popolo is the pedestrian-zone terminus.
- **Linea S (Savio greenway).** Drawn on the network map (p. 9) but has no dedicated page. The Comune (11/02/2025 and 16/05/2025) says it was inaugurated on 25/09/2021, "collegando il Ponte vecchio a via Ancona, per oltre 2 chilometri" [P].
  - OSM tags its surfaces as **fine_gravel / dirt / compacted** [OSM, UNVERIFIED]. It is probably unsuitable for small scooter wheels; check on site.

### 3.3 Network, Zone 30 and design standards (Biciplan)

- **p. 6:** e-scooters are recognised: "monopattini elettrici, recentemente equiparati ai velocipedi della legge 160/2019 (art. 1 comma 75)".
  - Cyclist sway of 15–20 cm per side, and up to 40 cm per side when starting off.
- **p. 9:** "La rete ciclabile di Cesena è già oggi composta da una maglia di percorsi, in sede propria e condivisa, in grado di coprire buona parte del Comune. L'area urbana centrale risulta essere la più servita in termini di infrastrutture esistenti …"
- **p. 38:** "nel Piano Urbano della Mobilità Sostenibile (PUMS, 2020) di Cesena si è pianificata la conversione di gran parte del nucleo abitato della città in "Zone 30", con l'esclusione di alcuni assi di scorrimento e penetrazione veicolare."
- **p. 39 (map):** "ZTL Centro" (purple), "Zone 30 esistenti" (yellow), "Zone 30 da potenziare" and "Nuovi Spazi di Condivisione" (PUMS 21–30). The whole urban core around the ZTL is shown as Zona 30 (existing or to be strengthened).
- **p. 42:** widths.
  - Primary network: one-way >1.8 m, two-way >2.8 m, design speed 16–25 km/h.
  - DM 557/1999 minimum: >1.5 m and >2.5 m.
- **p. 44–49, solution types:**
  - A = shared bike–car street (30 km/h preferred);
  - B = corsia ciclabile valicabile;
  - C = strada ciclabile E-bis/F-bis (cars as guests, ≤30 km/h);
  - D1/D2 = two-way/one-way pista on a reserved lane;
  - E1/E2 = two-way/one-way pista in sede propria (kerb-protected);
  - p. 49 = shared ciclopedonale: "la precedenza spetti comunque ai pedoni: in caso di pericolo o intralcio i ciclisti devono infatti condurre il veicolo a mano" (the plan advises against it in urban areas).
- **p. 53, roundabouts:** "Per evitare che il ciclista transiti in corona con i veicoli, in rotatorie compatte e di grandi dimensioni è sempre necessario (anche dove non esiste un percorso ciclabile) procedere alla separazione dei flussi creando un anello ciclabile esterno …"
  - Crossings should be set back 4–5 m from the ring.
- **p. 56, cycle crossings:** the cyclist "ha piena priorità sul traffico veicolare".
  - Width ≥1 m for one-way crossings and ≥2 m for two-way.

### 3.4 Post-2021 updates from the Comune [P]

- **"Bicipolitana cittadina…" (11/02/2025):** https://www.comune.cesena.fc.it/novita/bicipolitana-cittadina-il-punto-sui-percorsi-ciclabili-esistenti-e-sui-lavori-in-corso/
  - Viale Bovio, Angeloni → Rotonda Panathlon, 800 m: built.
  - Via Ravennate: 1.5 km.
  - Via Cerchia di Sant'Egidio: 800 m.
  - Viale Gramsci: 300 m, "collegamento tra la zona dell'Ippodromo e il centro storico".
  - Linea S: built.
  - The network totals "101 chilometri".
- **"Cesena pedala verso il futuro…" (16/05/2025):** https://www.comune.cesena.fc.it/novita/cesena-pedala-verso-il-futuro-ben-101-chilometri-di-ciclabili-attraversano-il-territorio-comunale/ (same list).

### 3.5 Official open data cross-check per street (Comune di Cesena layer "Piste Ciclabili", [OD])

- Layer: `OD_PISTE_CICLABILI_2019_LINE_SDO`, CC BY 4.0 (see §5). The layer name says 2019; the vintage may predate recent works.
- 983 features. Categories:
  - 01 existing in sede propria;
  - 02 existing on sidewalk-level reserved lane ("corsia riservata su marciapiede");
  - 03 existing reserved lane on the carriageway;
  - 04 existing "altri percorsi ciclopedonali";
  - 05 being built;
  - 06 planned.
- Each feature was matched to the nearest named OSM street within 35 m (script `<workdir>/tools/match_cycle.py`; approximate). Lengths are summed within the study bbox.

| Street / link | Existing | Planned |
|---|---|---|
| Via Niccolò Machiavelli | 280 m in sede propria (around 44.1430, 12.2359, near the Ponte Europa Unita node); 715 m on sidewalk level (around 44.1489, 12.2346, campus side); 445 m other ciclopedonale (around 44.1504) | 476 m (around 44.1502, **north** of campus) |
| Via Italo Calvino | 229 m on sidewalk level | – |
| Via Salvatore Quasimodo | 24 m on sidewalk level (connector only) | – |
| Ponte Europa Unita | 312 m in sede propria | 87 m (west end) |
| Via Mulini (at Rotonda dei Mulini) | 33 m in sede propria plus 170 m on sidewalk level | – |
| Via Zuccherificio (Rotonda dei Mulini → Piazzale Risorgimento) | 209 m in sede propria (south end, around 44.1396) | **356 m** (around 44.1416) |
| Viale Europa | 500 m in sede propria plus 170 m on sidewalk level | – |
| Rotonda Panathlon | 24 m | – |
| Viale Bovio / Viale Angeloni / Corso Cavour | 354 / 282 / 774 m in sede propria | – |
| Viale Finali (Linea 5) | 277 m in sede propria | – |
| Via Cesare Battisti | 475 m reserved lane on the carriageway | – |
| Via Umberto Saba, Via Oriani (campus district) | 45 + 481 m; 226 m | – |
| Viale Matteotti (west of the Savio, Via Emilia W) | 784 m in sede propria | – |

### 3.6 OSM cross-check of key links [OSM, all UNVERIFIED; verify on site]

- **Via Machiavelli main carriageway, about 44.1476–44.1499 (from the campus junction northward): `maxspeed=70`.**
  - If true, the e-scooter **cannot** use that carriageway (75-terdecies).
  - The SS726 Tangenziale (Via Ugo La Malfa, trunk, 90 km/h) is about 300 m north of the campus. Forbidden; avoid.
- **Along Via Machiavelli, campus → Ponte Europa Unita node** (44.1481 → 44.1438): a 489 m footway tagged `bicycle=yes`, surface **paving_stones**.
  - The official data calls this "corsia riservata su marciapiede" / pista.
  - Check the signs on site. Fig. II 90/92/93 (pista ciclabile / ciclopedonale) means the scooter may ride. A plain sidewalk means the scooter must be walked.
- **Via Calvino:** a 230 m shared path (`bicycle=designated, segregated=no`, asphalt, lit).
- **Viale Europa (Calvino → Panathlon):** shared cycle path, asphalt, with marked crossings.
- **Ponte Europa Unita:** two side footway bridges (`bicycle=yes`, concrete). The carriageway bridge is two-way.
- **Rotonda dei Mulini:** tertiary single-lane roundabout.
- **Via Zuccherificio:** secondary road, `cycleway:both=no` on the 214 m middle part. This matches the "absent" status in the Biciplan.
- **Ponte del Risorgimento (Ponte Nuovo):** secondary, 3 lanes, `maxspeed=30`. Separate side cycleway present.
- **Via Cesare Battisti:**
  - west part: unclassified, `maxspeed=30`, `cycleway:both=no`;
  - east part (towards Piazza del Popolo): `highway=pedestrian, bicycle=yes`, concrete plates.
- **Piazza del Popolo and Corso Mazzini:** `highway=pedestrian, bicycle=yes`, paving stones or concrete plates.
- **Via Zeffirino Re:** pedestrian, `surface=unhewn_cobblestone`. **Avoid with small wheels.**
- **[INF] Via Emilia.** The urban through-route of the Via Emilia appears to run "via Marconi, viale Oberdan, via Bovio, via Europa, via Zuccherificio, ponte del Risorgimento, via Matteotti, via Cattaneo, via Emilia Ponente".
  - Source: Giro d'Italia stage route, il Resto del Carlino 14/05/2022 [S]: https://www.ilrestodelcarlino.it/cesena/cronaca/mercoledi-passa-il-giro-e-si-blocca-la-via-emilia-1296060a
  - The same sequence appears for 08/05/2024 [S]: https://www.ilrestodelcarlino.it/cesena/cronaca/giro-italia-quando-viabilita-a283b024
  - Consistent with the Biciplan node name "Bovio-Europa-**SS9**" (p. 37) and with OSM `highway=secondary` on all of these streets.
  - **So Viale Europa, Via Zuccherificio, Piazzale Risorgimento and Viale Matteotti are the main urban arterial (former SS9 alignment).** Riding on their **separated cycle tracks** keeps the riders off the traffic. Riding **on the carriageway** of Via Zuccherificio or Piazzale Risorgimento means riding on the Via Emilia urban axis.

---

## 4. Cesena: ZTL, pedestrian area, sharing, Zone 30

### 4.1 ZTL rules [P]

- **"Disciplina di gestione delle ZTL e ZRU"**: approved by DG n. 1/2025, updated by DG n. 196/2025 and **n. 243/2025 of 07/10/2025**, **in force since 01/03/2025**. Licence: "licenza aperta".
  - Page: https://www.comune.cesena.fc.it/documento_pubblico/disciplina-di-gestione-ztl-e-zru/
  - PDF: https://static-www.comune.cesena.fc.it/wp-content/uploads/2023/11/Disciplinare_2025-ZTL_ZRU-rev_02-DG_243_2025.pdf
- p. 10 (§1.1): "orario di funzionamento: indicato da segnaletica in loco; divieto di transito e di sosta con rimozione: negli orari di funzionamento per i veicoli non iscritti nella lista "servizi collettivi", sprovvisti di permesso …"
  - Gates are enforced by cameras (the "Icarus" system, p. 4).
- p. 10–11 (§1.2): "La presente disciplina si applica ai **veicoli a motore**, classificati in base all'art. 47 del C.d.S. … a) veicoli di categoria L4e, L5e, L6e, L7e; b) … M1 …; c) … N1 …"
- **[INF]** Bicycles and e-scooters are not motor vehicles in these categories, so **ZTL access limits do not apply to them**.
  - Permit holders' transit is always "con rispetto delle aree pedonali fisse e variabili" (pp. 24, 29, 33, 39 …). That implies pedestrian zones fixed in time and variable in time inside the ZTL.
  - **ZTL hours are not given in the Disciplinare**; they are posted on the signs. **[UNVERIFIED]** The secondary site accessibilitacentristorici.it claims 24/7 for ZTL B and C.

### 4.2 Pedestrian area and Piazza del Popolo

- **2020 pedestrianisation plan:** CesenaNotizie 15/05/2020 (Comune press release) [S]: https://www.cesenanotizie.net/2020/05/15/ampliamento-area-pedonale-del-centro-storico-comune-di-cesena-accelera-fase-di-sperimentazione/19277/
  > "pedonalizzazione permanente (0-24) di alcune aree del centro storico …"
  > "Le aree pedonali e le Ztl saranno valide tutti i giorni, feriali e festivi, compatibilmente allo svolgimento del mercato ambulante settimanale (mercoledì e sabato) …"
  > "si inserisce la mobilità sostenibile con la possibilità per i cittadini di potersi muovere all'interno delle aree pedonali e delle Ztl con biciclette e monopattini elettrici."
  - It was extended to 31/10/2021; the Comune page is now 404. **Current ordinance text not found [UNVERIFIED].**
- **Il Fatto Quotidiano, 24/01/2024** [S]: the centro storico is "per larga parte isola pedonale, in alcune strade è stato fissato anche il limite dei 10 chilometri all'ora". https://www.ilfattoquotidiano.it/2024/01/24/cesena-va-a-30-km-allora-da-26-anni-e-dal-2001-ha-dimezzato-gli-incidenti-e-adesso-si-pensa-a-nuove-misure-per-la-sicurezza/7420119/
- **Official ZTL layer [OD]** (`OD_ZTL_SDO`, 4 polygons: ZTL "A", "B", "C" and "PEDONALE"). Point-in-polygon tests:
  - Piazza del Popolo centre (44.13716, 12.24197) → ZTL **C**. Another point on the square falls outside every polygon, so there may be a digitising gap.
  - Via C. Battisti pedestrian part, Corso Mazzini, Via Montalti → ZTL **B**.
  - Via Zeffirino Re → ZTL **C**.
  - Piazza della Libertà → **PEDONALE**.
  - Piazzale Risorgimento, Rotonda dei Mulini, Via Zuccherificio, the west part of Via Battisti → outside all polygons.
  - The layer vintage is unknown; the 2020–21 pedestrianisation may not be reflected [UNVERIFIED].
- **No ordinance found that bans bicycles or e-scooters from Cesena's pedestrian area or Piazza del Popolo [UNVERIFIED].**
  - Under national law, e-scooters must keep **≤6 km/h** in any area pedonale, and both modes must give way to pedestrians or dismount (art. 182 c. 4).
  - **Weekly market on Wednesday and Saturday** in the centre squares: avoid scheduling sessions then.
- **Parks:** Cesena "Codice della convivenza civile" (DCC 6/2012, last amended by DCC 22 of 29/06/2023), art. 34 c. 1 a) [P]: https://static-www.comune.cesena.fc.it/wp-content/uploads/2023/11/CODICE_CONVIVENZA_CIVILE.pdf
  - In parks, green areas and public gardens it is forbidden "circolare con velocipedi e dispositivi per la micromobilità elettrica di cui al D.M. 4 giugno 2019 (fatte salve le aree appositamente destinate a piste ciclabili)".
  - Art. 36: bikes and micromobility chained to street furniture can be removed.

### 4.3 E-scooter sharing in Cesena

- **History:** Helbiz single operator from 2020 [S]. Then **RideMovi**, selected by public call of November 2023 for 2 years plus 1.
  - Comune 28/03/2024: https://www.comune.cesena.fc.it/novita/micromobilita-elettrica-ridemovi-porta-a-cesena-200-monopattini-e-150-e-bike/
  - Launched with 50 e-bikes and 100 e-scooters on 06/09/2024. Hubs included "Campus universitario" and the station. Comune 05/09/2024: https://www.comune.cesena.fc.it/novita/mobilita-sostenibile-in-citta-arrivano-50-e-bike-e-100-e-scooter-ridemovi/
- **RideMovi withdrew** (scooters and e-bikes) after about a year. CesenaToday 13/05/2025 [S]: https://www.cesenatoday.it/cronaca/monopattini-in-sharing-disdetta-cesena-calo-noleggi-risposta-assessore.html
  - The deputy mayor gave the reason as "domanda insufficiente", linked to the new CdS.
- **No active scooter-sharing operator and no published slow/no-ride zones found for Oct 2026 [UNVERIFIED].** Use private scooters that meet §1.

### 4.4 Zone 30

- Cesena introduced Zone 30 in 1998.
  - Il Fatto, 24/01/2024 [S]: "Oggi a Cesena si estendono per 143 chilometri … coprono il 38% della popolazione"; the zones are small and bounded by 50 km/h roads (Bikeitalia 2015 [S]).
- The PUMS (approved by DCC n. 33 of 26/05/2022 [P]: https://www.comune.cesena.fc.it/documento_pubblico/il-piano-urbano-della-mobilita-sostenibile-pums/) and the Biciplan (p. 38–39) plan to extend them. No city-wide "Città 30" was found.
- **There is no street-level open-data layer of Zone 30.** The "Mobilità urbana" table [OD] has ZONE_30_KM only for 2008–2009 (40.73 km).
- Posted limits must be checked on site.

---

## 5. Official open data

| Dataset | Publisher | Licence | Access |
|---|---|---|---|
| **Piste Ciclabili** (`od-piste-ciclabili-2019-line-sdo`), "Mappa delle Piste Ciclabili esistenti", EPSG:25832, with existing / being built / planned classes | Unione dei Comuni Valle del Savio, for Comune di Cesena | **CC BY 4.0** | Portal: https://dati.unionevallesavio.it/dataset/od-piste-ciclabili-2019-line-sdo · mirrored on dati.emilia-romagna.it (`piste-ciclabili`, modified 2026-08-17) and dati.gov.it (`piste-ciclabili5`) · Shapefile (WFS shape-zip): https://servizisit.unionevallesavio.it/geoserverckan/Cesena/OD_PISTE_CICLABILI_2019_LINE_SDO_preview/wfs?service=WFS&version=1.3.0&request=GetFeature&typename=Cesena_public:OD_PISTE_CICLABILI_2019_LINE_SDO_preview&outputformat=shape-zip · GeoJSON via WFS (`outputformat=application/json&srsName=EPSG:4326`) · CSV (no geometry): https://servizisit.unionevallesavio.it/geonextservices/gnsvcopendata/csv/1/OD_PISTE_CICLABILI_2019_LINE_SDO · Downloaded: `<workdir>/ext/cesena/opendata/piste_ciclabili_2019.{geojson,csv}`, `_shp.zip` |
| **Zone Traffico Limitato ZTL** (`od-ztl-sdo`): polygons with TIPO A, B, C, PEDONALE | same | CC BY 4.0 | WFS/SHP: https://servizisit.unionevallesavio.it/geoserverckan/Cesena/OD_ZTL_SDO_preview/wfs?service=WFS&version=1.3.0&request=GetFeature&typename=Cesena_public:OD_ZTL_SDO_preview&outputformat=shape-zip · Downloaded: `<workdir>/ext/cesena/opendata/ztl.geojson` |
| Mobilità urbana (km of cycle paths and Zone 30, m² pedestrian; **2008–2009 only**) | same | CC BY 4.0 | https://servizisit.unionevallesavio.it/geonextservices/gnsvcopendata/csv/1/OD_AMB_MOBILITA_URBANA |
| Traffico medio giornaliero – Sensori (**2012–2015**; includes Rot. Panathlon) | same | CC BY 4.0 | https://servizisit.unionevallesavio.it/geonextservices/gnsvcopendata/csv/1/OD_MOB_FLUS_TRAF_V (not downloaded) |
| Aste Stradali (road graph, CTR 1995 plus updates) | same | CC BY 4.0 | `od-od-aste-vg-sdo` on dati.unionevallesavio.it (not downloaded) |
| Regional DBTR "Elemento di percorso ciclabile" | Regione Emilia-Romagna (geoportale) | Probably CC BY 4.0 like other DBTR classes **[UNVERIFIED]** | INSPIRE records r_emiro:2017-11-24T130923 etc. (redirect to data.europa.eu; not retrieved) |
| OpenStreetMap (Overpass extract, bbox 44.133–44.153 N, 12.228–12.252 E) | OSM contributors | ODbL 1.0 | `<workdir>/ext/cesena/osm/ways_bbox.json` |

---

## 6. Constraints for route design

1. **Equipment and paperwork (e-scooter):**
   - contrassegno (mandatory since 17/05/2026), affixed visibly;
   - RC policy that quotes the contrassegno code (mandatory since 16/07/2026; €100–400 fine otherwise);
   - indicators and brake lights on both wheels; brakes on both wheels; motor ≤0.5 kW; speed limiter 20/6 km/h; horn; lights and reflectors; CE marking;
   - helmet (EN 1078/1080) for **every** rider; rider aged ≥14.
   - Give cyclists helmets too, for comparability.
2. **Only urban roads (inside the "centro abitato" signs) with a posted limit ≤50 km/h.**
   - Exclude the SS726 Tangenziale (Via La Malfa, 90 km/h).
   - Exclude any segment signed 70 km/h. OSM tags **Via Machiavelli north of the campus** as 70; verify the sign and the centro abitato boundary near the campus.
   - Exclude any segment outside the centro abitato, **even on a cycle path**.
3. **Both modes must use cycle tracks or lanes where they exist** (art. 182 c. 9 plus 75-quinquies). Design the loop so that both ride exactly the same facility.
4. **No contraflow:**
   - The scooter may not use "doppio senso ciclabile" lanes, which bikes may.
   - Two-way separated cycle tracks are fine in either direction.
   - Respect one-way carriageways (Machiavelli and Calvino near the Ponte Europa Unita node are one-way per OSM).
5. **No sidewalks for the scooter.**
   - "Corsia riservata su marciapiede" segments (Machiavelli, Calvino, Quasimodo, Mulini, Viale Europa) are rideable **only if signed as pista ciclabile or percorso pedonale-ciclabile**. Verify every one on site.
6. **Pedestrian areas:**
   - scooter ≤6 km/h; posted 10 km/h streets exist in the centre;
   - give way to pedestrians or dismount;
   - avoid market days (Wednesday and Saturday);
   - keep pedestrian-area time short, or analyse it as a separate segment, because the speed regimes differ between modes.
7. **Parks and green areas:** forbidden for both modes except on designated cycle paths (Codice convivenza civile, art. 34).
8. **Surfaces:**
   - avoid the Savio riverside path (Linea S; OSM fine_gravel or dirt);
   - avoid cobblestones (Via Zeffirino Re);
   - check the paving-stone sidewalk-level paths (Machiavelli) for scooter suitability.
9. **Roundabouts:**
   - prefer roundabouts with an external cycle ring and set-back crossings (Biciplan p. 53);
   - Rotonda dei Mulini is small (single lane);
   - Rotonda Panathlon (Bovio-Europa-SS9) is a Biciplan critical point.
10. **Via Emilia urban axis.** Oberdan → Bovio → Europa → Zuccherificio → Ponte del Risorgimento → Matteotti carries Via Emilia through traffic [INF].
    - Use only the separated cycle tracks along it.
    - Do not use the Via Zuccherificio or Piazzale Risorgimento carriageways. The Biciplan marks the Macchiavelli–Risorgimento link as **absent** (long-term) and Piazzale Risorgimento as a **critical point**.
11. **Devices:** no handheld use and no headphones (art. 173). Scooter riders keep both hands on the handlebar, so mount any sensors.

### 6.1 Most promising candidate links (Biciplan status / open data status; all need on-site checks)

- **Campus → south along Via Machiavelli** to the Machiavelli / Calvino / Ponte Europa Unita node.
  - Biciplan C "Europa(Università)–Macchiavelli": present, improvable.
  - OD: existing, partly at sidewalk level, paving stones.
- **Via Calvino / Viale Europa cycle track → Rotonda Panathlon → Viale Bovio → Viale Angeloni** (Bovio built 2023–24) → Corso Cavour / Viale Finali → Piazza della Libertà.
  - Biciplan C and Linea 5: present, improvable. OD: existing in sede propria.
  - This gives a separated link from the campus to the centre's east side.
- **Centre:** Piazza della Libertà ↔ Piazza del Popolo.
  - Linea 6 says present and optimal; Linea 8 says absent.
  - Pedestrian / ZTL: scooter at 6 km/h.
- **Via Cesare Battisti** (Piazza del Popolo ↔ Piazzale Risorgimento).
  - Biciplan C and Linea 7: **present and optimal** (green). OD: reserved lane on the carriageway.
  - OSM: 30 km/h west part plus pedestrian east part.
- **Piazzale Risorgimento → Via Zuccherificio → Rotonda dei Mulini → Machiavelli → campus.**
  - This is the **weak link**: Biciplan "absent" with a long-term plan; OD 209 m existing plus 356 m planned; OSM shows no cycleway in the middle.
  - Use it only if a separated path exists on the ground. Otherwise close the loop back through Viale Europa / Calvino.
- **Ponte Europa Unita** (OD 312 m existing) gives an optional crossing of the Savio to Oltre Savio (Viale della Resistenza and Viale Gramsci cycle paths exist).
  - Returning east via Ponte del Risorgimento or Viale Matteotti means using the Via Emilia W corridor (separated track exists per OD).

---

## 7. Open items to verify on site or with the Comune

- Signage of each sidewalk-level cycle segment (Machiavelli, Calvino, Viale Europa, Via Mulini, Ponte Europa Unita side paths): pista ciclabile, ciclopedonale, or plain sidewalk.
- Speed-limit signs and the "centro abitato" boundary on Via Machiavelli at and north of the campus (OSM says 70 km/h).
- Whether the Rotonda Panathlon cycle ring exists; current layout of Piazzale Risorgimento and Via Zuccherificio.
- Current pedestrian-area ordinance (perimeter, hours, any velocipede or micromobility restriction, 10 km/h streets) and ZTL hours. Ask Servizio Mobilità e Trasporti, Piazza del Popolo 10, tel. 0547-356111.
- Surface of the Machiavelli paving-stone path and of the Ponte Europa Unita side paths.
- Whether any 2026 MIT/MIMIT act changed the insurance or contrassegno regime after July 2026 (none found).

## 8. Files

- **Biciplan:** `<workdir>/ext/cesena/VeloCe_Biciplan_Cesena.pdf`; text `<workdir>/pdftext/biciplan/biciplan_pages.txt`; images `<workdir>/pdftext/biciplan/img/pg-NN.png`.
- **Laws and circulars:**
  - `<workdir>/ext/cesena/web/nm_l160_art1*.html`, `nm_cds_art{3,173,182}.html`, `nm_l177_2024.html`;
  - `circ_interno_38625_20241220.pdf`, `circ_interno_20260427_contrassegno.pdf`, `RD_110_26.pdf`, `DM_250_2025.pdf`, `mit_*.html`;
  - text in `<workdir>/pdftext/`.
- **Comune:** `Disciplinare_2025_ZTL_ZRU_rev02_DG243_2025.pdf`, `CODICE_CONVIVENZA_CIVILE.pdf`, `cc_*.html`.
- **Open data:** `<workdir>/ext/cesena/opendata/`. **OSM:** `<workdir>/ext/cesena/osm/`.
- **Helper scripts** (kept outside ext): `<workdir>/tools/match_cycle.py`, `<workdir>/tools/pip.py`, `<workdir>/tools/wpextract.py`.
