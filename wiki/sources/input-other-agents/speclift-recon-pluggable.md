---
title: "Ricognizione SpecLift — EvidenceLocator pluggable (Adapter B agente+MCP, branch feat/speclift-pluggable-locator)"
type: source
tags: [speclift, sinthari, recon, pluggable-locator, provided-evidence-locator, mcp, three-gear, plan-084]
created: 2026-07-01
source: "Sinthari repo (github.com/themetriost/Sinthari, branch feat/speclift-pluggable-locator @ 00d5cd0), clonato in C:/Workspace/Git/ExternalRepos/Sinthari"
---

# Ricognizione SpecLift — EvidenceLocator pluggable

Studio di sola lettura del branch **`feat/speclift-pluggable-locator`** di themetriost/Sinthari, commit
**`00d5cd0`** («rendi pluggable l'EvidenceLocator (Adapter B: agente + MCP)»). Nessuna modifica al repo
Sinthari. Questo commit è la **risposta upstream** al nostro feedback di dogfooding (Sertor consuma il RAG
via MCP, non via CLI-vehicle `sertor-rag`): rende il locator pluggable **senza** rimuovere quello CLI.

**Convenzione FATTO vs INFERENZA:** i **FATTI** citano `file:riga` (verificati sul commit `00d5cd0`); le
**INFERENZE** sono marcate esplicitamente.

**Verifica ambiente:** `git rev-parse HEAD` = `00d5cd0debca9f52a19f7b7af4a6da875a572439` (FATTO). I 20 test
nuovi/toccati passano offline: `uv run --with pytest pytest … → 20 passed in 0.49s` (FATTO).

---

## 1. `ProvidedEvidenceLocator` (`adapters/provided_locator.py`)

**FATTO.** Nuovo adapter dietro la **stessa porta** `EvidenceLocator`, che **convive** con
`SertorRagLocator` (non lo sostituisce — pluggable, non swap). Interfaccia (`provided_locator.py:25-47`):

- `__init__(self, payload: dict, *, config=DEFAULT_CONFIG)` — consuma il dict `located.json`:
  `self._symbols = payload.get("symbols", {})`, `self._tests = payload.get("tests", {})`. **Nessuna
  validazione al costruttore**, nessun errore custom: chiave assente = `[]` (degrado onesto, `:14-15`).
- `locate_symbols(file_path, identifiers, snippet) -> list[Symbol]` (`:33-40`): deriva le query con
  `build_identifier_queries(identifiers, snippet, config.max_queries_per_symbol)` — **la stessa regola
  G6 del locator CLI** — poi per ogni query fa lookup su `self._symbols[_key(file_path, query)]`.
- `locate_tests(symbol) -> list[TestRef]` (`:42-47`): lookup su `self._tests[symbol.name]`.
- `_key(file_path, query) = f"{file_path}::{query}"` (`:50-52`) — **chiave composita** file+query.
- Nessun subprocess, nessuna rete, nessuna ricerca propria: «si limita a rileggerlo» (`:8`).

**Formato dell'evidenza fornita dall'agente** (`_symbol_from`/`_test_from`, `:55-72`): riusa i modelli di
dominio `Symbol`/`TestRef`. `Symbol` = `{name, path, line?(0), kind?(""), provenance?("")}`; `TestRef` =
`{name, path, covers_symbol, line?(0), provenance?("")}`. `name`/`path`/`covers_symbol` obbligatori (accesso
diretto `raw["..."]` → `KeyError` se assenti), il resto ha default.

**Coesistenza (FATTO).** `SertorRagLocator` (`rag_sertor.py`) resta l'Adapter A di default; entrambi
implementano la porta; il resto della pipeline non li distingue (`pipeline.py` docstring
`build_bundle_from_changeset`). Contratto: `contracts/evidence-locator-port.md:28-46`.

---

## 2. Il "three-gear flow" (marce 0/1/2)

**FATTO** (da `cli.py` + `test_three_gear_flow.py` + `evidence-locator-port.md:48-71`). Le tre marce con
l'Adapter B:

1. **`speclift changeset <ref> [--staged] [--range A..B] [--repo] [--out] [--include-docs]`** — **marcia 0,
   NUOVO comando** (`cli.py:118`, dispatch `main():78`). Deterministica: `ingest → parse_diff →
   filter_sources → STOP` (nessuna localizzazione, RAG mai toccato). Emette `<out>.changeset.json` (suffisso
   `CHANGESET_OUTPUT_SUFFIX = ".changeset.json"`, `cli.py:52`). **Questo è il canale dei "candidati".**
2. **Agente localizza via i propri tool MCP** (`search_code`/`find_symbol`/`who_calls`), derivando le query
   con la stessa regola G6, e scrive `located.json`. **Questo è il canale di rientro dell'evidenza.**
3. **`speclift bundle --changeset <path> --located <path> [--out]`** — **marcia 1, nuova modalità** dello
   stesso comando `bundle` (`cli.py:154-247`). Ricostruisce il changeset, crea
   `ProvidedEvidenceLocator(located_payload)`, chiama `build_bundle_from_changeset(...)` e produce lo
   **stesso** `<out>.bundle.json` dell'Adapter A. Poi `speclift assemble` (marcia 2) è **identico** al
   percorso di default.

**Nuovi flag CLI (FATTO):**
- `speclift bundle --changeset PATH` (`cli.py:200-204`), `--located PATH` (`:205-209`).
- **Vincoli fail-loud** (`cli.py:214-224`): `--changeset` e `--located` vanno **insieme** (exit **2** se uno
  manca); `--changeset` è **alternativo** a `<ref>`/`--staged`/`--range` (exit **2** se combinati).
- `speclift changeset --out` produce il file `.changeset.json`; senza `--out` va su stdout.

> **NOTA CRUCIALE.** I loro flag **NON** si chiamano `--candidates-out`/`--evidence` (i nomi che avevamo
> *inventato* noi). Sono: comando separato **`changeset`** (con `--out`) per i candidati, e
> **`bundle --changeset/--located`** per il rientro. Vedi §Impatto.

**Percorso di default invariato (FATTO):** `speclift bundle <ref>` (senza i flag) resta l'Adapter A
CLI-vehicle (`cli.py:233-247`).

---

## 3. Formato dell'evidenza (`serialize.py` + `query_keys.py`)

### 3a. `located.json` — evidenza in ingresso (l'agente la produce)
**FATTO** (`evidence-locator-port.md:58-64`, e consumo in `provided_locator.py`):
```json
{
  "symbols": { "<file_path>::<query>": [ {"name","path","line"?,"kind"?,"provenance"?} ] },
  "tests":   { "<symbol_name>": [ {"name","path","covers_symbol","line"?,"provenance"?} ] }
}
```
- Chiave di `symbols` = **composita** `"<file_path>::<query>"` (es. `"calc.py::multiply"`,
  `test_three_gear_flow.py:74`). Chiave di `tests` = **nome simbolo** (es. `"multiply"`, `:75-79`).
- **Nessun** `changeset_ref` top-level in `located.json` (FATTO: assente in test e contratto).
- Chiave assente = `[]` onesto, non errore.

### 3b. `changeset.json` — candidati in uscita (SpecLift lo produce)
**FATTO** (`serialize.changeset_to_dict:232-245`): forma completa del `Changeset`:
```json
{ "version": "<contract_version>", "changeset_ref": "<ref>", "kind": "commit",
  "files": [ { "path", "change_type", "old_path", "is_binary",
               "hunks": [ {"file_path","old_range","new_range","candidate_identifiers","lines"} ] } ],
  "excluded_sources": [ ["path","motivo"] ] }
```
- L'hunk del changeset **include `lines`** (il diff testuale, `_changeset_hunk:192-199`) — a differenza
  dell'hunk del *bundle* che lo omette. Serve all'agente per decidere cosa cercare
  (`serialize.py:186-189`, e assert `test_three_gear_flow.py:70`).

### 3c. Chiavi di query (`domain/query_keys.py`) — G6 condivisa
**FATTO.** Nuovo modulo puro `build_identifier_queries(identifiers, snippet, max_queries) -> list[str]`
(`query_keys.py:12-23`): identificatori deduplicati e limitati a `max_queries`; fallback alla prima riga
non vuota dello snippet **solo se** è un identificatore singolo valido (`.isidentifier()`). `SertorRagLocator`
è stato **refactorato** per usarlo (vedi §6): garantisce che i due adapter derivino le **stesse** chiavi.

---

## 4. `SKILL.md` aggiornato

**FATTO** (`skills/speclift/SKILL.md`, diff). Ora ha **due procedure**, con selezione a monte (`:34-43`):
- **Percorso A (default):** progetto espone `sertor-rag` come CLI-vehicle → Procedura A (marce 1+2, invariata).
- **Percorso B (alternativo):** «il progetto NON espone una CLI-vehicle invocabile da subprocess, ma tu hai
  accesso diretto ai tool MCP di Sertor (`search_code`/`find_symbol`/`who_calls`)» → Procedura B.

**Procedura B** (`:128-181`): 3 passi — (1) `speclift changeset <ref> --out …`; (2) «Localizza TU, coi tuoi
tool MCP» derivando le query con la stessa regola G6 e usando `search_code`/`find_symbol` per i simboli,
`who_calls`/`search_code` per i test, scrivendo `located.json` (schema mostrato inline `:157-166`); (3)
`speclift bundle --changeset … --located … --out …`, poi prosegue con autoring+assemble di Procedura A.

**Host-agnostica? (FATTO/INFERENZA).** La skill **nomina i tool MCP di Sertor** (`search_code`/`find_symbol`/
`who_calls`) — che sono vehicle **di Sertor** (il framework consumato), non del progetto ospite. **NON**
contiene path-assistente (`.claude/`/`.github/`), **NON** slash-command, **NON** nomi-modello (verificato via
grep sul diff — FATTO). Il contratto lo dichiara host-agnostico (`evidence-locator-port.md:79-80`): sceglie A
o B «in base a cosa l'host espone… non hardcoda un assistente specifico». **INFERENZA:** è la stessa postura
di confine che avevamo adottato noi nel plan 084 (Principio X «forma agnostica, contenuto Sertor-targeted»).

---

## 5. Contratto `evidence-locator-port.md`

**FATTO** (nuovo file, 80 righe). Dichiara:
- Porta **invariata** (`:16-26`): `locate_symbols`/`locate_tests`; `[]` = non-trovato onesto, mai eccezione;
  il **moat** (`AnchorResolver.verify`/`anchor_fs`) riverifica sul filesystem **indipendentemente** dall'adapter.
- **Adapter A** = `SertorRagLocator` (CLI-vehicle, un solo stadio di giudizio, default, `:28-32`).
- **Adapter B** = `ProvidedEvidenceLocator` (`:34-46`).
- **Compromesso «agente in 2 stadi» dichiarato apertamente** (`:41-46`): con l'Adapter B l'agente partecipa a
  **due** stadi (localizzazione **E** stesura EARS), deviazione esplicita dal «deterministic-sandwich a un
  solo stadio di giudizio» che resta il default; la garanzia forte che resta intatta è il **moat**, «non
  l'agente non ha mai visto il retrieval». «Perché non rompe il resto del contratto» (`:73-80`): moat,
  bundle-schema e `assemble` invariati; skill host-agnostica.

---

## 6. `rag_sertor.py` — cosa è cambiato

**FATTO** (diff, 10 righe). L'adapter CLI **resta presente e attivo** (NON deprecato, è l'Adapter A di
default). L'unico cambiamento: il metodo privato `_build_queries` (che aveva la logica G6 inline) ora
**delega** al modulo condiviso: `return build_identifier_queries(identifiers, snippet,
self._config.max_queries_per_symbol)` (`rag_sertor.py:76-77`), con `import` aggiunto (`:22`). Il corpo G6
duplicato è stato rimosso. Semantica identica; serve solo a garantire che i due adapter derivino le stesse
chiavi. `_search` (subprocess `sertor-rag search --type code --json -k 5`) **invariato**.

---

## 7. Test

**FATTO.** 18 test nuovi + poche estensioni (122 verdi totali secondo il commit). Verificati offline:
- `tests/unit/test_provided_locator.py` — **9 test** (`:20-84`): mapping, degrado a `[]` su chiave assente,
  cap query rispettato, dedup, G6 (no query da snippet non-identificatore / fallback da identificatore),
  `locate_tests` per nome. Fed da dict inline, **nessun RAG/MCP** (offline).
- `tests/unit/test_query_keys.py` — **5 test** (`:10-30`): dedup/filtro vuoti, cap, fallback G6. Puri, offline.
- `tests/integration/test_three_gear_flow.py` — **3 test** (`:49,144,150`): flusso completo
  changeset→located(scritto a mano)→bundle→assemble su **git-fixture locale** (`make_repo`, `StubEarsAuthor`,
  `_UnusedLocator` che fallisce rumoroso se la marcia 0 tocca il locator, `:30-37`); + rifiuto flag
  incompleti (exit 2) e flag mescolati con `<ref>` (exit 2). **Nessun RAG/MCP reale** — la localizzazione è
  simulata scrivendo `located.json` a mano (`:73-82`), come farebbe l'agente. `pytestmark = integration`.
- `tests/unit/test_serialize_roundtrip.py` — **+1 test** changeset round-trip (`changeset_to_dict` ↔
  `changeset_from_dict` preserva `lines`).

**Tutti offline (FATTO):** nessuna dipendenza da RAG/MCP/rete; git-fixture + fake. Confermato `20 passed`.

---

## Impatto sul nostro plan 084

Riferimento: `specs/084-speclift-self-host/plan.md` + `contracts/agent-evidence-interface.md`. Il nostro plan
progettava un design **inventato** (`AgentEvidenceLocator`, flag `--candidates-out`/`--evidence`). Upstream
ha ora consegnato la **loro** versione reale. **Adottare la loro** elimina la divergenza dal vendoring (la
nostra intera modifica al codice vendorato sparisce: il loro codice è già mergiabile così com'è).

### Cosa va SOSTITUITO (adottare il LORO codice/flow/formato)

| Nostro plan 084 (inventato) | Loro reale (`00d5cd0`) — da adottare |
|---|---|
| **Swap**: rimuovi `rag_sertor.py`, aggiungi `agent_evidence.py::AgentEvidenceLocator` | **Pluggable**: `rag_sertor.py` **resta**; aggiungi `provided_locator.py::ProvidedEvidenceLocator`. Entrambi dietro la porta. **Non rimuovere nulla** → vendoring più pulito |
| Flag `speclift bundle <ref> --candidates-out cand.json` | Comando separato **`speclift changeset <ref> --out …`** (marcia 0) |
| Flag `speclift bundle <ref> --evidence evidence.json` | **`speclift bundle --changeset … --located …`** (alternativo a `<ref>`) |
| `evidence.json`: `symbols` chiavati per **`file_path`**, con `changeset_ref` top-level | `located.json`: `symbols` chiavati per **`"<file_path>::<query>"`** (composita), **senza** `changeset_ref` |
| candidati: `{files:[{path, hunks:[{candidate_identifiers, snippet}]}]}` | changeset completo via `changeset_to_dict`: hunk con `file_path/old_range/new_range/candidate_identifiers/**lines**` |
| Nuovo `EvidenceInputError` (**exit 6**), validazione al `__init__` | **Nessun** errore nuovo. `ProvidedEvidenceLocator` non valida; il CLI mappa malformato → **exit 5** (`BundleContractError`-range) e flag-misuse → **exit 2** |
| G6 duplicata / non condivisa (rag_sertor rimosso) | **`domain/query_keys.py`** condiviso da entrambi gli adapter |
| `pipeline`: `emit_candidates()` + swap `default_components` | `pipeline`: `build_changeset()` + `build_bundle_from_changeset()` (seam; default li chiama entrambi) |
| `contracts/agent-evidence-interface.md` (nostro) | `contracts/evidence-locator-port.md` + `cli.md` (loro) — usare i loro |

Conseguenza pratica: **il nostro plan diventa vendoring-puro**. Non serve più «swap del locator» né file
divergenti (`config.py` invariato — loro non toccano `config.py`; `rag_sertor.py` resta). La feature 084 si
riduce a: vendorare il branch `feat/speclift-pluggable-locator` così com'è + integrazione workspace + skill
dogfood (che loro forniscono già in Procedura B).

### Cosa RESTA valido del nostro plan 084 (deciso da noi, non toccato da upstream)

- **Python `>=3.11`** (D-4): upstream ha `requires-python = ">=3.12"` (FATTO `pyproject.toml:6`) — la
  riconciliazione a 3.11 con verifica empirica **resta una nostra decisione di vendoring**.
- **`jsonschema` → dev-only, runtime `[]`** (D-2): invariato.
- **`LICENSE` MIT** (D-7): upstream **ancora senza LICENSE** (FATTO: `ls LICENSE → No such file`) — il nostro
  finding e l'aggiunta MIT nel pacchetto vendorato restano validi.
- **Skill dogfood** (`.claude/skills/speclift/SKILL.md`): il deposito resta nostro; ma il **contenuto** è ora
  la **loro Procedura B** (già scritta), non una skill da estendere noi.
- **Integrazione workspace** (D-1/D-5/D-6/D-8): membri `uv`, `ruff extend-exclude`, marker pytest, versione
  statica, esclusione dal packaging distribuibile — tutto invariato.
- **`sertor_core` byte-identico** (Principio XI) e **retrieval solo via MCP nella skill**: invariato — e ora
  **rafforzato**, perché è esattamente il Percorso B che upstream ha reso di prima classe.
- **Tracciamento scope** (FEAT-002 distribuzione, IT→EN, gap code-graph): invariato. **INFERENZA:** il
  «feedback a Sinthari» (FR-017) è di fatto **già stato recepito** da questo commit → quel rinvio si chiude.

### Note di allineamento (INFERENZE)

- Il nostro `contracts/agent-evidence-interface.md` e i riferimenti a `AgentEvidenceLocator`/`--candidates-out`/
  `--evidence`/`EvidenceInputError`/`emit_candidates` vanno **riscritti** per puntare al design reale, oppure
  il plan 084 va **rigenerato** su «adotta il branch pluggable» (raccomandato: rigenerare, il delta è ampio).
- Il loro design **preserva** il moat e il sandwich-di-default meglio del nostro (l'Adapter A resta
  disponibile per ospiti con CLI-vehicle); il nostro «swap» li avrebbe **esclusi**. Adottando il loro,
  l'ospite può scegliere A o B — più host-agnostico.
