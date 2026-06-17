# Data Model — `sertor configure` (Phase 1)

**Feature**: 051-configurazione-wizard · **Branch**: `051-configurazione-wizard` · **Date**: 2026-06-17

Entità del comando `sertor configure`. Vivono nel pacchetto **`sertor`** (installer); riusano
`Settings`/`validate_backend` del core (lettura statica) e `merge_env`/`_replace_key_line` del
`sertor-install-kit`. Nessun tipo di terze parti trapela (Principio I/II). Nessuna nuova porta del
core: il comando è un consumatore sottile.

---

## 1. `ConfigProfile` — la combinazione scelta (provider × store)

| Campo | Tipo | Note |
|-------|------|------|
| `backend` | `str` ∈ {`azure`, `local`} | provider di embedding (= `RAG_BACKEND`) |
| `store` | `str` ∈ {`local`, `azure`} | store vettoriale (= `SERTOR_STORE_BACKEND`); default = `backend` (come `settings.py:256`) |

- **Insieme delle opzioni = solo ciò che il core onora** (Q4 a, FR-001/SC-004): `backend` ∈
  {azure, local}, `store` ∈ {local, azure}. Nessuna altra opzione è offerta.
- **Profilo locale** = `backend=local, store=local` → `validate_backend()` ritorna `[]` → nessun
  campo cloud richiesto (FR-006, SC-007).
- I campi richiesti per il profilo **non** sono elencati qui: derivano da `validate_backend()` applicato
  a un `Settings` con questo `backend`/`store` (fonte unica, NFR-04, FR-002).

**Validazione (Principio IV, exit 2):** `backend`/`store` fuori dai valori ammessi → usage error
(argparse `choices`), come `install rag` (`__main__.py:103`).

---

## 2. `ConfigField` — descrittore di un campo richiesto (metadato di presentazione)

Catalogo **statico** che mappa il **nome** che `validate_backend` può emettere → metadati di
presentazione. NON è una seconda lista di "quali campi servono" (quella è `validate_backend`): è solo
testo + flag-segreto + default per i nomi che il validatore già conosce.

| Campo | Tipo | Note |
|-------|------|------|
| `name` | `str` | chiave env, es. `AZURE_OPENAI_ENDPOINT` (combacia con l'output di `validate_backend`) |
| `description` | `str` | testo breve mostrato nel prompt (FR-003/REQ-003) |
| `secret` | `bool` | `True` → input via `getpass`, sempre mascherato in output (FR-013) |
| `default` | `str \| None` | default non-segreto proposto (es. `text-embedding-3-large`), o `None` |

**Catalogo iniziale** (verificato su `settings.py:203-214` + `env.azure.tmpl`):

| name | secret | default | gruppo |
|------|--------|---------|--------|
| `AZURE_OPENAI_ENDPOINT` | no | — | backend azure |
| `AZURE_OPENAI_API_KEY` | **sì** | — | backend azure |
| `AZURE_OPENAI_EMBED_DEPLOYMENT` | no | `text-embedding-3-large` | backend azure |
| `AZURE_SEARCH_ENDPOINT` | no | — | store azure |
| `AZURE_SEARCH_API_KEY` | **sì** | — | store azure |

(Profilo locale: nessuna voce richiesta — `OLLAMA_HOST` ha un default valido nel template e
`validate_backend` non lo nomina mai.)

**Invariante di copertura (test, Principio V/NFR-04):** per ogni `backend∈{azure,local}` ×
`store∈{local,azure}`, **ogni** nome emesso da `validate_backend()` ha una voce nel catalogo. Se il core
aggiunge un campo richiesto, il test fallisce → niente drift silenzioso.

---

## 3. `FieldResolution` — esito della risoluzione di un campo

| Campo | Tipo | Note |
|-------|------|------|
| `field` | `ConfigField` | il descrittore |
| `value` | `str \| None` | valore risolto (flag/env/esistente/prompt), o `None` se irrisolto |
| `status` | `FieldStatus` | `SET` (nuovo) · `KEPT` (preservato esistente) · `MISSING` (irrisolto) · `OVERWRITTEN` (sovrascritto su conferma/`--overwrite`) |
| `source` | `str` | provenienza: `flag` · `env` · `existing` · `prompt` · `template-default` |

Risoluzione (Punto 1 research): `--set`/scorciatoia → valore in `.env`/ambiente → prompt (solo TTY) →
default-template. Nessun valore segreto compare mai in chiaro nei report (solo mascherato, §6).

---

## 4. `ValidationOutcome` — esito della validazione statica

| Campo | Tipo | Note |
|-------|------|------|
| `complete` | `bool` | `True` ⇔ `missing == []` |
| `missing` | `tuple[str, …]` | nomi dei campi mancanti, **da `validate_backend()`** (fonte unica) |

`complete=False` → exit 1 + elenco dei mancanti (FR-020/021, SC-002).

---

## 5. `LiveCheckOutcome` — esito del probe live (solo con `--check`)

| Campo | Tipo | Note |
|-------|------|------|
| `requested` | `bool` | `True` solo se passato `--check` |
| `ok` | `bool \| None` | `None` = non richiesto **o** probe non disponibile nel runtime (degrado onesto, research Punto 3) |
| `detail` | `str` | messaggio azionabile su fallimento (FR-023); mai un segreto |

- `requested=False` → **nessuna chiamata di rete** (FR-022, SC-009).
- `requested=True ∧ ok=False` → exit 1, **senza** scartare il `.env` scritto (FR-023).
- Eseguito via vehicle `sertor-rag` in subprocess (Principio XI, research Punto 3).

---

## 6. `ConfigureReport` — esito complessivo (umano + `--json`, zero segreti)

| Campo | Tipo | Note |
|-------|------|------|
| `target` | `str` | radice host risolta (`--target`) |
| `profile` | `ConfigProfile` | backend/store scelti |
| `fields` | `tuple[FieldResolution, …]` | con valori segreti **già mascherati** |
| `validation` | `ValidationOutcome` | esito statico |
| `live_check` | `LiveCheckOutcome` | esito probe (o non richiesto) |
| `env_path` | `str` | `.sertor/.env` (dove sono stati scritti i valori) |
| `notes` | `tuple[str, …]` | annotazioni (es. «valore X preservato; usa --overwrite per sostituirlo») |

**Metodi (puri):** `render_human() -> str`, `render_json() -> str`, `exit_code() -> int`.

**Mascheramento (funzione pura `mask_secret`, research Punto 2):** unico punto di decisione su come si
mostra un segreto; i campi `secret=True` entrano nel report **solo** attraverso di esso (SC-008/FR-013).
Un test asserisce: dato un segreto noto, esso non compare in `render_human` né `render_json`.

**Exit code derivato:** `0` se `validation.complete ∧ (¬live_check.requested ∨ live_check.ok)`;
altrimenti `1` (FR-032).

---

## Relazioni

```
ConfigProfile ── determina (via validate_backend) ──▶ {ConfigField richiesti}
        │
        ▼
{FieldResolution}  ──(merge_env + _replace_key_line)──▶  .sertor/.env  (additivo, non distruttivo)
        │
        ▼
ValidationOutcome  +  LiveCheckOutcome  ──▶  ConfigureReport (umano | --json, zero segreti)  ──▶ exit 0/1
```

**Confini (invarianti):** nessuna nuova porta del core; nessun import di SDK in `sertor`; segreti solo in
`.sertor/.env` (git-ignored); install≠run (nessuna ingestione/indice); idempotenza by construction
(merge additivo + overwrite controllato).
