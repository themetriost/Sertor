# Requisiti — `sertor-rag doctor` (verifica di salute deterministica)
<!-- Deriva da: FEAT-001 (epica usabilità) -->

## 1. Contesto e problema (perché)

Dopo il setup non esiste un modo **deterministico** per rispondere a *«ha funzionato?»*. Il probe
`--check` del wizard `sertor configure` è rimasto *deferred* proprio perché manca la primitiva che
dovrebbe invocare. Gli strumenti di stato esistono ma sono **sparsi** (`eval validate-path` per
l'indice, `validate_backend()` per i segreti, il self-test del server MCP, gli eventi di
osservabilità) e nessuno dà un quadro unico e azionabile. Conseguenza: l'utente scopre i problemi
solo quando un comando d'uso fallisce, con errori non sempre correlati alla causa.

`sertor-rag doctor` è la **primitiva deterministica** che mancava: un comando-vehicle (Principio XI)
che fotografa lo stato di salute dell'installazione e dice **cosa manca e come rimediare**. È il
substrato su cui poggiano le skill agentiche di usabilità (guided-setup, search-diagnose) e il modo
in cui il wizard chiude finalmente il suo `--check`.

## 2. Obiettivi e criteri di successo
- **CS-1:** un singolo comando riporta lo stato di **quattro aree** — *configurazione/env*,
  *provider di embeddings*, *indice* (presenza + freschezza), *server MCP* — con esito per-area.
- **CS-2:** l'output è **azionabile**: per ogni problema nomina la causa e il rimedio concreto (chiave
  mancante, provider non raggiungibile, indice assente/stantio, MCP non registrato).
- **CS-3:** esito **machine-readable** (`--json`) oltre che umano, così le skill lo consumano.
- **CS-4:** **exit code** non-zero se almeno un check critico fallisce (gate per script/CI/skill).
- **CS-5:** i check **statici** (env, presenza indice) funzionano **offline**; i check che richiedono
  rete (raggiungibilità provider) sono chiaramente distinti e degradano onestamente se offline.
- **CS-6:** **nessun segreto** nell'output (umano o JSON); host-agnostico (gira su qualunque ospite).

## 3. Stakeholder e attori
- **Utente / chi installa:** vuole sapere se l'installazione è sana prima di usarla.
- **Skill di usabilità** (guided-setup, search-diagnose) e **wizard `configure --check`:** consumatori
  primari dell'esito strutturato.
- **CI / script:** usano l'exit code come gate.
- **Il core/vehicle:** sorgente deterministica dei segnali (config, manifest dell'indice, store, MCP).

## 4. Ambito

### In ambito
- Un sottocomando **`sertor-rag doctor`** (vehicle CLI), reso umano + `--json`.
- Check delle quattro aree: **env/config**, **provider embeddings**, **indice** (presenza+freschezza),
  **server MCP** (registrato/raggiungibile).
- Riuso dei segnali esistenti: `Settings.validate_backend()` (campi mancanti), manifest/`index_dir`
  (presenza + `mtime`/freschezza), eventuale probe minimale del provider, stato MCP.
- Granularità: un comando con esito strutturato per-area; flag opzionali per selezionare/saltare i
  check che richiedono rete (DA-D1).
- Chiude il debito `--check` (US5) di `sertor-cli`/FEAT-003: `configure --check` invoca questo comando.

### Fuori ambito
- **Auto-fix:** il comando **diagnostica**, non ripara (la riparazione guidata è la skill guided-setup).
- **Spiegazione conversazionale** dell'esito: è la skill (l'agente), non il comando.
- **Qualsiasi chiamata a un LLM** (Principio D↔N): il comando è puramente deterministico.
- Probe pesanti/onerosi (es. indicizzazione di prova): il probe provider resta **minimale**.

## 5. Requisiti funzionali (EARS)
- **REQ-001 (Event-driven):** *When `sertor-rag doctor` is invoked, the system shall report the health
  of four areas — configuration/env, embeddings provider, index (presence + freshness), MCP server —
  with a per-area pass/warn/fail outcome.*
- **REQ-002 (Unwanted):** *If a required configuration value for the selected provider/store is missing,
  then the system shall report it naming the exact environment key and how to provide it.*
- **REQ-003 (State-driven):** *While the index for the active corpus is absent or its manifest is
  incompatible, the system shall report the index area as failing and name the re-index command.*
- **REQ-004 (Optional):** *Where the index exists, the system shall report its freshness (last-index
  time and whether sources changed since) so a stale index is surfaced.*
- **REQ-005 (Optional):** *Where a provider reachability check is requested, the system shall perform a
  minimal, non-indexing probe via the vehicle and report reachable / unreachable with the reason.*
- **REQ-006 (Optional):** *Where the MCP server is configured, the system shall report whether it is
  registered/reachable and flag a stale-after-reindex condition when detectable.*
- **REQ-007 (Ubiquitous):** *The command shall emit a machine-readable (`--json`) report in addition to
  the human-readable one, with a stable schema for skill consumption.*
- **REQ-008 (Unwanted):** *If any critical check fails, then the command shall exit with a non-zero
  status (and exit zero when all critical checks pass).*
- **REQ-009 (State-driven):** *While offline, the static checks (env, index presence) shall still run and
  report; network-dependent checks shall degrade honestly (skipped/unknown), not crash.*
- **REQ-010 (Unwanted):** *If an output field would contain a secret, then the system shall not include
  it (the existing redaction applies to the doctor output).*

## 6. Requisiti non funzionali
- **NFR-1 (deterministico/veloce):** i check statici sono deterministici e completano in tempi
  trascurabili; nessun effetto collaterale sull'indice o sulla config.
- **NFR-2 (host-agnostico, Principio X):** funziona su qualunque ospite; ciò che varia sta in config.
- **NFR-3 (vehicle, Principio XI):** accede alle capacità via i percorsi pubblici (CLI/factory), non
  reimplementa logica del core; **non** importa internamente per "scorciatoie".
- **NFR-4 (privacy):** zero segreti nell'output; il probe provider non logga chiavi.
- **NFR-5 (additività):** comando nuovo, non altera i comandi/percorsi esistenti.

## 7. Vincoli, assunzioni e dipendenze
- **Riuso:** `Settings.validate_backend()` (E2/`sertor-cli`) come fonte dei campi mancanti; manifest/
  `index_dir` (`sertor-core`) per presenza+freschezza; stato MCP dal vehicle.
- **Dipendenza inversa:** `sertor configure --check` (E2/FEAT-003, oggi deferred) **dipenderà** da
  questo comando — è la primitiva che lo sblocca.
- **Assunzione:** il probe provider può richiedere rete/credenziali → è **opt-in/distinto** dai check
  statici (DA-D1) per restare offline-safe.

## 8. Rischi
- **R-1 — Freschezza ambigua:** definire "stantio" senza falsi positivi (i `sources` larghi). Mitigare
  con la stessa logica del refresh incrementale (mtime+hash del manifest), non un'euristica nuova.
- **R-2 — Probe provider costoso/lento:** mantenerlo minimale e opt-in; mai indicizzare per provare.
- **R-3 — Sovrapposizione con osservabilità:** doctor è uno **snapshot puntuale**, non storicizzazione
  (quella è E3); non duplicare lo store.

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001/002/003/007/008 (le quattro aree, JSON, exit code) — check **statici** env+indice.
- **Should:** REQ-004 (freschezza), REQ-005 (probe provider opt-in), REQ-006 (MCP), REQ-009 (offline).
- **Could:** dettaglio esteso per-area, suggerimenti di rimedio più ricchi.

## 10. Domande aperte
- **DA-D1 — Forma dei check di rete:** [DA CHIARIRE in design: un comando unico con flag per
  includere/escludere il probe provider/MCP, o sotto-check selezionabili? Default proposto: comando
  unico con esito per-area + flag per saltare i check di rete (offline-safe by default).]
- **DA-D2 — Definizione di "indice stantio":** [DA CHIARIRE: riusare il segnale di drift del refresh
  incrementale (`sertor-core` FEAT-009) o un check leggero mtime? Default proposto: leggero su
  manifest, coerente col refresh incrementale; il drift "vero" resta a osservabilità FEAT-012.]
- **DA-D3 — Relazione con `configure --check`:** confermato che `--check` **invoca** `doctor`; resta da
  decidere se `--check` ne è un alias sottile o un sottoinsieme (solo config). Default: sottoinsieme
  config + rimando a `doctor` per il quadro completo.
