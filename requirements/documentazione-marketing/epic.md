# Epica — Documentazione esterna e marketing

> Livello: **epica (E13)**. Non aggiunge un nuovo motore di retrieval né una capacità in-product:
> rende **comprensibile, raccontabile e adottabile** ciò che già esiste. Costruisce lo **strato di
> comunicazione esterna** — documentazione utente consolidata + materiali di marketing — *sopra* i
> meccanismi (motori, installer, wiki) che restano nelle epiche d'origine: E13 li **racconta**, non li
> costruisce. Si decompone in `requirements/documentazione-marketing/<feature>/requirements.md` (EARS).
>
> **Due fasi, gated.** **Fase 1 (ora):** la **documentazione utente esterna** (README di valore,
> getting-started unico, tutorial, troubleshooting, reference utente). **Fase 2 (futura):** il
> **marketing pubblico** (landing/sito, posizionamento competitivo, demo, blog, materiali OSS) — è
> **gated sul go-public** e **presuppone un cambio di strategia di distribuzione** (apertura del repo /
> PyPI), oggi assente. Vedi §5 (dipendenza verso E2).
>
> **Gate missione & Costituzione (Principio X — host-agnosticità).** Come E12 (usabilità), questa epica
> è *periferica* al differenziatore (qualità del retrieval reso all'agente) ma **serve l'adozione e la
> portabilità** (Principio X): *documentare e comunicare bene aumenta l'adozione*. Vincolo non
> negoziabile (**Principio D↔N**): **nulla che il core debba fare**, **nessun LLM nel core** — la
> documentazione e i materiali sono artefatti **statici ed esterni**, derivati dalla realtà del prodotto.

## 1. Visione e problema (perché)

La documentazione **utente** di Sertor oggi è **frammentata** e **non comunica il valore**:

- **Sparsa e per-esperto:** la conoscenza utile vive sparpagliata in `docs/install.md`,
  `docs/install-claude.md`, `docs/install-copilot.md`, `docs/retrieval.md`, nel `README.md` di radice e
  — peggio — dentro `specs/` (che sono artefatti **interni** di design, non documentazione utente).
  Manca un **getting-started unico** che porti «dal nulla al primo valore» senza leggere gli internals.
- **Niente percorso «da curioso a convinto»:** non esiste materiale che **comunichi il valore** a un
  non-addetto o a uno stakeholder. Il **differenziatore** di Sertor — la **fusione code+doc** in un
  unico corpus reso all'agente (*il codice dice cosa fa, la documentazione dice perché*) — è chiaro
  nella mission ([[mission-vision]], `README.md`) ma **non è raccontato in modo accessibile** con un
  esempio concreto: chi non conosce gli internals non capisce «perché Sertor».
- **Distinzione interna/esterna non presidiata:** il `wiki/` è **documentazione INTERNA** (memoria
  cumulativa del progetto, per l'agente e per chi sviluppa Sertor) e **deve restare tale**; ciò che
  manca è la sua controparte **esterna** — documentazione e materiali pensati per chi **usa** Sertor su
  un ospite, senza mai aprire questo repo.

La **visione**: portare la percezione esterna da «funziona se sai dove guardare» a «capisco subito cos'è,
perché conviene, e arrivo al primo valore seguendo un solo percorso». Lo strumento è **documentazione e
materiali statici, derivati dalla realtà** (vehicle/asset reali), **host-agnostici** e — per la Fase 2 —
**pubblici solo dopo il go-public**.

> **Complementarità con E12 (usabilità).** E12 possiede l'esperienza **in-product** (un agente che
> *guida, verifica, spiega* a runtime: `doctor`, guided-setup, `explain`/help). E13 possiede la
> controparte **statica ed esterna**: la pagina che leggi *prima* di installare, il README che ti
> convince, la demo che ti mostra il valore. L'`explain` in-product (E12) e la pagina «cos'è e perché»
> (E13) **si rinforzano**, non si duplicano (vedi mapping §2).

> Il *come* (struttura del docs-site, stack del sito, formato dei materiali) è materia della **fase di
> design** a valle. Qui solo *cosa* e *perché*.

## 2. Ambito

Questa epica è **owner della documentazione ESTERNA e del marketing**. Possiede la **comunicazione** del
prodotto verso l'esterno; i **meccanismi** che racconta **restano nelle epiche d'origine** (nessuna
duplicazione — solo cross-reference e narrazione fedele).

### In ambito (Fase 1 — documentazione utente)
- **README di prodotto orientato al valore:** il pitch in radice, imperniato sul differenziatore
  (fusione code+doc), con l'esempio concreto.
- **Getting-started / quickstart unico e consolidato:** un solo percorso «dal nulla al primo retrieval»,
  che assorbe e ordina ciò che oggi è sparso in `docs/install*` e `docs/retrieval.md`.
- **Ristrutturazione di `docs/` utente + indice:** una gerarchia navigabile (eventuale **docs-site**),
  con un indice che dice *dove andare per cosa*.
- **Tutorial** «dal nulla al primo valore» (end-to-end, host-agnostico).
- **Reference utente:** comandi/manopole/scenari, derivata dai vehicle reali (non dagli internals).
- **Troubleshooting / FAQ** utente (complemento *statico* della diagnosi *agentica* di E12).
- **Changelog / release notes** (cosa è cambiato per chi usa Sertor).
- **Pagina «cos'è e perché»** per non-tecnici: il differenziatore code+doc spiegato con un'immagine
  quotidiana e un esempio concreto (controparte esterna degli `wiki/explainers/` interni).

### In ambito (Fase 2 — marketing pubblico, **gated sul go-public**)
- **Landing / sito pubblico** (Could).
- **Demo / screencast** del valore (Should).
- **Posizionamento & messaggistica** — il «perché Sertor» imperniato sulla fusione code+doc, **confronto
  vs alternative** (Should).
- **Blog / contenuti** (Could).
- **Materiali OSS** — README pubblico, `CONTRIBUTING`, `LICENSE` (già MIT) (Could).

### Mapping di confine (cosa E13 possiede vs cosa resta altrove)
- **vs E12 `usabilità` (in-product):** la **UX in-product** — `doctor`, guided-setup, `explain`/help,
  diagnosi agentica — **resta E12**. E13 possiede la **doc/marketing statica ed esterna** (README,
  getting-started, tutorial, pagina «perché», troubleshooting *statico*). L'`explain` in-product (E12) e
  la pagina «cos'è e perché» (E13) sono **complementari** (runtime vs statica), non duplicati.
- **vs `wiki/` (documentazione INTERNA):** il `wiki/` è e **resta** documentazione **interna** (memoria
  del progetto). E13 **non** lo tocca e **non** lo espone come doc utente; al più ne deriva la
  controparte esterna (es. una pagina «perché» pubblica ispirata agli explainer interni).
- **vs epiche dei meccanismi (E1 `sertor-core`/motori, E2 `sertor-cli`/installer, E3 `osservabilità`,
  …):** i **meccanismi** (motori di retrieval, packaging/installer, store/TUI) **restano** nelle epiche
  d'origine. E13 li **racconta** in modo fedele e accessibile, **non** li costruisce né li reimplementa.
- **vs E2 `sertor-cli` (go-public):** il **marketing pubblico** (Fase 2) **presuppone** un cambio di
  strategia di distribuzione — apertura del repo / **PyPI** — oggi **Won't** in E2
  ([`sertor-cli` FEAT-006 = «Won't (per ora)»](../sertor-cli/epic.md)). È una **dipendenza/gate**, non
  un dato di fatto (vedi §5, DA-DM-a).

### Fuori ambito
- **Il core che chiama un LLM** (Principio D↔N): la documentazione e i materiali sono artefatti statici,
  derivati; nessuna intelligenza nel core.
- **La UX in-product** (doctor / guided-setup / explain / help): è **E12**.
- **Il `wiki/`** come documentazione utente: resta **interno**.
- **I meccanismi** (motori, installer, osservabilità): E13 li **racconta**, non li costruisce — restano
  nelle epiche d'origine.
- **Pubblicare materiali di marketing prima del go-public:** vietato finché il gate E2 non è sciolto
  (Fase 2 è gated).

## 3. Criteri di successo
<!-- misurabili e tech-agnostici -->
- **CS-1 (un solo punto d'ingresso):** un utente nuovo trova **un getting-started unico** e arriva al
  **primo valore** (primo retrieval funzionante su un ospite) **senza** dover leggere `specs/` né gli
  internals, seguendo un solo percorso.
- **CS-2 (il «perché» in < N minuti):** uno stakeholder o un non-addetto, da **una sola pagina**, capisce
  **cos'è Sertor e perché conviene** in pochi minuti, **senza gergo**.
- **CS-3 (differenziatore con esempio concreto):** il differenziatore **fusione code+doc** è comunicato
  con **almeno un esempio concreto** (una query architetturale che restituisce *codice + documento*
  insieme), non solo a parole.
- **CS-4 (docs derivate e non in deriva):** la documentazione utente è **derivata dai vehicle/asset
  reali** (comandi, manopole, output) e **sottoposta a lint** come il resto del corpus; non diverge dalla
  realtà del prodotto.
- **CS-5 (separazione interna/esterna netta):** nessun artefatto **interno** (`wiki/`, `specs/`) è
  presentato come doc utente; la documentazione esterna è **autosufficiente** e non richiede accesso a
  questo repo.
- **CS-6 (host-agnostico & privato finché serve):** tutta la doc Fase 1 è **host-agnostica** (vale su
  Claude e Copilot, su un ospite qualunque) e **non assume** la pubblicità del repo; i materiali Fase 2
  **non vengono pubblicati** finché il gate go-public (E2) non è sciolto.
- **CS-7 (marketing ancorato al vero):** ogni claim di posizionamento/confronto (Fase 2) è **onesto e
  verificabile** (Principio XII): nessun «fatto» non vero, nessun confronto fuorviante.

## 4. Stakeholder e attori
- **Utente nuovo / chi valuta Sertor:** vuole un percorso unico «da curioso a primo valore» senza leggere
  gli internals — destinatario primario della Fase 1.
- **Stakeholder / decisore non-tecnico:** vuole capire il «perché» (valore, differenziatore) in pochi
  minuti — destinatario della pagina «cos'è e perché» e (Fase 2) dei materiali di marketing.
- **Owner/maintainer (tu):** vuole una documentazione utente che non vada in deriva e una storia di
  valore raccontabile, pronta per il go-public quando arriverà.
- **Pubblico OSS / esterno (futuro, Fase 2):** destinatario di landing/sito/blog/materiali OSS, **solo
  dopo** il go-public.
- **L'agente frontier dell'ospite (Claude/Copilot):** consumatore *indiretto* — la doc esterna lo aiuta a
  orientarsi, ma la guida *attiva* è E12 (in-product), non E13.

## 5. Vincoli, assunzioni e dipendenze
- **D↔N (non negoziabile):** nessun LLM nel core; la documentazione e i materiali sono artefatti
  **statici** prodotti dal flusso di authoring (mano/agente di sviluppo), **non** generati a runtime dal
  prodotto.
- **Derivazione dalla realtà:** la doc utente è **derivata dai vehicle/asset reali** (CLI/MCP, template
  `.env`, output dei comandi) e **soggetta a lint** come il resto del corpus — non scritta a mano una
  tantum e lasciata divergere (Principio XII, anti-drift).
- **Separazione interna/esterna:** il `wiki/` resta **interno**; la doc esterna è un **corpus distinto**,
  autosufficiente, senza dipendenze dal repo di Sertor.
- **Dipendenza/gate verso E2 (go-public):** la **Fase 2 (marketing pubblico)** è **gated** su un cambio
  di strategia di distribuzione (apertura del repo / **PyPI**). Oggi Sertor è un repo **PRIVATO**, niente
  PyPI ([`sertor-cli` FEAT-006 = Won't](../sertor-cli/epic.md), distribuzione interim `git+url`). Finché
  quel gate non è sciolto, i materiali Fase 2 si **progettano/abbozzano** ma **non si pubblicano**.
- **Complementarità con E12:** la doc *statica* (E13) e la guida *agentica* (E12) condividono i contenuti
  ma non i veicoli; vanno **cross-referenziate**, non duplicate.
- **Host-agnostico (Principio X):** la doc Fase 1 vale su qualunque ospite e su entrambi gli assistenti
  supportati (Claude, Copilot); ciò che varia sta in esempi/config, non in assunzioni hardcoded.
- **Calibra al valore:** molte voci sono artefatti di contenuto (pagine, tutorial) — non sovra-spec-are;
  un eventuale docs-site con tooling proprio segue il flusso SpecKit quando lo merita.
- **Assunzione:** il differenziatore (fusione code+doc) è già reale e misurabile (epica
  `retrieval-qualita`); E13 lo **comunica**, non deve dimostrarlo da capo.

## 6. Rischi
- **R-1 — Sovrapposizione con E12 / `wiki/`:** «owner della doc/marketing» rischia di duplicare la UX
  in-product (E12) o di confondersi con la doc interna (`wiki/`). Mitigazione: mapping di confine
  esplicito (§2) + cross-ref obbligatori + separazione netta interna/esterna (CS-5).
- **R-2 — Marketing pubblico prima del go-public:** pubblicare landing/blog/materiali OSS mentre il repo è
  privato e la distribuzione è `git+url`. Mitigazione: **Fase 2 gated su E2** (go-public/PyPI); fino ad
  allora si progetta, non si pubblica (CS-6).
- **R-3 — Drift della doc esterna vs realtà:** documentazione utente scritta a mano che diverge dai
  comandi/manopole reali. Mitigazione: **derivata dai vehicle/asset reali** e **sottoposta a lint** come
  il resto del corpus (CS-4, Principio XII).
- **R-4 — Claim di marketing disonesti:** confronti vs alternative fuorvianti o «fatti» non veri.
  Mitigazione: ancoraggio al vero e verificabilità (CS-7, Principio XII); il confronto cita ciò che è
  davvero il fronte competitivo (qualità del retrieval reso all'agente — vedi [[mission-vision]]).
- **R-5 — Scope creep verso «doc generica» o «sito bello»:** costruire materiali fini a sé stessi.
  Mitigazione: ancoraggio al gate missione (adozione/portabilità, Principio X), non «estetica».
- **R-6 — Deriva D↔N:** la tentazione di generare la doc «automaticamente» dal prodotto a runtime con un
  LLM nel core. Mitigazione: la doc è artefatto **statico** prodotto dal flusso di authoring; il core non
  chiama LLM.

## 7. Requisiti trasversali (EARS)
- **REQ-E1 (Ubiquitous):** *All documentation and marketing artifacts in this epic shall be static and
  external; the core shall never call an LLM to produce or serve them (Principio D↔N).*
- **REQ-E2 (Ubiquitous):** *The Phase-1 user documentation shall be host-agnostic and self-sufficient: a
  user shall be able to reach first value without reading the project internals (`specs/`, `wiki/`) or
  accessing the Sertor repository.*
- **REQ-E3 (Ubiquitous):** *The user documentation shall be derived from the real vehicles/assets (CLI/MCP,
  `.env` template, command output) and shall be subject to lint like the rest of the corpus, so it does not
  drift from the product reality (Principio XII).*
- **REQ-E4 (Ubiquitous):** *The value story shall communicate the differentiator (code+doc fusion) with at
  least one concrete example, not by assertion alone.*
- **REQ-E5 (Unwanted):** *If a public-facing marketing artifact (Phase 2) would be published before the
  go-public gate (E2: open repo / PyPI) is resolved, then it shall not be published; Phase-2 artifacts may
  be designed but not released until the gate is lifted.*
- **REQ-E6 (Optional):** *Where the documentation overlaps with the in-product experience (E12) or the
  internal wiki, it shall cross-reference rather than duplicate, keeping internal vs external clearly
  separated.*
- **REQ-E7 (Unwanted):** *If a marketing claim or competitive comparison cannot be verified as true, then
  it shall not be made (honest claims, Principio XII).*

## 8. Backlog di feature

> Due fasi. **Fase 1 (documentazione utente)** è attiva ora; **Fase 2 (marketing pubblico)** è **gated**
> sul go-public (E2). La colonna **Fase** marca l'appartenenza; la **Fase 1 (FEAT-001..008) è ✅ CONSEGNATA** (2026-07-11/12, vedi EXEC); la **Fase 2 (FEAT-009..013) resta `📋 gated`** sul go-public.

### Fase 1 — Documentazione utente esterna (ora)

| ID | Feature | Fase | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|------|--------------------|-------------------|-------|
| FEAT-001 | **Getting-started / quickstart unico e consolidato** — un solo percorso «dal nulla al primo retrieval» che assorbe e ordina `docs/install*` + `docs/retrieval.md`; host-agnostico (Claude/Copilot) | 1 | Un unico punto d'ingresso «da curioso a primo valore» senza leggere gli internals (CS-1) | **Must** | ✅ consegnata (merge `6e40ccc`/PR #172, item A-18 — [`doc-utente-mvp`](doc-utente-mvp/requirements.md); vedi EXEC) |
| FEAT-002 | **README di prodotto orientato al valore** — pitch in radice imperniato sul differenziatore (fusione code+doc) con l'esempio concreto | 1 | Il «perché» a colpo d'occhio; prima impressione che convince (CS-2/CS-3) | **Must** | ✅ consegnata (merge `6e40ccc`/PR #172, item A-18 — [`doc-utente-mvp`](doc-utente-mvp/requirements.md); vedi EXEC) |
| FEAT-003 | **Pagina «cos'è e perché» per non-tecnici** — differenziatore code+doc spiegato con immagine quotidiana ed esempio concreto (controparte esterna degli `wiki/explainers/`) | 1 | Lo stakeholder capisce il valore in < N minuti, senza gergo (CS-2/CS-3) | **Should** | ✅ consegnata (`docs/why-sertor.md`, batch Fase 1 doc utente 2026-07-12; authoring diretto — vedi EXEC) |
| FEAT-004 | **Ristrutturazione `docs/` utente + indice** — gerarchia navigabile (eventuale docs-site) con indice «dove andare per cosa» | 1 | Documentazione utente trovabile, non sparsa (CS-1/CS-5) | **Should** | ✅ consegnata (`docs/README.md` indice, batch Fase 1 2026-07-12 — vedi EXEC) |
| FEAT-005 | **Tutorial «dal nulla al primo valore»** — end-to-end, host-agnostico, dal repo non configurato al primo retrieval verificato | 1 | Onboarding guidato statico, complementare alla guided-setup agentica di E12 | **Should** | ✅ consegnata (`docs/tutorial.md`, batch Fase 1 2026-07-12 — vedi EXEC) |
| FEAT-006 | **Troubleshooting / FAQ utente** — complemento *statico* della diagnosi *agentica* (E12); errori comuni → causa → fix | 1 | Sblocco autonomo quando qualcosa non va, senza aprire il repo | **Could** | ✅ consegnata (`docs/troubleshooting.md`, batch Fase 1 2026-07-12 — vedi EXEC) |
| FEAT-007 | **Changelog / release notes** — cosa è cambiato per chi usa Sertor, per release/versione | 1 | Trasparenza sull'evoluzione; fiducia dell'utente | **Could** | ✅ consegnata (`CHANGELOG.md`, batch Fase 1 2026-07-12 — vedi EXEC) |
| FEAT-008 | **Reference utente** — comandi/manopole/scenari derivati dai vehicle reali (non dagli internals), sottoposti a lint anti-drift | 1 | Consultazione precisa e sempre allineata alla realtà (CS-4) | **Could** | ✅ consegnata (`docs/reference.md`, batch Fase 1 2026-07-12 — vedi EXEC) |

### Fase 2 — Marketing pubblico (**gated** sul go-public / E2)

| ID | Feature | Fase | Valore / obiettivo | Priorità (MoSCoW) | Stato |
|----|---------|------|--------------------|-------------------|-------|
| FEAT-009 | **Posizionamento & messaggistica + confronto vs alternative** — il «perché Sertor» imperniato sulla fusione code+doc, confronto onesto/verificabile con le alternative | 2 (gated E2) | La storia di valore competitiva, pronta per il go-public (CS-3/CS-7) | **Should** | 📋 da decomporre |
| FEAT-010 | **Demo / screencast** — mostra il valore (query architetturale → code+doc insieme) in azione | 2 (gated E2) | Il differenziatore *visto*, non solo letto (CS-3) | **Should** | 📋 da decomporre |
| FEAT-011 | **Landing / sito pubblico** — vetrina del prodotto per il pubblico esterno | 2 (gated E2) | Punto d'atterraggio pubblico per chi scopre Sertor | **Could** | 📋 da decomporre |
| FEAT-012 | **Blog / contenuti** — articoli su valore, casi d'uso, dietro-le-quinte | 2 (gated E2) | Acquisizione e fiducia nel tempo | **Could** | 📋 da decomporre |
| FEAT-013 | **Materiali OSS** — README pubblico, `CONTRIBUTING`, `LICENSE` (già MIT) e contorno per una repo aperta | 2 (gated E2) | Pronti per l'apertura del repo / community | **Could** | 📋 da decomporre |

> **Nota sull'MVP (Fase 1):** la prima release utile è **FEAT-001 + FEAT-002 + FEAT-003** — un
> **getting-started unico**, un **README orientato al valore** e una **pagina «perché»** per non-tecnici:
> bastano a portare un nuovo utente al primo valore e a far capire a uno stakeholder il differenziatore
> code+doc. Il resto della Fase 1 (docs-site, tutorial, troubleshooting, changelog, reference) cresce
> sopra questo nucleo.

> **Confine ribadito.** E13 possiede la **comunicazione esterna** (doc utente + marketing). La **UX
> in-product** resta [`usabilità` (E12)](../usabilita/epic.md); il **`wiki/`** resta documentazione
> **interna**; i **meccanismi** (motori, installer, osservabilità) restano nelle epiche d'origine — E13
> li **racconta**, non li costruisce. La **Fase 2** è **gated** sul go-public
> ([`sertor-cli` FEAT-006 PyPI = Won't](../sertor-cli/epic.md)): nessun materiale pubblico esce prima che
> quel gate sia sciolto.

## 9. Domande aperte
- **DA-DM-a — Trigger del go-public (gate Fase 2):** [DA CHIARIRE: quale evento scioglie il gate — apertura
  del repo? pubblicazione su PyPI (E2/FEAT-006, oggi Won't)? una decisione esplicita dell'owner? Default
  proposto: la Fase 2 si attiva solo su decisione esplicita dell'owner che dichiari il go-public, con E2
  come prerequisito tecnico.]
- **DA-DM-b — Sede della documentazione esterna:** [DA CHIARIRE: la doc utente vive come `docs/` arricchito
  in repo, come **docs-site** generato (es. static site), o entrambi? Default proposto: partire da `docs/`
  consolidato + indice; valutare un docs-site solo se il volume lo giustifica.]
- **DA-DM-c — Anti-drift della doc utente:** [DA CHIARIRE in decomposizione: quanto la reference utente
  (FEAT-008) è *derivata automaticamente* dai vehicle vs scritta e sottoposta a lint? Confine D↔N: nessuna
  generazione runtime dal core; eventuale derivazione è un passo di authoring/build, non del prodotto.]
- **DA-DM-d — Riuso degli `wiki/explainers/` per la pagina «perché»:** [DA CHIARIRE: la pagina pubblica
  «cos'è e perché» (FEAT-003) deriva dagli explainer interni o è autonoma? Default proposto: ispirata agli
  explainer interni ma **riscritta** come artefatto esterno autosufficiente (CS-5), mai esposizione diretta
  del `wiki/`.]
- **DA-DM-e — Onestà del confronto competitivo:** [DA CHIARIRE in FEAT-009: su quali assi si confronta
  Sertor (qualità del retrieval reso all'agente, fusione code+doc, portabilità/no-lock-in) e con quali
  alternative, mantenendo i claim verificabili (CS-7).]
