# Phase 0 — Research: CLI esecuzione

Decisioni tecniche per la CLI. Formato: **Decisione / Razionale / Alternative**. La CLI è un layer
sottile sul core (FEAT-001/002/003 in `master`); le decisioni puntano a minimalismo e testabilità.

---

## R1 — Framework CLI: `argparse` (stdlib)

**Decisione.** Usare `argparse` della stdlib per parser, sottocomandi (`index`/`search`/`wiki`) e
opzioni; entry-point console-script `sertor` → `sertor_cli.cli:main`.

**Razionale.** Principio III (YAGNI, no dipendenze pesanti): `argparse` copre sottocomandi, opzioni,
help ed exit code senza aggiungere `click`/`typer`. Coerente col minimalismo del core.

**Alternative.** (a) `typer`/`click`: ergonomia migliore ma dipendenza extra non necessaria → respinta;
riconsiderabile se la superficie comandi crescerà molto (FEAT-CLI-002/005).

---

## R2 — Entry-point `sertor` via console-script (DA-C1)

**Decisione.** Dichiarare in `pyproject.toml` `[project.scripts] sertor = "sertor_cli.cli:main"`.
Con l'installazione editable del pacchetto (`uv pip install -e .`) il comando `sertor` è disponibile
nel venv. `python -m sertor_cli` resta come fallback equivalente (`__main__.py`).

**Razionale.** DA-C1 risolta: comando globale `sertor`. Il console-script dà il comando senza fare la
**distribuzione pubblica** (PyPI/git+url), che resta fuori ambito.

**Alternative.** Solo `python -m`: meno ergonomico → il console-script è poco costo e più pulito.

---

## R3 — Dipendenza e testabilità: monkeypatch dei `build_*` del core

**Decisione.** I comandi chiamano `build_indexer`/`build_facade`/`build_baseline_engine`/`index_wiki`
del composition root. Nei test si **monkeypatcha** `build_embedder`/`build_store` (o i `build_*`) per
restituire `FakeEmbedder`/`InMemoryStore`/`FakeLLM`, così la CLI è esercitabile senza cloud né rete.

**Razionale.** NFR-02: testabilità con mock. Mantiene la CLL sottile (usa il composition root, non
ricabla a mano gli adapter). I `main([...])` ritornano l'exit code per asserzioni.

**Alternative.** Iniettare dipendenze esplicite nei comandi: più verboso; il monkeypatch del
composition root è sufficiente e meno invasivo.

---

## R4 — Mapping errori → exit code e messaggi leggibili (REQ-003, NFR-04)

**Decisione.** `cli.main` cattura le eccezioni di dominio del core (`SertorError` e sottoclassi:
`IngestionError`, `EmbeddingError`, `VectorStoreError`, `IndexNotFoundError`, `LLMNotConfiguredError`,
`ConfigError`) e le presenta come **messaggio leggibile su stderr + exit code non-zero**; in modalità
verbosa mostra il traceback completo. Successo → exit 0.

**Razionale.** Principio IV + REQ-003/022/041: errori espliciti e azionabili, non stack trace grezzi;
exit code per scriptabilità (REQ-004). `IndexNotFoundError` → messaggio "costruisci prima l'indice".

**Alternative.** Lasciar propagare il traceback: pessima UX → respinta (tranne in `--verbose`).

---

## R5 — Osservabilità: verbosity, JSON, `--log-config` (REQ-050..052, DA-C3)

**Decisione.** Modulo `observability.py` che configura il logger `sertor_core`:
- `-v/--verbose` → `level=INFO` su uno `StreamHandler` (default WARNING).
- `--log-json` → formatter JSON **minimale interno** (serializza `operation` + campi da `record.__dict__`),
  senza dipendere da `python-json-logger`.
- `--log-config <file>` → `logging.config.dictConfig` da **YAML o JSON** (DA-C3): l'utente collega
  qualunque handler/appender (file, syslog, Splunk HEC) senza modificare il codice.
La precedenza: `--log-config` (se dato) prevale; altrimenti `-v`/`--log-json` configurano un handler base.

**Razionale.** REQ-050..052 + Principio IX: rende **visibili** i log strutturati del core (oggi muti di
default) e li apre ad appender esterni. Formatter JSON interno per non aggiungere dipendenze (Principio III).

**Alternative.** `python-json-logger`: comodo ma dipendenza extra → formatter interno (~15 righe).

---

## R6 — Estensione additiva del core: logging degli errori sui boundary (REQ-053/054)

**Decisione.** Aggiungere un helper in `observability/logging.py` (es. `log_error(operation, exc, **fields)`)
e chiamarlo nei punti dove il core **avvolge e rilancia** un errore di boundary (adapter embeddings/
store; orchestratore di index): si emette un evento di log strutturato (operazione, provider/backend,
reason) **prima** del `raise`. Documentare i campi di log per-operazione in una pagina/README.

**Razionale.** REQ-053: oggi i fallimenti sono eccezioni esplicite (Principio IV) ma non eventi di log,
lasciando un buco nel Principio IX. È additivo (non cambia firme/comportamento) e abilita il
monitoring via appender. REQ-054 (schema campi) serve a chi configura Splunk/ELK.

**Alternative.** Loggare solo nella CLI (catch in `main`): perderebbe il contesto del boundary (provider/
backend) disponibile solo dentro l'adapter → meglio loggare alla sorgente.

---

## R7 — Output di `search`: testo/JSON, anteprima troncata (DA-C4/C5)

**Decisione.** `output.py`: default **testo leggibile** (path, tipo, score, anteprima); `--json` →
array JSON di oggetti `{path, doc_type, chunk_id, score, preview}`; **anteprima troncata** a lunghezza
limitata in entrambi i formati, `--full` per il testo completo. `-k`/`--type` ereditano i default dal
core (`default_k`, modalità `both`).

**Razionale.** DA-C4/C5 risolte + economia di token (l'anteprima troncata è la leva principale quando
un agente consuma la CLI). Coerenza `--json`/`--log-json`.

**Alternative.** Solo testo o solo JSON: meno flessibile per i due consumatori (umano vs agente).

---

## Sintesi NEEDS CLARIFICATION risolti

Le DA-C1..C5 erano già sciolte in fase requisiti; qui sono tradotte in decisioni tecniche
(R2/C1, R7/C2-namespace via opzione `--corpus`, R5/C3, R7/C4, R7/C5). Nessun NEEDS CLARIFICATION
residuo → si procede alla Phase 1.
