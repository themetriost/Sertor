# Data Model — Pulizia stile delle skill distribuite (E10-FEAT-022)

Questa feature **non introduce entità di dominio né codice di runtime**: tocca asset `.md` e guardie
di test. Le «entità» sono artefatti documentali e i loro invarianti. Tabelle di riferimento per
implementazione e verifica.

## 1. Asset in scope (file `.md` da modificare)

| # | Asset (canonico) | Pacchetto | Righe | Interventi | Sync dogfood |
|---|---|---|---|---|---|
| A1 | `assets/rag/skills/guided-setup/SKILL.md` | `sertor` | 189 | ALL-CAPS; rimuovi «What NOT to do» (tutta duplicata) | nessuna copia dogfood |
| A2 | `assets/rag/skills/eval-suite-author/SKILL.md` | `sertor` | 145 | ALL-CAPS; callout→pointer; condensa «What NOT to do» (tieni 2) | dogfood = fork IT (F-6, fuori ambito) |
| A3 | `assets/rag/skills/eval-feedback/SKILL.md` | `sertor` | 76 | ALL-CAPS; callout→pointer; fold «What NOT to do» (1 item) | dogfood = fork IT (F-6, fuori ambito) |
| A4 | `assets/claude/skills/wiki-author/wiki-playbook.md` | `sertor` | 281 | ToC; rimuovi wikilink orfano; ALL-CAPS (`SAME`,`JUDGMENT`) | `python -m sertor_installer.sync` |
| A5 | `assets/.../skills/requirements/SKILL.md` | `sertor-flow` | 163 | ALL-CAPS solo `SEMPRE`→`sempre` (lingua invariata) | `python -m sertor_flow.sync` |

Non in scope: `wiki-author/SKILL.md` (41, già pulito), `sertor-cli-reference.md` (FEAT-021),
agenti distribuiti, blocchi `CLAUDE.md`.

## 2. Allowlist acronimi/keyword (ALL-CAPS legittimi, ≥4 lettere)

Comune (tutti i file): `RAG CLI MCP API JSON JSONL YAML TOML URL NL POSIX HTTP SDLC MRR STOP PASS FAIL PATH`
Aggiuntivi `requirements/SKILL.md`: `EARS FEAT REQ`

> Il grep guardia opera su testo **privato di code span e fenced block** e poi sottrae l'allowlist.
> `CLI/MCP/API/URL/NL/REQ` (≤3) non sono catturati da `[A-Z]{4,}` ma stanno in allowlist per chiarezza.

## 3. ToC del `wiki-playbook.md` — anchor esatti (DA-D-2)

Heading `## Contents` subito dopo il blockquote introduttivo (prima di `## 0.`), poi:

| Voce ToC (link text) | Anchor (GitHub slug della heading reale) |
|---|---|
| `§0 — Host-agnostic: the host is configured, not assumed` | `#0-host-agnostic-the-host-is-configured-not-assumed` |
| `§1 — Identity & philosophy` | `#1-identity--philosophy` |
| `§2 — Deterministic core vs judgment (the boundary)` | `#2-deterministic-core-vs-judgment-the-boundary` |
| `§3 — Taxonomy (from the config)` | `#3-taxonomy-from-the-config` |
| `§4 — Conventions` | `#4-conventions` |
| `§5 — Operations — index (on-demand loading)` | `#5-operations--index-on-demand-loading` |
| `§6 — Log entry` | `#6-log-entry` |
| `§7 — Limits & delegations` | `#7-limits--delegations` |

Doppio `-` su `§1`/`§5`/`§7` è corretto (carattere `&`/`—` rimosso lascia due spazi → due hyphen).
Nessun titolo/contenuto di sezione viene alterato (FR-007: solo aggiunta ToC).

## 4. Pointer «How to invoke» per le eval-skill (DA-1/FR-010)

Sostituisce il blockquote callout (A2:31–37, A3:30–36). Forma (closure-safe, host-agnostica,
mantiene la forma robusta `uv run --project .sertor` già richiesta da FEAT-021):

```
> **How to invoke `sertor-rag`.** The runtime CLI lives in the project's `.sertor/.venv` (not on
> `PATH`); route every call through `uv run --project .sertor sertor-rag <args>`. For the two
> invocation levels, the venv fallback and the Windows notes, see `sertor-cli-reference.md` (it ships
> with the RAG capability).
```

Invarianti: contiene `uv run --project .sertor` (FEAT-021 presence), contiene `` `sertor-cli-reference.md` ``
(closure), NON contiene `uvx --from`/`github.com/themetriost/Sertor` (no installer inline), nessun
ALL-CAPS fuori allowlist (`PATH` ok).

## 5. Guardie (artefatti di test)

| Guardia | File | Copre |
|---|---|---|
| Stile skill (`sertor`) | `packages/sertor/tests/test_assets_skill_style.py` (nuovo) | A1–A4: ALL-CAPS=0, no `[[`, pointer eval, pin semantico, meta |
| Stile skill (`sertor-flow`) | `packages/sertor-flow/tests/unit/test_assets_skill_style.py` (nuovo) | A5: ALL-CAPS=0 |
| «How to invoke» 1 fonte (estesa) | `packages/sertor/tests/test_assets_cli_invocation.py` | + `test_eval_skills_point_to_reference` |
| Parità Copilot (invariata, deve restare verde) | `packages/sertor/tests/test_assets_copilot_parity.py` | no `.claude/`/slash/Claude + closure |
| Sync dogfood `sertor` (invariata) | `tests/unit/test_assets_sync.py` | A4 → `.claude/` |
| Sync dogfood `sertor-flow` (invariata) | `packages/sertor-flow/tests/unit/test_assets_sync.py` | A5 → `.claude/` |

## 6. Invarianti (pin) — riferimento

- **CS-1**: `[A-Z]{4,}` (post-strip, meno allowlist) == 0 su A1–A5.
- **CS-2**: nessuna regola proibitiva duplicata inline↔sezione (casi noti §1.2 requirements).
- **CS-3**: `## Contents` + lista `- [§N …](#…)` in testa ad A4; ≥8 heading `## `.
- **CS-4**: nessun `[[` bare in A1–A4 (A5 non ne ha).
- **CS-5**: pin semantici presenti (`contracts/stable-substrings.md`); parità Copilot verde.
- **CS-6**: A4 e A5 dogfood byte-identici ai canoni dopo i rispettivi `sync`.
