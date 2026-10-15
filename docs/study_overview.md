# Panoramica dello studio

*Documento sintetico per il responsabile scientifico - ottobre 2026. Stato: progettazione; nessun
dato reale del nuovo studio è stato acquisito.*

## In breve

Le stesse persone percorrono lo stesso anello urbano di Cesena **una volta in monopattino
elettrico e una volta in bicicletta tradizionale** (eventualmente due volte per mezzo, in ordine
controbilanciato), indossando gli occhiali **Meta Project Aria Gen 2** come unico sensore.
Confrontiamo **dove guardano**, **come muovono la testa** e **come guidano** (velocità, fermate,
rallentamenti stimati) sugli **stessi tratti di infrastruttura**, e valutiamo **che cosa si può
misurare in modo affidabile** con un solo dispositivo indossabile.

## Che cosa è già noto e che cosa è nuovo

- Il confronto bici/monopattino con eye tracking sulle stesse persone **esiste già**, ma su un
  solo tratto breve e un solo passaggio: Pashkevich et al. 2022 (12 persone, 50 m) e
  Trefzger et al. 2021 (24 persone, 200 m, sempre prima la bici). Velocità medie simili; piccole
  differenze di sguardo, più marcate su fondo irregolare.
- Il riferimento metodologico principale per il monopattino è Kegalle et al. 2025 (Melbourne,
  solo monopattino): abbiamo rianalizzato i loro dati pubblici e riprodotto i risultati
  principali, trovando anche metriche mal definite ed errori statistici
  (`docs/literature/kegalle_replication.md`).
- **Il nostro contributo realistico** (`docs/research/scientific_contribution.md`):
  1. confronto entro-soggetto controbilanciato e ripetuto, **a scala di percorso**, con
     confronto sugli **stessi tratti fisici** e più modalità (sguardo, testa, dinamica stimata);
  2. **validazione della misura con un solo dispositivo indossabile** (copertura e qualità di
     VIO, sguardo, mani; affidabilità delle stime di velocità e decelerazione): manca in
     letteratura;
  3. **ripetibilità individuale** delle misure tra prove e tra mezzi (se due prove per mezzo).
  Esplorativi: relazione temporale percezione-azione, interazione mezzo x infrastruttura,
  mani/postura, PPG.

## Domande di ricerca

RQ1 effetto del mezzo; RQ2 effetto dell'infrastruttura (e interazione con il mezzo); RQ3
percezione-azione (esplorativa); RQ4 coerenza individuale e ripetibilità; RQ5 mani e postura
(esplorativa). Dettagli: `docs/research_questions.md`.

## Che cosa misuriamo (e che cosa no)

| Tipo | Esempi | Note |
|---|---|---|
| Misure dirette | sguardo (angoli, 30 Hz), rotazione della testa (giroscopio, VIO), mani quando rilevate | con validità e copertura per ogni finestra |
| Stime indirette | velocità, decelerazioni, fermate, direzione di marcia, oscillazioni laterali | stime dal moto della testa, mai "misure del mezzo" |
| Non identificabili | forza sui freni, sterzo, pedalata, moto del telaio, distanza metrica dagli altri utenti senza ricostruzione validata, stress | esclusi |

Catalogo completo: `docs/methodology/metrics_catalog.md`.

## Percorso

Bozza **CES_A** (consigliata): anello di **4,25 km** dal Campus (Via dell'Università 50):
pista lungo Via Machiavelli, Rotonda dei Mulini, Via Mulini, margine del centro storico (ZTL),
Via Cesare Battisti, ponte del Risorgimento (pista), Viale della Resistenza, Ponte Europa Unita,
Via Calvino/Quasimodo. Stima **16-24 minuti** di guida. Alternativa **CES_B** (3,66 km, senza
attraversare il Savio). Geometria da OpenStreetMap con regole di legalità per entrambi i mezzi,
confrontata con i dati aperti del Comune; **da verificare sul posto**. Mappa interattiva:
`docs/route/cesena_route_map.html`.

## Pilota con 3 partecipanti

Studio di **fattibilità** (non generalizzabile, nessun test di ipotesi): una visita con 4 giri
(monopattino-bici-bici-monopattino o simmetrico), pause di 10 minuti, controllo dell'accuratezza
dello sguardo prima e dopo ogni giro, questionari brevi. Obiettivi: verificare acquisizione e
qualità dei dati, procedure e sicurezza, stimare la variabilità delle misure per dimensionare lo
studio principale. Protocollo: `docs/methodology/pilot_protocol.md`; piano statistico:
`docs/methodology/statistical_analysis_plan.md`.

## Etica e privacy

Nessuna acquisizione con partecipanti prima delle autorizzazioni. Elaborazione locale; volti e
targhe sfocati con EgoBlur prima di ogni visione; immagini degli occhi e metadati del dispositivo
esclusi dalle copie di lavoro; nessun uso di servizi cloud (MPS) senza autorizzazione.
Documenti: `docs/ethics/` (italiano), `docs/privacy_pipeline.md`.

## Stato del software

Pipeline esistente conservata ed estesa: schema a due mezzi (manifest v2, catalogo mezzi),
controllo qualità per flusso, estrazione Aria aggiornata (VIO con stato e reset, VIO ad alta
frequenza, hand tracking) e verificata su registrazioni Gen 2 ufficiali di test, allineamento GPS
ai tratti del percorso, piano delle prove controbilanciato, tabelle di confronto entro-soggetto.
Test automatici superati su dati sintetici; **nessuna validazione su dati reali di guida**.

## Decisioni richieste al responsabile

1. Contributo e domanda principale proposti (`docs/research/scientific_contribution.md`).
2. Una o due prove per mezzo nel pilota; una o due visite.
3. Percorso CES_A o CES_B, dopo il sopralluogo.
4. Profilo di registrazione definitivo (chiavi in formato documentato, algoritmo di eye tracking,
   VIO ad alta frequenza esplicito; `configs/recording_profiles/README.md`).
5. Mezzi (modello di monopattino, contrassegno, assicurazione; bicicletta), caschi.
6. Percorso autorizzativo per il pilota (Comitato Etico, DPO).
