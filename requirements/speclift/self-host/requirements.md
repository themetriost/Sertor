# Requisiti — Self-hosting SpecLift su Sertor (dogfooding)

<!-- Deriva da: FEAT-001 (epica speclift) -->

## 1. Contesto e problema (perché)

**SpecLift** (handoff da Sinthari, `github.com/themetriost/Sinthari` `master @ be4da28`, PR #5, MVP
mergiato con 104 test verdi — vedi `wiki/sources/input-other-agents/speclift-handoff-sinthari.md` e
la ricognizione ancorata `wiki/sources/input-other-agents/speclift-recon.md`) è una capacità
`diff → requisiti EARS ancorati`: dato un changeset git, genera requisiti multi-quota (capacità
utente / comportamento / implementazione), ognuno legato a `file:righe` + simbolo + test, riverificati
sul filesystem prima di essere resi ("il moat"). Il meccanismo è un "sandwich deterministico": CLI
meccanica a due marce (`speclift bundle` / `speclift assemble`) + un solo stadio di giudizio, l'agente
chiamante che scrive le frasi EARS via la skill `speclift`.

L'handoff chiede **due cose**, lasciando il *come* a Sertor: (1) installare SpecLift su Sertor stesso
(self-hosting/dogfooding — **questa feature**); (2) renderlo disponibile via l'installer a un ospite
(FEAT-002, epica separata). Questo documento copre **solo** il punto (1): rendere SpecLift
**usabile nel repo Sertor** per generare requisiti EARS ancorati dai changeset reali di Sertor, senza
toccare `sertor_core` (Principio XI).

**Perché ora e perché self-host prima di distribuire:** Sertor pratica già il dogfooding del proprio
RAG; SpecLift ne è un'estensione naturale per il "lint semantico" del rituale di step (punto 3 del
`CLAUDE.md`: verificare che wiki/`requirements/`/`CLAUDE.md` non siano andati alla deriva rispetto
all'implementazione reale). Il self-hosting è il prerequisito logico della distribuzione: non ha senso
decidere come impacchettare SpecLift per un ospite prima di aver verificato che gira nel proprio repo.

**Problemi concreti da risolvere, verificati nel recon (non ipotetici):**
- Il pacchetto Sinthari pinna `requires-python = ">=3.12"`; tutti i pacchetti Sertor pinnano `>=3.11`
  — un membro del workspace più stretto alzerebbe il pavimento effettivo dell'intero `.venv`.
- Il vehicle RAG di SpecLift è hardcodato di default a `("uv","run","--project",".sertor","sertor-rag")`
  (`config.py:27`); nel repo Sertor il RAG vive a **root** (`uv run sertor-rag`), non in un
  sottoprogetto `.sertor/` — il default upstream punterebbe al posto sbagliato se usato senza modifica.
- L'handoff e la wiki Sinthari descrivono SpecLift come utente del code-graph MCP
  (`find_symbol`/`who_calls`); il codice verificato usa **solo** `sertor-rag search --type code --json`
  via subprocess — discrepanza doc↔codice da dichiarare, non da propagare senza correzione.

## 2. Obiettivi e criteri di successo

- **CS-1 (gira nel repo Sertor):** `speclift bundle <ref>` eseguito su un commit reale di Sertor, con
  l'indice RAG del repo costruito e fresco, produce un fascicolo di evidenza non vuoto con àncore su
  file/simboli Sertor reali. Verificabile eseguendo il comando su un commit dogfood scelto.
- **CS-2 (report verificato prodotto):** il fascicolo, una volta autorato (frasi EARS scritte
  dall'agente chiamante) e passato a `speclift assemble`, produce un report canonico (JSON +
  Markdown) le cui àncore risultano riverificate sul filesystem di Sertor. Verificabile ispezionando
  l'output (nessuna àncora non verificata accettata in silenzio).
- **CS-3 (`sertor_core` invariato):** zero modifica e zero nuovo import di `sertor_core` come
  conseguenza di questa feature. Verificabile con `git diff` limitato al pacchetto core e con un
  grep di `import sertor_core`/`from sertor_core` su `packages/speclift` (atteso: zero occorrenze
  fuori da commenti che *dichiarano* di non farlo, come nell'upstream).
- **CS-4 (test integrati verdi):** la suite di test vendorata gira ed è verde nell'infrastruttura di
  test del workspace Sertor (`uv run pytest`), non solo isolatamente nel repo Sinthari originale.
- **CS-5 (nessun ciclo di dipendenze):** `uv sync --all-packages` risolve senza errori con il nuovo
  membro `packages/speclift` aggiunto al workspace.
- **CS-6 (fail-loud azionabile):** su un repo senza indice RAG costruito, l'esecuzione di SpecLift
  fallisce con l'exit code dedicato (3) e un messaggio che identifica la causa, idealmente indicando
  il comando di rimedio (`sertor-rag index .`). Verificabile eseguendo SpecLift su un repo/indice
  assente.

## 3. Stakeholder e attori

- **Manutentore di Sertor** — esegue il vendoring, verifica la riconciliazione Python, configura il
  vehicle, integra i test; garante che `sertor_core` resti invariato.
- **Agente frontier del dogfood Sertor** (Claude Code oggi) — invoca la skill `speclift` depositata,
  legge il fascicolo di evidenza e scrive le frasi EARS: è lo stadio di giudizio del sandwich.
- **Sinthari** — manutentore upstream del codice vendorato; non coinvolto operativamente in questa
  feature (nessuna PR verso il loro repo), ma la nota di provenienza lo referenzia.
- **Contributore che consulta i requisiti generati** — beneficiario finale della verifica di
  dogfooding: vede se SpecLift, applicato al repo reale di Sertor, produce evidenza sensata.

## 4. Ambito

### In ambito

- **Vendoring di `speclift`** come nuovo membro del workspace `packages/speclift`, a partire dal repo
  Sinthari `master` (con **nota di provenienza** esplicita: repository, commit, versione — pattern
  di trasparenza già in uso per asset vendorati, es. lo storico vendoring SpecKit).
- **Riconciliazione della versione Python** dichiarata (`>=3.12`) verso il pavimento del workspace
  Sertor (`>=3.11`), con **verifica empirica** (la suite gira ed è verde su 3.11) prima di considerare
  il pin abbassato valido; se risultasse irriducibile, la dichiarazione esplicita del vincolo.
- **Configurazione del vehicle RAG** per il repo Sertor (root `uv run sertor-rag`, non
  `.sertor/`-project) — requisito comportamentale esplicito, indipendente dal meccanismo scelto in
  plan.
- **Deposito della skill per il dogfood** (`.claude/skills/speclift/SKILL.md`), così l'agente Sertor
  può invocare la capacità.
- **Fail-loud sul prerequisito RAG**: indice assente/irraggiungibile → errore esplicito con exit code
  dedicato, idealmente con messaggio azionabile che indichi il comando di rimedio.
- **Integrazione dei test** vendorati (104 alla data dell'handoff) nell'infrastruttura di test del
  workspace Sertor, verdi.
- **Verifica di dogfooding end-to-end**: `speclift bundle <ref>` su un commit reale di Sertor produce
  un bundle sensato via il RAG di Sertor; il ciclo bundle→autoring→assemble produce un report
  verificato.
- **Dichiarazione esplicita** della discrepanza doc↔codice sul legame con il RAG (search CLI, non
  code-graph MCP), in questo documento e in ogni artefatto derivato (es. pagina wiki di distillazione).

### Fuori ambito

- **Distribuzione su ospiti esterni** (installer, packaging per chi installa Sertor da zero): FEAT-002,
  epica separata — la casa di distribuzione non è nemmeno decisa.
- **Traduzione IT→EN** degli asset SpecLift (codice/commenti/skill restano in italiano per il
  self-host/dogfood; è un tema linguistico trasversale del prodotto tracciato altrove).
- **Implementazione della famiglia futura** (SpecAudit, Debrief, Guida al test): capacità distinte,
  non in ambito qui.
- **Contribuire a monte** al repo Sinthari (nessuna PR verso `github.com/themetriost/Sinthari`).
- **Qualunque modifica a `sertor_core`**: la libreria core resta byte-identica; SpecLift consuma
  Sertor esclusivamente tramite il vehicle CLI `sertor-rag search`.
- **Automatizzare l'invocazione di SpecLift** dentro il rituale di step (es. farlo scattare
  automaticamente ad ogni commit, o farne un gate): resta uno strumento disponibile su richiesta, non
  un enforcement — coerente con CS-5 dell'epica.
- **Correggere la narrativa upstream** (handoff/wiki Sinthari) sulla discrepanza doc↔codice: si
  dichiara la discrepanza lato Sertor, non si tenta di farla correggere a monte.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Vendoring e provenienza

- **REQ-001** *Ubiquitous.* The Sertor workspace shall include a new member package
  `packages/speclift`, containing the speclift source code, resolvable as part of the `uv` workspace.

- **REQ-002** *Ubiquitous.* The vendored `packages/speclift` shall carry an explicit provenance note
  (source repository URL, commit hash, and version at the time of vendoring) that documents which
  upstream state it was derived from, inspectable without external lookup.

- **REQ-003** *Unwanted.* If the vendored copy of speclift is updated from a newer upstream state,
  then the provenance note shall be updated accordingly, so it never silently goes stale.

### Gruppo B — Compatibilità versione Python

- **REQ-004** *Ubiquitous.* The vendored speclift package's `requires-python` declaration shall be
  reconciled with the Sertor workspace floor (`>=3.11`), unless a genuine Python-3.12-only language
  feature is verified to be required by the codebase.

- **REQ-005** *Event-driven.* When the `requires-python` constraint of speclift is lowered to
  `>=3.11`, the vendored test suite shall be executed on a Python 3.11 interpreter and shall pass,
  as the acceptance condition for the lowered constraint.

- **REQ-006** *Unwanted.* If a genuine Python-3.12-only construct is found to be required by
  speclift's codebase, then the constraint shall NOT be silently lowered; the discrepancy shall be
  documented explicitly, together with its impact on the Sertor workspace's effective floor.

### Gruppo C — Vehicle RAG configurato per Sertor

- **REQ-007** *Ubiquitous.* The self-hosted speclift instance shall invoke the Sertor RAG through the
  vehicle command applicable to the Sertor repository root (equivalent to `uv run sertor-rag`), not
  through the upstream default vehicle that assumes a `.sertor/`-rooted sub-project.

- **REQ-008** *Ubiquitous.* The mechanism used to configure the RAG vehicle for the Sertor self-host
  shall be explicit and inspectable (documented in the vendored package or its configuration), never
  an undocumented, untracked local edit that could silently diverge from what the provenance note
  (REQ-002) implies about the vendored source.

- **REQ-009** *Event-driven.* When speclift is invoked from the Sertor repository root, it shall
  successfully reach the Sertor RAG index and return results, without requiring the invoker to pass
  ad-hoc, undocumented flags or environment variables each time.

### Gruppo D — Skill depositata per il dogfood

- **REQ-010** *Ubiquitous.* The Sertor repository shall include a copy of the speclift skill at
  `.claude/skills/speclift/SKILL.md`, so that the Sertor host agent can discover and invoke the
  capability during dogfooding.

- **REQ-011** *Ubiquitous.* The deposited skill body shall remain host-agnostic (no hardcoded
  assistant-specific paths, no slash-command syntax, no assistant model names), consistent with the
  host-agnostic property already verified in the upstream skill.

### Gruppo E — Fail-loud sul prerequisito RAG

- **REQ-012** *Unwanted.* If the Sertor RAG index is missing, unbuilt, or unreachable when speclift's
  evidence-location stage runs, then speclift shall exit with the dedicated non-zero exit code (3)
  and print an explicit, actionable error message on stderr, rather than degrading silently or
  returning fabricated/empty results as if the query had succeeded.

- **REQ-013** *Where.* Where the self-hosted instance raises the RAG-unavailable error, the error
  message shall recommend the concrete remediation command (`sertor-rag index .`, run from the
  repository root) to the user, instead of a generic "RAG unreachable" statement with no next step.

### Gruppo F — Test integrati e non-regressione

- **REQ-014** *Ubiquitous.* The vendored speclift test suite (104 tests at handoff time) shall run
  and pass within the Sertor workspace's test infrastructure (`uv run pytest`), invoked alongside the
  existing test suites of the other workspace members.

- **REQ-015** *Ubiquitous.* The `sertor-core` package shall remain unchanged — zero modification,
  zero new import — as a direct result of vendoring and self-hosting speclift (Principio XI).

- **REQ-016** *Unwanted.* If adding the `speclift` workspace member introduces a dependency cycle
  among workspace members (`sertor-core`, `sertor`, `sertor-install-kit`, `sertor-flow`, `speclift`),
  then the vendoring approach shall be revised before the feature is considered complete.

### Gruppo G — Verifica di dogfooding end-to-end

- **REQ-017** *Event-driven.* When `speclift bundle <ref>` is run against a real Sertor commit with
  the Sertor RAG index built and fresh, the command shall produce a non-empty evidence bundle whose
  items reference real Sertor file paths and (where resolvable) real symbols.

- **REQ-018** *Event-driven.* When the resulting bundle is authored (EARS statements written by the
  calling agent, referencing bundle items by index) and passed to `speclift assemble`, the command
  shall produce a canonical report (JSON + Markdown) whose anchors have been re-verified against the
  actual Sertor filesystem, with any non-verifying anchor listed under `excluded` rather than silently
  dropped.

### Gruppo H — Onestà sulla discrepanza doc↔codice

- **REQ-019** *Ubiquitous.* This feature's documentation (this requirements artifact and any wiki
  entity page distilled from it) shall state explicitly that speclift's actual runtime link to Sertor
  is a single CLI command (`sertor-rag search --type code --json`), not the MCP code-graph navigation
  tools (`find_symbol`/`who_calls`) that the upstream handoff and Sinthari wiki narrative describe.

## 6. Requisiti non funzionali

- **NFR-1 (Principio XI — vehicle-only):** SpecLift consuma il retrieval di Sertor esclusivamente
  tramite il vehicle CLI (subprocess), mai importando `sertor_core`; nessuna nuova via di accesso
  diretto alla libreria viene introdotta da questa feature.
- **NFR-2 (Isolamento dipendenze runtime):** la dipendenza runtime dichiarata da Sinthari
  (`jsonschema`, usata solo dai test di contratto per quanto verificato) dovrebbe restare/diventare
  una dipendenza di solo-test/dev quando possibile, per non gonfiare l'installazione runtime del
  pacchetto (Should — vedi DA-2).
- **NFR-3 (Additività del workspace):** l'aggiunta del membro `packages/speclift` non altera il
  comportamento o le dipendenze risolte degli altri membri esistenti (`sertor`, `sertor-install-kit`,
  `sertor-flow`); `uv sync --all-packages` continua a risolvere per tutti.
- **NFR-4 (Non-fatale sugli stadi che non toccano il RAG):** le fasi di SpecLift che non interrogano
  il RAG (`ingest`, `parse_diff`, `filter_sources`) continuano a funzionare senza indice costruito;
  solo lo stadio `locate_evidence` (e quindi l'intera marcia `bundle`) richiede il prerequisito RAG.
  Questo comportamento upstream **non va alterato** dal self-hosting.
- **NFR-5 (Lingua):** codice, commenti e skill di SpecLift restano in italiano per il self-host; è
  coerente con l'uso interno/dogfood del progetto. La traduzione per la distribuzione host-facing
  generale è fuori ambito (§4).
- **NFR-6 (Determinismo del sandwich):** nessuna delle modifiche introdotte da questa feature
  (vendoring, riconciliazione versione, vehicle, skill) altera la proprietà "un solo stadio
  intelligente" del sandwich: la CLI resta deterministica in ingresso e in uscita.

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo (ereditato dall'epica, non negoziabile):** i vincoli di design dell'handoff — sandwich
  deterministico, moat, multi-quota sempre, filtro sorgenti, vehicle-only, fail-loud, skill
  host-agnostica — si applicano invariati al self-hosting.
- **Vincolo (verificato):** il pacchetto `speclift` è self-contained sotto `src/speclift/`, hatchling,
  dominio puro ports&adapters, **zero import di `sertor_core`** (grep negativo confermato dal recon).
- **Vincolo (verificato):** l'unico consumo del RAG di Sertor è il sottocomando
  `sertor-rag search --type code --json -k 5`; l'output atteso è un array JSON piatto con almeno
  `path` (e opzionale `chunk_id`) — compatibile con la CLI Sertor odierna (`--type code` non è
  impattato dal breaking change di `--type both`, feature 070).
- **Vincolo (verificato):** il vehicle di default oggi è un campo del dataclass `Config`
  (`sertor_rag_vehicle`), usato come costante module-level `DEFAULT_CONFIG` nell'entry point CLI
  (`cli.py`); **non esiste** oggi un flag CLI o una variabile d'ambiente che lo sovrascriva senza
  toccare il codice — è un fatto rilevante per DA-3 (§10).
- **Vincolo (verificato):** `requires-python = ">=3.12"` in Sinthari, `target-version = "py312"`; nel
  grep del recon **nessuna** sintassi 3.12-only (PEP 695, `itertools.batched`) è stata trovata; l'unico
  costrutto "recente" è `StrEnum` (`domain/models.py:24`), disponibile da Python 3.11.
- **Assunzione:** `git` è già un prerequisito di SpecLift (invocato via subprocess per `git show`/
  `git diff`) — nessun requisito aggiuntivo qui, il repo Sertor lo soddisfa per definizione.
- **Dipendenza:** l'indice RAG di Sertor resta fresco tramite il meccanismo esistente
  (`sertor-rag index .`, hook `rag-freshness` SessionEnd/SessionStart, E10-FEAT-011/016); questa
  feature **non** introduce un meccanismo di refresh proprio — si appoggia a quello che c'è già.
- **Dipendenza:** la skill depositata deve restare coerente con l'upstream (`skills/speclift/SKILL.md`
  in Sinthari) salvo le correzioni di onestà richieste dal Gruppo H (discrepanza doc↔codice).

## 8. Rischi

- **R-1 — Discrepanza doc↔codice propagata senza correzione:** se la skill/documentazione depositata
  ripetesse acriticamente il claim "usa `find_symbol`/`who_calls`" senza la precisazione, gli agenti
  del dogfood potrebbero aspettarsi capacità di navigazione del code-graph che SpecLift non usa.
  **Mitigazione:** REQ-019 e Gruppo H.
- **R-2 — Pin Python 3.12 irriducibile:** se la verifica empirica su 3.11 fallisse per ragioni non
  anticipate dal grep statico, il pin resterebbe a 3.12, alzando il pavimento effettivo del
  workspace `uv`. **Mitigazione:** REQ-006, dichiarazione esplicita e valutazione dell'impatto prima
  di procedere al merge.
- **R-3 — Vehicle mal configurato → self-host silenzioso-sbagliato:** se il vehicle non venisse
  esplicitamente riconfigurato per la root Sertor, SpecLift proverebbe a invocare
  `uv run --project .sertor sertor-rag`, che nel repo Sertor **non corrisponde** al progetto RAG reale
  (situato a root) — l'errore sarebbe fail-loud (REQ-012) ma la causa (vehicle sbagliato, non "RAG
  giù") non sarebbe ovvia senza REQ-013. **Mitigazione:** REQ-007/008/009 rendono il vehicle esplicito
  e verificato, REQ-013 rende il messaggio azionabile.
- **R-4 — Deriva silenziosa del vendoring rispetto a Sinthari:** senza un processo di
  aggiornamento/nota di provenienza, la copia in `packages/speclift` può divergere silenziosamente
  dall'upstream (bug-fix o feature Sinthari non recepite). **Mitigazione:** REQ-002/003, e la
  decisione DA-1 in plan su come gestire aggiornamenti futuri.
- **R-5 — Conflitto di configurazione pytest/lint:** Sinthari usa marker `contract`/`integration` e
  `ruff` con `line-length=110`/`target-version=py312`/regola aggiuntiva `SIM`; Sertor usa marker
  `cloud`/`integration` e `ruff` con `line-length=100`/`target-version=py311`. L'integrazione dei
  test (REQ-014) potrebbe richiedere di riconciliare configurazione pytest (marker dichiarati,
  altrimenti warning/errore a seconda della configurazione pytest) e stile lint. **Mitigazione:**
  materia di plan; il requisito qui è solo l'esito (suite verde), non il meccanismo.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-014, REQ-015,
  REQ-016, REQ-017, REQ-018, REQ-019.
- **Should:** REQ-003, REQ-004, REQ-005, REQ-013.
- **Could:** REQ-006 (si applica solo se il pin risulta davvero irriducibile — condizionale, non
  detto che serva).
- **Won't (qui):** distribuzione su ospiti esterni (FEAT-002); traduzione IT→EN; implementazione di
  SpecAudit/Debrief/Guida al test; automazione dell'invocazione di SpecLift nel rituale di step;
  contributi upstream a Sinthari.

## 10. Domande aperte

- **[DA-1 — DA CHIARIRE in plan]** *Copia versionata vs sync dal repo Sinthari.* Due opzioni: **(a)
  copia versionata "one-shot"** — si vendora lo stato a un commit pinnato (`be4da28`), documentato
  dalla nota di provenienza (REQ-002), e ogni aggiornamento futuro è un'azione manuale esplicita
  (re-vendoring); **(b) meccanismo di sync** — uno script analogo a `sync.py`/`generate.py` di
  `sertor-flow` che periodicamente riallinea la copia locale allo stato upstream. **Osservazione:**
  il precedente più vicino in Sertor (SpecKit) ha **abbandonato** il vendoring a favore di un
  launch-installer (`specify init` a runtime) proprio per evitare la divergenza — ma SpecLift ha
  **codice runtime proprio eseguibile** (non solo template/istruzioni), quindi il pattern
  launch-installer non si applica direttamente: non esiste un "SpecLift upstream" da invocare a
  install-time senza portare con sé l'intero pacchetto Python. La raccomandazione debole è (a),
  più semplice e più facilmente verificabile, con (b) come possibile evoluzione se il ritmo di
  aggiornamenti upstream lo giustifica — ma la decisione finale spetta al plan.
- **[DA-2 — DA CHIARIRE in plan]** *`jsonschema` in dipendenze runtime vs dev.* Il recon conferma che
  `jsonschema` è usata **solo** dai test di contratto (`tests/contract/`), non dal runtime della
  pipeline. Spostarla in `[project.optional-dependencies].dev` (o equivalente) ridurrebbe
  l'impronta runtime del pacchetto senza perdere copertura di test — ma è una divergenza dal
  `pyproject.toml` upstream che va documentata (coerente con REQ-008) e verificata (nessun import
  runtime nascosto di `jsonschema` fuori dai test). Raccomandazione debole: spostarla; decisione
  finale in plan.
- **[DA-3 — DA CHIARIRE in plan]** *Come si materializza il vehicle configurabile per Sertor-self vs
  ospite.* Il vehicle è oggi un default hardcoded di `Config` letto come costante module-level
  (`DEFAULT_CONFIG`) dall'entry point CLI, senza flag/env var di override. Opzioni: **(a)** patchare
  direttamente la costante nella copia vendorata di Sertor, documentando la divergenza puntuale dalla
  nota di provenienza (semplice, ma è una modifica di sorgente specifica-per-host, da mantenere ad
  ogni re-vendoring); **(b)** estendere il codice vendorato con una variabile d'ambiente configurabile
  (es. un nome tipo `SPECLIFT_RAG_VEHICLE`) letta da `config.py`, così sia il self-host sia un futuro
  ospite (FEAT-002) configurano il vehicle senza toccare il sorgente — più pulito e riusabile, ma è
  una modifica funzionale al codice vendorato (non solo una patch di valore) da valutare rispetto a
  DA-1 (se poi va ri-applicata a ogni sync); **(c)** un wrapper/composition locale che costruisce
  `Components`/`Config` programmaticamente per il caso Sertor, bypassando l'entry-point console
  `speclift` standard (richiede invocare la libreria invece dello script installato, un cambio più
  invasivo dell'esperienza CLI). Nessuna opzione è scelta qui; il requisito comportamentale (REQ-007)
  resta valido indipendentemente dal meccanismo.
