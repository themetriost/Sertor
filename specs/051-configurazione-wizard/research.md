# Research — `sertor configure` (Phase 0)

**Feature**: 051-configurazione-wizard · **Branch**: `051-configurazione-wizard` · **Date**: 2026-06-17

**Input**: `spec.md` (5 user story, 23 FR, 9 SC) + `requirements/sertor-cli/configurazione/requirements.md`
(decisioni di scope Q1–Q4 chiuse). Qui si risolvono solo le **ambiguità di *come*** delegate al plan
(spec §Assumptions, requirements §10). Ogni decisione cita il codice reale (`path:lineno`).

> **Nota di processo (deviazione segnalata):** il workflow canonico prevede
> `.specify/scripts/powershell/setup-plan.ps1 -Json`. Questo script **non esiste** in `.specify/`
> (presenti solo `feature.json`, `memory/`, `templates/`). Anche `.claude/skills/speckit-plan/SKILL.md`
> **non esiste** (skill presenti: `requirements`, `wiki-author`). Ho ricavato `FEATURE_SPEC`/`IMPL_PLAN`/
> `SPECS_DIR`/`BRANCH` per convenzione dal nome-branch (già `051-configurazione-wizard`, directory
> `specs/051-configurazione-wizard/` già presente). Nessun hook `EXECUTE_COMMAND` eseguito.

---

## Confine architetturale che ancora tutte le decisioni

Il pacchetto **`sertor`** (l'installer, `packages/sertor`) **dipende da `sertor-core`**
(`packages/sertor/pyproject.toml`: `dependencies = ["sertor-core", "sertor-install-kit"]`) e già
importa `sertor_core.domain.errors`/`Settings` nel suo `__main__.py:14,30`. Quindi `sertor configure`:

- **PUÒ** importare `Settings`/`validate_backend` direttamente: è **lettura statica pura**
  (`settings.py:194-215`), non un'operazione runtime tracciata (indicizzazione/retrieval). Il
  Principio XI vieta di consumare a runtime *capacità* del core via libreria (es.
  `build_indexer().index()`); leggere la config e chiamare il validatore statico non è una di quelle
  operazioni e non bypassa osservabilità (non c'è nulla da tracciare). Lo fa già la CLI `sertor-rag`
  in `_check_backend` (`cli/__main__.py:183-189`).
- **NON DEVE** importare `build_embedder()` per il probe live: una chiamata di embedding reale **è**
  un'operazione runtime osservabile → va esercitata via **vehicle** (`sertor-rag`), non via libreria
  (Principio XI). Vedi Punto 3.

Lo scaffold/scrittura del `.env` riusa il toolkit del kit (`env_merge.merge_env`,
`env_merge.py:44-88`), già usato da `install rag` (`install_rag.py:238-242`) — niente logica nuova
(NFR-02, Principio III/DRY).

---

## Punto 1 — Rilevamento TTY, modalità interattiva vs flag-driven, comportamento CI-safe

**Decisione.** Modalità **ibrida** decisa per campo, sull'asse «ho già un valore? c'è un TTY?»:

1. Per ogni campo richiesto dal profilo, il valore si risolve nell'ordine: **flag esplicito**
   (`--set KEY=VAL`, o le scorciatoie `--backend`/`--store`) → **valore già presente** in
   `.sertor/.env` (non vuoto) → **prompt interattivo** se e solo se `sys.stdin.isatty()` **e**
   `sys.stdout.isatty()` sono veri.
2. **Interattivo** = c'è un TTY e mancano valori → si prompta (Punto 2).
3. **Non interattivo** = nessun TTY **oppure** `--non-interactive`/`--yes` esplicito → **mai** un
   prompt. Se al termine della risoluzione resta un campo richiesto senza valore → **errore esplicito**
   `ConfigError` che **nomina i campi mancanti**, **exit 1**, **senza scrivere configurazione parziale**
   (FR-005, REQ-005).

**Razionale.** Replica esattamente il pattern CI-safe già consolidato nell'installer: il gate
`--purge-wiki` in `__main__.py:264-291` usa `sys.stdin.isatty()` → ramo interattivo, `args.yes` →
ramo non interattivo, e «no TTY e no `--yes` → default sicuro non distruttivo». Stessa decisione D4 di
`lifecycle-installer` citata nei requirements. Si controllano **entrambi** stdin e stdout perché un
prompt scritto su stdout rediretto non sarebbe visibile (CI con stdout su file).

**Determinismo (NFR-05).** Nessun prompt nascosto: la sola condizione che attiva un prompt è
`isatty() ∧ valore mancante ∧ ¬--non-interactive`. In CI (`isatty()=False`) il ramo prompt è
irraggiungibile per costruzione.

**Alternative scartate.**
- *Solo flag-driven (Q1 b)* — scartata a monte (decisione Q1 a): perde l'esperienza «wizard».
- *Heuristica su `CI=true`* — fragile e non portabile; `isatty()` è il segnale canonico già in uso.

---

## Punto 2 — Presentazione dei prompt (per campo) e mascheramento dei segreti

**Decisione.** Un prompt per campo richiesto-e-mancante, costruito da un **descrittore di campo** (vedi
data-model `ConfigField`): mostra `name` (la chiave env, es. `AZURE_OPENAI_ENDPOINT`), una `description`
breve, e — se presente — il **valore corrente mascherato** (`AZURE_OPENAI_API_KEY (current: ****…3f2a)`).

- **Campi non segreti** → `input()` standard, eco normale.
- **Campi segreti** (`secret=True` nel descrittore) → input via **`getpass.getpass()`** (stdlib): non
  riecheggia il testo digitato sul terminale (FR-013, NFR-01). Mai stampare il valore digitato.
- **Default / invio a vuoto**: se esiste un valore corrente non vuoto, invio a vuoto = «tienilo»; se il
  campo ha un default sensato non-segreto dal template (es. `AZURE_OPENAI_EMBED_DEPLOYMENT=
  text-embedding-3-large`, `env.azure.tmpl:7`), lo si propone come default.

**Mascheramento (funzione pura, riusabile da prompt e report).** `mask_secret(value) -> str`:
stringa vuota → `"(unset)"`; altrimenti `"****" + ultimi≤4 caratteri` (mai più di 4, mai per valori
corti < 8 → solo `"****"`). È l'**unico** punto che decide come si mostra un segreto, usato sia nei
prompt sia nel report (Punto 6), così non esiste un percorso che stampi un segreto in chiaro
(SC-008, FR-013).

**Razionale.** `getpass` è stdlib, già il mezzo standard per input nascosto; non aggiunge dipendenze
(Principio III). La decisione «quali campi sono segreti» NON è duplicata nel comando: deriva dal
descrittore (vedi Punto sotto, fonte unica).

**Alternative scartate.**
- *Una libreria di prompt (questionary/rich-prompt)* — dipendenza pesante non giustificata (YAGNI,
  Principio III); l'installer non ne usa.

---

## Fonte unica dei campi richiesti (NFR-04, FR-002) — pilastro trasversale

`Settings.validate_backend()` (`settings.py:194-215`) è **la** fonte di verità su «quali variabili
servono per la combinazione scelta»: ritorna i **nomi** delle env mancanti per `backend`/`store_backend`.
Il comando NON duplica questa lista. Ma `validate_backend` ritorna **solo i nomi** (non descrizione né
flag-segreto), quindi serve un **catalogo descrittivo statico** che mappa `nome → (description, secret)`
per i campi che il validatore può nominare. Questo catalogo:

- **non è una seconda lista di "quali campi servono"** (quella resta `validate_backend`): è puro
  *metadato di presentazione* (testo + flag segreto) per i nomi che il validatore già conosce;
- un **test di copertura** (Principio V) verifica che ogni nome che `validate_backend` può emettere per
  ciascun backend/store abbia una voce nel catalogo → niente drift silenzioso. Se il core aggiunge un
  campo richiesto, il test fallisce finché il catalogo non lo copre.

Insieme dei nomi che `validate_backend` emette oggi (verificato in `settings.py:203-214`):
`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_EMBED_DEPLOYMENT` (backend azure);
`AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY` (store azure). Profilo locale (Ollama+Chroma) → lista
vuota → nessun campo richiesto (FR-006, SC-007: local-only senza cloud).

---

## Punto 3 — Forma del probe live `--check`

**Decisione.** Il probe live è **opt-in** (`--check`), separato dalla validazione statica, ed è
eseguito **via il vehicle `sertor-rag`** invocato come **subprocess** (Principio XI), **non**
importando `build_embedder`. Meccanismo:

- il comando individua l'eseguibile `sertor-rag` del **runtime isolato** dell'ospite (`.sertor/`)
  tramite il `SubprocessRunner`/`CommandRunner` del kit (`command_runner.py`), nello stesso modo in cui
  `install rag` invoca `uv`/`claude`;
- richiede a `sertor-rag` un **embed minimo di prova** (una sola stringa breve, es. `"ping"`),
  registrato come operazione → osservabilità/errori cablati dal vehicle (Principio XI/IX);
- l'esito (ok / fallito + motivo azionabile) è riportato **separatamente** dalla validazione statica
  nel report (Punto 6). Fallimento del probe → **exit 1** (FR-023), **senza** scartare il `.env` scritto.

**Dipendenza di prodotto rilevata → promossa (non lasciata nello spec).** `sertor-rag` **oggi non ha**
un comando «embed di prova»: ha `index`/`search`/`observe`/`memory` (`cli/__main__.py:48-90`). `search`
richiede un indice esistente (`engine.ensure_index()`, `:279`) → non adatto come probe a freddo (l'ospite
ha config ma nessun indice). Servono due tasselli, di cui il primo è **core**:

1. **(core — `sertor-core`)** un sottocomando minimale del vehicle, es. `sertor-rag check`
   (o `--probe`), che fa una **singola** chiamata di embedding (`build_embedder(settings).embed(["ping"])`
   dentro il vehicle, con `enable_observability` già cablato), riporta ok/errore in forma machine-readable
   ed esce 0/1. È **lavoro di `sertor-core`** (estende il vehicle), NON di questa feature `sertor`.
2. **(questa feature — `sertor`)** `sertor configure --check` invoca quel comando via subprocess e ne
   integra l'esito nel proprio report.

**Promozione del debito (regola «Out of Scope si promuovono»):** poiché il tassello (1) è una capacità
di prodotto reale e ricade in un'altra unità (`sertor-core`), va promosso a una casa durevole **prima**
che US5/`--check` conti come *done*. Mapping proposto: nuova riga **FEAT-NNN «probe di connettività del
vehicle» nel backlog `requirements/sertor-core/…`** (Should, gemella del self-test MCP già citato in
`CLAUDE.md`/`server.py`). Vedi §«Capacità da promuovere» in fondo e il report finale.

**Confine MVP di questa feature.** Il **valore P1** (US1/2/3) è completo con la **sola validazione
statica** (probe = Should, P2, spec §Assumptions). Opzioni per chiudere il piano senza bloccarsi:
- **(consigliata)** implementare il tassello (1) `sertor-rag check` **in parallelo come piccolo lavoro
  di core** e cablare `--check`; oppure
- **(ripiego)** consegnare `sertor configure` con `--check` che, se il sottocomando-probe non è
  disponibile nel `sertor-rag` installato, **degrada onestamente**: riporta «probe live non disponibile
  in questa versione del runtime» (NON un crash), exit invariato dalla validazione statica. Mai un probe
  importando la libreria (Principio XI).

**Razionale.** Embed di una sola stringa = costo trascurabile, è l'operazione reale minima che prova
endpoint+chiave+deployment (Azure) o raggiungibilità di Ollama. Passare per il vehicle garantisce che
anche il probe sia osservato e che gli errori siano avvolti al boundary (Principio IV/IX/XI). Mai rete
senza `--check` (FR-022, SC-009 spirito install≠run).

**Alternative scartate.**
- *Importare `build_embedder` nel comando configure* — viola il Principio XI (operazione runtime via
  libreria, bypassa il wiring del vehicle); scartata.
- *Riusare `sertor-rag search` come probe* — richiede un indice, fallirebbe a freddo per la ragione
  sbagliata; non discrimina «config valida» da «indice assente».
- *Probe HTTP grezzo nel comando (httpx diretto)* — duplicherebbe la logica dell'adapter
  (`azure.py`/`ollama.py`), violerebbe DRY (Principio III) e il boundary (Principio II); scartata.

---

## Punto 4 — Nomi comando/flag e mappatura exit code

**Decisione.** Nuovo sottocomando `sertor configure` (Q2 a), forma:

```
sertor configure [rag]
                 [--target DIR]                 # default: cwd  (come install/upgrade/uninstall)
                 [--backend {azure,local}]      # scorciatoia: imposta RAG_BACKEND
                 [--store {local,azure}]        # scorciatoia: imposta SERTOR_STORE_BACKEND
                 [--set KEY=VALUE ...]           # valore esplicito per qualunque campo (ripetibile)
                 [--overwrite]                   # consenti la sovrascrittura di valori già presenti
                 [--non-interactive]             # forza il ramo flag-driven anche con TTY
                 [--check]                       # probe live opt-in (Punto 3)
                 [--json]                        # report machine-readable
```

- `rag` è il **solo** sottocomando-capacità (posizionale opzionale, default `rag`): oggi l'unica
  capacità con provider da configurare è il RAG (wiki/governance non ne hanno — spec §Fuori ambito).
  Tenerlo esplicito lascia spazio coerente con `install <capability>` senza prometterne altri.
- `--set KEY=VALUE` è la via generica e CI-friendly per qualunque campo (inclusi i segreti, anche se
  in CI è preferibile passarli via **ambiente** — vedi sotto); `--backend`/`--store` sono scorciatoie
  ergonomiche per le due scelte di profilo.
- **Ambiente come sorgente in CI:** un valore già presente nell'ambiente del processo (es.
  `AZURE_OPENAI_API_KEY` esportato dalla CI) viene letto da `Settings.load()` e conta come «fornito»
  → nessun prompt, nessun obbligo di `--set` per i segreti (CI-safe, FR-004).

**Exit code (FR-032, REQ-032), allineati a `sertor-rag`/`sertor` esistenti:**

| Code | Condizione |
|------|------------|
| `0` | configurazione completa **e** valida (validazione statica senza campi mancanti; se `--check`, anche probe ok) |
| `1` | configurazione incompleta/invalida (campi mancanti), **oppure** probe `--check` fallito, **oppure** errore di dominio (`SertorError`/`InstallerError`) |
| `2` | uso errato (argparse: `--backend` con valore non valido, `--set` malformato senza `=`, combinazione vietata) |

Il dispatch e la mappatura 0/1/2 riusano lo schema di `sertor` `main()`
(`__main__.py:383-402`): `UsageError`→2, `SertorError|InstallerError`→1.

**Razionale.** Coerenza con le convenzioni dell'installer (NFR-06): `--target`, `--json`, exit 0/1/2 già
in uso (`__main__.py`). `--overwrite` (e non `--force`) per allinearsi al lessico «non distruttivo» dei
requirements (REQ-011 nomina `--overwrite`/`--force`; si sceglie `--overwrite`, più descrittivo).

**Alternative scartate.**
- *`sertor install rag --configure`* — Q2 b, scartata a monte (accoppia install e config).
- *Comando top-level senza posizionale-capacità* — meno estensibile e meno coerente con `install <cap>`.

---

## Punto 5 — Scrittura: riuso di `env_merge`, overwrite, scaffold del `.env` assente

**Decisione.** La scrittura riusa **`merge_env`** del kit (`env_merge.py:44-88`), che è già
additivo-non-distruttivo (aggiunge solo le chiavi **mancanti**, **mai** sovrascrive un valore esistente,
preserva righe/commenti) e idempotente. Strategia in tre passi:

1. **`.env` assente** (`.sertor/.env` non esiste) → **scaffold dal template di backend**
   (`env.{azure,local}.tmpl`) **senza avviare il RAG** (FR-015, REQ-015): si riusa esattamente
   `_apply_env`-equivalente — `read_asset_text("rag/env.{backend}.tmpl").format(corpus=...)` +
   `merge_env(path, rendered)` (`install_rag.py:238-242`). Il `corpus` di default = nome cartella
   sanitizzato (`sanitize_corpus`, `rag_profile.py:23`). Nessun `uv`, nessun indice (install≠run, FR-030).
2. **Valori NUOVI per chiavi mancanti** → `merge_env` li aggiunge (è il suo comportamento nativo).
3. **Overwrite di una chiave già valorizzata** (FR-011, REQ-011) → `merge_env` da solo **non**
   sovrascrive; serve un passo dedicato **prima** del merge: per ogni chiave che l'utente vuole
   cambiare e che ha già un valore non vuoto:
   - **`--overwrite`** presente → sovrascrivi (riusa il primitivo `_replace_key_line`,
     `env_merge.py:32-41`, già nel kit) — **funzione esistente, niente nuova logica**;
   - **interattivo (TTY)** → chiedi conferma puntuale; conferma sì → sovrascrivi, no → conserva;
   - **non interattivo senza `--overwrite`** → **conserva** il valore esistente e **annota** nel report
     che è stato preservato (non un errore: la non-distruttività è il default sicuro).

**Idempotenza (FR-014, SC-005).** Stessi input due volte → secondo run: tutte le chiavi già presenti
con lo stesso valore → `merge_env` ritorna `SKIPPED`/nessuna modifica; i passi di overwrite riscrivono lo
stesso valore → contenuto identico. Verificabile per byte (test).

**Segreti (FR-012, SC-003).** I segreti finiscono **solo** in `.sertor/.env`, già git-ignored
(`gitignore_append.RUNTIME_IGNORES`, install rag) — nessun file versionato viene toccato dal comando.

**Razionale.** Zero logica nuova di parsing/scrittura `.env`: si compongono `merge_env` +
`_replace_key_line` esistenti (DRY, Principio III; NFR-02). La gestione overwrite è l'unico
comportamento aggiuntivo, costruito sopra primitivi già testati.

**Alternative scartate.**
- *Riscrivere un parser `.env` nel comando* — duplicazione, scartata (DRY).
- *`merge_env` esteso con un flag `overwrite`* — possibile, ma cambierebbe la firma usata da `install
  rag`; preferito comporre `_replace_key_line` lato comando per non toccare il percorso install (NFR
  non-regressione). (Da valutare in tasks se un piccolo helper condiviso nel kit è più pulito — resta
  scelta di implementazione, non architetturale.)

---

## Punto 6 — Forma del report (umano + `--json`), zero segreti

**Decisione.** Una **entità di esito** `ConfigureReport` (data-model) + due funzioni di resa **pure**
(`render_human`/`render_json`), nello stile di `InstallReport` (`report.py`) e di
`cli/output.py` del core. Contenuto:

- `backend` (azure|local), `store` (local|azure|none);
- `fields`: per ogni campo del profilo → `name`, `status` ∈ {`set`, `kept`, `missing`}, e per i segreti
  il **valore mascherato** (`mask_secret`, Punto 2) — **mai** il valore in chiaro;
- `validation`: `complete: bool` + `missing: [name…]` (da `validate_backend`);
- `live_check` (solo se `--check`): `{requested: bool, ok: bool|null, detail: str}` — `null` quando non
  richiesto o non disponibile (degrado onesto, Punto 3);
- `exit_code` derivato (0/1).

**Garanzia anti-leak (SC-008, FR-013).** Il report **non contiene mai** un valore segreto: i campi
segreti vi entrano **solo** già mascherati da `mask_secret`. Un test (Principio V) asserisce che, dato
un segreto noto in input, esso **non** compare né in `render_human` né in `render_json`. Lo stesso vale
per gli eventi di osservabilità emessi dal comando (solo conteggi/nomi-campo, mai valori — pattern
`memory_list`/`memory_show` in `cli/__main__.py:350-370`).

**Razionale.** Riuso del pattern report già consolidato (umano + `--json`, exit code derivato); il
mascheramento centralizzato in `mask_secret` rende impossibile un percorso che stampi un segreto.

**Alternative scartate.**
- *Redigere a valle (alla stampa)* — fragile: un punto dimenticato perde un segreto. Mascherare
  **all'ingresso** del report è strutturalmente più sicuro.

---

## Capacità da promuovere (regola «Out of Scope si promuovono», non lasciate nello spec)

| Capacità rinviata | Casa durevole proposta | Priorità |
|-------------------|------------------------|----------|
| **Probe di connettività del vehicle** (`sertor-rag check` / embed di prova osservato) — prerequisito di core per `sertor configure --check` | **Nuova FEAT nel backlog `requirements/sertor-core/`** (gemella del self-test MCP, `server.py`) | Should |
| **Wizard delle manopole opzionali** (cache/observability/engine/graph/limiti) | già tracciato: spec §Assumptions «estensione *Could*» + epica `sertor-cli` | Could |
| **Estensione provider/store** (OpenAI pubblico, PGVector, …) | già `epica backend-store-scala` (citata in spec/requirements) | Won't (qui) |

> Il primo va creato nel backlog **prima** che `--check`/US5 conti come completo (vedi report finale,
> brief al `configuration-manager`/follow-up). Gli altri due hanno già casa.

---

## Errore MCP riscontrato (dogfooding — segnalato, non sepolto)

Durante la ricognizione, `mcp__sertor-rag__search_code` ha restituito:
`Error executing tool search_code: error during vector store query [backend=chroma, reason=InternalError]`.
Ho ripiegato su `Read`/`Grep`/`Glob` per non bloccarmi, ma l'errore è reale e va visto: l'indice
dogfood Chroma sembra in stato di errore interno alla query (possibile indice stantio/corrotto o
backend non inizializzato). **Segnalato nel report finale** come segnale di affidabilità del nostro
stesso strumento (Principio dogfooding / regola standing su errori MCP).
