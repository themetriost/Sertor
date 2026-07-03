# Feature Spec — Il dogfood di Sertor come client Sertor fedele (machinery SpecKit)

- **Feature branch:** `087-a05-dogfood-client-debt` (continuazione; A-05 → E10-FEAT-027)
- **Deriva da:** E10-FEAT-027 (`requirements/debito-tecnico/dogfood-client-fedele/requirements.md`)
- **Created:** 2026-07-03
- **Status:** Draft (specify) — Q1/Q2 risolte; Q3 (come materializzare) → `plan`

## Perché (in una frase)

Il workspace di Sertor deve **esercitare lo stesso percorso d'install/layout SpecKit** che riceve un
ospite reale, così da eliminare il doppio special-case dogfood↔client (machinery mancante + agenti orfani)
che l'item A-05 dell'audit ha portato alla luce.

## User Scenarios & Testing

### Storia primaria
Come **manutentore/agente del dogfood di Sertor**, voglio che il workspace ottenga la machinery SpecKit
**allo stesso modo di un ospite** (via il percorso d'install) e non porti artefatti che nessun ospite ha,
così che le fasi SpecKit girino sul percorso reale e i riferimenti degli asset **risolvano** invece di
essere link morti tollerati.

### Scenari di accettazione (Given / When / Then)

- **AS-1 — surface risolta.** *Given* il dogfood dopo lo step di setup, *when* un asset (agente/skill)
  referenzia una skill o uno script SpecKit, *then* il file referenziato **esiste** (0 riferimenti irrisolti).
- **AS-2 — niente agenti orfani.** *Given* il repo, *when* si elencano `.claude/agents/speckit-*.md`,
  *then* il risultato è **vuoto** (nessun agente hand-authored).
- **AS-3 — no re-vendoring.** *Given* la machinery materializzata localmente, *when* si esegue `git status`,
  *then* **nessun** file di machinery rigenerabile compare come da committare (è gitignorata).
- **AS-4 — artefatti Sertor preservati.** *Given* la materializzazione, *when* la si esegue, *then*
  `.specify/memory/constitution.md` (v1.4.0), `.specify/templates/plan-template.md` (custom) e
  `.specify/feature.json` restano **byte-identici** a prima.
- **AS-5 — guardia anti-regressione.** *Given* la suite di test, *when* qualcuno reintroduce un agente
  `speckit-*` hand-authored **o** committa una copia della machinery rigenerabile, *then* un test **fallisce**.
- **AS-6 — setup documentato.** *Given* un clone fresco, *when* il manutentore legge la doc di setup dev,
  *then* trova lo step che materializza la machinery SpecKit (analogo a `uv sync`).
- **AS-7 — zero core.** *Given* il diff della feature, *when* lo si confronta con `sertor-core`, *then*
  `src/sertor_core/**` è **invariato**.

### Edge case
- **EC-1 — clone senza setup / CI.** La machinery è assente (gitignorata): una fase SpecKit non gira finché
  non si materializza; la doc lo dichiara, la guardia **non** dipende dalla presenza locale (asserisce
  assenze/tracciamento, gira offline).
- **EC-2 — console non-UTF8.** La materializzazione senza overlay UTF-8 aborta (`UnicodeEncodeError` cp1252):
  il percorso deve applicare `PYTHONUTF8`/`PYTHONIOENCODING` (come il vehicle di produzione).
- **EC-3 — re-run.** Materializzare due volte è idempotente e non tocca gli artefatti Sertor-authored.

## Requirements

I requisiti funzionali sono in `requirements/dogfood-client-fedele/requirements.md` (REQ-001…REQ-009).
Sintesi vincolante per l'accettazione:

- **FR (fedeltà):** surface SpecKit presente via install-path (REQ-001); artefatti Sertor-authored
  preservati (REQ-002/003).
- **FR (igiene git):** machinery rigenerabile **non** tracciata (REQ-004); nessun agente speckit
  hand-authored (REQ-005); guardia su entrambi (REQ-006).
- **FR (onestà/doc):** step di setup documentato (REQ-007); degradazione onesta in assenza (REQ-008).
- **FR (confine):** `sertor-core` invariato (REQ-009).

### Key Entities
- **Machinery SpecKit (rigenerabile):** `.claude/skills/speckit-*/`, `.specify/scripts/`, template/workflows/
  integrations upstream — *stato: gitignorata, materializzata dal setup*.
- **Artefatti Sertor-authored (tracciati):** `.specify/memory/constitution.md`, `.specify/templates/plan-template.md`,
  `.specify/feature.json` — *stato: committati, preservati*.
- **Guardia:** test di root che asserisce assenza di agenti speckit hand-authored e di copie di machinery tracciate.

## Success Criteria (misurabili)
- SC-1: 0 riferimenti SpecKit irrisolti dopo il setup.
- SC-2: 0 file di machinery rigenerabile tracciati in git.
- SC-3: 0 agenti `.claude/agents/speckit-*.md`.
- SC-4: 3/3 artefatti Sertor-authored byte-identici post-materializzazione.
- SC-5: `sertor-core` invariato (diff vuoto su `src/sertor_core/**`).
- SC-6: guardia verde in CI (offline, senza machinery locale).

## Scope

### In
Materializzazione sicura/isolata (layout **Claude**) + gitignore + rimozione 9 agenti orfani + guardia +
doc di setup dev.

### Out
Layout **Copilot**; modifiche a `sertor-flow`/installer o a `specify init`; ridistribuzione agenti agli
ospiti; qualunque tocco a `sertor-core`.

## Assumptions
- Rete disponibile per `uvx` al setup; pin upstream `SPECKIT_VERSION = 0.8.18` (fonte unica).
- Layout `specify init --ai claude` come osservato dal vivo (9 skill + `.specify/scripts/powershell/*` + template).
- Ritiro del fix de-reference di A-05 già applicato (branch corrente).

## [NEEDS CLARIFICATION → plan]
- **Q3 — come materializzare in sicurezza (design):** (a) `specify init` in dir isolata + copia chirurgica
  della sola machinery rigenerabile; (b) piccolo script/entrypoint dedicato di sola-materializzazione. Da
  decidere in `plan` con il Constitution Check (tocca il "come", non il "cosa").

## Decisioni bloccate (dall'utente, «1 2 3» 2026-07-03)
- **Q1:** rimuovere i 9 agenti hand-authored (End-state fedele = skill native).
- **Q2:** machinery **gitignorata** + step di setup (no re-vendoring — NFR-1).
