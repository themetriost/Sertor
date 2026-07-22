# Requisiti — Soluzione definitiva del `distill`: «daily distill floor» (≥1 distill/giorno)

<!-- Deriva da: FEAT-039 dell'epica E10 `debito-tecnico`. Direttiva utente 2026-07-21: non basta
     tracciare/dichiarare (FEAT-026), serve una soluzione DEFINITIVA con un pavimento di almeno un
     distill al giorno. Gemella lato-enforcement di FEAT-026 (che fornì il tool `ritual-check` +
     la dichiarazione forzata). Origine doppia: recupero del debito distill di 5 settimane sul
     dogfood + needfinding indipendente del nodo Acta (stesso giorno, stessi 3 punti). -->

## 1. Contesto e problema (perché)

Il passo `distill` del rituale wiki è *giudizio* + *condizionale* («calibra al valore») + *auto-eseguito
dal flusso principale*: la **stessa firma** dei passi che si saltano in silenzio. A differenza di `record`
(delegato al `wiki-curator` **e** sollecitato dall'hook `wiki-pending-check` su `Stop`/`SessionEnd`),
`distill` **non ha alcuna rete** → dipende solo dall'agente.

**Danno misurato (dogfood).** Dal **2026-06-15 al 2026-07-21** (~5 settimane) **nessuna** voce di log
taggata `distill`, pur avendo consegnato decine di step; il distill-*lavoro* è proseguito sporadico (5
pagine-entità) ma la **dichiarazione** del verdetto è sparita — emerso **solo** su domanda diretta
dell'utente. La **dichiarazione forzata** di FEAT-026 (merge `e906e34`/PR #176, 2026-07-12) è un contratto
**comportamentale** (un hook non può *giudicare*), quindi non enforced: il «distill: non necessario» è la
casella che si spunta a costo zero, sessione dopo sessione. La guardia c'era, ma difendeva dal buco
sbagliato — l'**omissione**, non la **reiterazione del «no»**.

**Convergenza indipendente — needfinding del nodo Acta** (Acta, canale *Feedback Sertor*, 2026-07-21,
stesso giorno, con prova sul campo): dopo ~10 sessioni il loro strato distillato era `concepts/`: 2 ·
`tech/`: 1 · `explainers/`: 1, mentre `log/`/`sources/` erano pieni. Sei capacità costruite e referenziate
da più punti (publish/discover, subscribe, l'occasione, provenienza+canale+tag, l'assenza dichiarata, il
gate memoria/azione) **senza pagina propria**. Tre raffinamenti proposti (decide Sertor, non Acta):
- **(a) discovery cross-sessione, non git-diff** — `ritual-check` scopre via diff del singolo step, ma il
  distill matura per **accumulo** (un'entità diventa referenziata da ≥k punti *settimane* dopo) → invisibile
  al diff. Il candidato più importante è **strutturalmente invisibile** allo strumento di discovery.
- **(b) il «no» deve costare** — «distill: non necessario» deve **nominare i candidati considerati e perché**
  non durevoli (come l'assenza dichiarata di Acta dice *cosa e dove* ha cercato).
- **(c) debito visibile** — una metrica leggera «N entità candidate senza pagina» a fine sessione: un numero
  che sale si nota.

Ancoraggio: `requirements/debito-tecnico/epic.md` (FEAT-039); il tool reale `sertor-wiki-tools`
(`src/sertor_core/wiki_tools/`, host-agnostico via `wiki.config.toml`, zero-LLM) e il sottocomando
`ritual-check` (`ritual_check.py`, FEAT-026, scope **git-diff**); l'hook host-facing `wiki-pending-check.py`
(la rete che tiene onesto `record`, `Stop`/`SessionEnd`, si auto-silenzia quando il wiki è aggiornato).

## 2. Obiettivi e criteri di successo

- **OB-1 — Pavimento giornaliero reale:** ogni **giornata attiva** chiude con ≥1 `distill` *dichiarato*
  (una passata reale **o** un «no» *costato* che nomina i candidati). *Criterio:* nessuna giornata di lavoro
  significativo termina senza una voce `distill` di quel giorno o una dichiarazione di non-necessità motivata.
- **OB-2 — Scoperta cross-sessione (non git-diff, non memoria):** il debito di distillazione è prodotto da
  uno **strumento deterministico** che scandisce **tutto il corpus** (non il diff dello step), così le entità
  rese durevoli *per accumulo* emergono indipendentemente da quando sono state scritte. *Criterio:* dato un
  corpus con entità referenziate da ≥k punti senza pagina, il tool le **elenca** e produce un **debito N**.
- **OB-3 — Il «no» costa:** un verdetto «distill: non necessario» deve **nominare i candidati considerati**
  e perché non durevoli; non è più a costo zero. *Criterio:* la dichiarazione di non-necessità cita i
  candidati emersi dal tool.
- **OB-4 — Il pavimento è persistente (rete come `record`):** l'assenza di un distill giornaliero è
  sollecitata ripetutamente (SessionStart + Stop/SessionEnd) finché la giornata non ha una voce `distill` o
  un «no» dichiarato — non un singolo nudge liquidabile. *Criterio:* con N>0 e nessun distill del giorno,
  l'hook continua a segnalare; si auto-silenzia appena la condizione è soddisfatta.
- **OB-5 — Confine D↔N onorato:** il **tool trova** (deterministico, zero-LLM), l'**agente giudica** (crea
  la pagina o dichiara un «no» motivato); l'**hook annuncia ed esige**, ma **non può obbligare** il giudizio
  (limite onesto). *Criterio:* il tool non invoca alcun LLM; l'hook non scrive pagine né giudica.
- **OB-6 — Host-agnostico & distribuibile:** il pavimento vale su qualunque ospite col wiki (config da
  `wiki.config.toml`) e viaggia nell'installer (tool + hook + blocco/playbook), non è dogfood-only.

## 3. Stakeholder e attori

- **L'agente frontier dell'ospite** (Claude/Copilot) — consumatore del tool e destinatario del pavimento;
  oggi salta `distill` in silenzio o dichiara «no» a costo zero.
- **L'utente/owner dell'ospite** — vittima del wiki che «cresce in cronologia e resta povero nello strato
  che dà valore» (i concetti navigabili); ha dato la direttiva del pavimento (Sertor) e l'ha segnalato (Acta).
- **L'hook `wiki-pending-check`** — la rete esistente per `record`, da estendere/affiancare per `distill`.
- **Il team Sertor (dogfood)** — primo cliente; il debito di 5 settimane è la prova d'origine.

## 4. Ambito

### In ambito (le 4 parti coese)
- **Parte 1 — `distill-audit`** (nuovo sotto-comando deterministico di `sertor-wiki-tools`, zero-LLM,
  read-only): scandisce **tutto** il wiki (+ requirements se in config) e trova le **entità referenziate da
  ≥k punti senza pagina propria**, per **due segnali deterministici**: (i) **wikilink penzolanti** (`[[x]]`
  senza `x.md`) contati per frequenza; (ii) **frequenza-prosa** di termini/frasi candidati (regola fissa,
  stopword escluse) menzionati ≥k volte senza pagina. Output: lista candidati (ordinata per frequenza) +
  **debito N**; JSON (`wiki.distill_audit/1`) + summary umano.
- **Parte 2 — pavimento giornaliero (hook), persistente:** un check **once-per-day** su `SessionStart`
  annuncia lo stato del pavimento (debito N + top candidati) se la giornata non ha ancora una voce `distill`
  **e** N>0; **Stop/SessionEnd** continuano a sollecitare finché la giornata non ha una voce `distill` o un
  «no» dichiarato — si auto-silenzia appena soddisfatto. Non-bloccante (nudge), come `wiki-pending-check`.
- **Parte 3 — il «no» costa:** il contratto host-facing (blocco rituale + playbook) richiede che «distill:
  non necessario» **nomini i candidati considerati** (dal tool) e perché non durevoli.
- **Parte 4 — regola standing:** «≥1 distill per giornata attiva» nel rituale (blocco + playbook), con il
  debito N come metrica leggera di fine sessione.
- **Distribuzione via installer** di tutte le parti (tool + hook + `claude-md-block`/playbook), parità
  Claude/Copilot, guardia sync.

### Fuori ambito
- **L'atto di distillare** (creare la pagina) e il **giudizio** su quali candidati siano durevoli — restano
  nel flusso principale (D↔N).
- **Enforcement forte/bloccante** del pavimento — l'hook non può *giudicare* né *obbligare* (un «no» falso
  resta possibile); l'obiettivo è rendere lo skip **caro e visibile**, non impossibile.
- **Qualunque LLM nel tool/core** (Principio XI/D↔N).
- **La riscrittura di `ritual-check`** (FEAT-026, git-diff per lo *step*): `distill-audit` è
  **complementare** (cross-sessione per il *debito*), non lo sostituisce.
- **Segnale-prosa via NLP/embedding** — la frequenza-prosa resta una **regola deterministica** (conteggio +
  stopword), non un modello.

## 5. Requisiti funzionali (EARS)

**Parte 1 — `distill-audit` (tool cross-sessione)**

- **REQ-001 (Ubiquitous):** *The wiki tooling shall provide a deterministic, offline operation (no LLM) that
  audits the **whole corpus** (not a step diff) and reports **distill candidates** — entities referenced from
  ≥k points that have no dedicated page.*
- **REQ-002 (Ubiquitous):** *Candidate detection shall use only **deterministic structural signals**: (i)
  **dangling wikilinks** (`[[x]]` with no `x.md`) counted by frequency, and (ii) **prose-frequency** of
  candidate terms/phrases mentioned ≥k times with no page, via a fixed rule (stop-words excluded) — no
  semantic model, no LLM.*
- **REQ-003 (Ubiquitous):** *The operation shall compute and report a lightweight **debt count N** (number of
  candidate entities without a page) and a candidate list ordered by frequency.*
- **REQ-004 (Ubiquitous):** *The operation shall emit a machine-readable JSON contract (`--json`) and a terse
  human summary, consistent with the other `sertor-wiki-tools` subcommands.*
- **REQ-005 (Ubiquitous):** *The operation shall be host-agnostic: it shall read its scope and taxonomy from
  `wiki.config.toml` and make no assumptions about a specific project's structure (Principio X).*
- **REQ-006 (Ubiquitous):** *The prose-frequency signal shall remain a **fixed deterministic rule** (token/
  phrase frequency with a stop-word list and a threshold k), so the tool **finds** while the agent **judges**;
  it shall not classify durability itself (D↔N).*

**Parte 2 — pavimento giornaliero (hook), persistente**

- **REQ-007 (State-driven):** *While a working day has produced significant work and has **no** `distill` log
  entry for that day and the debt N is > 0, the daily-floor hook shall remind (non-blocking) that the floor is
  unmet, stating the debt N and the top candidates.*
- **REQ-008 (Event-driven):** *When the assistant session starts (`SessionStart`), the hook shall evaluate the
  daily floor **at most once per day** and surface its state.*
- **REQ-009 (Event-driven):** *When a turn/session ends (`Stop`/`SessionEnd`), the hook shall re-evaluate and
  keep reminding until the day has a `distill` entry or a declared "no", mirroring `wiki-pending-check`.*
- **REQ-010 (Unwanted):** *If the day already has a `distill` log entry (or a declared non-necessity), then the
  hook shall self-silence and not remind.*
- **REQ-011 (Ubiquitous):** *The hook shall be non-blocking (exit 0 always) and shall not itself write pages or
  make the distill judgment (D↔N); it announces and demands, it does not force.*

**Parte 3 — il «no» costa (contratto host-facing)**

- **REQ-012 (Ubiquitous):** *The distributed wiki-ritual contract (ritual block + playbook) shall require that a
  «distill: not needed» verdict **name the candidates considered** (from the tool) and why they are not durable
  — a reflexive zero-cost "no" shall not satisfy the ritual.*

**Parte 4 — regola standing & distribuzione**

- **REQ-013 (Ubiquitous):** *The ritual (block + playbook) shall state the standing rule «≥1 distill per active
  day», with the debt N surfaced as a lightweight end-of-session metric.*
- **REQ-014 (Ubiquitous):** *All parts (tool, hook, ritual block/playbook) shall be distributable to hosts
  through the installer with Claude/Copilot parity, so a host with a wiki receives the same daily floor (not
  dogfood-only), and the bundle stays in sync (sync guard).*

**Confine D↔N**

- **REQ-015 (Ubiquitous):** *The Part-1 tool shall invoke no LLM and shall not decide durability; the Part-2
  hook shall not judge nor block. The judgment (distill or declared "no") stays in the main flow.*

## 6. Requisiti non funzionali

- **NFR-1 (D↔N / zero-LLM):** tool deterministico e offline; hook non giudicante; nessun LLM nel core
  (Principio XI).
- **NFR-2 (Host-agnostico):** nessuna assunzione sulla struttura dell'ospite; config da `wiki.config.toml`
  (Principio X). Il segnale-prosa non deve assumere una lingua/tassonomia specifica oltre alla config.
- **NFR-3 (Determinismo/idempotenza):** stesso corpus in input → stesso debito N e stessi candidati
  (Principio VI); sola lettura, nessun effetto collaterale sulle pagine.
- **NFR-4 (Coerenza CLI):** stesso stile di output (JSON + summary) e ergonomia degli altri sottocomandi;
  contratto versionato (`wiki.distill_audit/1`).
- **NFR-5 (Performance):** l'audit dell'intero corpus a `SessionStart`/`SessionEnd` deve restare veloce (il
  once-per-day cache evita di riscandire ad ogni turno).
- **NFR-6 (Distribuibilità):** parte del pacchetto `sertor-core` (tool) + hook e blocco host-facing cablati
  nell'installer con parità Claude/Copilot; guardia sync sul bundle.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo D↔N (non negoziabile):** il tool non giudica la durevolezza; l'hook non obbliga il giudizio.
- **Vincolo — limite onesto del pavimento:** un hook deterministico vede solo *se esiste una voce `distill`
  del giorno*, non se il distill è *genuino* → un «no» falso resta possibile. L'efficacia sta nel rendere lo
  skip **caro e visibile** (persistenza + debito + no-costato), non nell'impedirlo.
- **Dipendenza — `sertor-wiki-tools`/`wiki.config.toml`:** l'operazione estende il tool esistente, riusando
  lo scan dei backlink e la tassonomia; complementare a `ritual-check` (git-diff, per lo step).
- **Dipendenza — hook `wiki-pending-check` + installer:** la Parte 2 estende/affianca la rete `record`
  esistente; l'asset host-facing va cablato in `sertor install wiki`/`rag` e sincronizzato nel bundle
  (`sertor_installer.sync` + `test_assets_sync`), parità Claude/Copilot.
- **Assunzione — la voce `distill` del giorno è rilevabile** dal log del giorno (`wiki/log/<data>.md`,
  operazione `distill`), come già fa l'hook per il freshness del wiki.
- **Gemella di FEAT-026:** stesso confine D↔N (tool trova, agente giudica), ma lato-**enforcement**
  (pavimento persistente + audit cross-sessione) invece che lato-**scoperta-di-step** (git-diff).

## 8. Rischi

- **R-1 — Segnale-prosa rumoroso (falsi positivi):** la frequenza-prosa senza NLP può proporre non-entità.
  Mitigazione: stop-word list + soglia k tarabile + il verdetto resta all'agente (un falso positivo costa un
  «no» motivato, non una pagina spuria); i wikilink penzolanti restano il segnale ad alta precisione.
- **R-2 — Il pavimento diventa cerimonia (il «no» riflesso):** l'agente scrive «distill: non serve» senza
  guardare i candidati. Mitigazione: REQ-012 pretende che il «no» *nomini* i candidati (il tool li mette
  davanti); il debito N visibile alza il costo dell'ignorarli.
- **R-3 — Fatica da nudge (alert fatigue):** un pavimento persistente che grida ogni giorno si svaluta.
  Mitigazione: once-per-day + auto-silenzio appena soddisfatto + debito N=0 → nessun nudge (giornate senza
  candidati non innescano).
- **R-4 — Deriva D↔N:** tentazione di far «giudicare» al tool la durevolezza o all'hook il blocco.
  Mitigazione: REQ-006/REQ-011/REQ-015 confinano tool e hook; il giudizio è dichiarato fuori ambito.
- **R-5 — Drift dogfood↔bundle:** l'asset host-facing tocca hook + `claude-md-block`. Mitigazione: guardia
  sync (NFR-6) + parità Claude/Copilot.
- **R-6 — Costo del re-scan a ogni turno:** l'audit dell'intero corpus è più pesante del git-diff.
  Mitigazione: cache once-per-day (NFR-5); lo Stop/SessionEnd riusa lo stato del giorno.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-003, REQ-004, REQ-005 (audit cross-sessione deterministico, debito N,
  host-agnostico, contratto CLI); REQ-007, REQ-008, REQ-009, REQ-010, REQ-011 (pavimento persistente,
  once-per-day, auto-silenzio, non-bloccante); REQ-012 (il «no» costa); REQ-015 (confine D↔N).
- **Should:** REQ-006 (segnale-prosa come regola fissa — parte del valore ma il MVP può partire dai soli
  wikilink penzolanti se serve tagliare rischio), REQ-013 (regola standing + metrica), REQ-014 (distribuzione
  via installer — necessaria perché conti come «done» host-facing).
- **Could:** soglia k configurabile per segnale; flag per includere/escludere `requirements/` dallo scope;
  esclusione di uno «snooze» esplicito del pavimento; conteggio storico del debito (trend).
- **Won't (qui):** enforcement bloccante; segnale-prosa via NLP/embedding; riscrittura di `ritual-check`;
  l'atto di distillare automatico.

## 10. Domande aperte

- **DA-1 — Cosa conta come «entità candidata» in prosa, deterministicamente.** [DA CHIARIRE in clarify: solo
  frasi capitalizzate / multi-parola? termini in `code span`? nomi di file/simboli? Serve una regola fissa che
  massimizzi precisione senza NLP. Il wikilink penzolante è già ad alta precisione; la prosa è l'estensione.]
- **DA-2 — Nuovo sottocomando `distill-audit` o estensione di `ritual-check`/`lint`.** [DA CHIARIRE: un nuovo
  verbo (cross-sessione) vs un flag `--corpus`/`--cross-session` su `ritual-check`. Impatta superficie CLI e
  distribuzione. Raccomandazione iniziale: nuovo verbo, perché lo *scope* è diverso (corpus vs step).]
- **DA-3 — Come l'hook rileva «giornata attiva» e «voce distill del giorno».** [DA CHIARIRE: «giornata attiva»
  = ci sono modifiche a file indicizzati più recenti dell'ultima voce di log (come `wiki-pending-check`)? La
  «voce distill del giorno» = grep dell'operazione `distill` in `wiki/log/<data>.md`? Il «no» dichiarato dove
  vive (log? un marker)?]
- **DA-4 — Estendere `wiki-pending-check` o un nuovo hook `distill-floor`.** [DA CHIARIRE: aggiungere la logica
  del pavimento a `wiki-pending-check.py` (già su Stop/SessionEnd) + un check SessionStart, oppure un asset
  hook separato. Impatta il wiring `settings.json`/Copilot e il numero di asset host-facing.]
- **DA-5 — Once-per-day: dove si persiste lo stato.** [DA CHIARIRE: un file di stato `.sertor/.distill-floor.json`
  (come `.rag-health.json`) con la data dell'ultima valutazione + debito N? Confine con l'osservabilità.]
