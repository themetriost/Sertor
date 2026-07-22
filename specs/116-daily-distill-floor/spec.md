# Feature Specification: Daily distill floor (≥1 distill/giorno)

**Feature Branch**: `116-daily-distill-floor`

**Created**: 2026-07-22

**Status**: Draft

**Input**: E10-FEAT-039 (epica `debito-tecnico`). Direttiva utente 2026-07-21: dare al passo `distill` del
rituale wiki una **soluzione definitiva** con un pavimento di **almeno un distill al giorno**. Requisiti
EARS: `requirements/debito-tecnico/daily-distill-floor/requirements.md`.

> **⚑ DESIGN FINALE (2026-07-22, supera le sezioni sotto scritte per la prima ipotesi).** In corso di
> implementazione l'utente ha ricalibrato due volte: (1) *«non uno strumento che indovina i candidati con
> un debito, ma un OBBLIGO giornaliero»* → il debito `distill-audit` NON è il gate, è **contesto advisory**
> allegato; (2) *«bloccante: senza almeno un distill non si può fare merge»* → l'enforcement è un **hook
> `PreToolUse` che BLOCCA il merge di consegna** (`git merge <feature>` / `gh pr merge`) finché la giornata
> non ha una voce `distill` nel log. **Gate = solo presenza** («c'è una voce `distill` oggi? sì/no»), non
> un conteggio. Il segnale-prosa dell'audit, misurato sul dogfood reale, è rumore-dominato (228 vs 9
> wikilink) → confermato che l'audit vale solo come *hint*, non come cancello. Le User Story / FR / SC qui
> sotto restano validi per il TOOL (US1) e il concetto di pavimento, ma la *forma dell'enforcement* è il
> merge-block (non il nudge persistente della prima stesura). Vedi [[feedback_distill_floor_obbligo_non_scoperta]].

## User Scenarios & Testing *(mandatory)*

Il rituale wiki chiude ogni step significativo con `record → distill → lint → explainer`. Di questi,
`distill` (estrarre in pagine proprie le entità durevoli che il lavoro fa emergere) è **giudizio**,
**condizionale** e **auto-eseguito** dall'agente — senza alcuna rete. `record`, invece, è delegato a un
sub-agente **e** sollecitato da un hook: sopravvive. Risultato osservato: su un progetto reale (il dogfood
di Sertor) `distill` è stato **dichiarato zero volte per ~5 settimane** pur consegnando decine di step;
un secondo progetto indipendente (nodo Acta) ha misurato lo stesso esito — un wiki che cresce in cronologia
e sorgenti ma resta **povero nello strato che dà valore** (i concetti navigabili). La feature dà a `distill`
la stessa rete di `record`, più uno strumento che rende **visibile** il debito accumulato.

### User Story 1 - Il debito di distillazione è scopribile a comando (Priority: P1)

L'agente (o l'utente) lancia uno strumento che scandisce **tutto il wiki** e restituisce l'elenco delle
**entità referenziate da più punti ma senza pagina propria**, con un **numero di debito N**. Non serve che
l'agente «si ricordi» cosa distillare: lo strumento glielo mette davanti, indipendentemente da quando
quell'entità è stata introdotta.

**Why this priority**: È la fondazione. Senza una scoperta **deterministica e cross-sessione** del debito,
il pavimento sarebbe di nuovo affidato alla memoria dell'agente — la causa-radice del fallimento. Lo
strumento è anche indipendentemente utile (un audit di salute del wiki) a prescindere dall'hook.

**Independent Test**: Su un wiki con entità citate ≥k volte (via wikilink penzolanti e/o in prosa) senza
pagina, eseguire lo strumento e verificare che le elenchi ordinate per frequenza e riporti un debito N
corretto; su un wiki senza tali entità, N=0 e lista vuota. Nessuna pagina viene modificata (sola lettura).

**Acceptance Scenarios**:

1. **Given** un wiki dove `[[subscribe]]` è citato da 6 pagine senza `subscribe.md`, **When** si esegue
   l'audit, **Then** «subscribe» compare tra i candidati con frequenza 6 e concorre al debito N.
2. **Given** un termine-entità menzionato ≥k volte in prosa (senza wikilink) senza pagina, **When** si
   esegue l'audit, **Then** compare tra i candidati per il segnale frequenza-prosa.
3. **Given** un wiki dove ogni entità citata ha già la sua pagina, **When** si esegue l'audit, **Then** il
   debito N è 0 e la lista candidati è vuota.
4. **Given** lo stesso wiki eseguito due volte senza modifiche, **When** si confrontano gli output, **Then**
   sono identici (deterministico) e nessun file è stato toccato.

---

### User Story 2 - Il pavimento giornaliero è persistente (Priority: P1)

Se in una giornata di lavoro significativo non è ancora stata registrata una distillazione **e** il debito è
> 0, l'agente riceve un promemoria **ripetuto** (all'avvio sessione e a fine turno/sessione) che dichiara il
pavimento non raggiunto, il debito N e i candidati principali — finché la giornata non ha una distillazione
o un «no» dichiarato. Non un singolo avviso liquidabile: la stessa insistenza che tiene onesto `record`.

**Why this priority**: È il cuore del «pavimento». Un singolo nudge a inizio sessione è la modalità di
fallimento già vissuta (la dichiarazione forzata precedente veniva ignorata). La persistenza rende lo skip
una **scelta ripetuta e visibile**, non una dimenticanza.

**Independent Test**: Simulare una giornata con lavoro significativo, debito N>0 e nessuna voce `distill`
del giorno → verificare che il promemoria compaia all'avvio e si ripeta a fine turno; poi registrare una
voce `distill` (o un «no» dichiarato) → verificare che il promemoria **si auto-silenzia**. Con debito N=0,
nessun promemoria compare mai.

**Acceptance Scenarios**:

1. **Given** una giornata con lavoro significativo, N>0 e nessuna distillazione, **When** inizia la sessione,
   **Then** l'agente vede lo stato del pavimento (non raggiunto, debito N, top candidati).
2. **Given** lo stesso stato, **When** un turno/sessione termina, **Then** il promemoria si ripete.
3. **Given** la giornata acquisisce una voce `distill` (o un «no» dichiarato), **When** un turno termina,
   **Then** il promemoria non compare più (auto-silenzio).
4. **Given** debito N=0, **When** inizia la sessione o termina un turno, **Then** nessun promemoria compare.
5. **Given** qualunque stato, **When** l'hook gira, **Then** non blocca il flusso (sempre esito neutro) e
   non scrive pagine né decide cosa distillare.

---

### User Story 3 - Un «no» al distill deve costare (Priority: P2)

Quando l'agente decide che per lo step non serve distillare, la dichiarazione «distill: non necessario» deve
**nominare i candidati considerati** (quelli emersi dallo strumento) e perché non sono durevoli — non è più
una casella spuntabile a costo zero.

**Why this priority**: Senza questo, il pavimento si degrada a cerimonia: l'agente scrive «non serve» senza
guardare i candidati, come prima. Mettere i candidati *davanti* al verdetto e pretendere che il «no» li
nomini alza il costo dello skip riflesso.

**Independent Test**: Verificare che il contratto host-facing (blocco rituale + playbook) richieda
esplicitamente che un verdetto negativo citi i candidati; una dichiarazione «non serve» nuda non soddisfa il
rituale.

**Acceptance Scenarios**:

1. **Given** candidati emersi dallo strumento, **When** l'agente dichiara «distill: non necessario», **Then**
   la dichiarazione nomina quei candidati e perché non durevoli.
2. **Given** un «no» nudo senza riferimento ai candidati, **When** si valuta la chiusura dello step, **Then**
   non soddisfa il contratto del rituale.

---

### User Story 4 - Ogni ospite col wiki riceve il pavimento (Priority: P2)

Il pavimento non è una regola solo del progetto Sertor: qualunque progetto che installa la capacità wiki
riceve lo strumento, l'hook e il contratto di rituale aggiornato, con lo stesso comportamento su entrambi
gli assistenti supportati.

**Why this priority**: Per la definizione di «feature completa» del progetto, una capacità host-facing non è
«done» finché non è installabile su un ospite. Ma il valore è dimostrabile già sul progetto stesso (US1–US3),
quindi la distribuzione è P2.

**Independent Test**: Eseguire l'installazione della capacità wiki su un progetto ospite pulito e verificare
che lo strumento sia invocabile, l'hook cablato e il blocco di rituale aggiornato — identico sui due
assistenti; il bundle resta in sync con la guardia dedicata.

**Acceptance Scenarios**:

1. **Given** un progetto ospite senza la feature, **When** installa/aggiorna la capacità wiki, **Then**
   ottiene strumento + hook + contratto di rituale aggiornato, con parità tra gli assistenti.
2. **Given** l'asset host-facing modificato, **When** gira la guardia di sincronizzazione, **Then** il bundle
   e la sorgente non divergono.

---

### Edge Cases

- **Giornata senza candidati (N=0):** nessun pavimento da imporre → nessun promemoria (le giornate legittime
  senza debito non innescano rumore).
- **Giornata senza lavoro significativo:** il pavimento non scatta (una giornata puramente meccanica non
  richiede distillazione) — coerente con la «regola aurea» del wiki.
- **Falso positivo del segnale-prosa:** un termine frequente non è un'entità durevole → costa all'agente un
  «no» motivato, mai una pagina spuria; i wikilink penzolanti restano il segnale ad alta precisione.
- **Corpus grande:** l'audit dell'intero corpus a ogni turno sarebbe costoso → si valuta al più una volta al
  giorno, con lo stato riusato entro la giornata.
- **«No» dichiarato ma non genuino:** un hook deterministico non può distinguere un «no» sincero da uno
  falso → limite onesto dichiarato: l'obiettivo è rendere lo skip **caro e visibile**, non impossibile.
- **Scope indeterminabile / corpus illeggibile:** lo strumento fallisce in modo esplicito, non restituisce
  «N=0» come se non ci fosse nulla da distillare.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Il sistema DEVE fornire un'operazione **deterministica e offline** (nessun LLM) che scandisce
  **l'intero corpus del wiki** (non il diff di un singolo step) e riporta le **entità candidate a
  distillazione** — referenziate da ≥k punti e prive di pagina propria.
- **FR-002**: La rilevazione DEVE usare solo **segnali strutturali deterministici**: (i) **wikilink
  penzolanti** (`[[x]]` senza `x.md`) contati per frequenza, e (ii) **frequenza-prosa** di termini/frasi
  candidati (regola fissa, stop-word escluse, soglia k) — senza modello semantico né LLM.
- **FR-003**: L'operazione DEVE calcolare un **debito N** (numero di entità candidate senza pagina) e una
  lista candidati ordinata per frequenza.
- **FR-004**: L'operazione DEVE emettere un output **leggibile da macchina** (contratto JSON versionato) e un
  **summary umano** conciso, coerente con gli altri strumenti wiki del progetto.
- **FR-005**: L'operazione DEVE essere **host-agnostica**: scope e tassonomia letti dalla configurazione del
  wiki, nessuna assunzione sulla struttura di un progetto specifico.
- **FR-006**: Il segnale frequenza-prosa DEVE restare una **regola deterministica fissa**; lo strumento
  **trova**, l'agente **giudica** la durevolezza (confine deterministico↔giudizio).
- **FR-007**: Il sistema DEVE, in una **giornata attiva** priva di distillazione dichiarata e con debito N>0,
  **segnalare (non-bloccante)** che il pavimento non è raggiunto, indicando il debito N e i candidati
  principali.
- **FR-008**: La valutazione del pavimento DEVE avvenire **all'avvio sessione** e ripetersi **a fine
  turno/sessione**, riusando lo stato al più una volta al giorno per non riscandire ad ogni turno.
- **FR-009**: Il promemoria DEVE **auto-silenziarsi** appena la giornata ha una voce `distill` o un «no»
  dichiarato.
- **FR-010**: L'hook DEVE essere **non-bloccante** e non DEVE scrivere pagine né decidere cosa distillare
  (il giudizio resta nel flusso principale).
- **FR-011**: Il contratto di rituale distribuito (blocco + playbook) DEVE richiedere che un verdetto
  «distill: non necessario» **nomini i candidati considerati** e perché non durevoli; un «no» nudo non
  soddisfa il rituale.
- **FR-012**: Il rituale (blocco + playbook) DEVE enunciare la **regola standing** «≥1 distill per giornata
  attiva», con il debito N come metrica leggera di fine sessione.
- **FR-013**: Tutte le parti (strumento, hook, blocco/playbook) DEVONO essere **distribuibili agli ospiti**
  tramite l'installer, con **parità tra gli assistenti supportati**, e il bundle DEVE restare in sync
  (guardia dedicata).

### Key Entities

- **Entità candidata a distillazione**: un concetto/entità referenziato da ≥k punti del corpus senza pagina
  propria; attributi: nome, frequenza, segnale d'origine (wikilink penzolante | prosa), sedi di riferimento.
- **Debito di distillazione (N)**: il conteggio delle entità candidate senza pagina in un dato momento —
  metrica leggera e osservabile di salute del wiki.
- **Stato del pavimento giornaliero**: per la giornata corrente — se esiste una distillazione dichiarata,
  il debito N, l'ultima valutazione — usato dall'hook per decidere se sollecitare.
- **Dichiarazione di rituale**: il verdetto esplicito di `record`/`distill`/`lint` a chiusura di uno step;
  per `distill` un «no» deve nominare i candidati.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Su un corpus con entità note referenziate da ≥k punti senza pagina, lo strumento le individua
  tutte (nessun falso negativo sui wikilink penzolanti) e riporta un debito N pari al loro numero.
- **SC-002**: Eseguito due volte sullo stesso corpus immutato, lo strumento produce output identico e non
  modifica alcun file (determinismo + sola lettura verificabili).
- **SC-003**: In una giornata con debito N>0 e nessuna distillazione, il promemoria del pavimento compare
  all'avvio e si ripete a fine turno finché la condizione non è soddisfatta; una volta soddisfatta, non
  compare più nella stessa giornata.
- **SC-004**: Con debito N=0, nessun promemoria del pavimento compare in nessun momento della giornata.
- **SC-005**: L'hook non altera mai l'esito del flusso di lavoro (nessun blocco) in tutti gli scenari.
- **SC-006**: Su un progetto ospite pulito, dopo l'installazione della capacità wiki, lo strumento è
  invocabile, l'hook è attivo e il contratto di rituale aggiornato è presente — identico sui due assistenti.
- **SC-007**: Misura di regressione anti-debito sul dogfood: dopo l'adozione, ogni giornata attiva chiude con
  una distillazione dichiarata o un «no» che nomina i candidati (nessuna ricomparsa del buco di 5 settimane).

## Assumptions

- **Scope del corpus**: l'audit copre il wiki (e, se la configurazione lo indica, i requirements); il default
  e l'eventuale flag di inclusione/esclusione si fissano in fase di clarify/plan (DA-1/DA-2 dei requirements).
- **Regola «entità candidata» in prosa**: si assume una regola deterministica ad alta precisione (es. frasi
  capitalizzate/multi-parola, con stop-word escluse e soglia k); la definizione esatta è materia di clarify —
  i wikilink penzolanti restano il segnale primario ad alta precisione.
- **Rilevazione «giornata attiva» e «voce distill del giorno»**: si riusa il meccanismo già impiegato dalla
  rete di `record` (file più recenti dell'ultima voce di log per «attiva»; presenza dell'operazione `distill`
  nel log del giorno). Dettaglio in clarify (DA-3).
- **Collocazione dell'hook**: si assume l'estensione/affiancamento della rete `record` esistente più un check
  all'avvio sessione; nuovo asset separato vs estensione è scelta di plan (DA-4).
- **Stato once-per-day**: si assume un piccolo file di stato per non riscandire ad ogni turno; la sede esatta
  è dettaglio di plan (DA-5).
- **Complementarità, non sostituzione**: lo strumento di audit cross-sessione è complementare all'esistente
  scoperta per-step (git-diff, FEAT-026); quest'ultima non viene riscritta.
- **Limite onesto del pavimento**: un hook deterministico non può verificare che un «no» sia genuino; la
  feature massimizza il costo/visibilità dello skip, non lo rende impossibile — assunzione dichiarata, non un
  gap da chiudere.
- **Confine deterministico↔giudizio (non negoziabile)**: nessun LLM nello strumento/core; l'atto di
  distillare e il giudizio di durevolezza restano nel flusso principale dell'agente.
