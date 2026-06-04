# Research — Lint semantico del wiki (scope ampliato: US3/US4-scrittura/US5)

Decisioni di design per il nuovo scope. Le decisioni R1–R7 (P1) sono in `plan.md` e restano valide.

## R8 — Porta git nel dominio (`GitPort`), adapter fuori
- **Decisione**: introdurre `GitPort` (Protocol) in `src/sertor_core/domain/ports.py`; implementazione
  concreta `SubprocessGitAdapter` in `src/sertor_core/adapters/git/`. Il modulo `wiki/semantic.py`
  dipende **solo** dalla porta, mai da `subprocess`/git.
- **Razionale**: Principio I (dipendenze verso il dominio) e testabilità (finding C1 dell'analyze): nei
  test si inietta un `FakeGit` deterministico, senza repo reale.
- **Alternative**: chiamare `subprocess` direttamente in `semantic.py` → viola Principio I, non testabile
  in isolamento. Scartata.

## R9 — Mappa entità↔pagine **derivata**, non mantenuta
- **Decisione**: `EntityPageMap` si **deriva** a ogni run dal frontmatter `sources:` delle pagine e dai
  wikilink/backlink; nessun indice persistito separato. `changed_paths` (file di codice) → pagine che li
  citano in `sources:` o nel corpo.
- **Razionale**: REQ-090 ammette "maintain **or** derive"; derivare evita un secondo stato da mantenere
  in sync (Principio III YAGNI/DRY) e riusa convenzioni esistenti (finding U3).
- **Alternative**: indice persistito entità→pagine → più veloce ma stato duplicato e a rischio drift.
  Scartata per ora (riapribile se la derivazione risulta lenta).

## R10 — Watermark come file di stato testuale sotto la radice wiki
- **Decisione**: `wiki/.sertor/semantic-watermark` contiene il **commit SHA** dell'ultimo lint
  completato (singola riga). `read_watermark(root) -> str | None`, `write_watermark(root, sha)`.
  La directory `.sertor/` è **esclusa** dalla scoperta pagine del lint e dall'indicizzazione.
- **Razionale**: portabile e ispezionabile, non tocca `.git` (finding U2); non distruttivo (Principio VI);
  assenza → baseline naturale (REQ-087/089).
- **Alternative**: git note / branch ref → più "git-native" ma opaco e accoppiato a git. Scartata.

## R11 — Verifica incrementale come **wrapper** attorno al baseline
- **Decisione**: funzione `semantic_lint_incremental(root, llm, facade, git, *, watermark_path, threshold,
  k_code, max_pages) -> SemanticReport`. Calcola le pagine da ri-verificare e **delega** a
  `semantic_lint(..., pages=<selezione>)` (già esistente, accetta `pages=`). `SemanticReport` esteso con
  `mode` (`baseline|incremental`) e `fallbacks` (lista di stringhe segnalate).
- **Razionale**: riusa il motore P1 (Principio III); il parametro `pages=` esiste già. Incrementale =
  solo selezione + watermark + fallback, niente duplicazione della logica di rilevazione.
- **Alternative**: nuovo motore separato → duplicazione. Scartata.

## R12 — Re-index del change set: **solo fallback working tree** (dipendenza FEAT-009)
- **Decisione**: il re-index incrementale reale (REQ-096) è **inattivo** perché **FEAT-009 non è
  costruita**. In questo ciclo il confronto usa il **fallback** (REQ-097): si legge il contesto codice
  dalla working tree / dal corpus esistente e si **segnala** in `report.fallbacks` che l'indice può
  essere stantio. Il punto d'aggancio per il re-index reale è predisposto ma non implementato.
- **Razionale**: dipendenza esterna dichiarata (finding D1 dell'analyze, D-7 dei requisiti). Meglio un
  fallback esplicito e segnalato che un confronto silenziosamente stantio (Principio IV).
- **Alternative**: bloccare US3 finché FEAT-009 esiste → rinvia valore già realizzabile. Scartata.

## R13 — Auto-fix scrittura: `apply_fixes`, chirurgico, solo generated, non interattivo
- **Decisione**: `apply_fixes(proposals, root, *, dry_run=False) -> list[FixApplication]`. Per
  `rewrite_claim`: sostituzione **della sola claim** nel file (match esatto del testo della claim →
  `proposed_text`), preservando il resto e il marcatore `provenance: generated`. Per `delete_page`:
  rimozione del file. **Rifiuta** ogni pagina `curated` (nessuna scrittura/cancellazione). `dry_run`
  produce le `FixApplication` senza toccare il filesystem.
- **Razionale**: REQ-078/079/080/085; diff minimo e revisionabile via git (Principio VI). Non
  interattiva → integrabile in hook/CI (NFR-08).
- **Alternative**: riscrittura dell'intera pagina via LLM → diff grande, rischio di alterare contenuto
  corretto. Scartata a favore della sostituzione chirurgica.
- **Edge**: se la claim non è più trovata nel file (testo cambiato) → `FixApplication` con esito
  `skipped` (no match), non un errore.

## R14 — Gate fuori dal dominio (CLI/hook), core resta libreria
- **Decisione**: il **core** espone `SemanticReport.ok`; il **gate** vive in un entrypoint CLI/hook —
  proposto `sertor wiki semantic-gate` (o funzione `run_semantic_gate(...) -> GateOutcome` nel layer
  services/CLI) — che orchestra: incrementale → `apply_fixes` su generated → confronto `report` vs
  soglia → **exit ≠ 0** se bloccato, **warning** sotto soglia, **override** esplicito (flag
  `--override`/env `SERTOR_SEMANTIC_OVERRIDE`) che fa procedere **registrando** l'override (log
  strutturato + record tracciabile).
- **Razionale**: finding A1/C1: il dominio non deve conoscere exit code né git; il blocco è una
  responsabilità del confine (CLI/hook). Trigger **a monte** del configuration-manager (REQ-092): le
  correzioni alle pagine generate finiscono nello **stesso commit**.
- **Alternative**: gate dentro `semantic_lint` → accoppia dominio e processo, viola Principio I.
  Scartata.

## Sintesi dipendenze/decisioni
- **GitPort** (R8) → `domain/ports.py` + adapter. **Watermark** (R10) → `conventions`/helper wiki.
- **Incrementale** (R11) riusa `semantic_lint(pages=)`. **Re-index reale** (R12) **rinviato a FEAT-009**.
- **apply_fixes** (R13) nel dominio wiki (solo filesystem, nessun git). **Gate** (R14) nel layer CLI/hook.
