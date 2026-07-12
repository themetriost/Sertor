# Contract — `sertor-wiki-tools ritual-check`

Nuovo sottocomando del vehicle `sertor-wiki-tools`. **Sola lettura**, deterministico, zero-LLM, offline.

## CLI

```
sertor-wiki-tools ritual-check [--base <ref>] [--pages <a.md,b.md,...>] [--json] [--config <toml>] [--root <path>]
```

- `--base <ref>` — base del diff git (default: merge-base con `master`). Le pagine dello step = quelle
  changed in `<base>...HEAD` sotto i `source_dirs` del profilo.
- `--pages <lista>` — override esplicito dell'insieme (host non-git o scope manuale). Bypassa git.
- `--json` — emette il contratto `wiki.ritual_check/1`; altrimenti summary umano terso.
- `--config`/`--root` — come gli altri sottocomandi (auto-discovery `wiki.config.toml`).

**Exit code:** `0` successo · `1` errore di dominio (scope indeterminabile senza `--pages`, messaggio
azionabile su stderr — REQ-006) · `2` uso errato.

## Output JSON (`wiki.ritual_check/1`)

```json
{
  "contract": "wiki.ritual_check/1",
  "scope": "git:<base>...HEAD",
  "pages_in_scope": ["experiments/feat-x.md", "concepts/y.md"],
  "distill_candidates": [
    {"pages": ["a.md", "b.md"], "shared_new_backlinks": 2,
     "reason": "≥2 pagine collegate da nuovi backlink, 0 nuove pagine concepts/tech"}
  ],
  "drift_candidates": [
    {"page": "syntheses/roadmap.md", "signal": "capability-exec",
     "detail": "diff tocca src/** ma non l'exec_page"},
    {"page": "tech/z.md", "signal": "stale-updated",
     "detail": "updated 2026-06-30 < modifica git 2026-07-12"}
  ],
  "declaration_scaffold": "Rituale: record: <?> · distill: <1 candidato → verdetto?> · lint: <2 pagine drift → verdetto?>"
}
```

## Summary umano (senza `--json`)

```
ritual-check  scope=git:master...HEAD  pages=2
  distill: 1 candidato → [a.md + b.md] (2 nuovi backlink, 0 nuove pagine concepts/tech)
  drift:   2 pagine → syntheses/roadmap.md (capability-exec) · tech/z.md (stale-updated)
  →  Rituale: record: <?> · distill: <1 candidato → verdetto?> · lint: <2 pagine → verdetto?>
```

## Invarianti del contratto

- **Additivo:** nuovo contratto, non modifica quelli esistenti (`scan/1`, `lint/1`, …).
- **Deterministico & sola lettura:** nessuna scrittura; stesso input → stesso output.
- **Fail-loud:** scope indeterminabile → exit 1 + messaggio, **mai** liste vuote silenziose.
- **D↔N:** solo candidati/segnali strutturali; nessun verdetto semantico (giudizio → agente).
