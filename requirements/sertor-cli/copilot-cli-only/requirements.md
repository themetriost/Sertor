# Requisiti — Refactor distribuzione Copilot verso CLI-only

<!-- Deriva da: decisioni utente 2026-06-17 (post-verifica empirica FEAT-007/009/011) -->

> **Stato:** decomposizione **chiusa** — Q1–Q4 risolte con l'utente (2026-06-17, §10). Pronta per
> `/speckit-specify`. Decisioni: **Q1 (a)** rimozione TOTALE di `AssistantId.COPILOT` (VS Code) ·
> **Q2** mapping `copilot-cli → --ai copilot` confermato (un solo punto, documentato) · **Q3 (a)**
> solo nota di migrazione (cleanup manuale; nessun rilevamento automatico) · **Q4 (a)** rinomina
> diretta `copilot → copilot-cli` in `sertor-flow` (breaking dichiarato).

## 1. Contesto e problema (perché)

La distribuzione Copilot è stata verificata end-to-end (Copilot CLI 1.0.63) ed è funzionante:
MCP, agent incluso SpecKit, hook. L'implementazione attuale introduce tuttavia tre incoerenze
che generano footgun reali per chi installa Sertor su un ospite Copilot:

**Due target Copilot paralleli e non-equivalenti.** Esistono oggi `AssistantId.COPILOT` (VS Code
→ `.vscode/mcp.json`, chiave `servers`, comandi come prompt-file) e `AssistantId.COPILOT_CLI`
(CLI → `.mcp.json`, chiave `mcpServers`, comandi come custom-agent). Si tratta dello stesso
assistente con superfici client diverse. Tenere entrambi come opzioni dello stesso flag
`--assistant` crea il rischio concreto che un utente installi con `--assistant copilot` credendo
di usare la CLI, ottenga un `.vscode/mcp.json` che la CLI non legge, e la capacità risulti
silenziosamente non funzionante. La verifica empirica ha dimostrato che la CLI legge `.mcp.json`
(formato `mcpServers`), non il file VS Code. Il target VS Code non è mai stato validato su un
client VS Code reale (resta `[ASSUNTO-VSC]` dichiarato in FEAT-011).

**Incoerenza di naming tra pacchetti.** `sertor` (pacchetto RAG/wiki) accetta già
`--assistant claude|copilot|copilot-cli`; `sertor-flow` (governance) accetta solo
`--assistant claude|copilot`. Un utente che usa la CLI vede due interfacce divergenti per due
comandi dello stesso ecosistema.

**Skill `requirements` non invocabile da CLI.** Su `sertor-flow`, la skill `requirements`
(Sertor-authored) è resa come prompt-file (`.github/prompts/requirements.prompt.md`) anche per
`copilot-cli`. I prompt-file sono invocabili solo in VS Code, non dalla CLI. Il target
`copilot-cli` di `sertor` (FEAT-011) ha già risolto il problema per i comandi wiki rendendoli
custom-agent; solo `requirements` di `sertor-flow` è rimasto indietro. SpecKit 0.8.18 produce
già `speckit.*.agent.md`, quindi la superficie mancante è esclusivamente la skill `requirements`.

**Upstream spec-kit e mapping del nome.** `specify init` accetta `--ai copilot` (non
`copilot-cli`). Il nostro flag `--assistant copilot-cli` deve essere tradotto in `--ai copilot`
al momento del lancio; il mapping vive in un unico posto (`speckit_launch.py`).

Riferimenti al codice:
- `packages/sertor-install-kit/src/sertor_install_kit/assistant.py` — `AssistantId`,
  `AssistantProfile.for_assistant()` con la biforcazione `COPILOT` / `COPILOT_CLI`
- `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py` — `render_prompt_file`,
  `render_custom_agent`, `render_copilot_hooks`
- `packages/sertor-flow/src/sertor_flow/__main__.py` — `choices=["claude", "copilot"]` nel
  flag `--assistant`
- `packages/sertor-flow/src/sertor_flow/install_governance.py` — `_SERTOR_AUTHORED` con
  `(_SKILL_REQUIREMENTS, Surface.COMMAND, "skills/requirements/SKILL.md", "requirements")`
- `packages/sertor-flow/src/sertor_flow/speckit_launch.py` — `build_specify_command`,
  `_EXPECTED_LAYOUT`, `_SCRIPT_VALUE`
- `packages/sertor/src/sertor_installer/__main__.py` — `help="... | copilot (VS Code) | copilot-cli"`
- `docs/install-copilot.md` — documenta entrambi i target, usa `copilot` negli esempi

---

## 2. Obiettivi e criteri di successo

**CS-1 (target unico per la CLI Copilot):** a valle di questo refactor, `--assistant copilot-cli`
è il solo valore Copilot esposto dalla CLI di `sertor`, `sertor-flow` e `sertor-install-kit`. Il
valore `copilot` (VS Code) non è più raggiungibile tramite il flag in nessun pacchetto. Verificabile:
`sertor install rag --assistant copilot` restituisce un errore esplicito.

**CS-2 (naming uniforme):** `sertor` e `sertor-flow` espongono esattamente le stesse scelte
`claude|copilot-cli`; nessun pacchetto elenca `copilot` come valore valido. Verificabile:
`--help` di entrambi mostra `claude|copilot-cli`.

**CS-3 (skill `requirements` su CLI):** dopo l'installazione con `--assistant copilot-cli`,
la skill `requirements` di `sertor-flow` risulta in `.github/agents/requirements.agent.md`
(custom-agent), non come prompt-file; è invocabile dalla Copilot CLI. Verificabile:
`.github/prompts/requirements.prompt.md` non esiste; `.github/agents/requirements.agent.md` esiste.

**CS-4 (non-regressione Claude):** tutte le superfici installate con `--assistant claude` sono
invariate, sia per `sertor` sia per `sertor-flow`. Verificabile: la suite di test esistente
per Claude è verde senza modifiche ai test.

**CS-5 (mapping upstream corretto):** quando `sertor-flow` lancia `specify init` per
`copilot-cli`, la chiamata effettiva usa `--ai copilot` (il valore che spec-kit 0.8.18
riconosce). Verificabile: test unitario sul `build_specify_command` con
`assistant="copilot-cli"` → flag `--ai copilot` nella lista.

**CS-6 (documentazione allineata):** `docs/install-copilot.md` non menziona più il target
VS Code come opzione separata; un singolo percorso d'installazione per Copilot CLI.

---

## 3. Stakeholder e attori

- **Utente finale (ospite Copilot CLI):** installa Sertor su un repository e usa Copilot CLI;
  non deve trovarsi con superfici VS Code non funzionanti.
- **Maintainer Sertor:** mantiene un'unica base di codice senza due target Copilot paralleli
  da sincronizzare.
- **`sertor-install-kit`:** seam condiviso tra `sertor` e `sertor-flow`; le modifiche
  all'`AssistantId` si propagano a entrambi i consumatori.
- **spec-kit upstream (esterno):** accetta `--ai copilot`; il mapping interno da
  `copilot-cli` → `copilot` è responsabilità di Sertor.

---

## 4. Ambito

### In ambito

- Rimozione/disattivazione del target VS Code (`AssistantId.COPILOT`) come opzione CLI.
- Unificazione del naming: sia `sertor` sia `sertor-flow` espongono `claude|copilot-cli`.
- Resa della skill `requirements` come custom-agent su `copilot-cli` (in `sertor-flow`).
- Aggiornamento del mapping `_EXPECTED_LAYOUT` in `speckit_launch.py` per `copilot-cli`.
- Mapping `--ai copilot` (upstream) dal valore `copilot-cli` (nostro) in `speckit_launch.py`.
- Aggiornamento dei test esistenti per il target Copilot (VS Code → CLI-only).
- Aggiornamento di `docs/install-copilot.md` (e riferimenti in `docs/install.md`).
- Nota di migrazione per ospiti già installati con `--assistant copilot` (VS Code).
- Preservazione della non-regressione del target `claude`.

### Fuori ambito

- Cloud-agent / Codex (già Won't in FEAT-007).
- Nuovi assistenti (oltre `claude` e `copilot-cli`).
- Supporto VS Code come target futuro: non preclusivo, ma non in questo refactor.
- Comando `sertor-rag check` (follow-up FEAT-003).
- Retrocompat runtime per ospiti già installati con `--assistant copilot` (VS Code): al più
  nota di migrazione, non logica di rilevamento/migrazione automatica.
- Modifica al runtime di `sertor-core` (porte, adapter, composition invariati).

---

## 5. Requisiti funzionali (EARS)

### Gruppo A — Rimozione/disattivazione del target VS Code

**REQ-001 (Event-driven):** *When the user passes `--assistant copilot` to any `sertor` or
`sertor-flow` CLI command, the system shall reject the value with an explicit error message
naming `copilot-cli` as the correct Copilot value.*

**REQ-002 (Ubiquitous):** *The system shall not produce `.vscode/mcp.json` as an installation
artifact for any assistant target.*

**REQ-003 (Ubiquitous):** *The system shall not produce `.github/prompts/*.prompt.md` as an
installation artifact for the `copilot-cli` assistant target.*

**REQ-004 (Ubiquitous):** *The `AssistantId` enumeration shall NOT contain a `COPILOT` (VS Code)
value at all (Q1=a, full removal): its profile and all VS-Code-specific rendering branches
(`.vscode/mcp.json`, `servers` root-key, prompt-file as COMMAND vehicle) are deleted from the kit.*

### Gruppo B — Naming uniforme `copilot-cli`

**REQ-005 (Ubiquitous):** *The `sertor install` command shall accept exactly `claude` and
`copilot-cli` as valid values for the `--assistant` flag; all other values shall produce an
explicit error.*

**REQ-006 (Ubiquitous):** *The `sertor-flow install`, `sertor-flow upgrade`, and
`sertor-flow uninstall` commands shall accept exactly `claude` and `copilot-cli` as valid
values for the `--assistant` flag; all other values shall produce an explicit error.*

**REQ-007 (Ubiquitous):** *The `sertor upgrade` and `sertor uninstall` commands shall accept
exactly `claude` and `copilot-cli` as valid values for the `--assistant` flag; all other values
shall produce an explicit error.*

**REQ-008 (Ubiquitous):** *After the removal of `COPILOT` (Q1=a), the
`AssistantProfile.for_assistant()` factory shall resolve the `copilot-cli` profile to
`.mcp.json` (root-key `mcpServers`) for the MCP surface and to `.github/**` for all other
surfaces, and shall raise on the (now-unknown) `copilot` value.*

### Gruppo C — Skill `requirements` come custom-agent su `copilot-cli`

**REQ-009 (Event-driven):** *When `sertor-flow install --assistant copilot-cli` is executed,
the system shall deposit the `requirements` skill as a custom-agent file at
`.github/agents/requirements.agent.md`.*

**REQ-010 (Event-driven):** *When `sertor-flow install --assistant copilot-cli` is executed,
the system shall NOT produce a prompt-file at `.github/prompts/requirements.prompt.md`.*

**REQ-011 (Ubiquitous):** *The `requirements` skill custom-agent for `copilot-cli` shall be
derived from the same canonical Claude asset as all other Sertor-authored surfaces (anti-drift
via `render_custom_agent`), with no separately maintained copy.*

**REQ-012 (Ubiquitous):** *The `CommandVehicle` for the `COMMAND` surface on the `copilot-cli`
profile shall be `CUSTOM_AGENT`.*

### Gruppo D — Mapping upstream spec-kit

**REQ-013 (Event-driven):** *When `sertor-flow install --assistant copilot-cli` launches
`specify init`, the system shall pass `--ai copilot` (the upstream value recognized by
spec-kit 0.8.18) in the command.*

**REQ-014 (Ubiquitous):** *The expected layout verification after `specify init` for the
`copilot-cli` target shall check for `.github/agents/` markers consistent with the Copilot
assistant layout (not a `copilot-cli`-specific key that spec-kit does not produce).*

**REQ-015 (Ubiquitous):** *The mapping from the `copilot-cli` assistant value to the upstream
`--ai` argument shall reside in a single location and be explicitly documented.*

### Gruppo E — Non-regressione Claude e test

**REQ-016 (Ubiquitous):** *The system shall produce identical artifacts for `--assistant claude`
before and after this refactor; no Claude-targeted test shall require modification.*

**REQ-017 (Ubiquitous):** *The existing test suite for `copilot-cli` (RAG, wiki, hooks) shall
continue to pass without requiring changes to the test logic targeting `copilot-cli`.*

**REQ-018 (Event-driven):** *When the test suite for the former `copilot` (VS Code) target is
updated, the system shall provide equivalent coverage for `copilot-cli` in its place, so that
no surface is left untested.*

**REQ-019 (Ubiquitous):** *The guard tests (`test_assets_copilot_guard.py`) shall verify
assets for `copilot-cli` only; references to the VS Code profile shall be removed from the
guard scope.*

### Gruppo F — Documentazione e migrazione

**REQ-020 (Ubiquitous):** *The `docs/install-copilot.md` file shall describe a single
installation path for Copilot, using `--assistant copilot-cli` throughout, with no VS Code
target section or `--assistant copilot` examples.*

**REQ-021 (Ubiquitous):** *The `docs/install.md` reference documentation shall list
`claude|copilot-cli` as the complete set of valid `--assistant` values, removing `copilot`
(VS Code).*

**REQ-022 (Ubiquitous):** *The system shall include a migration note (inline in the install
documentation or as a separate section) for users who previously ran
`sertor install ... --assistant copilot`, explaining that the target has been consolidated
into `copilot-cli` and that re-running install with `--assistant copilot-cli` on the same
host is the upgrade path.*

---

## 6. Requisiti non funzionali

**NFR-01 (Non-distruttività):** il refactor non introduce modifiche ai file depositati su
ospiti già installati con `--assistant copilot-cli`; solo il codice Sertor e la documentazione
cambiano.

**NFR-02 (Backward-incompatibilità esplicita):** la rimozione del valore `copilot` è una
breaking change voluta e deve produrre un errore esplicito e azionabile (exit 1, messaggio che
nomina `copilot-cli`), non un comportamento silenzioso.

**NFR-03 (Invarianza del core):** nessuna modifica a `sertor-core` (porte, adapter,
composition root, `sertor-rag`); il refactor è confinato ai pacchetti `sertor`,
`sertor-flow`, `sertor-install-kit`.

**NFR-04 (Anti-drift):** le superfici Copilot CLI restano derivate da una sorgente canonica
unica (`assets/claude/**`); nessuna copia mantenuta separatamente per il target `copilot-cli`.

**NFR-05 (Testabilità offline):** i nuovi test per `copilot-cli` (in sostituzione di quelli VS
Code) non richiedono accesso a una rete o a un client Copilot reale; usano `FakeCommandRunner`
/ `FakeSpecifyRunner` come i test esistenti.

**NFR-06 (Idempotenza preservata):** `sertor-flow install --assistant copilot-cli` eseguito
due volte sullo stesso ospite produce il medesimo risultato della seconda chiamata (nessun
artefatto duplicato, nessuna sovrascrittura non-deterministica).

---

## 7. Vincoli, assunzioni e dipendenze

**VIN-01 (spec-kit upstream):** spec-kit 0.8.18 accetta `--ai copilot`, non `--ai copilot-cli`.
Il mapping è interno a Sertor e non richiede una modifica upstream. [ASSUNTO: questo rimarrà
vero anche nelle versioni pinned future, fino a una revisione esplicita — vedi Q2.]

**VIN-02 (AssistantId come enum condiviso):** `AssistantId` vive in `sertor-install-kit` ed è
condiviso tra `sertor` e `sertor-flow`. La modifica al seam si propaga ad entrambi i
consumatori automaticamente; la consistenza è garantita dal fatto che entrambi importano lo
stesso tipo.

**VIN-03 (assets/claude/ come sorgente unica):** tutti i file Copilot CLI devono restare
derivati dalla sorgente canonica Claude via `render_custom_agent` / `render_copilot_hooks`;
non si introducono asset separati per `copilot-cli`.

**VIN-04 (stdlib-only nel kit):** `sertor-install-kit` non dipende da `sertor-core`; le
modifiche al seam devono restare stdlib-only.

**VIN-05 (Principio X — host-agnostico):** il target assistant è una configurazione, non una
presunzione nel corpo dei plan-builder; `AssistantProfile.for_assistant()` rimane l'unico
punto che conosce le convenzioni per-assistente.

**VIN-06 (install ≠ run):** nessuna modifica al principio; l'installer deposita artefatti e
non avvia indicizzazione.

[ASSUNTO: il target `copilot-cli` copre il 100% degli utenti Copilot che oggi usano Sertor;
non esiste un caso d'uso validato dell'integrazione VS Code che giustifichi il mantenimento
di `copilot` (VS Code) come target. Se emergesse, sarebbe una nuova feature separata.]

---

## 8. Rischi

**R-01 — Rottura silente per ospiti VS Code esistenti.** Ospiti che hanno installato con
`--assistant copilot` (VS Code) hanno `.vscode/mcp.json` sul disco. Dopo il refactor,
`sertor upgrade --assistant copilot` restituisce errore. La mitigazione è la nota di
migrazione (REQ-022) e l'errore esplicito (REQ-001), non una logica di migrazione automatica.
*Probabilità: bassa (target VS Code mai validato su client reale; uso reale probabilmente nullo).
Impatto: basso.*

**R-02 — Mapping `copilot-cli` → `copilot` (upstream) dimentica un punto di chiamata.**
Se `speckit_launch.py` non è l'unico posto che forma la stringa `--ai <assistant>`, il mapping
potrebbe essere incompleto. La mitigazione è REQ-015 (mapping in un solo posto) e test
esplicito su `build_specify_command` (REQ-013/CS-5). *Probabilità: bassa se si verifica
completezza. Impatto: medio (SpecKit non viene lanciato per CLI).*

**R-03 — Test VS Code eliminati senza equivalente CLI.** Se i test di accettazione per
`--assistant copilot` (VS Code) vengono rimossi senza rimpiazzo `copilot-cli`, una superficie
resta incopertura. La mitigazione è REQ-018 (copertura equivalente obbligatoria).
*Probabilità: media (facile da dimenticare in un refactor). Impatto: medio.*

**R-04 — `GovernanceProfile` e `_EXPECTED_LAYOUT` non aggiornati per `copilot-cli`.**
L'idempotency check di `launch_speckit` usa `_EXPECTED_LAYOUT["copilot"]`; se non si aggiunge
una chiave per `copilot-cli`, l'idempotenza fallisce (layout mai trovato, SpecKit rilancia
ogni volta). La mitigazione è REQ-014 e test esplicito.
*Probabilità: alta (layout check usa una chiave stringa). Impatto: medio.*

---

## 9. Prioritizzazione (MoSCoW)

| ID | Requisito | Priorità | Note |
|----|-----------|----------|------|
| REQ-001 | Errore esplicito su `--assistant copilot` | **Must** | Comportamento breaking-change obbligatorio |
| REQ-002 | Nessun `.vscode/mcp.json` prodotto | **Must** | Rimozione dell'artefatto VS Code |
| REQ-003 | Nessun prompt-file per `copilot-cli` | **Must** | Coerente con FEAT-011 già consegnato |
| REQ-004 | `AssistantId.COPILOT` rimosso del tutto dall'enum | **Must** | Q1=a (rimozione totale) |
| REQ-005 | `sertor --assistant` accetta solo `claude|copilot-cli` | **Must** | |
| REQ-006 | `sertor-flow --assistant` accetta solo `claude|copilot-cli` | **Must** | Oggi accetta `copilot` |
| REQ-007 | `sertor upgrade/uninstall` coerente | **Must** | |
| REQ-008 | `AssistantProfile` per `copilot-cli` invariato | **Must** | Già corretto, solo verifica |
| REQ-009 | `requirements` come custom-agent su `copilot-cli` | **Must** | Invocabilità dalla CLI |
| REQ-010 | Nessun prompt-file `requirements` per `copilot-cli` | **Must** | Speculare a REQ-009 |
| REQ-011 | Anti-drift: sorgente canonica unica | **Must** | Principio architetturale |
| REQ-012 | `CommandVehicle.CUSTOM_AGENT` per `copilot-cli` COMMAND | **Must** | Già così oggi; conferma |
| REQ-013 | `specify init --ai copilot` per `copilot-cli` | **Must** | Mapping upstream |
| REQ-014 | Layout check per `copilot-cli` corretto | **Must** | Idempotenza |
| REQ-015 | Mapping in un unico posto documentato | **Must** | |
| REQ-016 | Non-regressione Claude | **Must** | Invariante assoluto |
| REQ-017 | Test `copilot-cli` esistenti verdi | **Must** | |
| REQ-018 | Copertura equivalente (ex VS Code → CLI) | **Must** | |
| REQ-019 | Guard test aggiornati per `copilot-cli` | **Should** | |
| REQ-020 | `docs/install-copilot.md` aggiornato | **Should** | |
| REQ-021 | `docs/install.md` aggiornato | **Should** | |
| REQ-022 | Nota di migrazione per ex utenti VS Code | **Could** | Uso reale probabile nullo |

---

## 10. Domande aperte — RISOLTE (2026-06-17)

Tutte chiuse con l'utente: **Q1 (a)** rimozione totale `AssistantId.COPILOT` · **Q2** mapping
`copilot-cli → --ai copilot` confermato (un solo punto, documentato) · **Q3 (a)** solo nota di
migrazione (cleanup manuale; niente rilevamento automatico — opzione b/c scartate) · **Q4 (a)**
rinomina diretta `copilot → copilot-cli` in `sertor-flow`. Contesto originale sotto.

**Q1 — Rimozione vs deprecazione di `AssistantId.COPILOT` (impatto: alto)**

Oggi `AssistantId.COPILOT` è un valore dell'enum con il profilo VS Code completo
(`packages/sertor-install-kit/src/sertor_install_kit/assistant.py`, righe 156-176).

*Opzione (a) — Rimozione totale:* `AssistantId.COPILOT` viene eliminato dall'enum. Il seam
del kit non ha più traccia del profilo VS Code. Vantaggio: pulizia completa, nessun codice
morto. Rischio: se in futuro si vuole aggiungere il target VS Code, va ricostruito da zero.

*Opzione (b) — Nascondere senza rimuovere:* `AssistantId.COPILOT` resta come valore interno
dell'enum ma non è più esposto come scelta valida nella CLI (`from_str` lo rifiuta; non è
nelle `choices`). Vantaggio: la logica VS Code è conservata senza essere esponibile.
Rischio: codice raggiungibile ma non testato → rottura silenziosa a valle.

*Raccomandazione:* se non esiste alcun piano concreto per VS Code nel backlog, preferire la
**(a) rimozione** per evitare codice morto non testato. Se VS Code è previsto nel Could/futuro,
preferire **(b)** con test espliciti di validità del profilo nascosto.

---

**Q2 — Stabilità del mapping `copilot-cli` → `--ai copilot` (upstream) (impatto: medio)**

Oggi spec-kit 0.8.18 non ha un valore `--ai copilot-cli`; il nostro flag interno `copilot-cli`
deve essere tradotto in `--ai copilot` al lancio (`speckit_launch.py:build_specify_command`).

Occorre confermare: (a) il mapping `copilot-cli` → `copilot` (upstream) è la scelta corretta
oggi; (b) la policy per le versioni future di spec-kit pinnate (se spec-kit aggiunge
`--ai copilot-cli`, il mapping va aggiornato in quel punto); (c) il mapping deve comparire in
un solo posto con commento esplicito (REQ-015).

*Raccomandazione:* confermare il mapping `copilot-cli` → `copilot` (upstream) come decisione
progettuale esplicita, documentata nel sorgente e nel commento inline di `_SCRIPT_VALUE` o di
una nuova map `_SPECKIT_AI_FLAG`.

---

**Q3 — Retrocompat per ospiti già installati con `--assistant copilot` (VS Code)
(impatto: basso)**

Un ospite che ha eseguito `sertor install rag --assistant copilot` ha `.vscode/mcp.json` sul
disco. Dopo il refactor, `sertor upgrade --assistant copilot` fallisce con REQ-001.

Opzioni: (a) solo nota di migrazione in `docs/install-copilot.md` (REQ-022) — l'utente ri-esegue
manualmente con `copilot-cli`; (b) logica di rilevamento: se esiste `.vscode/mcp.json` Sertor,
proporre la migrazione automatica; (c) fuori ambito, l'utente esegue `uninstall` manuale.

*Raccomandazione:* dato che il target VS Code non è mai stato validato su client reale e l'uso
effettivo è probabilmente nullo, l'**(a) solo nota di migrazione** è sufficiente e meno
rischiosa delle logiche di rilevamento automatico. Confermare che la retrocompat automatica
(b) è fuori ambito.

---

**Q4 — `copilot-cli` in `sertor-flow`: aggiungere o rinominare? (impatto: medio)**

`sertor-flow` oggi ha `choices=["claude", "copilot"]`. L'opzione `copilot` punta al profilo VS
Code (`.github/prompts/` per COMMAND).

*Opzione (a) — Rinomina `copilot` → `copilot-cli` con cambio del profilo interno:* il valore
stringa `"copilot"` nel parser diventa `"copilot-cli"`, il profilo risolve COMMAND come
custom-agent. Semplice, un solo valore Copilot.

*Opzione (b) — Aggiunge `copilot-cli` e depreca `copilot`:* si aggiunge il nuovo valore
mantenendo il vecchio temporaneamente con un avviso. Più cauta ma introduce transitorio.

*Raccomandazione:* data la decisione di mandare a CLI-only, preferire la **(a) rinomina
diretta** senza transitorio: la breaking change è voluta e documentata (REQ-001). Non c'è
valore in un periodo di deprecazione se l'uso VS Code è zero.
