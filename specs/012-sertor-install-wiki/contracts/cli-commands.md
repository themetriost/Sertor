# Contratto CLI — comando `sertor` (FEAT-012)

**Branch**: `012-sertor-install-wiki` | **Spec**: [`../spec.md`](../spec.md) | **Data**: 2026-06-11

Interfaccia esterna esposta dall'installer: console-script `sertor` (equivalente
`python -m sertor_installer`). Layer **sottile** (Principio I/NFR-I-06): parsing argparse →
chiamata alle funzioni dell'installer → formattazione report. Pattern di riferimento:
`src/sertor_core/cli/__main__.py`, `src/sertor_core/wiki_tools/__main__.py`.

---

## Sinossi

```
sertor [-h]
sertor install [-h]
sertor install wiki [-h] [--target <path>] [--language <lang>] [--source-dirs <d1,d2,…>] [--json]
sertor install rag           # stub: "non ancora disponibile" → exit non-zero
sertor install governance    # stub: "non ancora disponibile" → exit non-zero
```

## Comandi e argomenti

### `sertor` (backbone) — FR-001/002

- Senza sottocomando → help + exit non-zero (argparse: subparser `required`, come
  `cli/__main__.py:32`). `-h/--help` → help + exit 0.
- Dichiara i sottocomandi: `install` (disponibile). Sotto `install`: `wiki` (disponibile),
  `rag` / `governance` (dichiarati, **stub**).

### `sertor install wiki` — FR-006/020/021/025

| Argomento | Tipo | Default | Requisito |
|-----------|------|---------|-----------|
| `--target <path>` | path | cwd | FR-006 — radice del repo ospite |
| `--language <lang>` | str | `en` | FR-020 — lingua nel `wiki.config.toml` generato |
| `--source-dirs <d1,d2,…>` | lista (CSV) | euristica (D7) | FR-021 — override delle cartelle sorgente |
| `--json` | flag | off | D8 (Could) — report come JSON |

**Comportamento:** installa l'`InstallPlan` (data-model §3) sotto `--target`, stampa l'`InstallReport`
su stdout, exit code derivato (sotto). `install ≠ run`: nessun LLM/rete/indicizzazione (FR-007/022).

### Stub `install rag` / `install governance` — FR-005/REQ-104

Messaggio leggibile «`install <cap>` non è ancora disponibile (taglio futuro)» su stderr; **exit
non-zero** (1); nessuna operazione su filesystem.

## Exit code (D8)

| Codice | Significato |
|--------|-------------|
| `0` | successo; nessun artefatto in errore (anche se tutto `skipped` — idempotenza, REQ-143) |
| `1` | errore di dominio (`SertorError`/`ConfigError`/`IngestionError`): target non valido/non scrivibile, `settings.json` malformato, permessi; fail-fast con report parziale (REQ-125); stub non implementato |
| `2` | errore d'uso (argparse): sottocomando ignoto, argomento mancante/invalido (REQ-102) |

## Edge case → contratto (dalla spec)

| Situazione | Risposta |
|------------|----------|
| `--target` inesistente/non scrivibile | exit 1, messaggio con il path, **nessun** artefatto scritto |
| `settings.json` malformato | exit 1, messaggio col file e la causa; file **non** toccato; artefatti già scritti restano |
| `CLAUDE.md` con blocco marker già presente | blocco **non** duplicato; fuori-marker intoccato; outcome `SKIPPED` |
| nessuna cartella standard | `source_dirs = ["."]` nel config generato |
| `wiki/` già presente | `init_structure` idempotente; esistenti → `skipped` |
| fallimento permessi a metà run | report stato parziale + `failed_step`; exit 1; re-run completa |
| import/installazione del pacchetto | nessun effetto collaterale (install ≠ run, FR-022) |

## Help (SC-007)

`sertor --help` e `sertor install --help` elencano i sottocomandi e descrivono gli argomenti; `rag` e
`governance` compaiono come **pianificati**. Verificabile da test (stringhe attese nell'help).

## Convenzioni I/O (allineate al core)

- UTF-8 forzato su `stdin/stdout/stderr` (`cli/__main__.py:132-137`).
- Errori di dominio → `errore: <msg>` su **stderr**, return 1. Argparse → exit 2.
- Report → **stdout** (umano o JSON con `--json`).
