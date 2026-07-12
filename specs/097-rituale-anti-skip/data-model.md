# Data model — Rituale wiki anti-skip (097)

Entità **di sola lettura** prodotte da `ritual-check` (nessuna persistenza; emesse su stdout come JSON +
summary). Dataclass in `sertor_core/wiki_tools/contracts.py`, versione contratto `wiki.ritual_check/1`.

## `RitualCheckResult` (`wiki.ritual_check/1`)

| Campo | Tipo | Significato |
|---|---|---|
| `scope` | `str` | come è stato determinato l'insieme dello step: `git:<base>...HEAD` o `explicit:<n>` |
| `pages_in_scope` | `list[str]` | path POSIX relativi (wiki root) delle pagine changed dello step |
| `distill_candidates` | `list[DistillCandidate]` | gruppi di pagine che fanno emergere un'entità non distillata |
| `drift_candidates` | `list[DriftCandidate]` | pagine con segnale strutturale di possibile drift (da lint) |
| `declaration_scaffold` | `str` | riga `Rituale: record: <?> · distill: <N…> · lint: <M…>` pre-popolata |

## `DistillCandidate`

| Campo | Tipo | Significato |
|---|---|---|
| `pages` | `list[str]` | le ≥2 pagine changed del gruppo |
| `shared_new_backlinks` | `int` | quanti backlink incrociati **nuovi** (HEAD∖base) tra le pagine del gruppo |
| `reason` | `str` | es. «≥2 pagine collegate da nuovi backlink, nessuna nuova pagina concepts/tech» |

## `DriftCandidate`

| Campo | Tipo | Significato |
|---|---|---|
| `page` | `str` | la pagina candidata al lint semantico |
| `signal` | `str` | quale segnale: `stale-updated` · `neighbor-of-change` · `capability-exec` (config) |
| `detail` | `str` | breve dettaglio deterministico (es. «updated 2026-06-30 < modifica git 2026-07-12») |

## Regole di validazione / invarianti

- **Sola lettura:** nessun campo comporta scrittura su pagine (Principio VI); il tool emette, l'agente
  giudica (Principio XI/D↔N).
- **Fail-loud (REQ-006):** se lo scope non è determinabile (no git, base non risolta, no `--pages`) →
  `ConfigError` esplicito, **non** un `RitualCheckResult` con liste vuote.
- **Determinismo:** stesso `(HEAD, base, stato-wiki)` → stesso `RitualCheckResult` (Principio VI).
- **Nessun giudizio semantico:** `drift_candidates` sono *candidati* (segnali strutturali), non verdetti; il
  lint semantico resta all'agente.
- **Host-agnostico:** `capability-exec` compare **solo** se `wiki.config.toml` ha `[ritual].capability_globs`
  + `exec_page`; assente → il segnale non esiste (nessun path hardcodato).
