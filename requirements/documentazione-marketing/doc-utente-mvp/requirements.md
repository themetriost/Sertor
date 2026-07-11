# Requisiti — Documentazione utente MVP (getting-started unico + README di valore)

<!-- Deriva da: FEAT-001 (getting-started unico e consolidato) + FEAT-002 (README di prodotto
     orientato al valore) dell'epica E13 `documentazione-marketing`. Corrisponde all'item di audit
     A-18 (SWOT 2026-07-02, EVO/P2). I due Must sono la coppia MVP di Fase 1: si consegnano
     insieme in un solo branch/PR. La FEAT-003 «pagina cos'è e perché» (Should) è FUORI scope. -->

## 1. Contesto e problema (perché)

La documentazione **utente** di Sertor oggi porta al valore, ma **senza un percorso unico** e **senza
comunicare il differenziatore**:

- **Nessun percorso unico «dal nulla al primo valore».** I quickstart sono **per-assistente**
  (`docs/install-claude.md`, `docs/install-copilot.md`) e il «come si interroga» vive separato in
  `docs/retrieval.md`. Un utente nuovo deve **scegliere l'assistente in cima** e poi ricomporre a mano
  install → index → prima query da file diversi. Manca un singolo viaggio lineare host-agnostico.
- **Il README non apre col valore.** `README.md` (radice) è **orientato alle feature** (visione,
  mission, profili, capacità, status): informativo ma **non guida col differenziatore** — la **fusione
  code+doc** in un unico corpus (*il codice dice cosa fa, la documentazione dice perché*) — né lo
  mostra con un **esempio concreto**. Chi non conosce gli internals non capisce «perché Sertor» a colpo
  d'occhio.
- **Il reference esiste ma non è un onboarding.** `docs/install.md` (824 righe) è il riferimento
  esaustivo (ogni flag, ogni manopola, refresh/uninstall): prezioso ma **non è** il percorso di primo
  valore.

Ancoraggio alla realtà (file reali consultati): `README.md`, `docs/install-claude.md`,
`docs/install-copilot.md`, `docs/retrieval.md`, `docs/install.md`, `packages/sertor/docs/install.md`
(tabella capability), `requirements/documentazione-marketing/epic.md` (E13, CS-1..CS-7).

## 2. Obiettivi e criteri di successo

Portare la percezione da «funziona se sai dove guardare» a «**capisco subito cos'è e perché, e arrivo
al primo valore seguendo un solo percorso**». Due artefatti **statici, esterni, host-agnostici**,
**derivati dai vehicle reali**.

- **OB-1 — Un solo ingresso al primo valore (CS-1):** un `docs/getting-started.md` unico porta da un
  repo non configurato al **primo retrieval funzionante**, senza leggere `specs/` né gli internals e
  **senza scegliere l'assistente in cima**.
- **OB-2 — Il «perché» in pochi minuti, senza gergo (CS-2):** il README, da solo, fa capire **cos'è
  Sertor e perché conviene** a un non-addetto.
- **OB-3 — Differenziatore con esempio concreto (CS-3):** la **fusione code+doc** è mostrata con
  **almeno un esempio concreto** (una query che restituisce **codice + documento insieme**), non solo
  a parole.
- **OB-4 — Derivata e non in deriva (CS-4):** ogni comando/claim è **copiato dai vehicle/asset reali** e
  **supera il lint** del corpus (link non rotti, nessuna divergenza dai comandi veri).
- **OB-5 — Separazione interna/esterna netta (CS-5):** nessun artefatto **interno** (`wiki/`, `specs/`)
  è presentato come doc utente; la doc esterna è **autosufficiente**.

## 3. Stakeholder e attori

- **Utente nuovo / chi valuta Sertor** — destinatario primario del getting-started (percorso unico).
- **Stakeholder / decisore non-tecnico** — destinatario del «perché» a colpo d'occhio nel README.
- **Owner/maintainer (tu)** — vuole doc utente che **non vada in deriva** e una storia di valore
  raccontabile, pronta per il go-public.
- **L'agente frontier dell'ospite (Claude/Copilot)** — consumatore *indiretto*: la doc lo orienta, ma
  la guida *attiva* resta E12 (in-product), non qui.

## 4. Ambito

### In ambito
- **Nuovo `docs/getting-started.md`** — percorso unico host-agnostico «nulla → primo valore»
  (prerequisiti → install RAG → index → prima query con esempio code+doc), che **assorbe e ordina**
  `docs/install-claude.md`/`docs/install-copilot.md` + `docs/retrieval.md` **delegando** ad essi il
  dettaglio dove diverge.
- **Riscrittura di `README.md`** in chiave **valore-first**: apre col differenziatore fusione code+doc
  + esempio concreto, poi il resto (capacità/status **fattuali preservati**, riordinati sotto la
  narrazione di valore), e punta a `docs/getting-started.md` come **ingresso unico**.
- **Aggiornamento dei puntatori** nei doc esistenti (`install-claude.md`, `install-copilot.md`,
  `retrieval.md`, `README.md`) affinché convergano sul getting-started come punto d'ingresso, senza
  duplicare contenuto.

### Fuori ambito
- **FEAT-003 «pagina cos'è e perché» per non-tecnici** (Should) — non è un Must, non è A-18.
- **Docs-site / tooling di sito** (DA-DM-b) — si parte da `docs/` consolidato; un docs-site si valuta
  solo se il volume lo giustifica (fuori da questo MVP).
- **Fase 2 (marketing pubblico)** — gated sul go-public (E2/FEAT-006 = Won't).
- **Le altre feature di Fase 1** — tutorial (FEAT-005), troubleshooting/FAQ (FEAT-006), changelog
  (FEAT-007), reference utente derivata (FEAT-008): crescono **sopra** questo nucleo, non qui.
- **Toccare il `wiki/`** (doc interna) o `specs/` — restano interni; al più se ne *deriva* prosa
  riscritta, mai esposizione diretta.
- **Modifiche a codice/vehicle** — questo è authoring di documentazione; nessun cambiamento a
  `sertor-core`, installer o CLI. (Se emergesse un comando errato/mancante è un finding, non scope.)

## 5. Requisiti funzionali (EARS)

**Getting-started (`docs/getting-started.md`)**

- **REQ-001 (Ubiquitous):** *The getting-started document shall present a single, host-agnostic path
  from an unconfigured repository to a first working retrieval, without requiring the reader to choose
  an assistant before starting.*
- **REQ-002 (Ubiquitous):** *The getting-started document shall cover, in order, four stages —
  prerequisites, RAG install, indexing, and a first query — as one linear journey.*
- **REQ-003 (Event-driven):** *When the reader's path diverges by assistant (Claude Code vs GitHub
  Copilot), the getting-started shall delegate the divergent detail to `install-claude.md` /
  `install-copilot.md` instead of duplicating it.*
- **REQ-004 (Ubiquitous):** *The getting-started document shall end with a concrete first-value
  example: a query that returns code and documentation together (the fused `search_combined` surface),
  demonstrating the code+doc differentiator.*
- **REQ-005 (Ubiquitous):** *The getting-started document shall reference `docs/install.md` as the full
  flag/knob reference and `docs/retrieval.md` for the hybrid-vs-graph concepts, absorbing and ordering
  them rather than restating them in full.*

**README (`README.md`)**

- **REQ-006 (Ubiquitous):** *The README shall open with the value proposition led by the code+doc
  fusion differentiator (the code says what it does, the documentation says why), before the feature
  and status lists.*
- **REQ-007 (Ubiquitous):** *The README shall make the "why" understandable by a non-expert in a few
  minutes, without jargon.*
- **REQ-008 (Ubiquitous):** *The README shall include at least one concrete example of the
  differentiator (a query returning code and documentation together).*
- **REQ-009 (Event-driven):** *When a reader wants to start, the README shall point to
  `docs/getting-started.md` as the single entry point.*
- **REQ-010 (Ubiquitous):** *The README shall preserve the accurate status/capability facts it already
  carries (no factual regression), re-ordered under the value narrative.*

**Trasversali (entrambi gli artefatti)**

- **REQ-011 (Ubiquitous):** *Both artifacts shall be host-agnostic (valid for Claude Code and GitHub
  Copilot); assistant-specific content shall live only in the per-assistant detail docs.*
- **REQ-012 (Ubiquitous):** *Every command shown shall be a real, current vehicle invocation copied
  from the real assets/docs (e.g. `uvx --from … sertor install rag`, `uv run --project .sertor
  sertor-rag index .`, `… sertor-rag search …`), not invented.*
- **REQ-013 (Unwanted):** *If the documentation would present an internal artifact (`wiki/`, `specs/`)
  as user documentation, then it shall not; the user docs shall be self-sufficient without repo
  internals.*
- **REQ-014 (Unwanted):** *If a command or claim cannot be verified against a real vehicle/asset, then
  it shall not be included (anti-drift honesty, Principio XII).*
- **REQ-015 (Ubiquitous):** *Both artifacts shall pass the repository's documentation link/lint checks
  (no broken internal links, no dangling references).*

## 6. Requisiti non funzionali

- **NFR-1 (Portabilità / host-agnostico):** i due artefatti valgono su qualunque ospite e su entrambi
  gli assistenti; ciò che varia sta in esempi/dettaglio delegati, non in assunzioni hardcoded
  (Principio X).
- **NFR-2 (Derivazione e anti-drift):** contenuto derivato dai vehicle/asset reali e sottoposto a lint
  come il resto del corpus; nessuna divergenza dai comandi veri (Principio XII).
- **NFR-3 (D↔N — artefatti statici):** getting-started e README sono **statici**, prodotti dal flusso
  di authoring; **il core non chiama alcun LLM** per produrli o servirli.
- **NFR-4 (Accessibilità del «perché»):** il valore è comprensibile senza gergo tecnico né conoscenza
  degli internals (destinatario non-addetto).
- **NFR-5 (Autosufficienza / separazione):** la doc esterna non richiede accesso a questo repo né la
  lettura di artefatti interni per raggiungere il primo valore.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo D↔N (non negoziabile):** nessun LLM nel core; artefatti statici (NFR-3).
- **Dipendenza — vehicle/asset reali:** i comandi derivano da `sertor install`/`configure`/`sertor-rag`
  e dai template `.env` reali; le fonti sono i `docs/install*.md`, `docs/retrieval.md`, `docs/install.md`.
- **Dipendenza — lint/link check:** esiste un controllo link/lint applicabile alla doc utente (per
  OB-4/REQ-015). [DA CHIARIRE in plan: quale strumento copre `docs/` oltre al lint del wiki.]
- **Assunzione:** il differenziatore (fusione code+doc) è **già reale e misurabile** (epica
  `retrieval-qualita`); qui lo si **comunica**, non lo si dimostra da capo.
- **Assunzione:** la distribuzione resta **interim `git+url`** (repo privato, niente PyPI); gli esempi
  di install non assumono la pubblicità del repo (CS-6).
- **Separazione interna/esterna:** il `wiki/` resta **interno**; la doc utente è un corpus distinto,
  autosufficiente.

## 8. Rischi

- **R-1 — Duplicazione di contenuto** tra getting-started e i per-assistente install-*.md. Mitigazione:
  il getting-started **delega** il dettaglio divergente (REQ-003), non lo ricopia.
- **R-2 — Drift dai comandi reali** (doc scritta a mano che diverge dai vehicle). Mitigazione: comandi
  copiati dagli asset reali + lint (REQ-012/REQ-014/REQ-015, NFR-2).
- **R-3 — README che perde fatti** riscrivendo in chiave valore (regressione informativa). Mitigazione:
  preservare i fatti accurati riordinandoli (REQ-010).
- **R-4 — Scope creep** verso «pagina perché» / docs-site / tutorial. Mitigazione: ambito Fuori esplicito
  (§4); questi sono altre feature di Fase 1.
- **R-5 — Sovrapposizione con E12** (guida in-product): il getting-started **statico** e la guided-setup
  **agentica** condividono i contenuti ma non i veicoli → cross-ref, non duplicazione.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-004 (getting-started percorso unico + esempio code+doc); REQ-006,
  REQ-008, REQ-009 (README valore-first + esempio + ingresso unico); REQ-011, REQ-012, REQ-013, REQ-014
  (host-agnostico, comandi reali, separazione, anti-drift).
- **Should:** REQ-003 (delega del dettaglio per-assistente), REQ-005 (rimandi a install.md/retrieval.md),
  REQ-007 (no gergo), REQ-010 (preservazione fatti), REQ-015 (lint/link check verde).
- **Could:** rifinitura visiva del README (badge, sommario), un secondo esempio di query.
- **Won't (qui):** FEAT-003 «pagina perché», docs-site, tutorial/troubleshooting/changelog/reference,
  qualunque materiale di Fase 2.

## 10. Domande aperte

- **DA-1 — Assistente di default negli esempi del getting-started.** Il percorso è host-agnostico, ma i
  blocchi comando concreti mostrano *un* assistente. [DA CHIARIRE: mostrare **Claude come default** (è il
  default dell'installer, `--assistant` omesso) con un callout Copilot che rimanda a `install-copilot.md`,
  oppure blocchi neutri con entrambe le varianti affiancate? Default proposto: **Claude di default +
  callout Copilot**, coerente col default reale del prodotto e meno verboso.]
- **DA-2 — Esempio concreto code+doc (REQ-004/REQ-008).** [DA CHIARIRE: usare una query **illustrativa
  generica** (sul repo dell'utente, con forma d'output realistica) o una query **reale dal dogfood**?
  Default proposto: **illustrativa generica host-agnostica** (la doc è esterna, non deve dipendere dal
  corpus di Sertor), mostrando la forma dei due flussi `docs`/`code` di `search_combined`.]
- **DA-3 — Quanto trim del README attuale (REQ-010).** [DA CHIARIRE in plan/design: quali sezioni
  correnti (Vision/Mission/profili/capacità/status/development) restano, si accorciano o migrano nel
  getting-started. Default proposto: valore+esempio in testa, capacità/status **condensati** e fattuali,
  install ridotto a puntatore al getting-started, development invariato.]
- **DA-4 — Strumento di lint per `docs/` (REQ-015).** [DA CHIARIRE in plan: il lint link del corpus
  copre già `docs/`, o serve estendere la verifica anche a quei file.]
