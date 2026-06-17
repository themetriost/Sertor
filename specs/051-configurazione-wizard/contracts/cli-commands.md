# Contract — CLI `sertor configure` (feature 051)

**Data**: 2026-06-17 · **Branch**: `051-configurazione-wizard`

Nuovo sottocomando dell'installer `sertor` (pacchetto `packages/sertor`). Additivo: i comandi esistenti
(`install`/`upgrade`/`uninstall`) restano invariati (NFR non-regressione). Stile e exit code allineati
a `sertor`/`sertor-rag` (`__main__.py:383-402`, `cli/__main__.py:374-389`).

---

## 1. Sintassi

```
sertor configure [rag]
                 [--target DIR]                 # default: cwd
                 [--backend {azure,local}]      # imposta RAG_BACKEND
                 [--store {local,azure}]        # imposta SERTOR_STORE_BACKEND (default: = backend)
                 [--set KEY=VALUE ...]           # valore esplicito per un campo (ripetibile)
                 [--overwrite]                   # consenti la sovrascrittura di valori già presenti
                 [--non-interactive]             # forza il ramo flag-driven anche con TTY
                 [--check]                       # probe live opt-in (una chiamata reale al provider)
                 [--json]                        # report machine-readable
```

- `rag` posizionale **opzionale**, default `rag` (unica capacità con provider da configurare oggi).
- `--set KEY=VALUE` ripetibile; `KEY` deve essere un campo noto del profilo (vedi data-model
  `ConfigField`), altrimenti **exit 2**. Valore senza `=` → **exit 2**.
- I segreti in CI sono forniti preferibilmente via **ambiente** (es. `AZURE_OPENAI_API_KEY` esportato):
  `Settings.load()` li legge e contano come «forniti» → nessun prompt, nessun obbligo di `--set`.

---

## 2. Modalità (Punto 1 research)

| Condizione | Comportamento |
|-----------|---------------|
| TTY presente (`stdin` **e** `stdout` `isatty()`), `--non-interactive` assente, campi mancanti | **interattivo**: prompt per campo (nome + descrizione + valore corrente mascherato); segreti via `getpass` |
| Nessun TTY **oppure** `--non-interactive` | **flag-driven**: nessun prompt mai; valori da `--set`/scorciatoie/ambiente/esistenti |
| Campo richiesto irrisolto **senza** TTY | **errore esplicito** che nomina i campi mancanti, **exit 1**, **nessuna** scrittura parziale (FR-005) |

Nessun prompt nascosto: l'unica condizione di prompt è `isatty ∧ mancante ∧ ¬--non-interactive` (NFR-05).

---

## 3. Scrittura (`.sertor/.env`) — additiva, non distruttiva, idempotente

| Stato di partenza | Effetto |
|-------------------|---------|
| `.sertor/.env` assente | creato dal template `env.{backend}.tmpl` (corpus = nome cartella sanitizzato), poi valori applicati; **nessun** `uv`/indice (FR-015/030) |
| chiave mancante | aggiunta (`merge_env`) |
| chiave già valorizzata, `--overwrite` | sovrascritta (`_replace_key_line`) → `status=OVERWRITTEN` |
| chiave già valorizzata, interattivo | conferma puntuale; sì → sovrascrive, no → `KEPT` |
| chiave già valorizzata, non interattivo, senza `--overwrite` | **preservata** (`KEPT`) + nota nel report (non un errore) |

Re-run con gli stessi input → `.env` **identico** (FR-014/SC-005). Segreti **solo** in `.sertor/.env`
(git-ignored); **nessun** file versionato toccato (FR-012/SC-003).

---

## 4. Validazione (FR-020/021, SC-002)

Sempre eseguita al termine: `Settings.load().validate_backend()` (statica, offline).
- `missing == []` → `complete`, contribuisce a **exit 0**.
- `missing != []` → elencati nel report; `.env` lasciato come scritto ma **marcato incompleto**;
  contribuisce a **exit 1**.

---

## 5. Probe live `--check` (FR-022/023, US5 — Should)

| Caso | Effetto | Exit |
|------|---------|------|
| `--check` assente | **nessuna** chiamata di rete (SC-009) | da validazione |
| `--check`, config completa, provider raggiungibile | una chiamata di embedding reale via vehicle `sertor-rag` (subprocess, Principio XI) → ok | `0` (se anche statica ok) |
| `--check`, probe fallito | messaggio azionabile, `.env` **non** scartato | `1` |
| `--check`, sottocomando-probe non disponibile nel runtime installato | degrado onesto: «probe live non disponibile» nel report, exit **invariato** dalla validazione statica | 0/1 da statica |

> Dipendenza di core: il vehicle `sertor-rag` deve esporre un comando di probe minimale (es.
> `sertor-rag check`). È **lavoro di `sertor-core`** da promuovere a backlog **prima** che `--check`
> conti come done (research Punto 3). Senza di esso, `--check` degrada onestamente (riga 4 sopra).

---

## 6. Report (FR-031, SC-008)

Umano (default) e `--json` (`--json`). Contiene: backend/store scelti, per ogni campo
`name`/`status`/(segreti **mascherati**), esito validazione (`complete`+`missing`), esito probe (se
richiesto), `env_path`, note. **Nessun valore segreto in chiaro** in nessuna delle due forme né nei log.

Esempio `--json` (forma):

```json
{
  "target": "/abs/host",
  "profile": {"backend": "azure", "store": "local"},
  "fields": [
    {"name": "AZURE_OPENAI_ENDPOINT", "status": "set", "source": "flag"},
    {"name": "AZURE_OPENAI_API_KEY", "status": "set", "source": "env", "value": "****3f2a"},
    {"name": "AZURE_OPENAI_EMBED_DEPLOYMENT", "status": "kept", "source": "existing"}
  ],
  "validation": {"complete": true, "missing": []},
  "live_check": {"requested": false, "ok": null, "detail": ""},
  "env_path": ".sertor/.env",
  "notes": [],
  "exit_code": 0
}
```

---

## 7. Exit code (FR-032)

| Code | Condizione |
|------|------------|
| `0` | `validation.complete ∧ (¬--check ∨ probe ok)` |
| `1` | campi mancanti **o** probe `--check` fallito **o** errore di dominio (`SertorError`/`InstallerError`) |
| `2` | uso errato (argparse): valore non valido per `--backend`/`--store`, `--set` malformato, combinazione vietata |

---

## 8. Osservabilità (Principio IX)

Un evento strutturato a completamento (`configure`): backend/store, conteggi `set`/`kept`/`missing`,
`live_check` ok/skip, errori. **Mai** valori segreti (solo nomi-campo/conteggi), come `memory_list`
(`cli/__main__.py:370`).

---

## 9. Invarianti (non-negoziabili)

- **install ≠ run**: nessuna ingestione/creazione indice (FR-030/SC-009).
- **Principio XI**: validazione statica = lettura `Settings` (ok); probe live = via vehicle
  `sertor-rag` subprocess, **mai** `build_embedder()` importato.
- **host-agnostico** (Principio X): nessuna assunzione sull'ospite oltre `--target`.
- **non-distruttività/idempotenza** (Principio VI): merge additivo, overwrite solo su conferma/flag.
- **segreti** (Sicurezza): solo in `.sertor/.env`, mai versionati, mai a video/log/report.
