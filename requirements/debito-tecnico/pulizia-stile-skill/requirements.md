# Requisiti — Pulizia stile delle skill distribuite

<!-- Deriva da: FEAT-022 (epica debito-tecnico) — audit ISSUE-08 del 2026-06-26 -->

## 1. Contesto e problema (perché)

Gli asset skill che Sertor deposita sugli ospiti tramite `sertor install rag` e
`sertor-flow install` presentano tre problemi di stile/leggibilità accumulati durante
lo sviluppo rapido:

### 1.1 Inventario degli asset skill in scope (stato attuale su `master`, branch `079`)

| Asset (percorso canonico nell'installer) | Pacchetto | Righe | Problemi presenti |
|---|---|---|---|
| `assets/rag/skills/guided-setup/SKILL.md` | `sertor` | 190 | ALL-CAPS enfatico in 12+ occorrenze; sezione «Hard boundary» (ll. 25–50) e sezione «What NOT to do» (ll. 180–189) si sovrappongono su tre regole (no-import-core, consent gate, no-auto-provider) |
| `assets/rag/skills/eval-suite-author/SKILL.md` | `sertor` | 146 | ALL-CAPS enfatico (ASSISTED, DETERMINISTIC, DOES NOT, DATA, NAVIGATION, EMPTY, DISCOVER, SHOULD — 8+ occorrenze); sezione «Hard boundary» e «What NOT to do» con overlap parziale; callout «How to invoke» inline identico al riferimento canonico `sertor-cli-reference.md` (introdotto da FEAT-021) |
| `assets/rag/skills/eval-feedback/SKILL.md` | `sertor` | 77 | ALL-CAPS moderato; sezione «Hard boundary» + «What NOT to do» con overlap parziale; callout «How to invoke» inline identico a `sertor-cli-reference.md` |
| `assets/claude/skills/wiki-author/wiki-playbook.md` | `sertor` | **282** (ridotto da 295 da FEAT-021; verifica: `Read` del file al 2026-06-30) | Nessuna ToC malgrado 8 sezioni numerate (§0–§7); wikilink orfano `[[assistant-targeting]]` alla riga 52 |
| `assets/claude/skills/wiki-author/SKILL.md` | `sertor` | 41 | Nessun problema rilevante |
| `assets/claude/skills/requirements/SKILL.md` | `sertor-flow` | 164 | Un'occorrenza di "SEMPRE" in maiuscolo in testo italiano; altrimenti clean |

Le copie dogfood in `.claude/skills/wiki-author/wiki-playbook.md` e
`.claude/skills/requirements/SKILL.md` sono copie derivate degli asset canonici,
tenute in sync dalla guardia `tests/unit/test_assets_sync.py`.

### 1.2 Problema 1 — ALL-CAPS enfatico pervasivo

Parole intere in maiuscolo come `MANDATORY`, `ONLY`, `NOT on PATH`, `DO NOT`,
`ASSISTED`, `DETERMINISTIC`, `DATA`, `NAVIGATION`, `EMPTY`, `DISCOVER`, `DOES NOT`
compaiono come marcatori di enfasi in testo inglese prosa. Questo stile appartiene
a una fase di scrittura rapida; il rubric di stile del progetto preferisce enfasi via
**bold** o struttura imperativa accompagnata dalla motivazione (*why*). Gli acronimi
tecnici legittimi (RAG, CLI, MCP, API, JSON, YAML, URL, TOML, NL, POSIX) e i
contenuti in blocchi di codice non sono toccati da questa regola.

Ancoraggio: `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md:47`
(«`--assistant <host>` is MANDATORY»),
`packages/sertor/src/sertor_installer/assets/rag/skills/eval-suite-author/SKILL.md:18`
(«It is ASSISTED authoring»).

### 1.2 Problema 2 — Sezioni «What NOT to do» e «Hard boundary» ridondanti

`guided-setup/SKILL.md` ha sia una sezione «Hard boundary» (righe 25–50) sia una
sezione «What NOT to do» (righe 180–189). Le regole sovrapposte sono:

- «do not import the core» → espressa in «Hard boundary» riga 27–29 **e** in
  «What NOT to do» riga 185;
- «do not run without explicit confirmation» → espressa nel «Consent gate» (righe
  62–69) **e** in «What NOT to do» riga 184;
- «do not select a provider automatically» → espressa in «Step 2» (righe 108–124)
  **e** in «What NOT to do» riga 186.

Analogamente, `eval-suite-author/SKILL.md` e `eval-feedback/SKILL.md` hanno «Hard
boundary» + «What NOT to do» con almeno una regola duplicata ciascuna. Una sezione
finale di proibizioni che riepiloga regole già espresse in linea è utile se contiene
solo regole NON espresse altrove; se contiene solo duplicazioni, allunga il file
senza aggiungere informazione.

Ancoraggio: `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md:25-50`
e `SKILL.md:180-189`.

### 1.3 Problema 3 — `wiki-playbook.md` senza ToC e con wikilink orfano

`wiki-playbook.md` ha 282 righe e 8 sezioni numerate (§0–§7) ma nessuna Table of
Contents all'inizio che consenta la navigazione rapida su un file di questa lunghezza.

Alla riga 52 compare il wikilink `[[assistant-targeting]]` nella frase: «See
`[[assistant-targeting]]` for the targeting mechanism.» La pagina
`wiki/tech/assistant-targeting.md` **esiste nel wiki dogfood di Sertor** (confermato
via `Glob`), ma `wiki-playbook.md` è un asset **distribuito sugli ospiti**: il wiki
dell'ospite non ha né avrà mai una pagina `assistant-targeting`. Il wikilink è
quindi orfano nel contesto degli ospiti, e crea confusione all'agente che legge la
skill su un host terzo. La frase informativa che lo contiene non è load-bearing:
lo stesso capoverso già spiega le regole della parity guard senza bisogno del
puntatore.

Ancoraggio dogfood: `.claude/skills/wiki-author/wiki-playbook.md:52` (copia sync
della canonica bundlata).

**Conseguenze dei tre problemi:**
- ALL-CAPS riduce la leggibilità e segnala bozze non rifinite che raggiungono
  comunque gli ospiti.
- Sezioni ridondanti gonfiano i file senza aggiungere informazione; aumentano il
  rischio che una modifica a una copia non venga propagata all'altra.
- Una skill lunga senza ToC costringe chi la legge (agente o manutentore) a
  scorrere interi file; un wikilink orfano introduce confusione sul host.

**Nessun problema è critico**, ma l'insieme degrada la qualità degli asset distribuiti
e la manutenibilità. FEAT-021 ha già ridotto la duplicazione delle istruzioni
«How to invoke» nei blocchi `CLAUDE.md` e nel body di `guided-setup`; questa
feature sistema lo strato sottostante (i body delle skill).

## 2. Obiettivi e criteri di successo

- **CS-1 (ALL-CAPS eliminato)** Nei body in prosa degli asset skill in scope, il
  numero di parole intere in maiuscolo usate come enfasi (escludendo acronimi tecnici
  e blocchi di codice) è zero. Verificabile con una grep `[A-Z]{4,}` sui file
  modificati, escludendo le righe che contengono solo codice/backtick/URL.

- **CS-2 (sezioni ridondanti rimosse o condensate)** Ogni file skill modificato non
  contiene regole identiche o semanticamente equivalenti in più di una sezione: ogni
  proibizione compare in un solo posto. Verificabile leggendo le sezioni «Hard
  boundary» e «What NOT to do» (o la sezione unificata risultante) e controllando
  l'assenza di duplicazioni sui casi noti identificati in §1.2.

- **CS-3 (ToC presente in `wiki-playbook.md`)** Il file `wiki-playbook.md` contiene
  una Table of Contents come prima sezione del corpo (dopo il blocco `>` iniziale),
  con link alle sezioni §0–§7. Verificabile meccanicamente: `grep -n "^## " wiki-playbook.md`
  restituisce almeno 8 righe e nella prima sezione del file compare una lista `- [§N …](#…)`.

- **CS-4 (zero wikilink orfani negli asset distribuiti)** Il file `wiki-playbook.md`
  bundlato non contiene il pattern `[[assistant-targeting]]` né altri wikilink che
  puntano a pagine non facenti parte del bundle distribuito. Verificabile: `grep -rn "\[\["`
  negli asset skill non produce match (oppure, se wikilink sono presenti, ogni pagina
  target è un file nell'asset bundle).

- **CS-5 (nessun cambiamento semantico)** Il comportamento atteso delle skill —
  le azioni da eseguire, l'ordine dei passi, le regole di consenso, le restrizioni
  sui vehicle — non cambia. Verificabile: la guardia di parità Copilot
  (`test_assets_copilot_guard.py`) resta verde; il sync guard
  (`tests/unit/test_assets_sync.py`) resta verde dopo il re-sync dogfood; un
  confronto leggibile dei file prima/dopo non rivela diff semantici.

- **CS-6 (sync dogfood preservato)** Le copie dogfood in `.claude/skills/` restano
  in byte-parità con gli asset bundlati dopo `python -m sertor_installer.sync`.

## 3. Stakeholder e attori

- **Agente frontier dell'ospite** — legge le skill distribuite: beneficia di body
  più compatti e leggibili, privi di segnali di enfasi incongruenti.
- **Manutentore di Sertor** — modifica le skill in futuro: una sola sezione per
  regola riduce il rischio di derive silenziose (si modifica un posto, non due).
- **Revisore e auditor** — esamina gli asset nell'audit periodico: regole duplicate
  e ALL-CAPS rendono la review più lenta.
- **CI e guardie di parità** — le guardie esistenti restano verdi; non sono introdotte
  guardie nuove come Must di questa feature (potrebbero arrivare con FEAT-024).

## 4. Ambito

### In ambito

- **Body in prosa dei file skill in scope** (tabella §1.1): rimozione ALL-CAPS
  enfatico, condensazione sezioni ridondanti, ToC, fix wikilink orfano.
- **I cinque file canonici bundlati** identificati come problematici:
  `guided-setup/SKILL.md`, `eval-suite-author/SKILL.md`, `eval-feedback/SKILL.md`,
  `wiki-playbook.md`, e come caso limite (vedi §10) `eval-suite-author` e
  `eval-feedback` per il callout «How to invoke».
- **Le copie dogfood** in `.claude/skills/wiki-author/wiki-playbook.md` e
  `.claude/skills/requirements/SKILL.md`: re-sincronizzate via
  `python -m sertor_installer.sync` dopo le modifiche ai canonici.
- **La modifica è puramente di forma**: le istruzioni load-bearing restano tutte
  presenti, solo la loro collocazione o formulazione cambia.

### Fuori ambito

- **`sertor_core`**: zero modifiche (Principio XI). La feature tocca esclusivamente
  asset host-facing (file `.md`) e nessun codice di runtime.
- **Agenti distribuiti** (`concierge.md`, `wiki-curator.md`, `configuration-manager.md`,
  `requirements-analyst.md`): questa feature è scoped sulle **skill** (file di
  istruzione procedurali). Gli agenti hanno stili diversi e sono oggetto di interventi
  autonomi se necessario.
- **Blocchi `CLAUDE.md`** (`claude-md-block*.md`): già sistemati da FEAT-021 (fuori
  ambito qui, confine standing).
- **`sertor-cli-reference.md`**: introdotto da FEAT-021, non toccato qui.
- **`wiki-author/SKILL.md`** (41 righe): già pulito, nessun intervento necessario.
- **`requirements/SKILL.md`** (164 righe): clean salvo un'occorrenza "SEMPRE" in
  testo italiano — trattata come borderline (vedi §10 domande aperte).
- **Budget altitude in CI** (test che fallisce se un file skill supera N righe):
  è FEAT-024 — cross-ref dichiarato. Questa feature riduce il debito; FEAT-024
  mette il freno deterministico che impedisce il re-accumulo.
- **Installer CLI o vehicle** (`sertor install`, `sertor-rag`, ecc.): invariati.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Riduzione ALL-CAPS enfatico

- **REQ-001** The system shall replace, in the prose bodies of the in-scope skill
  assets, every whole-word ALL-CAPS usage that serves as emphasis (e.g. MANDATORY,
  ONLY, NOT, DO NOT, ASSISTED, DETERMINISTIC, DOES NOT, DATA, NAVIGATION, EMPTY,
  DISCOVER, SHOULD) with an equivalent bold or plain lowercase formulation that
  preserves the original meaning.

- **REQ-002** When replacing an ALL-CAPS emphasis marker, the system shall not
  remove the accompanying rationale or behavioural rule — the *why* must remain
  in the body, either in the same sentence or in the adjacent sentence it was
  supporting.

- **REQ-003** The system shall not alter ALL-CAPS that are legitimate acronyms
  (RAG, CLI, MCP, API, JSON, YAML, URL, TOML, NL, POSIX, STOP) or that appear
  inside code spans, code blocks, or quoted CLI output.

### Gruppo B — Condensazione sezioni ridondanti

- **REQ-004** The system shall ensure that each prohibitive rule (e.g. «do not
  import the core», «do not run without confirmation», «do not select a provider
  automatically») appears in at most one section in each skill file; if a rule
  is expressed inline in the procedural steps or in the «Hard boundary» section,
  it shall not be repeated verbatim in a «What NOT to do» section.

- **REQ-005** When condensing or merging overlapping sections, the system shall
  preserve every prohibition that exists in only one of the two sections (i.e.
  a rule present only in «What NOT to do» and absent from «Hard boundary» and
  from the procedural steps shall not be dropped).

- **REQ-006** If merging results in an empty or single-item «What NOT to do»
  section, the system shall either retain it as a brief reminder or remove the
  heading and fold its sole item into the «Hard boundary» or inline context —
  whichever preserves readability.

### Gruppo C — Table of Contents per `wiki-playbook.md`

- **REQ-007** The `wiki-playbook.md` asset shall contain a Table of Contents
  immediately following the introductory blockquote (`>`), listing links to all
  numbered sections (§0 through §7 and their direct subsections); the ToC shall
  use standard Markdown anchor links so it is navigable in any Markdown renderer.

### Gruppo D — Wikilink orfano

- **REQ-008** The bundled `wiki-playbook.md` asset shall not contain the wikilink
  `[[assistant-targeting]]`; the sentence in which it appears shall be rewritten
  in plain prose (without any wikilink) or removed if its informational content
  is already covered by the surrounding paragraph.

- **REQ-009** If a rewrite is chosen (rather than removal), the system shall ensure
  that the replacement sentence remains self-contained and does not introduce a
  reference to any page that does not exist in the asset bundle deployed to the
  host.

### Gruppo E — Guardie di parità e sync

- **REQ-010** The existing sync guard (`tests/unit/test_assets_sync.py`) shall
  remain green after the feature; the dogfood copies of the modified assets in
  `.claude/` shall be re-synced to byte-parity with the canonical bundled sources
  via `python -m sertor_installer.sync`.

- **REQ-011** The existing parity guard (`packages/sertor/tests/test_assets_copilot_guard.py`)
  shall remain green after the feature; no modified skill body shall introduce an
  assistant-specific path, slash-command, or product/model name.

- **REQ-012** The change shall not alter the installer lifecycle: install, upgrade,
  and uninstall paths for the `rag` and `governance` capabilities remain consistent;
  the modified skill files continue to be deployed and removed as they were before.

## 6. Requisiti non funzionali

- **NFR-1 (Principio XI)** Zero modifiche a `sertor_core`: la feature tocca
  esclusivamente asset host-facing (file `.md`) e nessun engine, porta, adapter,
  comando o servizio del core.
- **NFR-2 (Principio X — host-agnostico)** I body modificati restano host-agnostici:
  nessun percorso letterale dell'assistente (`.claude/`), nessun slash-command,
  nessun nome di modello o prodotto Claude. Stessa leggibilità su Claude e Copilot CLI.
- **NFR-3 (Non-regressione semantica)** La semantica comportamentale delle skill —
  le azioni da compiere, le restrizioni, il flusso — non cambia. Un agente che
  legge il body modificato deve ricevere le stesse istruzioni operative di prima,
  espresse in forma più leggibile.
- **NFR-4 (Non-regressione suite)** Le suite esistenti (`sertor`, `sertor-install-kit`,
  `sertor-flow`, root) restano verdi. In particolare: `test_assets_copilot_guard.py`,
  `test_assets_sync.py`, e ogni guard esistente su asset skill.
- **NFR-5 (Coerenza con FEAT-021)** La pulizia non re-introduce la sezione «How to
  invoke» in forma espansa in nessun body: dove FEAT-021 ha già sostituito con un
  puntatore a `sertor-cli-reference.md`, quel puntatore resta tale. Non si aggiungono
  né si espandono istruzioni di invocazione inline.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo (Principio XI):** nessuna modifica al codice di `sertor_core`.
- **Vincolo (Principio X):** i body degli asset modificati restano identici tra
  Claude e Copilot (nessuna variante per-assistente).
- **Vincolo (scope FEAT-021):** la sezione «How to invoke» in `guided-setup/SKILL.md`
  è già ridotta a un puntatore (3 righe) da FEAT-021; questa feature non la tocca,
  né re-espande.
- **Vincolo (confine skill/agente):** agenti distribuiti (`concierge.md`,
  `wiki-curator.md`, `configuration-manager.md`, `requirements-analyst.md`) fuori
  ambito — solo skill.
- **Assunzione (nessuna perdita load-bearing):** ogni regola rimossa da una sezione
  per ridondanza è effettivamente già presente altrove nello stesso file; il
  revisore (plan) verifica la conservazione prima di eliminare.
- **Assunzione (wikilink = non load-bearing):** la frase che contiene
  `[[assistant-targeting]]` è informativa e non porta alcuna istruzione che influenzi
  il comportamento dell'agente; la rimozione o la riscrittura in prosa semplice è
  sicura.
- **Dipendenza (sync guard):** `tests/unit/test_assets_sync.py` copre
  `assets/claude/**` (incluse le copie dogfood di `wiki-playbook.md` e
  `wiki-author/SKILL.md`). Le modifiche a quei file richiedono un
  `python -m sertor_installer.sync` e il guard verde.
- **Dipendenza (parity guard):** `packages/sertor/tests/test_assets_copilot_guard.py`
  verifica che i body siano host-agnostici; ogni modifica ai body va verificata
  contro questa guardia.
- **Dipendenza (FEAT-024):** il budget altitude in CI (gate che fallisce se un
  file skill supera N righe) NON viene scritto in questa feature. L'intervento qui
  riduce il debito; FEAT-024 introduce il freno automatico.
- **Dipendenza (FEAT-021 completata):** l'asset `sertor-cli-reference.md` esiste
  già (`packages/sertor/src/sertor_installer/assets/rag/sertor-cli-reference.md`);
  il callout «How to invoke» nei body eval-skills (forca §10) può puntare a questo
  asset se in scope.

## 8. Rischi

- **R-1 (Over-riduzione semantica)** Durante la condensazione di «Hard boundary» /
  «What NOT to do», si rimuove una proibizione che esiste SOLO in una delle due
  sezioni e non è espressa altrove nel file → l'agente perde un vincolo operativo.
  Mitigazione: REQ-005 obbliga a conservare ogni regola non duplicata; il plan
  deve verificare file per file prima di eliminare.

- **R-2 (Regressione sync)** Le modifiche ai canonici non vengono propagate alle
  copie dogfood → il sync guard fallisce in CI. Mitigazione: REQ-010 richiede il
  re-sync e il guard verde.

- **R-3 (ALL-CAPS rimozione acritica)** Si abbassa un ALL-CAPS che era un segnale
  genuino (es. una parola che l'agente deve trattare come keyword letterale) →
  ambiguità nella lettura. Mitigazione: REQ-003 esclude acronimi e contenuto in
  codice; il revisore controlla i casi borderline.

- **R-4 (Scope creep)** La pulizia di stile tenta di rifattorizzare la struttura
  logica delle sezioni (es. rinominare «Hard boundary» in qualcosa di diverso,
  spostare sezioni tra file) → esce dallo scope igiene. Mitigazione: §4 delimita
  esplicitamente l'ambito a forma/leggibilità, non a ristrutturazione semantica.

- **R-5 (ToC che diverge dai titoli)** La ToC aggiunta in `wiki-playbook.md`
  viene aggiornata manualmente quando cambiano i titoli di sezione → drift tra
  ToC e corpo. Mitigazione: la ToC usa anchor link standard Markdown (il link
  si rompe visibilmente se il titolo cambia); CS-3 verifica la presenza ma non
  controlla il drift futuro (presidiato da FEAT-024/lint).

- **R-6 (Wikilink rimosso ma frase lasciata incompleta)** Il `[[assistant-targeting]]`
  viene rimosso ma la frase rimane con un riferimento vuoto o senza senso →
  il testo risultante è peggiore dell'originale. Mitigazione: REQ-008 richiede
  riscrittura in prosa o rimozione della frase intera; REQ-009 obbliga a
  verificare che il risultato sia self-contained.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-007 (ToC wiki-playbook — il file ha 282 righe senza indice),
  REQ-008, REQ-009 (wikilink orfano — impatta ogni ospite che usa la skill e
  vede il link orphan), REQ-010, REQ-011, REQ-012 (guardie — non regressione
  non negoziabile).

- **Should:** REQ-001, REQ-002, REQ-003 (ALL-CAPS — leggibilità e manutenibilità,
  nessun impatto funzionale immediato), REQ-004, REQ-005, REQ-006 (condensazione
  sezioni ridondanti — riduce la superficie di deriva futura).

- **Could:** Estendere la condensazione al callout «How to invoke» in
  `eval-suite-author/SKILL.md` e `eval-feedback/SKILL.md` (vedi forca §10 —
  riduzione identica a FEAT-021 ma su file non coperti da quella feature); aggiungere
  una guardia che rilevi pattern `[[wikilink]]` nei body distribuiti (protezione
  futura contro nuovi wikilink orfani).

- **Won't (qui):** Budget altitude in CI (FEAT-024); pulizia agenti distribuiti;
  modifiche a blocchi `CLAUDE.md` (FEAT-021, done); modifiche a `sertor_core`.

## 10. Domande aperte

### Scope (da girare all'utente)

- **[DA CHIARIRE — scope]** I callout «How to invoke» in `eval-suite-author/SKILL.md`
  (righe 31–37) e `eval-feedback/SKILL.md` (righe 31–37) sono quasi identici tra
  loro e ridondanti rispetto al `sertor-cli-reference.md` introdotto da FEAT-021.
  Sostituire questi callout con un puntatore a `sertor-cli-reference.md` (come
  FEAT-021 ha fatto per `guided-setup`) è in scope per FEAT-022 (è ridondanza di
  stile) oppure è una mini-FEAT-021 separata? Se in scope: va aggiunto come SHOULD
  e trattato con la stessa logica della chiusura-del-puntatore di FEAT-021 (closure
  asset verificata offline). Se fuori scope: la ridondanza resta e va promossa come
  voce separata in roadmap/backlog.

- **[DA CHIARIRE — scope]** La riga 13 di `requirements/SKILL.md` (distribuita da
  `sertor-flow`) contiene «Considera SEMPRE l'input dell'utente» — «SEMPRE» è
  un'enfasi in maiuscolo in testo italiano. È da normalizzare in **sempre** insieme
  agli altri ALL-CAPS, o la skill `requirements` è considerata fuori scope perché
  è in italiano e il rubric si applica ai body inglesi?

### Design/plan (non bloccanti per i requisiti)

- **[DA CHIARIRE in design/plan]** Qual è la regola di condensazione precisa per
  le sezioni «Hard boundary» + «What NOT to do»? Tre opzioni: (A) mantenere entrambe
  le sezioni ma rimuovere solo le righe duplicate (sezione finale più corta);
  (B) fondere in una sola sezione «Boundaries» che contiene hard limits e
  proibizioni in unico elenco; (C) tenere «Hard boundary» per le restrizioni
  architetturali (no-import-core, consent gate) e «What NOT to do» solo per le
  restrizioni specifiche del flusso non espresse nei passi. Il *cosa* (nessuna
  duplicazione) è fissato da REQ-004; il *come* (quale struttura risultante) è
  una decisione di plan.

- **[DA CHIARIRE in design/plan]** La ToC di `wiki-playbook.md` deve includere
  anche le sottosezioni (`### Placement`, `### Host-agnostic authoring`,
  `### Truth, authority and obsolescence`)? Una ToC con solo le sezioni principali
  (§0–§7) è più stabile contro future modifiche interne; includere le sottosezioni
  dà più granularità ma deve essere mantenuta a ogni modifica del file. CS-3 richiede
  che le sezioni numerate §0–§7 siano linkate; le sottosezioni sono opzionali.

- **[DA CHIARIRE in design/plan]** Il criterio di CS-1 (grep `[A-Z]{4,}`) esclude
  le righe con backtick. Va esplicitato quali pattern di riga sono esclusi dalla
  verifica: solo le righe che iniziano con `` ` `` (code block), o anche le righe
  che contengono almeno un backtick (code span inline)? Ai fini del test, è
  sufficiente escludere le righe che iniziano con `` ``` `` (fenced block) oppure
  serve un'esclusione più granulare?
