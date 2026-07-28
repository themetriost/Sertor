# Epica E16 — Evoluzione del modello wiki (sfruttare meglio il confine D↔N)

> **Stato: epica FUTURA — non iniziata.** Nessuna feature in corso, nessuna consegnata. Esiste per dare
> una **casa durevole** a un corpo di richieste che finora viveva come «idee da discutere» nella roadmap.
>
> **Origine:** handoff del nodo *Nunzio* (2026-07-09), nato da un dogfooding reale — un wiki di 33 pagine
> costruito da zero su un corpus di 34 documenti con `sertor-wiki-tools` e il playbook — più l'analisi
> **sul codice** di due sistemi concorrenti. Documento integrale:
> [`wiki/sources/usersfeedback/processed/evoluzione-modello-wiki-lezioni-da-openwiki-e-wiki-compiler.md`](../../wiki/sources/usersfeedback/processed/evoluzione-modello-wiki-lezioni-da-openwiki-e-wiki-compiler.md)
> · catalogo: [[archivio-processati]].

## 1. Visione e problema (perché)

Fare un wiki sono **due lavori separabili**: qualcuno lo **compila** (decide cosa scrivere, come
collegarlo, cosa significa) e qualcuno lo **verifica** (i link esistono, le pagine non sono orfane, il
frontmatter c'è). Il primo richiede di capire il significato; il secondo si fa **contando**.

| Sistema | Compila | Verifica |
|---|---|---|
| `langchain-ai/openwiki` | LLM | **nessuno** |
| **Sertor** · `nvk/llm-wiki` | LLM | **codice** |
| `Emmimal/wiki-compiler` | codice | codice |

**Il dato che motiva l'epica: i due estremi convergono da soli verso il centro dove Sertor è già.**
L'autore del compilatore puramente deterministico conclude che l'LLM serve per *«il 10% che richiede
comprensione, non per il 90% puramente meccanico»* — parola per parola il confine formalizzato in
[[deterministic-vs-judgment]]. E `nvk/llm-wiki`, partito dall'agente, ha finito per aggiungere un helper
Python per *«structural checks and safe migrations that do not require an LLM»*. Due progetti
indipendenti, partiti dai capi opposti, arrivati dove eravamo.

> **La tesi dell'epica non è spostare quel confine: è sfruttarlo meglio.** Oggi lasciamo all'LLM lavoro
> che è **aritmetica** (i backlink sono la relazione inversa dei wikilink, già estratti da `collect.py`),
> e non **promettiamo né verifichiamo** il determinismo che dichiariamo. Entrambe sono occasioni mancate
> sul nostro stesso differenziatore.

Il limite da rispettare, dichiarato dalla fonte con onestà: il modello puramente deterministico
**fallisce producendo struttura corretta e vuota** — il grafo lessicale collega per corrispondenza
esatta, e *«nulla in quella pipeline capisce il significato»*. Le due promesse di un wiki — *è vero* e
*i collegamenti esistono* — richiedono **due macchine diverse**. Il core non deve scrivere prosa.

## 2. Ambito

### In ambito
- **Generazione deterministica** di ciò che è derivabile (backlink / «Referenced by»), **preservando le
  sezioni scritte a mano**.
- **Difesa del confine D↔N**: misurare quanto il core deterministico viene *aggirato* dall'LLM, prima di
  scrivere codice per impedirlo.
- **Preparazione deterministica del lavoro di giudizio**: da `scan` a un *piano* (quali pagine sono
  probabilmente stantie), e una **coda di riverifica dei «passivi»** (comandi, versioni, URL) ordinata
  per età.
- **Rendere misurato il differenziatore**: riproducibilità cross-OS verificata in CI e benchmark di
  scalabilità di `lint`/`collect`.

### Fuori ambito
- **Spostare il confine D↔N.** Il core non genera prosa e non chiama LLM: è il vincolo, non un dettaglio.
- **Connettori di ingestione** — richiesta §7 della fonte, ma mappa su un'epica esistente: **E7
  `ingestione-estesa`**. Citata, non duplicata (regola A-12).
- **Comunicare il differenziatore all'esterno** («una richiesta a costo zero» della fonte: il confine
  D↔N è la cosa migliore che Sertor ha, ed è documentata in un playbook che legge solo l'assistente) →
  **E13 Fase 2 (marketing)**, sbloccata dal go-public.
- Imitare OpenWiki sulla **validazione**: nel suo sorgente non esiste alcun controllo deterministico
  (nessuna occorrenza di `brokenLink`/`orphan`/`validateWiki`). Coerente col loro obiettivo headless,
  **non da imitare**.

### ✅ Già chiuso — non riaprire
La richiesta **priorità 2** della fonte (l'hook `SessionStart` che violava il Principio X con percorsi
hard-coded, `roadmap.md` assunto anziché configurato, e il fallback del log rotto) **è risolta**:
`wiki-session-start.py` legge oggi i percorsi dal profilo (`index_file`, `log_dir`/`log_file`, e l'opt-in
`[ritual].exec_page`) e **legge solo file che esistono** — un wiki fresco senza roadmap non produce più
letture fallite. Chiusa da E10-FEAT-029 + la migrazione `.ps1`→`.py` (A-09/E2-FEAT-010).

## 3. Criteri di successo (misurabili, tech-agnostici)

- **SC-01** — Esiste un **dato** su quante sessioni reali attraversano il core deterministico rispetto a
  quelle in cui l'LLM scrive i file a mano (oggi il solo campione noto è *zero invocazioni di
  `upsert-index`* su un progetto ben istruito).
- **SC-02** — La sezione di backlink di una pagina è **derivata**, non scritta a mano, e un backlink
  stantio è **impossibile per costruzione**; le sezioni redatte a mano sopravvivono a una rigenerazione.
- **SC-03** — Il determinismo è **verificato**, non solo dichiarato: stesso corpus su due OS ⇒ output
  identico, controllato in CI.
- **SC-04** — Il costo di `lint`/`collect` è **noto** in funzione del numero di pagine, e il rilevamento
  degli orfani non è quadratico (o lo è **dichiaratamente**, con la soglia oltre cui morde).
- **SC-05** — Il lavoro di giudizio arriva **preparato**: il curatore riceve una coda ordinata di pagine
  da riverificare invece di rileggere il wiki.

## 4. Stakeholder e attori

- **Il curatore del wiki** (flusso principale / `wiki-curator`) — riceve lavoro preparato invece di
  cercarlo.
- **Gli ospiti** — ereditano generazione e guardie con `sertor install wiki`: ogni feature qui è
  host-facing e ricade sotto la regola *«una feature è completa solo se è installabile su un ospite»*.
- **Il nodo *Nunzio*** — origine delle richieste; destinatario naturale di un riscontro.

## 5. Vincoli, assunzioni e dipendenze

- **Vincolo forte:** il nucleo resta **zero-LLM, offline, stdlib** ([[wiki-tools]]). Ogni feature qui sta
  dal lato deterministico o **non entra**.
- **Assunzione da verificare:** che la quota di pagina *derivabile* sia abbastanza grande da valere la
  generazione. La fonte lo suggerisce (il `## Collegamenti` di ogni pagina è di fatto un backlink set
  curato a mano) ma **non l'ha misurata**.
- **Dipendenza:** FEAT-003 converge con **E10-FEAT-049** (lint sui riferimenti entranti) e con
  **E13-FEAT-014** (anti-drift della doc utente): sono la stessa forma — *il codice dice dove guardare,
  l'LLM se è ancora vero*. **Progettarle insieme.**
- **Sospetto non verificato** (dichiarato tale dalla fonte): il rilevamento orfani potrebbe essere O(n²).
  Il concorrente riporta di aver dovuto passare a scaling quasi-lineare, col lint al 56% del tempo totale.

## 6. Rischi

| Rischio | Effetto | Mitigazione |
|---|---|---|
| Generare struttura **corretta e vuota** | Pagine che sembrano collegate e non dicono nulla | Il core genera **solo** relazioni già presenti nei dati; la prosa resta all'LLM |
| Una rigenerazione **sovrascrive** il lavoro a mano | Perdita di contenuto curato | Rewriter *section-aware*: sezioni generate delimitate, il resto intoccato (come `wiki-compiler`) |
| Le fonti sono **autodichiarate** | Progettare su numeri altrui | I benchmark del concorrente vengono dal suo articolo, non da una nostra esecuzione: **rimisurare da noi** prima di decidere |
| Software in movimento | Analisi che invecchia | OpenWiki era a `v0.1.0` con commit del giorno stesso; **riverificare** prima di implementare |

## 7. Backlog di feature

| ID | Feature | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|--------------------|-------------------|-------|
| FEAT-001 | **Misurare quanto il core D↔N viene *aggirato*** — dato prima del codice. Costruendo un wiki reale, `index.md` è stato scritto **a mano** invece che via `upsert-index`, sia dal flusso principale sia dal `wiki-curator` delegato: nessuno ha disobbedito, semplicemente scrivere il file era la strada più breve e **nulla lo impediva**. Le garanzie del core (idempotenza, contratti JSON, verificabilità) valgono **solo se il core viene attraversato**. Misurare in quante sessioni reali viene invocato; *poi* decidere se serve un lint che rilevi un `index.md` non conforme a ciò che `upsert-index` avrebbe prodotto, e se convenga rendere il core la via **più comoda**, non solo quella corretta | Un confine architetturale difeso solo dalla buona volontà dell'assistente è nominale | **Should (P1)** | 📋 da fare — la fonte lo indica come il rilievo più importante; nessuna riga di codice nuova richiesta per il primo passo |
| FEAT-002 | **Backlink deterministici generati dal core** — `collect.py` estrae già i wikilink **uscenti** per ogni pagina; i backlink sono la **relazione inversa**, cioè aritmetica. Oggi li scrive l'LLM a mano e il playbook gli chiede di decidere *«quali backlink hanno senso»*. Distinzione da preservare: *quali backlink hanno senso in prosa* è **giudizio**; *quali pagine puntano a questa* è **aritmetica**. Generare una sezione rigenerata a ogni run (mai stantia per costruzione, gratis in token), con **rewriter section-aware** che preserva le sezioni scritte a mano | Toglie all'LLM un compito in cui non porta valore, e rende impossibile un backlink stantio | **Could (P2)** | 📋 da fare |
| FEAT-003 | **`sertor-wiki-tools plan` + coda di riverifica dei «passivi»** — `scan` è **a un passo** da un update diff-driven: già confronta lo stato del repo con l'ultima voce di log, ma non produce un *piano di lavoro*. Emettere un contratto `wiki.plan/1` con: file toccati dall'ultima entry · pagine che li citano (via `sources:`) · pagine non aggiornate da N giorni. Più la **coda dei passivi**: pagine contenenti comandi, numeri di versione, URL o riferimenti a file, ordinate per età dell'ultimo `updated:`. Nessun giudizio, solo pattern matching e aritmetica sulle date. *Prova sul campo dalla fonte: una nota di **sette giorni** documentava `openwiki --init`, comando che non esisteva più* | Il codice dice **dove guardare**, l'LLM **se è ancora vero**: restringe lo spazio di ricerca del lint semantico invece di sostituirlo | **Could (P2)** | 📋 da fare — **converge con E10-FEAT-049 e E13-FEAT-014: progettare insieme** |
| FEAT-004 | **Riproducibilità cross-OS verificata + benchmark di scalabilità** — «zero-LLM, offline» nell'`--help` *implica* il determinismo ma non lo **promette** né lo **verifica**. Due cose: (a) un test CI che esegua la pipeline sullo stesso corpus su due OS e verifichi che gli output **coincidano** — una garanzia che nessun sistema LLM-based può offrire; (b) un benchmark di `lint`/`collect` al crescere delle pagine, con verifica del **sospetto O(n²)** sul rilevamento orfani (il concorrente ha dovuto passare a scaling quasi-lineare, col lint al 56% del tempo totale). La CI ha già una matrice windows+ubuntu (E10-FEAT-003): manca il confronto degli output | Rende **misurato** il differenziatore invece che dichiarato; e il profilo di costo si scopre su un wiki grande, non sui nostri | **Could (P2)** | 📋 da fare — i numeri del concorrente sono autodichiarati: rimisurare |

> **Nota sulla priorità.** Nessuna di queste è urgente: il wiki funziona e il lint è a zero. L'ordine di
> valore percepito dalla fonte è FEAT-001 → FEAT-002 → FEAT-003 → FEAT-004, e FEAT-001 è l'unica che
> **produce un dato invece di consumare tempo di implementazione**: è il punto d'ingresso naturale.
