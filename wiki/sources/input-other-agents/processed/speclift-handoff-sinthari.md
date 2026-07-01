---
title: Handoff SpecLift — da Sinthari a Sertor (self-hosting + distribuzione sertor-flow)
type: handoff
tags: [handoff, speclift, sertor-flow, dogfooding, diff-to-ears, distribuzione, skill-runtime]
created: 2026-07-01
updated: 2026-07-01
from: Sinthari
to: Sertor
status: MVP pronto (mergiato in master) → richiesta self-hosting + distribuzione via sertor-flow
sources:
  - github.com/themetriost/Sinthari (PR #5, merge commit be4da28, master)
---

# Handoff: SpecLift — installalo su Sertor stesso e distribuiscilo via `sertor-flow`

**Da:** Sinthari · **A:** Sertor · **Data:** 2026-07-01

Questo è il passaggio di consegne di **SpecLift**: il lavoro è fatto, testato e mergiato in Sinthari.
Vi chiediamo due cose concrete (sezione 3); su **come** realizzarle decidete voi — conoscete meglio
le convenzioni del vostro installer/kit.

## 1. Cos'è SpecLift (in una frase)

Una capacità che, dato un **changeset git** (un commit, un range `A..B`, o il diff *staged*), genera
**requisiti EARS ancorati** a più livelli insieme (*multi-quota*: capacità utente / comportamento /
implementazione), ognuno ancorato a `file:righe` + simbolo + (se esiste) il test che fallirebbe se il
requisito si rompesse. È il ponte `diff → requisito`.

**Come funziona (il "sandwich deterministico"):** una CLI a due marce fa tutto il lavoro meccanico e
verificabile; **un solo stadio è intelligente** — l'agente chiamante, che scrive le frasi EARS a partire
dall'evidenza già ancorata. La CLI poi **riverifica** ogni àncora sul filesystem (il "moat") prima di
emettere il report: niente requisito ancorato a qualcosa che non regge.

## 2. Perché dovrebbe interessare a Sertor

- **Dogfooding**: Sertor già interroga se stesso col proprio RAG (corpus `sertor`). SpecLift è
  un'estensione naturale — usarlo sui vostri stessi changeset per generare requisiti ancorati e
  riconciliare `CLAUDE.md`/`requirements/`/wiki con l'implementazione reale, in linea col vostro
  "lint semantico" del rituale di step.
- **Distribuzione**: è un candidato naturale per `sertor-flow`, accanto a `requirements`/`speckit-*`.

## 3. Cosa chiediamo esplicitamente

1. **Installatelo su voi stessi** (self-hosting/dogfooding): rendete SpecLift utilizzabile nel repo
   Sertor, così potete generare requisiti EARS ancorati dai vostri changeset reali.
2. **Rendetelo disponibile in `sertor-flow`**: la stessa via di distribuzione delle vostre skill
   esistenti, così un ospite che installa `sertor-flow` riceve anche SpecLift.
3. **Il "come" lo decidete voi** — sia l'installazione su di voi stessi sia il meccanismo di
   distribuzione/packaging. Non prescriviamo un'implementazione: sotto trovate solo i vincoli di
   design da preservare (sezione 5) e una nota tecnica sul punto che, secondo noi, richiede una vostra
   decisione (sezione 6).

## 4. Dove sta il lavoro (fatto, testato, mergiato)

Repo: `github.com/themetriost/Sinthari`, mergiato in `master` (PR #5, merge commit `be4da28`, 103
file, +9008 righe). Artefatti:

- **Runtime CLI:** `src/speclift/` + `pyproject.toml` (entry point console `speclift`), due marce:
  - `speclift bundle <ref> [--out ...] [--repo ...] [--include-docs]` → estrae l'evidenza
    (diff→simboli/test ancorati) via **Sertor RAG** (vehicle CLI/MCP, mai `import sertor_core`),
    emette un fascicolo JSON (`items` indicizzati + diff + `excluded_sources`).
  - `speclift assemble --bundle .. --authored .. --out ..` → riverifica ogni àncora sul filesystem
    (il "moat") e produce il report canonico (JSON + Markdown).
- **Skill sottile:** `skills/speclift/SKILL.md` (host-agnostica, **fonte canonica**) — l'agente
  chiamante è la parte intelligente: legge il fascicolo, scrive le frasi EARS multi-quota
  referenziando gli item per indice, mai inventa àncore.
- **Contratti:** `specs/001-speclift-mvp/contracts/` (`cli.md`, `ears-author-port.md`,
  `evidence-bundle.schema.json`, `output.schema.json`) + requisiti canonici in `requirements/speclift/`.
- **Test:** `tests/` — 104 verdi.

## 5. Vincoli di design da preservare (decisioni prese, non da rimettere in discussione)

- **Sandwich deterministico**: CLI meccanica e verificabile; **un solo** stadio intelligente = l'agente
  chiamante che scrive le frasi EARS (mai un batch esterno o un LLM interno alla CLI).
- **Il "moat"**: ogni àncora (file:righe + simbolo + test) è riverificata sul filesystem dopo la
  stesura; ciò che non regge viene scartato (`excluded`), mai accettato in silenzio.
- **Multi-quota sempre**: capacità utente / comportamento / implementazione generati insieme, non uno
  scelto a priori.
- **Filtro sorgenti**: spec/requisiti (`specs/`, `requirements/`, `.specify/`) sempre esclusi
  (includerli sarebbe circolare — sono ciò contro cui SpecLift andrebbe confrontato, lavoro di
  SpecAudit); configurazione inclusa; documentazione opzionale via `--include-docs`.
- **Localizzazione solo via Sertor RAG vehicle** (CLI/MCP) — mai importare `sertor_core` a mano: è lo
  stesso principio che già seguite voi (Principio XI).
- **Fail-loud**: ref invalido, RAG giù, bundle invalido → errore esplicito con exit code dedicato
  (vedi `contracts/cli.md`), mai fallback silenzioso.
- **Corpo skill host-agnostico**: nessun path d'assistente né slash-command hardcoded — pensato per
  restare riusabile sugli assistenti che già targettizzate (Claude, Copilot, ...).

## 6. Nota tecnica per chi la impacchetta

SpecLift è, per quanto ne sappiamo, **la prima skill del flow con una CLI runtime propria** — non
solo istruzioni per l'agente. Le vostre skill attuali (`requirements`, `speckit-*`) sono asset puri
(`SKILL.md`). Questo significa che copiare solo l'asset non basta: serve decidere **come spedire il
comando `speclift`** — ad esempio vendorizzandolo come dipendenza del pacchetto `sertor-flow` stesso,
oppure come pacchetto separato (tipo `packages/speclift`) di cui `sertor-flow` dipende. `speclift`
richiede la presenza del Sertor RAG indicizzato nel progetto ospite (lo usa per localizzare simboli e
test). Lasciamo la scelta di packaging a voi: avete più contesto sulle vostre convenzioni di kit.

## 7. Fuori scope (capacità future, separate)

**SpecAudit** (confronto requisiti originali ↔ generati — "drift #2"), **Debrief**, **Guida al test**:
sono consumatori a valle dello stesso primitivo `diff→requisito`, ma capacità distinte e future.
SpecLift è solo il generatore.

## 8. Per approfondire

Se vi serve più contesto prima di decidere, nel repo Sinthari: `wiki/concepts/speclift.md`,
`wiki/concepts/deterministic-sandwich.md`, `wiki/syntheses/roadmap.md`,
`wiki/syntheses/handoff-speclift-to-sertor-flow.md` (quest'ultima è la nostra ricognizione della
struttura di `packages/sertor-flow` fatta ispezionando il vostro repo — skill come asset in
`src/sertor_flow/assets/claude/skills/<nome>/SKILL.md` + manifest generato da `generate.py`/`sync.py`).
