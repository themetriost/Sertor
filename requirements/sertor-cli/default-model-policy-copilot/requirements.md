# Requisiti — Default model-policy per i subagent Copilot CLI

<!-- Deriva da: FEAT-015 (requirements/sertor-cli/epic.md §8) -->

## 1. Contesto e problema (perché)

Sertor distribuisce cinque agenti propri (Sertor-authored) come *custom-agent* `.agent.md` quando
l'ospite installato è **GitHub Copilot CLI**: `concierge` e `wiki-curator` (pacchetto `sertor`),
`requirements-analyst`, `configuration-manager` e la skill `requirements` resa come custom-agent
(pacchetto `sertor-flow`, FEAT-012). Oggi il renderer che produce questi file
(`render_custom_agent`, `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py:53-74`)
**omette sempre** il campo `model:` (`include_model=False` di default) — la selezione del modello
resta implicita, affidata al default della CLI Copilot dell'utente al momento dell'esecuzione.

Un utente Copilot CLI ha segnalato (`wiki/sources/usersfeedback/copilot-default-models.md`,
2026-06-30) che questo produce **variabilità non voluta** tra installazioni: agenti con profili
cognitivi molto diversi (dispatcher meccanici come `concierge`/`configuration-manager`, agenti di
scrittura/reasoning come `requirements-analyst`/`requirements`, agenti di sintesi come
`wiki-curator`) finiscono tutti sullo stesso modello implicito, senza un default ragionato che
ottimizzi costo/latenza sui task meccanici e tenga la qualità alta sulle fasi ad alto impatto.

**Finding critico di verifica (vincolante per questi requisiti):** la proposta originale
dell'utente (un blocco `subagents.agents.<name>.model` nel profilo Copilot) **non corrisponde al
meccanismo reale**. La documentazione ufficiale GitHub
(`https://docs.github.com/en/copilot/reference/custom-agents-configuration`) stabilisce che il
modello di un custom agent Copilot CLI si imposta con il campo **`model:` nel frontmatter YAML del
file `.agent.md` stesso** («Model to use when this custom agent executes. If unset, inherits the
default model.»). Questi requisiti sono scritti sul meccanismo **verificato** (frontmatter
per-file), non sulla proposta letterale dell'utente.

Questo riapre — senza contraddirla — la regola introdotta da FEAT-011/FEAT-049
(`packages/sertor/tests/test_assets_copilot_guard.py:37-48`,
`packages/sertor/tests/test_schema_copilot_frontmatter.py:43-69`), che oggi impone «`model:` **sempre
assente**» sui custom-agent Copilot. Quella regola nasceva per impedire il **leak** dell'alias
Claude (`haiku`/`sonnet`) ereditato dal frontmatter canonico — invalido su Copilot — non per vietare
un `model:` **deliberato e nativo Copilot**. L'invariante da riformulare (materia di design a
valle, qui solo dichiarata) è: *ometti l'alias Claude ereditato, ma emetti un `model:` esplicito
quando una policy Copilot lo prescrive*.

## 2. Obiettivi e criteri di successo

**Obiettivo:** ogni agente Copilot CLI Sertor-authored riceve, all'installazione, un modello di
default ragionato — non la selezione implicita di oggi — restando **modificabile** dall'utente.

- **CS-1 (default esplicito):** i 5 agenti in ambito, installati su Copilot CLI, hanno **tutti** un
  campo `model:` esplicito e non-vuoto nel frontmatter depositato (0 agenti a selezione implicita).
- **CS-2 (no leak alias Claude):** 0 occorrenze di un alias-modello Claude (`haiku`/`sonnet`) nel
  frontmatter Copilot risultante — nessuna regressione rispetto alla garanzia FEAT-011/049.
- **CS-3 (fonte unica versionata):** ogni model-ID usato dalla policy compare in **un solo posto**
  versionato, leggibile da entrambi i pacchetti coinvolti (`sertor` e `sertor-flow`); 0 ID
  hardcoded/sparsi nel codice installer per-agente.
- **CS-4 (idempotenza):** install/upgrade ripetuti a parità di versione del profilo producono un
  contenuto renderizzato byte-identico.
- **CS-5 (fail-loud su profilo incompleto):** un profilo privo della voce per uno dei 5 agenti in
  ambito fa fallire l'installazione con un messaggio che **nomina** l'agente mancante — 0
  installazioni silenziosamente incomplete.
- **CS-6 (DoD — distribuzione + doc):** la policy raggiunge un ospite reale **solo** tramite
  `sertor install rag` e `sertor-flow install` (nessun passo manuale); la documentazione utente
  (`docs/install-copilot.md` + tabella capability di `packages/sertor/docs/install.md`) elenca il
  default per ciascuno dei 5 agenti e il modo per modificarlo, aggiornata nello stesso step.
- **CS-7 (zero impatto su Claude):** 0 regressioni misurabili sul path Claude (il pin `model: sonnet`
  di `concierge` e gli altri frontmatter Claude restano bit-per-bit invariati).

## 3. Stakeholder e attori

- **Utente Copilot CLI** che installa/aggiorna Sertor su un repo ospite — riceve la policy.
- **Utente Claude** — non impattato (nessun cambiamento sul suo path).
- **Manutentore Sertor** — cura il profilo versionato dei model-ID nel tempo (i model-ID invecchiano).
- **Pacchetto `sertor`** (owner di `concierge`, `wiki-curator`) e **pacchetto `sertor-flow`** (owner
  di `requirements-analyst`, `configuration-manager`, `requirements`) — entrambi consumano la stessa
  policy, senza che `sertor-flow` dipenda da `sertor-core`.

## 4. Ambito

### In ambito
- I **5 agenti Sertor-authored** resi come `.agent.md` su Copilot CLI:
  `concierge`, `wiki-curator` (pacchetto `sertor`); `requirements-analyst`, `configuration-manager`,
  `requirements` (pacchetto `sertor-flow`).
- Un **profilo versionato** che centralizza la mappa agente→model-ID (un solo posto, non ID sparsi).
- L'emissione del campo `model:` nel frontmatter dei 5 `.agent.md`, in modo non distruttivo,
  idempotente, coerente su install/upgrade/uninstall.
- Il comportamento **fail-loud** quando il profilo non copre un agente in ambito.
- La riconciliazione dichiarata (nota d'impatto, non risolta qui) con le guardie esistenti che oggi
  impongono «`model:` sempre assente».
- L'aggiornamento della documentazione utente (DoD di setup, regola standing del workspace).
- Solo **Copilot CLI**; nessuna modifica al meccanismo Claude.

### Fuori ambito
- **Gli agenti `speckit.*`** (`speckit.specify/clarify/plan/tasks/analyze/implement/constitution/
  checklist/taskstoissues`): sono **prompt-file vendorati da spec-kit**
  (`.github/prompts/speckit.*.prompt.md`, depositati da `specify init --ai copilot` tramite
  `packages/sertor-flow/src/sertor_flow/speckit_launch.py`). Sertor non ne scrive il frontmatter e
  la documentazione ufficiale **non conferma** che i prompt-file supportino `model:`. Una loro
  assegnazione richiede una spike separata di verifica — **tracciata come follow-up**, non sepolta:
  da promuovere a nuova voce di backlog (`FEAT-NNN`, epica `sertor-cli`) quando si deciderà di
  affrontarla.
- **Claude:** nessun impatto; il `model:` Claude nel frontmatter resta gestito come oggi.
- **Codex** come assistente ospite: fuori ambito (già `Could`/non avviato altrove nell'epica).
- **Probe di disponibilità modello per-tenant a install-time** come capacità garantita: da verificare
  se è realizzabile (vedi DA-2); se non lo è, resta fuori ambito per costruzione.
- **Nuovi provider di modello** o nuova logica di scelta modello runtime: fuori ambito (qui si
  distribuisce solo un *default*, non un motore di instradamento).

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Optional):** *Where the target assistant is Copilot CLI, the system shall assign an
  explicit model to each of the five in-scope Sertor-authored custom-agents
  (`concierge`, `wiki-curator`, `requirements-analyst`, `configuration-manager`, `requirements`) via
  the `model:` field of the deposited `.agent.md` frontmatter.*
- **REQ-002 (Unwanted):** *If the target assistant is Claude, then the system shall not apply the
  Copilot model-policy — the Claude-specific `model:` handling (e.g. the `sonnet` pin on
  `concierge`) shall remain unaffected.*
- **REQ-003 (Ubiquitous):** *The system shall source every model-ID assigned by the policy from a
  single versioned model-policy profile, shared by every package that deposits an in-scope agent,
  rather than from values embedded in individual agent assets or scattered per-agent in installer
  code.*
- **REQ-004 (Event-driven):** *When rendering a Copilot custom-agent's frontmatter for an in-scope
  agent, the system shall emit the model-ID prescribed by the policy for that agent, instead of any
  Claude-alias model value inherited from the canonical asset's own frontmatter.*
- **REQ-005 (Event-driven):** *When `sertor install rag` or `sertor-flow install` deposits an
  in-scope agent that does not yet exist on the host, the system shall write its frontmatter with
  the policy-assigned model, merged non-destructively with the rest of the frontmatter (identity/
  description/tools fields untouched).*
- **REQ-006 (Unwanted — DA aperta):** *If a host already carries a deposited in-scope `.agent.md`
  whose `model:` value differs from what the current policy would produce, then the system shall
  not silently overwrite it without the user's confirmation.*
  [DA CHIARIRE: DA-1 — il file `.agent.md` è oggi un `owned_file` interamente ri-renderizzato a
  ogni upgrade (`update_file_if_changed`); non esiste un meccanismo che distingua "valore di
  default" da "valore scelto dall'utente" nel file stesso. Va accertato anche **dove** un cambio
  fatto con `/subagents` persiste davvero (nel file `.agent.md` o altrove in `~/.copilot/`), perché
  cambia cosa va protetto.]
- **REQ-007 (Ubiquitous — idempotenza):** *The system shall produce byte-identical rendered
  frontmatter for an in-scope agent across repeated install/upgrade runs, as long as the host state
  and the policy version are unchanged.*
- **REQ-008 (Unwanted — fail-loud su profilo incompleto):** *If the model-policy profile has no
  entry for one of the five in-scope agents, then the system shall fail the installation with an
  error that explicitly names the missing agent, rather than deposit that agent without a model or
  with an undefined value.*
- **REQ-009 (Unwanted — DA aperta, fallback fail-loud):** *If a policy-assigned model is not
  available in the installing user's Copilot tenant/environment, then the system shall make this
  explicit to the user rather than fail or degrade silently, and shall prefer, when the profile
  defines one, a fallback model of comparable cost/quality class.*
  [DA CHIARIRE: DA-2 — Sertor non ha oggi (e potrebbe non avere mai) un modo di interrogare a
  install-time quali modelli sono abilitati nel tenant Copilot dell'utente; se confermato,
  "fail-loud" qui non può essere un controllo install-time reale e deve ridursi a (a) un avviso
  documentale esplicito e/o (b) demandare il segnale al comportamento runtime di Copilot stesso.]
- **REQ-010 (Ubiquitous — non rigidità):** *The system shall document, in the installation output
  and/or in the user documentation, that the assigned model per agent is a modifiable default (e.g.
  via Copilot's own `/subagents` command or by editing the `.agent.md` frontmatter), not an
  enforced constraint.*
- **REQ-011 (Ubiquitous — coerenza cross-pacchetto):** *The system shall apply the same
  model-policy profile identically whether the in-scope agent is deposited by the `sertor` package
  (`concierge`, `wiki-curator`) or by the `sertor-flow` package (`requirements-analyst`,
  `configuration-manager`, `requirements`), so a host installing both receives one coherent policy.*
- **REQ-012 (Ubiquitous — lifecycle):** *The system shall resolve and apply the model-policy
  identically at first install and at upgrade time for every in-scope agent; uninstall shall not be
  affected by any model-policy semantics (removal only).*
- **REQ-013 (Event-driven — confine scope):** *When rendering the `speckit.*` prompt-files vendored
  by `specify init` for Copilot CLI, the system shall not attempt to assign a model — they are
  explicitly out of scope for this feature (see §4).*
- **REQ-014 (Ubiquitous — DoD distribuzione):** *The system shall make the model-policy reach a
  host exclusively through `sertor install rag` (for `concierge`, `wiki-curator`) and `sertor-flow
  install` (for `requirements-analyst`, `configuration-manager`, `requirements`), with no manual
  post-install step required to obtain it.*
- **REQ-015 (Ubiquitous — DoD documentazione):** *The system's user-facing documentation
  (`docs/install-copilot.md` and the capability table in `packages/sertor/docs/install.md`) shall
  describe the default model assigned to each in-scope agent and how a user can change it.*
- **REQ-016 (Ubiquitous — non contraddizione con FEAT-011/049):** *The system shall continue to omit
  any Claude-alias model value (e.g. `haiku`, `sonnet`) inherited unintentionally from a canonical
  asset's frontmatter on every Copilot custom-agent render, whether or not the model-policy assigns
  an explicit model for that agent.*

## 6. Requisiti non funzionali

- **NFR-001 (manutenibilità):** aggiornare un model-ID datato (i modelli invecchiano) deve richiedere
  la modifica di **un solo** artefatto versionato, non una ricerca/sostituzione sparsa nel codice
  installer.
- **NFR-002 (determinismo):** la risoluzione agente→modello deve essere deterministica: stesso
  agente + stessa versione del profilo → stesso model-ID, indipendentemente dall'ambiente di
  installazione.
- **NFR-003 (trasparenza):** il modello risolto per ciascun agente deve essere visibile nel file
  depositato (e idealmente nel report d'installazione), mai un default nascosto.
- **NFR-004 (tracciabilità):** un cambiamento del profilo (bump di model-ID) deve essere distinguibile,
  tramite un marcatore di versione del profilo, da un cambiamento del corpo/persona dell'agente.
- **NFR-005 (Principio XI — nessun runtime di core):** risolvere e applicare la policy è
  esclusivamente una responsabilità dell'installer/distribuzione; non deve richiedere di importare o
  invocare `sertor_core`.
- **NFR-006 (isolamento Claude):** applicare la policy Copilot non deve avere alcun effetto
  collaterale osservabile sul path Claude (stesso plan-builder, nessuno stato condiviso mutato).
- **NFR-007 (degradazione offline):** l'assenza di connettività per una verifica di disponibilità
  modello a runtime del tenant non deve bloccare il completamento dell'installazione: il default del
  profilo deve poter essere scritto comunque (nessuna dipendenza bloccante da un probe live).
- **NFR-008 (verificabilità offline):** il comportamento della policy (emissione del model-ID
  corretto, non-leak dell'alias Claude, fail-loud su profilo incompleto, idempotenza) deve essere
  verificabile senza rete e senza un tenant Copilot reale (offline, come le guardie esistenti
  `test_assets_copilot_guard.py`/`test_schema_copilot_frontmatter.py`).

## 7. Vincoli, assunzioni e dipendenze

- **Meccanismo reale confermato:** il modello di un custom-agent Copilot CLI si imposta col campo
  `model:` nel frontmatter YAML del file `.agent.md` (fonte: doc ufficiale GitHub, citata in §1),
  **non** un blocco `subagents.agents.<name>.model` (proposta utente inesistente nel prodotto reale).
- **Stato attuale del renderer:** `render_custom_agent(canonical_text, *, include_model: bool =
  False)` (`packages/sertor-install-kit/src/sertor_install_kit/surfaces.py:53-74`) già supporta
  l'emissione del campo, ma **solo in eco verbatim** del valore presente nel frontmatter canonico
  (es. `model: haiku` → `model: haiku` se `include_model=True`) — non da una policy. Questa feature
  richiede quindi un meccanismo di **sostituzione** del valore (dalla policy, non dall'asset
  canonico): è un gap architetturale reale, da risolvere in fase di design, non qui.
- **Guardie esistenti da riconciliare (impatto, non da risolvere qui):**
  `packages/sertor/tests/test_assets_copilot_guard.py::test_custom_agent_omits_model_field` e
  `test_anti_pattern_custom_agent_drops_claude_model`,
  `packages/sertor/tests/test_schema_copilot_frontmatter.py::test_custom_agent_has_no_model` e
  `test_anti_pattern_custom_agent_drops_claude_model` impongono oggi «`model:` sempre assente» sui
  custom-agent Copilot. Vanno **riformulate** (non rimosse): «l'alias Claude ereditato resta sempre
  assente» **e** «un `model:` esplicito della policy Copilot è ammesso e atteso».
- **Punti di deposito reali (5 agenti):**
  - `concierge` — `packages/sertor/src/sertor_installer/install_rag.py:344-360` (`_concierge_artifact`)
    + `:363-375` (`_render_rag_file`, dispatch su `.agent.md`).
  - `wiki-curator` — `packages/sertor/src/sertor_installer/install_wiki.py:95-96` (sorgente/target),
    `:241-245` (artifact), `:278-296` (`_render_for_target`).
  - `requirements-analyst`, `configuration-manager`, `requirements` (come custom-agent) —
    `packages/sertor-flow/src/sertor_flow/install_governance.py:99-111` (`_SERTOR_AUTHORED`),
    `:127-157` (`build_governance_plan`), `:199-211` (`_render_for_target`).
- **Lifecycle attuale:** i 5 file sono depositati con `WriteStrategy.CREATE_IF_ABSENT` al primo
  install; all'**upgrade** vengono interamente ri-renderizzati e sovrascritti se cambiati
  (`_apply_rag_upgrade`, `packages/sertor/src/sertor_installer/install_rag.py:924-945`, ramo FILE
  `:936-945`) — non esiste oggi una nozione di "patch del solo campo `model:`" che preservi un
  valore diverso dal default. Questo è precisamente il vincolo dietro DA-1.
- **Targeting/vehicle:** `AssistantId.COPILOT_CLI`, `AssistantProfile.render_path`,
  `command_vehicle=CUSTOM_AGENT` per la superficie COMMAND su Copilot CLI
  (`packages/sertor-install-kit/src/sertor_install_kit/assistant.py:21-25, 87-130, 155-164`).
- **`sertor-core` invariato** (Principio XI): questa feature è puramente di distribuzione/installer;
  zero impatto runtime sul core.
- **`sertor-flow` non dipende da `sertor-core`**: il profilo versionato deve restare leggibile da
  entrambi senza introdurre questa dipendenza (vincolo architetturale duro dell'epica).
- **Il profilo è un default modificabile**, non una regola imposta: l'utente resta libero di
  cambiarlo dopo l'installazione (nota esplicita dell'utente originale, §1 richiesta).

## 8. Rischi

- **R-1 — Perdita silente di un override utente a upgrade:** dato che il file `.agent.md` è
  interamente ri-renderizzato a ogni upgrade, un edit manuale del `model:` fatto dall'utente rischia
  di essere sovrascritto al prossimo `sertor upgrade`/`sertor-flow upgrade` finché DA-1 non è
  risolta in design.
- **R-2 — Model-ID datati/non disponibili nel tenant:** un model-ID della policy può diventare
  deprecato o non abilitato nel piano dell'utente; senza un probe a install-time (DA-2), l'install
  "riesce" ma l'agente può risultare inutilizzabile a runtime finché l'utente non se ne accorge.
- **R-3 — Drift con le guardie FEAT-011/049:** se la riconciliazione delle guardie esistenti (§7)
  non viene fatta con cura, si rischia (a) di rompere la protezione contro il leak dell'alias
  Claude, oppure (b) di reintrodurre in CI un falso positivo che blocca la feature.
- **R-4 — Incoerenza cross-pacchetto:** se `sertor` e `sertor-flow` finissero per leggere il profilo
  da fonti o versioni diverse, un host che installa entrambi i pacchetti riceverebbe una policy
  incoerente (viola NFR-001/CS-3).
- **R-5 — Agente-fantasma/drift bundlato↔dogfood:** come già accaduto per altri asset (pattern noto
  nel workspace), un profilo versionato non allineato dal meccanismo di sync esistente
  (`sertor_installer.sync`) rischia di divergere tra l'asset bundlato e la copia dogfood.
- **R-6 — Confusione sul confine speckit.\*:** se la spiegazione del confine (§4 Fuori ambito) non è
  comunicata chiaramente all'utente in doc, ci si può aspettare erroneamente che anche gli agenti
  `speckit.*` ricevano un default di modello.

## 9. Prioritizzazione (MoSCoW)

| Requisito | Priorità | Nota |
|---|---|---|
| REQ-001, REQ-002, REQ-003, REQ-004, REQ-005 | **Must** | Nucleo della capacità: policy versionata applicata ai 5 agenti Copilot CLI |
| REQ-007 (idempotenza) | **Must** | Invariante installer già richiesto ovunque nel progetto |
| REQ-008 (fail-loud profilo incompleto) | **Must** | Install-time, deterministico, realizzabile oggi |
| REQ-011 (coerenza cross-pacchetto) | **Must** | Senza, la feature è incoerente tra `sertor`/`sertor-flow` |
| REQ-012 (lifecycle install/upgrade) | **Must** | Coerente col ciclo di vita già consegnato (FEAT-008) |
| REQ-013 (confine speckit.\* dichiarato) | **Must** | Necessario per non promettere ciò che non si può verificare |
| REQ-014 (DoD distribuzione) | **Must** | Regola standing del workspace (feature completa ⇔ installabile) |
| REQ-015 (DoD documentazione) | **Must** | Regola standing del workspace |
| REQ-016 (non contraddizione FEAT-011/049) | **Must** | Non regressione di una garanzia esistente |
| REQ-006 (protezione override utente) | **Should** | Valore reale ma **dipende da DA-1**; degradare onestamente finché non risolta |
| REQ-010 (non rigidità/documentare modificabilità) | **Should** | Basso costo, alto valore percepito |
| REQ-009 (fail-loud disponibilità tenant) | **Could** | **Dipende da DA-2**: la parte "probe reale a install-time" potrebbe non essere realizzabile; la parte documentale è più economica e può essere Should |
| Fallback esplicito multi-tier per agente nel profilo | **Could** | Raffinamento del profilo, non necessario al primo taglio |
| Assegnazione modello per `speckit.*` | **Won't** (qui) | Fuori ambito dichiarato; da valutare come feature separata dopo una spike |

## 10. Domande aperte

> **Aggiornamento (elicitazione, 2026-07-01):** meccanismo confermato = **A — `model:` nel
> frontmatter `.agent.md` per-repo** (decisione utente), scartato il meccanismo B (settings
> machine-global `~/.copilot/settings.json`, schema non documentato, viola per-repo/non-distruttivo).
> Verifica doc: il changelog Copilot CLI v1.0.62 conferma che il modello del subagent si configura
> «via user settings **or** the /subagents picker» → l'override utente vive in `~/.copilot/settings.json`
> (file **diverso** da quello che Sertor renderizza) e vince a runtime. Questo **scioglie DA-1 e DA-2**.

- **DA-1 (upgrade vs override utente) — ✅ RISOLTA.** Un cambio fatto con `/subagents` persiste in
  `~/.copilot/settings.json` (config utente, non nel repo) e ha precedenza a runtime sul default del
  frontmatter. Quindi l'override naturale dell'utente è **al sicuro per costruzione**: Sertor scrive
  solo il *default* nel `.agent.md` (owned_file, ri-renderizzato a upgrade come oggi), senza toccare
  la scelta utente. REQ-006 si riduce a semantica owned_file standard + nota documentale (un edit
  *manuale* diretto del frontmatter resta soggetto al normale upgrade, documentato — non protetto ad hoc).
- **DA-2 (disponibilità modelli per-tenant a install-time) — ✅ RISOLTA (no probe).** L'installer è
  offline/locale (NFR-007) e non chiama l'API Copilot → **non può** conoscere i modelli abilitati nel
  tenant. Il «fail-loud» di REQ-009 si riduce a (a) avviso documentale esplicito + (b) comportamento
  runtime di Copilot quando il modello non è disponibile. Nessun controllo install-time reale.
- **DA-3 (dove vive il profilo versionato) — ✅ RISOLTA (raccomandazione ratificata).** Il profilo
  versionato agente→model-ID vive nel kit condiviso **`sertor-install-kit`** (già dipendenza di
  `sertor` e `sertor-flow`, zero legame con `sertor-core`) → fonte unica, nessuna dipendenza vietata.
- **DA-4 (riconciliazione delle guardie esistenti) — resta a plan.** Criterio da fissare in design:
  riformulare `test_custom_agent_omits_model_field`/`test_anti_pattern_custom_agent_drops_claude_model`
  (e gemelle) da «`model:` sempre assente» a «alias Claude (`haiku`/`sonnet`/`opus`) sempre assente,
  `model:` di policy nativo Copilot ammesso e atteso». Materia di plan (§7).
- **DA-5 (fallback per-agente, minore) — resta a plan (ridimensionata).** Con DA-2 risolta (no probe),
  il fallback è per lo più documentale; se il profilo definisce un fallback, per-agente vs globale è
  dettaglio di plan. Non blocca il primo taglio.

---

## Nota di processo (ancoraggio ed errori strumenti)

- **MCP `sertor-rag` non disponibile in questa invocazione:** i tool `mcp__sertor-rag__find_symbol`
  e `mcp__sertor-rag__search_code` hanno restituito `Error: No such tool available` — non erano
  esposti al contesto di questo subagent. Segnalato esplicitamente (regola standing "errori MCP =
  segnale, non rumore"); **non degradato in silenzio**: l'ancoraggio al codice è stato comunque
  completato con `Grep`/`Read` diretti sui file reali (citazioni `path:lineno` in tutto il documento).
- Ogni requisito che cita un meccanismo di codice è ancorato a un simbolo/file verificato per
  lettura diretta (vedi §7 per l'elenco completo dei percorsi).
