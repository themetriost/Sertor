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

**Cambio di decisione del proprietario del progetto (vincolante, sostituisce l'approccio iniziale).**
I requisiti mettevano inizialmente in ambito "configurare il vehicle CLI per la root Sertor". Il
problema reale non è *quale* vehicle CLI configurare: è che SpecLift, così come vendorato, si aggancia
esclusivamente alla **CLI** (`sertor-rag search` via subprocess) mentre **il contratto d'integrazione
stabile che Sertor pubblica per i consumatori esterni è il server MCP**. Principio guida: **Sertor
espone l'MCP proprio perché i consumatori esterni NON debbano dipendere dalla CLI** — la CLI è un
consumatore interno/sottile, l'MCP è l'interfaccia d'integrazione per gli agenti. La decisione presa:
**rimuovere ogni dipendenza dalla CLI** e incapsulare il retrieval **in una skill** che usa i **tool
MCP** (`search_code`), guidata dall'agente che orchestra la localizzazione dell'evidenza. L'adapter CLI
`rag_sertor.py` (vendorato da Sinthari) **non viene usato** nel self-host (vedi Gruppo C/H).

**Problemi concreti, verificati nel recon (restano validi salvo dove annotato "SUPERATO"):**
- Il pacchetto Sinthari pinna `requires-python = ">=3.12"`; tutti i pacchetti Sertor pinnano `>=3.11`
  — un membro del workspace più stretto alzerebbe il pavimento effettivo dell'intero `.venv`.
- **[SUPERATO dal cambio di decisione]** Il vehicle RAG di SpecLift era hardcodato di default a
  `("uv","run","--project",".sertor","sertor-rag")` (`config.py:27`), puntato al posto sbagliato per il
  repo Sertor (RAG a root, non in un sottoprogetto `.sertor/`). Questo non è più un problema da
  "configurare": il self-host non invoca affatto quella CLI, quindi il vehicle hardcodato dell'upstream
  resta semplicemente inutilizzato dal path di localizzazione evidenza.
- L'handoff e la wiki Sinthari descrivono SpecLift come utente del code-graph MCP
  (`find_symbol`/`who_calls`); il codice **vendorato** (upstream, invariato in questo self-host) usa
  **solo** `sertor-rag search --type code --json` via subprocess — resta una discrepanza doc↔codice
  **nel codice upstream**, indipendente dalla decisione qui sopra. **Decisione presa qui:** per il
  self-host su Sertor, l'evidenza non viene più localizzata da quell'adapter CLI: la si ottiene tramite
  il tool MCP `search_code`, dentro una skill che orchestra l'agente — una **divergenza intenzionale
  dal codice vendorato** (non dalla narrativa upstream, a cui anzi si avvicina restando comunque un
  gap: `search_code` è ricerca semantica, non navigazione del code-graph), dichiarata e comunicata a
  Sinthari come feedback (Gruppo H).

## 2. Obiettivi e criteri di successo

- **CS-1 (gira nel repo Sertor):** il flusso self-host — evidenza localizzata dall'agente via il tool
  MCP `search_code`, poi impacchettata dallo stadio deterministico `speclift bundle` — eseguito su un
  commit reale di Sertor, con l'indice RAG del repo costruito e fresco, produce un fascicolo di
  evidenza non vuoto con àncore su file/simboli Sertor reali. Verificabile eseguendo il flusso su un
  commit dogfood scelto.
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
- **CS-6 (fail-loud azionabile):** se il server MCP di Sertor o il suo indice non sono disponibili
  quando l'agente tenta di localizzare l'evidenza (`search_code`), oppure se l'evidenza che l'agente
  passa a SpecLift è assente o malformata, l'esecuzione fallisce **esplicitamente** — mai risultati
  vuoti o inventati spacciati per evidenza valida — con un messaggio che identifica la causa e, quando
  applicabile, il rimedio (es. ricostruire/aggiornare l'indice RAG). Verificabile eseguendo il flusso
  con l'MCP/indice non disponibile o con un file di evidenza malformato.

## 3. Stakeholder e attori

- **Manutentore di Sertor** — esegue il vendoring, verifica la riconciliazione Python, predispone
  l'adapter/interfaccia MCP per il self-host (Gruppo C), integra i test; garante che `sertor_core`
  resti invariato.
- **Agente frontier del dogfood Sertor** (Claude Code oggi) — invoca la skill `speclift` depositata,
  **localizza l'evidenza** interrogando il tool MCP `search_code` (guidato dalla skill), passa
  l'evidenza a SpecLift, legge il fascicolo prodotto e scrive le frasi EARS: nel design del self-host
  tocca **due stadi** del sandwich (localizzazione + stesura), non uno solo come nel design originale
  di Sinthari — deviazione dichiarata (vedi NFR-6, R-6).
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
- **Retrieval incapsulato in una skill via MCP, non via CLI** — il self-host **non** dipende dalla
  CLI `sertor-rag search` (l'adapter `SertorRagLocator`/`rag_sertor.py` vendorato resta inutilizzato):
  la localizzazione dell'evidenza (simboli/test) avviene tramite il tool MCP `search_code`, invocato
  dall'agente orchestratore dentro la skill; la porta `EvidenceLocator` è alimentata dall'evidenza già
  ottenuta dall'agente, attraverso un'interfaccia esplicita e ispezionabile (meccanismo esatto in
  plan, vedi DA-4).
- **Deposito della skill per il dogfood** (`.claude/skills/speclift/SKILL.md`), estesa a **orchestrare
  anche il retrieval** (localizzazione dell'evidenza via MCP `search_code`, non solo la stesura EARS),
  così l'agente Sertor può invocare l'intera capacità end-to-end restando host-agnostico.
- **Fail-loud sulla localizzazione dell'evidenza**: MCP/indice non disponibile quando l'agente tenta
  di localizzare l'evidenza, **o** evidenza fornita dall'agente assente/malformata → la skill/pipeline
  lo segnala esplicitamente, mai risultati vuoti o inventati spacciati per validi (Principio XII).
- **Integrazione dei test** vendorati (104 alla data dell'handoff) nell'infrastruttura di test del
  workspace Sertor, verdi.
- **Verifica di dogfooding end-to-end**: il ciclo localizzazione-evidenza (agente + MCP `search_code`)
  → bundle → autoring → assemble, eseguito su un commit reale di Sertor, produce un report verificato.
- **Dichiarazione esplicita** che il self-host **diverge intenzionalmente** dal codice vendorato/
  upstream (che usa la CLI `sertor-rag search`) adottando l'MCP (`search_code`) per la localizzazione
  dell'evidenza, con **feedback inviato a Sinthari** (canale `input-other-agents`) per un'eventuale
  convergenza upstream — in questo documento e in ogni artefatto derivato (es. pagina wiki di
  distillazione).

### Fuori ambito

- **Distribuzione su ospiti esterni** (installer, packaging per chi installa Sertor da zero): FEAT-002,
  epica separata — la casa di distribuzione non è nemmeno decisa.
- **Traduzione IT→EN** degli asset SpecLift (codice/commenti/skill restano in italiano per il
  self-host/dogfood; è un tema linguistico trasversale del prodotto tracciato altrove).
- **Implementazione della famiglia futura** (SpecAudit, Debrief, Guida al test): capacità distinte,
  non in ambito qui.
- **Contribuire a monte** al repo Sinthari (nessuna PR verso `github.com/themetriost/Sinthari`).
- **Qualunque modifica a `sertor_core`**: la libreria core resta byte-identica; SpecLift consuma
  Sertor esclusivamente tramite il tool MCP `search_code`, mai importando `sertor_core` e mai tramite
  la CLI `sertor-rag search`.
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

### Gruppo C — Retrieval via MCP dentro una skill, non via CLI

- **REQ-007** *Unwanted.* If the self-hosted speclift instance's evidence-location path attempted to
  invoke the `sertor-rag` CLI (subprocess vehicle) — including the upstream `SertorRagLocator` adapter
  (`adapters/rag_sertor.py`) — then that path shall be considered incorrect for the self-host: the
  self-host shall NOT depend on, or invoke, the `sertor-rag` CLI for locating evidence.

- **REQ-008** *Ubiquitous.* The self-hosted speclift instance shall locate evidence (candidate symbols
  and covering tests) exclusively through Sertor's MCP tool `search_code`, invoked by the orchestrating
  agent from within a dedicated skill — never by a deterministic pipeline stage querying the RAG
  directly, and never by importing `sertor_core`.

- **REQ-009** *Ubiquitous.* The `EvidenceLocator` port implementation used by the self-host shall be
  fed by evidence that the orchestrating agent has already located (via MCP), rather than performing
  live retrieval queries itself; the interface through which the agent hands this located evidence to
  speclift shall be explicit and inspectable (e.g., a documented JSON artifact produced by the agent),
  never an implicit or undocumented convention. The exact shape of this interface is a plan-level
  decision (see DA-4, §10).

### Gruppo D — Skill depositata per il dogfood

- **REQ-010** *Ubiquitous.* The Sertor repository shall include a copy of the speclift skill at
  `.claude/skills/speclift/SKILL.md`, so that the Sertor host agent can discover and invoke the
  capability during dogfooding. For the self-host, this skill shall additionally instruct the agent to
  orchestrate evidence localization — querying Sertor's `search_code` MCP tool per changed hunk — and
  to hand the resulting evidence to speclift's deterministic bundle stage (per REQ-009's interface),
  before authoring the EARS statements.

- **REQ-011** *Ubiquitous.* The deposited skill body shall remain host-agnostic (no hardcoded
  assistant-specific paths, no slash-command syntax, no assistant model names), consistent with the
  host-agnostic property already verified in the upstream skill.

### Gruppo E — Fail-loud sulla localizzazione dell'evidenza

- **REQ-012** *Unwanted.* If Sertor's MCP server or its RAG index is unavailable or unreachable when
  the orchestrating agent attempts to locate evidence via `search_code`, then the skill shall stop and
  report this explicitly, naming the unavailable component and (when applicable) the remediation
  action (e.g., rebuilding/refreshing the RAG index), rather than continuing with a partial, empty, or
  fabricated evidence set as if retrieval had succeeded.

- **REQ-013** *Unwanted.* If the evidence artifact that the orchestrating agent hands to speclift (per
  REQ-009) is missing, malformed, or does not conform to its documented interface, then speclift's
  evidence-consuming stage shall fail loud with an explicit, actionable error identifying the problem,
  rather than silently falling back to empty/default evidence or fabricating an anchor.

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

- **REQ-017** *Event-driven.* When the self-hosted flow — evidence located by the orchestrating agent
  via the MCP tool `search_code`, then packaged by speclift's deterministic bundle stage — is run
  against a real Sertor commit with the Sertor RAG index built and fresh, it shall produce a non-empty
  evidence bundle whose items reference real Sertor file paths and (where resolvable) real symbols.

- **REQ-018** *Event-driven.* When the resulting bundle is authored (EARS statements written by the
  calling agent, referencing bundle items by index) and passed to `speclift assemble`, the command
  shall produce a canonical report (JSON + Markdown) whose anchors have been re-verified against the
  actual Sertor filesystem, with any non-verifying anchor listed under `excluded` rather than silently
  dropped.

### Gruppo H — Onestà sulla divergenza dal codice vendorato (INVERTITO)

> **Nota di revisione:** questo gruppo dichiarava in origine che SpecLift usa la CLI-search e non
> l'MCP. Con il cambio di decisione, è **invertito**: il self-host **adotta** l'MCP, in divergenza
> intenzionale dal codice vendorato/upstream (che resta sulla CLI); il gap residuo rispetto alla
> narrativa upstream (code-graph navigation) non è comunque colmato — vedi REQ-019.

- **REQ-019** *Ubiquitous.* This feature's documentation (this requirements artifact and any wiki
  entity page distilled from it) shall state explicitly that the self-hosted instance's
  evidence-location mechanism **intentionally diverges** from the vendored/upstream Sinthari code —
  which reaches Sertor exclusively via the `sertor-rag search --type code --json` CLI subprocess
  (`adapters/rag_sertor.py`) — by consuming evidence located through Sertor's MCP tool `search_code`,
  invoked by the orchestrating agent within the skill, instead of the CLI vehicle. The same
  documentation shall also state that this does not fully realize the upstream handoff/wiki
  narrative's original claim of code-graph navigation (`find_symbol`/`who_calls`): `search_code` is a
  semantic search tool, not a graph-navigation tool, so a smaller, shifted doc↔mechanism gap remains.

- **REQ-020** *Event-driven.* When this divergence from the vendored/upstream code is adopted for the
  self-host, it shall be recorded as feedback to Sinthari through the existing `input-other-agents`
  intake channel (`wiki/sources/input-other-agents/`), so that Sinthari can decide whether to converge
  the upstream `speclift` codebase toward MCP-based retrieval.

## 6. Requisiti non funzionali

- **NFR-1 (Principio XI — vehicle-only, MCP):** SpecLift consuma il retrieval di Sertor esclusivamente
  tramite il vehicle MCP (tool `search_code`), mai tramite CLI subprocess e mai importando
  `sertor_core`; nessuna nuova via di accesso diretto alla libreria viene introdotta da questa feature.
  (Sertor pubblica sia CLI sia MCP come vehicle legittimi — Principio XI — ma il self-host sceglie
  l'MCP come **unico** vehicle usato dal proprio path di localizzazione evidenza, disattivando
  l'adapter CLI vendorato.)
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
- **NFR-6 (Determinismo del sandwich — DEVIAZIONE DICHIARATA):** spostare la localizzazione
  dell'evidenza dall'adapter CLI deterministico all'agente (che la ottiene coi tool MCP, guidato dalla
  skill) fa sì che l'agente tocchi **due stadi** del sandwich — localizzazione dell'evidenza E stesura
  delle frasi EARS — anziché il solo stadio di stesura del design originale ("un solo stadio
  intelligente"). È una **deviazione dichiarata** dal principio "sandwich a un solo stadio
  intelligente" di Sinthari, non un'estensione silenziosa: comunicata come feedback a Sinthari
  (REQ-020). Le fasi di impacchettamento (bundle), verifica delle àncore (**il moat**) e resa (render)
  **restano** deterministiche e NON toccano il RAG — è lì che il moat preserva la garanzia forte
  (nessuna àncora accettata senza riverifica sul filesystem).

## 7. Vincoli, assunzioni e dipendenze

- **Vincolo (ereditato dall'epica, non negoziabile):** i vincoli di design dell'handoff — sandwich
  deterministico, moat, multi-quota sempre, filtro sorgenti, vehicle-only, fail-loud, skill
  host-agnostica — si applicano invariati al self-hosting.
- **Vincolo (verificato):** il pacchetto `speclift` è self-contained sotto `src/speclift/`, hatchling,
  dominio puro ports&adapters, **zero import di `sertor_core`** (grep negativo confermato dal recon).
- **Vincolo (verificato, riferito al codice vendorato/upstream, non usato nel self-host):** l'unico
  consumo del RAG di Sertor nell'adapter CLI vendorato è il sottocomando
  `sertor-rag search --type code --json -k 5`; l'output atteso è un array JSON piatto con almeno
  `path` (e opzionale `chunk_id`). Questo adapter (`SertorRagLocator`/`rag_sertor.py`) **non viene
  invocato** dal self-host (Gruppo C): è riportato qui solo come fatto di provenienza/tracciabilità.
- **[SUPERATO dal cambio di decisione, conservato come cronologia]** Il vehicle di default era un
  campo del dataclass `Config` (`sertor_rag_vehicle`), usato come costante module-level
  `DEFAULT_CONFIG` nell'entry point CLI (`cli.py`); **non esisteva** un flag CLI o una variabile
  d'ambiente che lo sovrascrivesse senza toccare il codice — era il fatto rilevante per la vecchia
  DA-3 (§10, ora superata). Con la rimozione della dipendenza dalla CLI, questo vincolo non si applica
  più al self-host: la nuova domanda aperta equivalente è **DA-4** (§10), sulla forma dell'interfaccia
  evidenza-agente→SpecLift.
- **Vincolo (nuovo, dal cambio di decisione):** il retrieval per il self-host avviene esclusivamente
  tramite il tool MCP `search_code` del server `sertor-rag` (le istruzioni del server prescrivono di
  citare sempre `path#chunk`); il file vendorato `adapters/rag_sertor.py` resta presente o meno nella
  copia vendorata a seconda di come si risolve DA-1/DA-4 (§10), ma in ogni caso **non è usato** dal
  path di localizzazione evidenza del self-host.
- **Vincolo (verificato):** `requires-python = ">=3.12"` in Sinthari, `target-version = "py312"`; nel
  grep del recon **nessuna** sintassi 3.12-only (PEP 695, `itertools.batched`) è stata trovata; l'unico
  costrutto "recente" è `StrEnum` (`domain/models.py:24`), disponibile da Python 3.11.
- **Assunzione:** `git` è già un prerequisito di SpecLift (invocato via subprocess per `git show`/
  `git diff`) — nessun requisito aggiuntivo qui, il repo Sertor lo soddisfa per definizione.
- **Dipendenza:** l'indice RAG di Sertor resta fresco tramite il meccanismo esistente
  (`sertor-rag index .`, hook `rag-freshness` SessionEnd/SessionStart, E10-FEAT-011/016); questa
  feature **non** introduce un meccanismo di refresh proprio — si appoggia a quello che c'è già.
- **Dipendenza:** la skill depositata deve restare coerente con l'upstream (`skills/speclift/SKILL.md`
  in Sinthari) salvo (a) le correzioni di onestà richieste dal Gruppo H (divergenza dal codice
  vendorato + gap residuo sulla narrativa upstream) e (b) l'estensione di orchestrazione del retrieval
  via MCP richiesta dal Gruppo C/D — assente nell'upstream, la cui CLI la esegue internamente.

## 8. Rischi

- **R-1 — Discrepanza doc↔codice propagata senza correzione:** anche dopo il cambio di decisione
  (adozione dell'MCP `search_code` per il self-host), la capacità reale resta **ricerca semantica**,
  non **navigazione del code-graph** (`find_symbol`/`who_calls`) come descrive la narrativa upstream
  (handoff/wiki Sinthari): se la skill/documentazione depositata lasciasse intendere che l'adozione
  dell'MCP colma questo gap, gli agenti del dogfood si aspetterebbero una capacità di navigazione che
  SpecLift non ha. **Mitigazione:** REQ-019/020 e Gruppo H dichiarano sia la divergenza dal codice
  vendorato sia il gap residuo rispetto alla narrativa originale.
- **R-2 — Pin Python 3.12 irriducibile:** se la verifica empirica su 3.11 fallisse per ragioni non
  anticipate dal grep statico, il pin resterebbe a 3.12, alzando il pavimento effettivo del
  workspace `uv`. **Mitigazione:** REQ-006, dichiarazione esplicita e valutazione dell'impatto prima
  di procedere al merge.
- **R-3 — Interfaccia agente↔SpecLift mal definita → evidenza persa o rifiutata silenziosamente:** se
  l'interfaccia tra l'agente (che localizza l'evidenza via MCP `search_code`) e lo stadio di consumo di
  SpecLift non fosse esplicita/ispezionabile (REQ-009), l'agente potrebbe passare evidenza in un
  formato inatteso, con SpecLift che la scarta silenziosamente o la interpreta in modo scorretto — un
  guasto più subdolo del vecchio "vehicle sbagliato", perché non c'è un unico comando CLI che fallisce
  in modo osservabile. **Mitigazione:** REQ-007/008/009 rendono l'interfaccia esplicita, REQ-013
  impone il fail-loud sull'evidenza malformata invece dell'accettazione silenziosa.
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
- **R-6 — Deviazione dal sandwich a un solo stadio intelligente:** spostare la localizzazione
  dell'evidenza dall'adapter CLI deterministico all'agente fa sì che l'agente tocchi **due stadi**
  (localizza l'evidenza via MCP E scrive le frasi EARS), non uno solo come nel design originale di
  Sinthari. È una deviazione **dichiarata**, non un compromesso silenzioso: il moat (verifica delle
  àncore sul filesystem) resta l'ultima rete che impedisce a un'evidenza mal-localizzata di produrre un
  requisito accettato. **Mitigazione:** la deviazione è comunicata a Sinthari come feedback (REQ-020,
  canale `input-other-agents`), così può essere valutata/eventualmente convergere upstream; nel
  frattempo il moat (invariato, NFR-6) contiene il rischio residuo.

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-007, REQ-008, REQ-009, REQ-010, REQ-011, REQ-012, REQ-013, REQ-014,
  REQ-015, REQ-016, REQ-017, REQ-018, REQ-019, REQ-020.
- **Should:** REQ-003, REQ-004, REQ-005.
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
  `pyproject.toml` upstream che va documentata esplicitamente (stesso principio di trasparenza della
  nota di provenienza, REQ-002/003) e verificata (nessun import runtime nascosto di `jsonschema` fuori
  dai test). Raccomandazione debole: spostarla; decisione finale in plan.
- **[DA-3 — SUPERATA dal cambio di decisione, non più DA CHIARIRE]** *Come si materializza il vehicle
  configurabile per Sertor-self vs ospite.* Conservata qui come cronologia: le opzioni (a)/(b)/(c) sotto
  presupponevano che il self-host continuasse a invocare `sertor-rag` via CLI, limitandosi a
  riconfigurare il vehicle di default. Il cambio di decisione (§1) rimuove questa dipendenza del
  tutto — non esiste più un "vehicle CLI da configurare" per il self-host, perché la localizzazione
  dell'evidenza non passa più dalla CLI. **Non va risolta**: la domanda aperta equivalente oggi è
  **DA-4** qui sotto.
  <br>*Testo originale (invariato, solo per tracciabilità):* Il vehicle è oggi un default hardcoded di
  `Config` letto come costante module-level (`DEFAULT_CONFIG`) dall'entry point CLI, senza flag/env var
  di override. Opzioni: **(a)** patchare direttamente la costante nella copia vendorata di Sertor,
  documentando la divergenza puntuale dalla nota di provenienza (semplice, ma è una modifica di
  sorgente specifica-per-host, da mantenere ad ogni re-vendoring); **(b)** estendere il codice
  vendorato con una variabile d'ambiente configurabile (es. un nome tipo `SPECLIFT_RAG_VEHICLE`) letta
  da `config.py`, così sia il self-host sia un futuro ospite (FEAT-002) configurano il vehicle senza
  toccare il sorgente — più pulito e riusabile, ma è una modifica funzionale al codice vendorato (non
  solo una patch di valore) da valutare rispetto a DA-1 (se poi va ri-applicata a ogni sync); **(c)** un
  wrapper/composition locale che costruisce `Components`/`Config` programmaticamente per il caso
  Sertor, bypassando l'entry-point console `speclift` standard (richiede invocare la libreria invece
  dello script installato, un cambio più invasivo dell'esperienza CLI).
- **[DA-4 — DA CHIARIRE in plan, nuova]** *Forma esatta dell'interfaccia evidenza-agente→SpecLift, e
  suo utilizzo nei test.* Il cambio di decisione impone che l'`EvidenceLocator` sia alimentato
  dall'evidenza già localizzata dall'agente (via MCP `search_code`), non da query live eseguite dalla
  porta. Restano aperte: **(a)** la forma esatta dell'artefatto che l'agente produce — es. un JSON con
  gli stessi campi già modellati da `Symbol`/`TestRef` in `domain/models.py`
  (`name`/`path`/`line`/`kind`/`provenance` per i simboli; `name`/`path`/`covers_symbol`/`line`/
  `provenance` per i test), o un formato più grezzo che un adapter self-host traduce — e dove vive
  (es. `<TMP>/speclift-evidence-input.json` accanto agli altri file temporanei del sandwich, o un
  percorso dedicato); **(b)** se `adapters/rag_sertor.py` (l'adapter CLI vendorato da Sinthari) viene
  **escluso fisicamente** dalla copia vendorata in `packages/speclift`, oppure vendorato-ma-morto (mai
  importato dal composition root del self-host) — coerente con DA-1 (copia one-shot vs sync: escludere
  selettivamente un file complica un futuro re-vendoring "tutto il tree"; tenerlo-ma-morto è più
  semplice ma lascia codice inerte/potenzialmente fuorviante nel pacchetto). **Osservazione:** un
  test-double con la stessa forma esiste **già** upstream — `FakeLocator` in
  `tests/unit/test_locate_evidence.py` (implementa `locate_symbols`/`locate_tests` restituendo dati
  precostituiti per file/simbolo) — è il precedente più vicino a un adapter "alimentato" invece che
  "attivo": la nuova classe di produzione per il self-host può ricalcarne la forma (stessa interfaccia
  di porta, dati letti da un artefatto invece che cablati nel test). Raccomandazione debole: JSON con
  la stessa forma di `Symbol`/`TestRef` (riuso dei modelli di dominio già esistenti, zero nuovo schema
  da inventare), e `rag_sertor.py` escluso fisicamente dalla copia (un ospite che ispeziona
  `packages/speclift` non trova così codice morto che finge di essere usato). Decisione finale in plan.
