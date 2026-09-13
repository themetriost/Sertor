# Tasks — Il server MCP funziona su entrambe le linee dell'SDK

**Feature**: `128-porting-mcp-sdk-v2` · **Data**: 2026-09-13
**Design**: [plan.md](./plan.md) · [research.md](./research.md) · [data-model.md](./data-model.md) ·
[contracts/](./contracts/) · [quickstart.md](./quickstart.md)

**I test sono richiesti** da questa feature, non opzionali: FR-007 (verifica sul protocollo), FR-012
(esecuzione su entrambe le linee) e SC-004 sono requisiti, e la loro assenza è ciò che ha permesso a una
conclusione sbagliata di entrare nel backlog.

---

## Phase 1 — Setup

- [X] T001 Verificare che l'ambiente possa risolvere entrambe le linee dell'SDK, eseguendo `uv run --with "mcp==2.2.0" --no-project python -c "import mcp.server"` e `uv run --with "mcp==1.29.0" --no-project python -c "import mcp.server.fastmcp"` dalla radice del repo — se una delle due fallisce, il lavoro successivo non è verificabile e va risolto prima
- [X] T002 Annotare in `specs/128-porting-mcp-sdk-v2/research.md`, sezione *Perimetro del non misurato*, la versione esatta di `mcp` risolta dal lock del workspace al momento dell'inizio lavori (`uv run python -c "from importlib.metadata import version; print(version('mcp'))"`), così il confronto «prima/dopo» resta leggibile

---

## Phase 2 — Foundational (blocca tutte le user story)

- [X] T003 Creare `src/sertor_mcp/_sdk.py` che esporta esattamente i tre nomi del contratto (`ServerClass`, `ToolError`, `SDK_LINE`): tenta prima la linea v2 (`from mcp.server import MCPServer`, `from mcp.server.mcpserver.exceptions import ToolError`), poi la v1 (`from mcp.server.fastmcp import FastMCP`, `from mcp.server.fastmcp.exceptions import ToolError`); `SDK_LINE` è **derivato** dal ramo riuscito, mai dichiarato — vedi [`contracts/sdk-compat.md`](./contracts/sdk-compat.md)
- [X] T004 In `src/sertor_mcp/_sdk.py`, se nessuna linea è importabile sollevare un errore che nomina **la versione installata** (da `importlib.metadata`) e **l'intervallo supportato**, invece di lasciar propagare il `ModuleNotFoundError` su un sottomodulo interno (FR-003) — è il messaggio illeggibile con cui il guasto si è manifestato agli ospiti
- [X] T005 In `src/sertor_mcp/_sdk.py`, scrivere il commento d'intenzione: perché esistono due linee, cosa succede quando la prossima major arriva, e che **questo modulo è pensato per essere cancellato** quando la 1.x sarà abbandonata (Principio VII: il commento dice l'intenzione, non la meccanica)
- [X] T006 Creare `tests/unit/test_sdk_compat.py` e il test che i tre nomi del contratto esistono e sono usabili sulla linea corrente (`ServerClass` costruibile, `ToolError` sollevabile, `SDK_LINE` valorizzato)
- [X] T006a [P] In `tests/unit/test_sdk_compat.py`, il test che `SDK_LINE` combacia con la linea **realmente importata**, leggendola dal modulo della classe ottenuta e non da una costante — è il test che T021 usa per rendere non-vuoto il passo CI, quindi ha un ID proprio
- [X] T006b [P] In `tests/unit/test_sdk_compat.py`, il test che il fallimento d'import nomina versione installata e intervallo supportato, simulando l'assenza di entrambe le linee (FR-003)
- [X] T006c [P] In `tests/unit/test_sdk_compat.py`, la verifica testuale che `src/sertor_mcp/server.py` **non contenga** le stringhe `fastmcp` né `mcpserver`: l'invariante che dice se il layer sta facendo il suo lavoro o se è stato aggirato
- [X] T006d Creare `tests/contract/__init__.py` (la cartella `tests/contract/` **non esiste**: verificato in fase `analyze`; le sorelle `unit/` e `integration/` hanno il proprio `__init__.py`)

---

## Phase 3 — User Story 1 (P1): l'ospite già colpito riottiene i suoi tool

**Obiettivo:** su un ambiente che ha risolto la major 2.x, il server parte e serve i dieci tool.
**Test indipendente:** in un venv con `mcp==2.2.0`, il server completa l'handshake e dichiara dieci tool.

- [X] T007 [US1] In `src/sertor_mcp/server.py:25`, sostituire l'import diretto dell'SDK con l'import dal layer (`from ._sdk import ServerClass, ToolError`), lasciando il resto degli import invariato
- [X] T008 [US1] In `src/sertor_mcp/server.py:112`, istanziare `ServerClass(...)` al posto di `FastMCP(...)`, senza toccare `instructions=` né i dieci decoratori `@mcp.tool` (misurato: reggono invariati su entrambe le linee)
- [X] T009 [P] [US1] Creare `tests/contract/test_mcp_protocol_e2e.py` che lancia il server **come processo** (`python -m sertor_mcp.server`) e vi si connette con un client MCP reale sul transport stdio, asserendo: handshake completato, `instructions` non vuote, **dieci** tool con i nomi attesi, e il payload di un tool `list[dict]` nella forma `{"result": [...]}` — il server si esercita come lo esercita un client, non importandone le funzioni (Principio XI)
- [X] T010 [P] [US1] In `pyproject.toml`, portare il vincolo a `mcp>=1.2,<2.3` in **entrambi** i punti (extra `mcp` a `:52` e extra `dev` a `:91`), con un commento che nomina la versione misurata (`2.2.0`, 2026-09-13), la ragione del limite superiore e la condizione per alzarlo, citando **E10-FEAT-071** come riconciliatore (Principio XIV)
- [X] T011 [US1] Rigenerare `uv.lock` (`uv lock`) e verificare che la versione risolta di `mcp` sia coerente col nuovo intervallo, riportando il valore prima/dopo
- [X] T012 [US1] Estendere `tests/integration/test_host_smoke.py` con il settimo esito richiesto per nome `mcp-server-imports`, aggiungendolo alla tupla `required` accanto ai sei esistenti (`pin-moved`, `host-config-preserved`, `mcp-invocation-shape`, `no-stale-divergence`, `version-derived-from-runtime`, `health-green`)
- [X] T013 [US1] In `scripts/smoke.ps1` e `scripts/smoke.sh`, per il percorso di **upgrade**: piantare la condizione dell'ospite colpito (forzare il runtime dell'host a risolvere `mcp` 2.x **prima** dell'upgrade), asserire che in quello stato l'import del server **fallisca**, eseguire l'upgrade, e asserire che l'import **riesca** — stampando `OK   mcp-server-imports`. Senza l'asserzione «prima falliva» l'esito passa gratis (R-4)
- [X] T014 [US4] Negli stessi due script, per il percorso di **installazione** (non upgrade): asserire l'import del server dopo l'installazione. *Sta in questa fase per prossimità di file (gli stessi due script di T013), ma realizza **US4** — dipendenza dichiarata in fase `analyze` invece di essere lasciata implicita.* Serve perché `doctor` resta verde con il server morto (E10-FEAT-072) e `search` passa dalla CLI: **oggi nessuno dei quattro smoke d'installazione vedrebbe un server che non parte**

---

## Phase 4 — User Story 2 (P1): un guasto previsto dice all'agente cosa è rotto

**Obiettivo:** la diagnosi di un guasto previsto raggiunge il client su entrambe le linee.
**Test indipendente:** si provoca un indice assente e si legge il contenuto dell'esito d'errore.

- [X] T015 [US2] In `src/sertor_mcp/server.py`, dentro `_guard` (`:210`): se l'eccezione è un `SertorError` (import dal dominio), registrare l'evento come oggi e sollevare `ToolError(str(exc))`; **ogni altra eccezione resta ri-sollevata invariata**. La discriminazione è per tipo (`isinstance`), mai sul testo del messaggio
- [X] T016 [US2] Aggiornare il docstring di `_guard`: oggi dichiara che «the exception still reaches the MCP client unchanged», che dopo questa modifica è **falso**. Il nuovo testo distingue le due classi e spiega perché (l'SDK v2 trattiene il testo dei crash *by design*), citando la decisione D-1
- [X] T017 [P] [US2] In `tests/contract/test_mcp_protocol_e2e.py`, aggiungere la verifica del **contenuto diagnostico**: un tool che incontra un guasto previsto produce `isError=true` e un contenuto che **nomina la causa**, non solo il tool — vedi la tabella normativa di [`contracts/tool-error-surface.md`](./contracts/tool-error-surface.md). ⚠️ **La condizione va provocata in modo deterministico, e il default NON basta:** il motore predefinito (`hybrid`) è **tollerante** — indice assente → `[]` + warning, nessuna eccezione — mentre `IndexNotFoundError` lo solleva il motore **strict** (`engines/baseline.py`). Il test deve quindi lanciare il server con `SERTOR_ENGINE=baseline` e un corpus senza indice, **oppure** iniettare un `SertorError` da un doppio del core; la scelta va dichiarata nel docstring del test. *(Senza questa precisazione il test asserirebbe una diagnosi che la configurazione di default non produce — trovato in fase `analyze`.)*
- [X] T018 [P] [US2] In `tests/unit/test_mcp_server.py`, aggiungere due test per la mappatura: (a) un `SertorError` sollevato dal core diventa un `ToolError` con il messaggio d'origine preservato **e** l'evento `mcp.<tool>.error` registrato; (b) un'eccezione qualsiasi **non** viene convertita (resta il tipo originale), così la scelta di R-2 è presidiata e non solo documentata
- [X] T019 [US2] Eseguire i quattro test esistenti che asseriscono il re-raise (`test_tool_error_emits_event_and_reraises`, `test_combined_tool_error_emits_event_and_reraises`, `test_tool_error_detail_is_secret_scrubbed`, `test_internal_error_propagates_then_server_recovers`) e **confermare che passano invariati** — R-2 prevede che sollevino `RuntimeError`, che non è un `SertorError`. Se uno fallisse, la mappatura è più larga di quanto deciso: correggere il codice, **non** il test

---

## Phase 5 — User Story 3 (P2): il ramo di compatibilità non marcisce

**Obiettivo:** entrambe le linee sono esercitate da una verifica automatica.
**Test indipendente:** si esegue la verifica in due ambienti e si controlla che *entrambe* le esecuzioni siano avvenute.

- [X] T019b [US2] Eseguire per **nome** gli 11 test che R-3 nomina come presidio di FR-008 (`test_main_warms_facade_before_stdio_loop`, `test_main_starts_server_even_if_warmup_fails`, `test_main_runs_self_test_before_stdio_loop`, `test_self_test_ok_on_healthy_facade`, `test_self_test_is_loud_and_nonfatal_on_failure`) e di FR-009 (`test_main_wires_observability`, `test_tool_error_emits_event_and_reraises`, `test_combined_tool_error_emits_event_and_reraises`, `test_tool_error_detail_is_secret_scrubbed`, `test_memory_search_does_not_log_query_in_clear`, `test_memory_search_semantic_does_not_log_query_in_clear`) e riportarne l'esito. *Senza questo task i due requisiti erano coperti solo dal gate complessivo, cioè indistinguibili da requisiti non verificati (trovato in fase `analyze`).*

---

- [X] T020 [US3] In `.github/workflows/ci.yml`, aggiungere al job di test un passo che ri-esegue **solo** i test che toccano `sertor_mcp` con l'altra linea dell'SDK installata, usando `uv run --with "mcp==<altra linea>" --no-project pytest …` così che il lock del workspace **non** si sposti (R-5)
- [X] T021 [US3] Nello stesso passo, far girare **per primo** il test che asserisce `SDK_LINE` (**T006a**): se l'ambiente non ha davvero cambiato linea, il passo deve diventare **rosso** invece di essere verde e vuoto. Un passo che installa l'altra linea senza verificare quale sia attiva è indistinguibile da un passo che non ha cambiato nulla
- [X] T022 [P] [US3] Aggiungere al passo un commento che spiega **perché** esiste: il ramo di fallback introdotto da `_sdk.py` non viene attraversato da nessuna esecuzione se la CI gira su una linea sola, e un ramo non attraversato si rompe in silenzio (R-1 della spec, decisione D-3)
- [X] T023 [US3] Verificare che i sei file di test che importano `sertor_mcp` passino sull'altra linea: `tests/unit/test_mcp_server.py`, `test_mcp_graph_tools.py`, `test_mcp_combined_graph.py`, `test_score_contract.py`, `test_doctor.py`, `test_single_venv_guard.py`. Ogni fallimento è un fatto sul porting, non un test da adattare

---

## Phase 6 — User Story 4 (P3): chi installa oggi ottiene un server funzionante

**Obiettivo:** un'installazione da zero produce un server che parte, e l'ospite sa quali versioni sono supportate.
**Test indipendente:** installazione su host pulito, verifica dell'import del server; lettura della doc utente.

- [X] T024 [US4] Riscrivere la sezione di `docs/troubleshooting.md` (righe ~121-144) che oggi descrive il guasto `No module named 'mcp.server.fastmcp'` e prescrive come conviverci: dopo questa feature quel rimedio è **obsoleto**. La sezione nuova dichiara l'intervallo supportato, dice che entrambe le linee funzionano, e indica l'azione per un ospite **già colpito** (aggiornare Sertor, senza toccare il proprio lock) — FR-011, e la regola standing «una modifica al setup non è done finché la doc utente non è aggiornata»
- [X] T025 [P] [US4] Verificare la tabella delle capability in `packages/sertor/docs/install.md` e i quick-start per-assistente: se dichiarano qualcosa sul server MCP o sulle versioni dell'SDK, allinearli; se non ne parlano, **dichiararlo qui** invece di presumere che vada bene

---

## Phase 7 — Polish & cross-cutting

- [X] T026 Eseguire il gate pre-merge completo: le **sette** suite (`pytest -m "not cloud"` alla radice · `packages/sertor/tests` senza `hooks_smoke` · `packages/sertor/tests -m hooks_smoke` **col percorso**, altrimenti deseleziona tutto ed esce 0 · install-kit · flow · speclift · specaudit) più `ruff check .`
- [X] T027 Aggiornare lo **stato di E10-FEAT-070** in `requirements/debito-tecnico/epic.md` con l'esito reale e i valori finali dei criteri SC-001..SC-007, e citare **E10-FEAT-076** (fuori ambito) come ancora aperta
- [X] T028 Aggiornare il blocco EXEC di `wiki/syntheses/roadmap.md`: la voce del blocco rosso passa da «da fare adesso» a consegnata, **e resta aperta la parte di consegna** — la release che porta il porting agli ospiti e la risposta in bacheca, che non sono soddisfatte dal merge
- [ ] T029 Chiudere il rituale di step: `record` delegato al `wiki-curator`, `distill` con verdetto dichiarato, lint semantico contro ciò che è cambiato (in particolare le pagine che citano il tetto come rimedio corrente)
- [X] T030 Verificare che il perimetro del **non misurato** sia ancora dichiarato dove si legge, dopo l'implementazione: cancellazione, timeout, payload grandi, concorrenza. Se l'implementazione ne ha misurato qualcuno per caso, spostarlo fra i misurati; se no, lasciarlo dichiarato — non silenziarlo

---

## Dipendenze fra le fasi

```
Phase 1 (setup)
   └─> Phase 2 (_sdk.py)  ← BLOCCA tutto: ogni user story importa da qui
         ├─> Phase 3 (US1) ── il porting vero + le misure su host
         │     └─> Phase 4 (US2) ── dipende da T007/T008: `ToolError` arriva dal layer
         ├─> Phase 5 (US3) ── indipendente da US2, dipende da T006b per l'asserzione su SDK_LINE
         └─> Phase 6 (US4) ── indipendente: doc utente
                └─> Phase 7 (polish) ── gate, backlog, wiki
```

**US1 e US2 sono entrambe P1 ma non sono intercambiabili:** US1 fa partire il server (senza di essa non
c'è niente da diagnosticare), US2 rende utile ciò che dice quando fallisce. Consegnare solo US1 darebbe un
server che funziona e, su v2, tace quando si rompe — accettabile come stato intermedio di un branch, **non**
come consegna.

## Opportunità di parallelismo

- **Dentro US1:** T009 (test e2e), T010 (vincolo) sono indipendenti fra loro e da T007/T008.
- **Dentro US2:** T017 (contract) e T018 (unit) sono su file diversi.
- **Fra story:** US3 (CI) e US4 (doc) non si toccano e possono procedere in parallelo a US1/US2 una volta
  chiusa la Phase 2.
- **Non parallelizzabili:** T007→T008 (stesso file, stesse righe), T012→T013→T014 (stessi script),
  T003→T004→T005 (stesso file nuovo).

## MVP e consegna incrementale

**MVP = Phase 2 + Phase 3 (US1) + Phase 4 (US2).** È il minimo che chiude il danno in essere: il server
parte su entrambe le linee **e** dice cosa è rotto quando si rompe.

**Perché US3 non è nell'MVP ma non è opzionale:** senza di essa il porting funziona *oggi* e nessuno sa
quando smetterà. È la differenza fra riparare e rendere improbabile che si riguasti — e va nella stessa PR,
non «dopo».

**Ciò che il merge NON chiude, e va detto al momento della consegna:** gli ospiti agganciati a una versione
pubblicata non ricevono nulla finché non esce una release, e due nodi aspettano da undici giorni la risposta
alla domanda che hanno posto in bacheca. Sono attività di consegna (T028 le tiene visibili), non task di
implementazione.
