# Requirements Quality Checklist: Ciclo di vita dell'installer (upgrade e uninstall)

**Purpose**: Validare la qualità della specifica `spec.md` (chiarezza, testabilità, completezza,
assenza di dettagli implementativi, misurabilità dei criteri di successo) prima di passare a
`/speckit-clarify` o `/speckit-plan`.
**Created**: 2026-06-17
**Feature**: [spec.md](../spec.md)

## Orientamento al valore (COSA/PERCHÉ, non COME)

- [x] CHK001 La spec descrive le capacità in termini di valore utente, senza prescrivere stack, API o
  codice. *(Le user story parlano di maintainer/ospite; i dettagli implementativi — `WriteStrategy`,
  classi, schema JSON concreto — sono confinati alle Assumptions come "domande di design ancora aperte".)*
- [x] CHK002 Le scelte implementative note (toolkit condiviso, diff a posteriori, esiti
  `updated`/`removed`) sono espresse come **vincoli/decisioni** e non come dettaglio di realizzazione.
  *(FR-017/FR-043 esprimono il vincolo, non il "come".)*
- [x] CHK003 Nessuna user story richiede al lettore di conoscere la struttura interna degli artefatti.

## User Stories e scenari di accettazione

- [x] CHK004 Ogni user story ha priorità assegnata (P1/P2) con motivazione. *(US1–US9.)*
- [x] CHK005 Ogni user story è indipendentemente testabile (campo *Independent Test* presente).
- [x] CHK006 Gli scenari di accettazione sono in forma Given/When/Then.
- [x] CHK007 Esiste almeno un MVP indipendente (US1 da sola consegna valore: Sertor rimovibile).
- [x] CHK008 Gli edge case sono enumerati (file senza marker, obsoleto non riconosciuto, client MCP
  assente, wiki senza conferma, ospite già allineato, install ≠ run).

## Copertura dei requisiti EARS della fonte

- [x] CHK009 I 34 REQ EARS dei requisiti sono mappati in FR della spec (comuni → Gruppo A; upgrade →
  Gruppo B; uninstall → Gruppo C/D; governance → Gruppo E; invarianti → Gruppo F).
- [x] CHK010 I 7 NFR della fonte sono riflessi (non-distruttività FR-050, idempotenza FR-005/026/044,
  host-agnosticità FR-052, performance SC-011, segreti FR-053, osservabilità FR-002/007, stdlib-first →
  rinviato come decisione di *come* nelle Assumptions).
- [x] CHK011 Le 4 decisioni risolte (Q1–Q4) sono riflesse e **non riaperte** (wiki opt-in FR-027/028;
  diff a posteriori FR-017; granularità FR-032; governance in ambito Gruppo E).

## Testabilità e non ambiguità dei requisiti

- [x] CHK012 Ogni FR è verificabile (azione + esito osservabile; nessun "il sistema dovrebbe funzionare
  bene").
- [x] CHK013 I requisiti "unwanted" (FR-004, FR-013) usano la forma condizionale If/Then.
- [x] CHK014 Non restano `[NEEDS CLARIFICATION]` su decisioni critiche di scope/sicurezza/UX.
  *(Le 4 critiche sono chiuse a monte; le residue sono di design, marcate come tali, non bloccanti.)*
- [x] CHK015 I termini chiave sono ancorati al vocabolario reale del codice (tipi A/B/C/D di artefatto,
  esiti, blocchi a marker, toolkit condiviso, capacità) — verificato contro la fonte e il kit.

## Criteri di successo misurabili e tech-agnostici

- [x] CHK016 Ogni SC è misurabile (conteggi 0/>0, percentuali, soglie temporali).
- [x] CHK017 Gli SC sono tech-agnostici (non nominano librerie/file specifici; "ricerca produce 0
  residui", "0 byte cambiati", "< 10 s").
- [x] CHK018 Gli SC coprono tutti gli obiettivi della fonte (CS-1..CS-9 → SC-001..SC-009) e aggiungono
  simmetria (SC-010) e performance (SC-011).

## Ambito e confini

- [x] CHK019 L'ambito in/out è esplicito (Assumptions: fuori ambito = rollback/versioning, upgrade
  runtime Python, dati di progetto, bootstrap del bootstrap, cross-utente, GUI, CI automatica).
- [x] CHK020 Gli "out of scope" che sono capacità future hanno una casa durevole citata (FEAT-006 per
  versioning/rollback; gli altri sono confini permanenti o già coperti dal merge idempotente).
- [x] CHK021 L'invariante "governance non dipende da retrieval/`sertor`" è dichiarato (FR-045).

## Ipotesi e dipendenze

- [x] CHK022 Le ipotesi adottate (default ragionevoli) sono documentate nella sezione Assumptions.
- [x] CHK023 Le dipendenze interne (toolkit condiviso, plan-builder come fonte di verità) sono nominate
  come vincoli, non come design imposto.

## Coerenza interna

- [x] CHK024 Nessuna contraddizione tra FR (es. FR-027 wiki preservato ↔ FR-020 rimozione asset
  standalone: il wiki è l'eccezione esplicita).
- [x] CHK025 La terminologia è uniforme in tutta la spec (capacità, artefatto, esito, runtime isolato,
  file condiviso).
- [x] CHK026 Frontmatter/intestazione coerenti (branch `048-lifecycle-installer`, data, input tracciato).

## Notes

- Esito complessivo: **PASS** — 26/26. La spec è pronta per `/speckit-plan`.
- `/speckit-clarify` è **opzionale**: le 4 domande critiche sono già chiuse a monte (§10 dei requisiti).
  Le ambiguità residue sono decisioni di *come* (forma delle primitive nel kit, derivazione dei plan,
  forma della dichiarazione statica dei path, conferma interattiva vs `--yes` non interattivo) → da
  sciogliere in `/speckit-plan`, non bloccanti per la spec.
