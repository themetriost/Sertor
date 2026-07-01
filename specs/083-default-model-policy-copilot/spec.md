# Feature Specification: Default model-policy per i subagent Copilot CLI (E2-FEAT-015)

**Feature Branch**: `083-default-model-policy-copilot` · **Created**: 2026-07-01 · **Status**: Draft

<!-- Deriva da: FEAT-015 (epica sertor-cli E2) — requirements/sertor-cli/default-model-policy-copilot/requirements.md (user feedback wiki/sources/usersfeedback/copilot-default-models.md, 2026-06-30) -->

**Input**: FEAT-015 dell'epica `sertor-cli` (E2). Quando l'ospite è **GitHub Copilot CLI**, Sertor
distribuisce cinque agenti propri (Sertor-authored) come *custom-agent* `.agent.md`: `concierge` e
`wiki-curator` (pacchetto `sertor`); `requirements-analyst`, `configuration-manager` e la skill
`requirements` resa come custom-agent (pacchetto `sertor-flow`). Oggi il renderer di questi file
**omette sempre** il campo `model:` → la scelta del modello resta implicita, affidata al default della
CLI Copilot dell'utente al momento dell'esecuzione. Un utente Copilot CLI ha segnalato che questo
produce **variabilità non voluta** tra installazioni: agenti con profili cognitivi molto diversi
(dispatcher meccanici come `concierge`/`configuration-manager`, agenti di scrittura/reasoning come
`requirements-analyst`/`requirements`, agenti di sintesi come `wiki-curator`) finiscono tutti sullo
stesso modello implicito, senza un default ragionato che ottimizzi costo/latenza sui task meccanici e
tenga alta la qualità sulle fasi ad alto impatto. Il valore: **ogni agente Copilot CLI Sertor-authored
riceve, all'installazione, un modello di default ragionato — non la selezione implicita di oggi —
restando modificabile dall'utente**, con una fonte unica versionata dei model-ID.

---

> **Allineamento alla missione (gate Constitution).** La stella polare di Sertor è dotare l'ospite di
> auto-conoscenza interrogabile portabile e senza lock-in, il cui differenziatore è la qualità del
> contesto reso all'agente frontier ospite. Assegnare a ciascun agente un modello adeguato al suo compito
> (meccanico → economico/veloce; scrittura/reasoning/sintesi → capace) **migliora la qualità e la
> prevedibilità del lavoro che l'agente ospite svolge sul corpus fuso code+doc**, e rende la
> host-agnosticità (Principio X) più reale: l'agente installato «funziona bene» su Copilot senza che
> l'utente debba configurare a mano i modelli. È distribuzione host-facing sul confine **D↔N**: nessun
> codice del core, nessun LLM invocato dall'installer — solo un *default* scritto in un file, che l'utente
> resta libero di cambiare.

> **Natura del cambiamento: ADDITIVA / distribuzione-installer, ZERO runtime di `sertor_core`
> (Principio XI).** La feature vive interamente nei pacchetti di distribuzione (`sertor`, `sertor-flow`,
> kit condiviso `sertor-install-kit`); **non** importa né invoca `sertor_core`, non introduce nuovi
> provider di modello né logica di instradamento runtime. Aggiunge una **fonte unica versionata**
> agente→model-ID e fa emettere il campo `model:` nel frontmatter dei 5 custom-agent Copilot. **Zero
> impatto sul path Claude**: il `model: sonnet` di `concierge` e gli altri frontmatter Claude restano
> byte-per-byte invariati.

> **Decisioni di scope — FISSATE (ratificate dall'utente; non riaprire).**
> - **Meccanismo A (confermato):** il modello di default per-agente si imposta col campo `model:` nel
>   **frontmatter YAML del file `.agent.md`** che Sertor deposita per Copilot CLI (documentato
>   ufficialmente da GitHub). **Scartato** il meccanismo B (settings machine-global
>   `~/.copilot/settings.json`): schema non documentato, viola i principi per-repo/non-distruttivo/
>   host-agnostico.
> - **Scope: solo i 5 agenti Sertor-authored** resi come `.agent.md` su Copilot CLI. Gli `speckit.*` sono
>   prompt-file vendorati da spec-kit → **fuori ambito, limite dichiarato e tracciato** (promuovere a
>   nuova voce di backlog, non sepolto).
> - **Solo Copilot CLI.** Nessun impatto sul path Claude.
> - **Profilo modelli versionato** come fonte unica agente→model-ID, nel kit condiviso
>   `sertor-install-kit` (leggibile da `sertor` e `sertor-flow` senza introdurre la dipendenza vietata
>   `sertor-flow`→`sertor-core`).
> - **Override utente al sicuro per costruzione:** un cambio fatto con il picker `/subagents` di Copilot
>   persiste in `~/.copilot/settings.json` (file diverso dal `.agent.md`) e vince a runtime; Sertor scrive
>   solo il *default* nel frontmatter → non c'è conflitto da proteggere ad hoc.
> - **Nessun probe install-time della disponibilità modelli del tenant** (installer offline): il
>   «fail-loud sulla disponibilità» è **documentale + comportamento runtime di Copilot**, non un controllo
>   install-time.
> - **Fail-loud REALE e install-time** invece è quello sul **profilo incompleto**: se la fonte unica non
>   copre uno dei 5 agenti in ambito → l'installazione FALLISCE nominando l'agente mancante.
> - La policy è un **default modificabile** (via `/subagents` o editando il frontmatter), non una regola
>   rigida — da comunicare in doc.

> **Ancoraggio all'esistente (dato di partenza, non da progettare — i riferimenti ancorano i requisiti,
> non prescrivono il *come*).** Il renderer dei custom-agent Copilot
> (`packages/sertor-install-kit/.../surfaces.py`, `render_custom_agent`) oggi omette `model:` di default e,
> se abilitato, lo eco-emette verbatim dal frontmatter canonico (alias Claude, invalido su Copilot) — non
> da una policy: la sostituzione dal profilo è il gap architetturale da colmare (materia di plan). Punti di
> deposito reali dei 5 agenti: `concierge` (`install_rag.py`, `_concierge_artifact`/`_render_rag_file`),
> `wiki-curator` (`install_wiki.py`, artifact/`_render_for_target`), `requirements-analyst`/
> `configuration-manager`/`requirements` (`install_governance.py`, `_SERTOR_AUTHORED`/
> `build_governance_plan`/`_render_for_target`). Guardie esistenti da **riconciliare** (non rimuovere):
> `test_assets_copilot_guard.py` e `test_schema_copilot_frontmatter.py` impongono oggi «`model:` sempre
> assente» → vanno riformulate a «alias Claude (`haiku`/`sonnet`/`opus`) sempre assente **e** `model:` di
> policy nativo Copilot ammesso e atteso». Targeting via `AssistantId.COPILOT_CLI` /
> `AssistantProfile.render_path` / `command_vehicle=CUSTOM_AGENT`.

> **Policy di default iniziale (default ragionato — i model-ID vivono nel profilo versionato, qui citati
> come default iniziale, non hardcoded).**
>
> | Agente | Pacchetto | Modello di default (iniziale) | Razionale |
> |---|---|---|---|
> | `concierge` | `sertor` | `claude-haiku-4.5` | dispatcher/orchestratore sottile, task meccanico → economico/veloce |
> | `configuration-manager` | `sertor-flow` | `claude-haiku-4.5` | operazioni git meccaniche rette da brief → economico/veloce |
> | `requirements-analyst` | `sertor-flow` | `claude-sonnet-4.6` | analisi/scrittura requisiti, alto impatto → capace |
> | `requirements` | `sertor-flow` | `claude-sonnet-4.6` | elicitazione/scrittura EARS, alto impatto → capace |
> | `wiki-curator` | `sertor` | `claude-sonnet-4.6` | sintesi/curation della conoscenza → capace |
>
> I model-ID sono **datati** e invecchiano: vivono nel profilo versionato (fonte unica), non sparsi nel
> codice installer; aggiornarli è una modifica deliberata di **un solo** artefatto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Ogni agente Copilot CLI riceve un default esplicito (P1, Must)
Un utente che installa Sertor su un repo ospite con Copilot CLI ottiene **tutti e cinque** i custom-agent
Sertor-authored con un campo `model:` esplicito e non-vuoto nel frontmatter — nessun agente a selezione
implicita. Il modello di ciascun agente è quello prescritto dalla policy versionata (non l'alias Claude
ereditato dall'asset canonico).

**Independent Test**: eseguendo il piano di deposito per `COPILOT_CLI` in una directory temporanea e
leggendo i 5 `.agent.md` resi, ciascuno espone un `model:` non-vuoto pari al valore che il profilo
prescrive per quell'agente.

**Acceptance**:
1. **Given** un ospite Copilot CLI, **When** `sertor install rag` deposita `concierge` e `wiki-curator`,
   **Then** ciascun `.agent.md` ha un `model:` esplicito non-vuoto uguale al valore del profilo per
   quell'agente.
2. **Given** un ospite Copilot CLI, **When** `sertor-flow install` deposita `requirements-analyst`,
   `configuration-manager`, `requirements`, **Then** ciascun `.agent.md` ha un `model:` esplicito
   non-vuoto uguale al valore del profilo per quell'agente.
3. **Given** un asset canonico il cui frontmatter porta un alias Claude (es. `model: sonnet`), **When**
   viene reso per Copilot CLI, **Then** il `model:` emesso è quello della policy Copilot, **non** l'alias
   Claude ereditato.

### User Story 2 — Un profilo incompleto fa fallire l'installazione nominando l'agente mancante (P1, Must)
Un manutentore che aggiunge un sesto agente in ambito, o rimuove per errore la voce di uno dei cinque dal
profilo versionato, ottiene un'installazione che **fallisce a install-time** con un messaggio che
**nomina** l'agente privo di voce — nessuna installazione silenziosamente incompleta (agente depositato
senza modello o con valore indefinito).

**Independent Test**: eseguendo il deposito per Copilot CLI con un profilo a cui manca la voce di un agente
in ambito, l'installazione fallisce e il messaggio nomina l'agente mancante; con il profilo completo,
riesce.

**Acceptance**:
1. **Given** un profilo che copre tutti e cinque gli agenti in ambito, **When** si installa su Copilot CLI,
   **Then** l'installazione riesce e ogni agente ottiene il suo modello.
2. **Given** un profilo privo della voce per uno dei cinque agenti in ambito, **When** si installa su
   Copilot CLI, **Then** l'installazione fallisce con un errore che **nomina** l'agente mancante.
3. **Given** il fallimento su profilo incompleto, **When** l'installazione si interrompe, **Then** nessun
   agente in ambito è depositato senza `model:` o con un valore indefinito.

### User Story 3 — Fonte unica versionata condivisa dai due pacchetti (P1, Must)
Un manutentore che deve aggiornare un model-ID datato lo modifica in **un solo** artefatto versionato,
leggibile identicamente da `sertor` e `sertor-flow`. Un host che installa entrambi i pacchetti riceve una
policy **coerente** (stesso ID per lo stesso agente), senza ID hardcoded/sparsi nel codice installer e
senza introdurre la dipendenza vietata `sertor-flow`→`sertor-core`.

**Independent Test**: si verifica che tutti i model-ID assegnati provengano dal profilo versionato
condiviso (nessun ID letterale sparso nel codice di deposito per-agente) e che i due pacchetti risolvano lo
stesso agente allo stesso ID.

**Acceptance**:
1. **Given** i model-ID della policy, **When** si ispeziona il codice installer, **Then** ogni ID proviene
   dal profilo versionato condiviso; 0 ID hardcoded per-agente nel codice di deposito.
2. **Given** un host che installa sia `sertor` sia `sertor-flow`, **When** entrambi depositano i loro
   agenti, **Then** la policy applicata è identica (stessa fonte, stessa versione).
3. **Given** un bump di un model-ID, **When** lo si applica, **Then** richiede la modifica di un solo
   artefatto versionato (non una ricerca/sostituzione sparsa).

### User Story 4 — Zero impatto su Claude, nessun leak di alias Claude su Copilot (P1, Must)
Un utente Claude non subisce alcun cambiamento: il `model: sonnet` di `concierge` e gli altri frontmatter
Claude restano bit-per-bit invariati. Sui custom-agent Copilot resta vietato il leak di un alias-modello
Claude (`haiku`/`sonnet`/`opus`) ereditato dall'asset — ma un `model:` nativo Copilot prescritto dalla
policy è ammesso e atteso.

**Independent Test**: i frontmatter Claude resi restano identici al baseline; i frontmatter Copilot resi
non contengono alcun alias Claude, e contengono il model-ID nativo della policy.

**Acceptance**:
1. **Given** il path Claude, **When** la feature è completa, **Then** i 5 frontmatter Claude sono
   byte-identici al baseline (incluso il `model: sonnet` di `concierge`).
2. **Given** un frontmatter Copilot reso, **When** lo si ispeziona, **Then** non contiene alcun alias
   Claude (`haiku`/`sonnet`/`opus`).
3. **Given** le guardie esistenti che oggi impongono «`model:` sempre assente» su Copilot, **When** la
   feature è completa, **Then** sono riformulate a «alias Claude sempre assente **e** `model:` di policy
   nativo ammesso e atteso», e restano verdi.

### User Story 5 — La policy raggiunge l'ospite via installer, con doc aggiornata (P1, Must, DoD)
Un utente ottiene la policy **senza alcun passo manuale**: solo tramite `sertor install rag` (per
`concierge`, `wiki-curator`) e `sertor-flow install` (per gli altri tre). La documentazione utente
(`docs/install-copilot.md` + tabella capability di `packages/sertor/docs/install.md`) elenca il default di
ciascuno dei cinque agenti e **come modificarlo** — aggiornata nello stesso step.

**Independent Test**: dopo un'installazione pulita su Copilot CLI, i cinque agenti hanno il modello della
policy senza intervento manuale; la doc utente descrive default per-agente e modo di cambiarlo.

**Acceptance**:
1. **Given** un ospite Copilot CLI pulito, **When** si eseguono `sertor install rag` e `sertor-flow
   install`, **Then** i cinque agenti hanno il modello della policy senza passi post-install manuali.
2. **Given** la documentazione utente, **When** la feature è completa, **Then** `docs/install-copilot.md` e
   la tabella capability di `packages/sertor/docs/install.md` elencano il default per ciascun agente e come
   modificarlo.
3. **Given** la regola standing «una modifica al setup non è done finché la doc utente non è aggiornata»,
   **When** la feature è dichiarata completa, **Then** la doc è aggiornata nello stesso step (non un debito
   rinviato).

### User Story 6 — Idempotenza e coerenza di lifecycle (P1, Must)
Install e upgrade ripetuti, a parità di versione del profilo e di stato dell'host, producono un frontmatter
renderizzato byte-identico. La policy è risolta e applicata identicamente al primo install e all'upgrade;
la disinstallazione non è toccata da alcuna semantica di modello (sola rimozione).

**Independent Test**: rieseguire il deposito per Copilot CLI a parità di versione profilo produce lo stesso
contenuto; l'upgrade applica la policy come il primo install; uninstall rimuove senza logica di modello.

**Acceptance**:
1. **Given** un profilo a versione fissa e host invariato, **When** si eseguono install/upgrade ripetuti,
   **Then** il frontmatter reso è byte-identico tra le esecuzioni.
2. **Given** un host che passa da install a upgrade, **When** gli agenti in ambito sono ri-renderizzati,
   **Then** la policy è risolta e applicata identicamente (stesso model-ID atteso).
3. **Given** l'uninstall, **When** gli agenti in ambito sono rimossi, **Then** la rimozione non dipende da
   alcuna semantica di modello.

### User Story 7 — Default modificabile e override utente al sicuro (P2, Should)
Un utente che preferisce un altro modello per un agente lo cambia con il picker `/subagents` di Copilot (o
editando il frontmatter): il primo persiste in `~/.copilot/settings.json` e **vince a runtime** sul default
del `.agent.md` → l'override naturale è al sicuro per costruzione. La documentazione comunica che il modello
assegnato è un **default modificabile**, non un vincolo imposto.

**Independent Test**: la documentazione descrive il modello per-agente come default modificabile e i due
modi per cambiarlo; si dichiara che un override via `/subagents` (file utente separato) prevale a runtime,
mentre un edit manuale diretto del frontmatter è soggetto al normale upgrade (documentato).

**Acceptance**:
1. **Given** la doc utente, **When** la feature è completa, **Then** dichiara che il modello per-agente è un
   default modificabile (via `/subagents` o edit del frontmatter), non una regola rigida.
2. **Given** un override utente fatto con `/subagents`, **When** l'utente esegue un successivo upgrade di
   Sertor, **Then** l'override (in `~/.copilot/settings.json`) non è toccato da Sertor e continua a vincere
   a runtime.
3. **Given** un edit manuale diretto del `model:` nel `.agent.md`, **When** avviene un upgrade, **Then** la
   doc chiarisce che tale edit è soggetto al normale ri-render dell'owned_file (non protetto ad hoc).

### User Story 8 — Confine speckit.* e disponibilità tenant dichiarati onestamente (P2, Should)
Un utente comprende, dalla documentazione e dal comportamento, che gli agenti `speckit.*` (prompt-file
vendorati da spec-kit) **non** ricevono un default di modello da questa feature — è un limite dichiarato e
tracciato come follow-up, non un buco silenzioso. Analogamente, poiché l'installer è offline e non
interroga il tenant Copilot, l'eventuale indisponibilità di un modello nel piano dell'utente è resa
esplicita a livello documentale + demandata al comportamento runtime di Copilot, non finta come un
controllo install-time.

**Independent Test**: durante il deposito per Copilot CLI, i prompt-file `speckit.*` non ricevono un
`model:`; la documentazione dichiara il confine e il limite «no probe tenant a install-time».

**Acceptance**:
1. **Given** i prompt-file `speckit.*` vendorati per Copilot CLI, **When** vengono depositati, **Then** la
   feature non tenta di assegnare loro un modello (fuori ambito dichiarato).
2. **Given** la documentazione, **When** la feature è completa, **Then** dichiara che gli `speckit.*` sono
   fuori ambito e che l'assegnazione di un loro modello è tracciata come follow-up di backlog.
3. **Given** un model-ID della policy non disponibile nel tenant dell'utente, **When** l'utente esegue
   l'agente, **Then** il segnale di indisponibilità viene dal runtime di Copilot; la doc avverte del rischio
   (nessun probe install-time promesso).

## Edge Cases
- **Alias Claude nel frontmatter canonico** (es. `model: sonnet` di `concierge`) — sul render Copilot va
  **sostituito** dal model-ID della policy, mai eco-emesso verbatim (invalido su Copilot). È il gap del
  renderer attuale che eco-emette verbatim quando abilitato (US1, US4).
- **Profilo privo della voce di un agente in ambito** — fail-loud install-time nominando l'agente (US2);
  **non** un default silenzioso né un valore indefinito.
- **Model-ID datato/deprecato o non abilitato nel tenant** — l'install «riesce» comunque (offline, nessun
  probe); l'indisponibilità emerge a runtime + è avvisata in doc (US8, R-2). Se il profilo definisce un
  fallback, la sua granularità (per-agente vs globale) è dettaglio di plan.
- **Host che installa sia `sertor` sia `sertor-flow`** — deve ricevere una policy coerente dalla stessa
  fonte/versione (US3, R-4); fonti divergenti = incoerenza da evitare.
- **Edit manuale diretto del `model:` nel `.agent.md`** — soggetto al normale ri-render dell'owned_file a
  upgrade (documentato); l'override *via `/subagents`* (file utente separato) è invece al sicuro (US7).
- **Drift bundlato↔dogfood del profilo versionato** — un profilo non allineato dal meccanismo di sync
  esistente rischia di divergere tra asset bundlato e copia dogfood (R-5); da coprire come per gli altri
  asset.

## Requirements *(mandatory)*

### Requisiti funzionali

**Gruppo A — Applicazione della policy ai 5 custom-agent Copilot (Must)**
- **FR-001 (default esplicito per-agente).** Quando l'assistente target è Copilot CLI, il sistema assegna
  un modello esplicito e non-vuoto a ciascuno dei cinque custom-agent in ambito, via il campo `model:` del
  frontmatter `.agent.md` depositato. *(REQ-001; CS-1)*
- **FR-002 (sostituzione dell'alias ereditato).** Rendendo il frontmatter Copilot di un agente in ambito,
  il sistema emette il model-ID prescritto dalla policy per quell'agente, **al posto** di qualunque alias
  Claude ereditato dal frontmatter dell'asset canonico. *(REQ-004, REQ-016; CS-1/CS-2)*
- **FR-003 (deposito non distruttivo).** Depositando un agente in ambito non ancora presente sull'host, il
  sistema scrive il frontmatter con il modello di policy, fondendolo in modo non distruttivo col resto del
  frontmatter (identità/descrizione/tools intatti). *(REQ-005; CS-1)*
- **FR-004 (coerenza cross-pacchetto).** Il sistema applica lo stesso profilo di policy in modo identico sia
  che l'agente sia depositato da `sertor` (`concierge`, `wiki-curator`) sia da `sertor-flow`
  (`requirements-analyst`, `configuration-manager`, `requirements`). *(REQ-011; CS-3)*

**Gruppo B — Fonte unica versionata (Must)**
- **FR-005 (profilo unico versionato).** Ogni model-ID assegnato dalla policy proviene da un **singolo**
  profilo di modello versionato, condiviso da ogni pacchetto che deposita un agente in ambito, non da valori
  incorporati nei singoli asset o sparsi per-agente nel codice installer. *(REQ-003; CS-3, NFR-001)*
- **FR-006 (leggibile da entrambi i pacchetti, senza dipendenza vietata).** Il profilo è leggibile
  identicamente da `sertor` e `sertor-flow` senza introdurre la dipendenza `sertor-flow`→`sertor-core`.
  *(REQ-011; CS-3)*
- **FR-007 (tracciabilità di versione).** Un cambiamento del profilo (bump di un model-ID) è distinguibile,
  tramite un marcatore di versione del profilo, da un cambiamento del corpo/persona dell'agente. *(NFR-004)*

**Gruppo C — Fail-loud su profilo incompleto (Must)**
- **FR-008 (fail-loud nominante).** Se il profilo non ha una voce per uno dei cinque agenti in ambito, il
  sistema fa **fallire l'installazione** con un errore che **nomina** l'agente mancante, invece di
  depositarlo senza modello o con valore indefinito. *(REQ-008; CS-5)*
- **FR-009 (nessun deposito parziale).** Al fallire per profilo incompleto, nessun agente in ambito viene
  depositato con `model:` assente o indefinito. *(REQ-008; CS-5)*

**Gruppo D — Lifecycle, idempotenza, isolamento Claude (Must)**
- **FR-010 (idempotenza).** Il frontmatter reso per un agente in ambito è byte-identico tra install/upgrade
  ripetuti, a parità di stato host e versione del profilo. *(REQ-007; CS-4)*
- **FR-011 (lifecycle install/upgrade).** La policy è risolta e applicata identicamente al primo install e
  all'upgrade per ogni agente in ambito; l'uninstall non è influenzato da semantiche di modello (sola
  rimozione). *(REQ-012)*
- **FR-012 (zero impatto Claude).** Applicare la policy Copilot non ha alcun effetto osservabile sul path
  Claude: i frontmatter Claude (incluso il `model: sonnet` di `concierge`) restano bit-per-bit invariati.
  *(REQ-002; CS-7, NFR-006)*
- **FR-013 (non-regressione FEAT-011/049).** Su ogni render di custom-agent Copilot il sistema continua a
  omettere qualunque alias Claude (`haiku`/`sonnet`/`opus`) ereditato dall'asset, indipendentemente dal
  `model:` di policy emesso; le guardie esistenti che imponevano «`model:` sempre assente» sono riformulate,
  non rimosse. *(REQ-016; CS-2)*

**Gruppo E — DoD distribuzione + documentazione (Must)**
- **FR-014 (distribuzione via installer).** La policy raggiunge un host esclusivamente tramite `sertor
  install rag` (per `concierge`, `wiki-curator`) e `sertor-flow install` (per gli altri tre), senza alcun
  passo manuale post-install. *(REQ-014; CS-6)*
- **FR-015 (documentazione utente).** La documentazione utente (`docs/install-copilot.md` e la tabella
  capability di `packages/sertor/docs/install.md`) descrive il modello di default assegnato a ciascun agente
  in ambito e come l'utente può cambiarlo — aggiornata nello stesso step della feature. *(REQ-015; CS-6)*

**Gruppo F — Non rigidità e confini dichiarati (Should)**
- **FR-016 (default modificabile documentato).** La documentazione dichiara che il modello assegnato
  per-agente è un default modificabile (via il comando `/subagents` di Copilot o editando il frontmatter),
  non un vincolo imposto; un override via `/subagents` (in `~/.copilot/settings.json`, file separato) vince
  a runtime ed è al sicuro dagli upgrade. *(REQ-006, REQ-010)*
- **FR-017 (confine speckit.* dichiarato).** Rendendo i prompt-file `speckit.*` vendorati da `specify init`
  per Copilot CLI, il sistema non tenta di assegnare un modello; il confine è dichiarato in doc e tracciato
  come follow-up di backlog, non sepolto. *(REQ-013)*
- **FR-018 (disponibilità tenant onesta).** L'eventuale indisponibilità di un model-ID nel tenant/ambiente
  dell'utente è resa esplicita a livello documentale e demandata al comportamento runtime di Copilot; il
  sistema non promette né esegue un probe install-time del tenant. *(REQ-009; NFR-007)*

### Requisiti non funzionali
- **RNF-1 (Principio XI — nessun runtime di core):** risolvere e applicare la policy è esclusivamente
  responsabilità dei pacchetti di distribuzione; non richiede di importare o invocare `sertor_core`, non
  invoca alcun LLM. *(NFR-005)*
- **RNF-2 (manutenibilità):** aggiornare un model-ID datato richiede la modifica di **un solo** artefatto
  versionato. *(NFR-001)*
- **RNF-3 (determinismo):** stesso agente + stessa versione del profilo → stesso model-ID, indipendentemente
  dall'ambiente di installazione. *(NFR-002)*
- **RNF-4 (trasparenza):** il modello risolto per ciascun agente è visibile nel file depositato (mai un
  default nascosto). *(NFR-003)*
- **RNF-5 (isolamento Claude):** applicare la policy Copilot non ha effetti collaterali osservabili sul path
  Claude (nessuno stato condiviso mutato). *(NFR-006)*
- **RNF-6 (degradazione offline):** l'assenza di connettività/probe non blocca il completamento
  dell'installazione: il default del profilo è scritto comunque. *(NFR-007)*
- **RNF-7 (verificabilità offline):** l'emissione del model-ID corretto, il non-leak dell'alias Claude, il
  fail-loud su profilo incompleto e l'idempotenza sono verificabili senza rete e senza un tenant Copilot
  reale (come le guardie esistenti). *(NFR-008)*
- **RNF-8 (`sertor-core` invariato):** nessuna modifica a porte/adapter/composition/engine/comandi del core.

### Key Entities
- **Profilo di modello versionato (nuovo)** — la fonte unica agente→model-ID, con marcatore di versione,
  collocata nel kit condiviso `sertor-install-kit` così da essere leggibile da `sertor` e `sertor-flow`
  senza dipendenza da `sertor-core`. Contiene i default iniziali (concierge/configuration-manager →
  `claude-haiku-4.5`; requirements-analyst/requirements/wiki-curator → `claude-sonnet-4.6`).
- **I 5 custom-agent Copilot in ambito** — `concierge`, `wiki-curator` (deposito `sertor`);
  `requirements-analyst`, `configuration-manager`, `requirements` (deposito `sertor-flow`), resi come
  `.agent.md` con `model:` prescritto dalla policy.
- **Renderer del frontmatter Copilot** — il meccanismo che emette il `model:` dalla policy (non eco verbatim
  dell'alias canonico) e continua a omettere l'alias Claude ereditato. Il gap «sostituzione dal profilo» è
  materia di design.
- **Guardie di frontmatter Copilot (esistenti, da riconciliare)** — `test_assets_copilot_guard.py`,
  `test_schema_copilot_frontmatter.py`: riformulate da «`model:` sempre assente» a «alias Claude sempre
  assente **e** `model:` di policy nativo ammesso e atteso»; restano verdi.
- **Documentazione utente** — `docs/install-copilot.md` + tabella capability di
  `packages/sertor/docs/install.md`: default per-agente e modo di modificarlo.
- **Prompt-file `speckit.*` (fuori ambito)** — vendorati da spec-kit; nessuna assegnazione di modello;
  confine dichiarato e tracciato.

## Success Criteria *(mandatory)*
- **CS-1 (default esplicito):** i 5 agenti installati su Copilot CLI hanno tutti un `model:` esplicito e
  non-vuoto nel frontmatter (0 agenti a selezione implicita) — verificabile offline sui file resi.
  *(FR-001/002/003, US1)*
- **CS-2 (no leak alias Claude):** 0 occorrenze di un alias-modello Claude (`haiku`/`sonnet`/`opus`) nel
  frontmatter Copilot risultante; nessuna regressione della garanzia FEAT-011/049. *(FR-002/013, US4)*
- **CS-3 (fonte unica versionata):** ogni model-ID usato dalla policy compare in un solo posto versionato,
  leggibile da `sertor` e `sertor-flow`; 0 ID hardcoded/sparsi per-agente nel codice installer.
  *(FR-004/005/006, US3)*
- **CS-4 (idempotenza):** install/upgrade ripetuti a parità di versione profilo producono contenuto
  renderizzato byte-identico. *(FR-010, US6)*
- **CS-5 (fail-loud su profilo incompleto):** un profilo privo della voce per uno dei 5 agenti fa fallire
  l'installazione nominando l'agente mancante; 0 installazioni silenziosamente incomplete — verificabile
  offline con un profilo sintetico incompleto. *(FR-008/009, US2)*
- **CS-6 (DoD — distribuzione + doc):** la policy raggiunge un ospite solo via `sertor install rag` e
  `sertor-flow install` (nessun passo manuale); la doc utente elenca il default per ciascun agente e il modo
  di modificarlo, aggiornata nello stesso step. *(FR-014/015, US5)*
- **CS-7 (zero impatto su Claude):** 0 regressioni misurabili sul path Claude (il `model: sonnet` di
  `concierge` e gli altri frontmatter Claude restano bit-per-bit invariati). *(FR-012, US4)*

## Assumptions
- **A-001 — Meccanismo A confermato (doc ufficiale):** il modello di un custom-agent Copilot CLI si imposta
  col campo `model:` nel frontmatter `.agent.md`; il meccanismo B (settings machine-global) è scartato.
- **A-002 — Override utente al sicuro per costruzione (DA risolta):** un cambio via `/subagents` persiste in
  `~/.copilot/settings.json` (file separato) e vince a runtime; Sertor scrive solo il default nel
  frontmatter → REQ-006 si riduce a semantica owned_file standard + nota documentale.
- **A-003 — Nessun probe tenant a install-time (DA risolta):** l'installer è offline e non interroga l'API
  Copilot → il «fail-loud disponibilità» è documentale + comportamento runtime, non un controllo
  install-time. Il fail-loud install-time REALE è quello sul profilo incompleto (FR-008).
- **A-004 — Profilo nel kit condiviso (DA risolta):** vive in `sertor-install-kit`, già dipendenza comune di
  `sertor` e `sertor-flow`, zero legame con `sertor-core`. *(FR-005/006)*
- **A-005 — Model-ID datati:** i valori della policy invecchiano; vivono nel profilo versionato con
  marcatore di versione (FR-007), non hardcoded — la tabella in questa spec è il *default iniziale*, non un
  valore fisso.
- **A-006 — Verificabilità offline:** emissione model-ID corretto, non-leak alias Claude, fail-loud su
  profilo incompleto e idempotenza sono verificabili come le guardie esistenti
  (`test_assets_copilot_guard.py`/`test_schema_copilot_frontmatter.py`), senza rete/tenant reale. *(RNF-7)*

### Fuori ambito (dichiarato)
- **Modifiche a `sertor_core`** o a qualunque comando/vehicle/porta/adapter/engine — la feature è
  distribuzione/installer pura (Principio XI).
- **Assegnazione di modello ai prompt-file `speckit.*`** — vendorati da spec-kit; la doc ufficiale non
  conferma il supporto di `model:` sui prompt-file → richiede una spike separata. **Tracciato come
  follow-up di backlog** (nuova voce `FEAT-NNN`, epica `sertor-cli`), non sepolto.
- **Claude:** nessun impatto; il `model:` Claude resta gestito come oggi.
- **Codex** come assistente ospite: fuori ambito.
- **Probe install-time della disponibilità modelli del tenant** come capacità garantita: escluso per
  costruzione (installer offline); resta il segnale runtime di Copilot + avviso documentale.
- **Nuovi provider di modello o logica di instradamento runtime:** fuori ambito — qui si distribuisce solo
  un *default*, non un motore di scelta modello.
- **Il *come* di dettaglio** (forma esatta del profilo, punto di innesto della sostituzione nel renderer,
  collocazione/forma dei test riconciliati): fase di **design/plan**.

> **Tracciamento dello scope.** L'unico rinvio reale — assegnazione di modello agli `speckit.*` — va
> **promosso a casa durevole** al plan/decomposizione: nuova voce `FEAT-NNN` nel backlog dell'epica
> `sertor-cli` (previa spike di verifica del supporto `model:` sui prompt-file). Nessun rinvio reale resta
> sepolto in `specs/`. La feature è *done* quando: i 5 agenti Copilot ricevono un `model:` di policy via
> installer senza passi manuali; il fail-loud su profilo incompleto nomina l'agente mancante; la fonte
> unica versionata è condivisa dai due pacchetti; nessun leak di alias Claude e path Claude invariato;
> idempotenza/lifecycle rispettati; la doc utente è aggiornata nello stesso step.

### Forche di design — per `/speckit-plan` (sono *come*, non scope)
- **DA-D-1 — Forma e collocazione del profilo versionato nel kit:** struttura dati (mappa costante,
  file dati versionato, funzione risolutrice) e API di lettura esposta a `sertor`/`sertor-flow`. La
  direzione (fonte unica in `sertor-install-kit`, con marcatore di versione) è fissata; la forma è plan.
  *(FR-005/006/007)*
- **DA-D-2 — Punto di innesto della sostituzione nel renderer Copilot:** estendere `render_custom_agent`
  (oggi `include_model` = eco verbatim) con una sostituzione dal profilo, vs un passo di post-processing sul
  frontmatter reso. Entrambe valide; scelta di plan. *(FR-001/002)*
- **DA-D-3 — Riconciliazione delle guardie esistenti:** riformulare
  `test_custom_agent_omits_model_field`/`test_custom_agent_has_no_model` (e gemelle anti-pattern) da
  «`model:` sempre assente» a «alias Claude sempre assente **e** `model:` di policy nativo ammesso» — forma
  esatta degli assert e collocazione. *(FR-013)*
- **DA-D-4 — Meccanismo di fail-loud su profilo incompleto:** dove e come si materializza l'errore
  (validazione al build del piano vs al render del singolo agente) e la forma del messaggio nominante.
  *(FR-008/009)*
- **DA-D-5 — Sync bundlato↔dogfood del profilo:** se e come il profilo versionato entra nel meccanismo di
  sync/guardia anti-drift esistente per evitare divergenza asset↔dogfood (R-5). *(Edge Case)*
- **DA-D-6 — Fallback per-agente (minore):** se il profilo definisce un fallback di classe costo/qualità
  comparabile, granularità per-agente vs globale. Non blocca il primo taglio. *(FR-018)*
