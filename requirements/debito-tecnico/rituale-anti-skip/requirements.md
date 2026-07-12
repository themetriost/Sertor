# Requisiti — Rituale wiki resistente allo skip silenzioso (scoperta deterministica + dichiarazione forzata)

<!-- Deriva da: FEAT-026 dell'epica E10 `debito-tecnico`. MVP = parte 1 (scoperta deterministica nel
     tool) + parte 3 (dichiarazione forzata a fine step). Parti 2 (output wiki-curator) e 4
     (propagazione ai moduli derivati `ops/*.md`) sono FOLLOW-UP, fuori da questo MVP. -->

## 1. Contesto e problema (perché)

Il rituale wiki (`record → distill → lint → explainer`) vive **solo come prosa** nel blocco host-facing
`SERTOR:WIKI-RITUAL` di `CLAUDE.md`: i passi di **giudizio** (`distill`, `lint semantico B`) sono
discrezionali → si saltano **in silenzio**, mentre `record` (meccanico, delegabile al `wiki-curator`) si
fa. Non esiste alcun **segnale strutturale** che distingua «fatto» da «saltato».

**Convergenza indipendente di due feedback ospiti** (stesso giorno, 2026-07-01):
- **`hermes-nunzio-ha`** (`wiki/sources/usersfeedback/processed/wiki-ritual-distill-lint-discrezionale.md`):
  `distill` giudicato solo nel brief del sub-agente (mai dichiarato), `lint` **mai eseguito** per 2 step
  di fila. **Danno reale:** una contraddizione è rimasta nel blocco **EXEC** di `roadmap.md` (mostrato
  all'utente a ogni SessionStart) per un'intera sessione — versione/test stantii, una capacità dichiarata
  disponibile ma rimandata, un «prossimo passo» già completato.
- **`Noetix`** (`wiki-ritual-distill-ignorato-noetix.md`): `distill` **completamente saltato** benché il
  criterio fosse evidente (un pattern di design riapplicato nella stessa sessione, **notato** in prosa ma
  mai distillato). Angolo aggiuntivo: un modulo `ops/*.md` **derivato** sopra `wiki-author` con checklist
  proprio **non ha richiamato** il rituale più ampio → distill perso *per costruzione*.

La causa comune: la **scoperta** dei candidati (a distillazione, e a lint) dipende dalla **memoria/
discrezione** dell'agente, e nulla **forza la dichiarazione** dell'esito. È un fallimento **silenzioso e
cumulativo** (Principio XII violato): il costo si paga a retrieval-time, molto dopo.

Ancoraggio: `requirements/debito-tecnico/epic.md` (FEAT-026); il tool reale `sertor-wiki-tools`
(sottocomandi `scan`/`structure`/`validate`/`lint`/`collect`/`index`/`append-log`/`migrate`/
`upsert-index`/`move`/`reconcile`, host-agnostico via `wiki.config.toml`, zero-LLM). Gemella
**lato-giudizio** di FEAT-011 (che spostò i passi **meccanici** — re-index/smoke — in un hook
`SessionEnd`).

## 2. Obiettivi e criteri di successo

- **OB-1 — Scoperta deterministica (non dalla memoria):** i candidati a **distillazione** e i candidati a
  **drift** (per il lint) sono prodotti da uno **strumento deterministico**, non lasciati alla memoria
  dell'agente. *Criterio:* dato uno stato-wiki che soddisfa l'euristica, il tool **elenca** i candidati;
  non dipende dal fatto che l'agente «se ne ricordi».
- **OB-2 — Lo skip diventa VISIBILE:** la chiusura di ogni step significativo **dichiara** l'esito di
  `record`/`distill`/`lint`; un passo saltato è un'**assenza dichiarata** («non serve») o un task
  visibile, mai un'omissione silenziosa. *Criterio:* nessuna chiusura di step è «completa» senza la riga
  di dichiarazione con i tre verdetti.
- **OB-3 — Confine D↔N onorato:** il **tool trova** (deterministico), l'**agente giudica** (crea la
  pagina o no, corregge o no). *Criterio:* il tool **non** invoca alcun LLM e **non** decide; il giudizio
  resta nel flusso principale.
- **OB-4 — Host-agnostico & distribuibile:** il meccanismo vale su qualunque ospite (legge
  `wiki.config.toml`) e viaggia nell'**installer** (blocco rituale + playbook + tool bundlati), non è
  dogfood-only.

## 3. Stakeholder e attori

- **L'agente frontier dell'ospite** (Claude/Copilot) — consumatore del tool e destinatario del contratto
  di dichiarazione; oggi salta i passi di giudizio in silenzio.
- **L'utente/owner dell'ospite** — vittima del drift silenzioso (specie nell'EXEC mostrato ad ogni avvio);
  ha segnalato il gap.
- **Il `wiki-curator`** (sub-agente di record) — attore della parte 2 (FOLLOW-UP), non di questo MVP.
- **Il team Sertor (dogfood)** — mantiene il rituale e ne è il primo cliente.

## 4. Ambito

### In ambito (MVP)
- **Parte 1 — operazione deterministica** in `sertor-wiki-tools` che **elenca**: (a) candidati a
  **distillazione** (insiemi di pagine che probabilmente fanno emergere un'entità durevole non
  distillata, per euristica strutturale) e (b) candidati a **drift** (pagine che potrebbero essere
  scollegate dalla realtà, da far giudicare all'agente col lint semantico). Output JSON + summary umano.
- **Parte 3 — contratto di dichiarazione forzata** a fine step nel blocco host-facing `SERTOR:WIKI-RITUAL`
  (+ playbook): la chiusura emette `Rituale: record ✅ · distill: <verdetto> · lint: <verdetto>`, con
  verdetto esplicito anche quando è «non serve».
- **Distribuzione via installer** di entrambe le parti (tool bundlato + blocco/playbook nel
  `claude-md-block`).

### Fuori ambito
- **Parte 2** — il `wiki-curator` che restituisce *sempre* candidati/contraddizioni come output (FOLLOW-UP).
- **Parte 4** — propagazione esplicita del rituale ai moduli `ops/*.md` derivati (FOLLOW-UP).
- **Il lint semantico stesso** — resta **giudizio dell'agente**; il tool produce solo *candidati* a drift,
  non il verdetto semantico.
- **Enforcement via hook** della dichiarazione — è **giudizio** (l'agente produce i verdetti), non
  automatizzabile in un hook deterministico come i passi meccanici di FEAT-011; qui è un **contratto**.
- **Qualunque LLM nel tool/core** (Principio XI/D↔N).

## 5. Requisiti funzionali (EARS)

**Parte 1 — scoperta deterministica (tool)**

- **REQ-001 (Ubiquitous):** *The wiki tooling shall provide a deterministic, offline operation (no LLM)
  that reports **distill candidates** — groups of pages whose changes likely surface a durable entity not
  yet distilled — for the work under review.*
- **REQ-002 (Ubiquitous):** *The distill-candidate detection shall rely only on **structural signals**
  derived from the wiki (e.g. pages changed together, new cross-backlinks among them, absence of a new
  `concepts/`/`tech/` page), without any semantic judgment.*
- **REQ-003 (Ubiquitous):** *The operation shall also report **drift candidates** — pages that may have
  diverged from repo reality and are worth a semantic lint — as deterministic candidates for the agent to
  judge; it shall NOT perform the semantic lint itself.*
- **REQ-004 (Ubiquitous):** *The operation shall emit a machine-readable JSON contract (`--json`) and a
  terse human summary, consistent with the other `sertor-wiki-tools` subcommands.*
- **REQ-005 (Ubiquitous):** *The operation shall be host-agnostic: it shall read its scope and taxonomy
  from `wiki.config.toml` and make no assumptions about a specific project's structure (Principio X).*
- **REQ-006 (Unwanted):** *If the operation cannot determine the set of pages under review, then it shall
  report this explicitly (fail-loud) rather than silently returning an empty candidate set as if there
  were nothing to distill (Principio XII).*

**Parte 3 — dichiarazione forzata (contratto host-facing)**

- **REQ-007 (Ubiquitous):** *The distributed wiki-ritual contract (host-facing ritual block + playbook)
  shall require that the closure of every significant step emit an explicit ritual declaration stating the
  verdict of `record`, `distill`, and `lint`.*
- **REQ-008 (Unwanted):** *If the closure of a significant step omits the verdict of `distill` or `lint`
  (rather than declaring it, "not needed" included), then the step shall not count as closed.*
- **REQ-009 (Optional feature):** *Where the Part-1 tool operation is available, its output shall include a
  declaration **scaffold** pre-populated with the deterministic candidates, so the closure has a concrete
  artifact to respond to.*
- **REQ-010 (Ubiquitous):** *The forced-declaration contract and the Part-1 operation shall be
  distributable to hosts through the installer (bundled tool + `claude-md-block`/playbook), so a host
  receives the same anti-skip behavior (not dogfood-only).*

**Confine D↔N**

- **REQ-011 (Ubiquitous):** *The Part-1 operation shall invoke no LLM and shall not make the
  create-or-not / correct-or-not judgment; it shall only surface candidates — the agent judges.*

## 6. Requisiti non funzionali

- **NFR-1 (D↔N / zero-LLM):** il tool è deterministico e offline; nessun LLM nel core (Principio XI).
- **NFR-2 (Host-agnostico):** nessuna assunzione sulla struttura dell'ospite; config da `wiki.config.toml`
  (Principio X). Test: gira su un ospite diverso senza modifiche al corpo.
- **NFR-3 (Idempotenza/determinismo):** stesso stato-wiki in input → stesso insieme di candidati (Principio
  VI); nessun effetto collaterale sulle pagine (sola lettura).
- **NFR-4 (Coerenza del contratto CLI):** stesso stile di output (JSON + summary) e stessa ergonomia degli
  altri sottocomandi.
- **NFR-5 (Distribuibilità):** parte del pacchetto `sertor-core` (tool, installabile per costruzione) +
  asset host-facing cablati nell'installer con parità Claude/Copilot; il template/blocco compare nel
  `claude-md-block` e nel bundle (guardia sync).

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo D↔N (non negoziabile):** il tool non giudica; la creazione della pagina e la correzione del
  drift restano nel flusso principale.
- **Dipendenza — `sertor-wiki-tools`/`wiki.config.toml`:** l'operazione estende il tool esistente e ne
  riusa lo scan/graph dei backlink e la tassonomia.
- **Dipendenza — installer & bundle:** l'asset host-facing (blocco rituale/playbook) va cablato in `sertor
  install wiki`/`rag` e sincronizzato nel bundle (`sertor_installer.sync` + `test_assets_sync`).
- **Assunzione:** la dichiarazione forzata è un **contratto di comportamento** dell'agente (non
  hook-enforced): la sua efficacia sta nell'avere un **artefatto deterministico** (l'output del tool) a cui
  la chiusura deve rispondere.
- **Gemella di FEAT-011:** stesso pattern «spostare fuori dalla discrezione», ma lato-**giudizio**
  (scoperta+dichiarazione) invece che lato-**meccanico** (re-index/smoke via hook).

## 8. Rischi

- **R-1 — Euristica rumorosa (falsi positivi/negativi):** troppi candidati → l'agente li ignora; troppo
  pochi → non cattura il gap. Mitigazione: soglie tarabili + il verdetto resta all'agente (un falso
  positivo costa una dichiarazione «non serve», non una pagina spuria).
- **R-2 — La dichiarazione diventa cerimonia vuota:** l'agente scrive «distill: non serve» senza guardare i
  candidati. Mitigazione: lo **scaffold pre-popolato** (REQ-009) mette i candidati *davanti* al verdetto;
  il costo di un «non serve» consapevole è basso ma il gap diventa visibile.
- **R-3 — Deriva D↔N:** tentazione di far «giudicare» al tool (semantic lint) per chiudere il cerchio.
  Mitigazione: REQ-003/REQ-011 confinano il tool ai *candidati*; il giudizio è dichiarato fuori ambito.
- **R-4 — Drift dogfood↔bundle:** l'asset host-facing tocca il `claude-md-block` → rischio di divergenza
  bundle. Mitigazione: guardia sync (NFR-5).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-004, REQ-005 (tool: candidati distill deterministici, host-agnostico,
  contratto CLI); REQ-007, REQ-008 (dichiarazione forzata con verdetto esplicito); REQ-011 (confine D↔N).
- **Should:** REQ-003 (candidati drift per il lint), REQ-006 (fail-loud sull'insieme indeterminato),
  REQ-009 (scaffold pre-popolato), REQ-010 (distribuzione via installer — necessaria perché la feature
  conti come «done» host-facing, ma implementabile subito dopo il nucleo).
- **Could:** soglie/euristiche aggiuntive; un flag per restringere/allargare la finestra di candidati.
- **Won't (qui):** parte 2 (wiki-curator output), parte 4 (propagazione `ops/*.md`), enforcement via hook,
  il lint semantico automatico.

## 10. Domande aperte

- **DA-1 — Come il tool determina «le pagine dello step».** [DA CHIARIRE in clarify: `git diff` vs una base
  (branch/commit)? recency vs l'ultima voce di log (come fa l'hook `wiki-pending-check.py`)? argomenti
  espliciti (lista pagine / range)? una combinazione? Impatta host-agnosticità e affidabilità.]
- **DA-2 — Nuovo sottocomando o estensione di `scan`.** [DA CHIARIRE: un nuovo verbo (es. `ritual-check` /
  `distill-suggest`) oppure un'estensione di `scan`/`lint` esistenti? Impatta la superficie CLI e la
  distribuzione.]
- **DA-3 — Cosa è, deterministicamente, il «segnale drift».** [DA CHIARIRE: quali segnali *strutturali* il
  tool può produrre senza sconfinare nel giudizio semantico — es. pagine con `updated` più vecchio
  dell'ultima modifica git, pagine toccate da change di codice nella stessa area, claim numerici a
  confronto con git? Confine con il lint semantico (che resta agente).]
- **DA-4 — Lo scaffold di dichiarazione: dove.** [DA CHIARIRE: il tool **emette** lo scaffold della
  dichiarazione (parte 3 agganciata all'output di parte 1, es. dopo `append-log`), oppure la parte 3 è
  **puro contratto di prosa** nel blocco rituale e lo scaffold è opzionale (REQ-009)?]
