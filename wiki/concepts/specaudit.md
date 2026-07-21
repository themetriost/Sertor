---
title: "SpecAudit — verdetto di conformità requisito↔codice, gemello top-down di SpecLift"
type: concept
tags: [specaudit, speclift, valutazione, requisiti, deterministic, moat, sandwich, conformita]
created: 2026-07-21
updated: 2026-07-21
sources: ["packages/specaudit/", ".claude/skills/specaudit/SKILL.md", "https://github.com/themetriost/Sinthari"]
---

# SpecAudit — audit di conformità requisito↔implementazione senza leggere codice

**SpecAudit** è il **gemello top-down** di [[speclift]]. Se SpecLift risale dal codice ai requisiti
(*bottom-up*: diff → EARS ancorate), SpecAudit scende dal **requisito originale** al **verdetto** di
conformità (*top-down*: requisito → giudizio), confrontando ciò che era **promesso** con ciò che
SpecLift ha estratto come **realmente fatto** per lo **stesso changeset**. Il suo valore: sapere in un
colpo cosa è stato **promesso ma non consegnato**, **consegnato ma non promesso**, o **consegnato con
deriva** — e saperlo *senza mai leggere codice*.

## Le due direzioni — bottom-up vs top-down

| | [[speclift]] (bottom-up) | **SpecAudit** (top-down) |
|---|---|---|
| **Ingresso** | un changeset git (diff) | il requisito **originale** + l'output SpecLift dello stesso changeset |
| **Uscita** | requisiti EARS **ancorati** al codice | un **verdetto per requisito** (con àncora citata) |
| **Domanda** | «cosa fa *davvero* il codice?» | «il codice *rispetta* ciò che era stato chiesto?» |
| **Verifica di realtà** | *moat*: riverifica le àncore sul filesystem | *moat strutturale*: copertura totale + integrità dei riferimenti |
| **Legge codice?** | sì, via evidence-locator (RAG/MCP) | **mai** — eredita le àncore di SpecLift e le *cita* |

SpecLift è il **produttore** dell'evidenza ancorata; SpecAudit ne è il **consumatore** puro: prende il
`*.speclift.json` (contratto pubblico versionato di SpecLift) e la fonte originale, e li **riconcilia**.
La coppia chiude il cerchio del lint semantico *code↔doc* che è la [[mission-vision|missione]] di Sertor:
SpecLift dice *cosa c'è*, SpecAudit dice *se combacia con cosa era chiesto*.

## Il verdetto per requisito

Il cuore di SpecAudit è la classificazione **N:M** di ogni requisito originale contro l'insieme (anche
vuoto) di item SpecLift che parlano della stessa cosa. Cinque verdetti:

- **SODDISFATTO** — l'originale è pienamente realizzato dagli item allineati, senza scostamenti.
- **PARZIALE** — realizzato solo in parte (copre un sottoinsieme del promesso).
- **MANCANTE** — nessun item SpecLift pertinente (promesso ma non consegnato).
- **DRIFTED** — realizzato *nello spirito* ma divergente in un dettaglio (tempistica, condizione, effetto
  collaterale). È il verdetto **più prezioso**: obbliga a spiegare *come* diverge, e resta una **proposta**
  da confermare, mai una decisione automatica.
- **NON_DOCUMENTATO** — item SpecLift che non mappa ad alcun originale (**consegnato ma non promesso**):
  finisce negli *extras*.

Invarianti che la CLI verifica *fail-loud*: **copertura totale** (ogni indice originale in esattamente un
gruppo, ogni indice SpecLift in un gruppo o negli extras — niente scarti silenziosi), **worst-wins** (un
gruppo eterogeneo prende il verdetto peggiore), **spiegazione specifica obbligatoria** per ogni verdetto
≠ SODDISFATTO, e **confidenza onesta** (severità × rilevabilità → punteggio di rischio, ordinamento del
report per rischio).

## Il confine D↔N — la CLI prepara e verifica, l'agente allinea e giudica

SpecAudit è lo **stesso stampo a due marce** di SpecLift (deterministico → agente → deterministico),
declinato sul giudizio anziché sulla stesura ([[deterministic-vs-judgment]]):

1. **`prepare`** (marcia 1, deterministica) — ingesta l'output SpecLift, risolve la fonte originale a
   cascata (`--requirements <dir>` · `--original <file>` · `--provided <path>` dall'agente via RAG/MCP;
   fonte assente = **gap dichiarato**, non errore), e indicizza i due insiemi in un `audit-bundle.json`.
2. **Adjudication** (la parte dell'**agente**) — l'agente legge *solo* il bundle (testo + àncore già
   prodotte) e scrive `adjudicated.json` referenziando gli item **per indice**: allinea N:M e classifica.
3. **`report`** (marcia 2, deterministica) — riverifica gli invarianti strutturali, **attacca le àncore
   dal bundle per indice** (mai riverificate), aggrega la matrice, ordina per rischio ed emette
   l'`AuditReport` (JSON canonico + vista Markdown coincidente).

Il **confine di fiducia** è netto e volutamente più stretto di SpecLift: l'agente **non** legge codice,
**non** esegue test, **non** interroga la CI, **non** usa `search_code`/`find_symbol` — e **non**
riverifica le àncore di SpecLift, le *cita*. Un eventuale falso MANCANTE ereditato da un limite di
retrieval di SpecLift resta un limite dichiarato, non un compito di verifica di SpecAudit. Referenziando
per indice, l'agente **non può inventare** un'àncora: è il *moat strutturale* di SpecAudit (Principio XI —
il codice non chiama un LLM, l'«agente» è l'assistente conversazionale via skill, non una chiamata
programmatica). Un `audit` monolitico con `StubAdjudicator` copre l'uso offline/test.

## Pacchetto proprio, zero-deps, RAG via MCP

SpecAudit è stato **vendorato** dal repo `themetriost/Sinthari` (handoff 2026-07-02) come **membro di
workspace autonomo** `packages/specaudit`, colato dallo **stampo di [[speclift]]** (`packages/speclift`):
Clean Architecture (`domain`/`adapters`/`stages`/`pipeline`), 59 test con nidificazione preservata, skill
host-agnostica in `.claude/skills/specaudit/`, contratti + quickstart, pin di provenienza in
`VENDORING.md`. È **zero-deps** e **non importa** né `speclift` né `sertor_core` (consuma solo il
`*.speclift.json` via il suo contratto pubblico versionato): usa il RAG **solo** via l'MCP a monte, nel
percorso SpecLift che gli fornisce l'evidenza — mai direttamente. Questa purezza è ciò che ha reso la
**decisione di distribuzione** (E14-FEAT-002, 2026-07-14) semplice: SpecLift/SpecAudit vengono **fusi in
`sertor-flow`** come moduli + console-script (non pacchetti PyPI a nome nostro, per non ripubblicare una
capacità vendorata in handoff), esattamente perché — come `sertor-flow` — sono zero-deps e ortogonali al
RAG.

## Dogfood — la coppia SpecLift→SpecAudit su changeset reali

SpecAudit è stato anticipato (vendorato prima di completare l'audit-backlog) proprio per esercitare la
**coppia** durante il lavoro reale ([[dogfooding]]). Primo giro end-to-end sul changeset **A-03** (BM25
staleness auto-heal): SpecLift ha prodotto **6 EARS, 6/6 àncore verificate**; SpecAudit, confrontandole
con l'intento originale in 2 bullet, ha emesso **SODDISFATTO ×2 · NON_DOCUMENTATO ×2** — i due
NON_DOCUMENTATO un *finding reale* (il codice gestisce anche il caso «sidecar sparito», consegnato ma non
promesso dall'intento). La coppia ha dimostrato di funzionare su codice vero, non solo sui test upstream:
è il ciclo di lint semantico che le due capacità promettono, esercitato sul dogfood.

## Concetti correlati

- [[speclift]] — il gemello bottom-up: produce l'evidenza ancorata (`*.speclift.json`) che SpecAudit
  consuma; stesso «sandwich» deterministico + moat.
- [[deterministic-vs-judgment]] — il confine D↔N che entrambe incarnano (la CLI prepara/verifica,
  l'agente allinea/giudica).
- [[valutazione-e-non-regressione]] — SpecAudit ancora la *conformità*, come la valutazione ancora la
  *qualità*, alla realtà del repo.
- [[mcp-server]] — il veicolo (via SpecLift) da cui arriva l'evidenza; SpecAudit non lo tocca direttamente.

## Note storiche

- **Origine:** Sinthari (progetto federato, stesso titolare legale `themetriost`), gemello top-down di
  SpecLift.
- **Vendoring:** Sertor, E14-FEAT-003, 2026-07-02 (`packages/specaudit`, pin Sinthari `e1bbdb2`, 59 test).
- **Distribuzione:** E14-FEAT-002, decisione 2026-07-14 — fold in `sertor-flow` (moduli + console-script).
