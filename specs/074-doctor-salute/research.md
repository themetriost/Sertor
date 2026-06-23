# Research — `sertor-rag doctor` (E12-FEAT-001)

**Branch**: `074-doctor-salute` · **Fase**: 0 (Outline & Research) · **Data**: 2026-06-23

Questo documento risolve gli ignoti tecnici (Technical Context) e le forche di design residue
**DA-D4** (già fissata dall'utente, qui solo codificata) e **DA-D5** (da risolvere). Ogni decisione è
ancorata al codice reale via RAG/`Read` (path:lineno citati). Le decisioni DA-D1/D2/D3 sono già chiuse
nella spec e **non** vengono riaperte.

---

## Technical Context (sintesi)

| Voce | Valore |
|------|--------|
| Linguaggio | Python ≥ 3.11 (stesso del core) |
| Pacchetti toccati | `sertor-core` (comando `doctor`) + `sertor` (wizard `configure --check`) |
| Dipendenze nuove | **Nessuna** per i check statici (SC-012) — stdlib (`json`, `sqlite3` via factory, `pathlib`) |
| Storage | sola lettura: manifest `<index_dir>/index_manifest.sqlite`, `.mcp.json`, env/`.env` via `Settings` |
| Vehicle | comando CLI `sertor-rag` (gruppo nuovo), factory `build_*` (Principio XI) |
| Test | offline, deterministici (mock dei segnali; nessun cloud) |
| Performance | check statici in tempo trascurabile; nessun re-scan del repo |
| Ignoti risolti | DA-D5 (probe provider + stantio MCP) — vedi sotto |

---

## D1 — Dove vive `doctor` e come accede ai segnali (ancoraggio)

**Decisione.** `doctor` è un **sottocomando di `sertor-rag`** registrato in
`src/sertor_core/cli/__main__.py` (gruppo nuovo, parallelo a `eval`/`graph-eval`/`memory`), con un
handler thin `_cmd_doctor` che:
1. risolve `Settings` via `_resolve_settings` (riusa `--corpus`, `src/sertor_core/cli/__main__.py:422`);
2. costruisce un **servizio di diagnosi puro** `HealthDiagnostics` (nuovo, `services/doctor.py`) iniettando
   i segnali letti via le factory pubbliche;
3. formatta con una funzione pura `format_health_report` in `cli/output.py` (umano vs `--json`);
4. determina l'exit code dal report (gate critici → `DoctorCheckFailed`, exit 1).

**Rationale.** È il pattern già consolidato per `eval`/`graph-eval` (handler thin → factory →
formatter puro), conforme a Principio I/XI/NFR-3. La logica diagnostica vive in un servizio puro
**testabile senza CLI**; la resa è separata (umano/JSON), invariante di equivalenza informativa come gli
altri formatter (`cli/output.py:5`).

**Segnali e da dove si leggono (tutti già esistenti, dato di partenza):**

| Area | Segnale | Sorgente (vehicle/factory) | Riferimento |
|------|---------|----------------------------|-------------|
| env/config | chiavi env mancanti per provider/store | `settings.validate_backend()` | `config/settings.py:238` |
| provider (statico) | config provider completa | derivato da `validate_backend()` (sottoinsieme provider) | `config/settings.py:248-254` |
| provider (rete, opt-in) | raggiungibilità | `build_embedder(settings)` + `embed([sentinel])` | `composition.py:68` |
| indice (presenza) | manifest caricabile? | `IndexManifest(index_dir).load(collection_name(...))` → `None`? | `services/index_manifest.py:122`, `composition.py:168` |
| indice (freschezza) | file modificati dall'ultima indicizzazione | `ManifestState.files` (mtime+hash registrati) vs `os.stat` corrente | `services/index_manifest.py:69-75,149` |
| MCP | server registrato? | lettura `.mcp.json` (`mcpServers.sertor-rag`) nella radice host | installer `install_rag.py:325` (root + `mcpServers`) |

**Alternativa scartata.** Reimplementare i check importando i componenti interni (es. leggere
`memory.sqlite`/Chroma direttamente) → viola Principio XI e duplica logica: si consumano i segnali
attraverso `Settings`/`IndexManifest`/`build_embedder`, non scorciatoie.

---

## D2 — DA-D4 (codifica deterministica critico/warn)

**Decisione (confermata dall'utente, qui resa testabile).** La severità di ciascun esito è una
funzione pura `area → criticità` cablata nel servizio, non un'euristica:

| Area / condizione | Esito | Severità (gate?) |
|-------------------|-------|------------------|
| env: chiave richiesta mancante | **fail** | **CRITICO** (exit ≠ 0) |
| env: tutte presenti / locale senza credenziali | pass | — |
| indice: assente o manifest incompatibile (`load()→None`) | **fail** | **CRITICO** (exit ≠ 0) |
| indice: presente, sorgenti invariate | pass | — |
| indice: presente ma sorgenti modificate (stantio) | **warn** | non-gate (exit 0) |
| provider: config statica incompleta | **fail** | **CRITICO** (eredita dall'area env: stesse chiavi) |
| provider: probe rete → non raggiungibile | **warn** | non-gate (exit 0) |
| provider: probe rete → skipped/unknown (offline, no flag) | skip | non-gate |
| MCP: non registrato | **warn** | non-gate (exit 0) |
| MCP: stantio-dopo-reindex (best-effort) | **warn**/unknown | non-gate |

**Modello deterministico.** L'exit code è `1` ⇔ esiste ≥1 `Problem` con `severity == CRITICAL`. La
severità è un attributo del `Problem`, derivato in modo puro dalla regola sopra; nessuna soglia
dinamica. `pass`/`warn`/`fail` è il **rollup per-area** (il massimo della severità dei problemi
dell'area; nessun problema → `pass`).

**Nota di sovrapposizione env↔provider.** La config provider statica (FR-007) è **lo stesso insieme di
chiavi** che `validate_backend()` produce per il ramo provider (`embed_provider == "azure"`,
`settings.py:248`). Per non duplicare: l'area **env** riporta TUTTE le chiavi mancanti (provider+store);
l'area **provider** riusa il sottoinsieme provider come «config statica» (criticità ereditata). Questo
evita una lista propria (FR-004) e tiene `validate_backend()` fonte unica.

**Rationale.** «Posso usare Sertor adesso?» è bloccato da due cose sole: config provider/store
incompleta (l'embedder non si costruisce) e indice assente (la query fallisce con
`IndexNotFoundError`). Stantio, MCP, irraggiungibilità sono *degradi noti e azionabili* ma non
impediscono l'uso immediato → warn. Allineato ad A-007 della spec.

---

## D3 — DA-D5a: forma del probe provider minimale (RISOLTA)

**Decisione.** Il probe opt-in costruisce l'embedder via la factory pubblica
`build_embedder(settings, allow_download=False)` (`composition.py:68`) e chiama `embed([sentinel])` su
**una stringa sentinella minima** (es. `"sertor doctor reachability probe"`). Il verdetto:
- nessuna eccezione → **reachable**;
- `EmbeddingError`/errore di rete/credenziali → **unreachable** + motivo (messaggio
  dell'eccezione, passato per `scrub_text`);
- offline senza flag → il probe **non viene eseguito** (skipped).

**`allow_download=False` è vincolante**: il probe non deve MAI scaricare il file GloVe (~822 MB) né
indicizzare; per `glove`/`hash` l'`embed` è puramente locale e deterministico → sempre reachable se il
file dati c'è (per `glove` senza file → `GloveUnavailableError`, riportato come unreachable azionabile,
**non** un download). Per `ollama`/`azure` l'`embed` di una stringa è la chiamata più leggera possibile
ed è esattamente la verifica di raggiungibilità richiesta (REQ-005, SC-008: nessuna indicizzazione).

**Perché non un «ping» specifico per provider.** Un endpoint di health per-provider (es. `/api/tags`
di Ollama, una GET su Azure) (a) reintrodurrebbe nel core conoscenza di SDK/URL specifici per provider
fuori dagli adapter (viola Principio I/II: i dettagli del provider stanno dietro il boundary
`EmbeddingProvider`), (b) duplicherebbe logica che l'adapter già incapsula, (c) non testa il *path
reale* (un endpoint health up ma deployment/modello sbagliato passerebbe). L'`embed` di una stringa
minima testa **il percorso che l'indicizzazione userà davvero**, attraverso il vehicle/factory, senza
indicizzare. È il probe più onesto e il meno accoppiato.

**Costo.** Una sola chiamata di embedding su una stringa corta (ordine di pochi token); trascurabile,
sotto controllo dell'utente (opt-in). Nessun upsert allo store (SC-008/SC-009).

**Privacy.** La sentinella è una costante, non contiene dati dell'utente; il messaggio d'errore passa
da `scrub_text` (`observability/scrub.py:36`) prima dell'output, e l'evento di osservabilità è
metrics-only (mai la sentinella/chiavi).

**Alternativa scartata.** Un comando separato `sertor-rag check` (come oggi assume `_probe_live`):
deciso di **non** introdurlo come comando distinto — `doctor` con flag rete è la primitiva unica
(DA-D1: comando unico). `configure --check` punterà a `doctor` (vedi D6).

---

## D4 — DA-D5b: rilevazione dello «stantio-dopo-reindex» del server MCP (RISOLTA, best-effort)

**Contesto verificato.** Il server MCP (`src/sertor_mcp/server.py`, non toccato qui) è un **processo
separato** che legge l'indice da disco all'avvio. Il guasto reale (2026-06-19, CLAUDE.md): dopo un
re-index il server continua a servire il vecchio store fino al riavvio. `doctor` gira come **un altro
processo CLI** e non ha accesso affidabile al PID/istante-di-avvio del server MCP.

**Decisione.** `doctor` **non inventa** un meccanismo di rilevazione cross-processo fragile. Codifica
lo stantio MCP come segnale **best-effort, sempre warn-or-unknown, mai gate**:
- se l'indice è **stantio** (D-indice warn) **e** il server MCP è **registrato**, l'area MCP riporta un
  warn informativo «l'indice è cambiato dall'ultima indicizzazione: se il server MCP `sertor-rag` è in
  esecuzione, riavvialo per servire il nuovo indice» — derivato dai segnali che `doctor` **ha già**
  (freschezza manifest + registrazione MCP), senza interrogare il processo;
- la rilevazione esatta «il server gira ed è più vecchio dell'artefatto» richiederebbe un canale
  liveness/handshake col server (PID file, ultimo-caricamento esposto) che **oggi non esiste** →
  riportata come `unknown` con nota, **non** sintetizzata in modo falsamente preciso (Principio XII:
  non fingere un segnale che non si ha).

**Rationale.** È coerente con FR-009 («quando rilevabile») e con la spec (US5.3 «la condizione
stantio-dopo-reindex è segnalata quando rilevabile»). Si consegna il valore deterministico disponibile
(stantio + registrato ⇒ avviso di riavvio) senza un meccanismo IPC fragile. La rilevazione *forte*
(handshake col server) è promossa come **debito** a osservabilità/MCP (vedi §Estensioni), non
implementata qui con un'euristica inaffidabile.

**Alternativa scartata.** Confrontare il mtime del file `.mcp.json`/indice con un lockfile del server:
nessun lockfile del server esiste oggi; introdurlo è scope del server MCP (FEAT separata), non di
`doctor`.

---

## D5 — Freschezza dell'indice dal manifest (senza riscansione, senza falsi positivi)

**Contesto verificato.** Il manifest **non** persiste un `last_index_time` esplicito; persiste per file
`(mtime, content_hash, logic_version)` (`index_manifest.py:97-100,69-75`) e i metadati di collezione
(schema/collection/`reconcile_counter`). `load(collection)` → `ManifestState | None`
(`index_manifest.py:122`).

**Decisione.** La freschezza è derivata **dai mtime registrati**, non da una riscansione completa:
- **last-index time (riportato all'utente)** = `max(mtime registrati)` nel manifest (proxy
  deterministico dell'istante dell'ultima scrittura del manifest; nessun nuovo campo da aggiungere,
  additività). In assenza di file → indice vuoto/assente.
- **stantio?** = esiste ≥1 file sorgente sul disco il cui `mtime` corrente è **> ** del `mtime`
  registrato per quel path, **oppure** un file registrato è scomparso, **oppure** un file nuovo non
  registrato compare nello stesso scope. Il confronto è un **`os.stat` per file registrato** (cheap
  pre-filter, come fa già `IndexManifest.classify`, `index_manifest.py:149-190`) — **non** un re-hash,
  **non** un re-chunk.

**No falsi positivi su `sources` larghi (R-1/SC-007).** Il confronto è **mtime-only** e limitato ai
file che il manifest **già conosce** + un conteggio dei nuovi nello scope: è esattamente il pre-filtro
del refresh incrementale, quindi «stantio» qui significa la stessa cosa che per `index` incrementale
(coerenza, nessuna euristica nuova). Per evitare il falso positivo del `touch` senza modifica, lo
**stato è `warn`, non `fail`**: un mtime avanzato è un *segnale di possibile drift*, non una certezza —
il drift «vero» (hash) resta al refresh incrementale e a osservabilità (FEAT-012). Il design **non**
ri-hasha in `doctor` per restare trascurabile (RNF-1) e perché lo scopo è «ti conviene ri-indicizzare?»,
non «misura esatta del delta».

**Servizio puro `freshness_from_manifest(state, current_stats)`** in `services/doctor.py`: input =
stato manifest + lista `(path, mtime)` corrente per i path noti; output = `pass`/`warn` + lista path
sospetti (troncata) + `last_index_iso`. Testabile offline con stati sintetici (no FS reale necessario).

**Helper di enumerazione corrente.** Per ottenere i `(path, mtime)` correnti senza re-scan completo si
fa `os.stat` **solo** sui path già in `state.files` (più un check di esistenza); l'eventuale conteggio
«nuovi file nello scope» è un check leggero opzionale rinviabile (vedi §Estensioni) — l'MVP rileva
modifiche/cancellazioni dei file **noti**, che copre il caso d'uso «ho editato/aggiunto e non
re-indicizzato» per i file già tracciati. *(Decisione di portata: lo stantio MVP = modifiche/delete dei
file noti; «nuovi file mai indicizzati» = miglioramento Could, non blocca, vedi §Estensioni.)*

---

## D6 — DA-D3 wiring `configure --check` (codifica, già deciso che invoca `doctor`)

**Contesto verificato.** `configure._probe_live` (`configure.py:369`) invoca oggi
`runner.run([_SERTOR_RAG, "check"], cwd=target_root)` e degrada onestamente se assente. `_SERTOR_RAG =
"sertor-rag"` (`configure.py:37`). L'esito è un `LiveCheckOutcome(requested, ok, detail)`
(`configure_report.py:58`); chiamato in `configure.py:296-300` solo se `check`.

**Decisione.** `_probe_live` cambia il comando invocato da `sertor-rag check` a:

```
sertor-rag doctor --area config --json
```

(`--area config` = sottoinsieme config richiesto da DA-D3; `--json` = parsing affidabile). La mappatura
exit→`LiveCheckOutcome`:
- comando assente / `unknown command` / exit 2 → `ok=None` + «probe live non disponibile … aggiorna il
  runtime» (degrado onesto preservato, FR-018/US8.3, branch oggi vivo, domani morto solo se sempre
  presente);
- exit 0 → `ok=True`, `detail` = breve rimando «esegui `sertor-rag doctor` per il quadro completo
  (provider/indice/MCP)»;
- exit ≠ 0 (config incompleta) → `ok=False`, `detail` = messaggio (config) estratto dal JSON, già
  scrubbed.

**`--area`**: nuovo flag opzionale di `doctor` che restringe le aree eseguite (`config` =
solo env/config). Senza `--area`, `doctor` esegue tutte e quattro. Questo realizza il «sottoinsieme
config» (DA-D3) **senza** un secondo comando e tiene `configure --check` un *vero* probe (non più
degrado). `configure` senza `--check` resta byte-identico (FR-017/SC-011).

**Rationale.** Riusa il punto d'estensione esistente (A-006): cambia solo la stringa-comando e il
parsing; il wizard non viene riscritto. La dipendenza è già nella forma giusta (subprocess via vehicle,
Principio XI). Il degrado onesto è preservato (il branch «non disponibile» resta).

---

## D7 — Osservabilità: evento `doctor` metrics-only

**Decisione.** `doctor` emette **un evento `doctor`** (gemello di `eval`, `runner.py:34`),
metrics-only: `overall` (pass/warn/fail), conteggi per severità (`n_fail`/`n_warn`/`n_pass`),
`online` (bool, se il flag rete era attivo), `areas` (le 4 etichette con esito). **Mai** chiavi, valori
env, sentinella del probe, path, motivi d'errore. Catturato solo se `SERTOR_OBSERVABILITY=true`
(l'handler già cablato da `enable_observability`, `composition.py:254`). L'handler dispatch chiama
`enable_observability(settings)` nel handler come gli altri comandi.

**Rationale.** Coerente con la pratica del repo (eventi metrics-only per ogni operazione, Principio
IX); utile per capire quanto spesso `doctor` rileva problemi senza esporre dati. Vale la pena: è
allineato a `eval`/`embeddings`/`configure` (`configure.py:348`).

---

## D8 — Schema JSON stabile (SC-003)

**Decisione.** Schema versionato `doctor.report/1` (vedi `contracts/cli-doctor.md` e `data-model.md`):
oggetto top-level con `schema`, `overall`, `online`, `exit_code`, `areas[]`; ogni area
`{name, status, problems[]}`; ogni problema `{severity, code, message, remedy, fields?}`. Schema =
contratto per skill (guided-setup/search-diagnose) e CI. Stabile tra invocazioni equivalenti (chiavi
fisse, ordine area deterministico).

---

## Estensioni e debiti (promozione, non rinvio appeso)

- **Knob env del probe rete.** Decisione: il probe è governato da un **flag CLI** (`--online`), **non**
  da un nuovo env → **nessun nuovo knob nel template `.env`** dell'installer (SC-012 preservata). *Se*
  in futuro si volesse un default env (es. `SERTOR_DOCTOR_ONLINE`), andrebbe promosso al template `.env`
  (owner E2). Tracciato come **nota** nel backlog `sertor-cli`, non introdotto ora (YAGNI III).
- **Stantio MCP forte (handshake col server).** Rilevazione cross-processo affidabile → **debito** a
  osservabilità/MCP (FEAT-012 / server MCP), promosso a roadmap *Nuove funzionalità da discutere*; qui
  `doctor` dà solo il best-effort derivato (D4).
- **Stantio su «file nuovi mai indicizzati».** Lo stantio MVP copre modifiche/delete dei file noti; il
  rilevamento di file nuovi nello scope (richiede un walk leggero) = **Could** → riga
  `FEAT-NNN`/roadmap dell'epica E12, non appeso in `specs/`.
- **Skill consumatrici (guided-setup/search-diagnose)** consumano `doctor --json`: sono **FEAT-002/E12**
  già a backlog; questo design fornisce loro lo schema stabile (seam), non le implementa.

---

## Constitution Check — Phase 0 (pre-design)

| Principio | Esito | Nota |
|-----------|-------|------|
| I — core verso l'interno | PASS | `doctor` è CLI (vehicle) + servizio puro nel core; nessun SDK importato; logica testabile come libreria |
| II — provider dietro boundary; local-first | PASS | il probe usa `EmbeddingProvider` via factory, nessun dettaglio provider nel comando; statici girano locale |
| III — YAGNI, unità piccole | PASS | nessuna nuova porta/dipendenza; servizio puro piccolo; flag, non env (no knob inutile) |
| IV — errori espliciti, no null silenzioso | PASS | gate critico → `DoctorCheckFailed` (exit 1) azionabile; degradi (offline/manifest assente) **segnalati**, mai silenziosi |
| V — testabilità/misure | PASS | servizio puro testabile offline; gli esiti sono deterministici e verificabili (un caso per area) |
| VI — idempotenza/non-distruttività | PASS | **sola lettura** in ogni scenario (FR-014/SC-009); nessuna scrittura su config/indice |
| VII — leggibilità | PASS | vocabolario di dominio (diagnose/probe/freshness); funzioni piccole guard-clause |
| VIII — config centralizzata | PASS | tutto deriva da `Settings`/`validate_backend()`; nessun default hardcoded nel comando |
| IX — osservabilità | PASS | evento `doctor` metrics-only (D7) |
| X — host-agnostico | PASS | nessuna assunzione sull'ospite; ciò che varia sta in config; gira su qualunque progetto |
| XI — vehicles | PASS | accede via CLI + `build_*`; **non** importa logica per scorciatoie; `configure --check` invoca `doctor` in subprocess |
| XII — fail loud, fix the cause | PASS | il probe riporta unreachable col motivo (non lo nasconde); stantio MCP `unknown` onesto, non finto; nessuna soppressione |
| **Allineamento alla missione** | **PASS** | `doctor` è il substrato deterministico «ha funzionato?» che rende **reale** la host-agnosticità (Principio X): un agente verifica da solo la salute su un ospite qualunque, prerequisito perché il retrieval fuso code+doc sia *davvero* fruibile. Serve l'adozione/portabilità (periferico al differenziatore ma abilitante), il core resta deterministico (l'intelligenza è nelle skill). |

**Esito Phase 0: PASS 12/12 + missione PASS, nessuna deroga.**
