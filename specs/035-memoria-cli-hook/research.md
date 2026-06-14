# Research — Superficie CLI memoria + hook SessionEnd (035)

**Feature**: `035-memoria-cli-hook` | **Date**: 2026-06-14 | **Fase**: Phase 0 (plan)

Risoluzione degli ignoti tecnici. Ogni decisione: *Decision · Rationale · Alternatives*. Le scelte
A-006…A-010 della spec («rinviate al design») sono qui risolte ancorandole al codice reale di
`src/sertor_core/`.

Sintesi del terreno (ancoraggio al codice):
- I servizi del core esistono già su master: `MemoryArchiveService.archive_all() -> ArchiveRunReport`
  (`services/memory_archive.py:30`, contatori `archived`/`skipped`/`errors`) e
  `EpisodicSearch.search(SearchQuery) -> EpisodicResults` con `EpisodicHit`
  (`services/episodic_search.py:101`, campi `session_key`/`captured_at`/`role`/`turn_index`/`snippet`/
  `score`/`source_path`).
- Le factory di composition sono **già gated**: `build_memory_archiver(settings)` e
  `build_episodic_search(settings)` ritornano `None` quando `settings.memory_enabled` è `False`
  (`composition.py:353` e `:370`), **senza** aprire file né importare l'adapter host-specifico. Sono
  riesportate da `__init__.py` (`build_memory_archiver`, `build_episodic_search`).
- La CLI `sertor-rag` (`cli/__main__.py`) usa argparse con `add_subparsers(dest="command",
  required=True)`, handler `_cmd_*` con `set_defaults(handler=…)`, `_resolve_settings`,
  `_check_backend`, exit code `0`/`1` (`SertorError` su stderr) / `2` (argparse).
- `Settings.memory_enabled` (`SERTOR_MEMORY`, default `False`), `episodic_limit` (20),
  `episodic_snippet_tokens` (12) sono già in `config/settings.py:123-130`.
- Gli hook Claude Code sono cablati in `.claude/settings.json` (versionato) e delegano a uno script
  PowerShell in `.claude/hooks/` (`wiki-pending-check.ps1`), già con un branch `SessionEnd`.

---

## D1 — Forma argparse: gruppo `memory` con sub-subcomandi vs comandi piatti

**Decision**: gruppo di comando `memory` con **due sub-subcomandi** `archive` e `search`, ottenuti
con un secondo livello di `add_subparsers` annidato nel parser di `memory`. Invocazioni:
`sertor-rag memory archive [--json]` e `sertor-rag memory search <query> [--since …] [--until …]
[-k …] [--full] [--json]`.

**Rationale**:
- argparse regge nativamente i sub-subparser. Lo schema corrente in `_build_parser` crea
  `sub = parser.add_subparsers(dest="command", required=True, metavar="command")`. Aggiungo
  `p_memory = sub.add_parser("memory", …)` e dentro `msub = p_memory.add_subparsers(
  dest="memory_command", required=True, metavar="subcommand")` con i due parser `archive`/`search`,
  ciascuno con `set_defaults(handler=…)`. Il dispatch in `main()` resta invariato
  (`args.handler(args)`), perché ogni sub-subparser registra il proprio handler — nessun ramo nuovo
  in `main()`.
- `required=True` sul sub-subparser dà gratis il messaggio d'uso (exit 2) quando si scrive
  `sertor-rag memory` senza azione, coerente con `command` di primo livello.
- Raggruppa concettualmente l'area «memoria» (oggi 2 comandi, in prospettiva FEAT-003/005/006 ne
  aggiungeranno altri: `remember`, `forget`, `distill`); i comandi piatti `memory-archive`/
  `memory-search` saturerebbero il livello dei comandi e non scalano.
- Coerente con la **lente di prodotto**: `observe`/`index`/`search` sono verbi; `memory` è un'area, e
  `memory <verbo>` è l'idioma giusto (come `git remote add`).

**Alternatives**:
- *Comandi piatti* `memory-archive`/`memory-search`: più piatto da parsare (un solo livello), ma
  non raggruppa l'area e sporca l'elenco dei comandi di primo livello; respinto perché non scala con
  l'epica memoria.
- *Sottocomando unico `memory` con flag `--archive`/`--search`*: respinto — flag mutuamente esclusivi
  che fingono di essere azioni; anti-idiomatico per argparse e meno scopribile in `--help`.

## D2 — Meccanismo del gate di privacy

**Decision**: il gate è già nel core (le factory ritornano `None` se `memory_enabled` è `False`). I
comandi **intercettano il `None`** restituito da `build_memory_archiver`/`build_episodic_search` e
sollevano un `ConfigError` azionabile (exit 1) che nomina `SERTOR_MEMORY=true`. L'hook PowerShell,
prima ancora di invocare la CLI, **controlla** la variabile d'ambiente `SERTOR_MEMORY` e, se non
abilitata, esce 0 senza alcun output (no-op silenzioso).

Helper condiviso nel CLI (uno per servizio):
```python
def _require_archiver(settings):
    archiver = build_memory_archiver(settings)
    if archiver is None:
        raise ConfigError(
            "memory is disabled; set SERTOR_MEMORY=true to enable archiving",
            key="SERTOR_MEMORY",
        )
    return archiver
```
(idem `_require_episodic_search`). `ConfigError` è già un `SertorError` → `main()` stampa
`error: …` su stderr e ritorna 1 (FR-016, SC-007).

**Rationale**:
- **Intercettare il `None`** (non leggere `settings.memory_enabled` nel comando) tiene il gate in
  **un solo posto** (le factory in composition, Principio I): il comando non duplica la regola di
  privacy, la *consuma*. Se domani il gate diventasse più ricco (es. per-capacità), il comando non
  cambia.
- L'hook **non può** intercettare un `None` Python (è uno script di shell che lancia un processo): il
  modo robusto e non-fatale per il no-op silenzioso (FR-015, SC-006) è controllare l'env e uscire
  PRIMA di avviare il processo CLI — così a memoria spenta non si avvia neppure Python (zero costo,
  zero rumore). È un controllo del *trigger* host-specifico, non una reimplementazione della logica.
- A memoria spenta `SERTOR_MEMORY` può essere assente/`false`/`0`/`no`: l'hook normalizza con un
  match permissivo (`'true'/'1'/'yes'/'on'`, case-insensitive) coerente con `_bool_env` del core.

**Alternatives**:
- *Comando legge `settings.memory_enabled`*: respinto — duplicherebbe la regola di gate fuori dalle
  factory (due fonti di verità del gate); l'intercettazione del `None` è più DRY e già pronta.
- *Hook invoca sempre la CLI e lascia che il comando faccia no-op*: respinto — a memoria spenta il
  comando solleva `ConfigError` (exit 1), che NON è un no-op silenzioso (FR-015): l'hook dovrebbe
  ignorare l'exit 1, ma avvierebbe comunque un processo Python a ogni fine sessione anche con memoria
  spenta (costo e rumore inutili). Il pre-check dell'env è più pulito.

## D3 — Cosa archivia l'hook (e il comando)

**Decision**: sia il comando `memory archive` sia l'hook invocano **`archive_all()`** (tutte le
sessioni scopribili del progetto), non «solo la sessione corrente». L'hook lancia esattamente
`sertor-rag memory archive` (in dev: `uv run sertor-rag memory archive`).

**Rationale**:
- `archive_all()` è **idempotente** by design: salta le sessioni già archiviate via
  `self._archive.exists(ref.session_key)` (`services/memory_archive.py:47`), incrementando `skipped`.
  Il costo sui già-archiviati è ~nullo (un `exists` per sessione, nessuna riscrittura) — Principio VI.
- È più **robusto**: recupera anche eventuale pregresso non ancora catturato (sessioni chiuse in
  passato senza hook, o quando la memoria era spenta e poi accesa). A fine sessione il transcript è
  completo (A-004), quindi catturare «tutto» include anche la sessione appena chiusa.
- È più **semplice** (YAGNI, Principio III): non serve un nuovo metodo «archivia-solo-questa» nel
  core né il passaggio dell'identità della sessione corrente attraverso l'hook → il CLI; l'unica
  superficie del core consumata è quella già esistente (`archive_all()`), additivo puro (FR-019).

**Alternatives**:
- *Archivia solo la sessione corrente*: richiederebbe un nuovo metodo di core
  (`archive_session(session_key)`) e che l'hook conoscesse/propagasse l'id di sessione — fuori
  ambito (A-007) e contro YAGNI; respinto. L'idempotenza rende `archive_all()` sicuro e sufficiente.

## D4 — Wiring dell'hook (file e configurazione)

**Decision**: un nuovo script PowerShell **versionato** `\.claude/hooks/memory-capture.ps1` +
**estensione del blocco `SessionEnd`** in `.claude/settings.json` (anch'esso versionato) con una
seconda voce di hook che lo invoca. Coerente con il pattern di `wiki-pending-check.ps1` (script
versionato richiamato da una voce in `settings.json`). Lo script è cablato **per il dogfood di
Sertor**; la distribuzione su ospiti via `sertor install` è FUORI AMBITO (annotata come estensione,
§Estensioni).

Voce aggiunta al blocco `SessionEnd` esistente (accanto a quella del wiki):
```jsonc
{ "type": "command", "shell": "powershell", "timeout": 15,
  "command": "$d = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { '.' }; & (Join-Path $d '.claude/hooks/memory-capture.ps1')" }
```

**Rationale**:
- **Versionato** (`settings.json`, non `settings.local.json`): l'hook fa parte del dogfood condiviso
  del repo — come gli hook wiki, deve valere per chiunque lavori su Sertor; `settings.local.json`
  resta per le sovrascritture personali. Coerenza col precedente esistente.
- **Script separato** (non comando inline in JSON): la logica del pre-check del gate + invocazione
  non-fatale è troppo per un one-liner JSON; lo script è testabile e leggibile come
  `wiki-pending-check.ps1`.
- **Aggiunta** al blocco `SessionEnd` esistente (Claude Code consente più hook per evento): non
  tocca l'hook wiki esistente (additivo, FR-019).

**Alternatives**:
- *`settings.local.json`*: respinto — l'hook è capacità di prodotto in dogfood, non preferenza
  personale.
- *Comando inline in `settings.json`*: respinto — non testabile, illeggibile, il pre-check del gate
  richiede più di una riga.

## D5 — Formato output

**Decision**: due nuove funzioni di proiezione **pure** in `cli/output.py` (stesso stile di
`format_index_report`/`format_search_results`, view-only, equivalenza umano↔JSON come invariante).

`format_archive_report(report: ArchiveRunReport, *, json)`:
- JSON: `{"archived": N, "skipped": N, "errors": N}`.
- Umano: `archived=N skipped=N errors=N` (una riga, stesso stile di `format_index_report`).

`format_memory_results(results: EpisodicResults, settings, *, json, full)`:
- JSON: array di oggetti `{"session_key", "captured_at", "role", "turn_index", "snippet", "score"}`
  (`score` arrotondato a 6 come in `format_search_results`); `latency_ms` NON nel payload per-hit ma
  resta disponibile per l'osservabilità (già loggato dal core). Decisione: includere `latency_ms`
  come campo a livello di risposta non è possibile con un array; si tiene l'array di hit coerente con
  `search` (che è anch'esso un array). `captured_at` è epoch float, reso così com'è (consumabile a
  macchina); render umano lo mostra ISO-8601 UTC via `time.gmtime`+`strftime`.
- Umano: blocchi numerati coerenti con `format_search_results`, es.
  `[1] score=0.873  role=user  session=<key>  turn=12  @=2026-06-14T10:21:03Z` + riga snippet
  indentata. `snippet` già delimitato `[…]` dal core (`snippet()` SQL).
- `(no results)` quando `hits` è vuoto (stato vuoto onesto, ereditato dal core — edge case
  «archivio assente/vuoto»).

**Rationale**: riuso del pattern esistente (DRY, Principio VII naming di dominio: i campi sono quelli
del core); l'equivalenza umano/JSON è invariante già rispettata da `output.py` (SC dei conteggi). Il
`--full` riusa la logica `--full` di `search` (snippet del core è già breve, ma `--full` lo lascia
intatto vs preview — nel caso episodico lo snippet è già la forma sintetica, quindi `--full` può
omettersi; **decisione**: `memory search` NON espone `--full` perché il core restituisce già uno
`snippet` (non il testo intero del turno); semplifica la superficie, YAGNI).

**Alternatives**:
- *Riusare `format_search_results`* per i risultati episodici: respinto — `EpisodicHit` ha campi
  diversi (`session_key`/`role`/`turn_index`/`snippet`) da `RetrievalResult` (`path`/`doc_type`/
  `chunk_id`); forzare l'adattamento sarebbe meno chiaro di una funzione dedicata simmetrica.
- *Render `captured_at` come epoch grezzo anche nell'umano*: respinto — illeggibile per un umano; ISO
  UTC è la forma giusta per la vista umana, epoch per il JSON consumabile.

## D6 — Non-bloccante / non-fatale dell'hook

**Decision**: lo script `memory-capture.ps1` garantisce non-fatalità e non-blocco con tre misure:
1. **Pre-check del gate** (D2): se `SERTOR_MEMORY` non è abilitata → `exit 0` immediato senza avviare
   nulla (no-op, FR-015).
2. **Invocazione che ignora l'esito**: lancia la CLI in `try { … } catch {}` e **non** propaga il
   codice d'uscita del comando; lo script esce **sempre 0** (FR-013, SC-005). Output del comando
   soppresso/minimale (redirect `2>$null` come in `wiki-pending-check.ps1`).
3. **Timeout** nella voce `settings.json` (`"timeout": 15`): cap superiore alla durata; se scade,
   l'host termina l'hook senza far fallire la chiusura. Per il non-blocco percepito, l'archiviazione
   è deterministica e locale (SQLite + lettura file, niente rete nel percorso di cattura) — già
   leggera; in più lo script può lanciare in background il processo CLI (`Start-Process -NoNewWindow`)
   per non attendere, ma **decisione**: avvio sincrono dentro il timeout dell'host è sufficiente e
   più semplice (YAGNI); l'osservabilità degli eventi resta intatta. Se in futuro la cattura
   crescesse, si passa a background.

**Rationale**: replica esattamente la disciplina di `wiki-pending-check.ps1` (try/catch → `exit 0`,
`2>$null`, niente propagazione d'errore) che è già il pattern «hook non rompe la sessione» del repo.
Il timeout dell'host è la rete di sicurezza contro un blocco (SC-005). L'evento di chiusura
`SessionEnd` non attende l'utente, quindi anche un ritardo non è percepito dall'utente nel turno.

**Alternatives**:
- *`Start-Process` in background sempre*: respinto come default — aggiunge complessità (orfani di
  processo, race sul lock SQLite tra due fine-sessione ravvicinate) senza necessità presente (YAGNI).
  Annotato come via di fuga se la cattura diventa costosa.
- *Far fallire l'hook su errore di archiviazione*: vietato dalla spec (FR-013) — degraderebbe la
  chiusura sessione.

---

## Estensioni / fuori ambito (annotate, non implementate)

- **Distribuzione su ospiti esterni** (A-009, Out of Scope): `sertor install` cablerà lo script
  + la voce `SessionEnd` sull'ospite. Qui l'hook è solo per il dogfood di Sertor.
- **Hook per altri assistenti** (FR-018, FEAT-008): l'hook è host-specifico Claude Code; altri
  assistenti = adattatori del trigger futuri, che invocheranno lo **stesso** comando host-agnostico.
- **Ricerca semantica** (FEAT-004), **distillazione** (FEAT-003), **retention** (FEAT-006),
  **remember-this** (FEAT-005), **refresh sessione parziale**: fuori ambito (Out of Scope della spec).

## Errori MCP

Nessun errore: `mcp__sertor-rag__find_symbol` ha risolto `build_memory_archiver` (`composition.py:353`)
e `build_episodic_search` (`composition.py:370`) — il code-graph dell'indice dogfood contiene i simboli
FEAT-001/002. Ancoraggio completato con `find_symbol` + `Read`/`Grep`.
