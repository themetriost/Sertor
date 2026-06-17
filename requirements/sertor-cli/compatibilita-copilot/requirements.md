# Requisiti — Hardening compatibilità GitHub Copilot dell'installer
<!-- Deriva da: FEAT-007/FEAT-009 (correzione) -->

## 1. Contesto e problema (perché)

Un audit di dogfooding su un ospite reale (Copilot CLI 1.0.63) condotto dopo la consegna di
FEAT-007 (PR #64, 2026-06-15) e FEAT-009 (PR #65, 2026-06-15) ha dimostrato che la **"parità
funzionale piena" Copilot dichiarata è falsa su più superfici**. Le superfici che l'installer
deposita per `--assistant copilot` (VS Code) e `--assistant copilot-cli` non sono tutte conformi
allo schema Copilot documentato.

Le difformità rilevate coprono cinque aree distinte:

1. **Hook JSON** (`packages/sertor/src/sertor_installer/assets/copilot/hooks/wiki.hooks.json` e
   `rag-usage.hooks.json`): i file sono in **formato Claude Code** — manca il campo `"version":1`
   obbligatorio, la struttura dell'oggetto è annidata in modo incompatibile, sono presenti campi
   (`"shell"`, `"statusMessage"`, `"timeout"`) non riconosciuti dallo schema Copilot. Senza
   `"version":1` il file viene scartato dall'interprete Copilot e **nessun hook viene eseguito**.

2. **Contratto di output degli script `.ps1`** (`wiki-pending-check.ps1`): emette
   `{"systemMessage":...}` (campo Claude-only) per gli eventi Stop e SessionEnd. Copilot richiede
   output diverso per evento — in particolare l'evento `agentStop` (Stop) si aspetta
   `{"decision":"block|allow","reason":"..."}`, e l'evento `preToolUse` è **fail-closed** su
   Copilot (un hook malformato o che produce errore **nega la tool call**).

3. **Output SessionStart**: il comando hook emette stringhe plain non-JSON. Copilot tenta
   `JSON.parse` sull'output e, fallendo, non inietta alcun contesto nel prompt.

4. **Veicolo comandi su Copilot CLI**: i comandi `/wiki`, `wiki-author` e `requirements` sono
   depositati come prompt-file (`.github/prompts/*.prompt.md`). I **prompt file non sono
   supportati da Copilot CLI** (solo VS Code/Visual Studio/JetBrains); su `copilot-cli` quei
   comandi semplicemente non esistono. Inoltre, anche su VS Code il campo frontmatter documentato
   per i prompt-file è `agent:` (es. `agent: 'agent'`), non `mode:` (il campo attualmente
   generato da `render_prompt_file` in
   `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py`).

5. **Frontmatter custom-agent**: il campo `model:` nei file `.agent.md` porta nomi Claude
   (es. `haiku`) non validi per Copilot; il campo non dovrebbe essere presente o dovrebbe essere
   omesso.

Questi problemi invalidano silenziosamente capacità che l'utente ritiene installate e funzionanti,
violando il criterio di successo CS-1 ("parità funzionale") e CS-6 ("onestà sui gap") dei
requisiti FEAT-007.

> Ancoraggio al codice (ground truth dell'audit):
> - Hooks JSON: `packages/sertor/src/sertor_installer/assets/copilot/hooks/wiki.hooks.json`,
>   `rag-usage.hooks.json`
> - Script output: `packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-pending-check.ps1`
> - Renderer frontmatter: `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py:39-47`
>   (`render_prompt_file`), `surfaces.py:50-64` (`render_custom_agent`)
> - Targeting: `packages/sertor-install-kit/src/sertor_install_kit/assistant.py`
> - Test anti-drift: `packages/sertor/tests/test_assets_copilot_guard.py`,
>   `packages/sertor/tests/test_surface_parity.py`

### Principio guida (VINCOLANTE) — supporto nativo, niente hack di compatibilità

Decisione utente (2026-06-17): **ogni superficie va resa nel formato/contratto NATIVO del tool
target** (Claude, Copilot VS Code, Copilot CLI). **Vietati gli hack di compatibilità**: niente JSON
con campi-di-entrambi che sfruttano il fatto che ciascun tool ignora i campi sconosciuti (es.
`systemMessage` + `additionalContext` insieme); niente formato Claude "tollerato" su Copilot; niente
veicolo sbagliato (prompt-file su Copilot CLI). Se due tool divergono davvero, **si supportano
entrambi appieno**, anche con asset/wiring/script **per-assistente** (parametrizzati o distinti) — non
è un hack, è supporto proprio. Il **riuso** riguarda il **CONTENUTO** (corpo istruzionale, fonte
unica byte-for-byte); il **CONTENITORE/contratto** va **tradotto nativamente**, non falsificato.

**Conseguenza sull'invariante FEAT-007.** L'FR-014 di FEAT-007 ("script `.ps1` riusati *identici*") è
**rilassato** a: *corpo dello script condiviso, ma invocazione e contratto di output **nativi** per
assistente* (es. parametro `-Assistant`). **Nodo di design per la fase `plan`:** verificare se il seam
`AssistantProfile`/`Surface` produce davvero artefatti nativi per ogni superficie; se non lo fa,
**rivederlo** (revisione architetturale autorizzata dall'utente), non applicare cerotti.

## 2. Obiettivi e criteri di successo

- **Obiettivo:** le superfici depositate dall'installer per i target `copilot` e `copilot-cli`
  sono conformi allo schema Copilot documentato e funzionano su un ospite reale; dove la parità
  completa non è raggiungibile, il gap è dichiarato esplicitamente all'utente.
- **CS-1 (Hook conformi):** dopo l'installazione con target `copilot` o `copilot-cli`, il file
  hook risultante è valido secondo lo schema Copilot (`"version":1`, struttura piatta, campi
  corretti); il file viene caricato dall'interprete Copilot e gli hook si eseguono.
- **CS-2 (Output script conformi):** per ogni evento hook installato, lo script `.ps1`
  associato emette l'output nella forma attesa da Copilot per quell'evento; in nessun caso un
  hook non-bloccante genera un comportamento bloccante involontario.
- **CS-3 (SessionStart inietta contesto):** l'hook SessionStart su target Copilot produce
  output parsabile da Copilot come contesto aggiuntivo (zero plain-string senza wrapper).
- **CS-4 (Comandi raggiungibili su Copilot CLI):** per il target `copilot-cli`, i comandi
  equivalenti a `/wiki`, `wiki-author` e `requirements` sono installati in una forma invocabile
  dalla CLI (non solo da VS Code).
- **CS-5 (Frontmatter agent senza campi Claude-only):** nessun file `.agent.md` generato per
  target Copilot contiene il campo `model:` con un valore Claude; il frontmatter è conforme alla
  reference Copilot.
- **CS-6 (Frontmatter prompt-file corretto):** il campo frontmatter dei `.prompt.md` generati
  usa la chiave documentata per Copilot (non `mode:` Claude-specific).
- **CS-7 (Validazione a test):** esiste una suite di test che verifica la **validità di schema**
  degli asset generati per i target Copilot (non solo la loro presenza); i difetti descritti
  nell'audit avrebbero fatto fallire questi test se fossero esistiti.
- **CS-8 (Correzione del claim):** la documentazione superfici di FEAT-007/009 non dichiara più
  "parità piena" per le aree in cui la parità non è verificata empiricamente.

## 3. Stakeholder e attori

- **Owner/maintainer:** installa le capacità Sertor su un ospite Copilot; destinatario diretto
  delle correzioni.
- **Team che usa Copilot:** riceve superfici funzionanti anziché silenziosamente broken.
- **Pacchetto `sertor` + `sertor-flow` + `sertor-install-kit`:** pacchetti da correggere.
- **Suite di test** (`packages/sertor/tests/`): primo rilevatore dei regressioni future.
- **Epica `sertor-core`:** invariata — il problema è solo nella distribuzione, non nel core.

## 4. Ambito

### In ambito

- **Correzione hook JSON** (superfici `wiki.hooks.json`, `rag-usage.hooks.json`): aggiornamento
  al formato schema Copilot (`"version":1`, struttura piatta, rimozione campi non supportati).
- **Correzione contratto output degli script `.ps1`** per evento: adattamento dell'output di
  `wiki-pending-check.ps1` (e di eventuali script hook di `sertor-flow`) al contratto per-evento
  Copilot, con cura particolare per `preToolUse` (fail-closed) e per la natura non-bloccante
  dell'hook wiki.
- **Correzione SessionStart**: l'output del comando hook SessionStart su target Copilot deve
  essere avvolto nella forma che Copilot riconosce come contesto aggiuntivo.
- **Veicolo comandi per Copilot CLI**: per il target `copilot-cli`, i comandi wiki/governance
  devono essere disponibili in una forma che funziona sulla CLI (es. custom-agent), non solo in
  prompt-file VS Code-only.
- **Correzione frontmatter `.prompt.md`** (campo `mode:` → chiave documentata Copilot).
- **Correzione frontmatter `.agent.md`** (rimozione o omissione del campo `model:` con valori
  Claude-only).
- **Suite di test di validità-schema-Copilot**: test che verificano che i file hook generati
  per i target Copilot rispettino lo schema (`"version":1`, campi richiesti, assenza di campi
  vietati), e che i frontmatter di prompt-file e custom-agent siano conformi.
- **Correzione del claim documentale** "parità funzionale piena" nelle superfici di
  FEAT-007/009 che risultano ancora parziali dopo questa feature.
- **`sertor-flow`**: le stesse correzioni si applicano alle superfici governance di `sertor-flow`
  (agenti `requirements-analyst`, `configuration-manager`, skill `requirements`) che condividono
  gli stessi pattern.

### Fuori ambito

- **Verifica empirica runtime** (smoke-test su host reale): è validazione operativa, non un
  requisito di prodotto; la feature la cita come necessaria ma non la specifica.
- **Nuove superfici o capacità** non presenti in FEAT-007/009 (espansione del perimetro di
  parità: fuori scope).
- **Provider/store backend** (epica `sertor-core`): invariato.
- **Funzionamento interno di spec-kit**: gestito upstream.
- **Codex** (was Could in FEAT-007): non nel perimetro.
- **Copilot come provider LLM** (DA-6 dell'epica): asse diverso.
- **Pubblicazione PyPI**.

## 5. Requisiti funzionali (EARS)

### Gruppo A — Hook JSON: conformità schema Copilot

- **REQ-001 (Ubiquitous):** *The system shall produce hook JSON files for the `copilot` and
  `copilot-cli` targets with a top-level `"version": 1` field, as required by the Copilot hook
  schema.*

- **REQ-002 (Ubiquitous):** *The system shall produce hook JSON files for the `copilot` and
  `copilot-cli` targets with the hook list nested under the event name key directly inside a
  top-level `"hooks"` object, with each entry using the flat Copilot entry shape (fields
  `type`, `command`, `timeoutSec`, and optionally `matcher`), without Claude-specific fields
  (`shell`, `statusMessage`).*

- **REQ-003 (Unwanted):** *If the hook JSON file for a `copilot` or `copilot-cli` target
  contains a field that is not part of the Copilot hook schema (e.g. `shell`, `statusMessage`),
  then the system shall not include that field in the generated artifact.*

- **REQ-004 (Ubiquitous):** *The system shall use the documented Copilot field name `timeoutSec`
  (not `timeout`) for the hook entry timeout value in artifacts generated for the `copilot` and
  `copilot-cli` targets.*

- **REQ-005 (Ubiquitous):** *The system shall support both PascalCase event names (e.g.
  `SessionStart`, `PreToolUse`) and their documented aliases when producing hook files for
  Copilot targets, consistent with the Copilot CLI compatibility contract.*

### Gruppo B — Contratto di output degli script hook per evento

- **REQ-006 (Event-driven):** *When the session-start surface is installed for a Copilot target,
  the system shall use the NATIVE Copilot mechanism for that target to inject session context —
  on Copilot CLI a `type: "prompt"` session-start hook entry; on Copilot VS Code its native
  session-context mechanism — and shall NOT emit plain non-JSON strings nor rely on a tolerated
  extra field.*

  > DECISO (Q1 = b, 2026-06-17): meccanismo nativo per target (`type:"prompt"` su CLI), wiring che
  > può divergere tra `copilot` e `copilot-cli`. Il meccanismo nativo esatto su VS Code va fissato in
  > fase di design + verifica empirica (vedi nodo seam).

- **REQ-007 (Event-driven):** *When a hook script is invoked for the Copilot `agentStop` event
  (equivalent to Claude `Stop`), the system shall produce non-blocking output in the form
  `{"decision": "allow", "reason": "<message>"}` rather than a `systemMessage` field that
  Copilot does not recognise.*

  > DECISO (Q3 = b, 2026-06-17): non-bloccante (`decision:"allow"` + `reason`) — è la forma nativa
  > di un reminder che non deve forzare un turno.

- **REQ-008 (Unwanted):** *If a hook script is invoked for the Copilot `preToolUse` event and
  detects no violation, then the system shall exit with code 0 and produce no output or only
  Copilot-conformant output, so that the fail-closed behaviour of `preToolUse` does not block
  tool calls.*

- **REQ-009 (Unwanted):** *If a hook script emits output for the `sessionEnd` event on a
  Copilot target, then the system shall not rely on that output being consumed by Copilot (the
  event produces no consumed output on Copilot); any terminal-facing message shall be written
  to stderr.*

- **REQ-010 (Unwanted):** *If the hook script for a Copilot target produces an output field
  that belongs exclusively to the Claude Code hook schema (e.g. `systemMessage` as a
  stand-alone top-level field), then the system shall not use it as the sole communication
  channel for that event.*

### Gruppo C — Output nativo per assistente degli script `.ps1` (no dual-compat)

- **REQ-011 (Ubiquitous):** *The system shall share the BODY of the hook scripts (`.ps1`) across
  Claude and Copilot targets (single source, no divergent content copy), but each script shall
  emit the output contract NATIVE to the invoking assistant, selected via an explicit invocation
  parameter (e.g. `-Assistant claude|copilot`) passed by the per-assistant wiring. The script
  shall NOT emit a single JSON carrying both Claude and Copilot fields (no dual-field hack).*

  > DECISO (Q4 = b, 2026-06-17): un solo script, output nativo selezionato per parametro
  > d'invocazione (il wiring hook è già per-assistente). FR-014 di FEAT-007 rilassato a "corpo
  > condiviso, output nativo per assistente".

- **REQ-012 (Unwanted):** *If a single parametrised script cannot cleanly emit the native contract
  for a given assistant, then the system shall use a per-assistant script variant rather than emit
  a non-native or dual-field output.*

### Gruppo D — Veicolo comandi per Copilot CLI

- **REQ-013 (Event-driven):** *When installing the `wiki` capability with the `copilot-cli`
  target, the system shall install wiki command surfaces (equivalent to `/wiki`, `wiki-author`)
  in a form that is invokable from Copilot CLI (not only from VS Code), such as custom-agent
  files.*

  > DECISO (Q2 = c, 2026-06-17): piano per-target — VS Code prompt-file nativo; Copilot CLI
  > custom-agent nativo (i prompt-file non esistono sulla CLI).

- **REQ-014 (Event-driven):** *When installing governance (`requirements` skill) with the
  `copilot-cli` target via `sertor-flow`, the system shall install the `requirements` skill
  surface in a form that is invokable from Copilot CLI.*

- **REQ-015 (Optional):** *Where the `copilot` (VS Code) target is selected, the system shall
  continue to provide prompt-files (`*.prompt.md`) for command surfaces, as these are
  supported in VS Code and Visual Studio.*

### Gruppo E — Frontmatter prompt-file e custom-agent

- **REQ-016 (Ubiquitous):** *The system shall use the documented Copilot frontmatter field for
  prompt-file mode (`agent:`) when generating `.prompt.md` files for Copilot targets, not a
  Claude-specific field name.*

  > Riferimento codice: `sertor_install_kit/surfaces.py:43` — il valore corrente è `mode: agent`.

- **REQ-017 (Unwanted):** *If the source Claude agent asset contains a `model:` field with a
  value that is not valid for Copilot (e.g. `haiku`), then the system shall omit the `model:`
  field from the generated Copilot custom-agent frontmatter.*

  > DECISO (Q6 = a, 2026-06-17): il campo `model:` con valore Claude viene omesso (default Copilot).

- **REQ-018 (Ubiquitous):** *The system shall preserve the `name:`, `description:`, and
  `tools:` fields when translating a Claude agent asset into a Copilot custom-agent, as these
  are part of the documented Copilot custom-agent frontmatter.*

- **REQ-019 (Ubiquitous):** *The system shall keep the instructional body of rendered
  prompt-files and custom-agents byte-for-byte identical to the canonical Claude source, as
  required by the anti-drift invariant (REQ-021 of FEAT-007).*

### Gruppo F — Conformità MCP (verifica)

- **REQ-020 (Ubiquitous):** *The system shall document the empirical evidence (or absence
  thereof) for whether Copilot CLI reads `.mcp.json` at the repository root with the
  `mcpServers` root key, and shall adjust the MCP configuration surface for `copilot-cli` if
  empirical evidence contradicts the current assumption.*

  > DECISO (Q5: incluso, 2026-06-17): la verifica empirica del target MCP nativo della CLI
  > (`.mcp.json` vs `~/.copilot/mcp-config.json`) è nello scope e va documentata; correggere la
  > surface se la prova empirica smentisce l'assunto di PR #66.

### Gruppo G — Test di validità-schema-Copilot

- **REQ-021 (Ubiquitous):** *The system shall include automated tests that verify the
  structural validity of every hook JSON file generated for Copilot targets, asserting: presence
  of `"version": 1`, correct top-level `"hooks"` object shape, absence of Claude-specific
  fields (`shell`, `statusMessage`), and correct field name `timeoutSec`.*

- **REQ-022 (Ubiquitous):** *The system shall include automated tests that verify the
  frontmatter of every generated `.prompt.md` file for Copilot targets uses the documented
  Copilot field name (not a Claude-specific field).*

- **REQ-023 (Ubiquitous):** *The system shall include automated tests that verify no generated
  `.agent.md` file for a Copilot target contains a `model:` field with a Claude-specific value.*

- **REQ-024 (Ubiquitous):** *The system shall include automated tests that verify, for each
  hook event installed on a Copilot target, that the associated script produces output
  conformant with the Copilot contract for that event (e.g. `additionalContext` for
  `sessionStart`, `decision`/`reason` for `agentStop`) and does not produce a blocking output
  for events declared as non-blocking.*

- **REQ-025 (Ubiquitous):** *The system shall include automated tests that verify, for the
  `copilot-cli` target, that command surfaces (wiki commands, requirements skill) are installed
  in a form that is not exclusively prompt-file-based.*

- **REQ-026 (Unwanted):** *If a new Copilot-facing asset is added to the installer, then the
  system shall require a corresponding schema-validation test before the asset is considered
  ready to ship.*

### Gruppo H — Onestà sui gap e correzione claim

- **REQ-027 (Ubiquitous):** *The system shall not claim full functional parity between Claude
  and Copilot targets for any surface that has not been validated against the Copilot schema
  and confirmed empirically on a real Copilot client.*

- **REQ-028 (Unwanted):** *If a surface installed for a Copilot target has a known gap or
  unverified behaviour, then the system shall declare that gap explicitly in the install output
  and in the surface-mapping documentation, rather than listing it as functionally equivalent.*

## 6. Requisiti non funzionali

- **NFR-1 (Non-distruttività e idempotenza):** le correzioni non devono alterare il
  comportamento dell'installer per il target `claude`; l'install per Copilot resta non
  distruttivo e idempotente (eredita NFR-3 di FEAT-007).
- **NFR-2 (Fonte unica / anti-drift — sul CONTENUTO):** l'anti-drift vincola il **contenuto**
  (corpo istruzionale), riusato byte-for-byte dalla fonte canonica; il **contenitore/contratto** è
  invece **tradotto nativamente** per assistente (non falsificato con campi tollerati). Le differenze
  per-assistante passano per il seam `AssistantProfile`/`Surface` nel `sertor-install-kit`.
- **NFR-3 (Fail-open per `preToolUse`):** qualsiasi script hook che gestisce l'evento
  `preToolUse` deve terminare sempre con exit code 0 su Copilot, anche in caso di errore di
  parsing o condizione imprevista (nessuna negazione accidentale di tool call).
- **NFR-4 (Manutenibilità):** il corpo LLM degli agenti e dei comandi è riusato byte-for-byte
  dalla fonte canonica Claude; non si aggiunge una seconda copia da mantenere.
- **NFR-5 (Copertura di test):** la suite di test di schema-validità (Gruppo G) deve poter
  girare offline (no dipendenza da un client Copilot reale); verifica strutturale, non
  comportamentale end-to-end.
- **NFR-6 (Robustezza alle Preview):** le superfici Copilot corrette rimangono isolate dietro
  il seam `AssistantProfile` in modo da poter essere aggiornate senza impattare il target
  `claude` (eredita NFR-6 di FEAT-007).
- **NFR-7 (Parità `sertor-flow`):** le stesse correzioni si propagano al pacchetto
  `sertor-flow` senza introdurre dipendenze di `sertor-flow` da `sertor-core`.

## 7. Vincoli, assunzioni e dipendenze

### Vincoli architetturali

- **Seam `AssistantProfile`/`Surface`** (`packages/sertor-install-kit/src/sertor_install_kit/assistant.py`):
  tutte le differenze per-assistente passano per questo seam (Principio X); nessuna modifica
  diretta ai plan-builder senza passare per il profilo.
- **`render_prompt_file` / `render_custom_agent`** in
  `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py`: le correzioni frontmatter
  passano per queste funzioni; il corpo rimane invariato (anti-drift, guarded da
  `test_assets_copilot_guard.py`).
- **Script `.ps1` condivisi**: `wiki-pending-check.ps1` e `sertor-rag-usage-check.ps1` sono
  today condivisi tra Claude e Copilot; l'adattamento per Copilot non deve rompere il
  comportamento Claude.
- **`sertor-flow` senza dipendenza da `sertor-core`**: invariante dura; le correzioni di
  `sertor-flow` usano solo il toolkit condiviso nel kit.

### Assunzioni [ASSUNTO]

- **[ASSUNTO] A-1:** il client target principale resta GitHub Copilot in VS Code agent mode e
  Copilot CLI 1.0.x; Copilot coding agent cloud (github.com) è fuori scope come in FEAT-007.
- **[ASSUNTO] A-2:** lo schema Copilot con `"version":1` e la struttura di hook descritta
  nell'audit è quella della versione CLI 1.0.63; versioni future potrebbero richiedere
  aggiornamenti (gestiti da NFR-6).
- **[ASSUNTO] A-3:** la verifica empirica di PR #66 (`.mcp.json` con `mcpServers` per
  `copilot-cli`) è valida per la versione CLI 1.0.63 del test (cfr. Q5 in §10).
- **[ASSUNTO] A-4:** l'hook `agentStop` di Copilot è l'equivalente dell'evento `Stop` di
  Claude Code; i nomi PascalCase sono accettati come alias (cfr. audit: "alias compat").

### Dipendenze

- `packages/sertor-install-kit` — seam `AssistantProfile`, renderer `surfaces.py`.
- `packages/sertor` — asset hook JSON, script `.ps1`, test parity/guard.
- `packages/sertor-flow` — superfici governance Copilot (agenti Sertor-authored).
- Test suite `packages/sertor/tests/test_assets_copilot_guard.py`,
  `test_surface_parity.py`, `test_install_wiki_copilot.py`, `test_install_rag_copilot.py`,
  `test_install_rag_copilot_cli.py`.

## 8. Rischi

- **R-1 — Regressione target `claude`:** le modifiche agli script `.ps1` condivisi potrebbero
  alterare il comportamento su Claude Code. Mitiga: test di non-regressione espliciti per il
  target `claude` e invarianti guard esistenti.
- **R-2 — Comportamento bloccante involontario su `preToolUse`:** un refactor dell'output
  script che genera `decision: deny` per errore blocca silenziosamente le tool call su Copilot.
  Mitiga: REQ-008 / NFR-3 (fail-open esplicito).
- **R-3 — Schema Copilot in evoluzione (Preview):** la versione 1.0.63 definisce un formato
  che una versione successiva potrebbe cambiare. Mitiga: NFR-6 (isolamento dietro seam); test
  di schema che falliscono in modo esplicito.
- **R-4 — Ambiguità dual-compat negli script `.ps1`:** tentare di emettere sia i campi Claude
  sia i campi Copilot nello stesso JSON potrebbe produrre side-effect indesiderati (es.
  `decision: block` interpretato da Claude). Mitiga: Q4 in §10 richiede conferma esplicita
  della strategia; REQ-011/REQ-012 la trattano come requisito.
- **R-5 — Parità illusoria persistente:** correggere la struttura ma non validarla
  comportamentalmente potrebbe lasciare gap non rilevati. Mitiga: CS-7 (test di schema); REQ-027
  (no claim senza verifica).
- **R-6 — Comandi Copilot CLI non invocabili:** se il custom-agent su CLI non è il veicolo
  corretto per i comandi wiki (mancata conferma Q2), i comandi restano non raggiungibili.
  Mitiga: Q2 in §10 richiede decisione esplicita; REQ-013 specifica il requisito funzionale.

## 9. Prioritizzazione (MoSCoW)

| REQ | Superficie | MoSCoW | Motivazione |
|-----|-----------|--------|-------------|
| REQ-001…REQ-005 | Hook JSON schema | **Must** | Senza `version:1` nessun hook parte; bug critico silenzioso |
| REQ-006 | Output SessionStart (`additionalContext`) | **Must** | Zero contesto iniettato oggi |
| REQ-007 | Output `agentStop` (non-blocking) | **Must** | Output ignorato; necessario per funzionamento |
| REQ-008 | `preToolUse` fail-open | **Must** | Fail-closed involontario è il rischio più grave |
| REQ-009…REQ-010 | Output `sessionEnd` / no `systemMessage` Claude-only | **Must** | Output non consumato da Copilot |
| REQ-011…REQ-012 | Dual-compat script `.ps1` | **Must** | Prerequisito per REQ-006…REQ-010 |
| REQ-013 | Comandi wiki su `copilot-cli` (custom-agent) | **Must** | Su CLI i prompt-file non esistono |
| REQ-014 | `requirements` su `copilot-cli` | **Must** | Stessa ragione di REQ-013, lato governance |
| REQ-015 | Prompt-file per VS Code | **Should** | VS Code li supporta; regressione evitabile |
| REQ-016 | Frontmatter `agent:` in `.prompt.md` | **Must** | Campo errato → comportamento non documentato |
| REQ-017 | Omissione `model:` Claude-only in `.agent.md` | **Must** | Valore non valido per Copilot |
| REQ-018…REQ-019 | Preservazione persona + anti-drift corpo | **Must** | Invariante esistente (FEAT-007 REQ-021) |
| REQ-020 | Verifica MCP CLI (`copilot-cli`) | **Should** | Confermato empiricamente PR #66; documentare |
| REQ-021…REQ-026 | Test di schema-validità Copilot (Gruppo G) | **Must** | Questi test avrebbero preso tutti i bug dell'audit |
| REQ-027…REQ-028 | Onestà claim / gap espliciti (Gruppo H) | **Must** | Correzione del false-positive di parità |

**Must complessivi:** REQ-001…REQ-014, REQ-016…REQ-019, REQ-021…REQ-028 (26 REQ).
**Should:** REQ-015, REQ-020 (2 REQ).

## 10. Domande aperte — RISOLTE (2026-06-17)

Tutte chiuse con l'utente sotto il **principio guida "supporto nativo, niente hack"** (§1):
**Q1 = (b)** SessionStart nativo (`type:"prompt"` su CLI; meccanismo nativo su VS Code) ·
**Q2 = (c)** piano per-target (VS Code prompt-file + CLI custom-agent) ·
**Q3 = (b)** `agentStop` non-bloccante (`decision:"allow"`+`reason`) ·
**Q4 = (b)** script condiviso con output nativo per assistente via parametro (no dual-field) ·
**Q5 = incluso** verifica empirica del target MCP CLI ·
**Q6 = (a)** omettere `model:` Claude nei custom-agent Copilot.

**Resta come nodo di DESIGN (non di requisito), per la fase `plan`:** il meccanismo nativo esatto di
iniezione contesto SessionStart su **Copilot VS Code** (il `type:"prompt"` è CLI-only) e l'eventuale
**revisione del seam `AssistantProfile`/`Surface`** se non produce artefatti nativi per superficie.
Sotto, il contesto originale di ciascuna domanda.

---

**Q1 — Output hook SessionStart su Copilot: strategia di wrapping**

*Contesto:* oggi il comando hook SessionStart emette stringhe plain; Copilot tenta `JSON.parse`
e, fallendo, non inietta contesto. Il tipo `type: "prompt"` nativo Copilot è disponibile solo
per `sessionStart` su CLI (non su VS Code agent mode) e renderebbe il comportamento diverso tra
i due target.

Opzioni:
- **(a) Avvolgere l'output in `{"additionalContext": "<messaggio>"}`** nel wiring hook JSON
  (o nello script stesso): funziona sia su VS Code che su CLI, è l'unica forma che la
  documentazione ufficiale cita per iniettare contesto a sessionStart via script.
- **(b) Usare `type: "prompt"` nel JSON hook**: più pulito, ma supportato solo da CLI e
  diverge da VS Code — richiede due varianti di wiring.

**Raccomandazione: (a).** Mantiene il comportamento uniforme tra `copilot` e `copilot-cli` e
non richiede due varianti di wiring. Il compromesso è che il messaggio passa attraverso JSON
escaping (non nativo), ma è meno frammentato. Se si scopre che `type: "prompt"` è supportato
anche su VS Code in una versione corrente, la decisione va riesaminata.

[DA CHIARIRE: confermare la scelta (a) o (b) per SessionStart.]

---

**Q2 — Veicolo comandi su Copilot CLI: prompt-file vs custom-agent**

*Contesto:* i prompt-file (`.github/prompts/*.prompt.md`) non sono supportati da Copilot CLI —
su CLI non esiste il concetto di slash-command da prompt-file. Il custom-agent
(`.github/agents/*.agent.md`) funziona su entrambi VS Code e CLI. Oggi il `copilot-cli` target
installa solo prompt-file (lo stesso piano del target `copilot`).

Opzioni:
- **(a) Per `copilot-cli`: installare SOLO custom-agent** (nessun prompt-file) — i comandi wiki
  e requirements diventano agenti invocabili.
- **(b) Per `copilot-cli`: installare custom-agent AL POSTO dei prompt-file** per i comandi che
  oggi sono solo slash-command (wiki, wiki-author, requirements); rimuovere i prompt-file dal
  piano `copilot-cli`.
- **(c) Per `copilot` (VS Code): prompt-file + custom-agent; per `copilot-cli`: solo
  custom-agent** — il piano differisce per target. Trade-off: più asset, copertura più ricca su
  VS Code; piano più semplice su CLI.

**Raccomandazione: (c).** La differenza tra i due target Copilot è già codificata nel seam
`AssistantProfile`; aggiungerci una differenza di piano è coerente con la logica esistente. VS
Code guadagna sia il prompt-file (invocabile come slash-command) sia il custom-agent; CLI ottiene
solo il custom-agent. Il costo è mantenere il piano `copilot-cli` con un insieme di artefatti
diverso da `copilot`. Alternativa (b) è più semplice da testare ma perde la slot-command su VS
Code.

[DA CHIARIRE: scegliere tra (a), (b), (c) per la gestione comandi `copilot-cli`.]

---

**Q3 — Output hook `agentStop`: blocking vs allow**

*Contesto:* l'hook wiki-pending-check su Claude emette `systemMessage` (non bloccante). Su
Copilot l'evento `agentStop` (Stop) si aspetta `{"decision":"block|allow","reason":"..."}`. Se
si emette `decision: block` si forza un turno extra (Copilot chiede all'utente prima di
terminare); se si emette `decision: allow` l'hook è un puro notificatore.

Opzioni:
- **(a) `decision: block`** con reason che riassume il pending wiki: invasivo, costringe
  l'agente a un turno extra anche per un promemoria minore.
- **(b) `decision: allow` + messaggio su stderr (o `reason`)**: non-bloccante, coerente con la
  natura del reminder wiki (non dovrebbe fermare il flusso).

**Raccomandazione: (b).** Il reminder wiki è intenzionalmente non-bloccante anche su Claude
(exit 0, `systemMessage` consigliato). Renderlo bloccante su Copilot creerebbe un comportamento
asimmetrico e invasivo. `reason` trasmette il messaggio senza bloccare.

[DA CHIARIRE: confermare (b) per `agentStop` / non-bloccante.]

---

**Q4 — Script `.ps1` dual-compat vs per-assistente**

*Contesto:* `wiki-pending-check.ps1` è condiviso tra Claude e Copilot (FR-014 di FEAT-007). Il
contratto di output diverge per evento: `systemMessage` per Claude, `additionalContext`/
`decision` per Copilot. Emettere entrambi i campi nello stesso JSON farebbe ignorare i campi
sconosciuti (entrambi gli assistenti di solito ignorano campi non riconosciuti), ma genera il
rischio che `decision: allow` venga interpretato da Claude in modo inatteso, o che un futuro
refactor introduca `decision: block` accidentalmente.

Opzioni:
- **(a) Script dual-compat**: emettere sia `systemMessage` sia `additionalContext`/`decision` in
  un unico JSON — un campo viene ignorato dall'assistente che non lo riconosce.
- **(b) Wiring JSON separato per assistente**: script identico, ma il JSON di wiring (hook
  entry) per Copilot invoca lo script con un parametro (es. `-Assistant copilot`) che lo porta a
  emettere solo i campi Copilot.
- **(c) Script separati per assistente** (rompe FR-014 di FEAT-007).

**Raccomandazione: (b).** Mantiene un unico script (FR-014 preservato), demanda la variazione al
parametro di invocazione (nel JSON hook entry che è già per-assistente), ed evita l'emissione
di `decision:` in contesto Claude dove potrebbe causare effetti indesiderati. Costo: lo script
acquisisce un parametro `-Assistant`, il JSON hook Copilot lo passa. Alternativa (a) è più
semplice ma dipende dall'assunzione che `decision: allow` sia ignorato da Claude —
assunzione non documentata e fragile.

[DA CHIARIRE: scegliere tra (a) e (b) per la strategia dual-compat degli script `.ps1`.]

---

**Q5 — MCP Copilot CLI: conferma `.mcp.json` repo-level**

*Contesto:* la doc ufficiale indica `~/.copilot/mcp-config.json` (user-level) per la CLI; la
PR #66 (2026-06-16) ha validato empiricamente che la CLI legge anche `.mcp.json` a livello di
repo con root key `mcpServers`. Il comportamento attuale del target `copilot-cli` si basa su
questa verifica.

Opzioni:
- **(a) Includere nello scope la conferma documentata** e, se la prova empirica viene
  smentita da una versione più recente, correggere la surface nel kit.
- **(b) Escludere dallo scope** (verifica solo operativa, non un requisito di prodotto).

**Raccomandazione: (a).** Il req REQ-020 è già formulato in modo da non essere bloccante: richiede
solo che la prova empirica sia documentata e che si agisca se viene smentita. Non aggiungere
questo requisito lascerebbe il target `copilot-cli` su un assunto non tracciato.

[DA CHIARIRE: confermare inclusione/esclusione di REQ-020 dallo scope.]

---

**Q6 — Frontmatter custom-agent: omettere `model:` vs mappare**

*Contesto:* il campo `model: haiku` nel frontmatter dell'agente `wiki-curator.md` (e degli
agenti di `sertor-flow`) è un nome Claude non valido per Copilot. Il renderer `render_custom_agent`
oggi lo copia verbatim.

Opzioni:
- **(a) Omettere il campo `model:` per i target Copilot** (lascia il default Copilot): approccio
  conservativo, nessuna dipendenza da una mappatura nomi-modelli.
- **(b) Mappare nomi Claude → nomi Copilot** (es. `haiku` → `gpt-4o-mini`): richiede una tabella
  di mapping da mantenere, dipende dall'offerta modelli Copilot (mutevole).

**Raccomandazione: (a).** La mappatura (b) è fragile e crea una dipendenza su versioni di modello
specifiche che possono cambiare. Omettere il campo lascia la scelta del modello al default
Copilot, che è la politica più robusta. Il campo `model:` negli agenti Sertor è comunque
un'indicazione di preferenza, non un vincolo rigido.

[DA CHIARIRE: confermare omissione del campo `model:` per i target Copilot (a) oppure interesse
a una mappatura (b).]
