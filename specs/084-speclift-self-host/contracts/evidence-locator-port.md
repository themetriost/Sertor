# Contratto — Porta `EvidenceLocator` (adottiamo quella upstream, pluggable)

**Feature**: speclift FEAT-001 (self-host) · **Branch**: `084-speclift-self-host`

> **Questo contratto NON reinventa nulla.** Con il vendoring puro da Sinthari `5ee6fc1` **adottiamo
> tale-e-quale** il contratto upstream della porta `EvidenceLocator` e del suo formato di scambio. La
> fonte di verità autoritativa è il file upstream, vendorato con il pacchetto:
>
> - **`packages/speclift/specs/001-speclift-mvp/contracts/evidence-locator-port.md`** (copia vendorata di
>   `Sinthari/specs/001-speclift-mvp/contracts/evidence-locator-port.md` @ `5ee6fc1`).
>
> Questo file di plan documenta **quale** delle due vie upstream usa il self-host e **come** ne
> garantiamo l'uso — non ridefinisce lo schema (sarebbe un secondo contratto che può divergere → contro
> Principio XII/III).

## Perché era un contratto NOSTRO, e ora non lo è

Il precedente plan 084 inventava un'interfaccia propria (`AgentEvidenceLocator`, flag
`--candidates-out`/`--evidence`, `evidence.json` con `changeset_ref` top-level, `EvidenceInputError`
exit 6) perché all'epoca upstream aveva **un solo** adapter (CLI-vehicle). Il 2026-07-01 Sinthari ha
**recepito il nostro feedback di dogfooding** e mergiato su `master` (`5ee6fc1`) una versione
**pluggable** della porta: un secondo adapter `ProvidedEvidenceLocator` che consuma evidenza già
localizzata dall'agente via i suoi tool MCP, **senza** rimuovere l'adapter CLI. → La nostra interfaccia
inventata è **superata**: adottiamo la loro, il vendoring diventa **puro** (zero fork del codice).

## La porta (upstream, invariata)

```text
EvidenceLocator.locate_symbols(file_path: str, identifiers: list[str], snippet: str) -> list[Symbol]
EvidenceLocator.locate_tests(symbol: Symbol) -> list[TestRef]
```

`[]` = "non trovato" onesto, mai un'eccezione (degrado onesto). Nessuna àncora nasce qui:
`locate_evidence` la costruisce, e il **moat** (`AnchorResolver.verify` / `anchor_fs.py`) la riverifica
sul **filesystem** — **indipendentemente** dall'adapter che l'ha proposta.

## I due adapter (entrambi vendorati, pluggable)

| Adapter | Classe | File | Come localizza | Uso nel self-host |
|---------|--------|------|----------------|-------------------|
| **A** (default upstream) | `SertorRagLocator` | `adapters/rag_sertor.py` | subprocess `sertor-rag search --type code --json -k 5` via la CLI-vehicle `("uv","run","--project",".sertor","sertor-rag")` | **DORMIENTE** — presente ma non usato dal dogfood |
| **B** (per host MCP) | `ProvidedEvidenceLocator` | `adapters/provided_locator.py` | rilegge `located.json` prodotto dall'agente coi suoi tool MCP; nessun subprocess, nessuna rete | **USATO dal self-host** |

Entrambi derivano le query con la **stessa regola G6** (`domain/query_keys.build_identifier_queries`):
identificatori deduplicati e limitati a `max_queries_per_symbol`, fallback alla prima riga dello snippet
solo se è un identificatore singolo valido. Garantisce che i due adapter rispondano alle **stesse**
chiavi (`provided_locator.py:34`, `rag_sertor.py` refactorato per delegare a `query_keys`).

## Il "three-gear flow" (Adapter B) — quello che usa il dogfood

1. **`speclift changeset <ref> [--staged|--range A..B] [--repo] [--out] [--include-docs]`** — **marcia 0**
   (deterministica): `ingest → parse_diff → filter_sources → STOP`. **Nessuna localizzazione, RAG mai
   toccato.** Emette `<out>.changeset.json` (suffisso `.changeset.json`). È il canale dei **candidati**:
   per ogni file, gli hunk con `candidate_identifiers` **e** le `lines` del diff (l'agente le legge per
   decidere cosa cercare). `cli.py:119-168`, `pipeline.build_changeset`.
2. **L'agente localizza** coi propri tool MCP (`search_code`/`find_symbol`/`who_calls`), deriva le query
   con la regola G6, e scrive **`located.json`** (schema sotto). Canale di rientro dell'evidenza.
3. **`speclift bundle --changeset <path> --located <path> [--out]`** — **marcia 1** (deterministica):
   ricostruisce il changeset, crea `ProvidedEvidenceLocator(located_payload)`, chiama
   `build_bundle_from_changeset(...)`, produce lo **stesso** `<out>.bundle.json` dell'Adapter A.
   `cli.py:213-230`, `pipeline.build_bundle_from_changeset`.
4. **`speclift assemble --bundle … --authored …`** — **marcia 2**: **identica** al percorso di default
   (lift → verify[moat] → render). Nessuna differenza per la marcia 2.

`speclift bundle <ref>` (senza i due flag) e `speclift <ref>` (monolitico) usano l'**Adapter A** →
il self-host **non li usa**.

### Vincoli fail-loud (upstream, adottati — NIENTE exit 6 nostro)

| Condizione | Esito | Ancora |
|------------|-------|--------|
| `--changeset` e `--located` non insieme | exit **2** (flag-misuse) | `cli.py:203-204` |
| `--changeset` combinato con `<ref>`/`--staged`/`--range` | exit **2** | `cli.py:206-208` |
| `changeset.json`/`located.json` illeggibile/non-JSON | exit **5** | `cli.py:217-219` |
| `changeset`/`located` **malformato** (`KeyError`/`TypeError`/`ValueError`) | exit **5** | `cli.py:227-229` |
| chiave assente in `located.json` | `[]` onesto (non errore) | `provided_locator.py:14-15` |

> Gli exit code di dominio restano quelli upstream (`domain/errors.py`): `2` ref invalido · `3` RAG giù
> · `4` EarsAuthor giù · `5` bundle/contratto invalido. **Non introduciamo `EvidenceInputError`/exit 6**
> (era nostro, superato): l'evidenza malformata cade nell'exit **5** upstream.

## Schema `located.json` (upstream — lo adottiamo, non lo ridefiniamo)

```json
{
  "symbols": { "<file_path>::<query>": [ {"name","path","line"?,"kind"?,"provenance"?} ] },
  "tests":   { "<symbol_name>": [ {"name","path","covers_symbol","line"?,"provenance"?} ] }
}
```

- Chiave di `symbols` = **composita** `"<file_path>::<query>"` (es. `"calc.py::multiply"`).
- Chiave di `tests` = **nome simbolo** (es. `"multiply"`).
- **Nessun** `changeset_ref` top-level (a differenza della nostra `evidence.json` inventata).
- `name`/`path` (e `covers_symbol` per i test) obbligatori; il resto ha default (`line=0`, `kind=""`,
  `provenance=""`). Riuso dei modelli di dominio `Symbol`/`TestRef` (`_symbol_from`/`_test_from`).
- Chiave assente = `[]`, non un errore.

## Come il self-host garantisce l'**Adapter B** (no CLI) — Principio XI

Il legame runtime con Sertor è il tool **MCP `search_code`** (vehicle legittimo per gli agenti), **mai**
la CLI `sertor-rag` e **mai** `import sertor_core`. Tre garanzie sovrapposte:

1. **Procedurale (skill).** La skill dogfood (`.claude/skills/speclift/SKILL.md`, copia della upstream)
   seleziona la **Procedura B** per il self-host di Sertor (l'host espone i tool MCP, non una CLI-vehicle
   `sertor-rag` invocabile da subprocess). La Procedura B **è** il three-gear flow sopra.
2. **Strutturale (code path).** Il flow B — `speclift changeset` + `speclift bundle --changeset
   --located` — costruisce `ProvidedEvidenceLocator` e **non invoca mai** `SertorRagLocator.locate_*`
   (l'unico punto in cui l'Adapter A spawnerebbe il subprocess `sertor-rag`). `_cmd_bundle` con
   `--changeset` non chiama nemmeno `default_components` (`cli.py:213-230`). *(Onestà: `_cmd_changeset`
   costruisce `default_components(repo).diff_source`, che istanzia un `SertorRagLocator` **inerte** — la
   costruzione non spawna alcun subprocess, che avviene solo in `locate_symbols`; la marcia 0 non lo
   invoca — cfr. `test_three_gear_flow._UnusedLocator`.)*
3. **Verificabile (tripwire naturale).** Il flow B non spawna alcun subprocess `sertor-rag`. In più, la
   root di Sertor **non ha** un progetto `.sertor/` (Sertor *è* Sertor): se l'Adapter A fosse invocato
   per errore, fallirebbe *loud* (`RagUnavailableError`, exit 3) invece di degradare in silenzio — un
   guasto **visibile**, non un fallback.

## Perché non rompe il resto del contratto (upstream, ereditato)

Il moat, l'`evidence-bundle.schema.json`, l'`output.schema.json` e `assemble` sono **identici** per
entrambi gli adapter: `verify`/`anchor_fs` non sanno né si curano di quale adapter ha proposto un
simbolo/test. La deviazione dal «sandwich a un solo stadio di giudizio» (con l'Adapter B l'agente tocca
**due** stadi: localizza **E** scrive EARS) è una **scelta upstream dichiarata apertamente** nel loro
`evidence-locator-port.md:41-46` — **non** una nostra estensione silenziosa. La garanzia forte che resta
in entrambi i casi è il **moat** (nessun'àncora sopravvive se non verificabile sul filesystem).
