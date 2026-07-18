# Implementation Plan: `ritual-check` rileva il default branch

**Branch**: `108-feat-033-ritual-check-default-branch` · **Spec**: `./spec.md` · **Requisiti**: `../../requirements/debito-tecnico/feat-033-ritual-check-default-branch/requirements.md`

**Date**: 2026-07-18

## Summary

`_resolve_base` (`src/sertor_core/wiki_tools/ritual_check.py:48`) fa `merge-base HEAD master` con `master`
**hardcoded** → su un repo `main`-default fallisce (Principio X violato). **Fix:** rilevare il branch di
default a runtime (remote `origin/HEAD` → candidati ordinati esistenti) e fare merge-base col primo che ne
ha uno; `--base` invariato, fail-loud finale invariato.

## Technical Context

- **Linguaggio:** Python ≥ 3.11, stdlib + `git` via `subprocess` (già usati; nessuna nuova dipendenza).
- **File toccati:**
  - `src/sertor_core/wiki_tools/ritual_check.py` — `_resolve_base` riscritta + nuovo helper
    `_default_base_candidates` (rilevamento). Nessun'altra funzione toccata.
  - `tests/unit/test_ritual_check.py` — nuovi test (repo `main`-default, `master`-default, `--base`,
    fail-loud); adeguamento se qualche test assume `master`.
- **Design del rilevamento (precedenza):**
  1. `--base` esplicito → ritorna subito (invariato).
  2. Candidati in ordine: `origin/HEAD` (via `git symbolic-ref --short refs/remotes/origin/HEAD`,
     autorevole) → poi i ref **esistenti** `origin/main`, `origin/master`, `main`, `master` (dedup) →
     merge-base col **primo** che ne ha uno.
  3. Nessun merge-base da alcun candidato → `ConfigError` fail-loud (messaggio azionabile, key `--base`).
- **Perché copre il dogfood:** `origin/HEAD` del repo Sertor punta a `master` → il path primario dà
  `master`, CS-2 preservata senza dipendere dal fallback.
- **Invarianti:** contratto `--base`/`--pages`, output JSON `wiki.ritual_check/1`, sola-lettura, zero-LLM.

## Constitution Check (gate)

| # | Principio | Esito | Nota |
|---|---|---|---|
| — | **Missione / North Star** | ✅ PASS | Rende usabile su *ogni* ospite la governance del rituale (forced declaration) che presidia la freschezza del wiki reso all'agente — serve la qualità del contesto, non deriva. |
| I | Core a dipendenze verso l'interno | ✅ PASS | Modifica confinata a `wiki_tools` (core); il CLI resta thin. |
| II | Provider/backend dietro boundary | ✅ N/A | Nessun provider/store. |
| III | Semplicità (YAGNI), unità piccole | ✅ PASS | Un helper piccolo + una lista ordinata; override in config **rinviato** (non serve ora). |
| IV | Errori espliciti, niente null silenzioso | ✅ PASS | Base irrisolvibile → fail-loud (mai scope vuoto silenzioso). |
| V | Testabilità / qualità provata | ✅ PASS | Repo `main`/`master` costruibili in tmp; guard test host-agnostico (SC-005). |
| VI | Idempotenza, determinismo, non-distruttività | ✅ PASS | Sola lettura; risoluzione deterministica (ordine candidati fisso). |
| VII | Leggibilità, lascia il codice più pulito | ✅ PASS | Rimuove l'assunto hardcodato; nomina il default nel messaggio d'errore. |
| VIII | Config centralizzata | ✅ PASS | Nessun default hardcodato nel componente; il default viene dal repo (git), non da una costante. |
| IX | Osservabilità | ✅ PASS | `ritual-check` emette già l'evento `ritual_check` (`log_event`); questa modifica non lo tocca (labels invariate). |
| X | Host-agnostico | ✅ PASS | **È il cuore della feature:** nessun nome di branch assunto; funziona su `main` e `master`; guard test. |
| XI | Consumo via vehicle | ✅ PASS | Il fix è nel core dietro il vehicle `sertor-wiki-tools`. |
| XII | Fail Loud, Fix the Cause | ✅ PASS | Elimina la causa (assunto `master`) invece di aggirarla; fail-loud finale preservato. |

**Esito gate: 12/12 + missione PASS.** Nessuna deviazione da giustificare.

## Design (pseudo)

```python
def _resolve_base(config_dir, base):
    if base:
        return base
    tried = _default_base_candidates(config_dir)   # ordered, existing refs (+ origin/HEAD first)
    for ref in tried:
        rc, out = _git(["merge-base", "HEAD", ref], config_dir)
        if rc == 0 and out.strip():
            return out.strip()
    raise ConfigError(
        "cannot determine a git diff base (no merge-base with the repo's default branch"
        + (f"; tried: {', '.join(tried)}" if tried else "")
        + "); pass --base <ref> or --pages <a.md,...>",
        key="--base",
    )

def _default_base_candidates(config_dir) -> list[str]:
    out_list = []
    rc, out = _git(["symbolic-ref", "--short", "refs/remotes/origin/HEAD"], config_dir)  # e.g. origin/main
    if rc == 0 and out.strip():
        out_list.append(out.strip())
    for cand in ("origin/main", "origin/master", "main", "master"):
        if cand not in out_list:
            rc, _ = _git(["rev-parse", "--verify", "--quiet", cand], config_dir)
            if rc == 0:
                out_list.append(cand)
    return out_list
```

## Test
- `test_ritual_check.py`: repo tmp con default **`main`** → `ritual-check` senza `--base` risolve (SC-001/005);
  repo con **`master`** → invariato (SC-002); `--base` esplicito onorato (SC-003); nessun candidato/merge-base
  → fail-loud (SC-004). Verificare/adeguare i test esistenti che eventualmente assumono `master`.

## Out of scope (rinviato)
- Override del default branch in `wiki.config.toml` (Could).
- Ogni altra logica di `ritual-check` (euristiche distill/drift, scope, output) — invariata.

## Phase completion
- [x] requirements · [x] specify · [x] clarify (ordine risoluzione sciolto) · [x] plan (+ Constitution Check 12/12)
- [ ] tasks · [ ] implement
