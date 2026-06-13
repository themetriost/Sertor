# Record retroattivo — Tema lingua (asset/CLI/seed in inglese) + bug runtime auto-localizzante

<!-- STATO: CONSEGNATO (record a posteriori). Lavoro fatto come "pass mirato" fuori dal flusso
     SpecKit, su decisione utente; questo documento lo traccia dopo la consegna. -->
<!-- Consegnato: PR #27 (asset/CLI EN), PR #28 (runtime auto-localizzante + .env template EN),
     PR #29 (seed localizzato it/en, D3). Tutto su master il 2026-06-13. -->

> **Natura.** Documento **a posteriori**: registra due interventi consegnati senza passare dal ciclo
> `requirements → spec → tasks` (erano un pass mirato + un bugfix emerso dalla validazione live su
> Kaelen). Parte A = **requirement** (tema lingua); Parte B = **bug**. Soddisfa anche i gruppi E/F di
> FEAT-007 ([[manutenzione-wiki]]), che vengono così consegnati in anticipo (vedi §Tracciabilità).

---

## Contesto

1. **Tema lingua (decisione utente 2026-06-13).** Principio: *tooling/infrastruttura in inglese
   canonico; il contenuto del wiki nella lingua scelta dall'host* (`language` della config). Prima
   gli asset installati, l'output CLI e i seed erano in italiano fisso.
2. **Bug runtime (emerso live su Kaelen, 2026-06-13).** `sertor-rag index` lanciato dalla radice
   host caricava un `.env` sbagliato → backend di default `local` → errore «ollama non raggiungibile»
   pur avendo configurato Azure in `.sertor/.env`. Causa: risoluzione di `.env`/indice relativa al
   **cwd**, non al runtime.

---

## Parte A — Requirement: tema lingua (CONSEGNATO)

### Requisiti funzionali (EARS)

- **REQ-L1 (Ubiquitous):** Gli asset installati (`skills/wiki-author/**`, agente, comando, hook,
  blocco rituale, commenti dei template `wiki.config.toml.tmpl` e `.env`) **devono** essere in
  **inglese canonico** — nessuna variante per-lingua. *(soddisfa FEAT-007 REQ-035)*
- **REQ-L2 (Ubiquitous):** L'output host-facing delle CLI (`sertor install`, `sertor-rag`,
  `sertor-wiki-tools`: help, descrizioni, report, messaggi d'errore di presentazione) **deve** essere
  in inglese.
- **REQ-L3 (Event-driven):** Quando `structure init` genera i seed di `index`/`log`, il sistema
  **deve** produrli nella lingua di `profile.language` (tabella it/en), con **fallback inglese** per
  lingue non in tabella e normalizzazione dei sottotag (`it-IT` → `it`). *(soddisfa FEAT-007
  REQ-030..034, D3)*
- **REQ-L4 (Ubiquitous):** La fonte unica della lingua del contenuto **deve** essere il campo
  `language` di `wiki.config.toml`; gli asset (in inglese) istruiscono l'agente a scrivere il
  contenuto in quella lingua. *(soddisfa FEAT-007 REQ-036/037)*
- **REQ-L5 (Ubiquitous):** Una **guardia automatica** **deve** impedire la regressione: gli asset
  installati non contengono italiano residuo ad alto segnale.

### Decisioni

- **DL-1** Scope = *bundle + output host-facing* in inglese; le **error-string profonde** del dominio
  restano in italiano e si traducono **gradualmente** (Boy-Scout), fuori da questo scope.
- **DL-2** Seed: tabella di localizzazione in modulo (approccio A, YAGNI), non file-risorsa.

### Consegnato

`assets/claude/**` + `claude-md-block.md` + `wiki.config.toml.tmpl` + `assets/rag/env.*.tmpl`
tradotti; `.claude/` ri-sincronizzato; `report.py` + i tre `__main__` CLI in inglese; `structure.py`
con tabella `_SEED_STRINGS` it/en + fallback; `wiki/wiki.config.toml` `[strings]` in inglese.
Guardia `packages/sertor/tests/test_assets_english.py` (denylist italiana su `assets/claude` +
`assets/rag`). PR #27, #29.

---

## Parte B — Bug: runtime non auto-localizzante (`.env`/indice legati al cwd) — RISOLTO

- **Sintomo (Kaelen):** `…\.sertor\.venv\Scripts\sertor-rag.exe index <host>` da radice host →
  `op=embeddings_error provider=ollama:nomic-embed-text` nonostante `.sertor/.env` con `RAG_BACKEND=azure`.
- **Causa radice:** `Settings.load()` leggeva `.env` dal **cwd** e l'`index_dir` di default era `.index`
  relativo al cwd. Lanciando da radice host (cwd ≠ `.sertor`), `.sertor/.env` non veniva caricato →
  fallback silenzioso a `local`/Ollama; e l'indice sarebbe finito in radice host.
- **Fix (REQ-B1..B3):**
  - **REQ-B1 (Event-driven):** quando `Settings.load()` risolve la config, **deve** cercare `.env` nel
    cwd e, se assente, **accanto al venv del runtime** (`Path(sys.prefix).parent`, cioè `.sertor/` per
    un install, radice repo in dev).
  - **REQ-B2 (Ubiquitous):** l'`index_dir` di default **deve** essere ancorato alla cartella del
    `.env` risolto (quando assoluto), così l'indice vive in `.sertor/.index` da **qualsiasi** cwd.
  - **REQ-B3 (Unwanted):** se non esiste alcun `.env` né `RAG_BACKEND` nell'ambiente, il sistema
    **deve** emettere un WARNING (`config_no_env_found`) invece del fallback silenzioso a `local`.
  - **Invariante preservata:** `Settings.load(env_file=None)` (isolamento test) resta identico; il
    caso «`.env` nel cwd» resta retro-compatibile (`index_dir` relativo `.index`).
- **Consegnato:** `src/sertor_core/config/settings.py` (`_resolve_env_path` + ancora indice + warning);
  template `.env` tradotti; test `tests/unit/test_settings_runtime.py` (4 casi). PR #28.

---

## Qualità

85 test pacchetto `sertor` + 334 root verdi, ruff pulito. Validato live su Kaelen (install rag/wiki:
radice pulita, config in `wiki/`, report in inglese). Constitution: nessuna deroga.

## Tracciabilità verso FEAT-007 ([[manutenzione-wiki]])

| Gruppo FEAT-007 | REQ | Stato dopo questo record |
|---|---|---|
| E — Seed localizzati | REQ-030..034 | ✅ **consegnato** (REQ-L3 / PR #29) |
| F — Asset installer in inglese | REQ-035..037 | ✅ **consegnato** (REQ-L1/L4 / PR #27/#28) |
| B — `move`-con-link | REQ-010..015 | ⏳ residuo FEAT-007 |
| C — `reconcile` + `collect`+status | REQ-020..027 | ⏳ residuo FEAT-007 |
| D — trigger periodico | REQ-028 | ⏳ Could |

Il bug runtime (Parte B) **non** apparteneva a FEAT-007: è un difetto del runtime RAG installato.
