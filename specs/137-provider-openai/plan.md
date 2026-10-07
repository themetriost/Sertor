# Implementation Plan: Embedding con l'API OpenAI diretta

**Branch**: `137-provider-openai` | **Date**: 2026-10-07 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/137-provider-openai/spec.md` · **Deriva da**: FEAT-012
(epica `sertor-core`) · **Requisiti**: [`requirements/sertor-core/provider-openai/requirements.md`](../../requirements/sertor-core/provider-openai/requirements.md)

## Summary

Nuovo valore `openai` di `SERTOR_EMBED_PROVIDER`: embedding via `POST {OPENAI_BASE_URL}/embeddings` con
`Authorization: Bearer`, modello di default `text-embedding-3-large`. La logica HTTP del protocollo
(lotti, errori, retry per lotto, dimensione, token) si **estrae** dall'adapter Azure in una base
condivisa, così Azure e OpenAI differiscono solo per URL, credenziale, query e nome (research D-1). Le
chiavi obbligatorie del provider diventano **derivate** da `Settings` anche nella CLI di `doctor`, che
oggi ne tiene una copia a mano (D-3). Il wizard dell'installer è congelato: attivazione manuale
documentata e richiesta di cablaggio a Kaelen (D-7).

## Technical Context

**Language/Version**: Python ≥3.11 (come il resto di `sertor-core`)

**Primary Dependencies**: `httpx` (già usato dall'adapter Azure). **Nessuna dipendenza nuova**: niente
SDK `openai`.

**Storage**: invariato (Chroma locale / Azure AI Search); una collezione per `(corpus, openai:<model>)`.

**Testing**: `pytest`, client `httpx.MockTransport` iniettato (senza rete); un test `cloud` opzionale
contro il servizio reale, saltato senza `OPENAI_API_KEY`.

**Target Platform**: ospiti Windows/Linux/macOS, Claude e Copilot (capacità di libreria + CLI/MCP).

**Project Type**: libreria (`sertor-core`) + vehicles CLI/MCP.

**Performance Goals**: pari ad `azure` — una richiesta per lotto da `EMBED_BATCH_SIZE` (default 64).

**Constraints**: chiave mai esposta; installer congelato; nessuna regressione su `azure`.

**Scale/Scope**: ~6 file di `src/`, ~4 file di test, 2 di documentazione utente.

## Constitution Check

*GATE: verificato prima della Phase 0 e ri-verificato dopo il design (esito invariato).*

- [x] **I — Dipendenze verso l'interno:** PASS. Adapter in `adapters/embeddings/`, dietro la porta
  `EmbeddingProvider`; import lazy dentro `build_embedder`; il dominio non cambia.
- [x] **II — Boundary & local-first:** PASS. Provider cloud **opt-in** da config; il default resta
  `glove`. Nessuna dipendenza esterna fuori dalla porta.
- [x] **III — YAGNI & unità piccole:** PASS. Base condivisa giustificata da evidenza presente (due
  adapter sullo stesso protocollo, D-1); niente SDK; niente `dimensions`/intestazioni org (rinviate).
- [x] **IV — Errori espliciti:** PASS. `EmbeddingError` con `provider`/`reason`/`retriable`; config
  incompleta → errore alla costruzione; mai vettori vuoti al posto di un errore.
- [x] **V — Testabilità & misure:** PASS. Test senza rete con trasporto finto; test Azure esistenti
  invariati come prova di non-regressione; test `cloud` opzionale.
- [x] **VI — Idempotenza & non-distruttività:** PASS. Collezione nuova per provider/modello: gli indici
  esistenti non vengono toccati.
- [x] **VII — Leggibilità:** PASS. Nomi di dominio (`OpenAIEmbedder`, `missing_provider_keys`).
- [x] **VIII — Configurazione centralizzata:** PASS. Default solo nei campi di `Settings`; `load()` li
  legge dal campo invece di ripetere il letterale (D-2).
- [x] **IX — Osservabilità:** PASS. Stessi eventi `embeddings`/`embeddings_error` di `azure`, con
  token; nessun segreto nei campi.
- [x] **X — Host-agnostico:** PASS con **debito dichiarato**. La capacità è di libreria e viaggia col
  pacchetto; il cablaggio nel wizard d'installazione è perimetro Kaelen (congelamento): tracciato nella
  riga FEAT-012 e affisso in bacheca alla consegna. Regola 1 del CLAUDE.md: la feature non conta come
  *completa sul wizard* finché Kaelen non la cabla; è *installabile* (variabili nel `.env` dell'ospite).
- [x] **XI — Consumo via vehicles:** PASS. Attivazione e verifica via `sertor-rag` / MCP.
- [x] **XII — Fail Loud:** PASS. Nessun guasto silenziato; anzi la ricerca porta a galla due silenzi del
  wizard congelato (`--set` ignorato, guardia di copertura cieca), segnalati a Kaelen invece di
  aggirarli.
- [x] **XIII — Product vs Fixture Plane:** PASS. Il motivo è il dogfood (chiave Azure in 401), ma la
  decisione si giustifica col caso reale-utente (chiave OpenAI senza Azure); nessun workaround-fixture.
- [x] **XIV — Derived State:** PASS. (a) default letti dal campo, non ripetuti (D-2); (b) chiavi del
  provider derivate da `Settings` invece dell'elenco a mano `_PROVIDER_ENV_KEYS` (D-3); (c) elenco dei
  provider ammessi esposto come costante unica `EMBED_PROVIDERS`, usata dalla composizione (e
  derivabile dalla guardia di Kaelen). La copia nel test di copertura dell'installer resta (congelato):
  **riconciliatore** = segnalazione a Kaelen.
- [x] **Missione:** PASS. Ripristina un embedding cloud di qualità con la credenziale più diffusa: è la
  qualità del retrieval resa all'agente, il fronte di valore.

## Project Structure

### Documentation (this feature)

```text
specs/137-provider-openai/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/openai-embedding-provider.md
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
src/sertor_core/
├── adapters/embeddings/
│   ├── _openai_protocol.py   # NUOVO — base condivisa: lotti, POST, errori, retry, dim, token
│   ├── openai.py             # NUOVO — OpenAIEmbedder (Bearer, base_url, model)
│   ├── azure.py              # RIDOTTO — sottoclasse della base (api-key, api-version, deployment)
│   └── __init__.py           # docstring: elenco provider
├── config/settings.py        # EMBED_PROVIDERS; campi openai_*; missing_provider_keys(); load()
├── composition.py            # ramo `openai` in build_embedder; usa EMBED_PROVIDERS
└── cli/__main__.py           # doctor: missing_provider_keys() al posto di _PROVIDER_ENV_KEYS

tests/unit/
├── test_openai_embedder.py         # NUOVO — contratto del provider (trasporto finto)
├── test_settings_validate_backend.py  # + casi openai, missing_provider_keys
├── test_embedder_local_composition.py # + ramo openai, valore sconosciuto elenca openai
└── test_cli_doctor.py              # + area provider con OPENAI_API_KEY mancante
tests/integration/ (o marker cloud)
└── test_openai_live.py             # NUOVO, marker `cloud`, salta senza chiave

.env.example                         # sezione openai
docs/install.md                      # provider openai: attivazione manuale, default, costo, re-index
```

**Structure Decision**: progetto singolo esistente (`src/sertor_core`, `tests/unit`); nessun file
dell'installer (`packages/sertor*`) viene modificato.

## Fasi d'implementazione (ordine)

1. **Base di protocollo** — estrarre da `azure.py` in `_openai_protocol.py`; `AzureEmbedder` diventa
   sottoclasse. Gate: test Azure esistenti verdi **senza modifiche**.
2. **Settings** — `EMBED_PROVIDERS`, tre campi, `missing_provider_keys()`, `validate_backend()`
   ricomposto, `load()`.
3. **Adapter OpenAI** + test di contratto.
4. **Composizione** — ramo `openai`, uso di `EMBED_PROVIDERS`, docstring.
5. **Doctor** — derivazione delle chiavi del provider; rimozione di `_PROVIDER_ENV_KEYS`.
6. **Documentazione utente** — `.env.example`, `docs/install.md`.
7. **Verifica** — suite completa `-m "not cloud"` + `ruff`; quickstart sul dogfood con chiave reale
   (se disponibile).

## Complexity Tracking

Nessuna violazione da giustificare.
