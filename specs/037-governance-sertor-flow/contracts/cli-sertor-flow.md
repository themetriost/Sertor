# Contract — CLI `sertor-flow` (`sertor-flow/1`)

Superficie a riga di comando del pacchetto `sertor-flow`. Thin consumer del toolkit
`sertor_install_kit` (Principio I). Install ≠ run.

## Console-script

`[project.scripts] sertor-flow = "sertor_flow.__main__:main"`

## Comando: `sertor-flow install`

Deposita l'**intero** bundle di governance (all-or-nothing, MVP — DA-d) su un repository ospite.

**Sintassi:** `sertor-flow install [--target PATH] [--json]`

| Opzione | Default | Significato |
|---|---|---|
| `--target PATH` | CWD | Radice del repository ospite (FR-004) |
| `--json` | off | Emette il resoconto in JSON (FR-020) |

**Comportamento (garanzie):**
- Deposita: skill/agenti SpecKit (vendored) + skill `requirements` + agente `requirements-analyst` +
  agente `configuration-manager` → `.claude/`; macchinario `.specify/` (templates, scripts ps+bash,
  extensions/git, workflows); starter costituzione → `.specify/memory/constitution.md`; file
  init/integration generati per-host; `NOTICE`/licenza MIT; blocco rituale SDLC a marker → `CLAUDE.md`.
- **install ≠ run (FR-003, SC-002):** NON avvia alcuna fase SDLC, operazione git o indicizzazione.
- **non distruttivo (FR-014/016):** file esistenti → SKIPPED; merge additivi; blocco a marker.
- **idempotente (FR-017):** seconda esecuzione → zero modifiche.
- **fail-fast (FR-019):** primo errore → stop, passo fallito nominato, artefatti già scritti restano.

**Output (umano):** una riga per artefatto `<outcome> <target_rel> [— detail]`, poi un riepilogo
`created/skipped/merged/block` + eventuale `failed_step`.

**Output (`--json`):** oggetto con `target`, `capability:"governance"`, `artifacts:[{target_rel,
outcome, detail}]`, `failed_step?`.

**Exit code:** `0` successo (anche con SKIPPED); `≠0` se un passo è fallito (errore di dominio).

**Fuori MVP (riconosciuti, non implementati):** `--only <subset>` (selettività interna, FR-024 Could),
`sertor-flow upgrade`/`uninstall` (FEAT-008 `sertor-cli`).

## Indipendenza dal core (FR-002 / SC-004)

`sertor_flow` e `sertor_install_kit` NON importano `sertor_core`. `sertor-flow install` completa in un
ambiente dove `sertor-core` non è installato.

## Puntatore dall'ombrello (`sertor install governance`) — FR-023 / SC-008

`sertor install governance` (pacchetto `sertor`) NON installa la governance: emette un messaggio che
rimanda a `sertor-flow` e a come installarlo, con exit code dedicato. `sertor` **non** dipende da
`sertor-flow`.
