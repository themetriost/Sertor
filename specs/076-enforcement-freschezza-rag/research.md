# Research — enforcement deterministico della freschezza RAG (hook) (E10-FEAT-011)

**Branch**: `076-enforcement-freschezza-rag` · **Data**: 2026-06-24 · **Fase**: Phase 0 (design)

> Scopo: risolvere le due forche residue di *come* (**DA-D-r1** file di stato, **DA-D-r2** aggancio
> del segnale d'avvio) e ancorare il design ai meccanismi esistenti, prima di compilare `plan.md`.
> Le 4 decisioni di scope (DA-1..DA-4) sono **già fisse** nella spec — qui non si riaprono, si
> ancorano al codice.

---

## D-0 — Ancoraggio: ciò che esiste già (dato di partenza)

Verificato via MCP `sertor-rag` (`search_code`) + `Read` dei file (citazioni `path:lineno`).

### D-0a — Pattern hook host (memory-capture) = template del nuovo hook
**Decision**: il nuovo hook `rag-freshness` riusa **byte-per-byte la disciplina** di
`memory-capture.ps1` (`.claude/hooks/memory-capture.ps1`): wrapper `SessionEnd` *thin*, exit 0
sempre, `try/catch` che assorbe ogni esito, lettura tollerante del payload JSON da stdin, root da
`$env:CLAUDE_PROJECT_DIR` → `hook.cwd` → `'.'`.
**Rationale**: è il pattern collaudato per FR-017 (non-fatale) e FR-004 (solo vehicle). Lo script
delega tutto al vehicle CLI, **nessuna logica nello script** oltre l'orchestrazione (FR-002).
**Riferimenti**: `.claude/hooks/memory-capture.ps1:54-63` (delega + exit 0); pattern privacy-gate
`:36-41`. La differenza: `rag-freshness` invoca `sertor-rag index .` **poi** `sertor-rag doctor`,
deriva un verdetto e **scrive il file di stato** (memory-capture non scrive nulla).

### D-0b — Wiring installer per-assistente (install_rag.py) = seam riusato
**Decision**: il cablaggio segue **esattamente** il pattern memory-capture in `install_rag.py`
(FILE `CREATE_IF_ABSENT` per lo script + `SETTINGS_MERGE` `MERGE_DEDUP` per la voce `SessionEnd`),
parametrico su `assistant` via `AssistantProfile`/`AssistantId`.
**Rationale**: A-003/A-004 (meccanismo + seam di parità riusati). Nessun nuovo `ArtifactKind`,
`Surface` o `WriteStrategy` (YAGNI III).
**Riferimenti**: `install_rag.py:142-167` (costanti + `_copilot_memory_hook_specs`), `:317-340`
(append al plan), `:424-446` (`_rag_hook_fragment`/`_apply_rag_settings` dispatch art-aware),
`:554-607` (uninstall art-aware con `delete_if_empty` per il file Copilot), `:610-658` (upgrade
idempotente), `:510-551` (`sertor_owned_paths`: owned_files + shared_edits).

### D-0c — Formato hook nativo Copilot (kit) = render generato, non asset statico
**Decision**: la voce Copilot è **generata** da `render_copilot_hooks([HookEntrySpec(...)])`
(formato `{"version":1,"hooks":{<Event>:[entry piatta con timeoutSec]}}`), via il sentinel-source
nel plan, mai un asset JSON in formato Claude.
**Rationale**: lezione FEAT-011/049 — gli asset JSON in formato Claude sono **scartati** da Copilot
(audit 2026-06-17). La fonte unica `HookEntrySpec` impedisce drift Claude↔Copilot.
**Riferimenti**: `sertor-install-kit/.../surfaces.py:145-190` (`HookEntrySpec`/`render_copilot_hooks`,
R1..R5). Per il `SessionEnd` rag-freshness lo spec è gemello di `_copilot_memory_hook_specs`
(`install_rag.py:156-167`): `HookEntrySpec("SessionEnd", "command", "<pwsh -File …>", 15)`.

### D-0d — Vehicle consumati (su `master`, accertati)
`sertor-rag index .` (re-index incrementale: manifest SQLite FEAT-009 + cache embeddings FEAT-019 →
zero-embedding a corpus invariato, FR-002/003/NFR-1) e `sertor-rag doctor` (E12-FEAT-001: quattro
aree env/provider/indice/MCP con pass/warn/fail + `--json` schema `doctor.report/1` + exit-code gate,
offline-safe; FR-005/006). L'hook li **usa**, non li estende (Fuori ambito spec).

### D-0e — Guardia di sync asset (oggi)
`tests/unit/test_assets_sync.py` compara `assets/claude/**` ↔ `.claude/` (sync via
`sertor_installer.sync.sync_assets_to_claude` = `sync_subtree(_ANCHOR, "claude", …)`). **Gli hook RAG
vivono in `assets/rag/hooks/`** e NON sono coperti da quel sync: la copia dogfood
`.claude/hooks/memory-capture.ps1` è **identica** all'asset (verificato `diff` → IDENTICI) ma tenuta
allineata a mano. → FR-024 richiede una **guardia dedicata** per il nuovo hook rag (vedi D-3).

---

## D-1 — DA-D-r1: nome / posizione / formato del file di stato (RISOLTA)

**Opzioni considerate**
1. `.sertor/.rag-health` (file singolo, sotto la radice runtime già esistente). *(proposta spec)*
2. File dentro `.index*/` (accanto al manifest). Scartata: il refresh `--full` può `reset` la
   collezione/manifest; lo stato di salute deve **sopravvivere** anche a un wipe dell'indice
   (FR-008, «attraversa il confine di sessione»).
3. File in radice host (es. `.rag-health`). Scartata: sporca la radice host (igiene radice, feature
   016: `.sertor/` è l'unica sede runtime).

**Decision**
- **Posizione**: `.sertor/.rag-health.json` — sotto la radice runtime `.sertor/` (igiene radice
  confermata, feature 016), accanto a `.env`/`.index*`.
- **Formato**: **JSON** a schema piatto e stabile (leggibile dal segnale d'avvio e da un umano):

  ```json
  {
    "schema": "rag.health/1",
    "verdict": "degraded",
    "timestamp": "2026-06-24T20:50:00Z",
    "reason": "index area: stale (manifest mtime older than source files)",
    "areas": { "config": "pass", "provider": "warn", "index": "fail", "mcp": "pass" },
    "exit_code": 1
  }
  ```

  Campi minimi richiesti da FR-011: `verdict` (`healthy`|`degraded`), `timestamp` (ISO-8601 UTC),
  `reason` (causa/area che ha fallito, scrubbed dal vehicle). `areas`/`exit_code` sono additivi
  (derivati da `doctor --json`), utili al messaggio d'induzione. `schema` versiona il contratto.
**Rationale**: JSON perché il segnale d'avvio (anche un prompt Copilot statico) e l'agente lo leggono
senza parser custom; piatto perché non serve nidificazione (NFR-6 idempotenza by construction:
healthy = stato canonico, degraded = stato canonico, nessuna oscillazione). Nessun segreto (NFR-3:
`reason` viene dall'output `doctor` già scrubbed — non si compone testo nuovo dai segreti).
**Gitignore (azione necessaria, NON gratis)**: `RUNTIME_IGNORES` oggi è
`(".sertor/.venv/", ".sertor/.index*", ".sertor/.env")` (`gitignore_append.py:14`) — **non** copre
`.sertor/.rag-health.json`. Si **aggiunge** `.sertor/.rag-health.json` a `RUNTIME_IGNORES` nel kit
(unica fonte di verità: install lo scrive in `.gitignore`, uninstall lo rimuove via
`remove_gitignore_lines`). È l'unica modifica al kit, additiva e non-breaking.

**Clear a verdetto sano (FR-010/015, R-1)**: a verdetto `healthy` l'hook **riscrive** il file con
`verdict: "healthy"` (non lo cancella): il segnale d'avvio legge `healthy` → no-op, niente
inducement (idempotenza NFR-6). Scrivere `healthy` invece di cancellare evita l'ambiguità
«file assente = mai eseguito vs guarito» e rende l'ultimo verdetto sempre ispezionabile.

---

## D-2 — DA-D-r2: aggancio del segnale d'avvio (RISOLTA)

**Contesto**: oggi su Claude dogfood il `SessionStart` è cablato a `wiki-session-start.ps1`
(`assets/settings.hooks.json:3-14`), che carica roadmap/index/log. È un asset **wiki/SDLC**, non rag.

**Opzioni considerate**
1. **Riusare** `wiki-session-start.ps1`: aggiungere la lettura del file di stato rag dentro quello
   script. **Scartata**: viola FR-016 (isolamento) — accoppia rag↔wiki, e l'uninstall della
   capacità `rag` non potrebbe toccare un file di proprietà del wiki senza disturbarlo. Inoltre il
   wiki-session-start è un asset `assets/claude/**` coperto dalla guardia sync wiki; mescolarvi rag
   romperebbe i confini di capacità del lifecycle.
2. **Voce/script `SessionStart` dedicato** `rag-freshness-start.ps1` cablato alla capacità `rag`,
   accanto (non dentro) a quello wiki. **SCELTA.**

**Decision**
- **Claude**: nuovo script `rag-freshness-start.ps1` (asset `rag/hooks/`, target
  `.claude/hooks/rag-freshness-start.ps1`) + voce `SessionStart` propria in `.claude/settings.json`
  (merge dedup, accanto alla voce wiki — `merge_settings` preserva le voci esistenti). Lo script
  legge `.sertor/.rag-health.json`; se `degraded`, **emette su stdout** la direttiva d'induzione
  (il messaggio che Claude riceve come contesto SessionStart: «lo stato RAG è degradato per
  <reason> — esegui `sertor-rag index .` e/o riconnetti il server MCP prima di procedere»); se
  `healthy`/assente, **no-op** (exit 0, nessun output → nessuna induzione, NFR-6).
- **Copilot CLI**: il `SessionStart` è `type:"prompt"` (statico, nessuno script — A-005, lezione
  FEAT-008/wiki). La voce è un **prompt nativo generato** (`HookEntrySpec("SessionStart","prompt",
  "<direttiva statica>",10)` → `render_copilot_hooks`) che **istruisce l'agente** a leggere
  `.sertor/.rag-health.json` e, se degradato, a indurre l'azione correttiva. La direttiva è statica
  (Copilot CLI non esegue script al SessionStart), ma il *contenuto* del file di stato lo legge
  l'agente conversando — coerente col confine D↔N (FR-014: l'hook/segnale induce, l'agente esegue).

**Rationale**: voce dedicata = lifecycle granulare per-capacità `rag` (FR-022/023) + isolamento
reciproco (FR-016/018). La divergenza Claude (script) / Copilot (prompt statico) **non è un hack**:
è il formato **nativo** di ciascuno (su Claude lo script può leggere il file; su Copilot CLI il
SessionStart è solo un prompt → il file lo legge l'agente). Entrambi rispettano D↔N: nessuno *esegue*
la correzione, la inducono.
**Confine D↔N sul SessionStart**: lo script Claude **non** lancia `sertor-rag index` da sé (sarebbe
giudizio + costo bloccante all'avvio): emette la direttiva, l'agente decide ed esegue (FR-013/014).

---

## D-3 — Coesistenza, isolamento e guardia di sync (ancoraggio FR-016/018/024)

**Decision (coesistenza/isolamento)**: due hook `SessionEnd` distinti (`memory-capture` + nuovo
`rag-freshness`) cablati **entrambi** alla capacità `rag`, ma con **script e voci separati**
(FR-016). Il `merge_settings` (`MERGE_DEDUP`) aggiunge la voce rag-freshness **senza** toccare quella
memory-capture (dedup per `command`); l'isolamento a runtime è garantito dal fatto che il client
agente invoca ogni voce in un processo separato e ogni hook esce 0 (FR-018, `try/catch` → exit 0).

**Decision (guardia di sync, FR-024)**: nuova guardia di test che compara l'asset bundlato
`assets/rag/hooks/rag-freshness.ps1` (+ `rag-freshness-start.ps1`) con la copia dogfood
`.claude/hooks/*` corrispondente. Modellata su `test_assets_sync.py` ma **mirata agli asset rag**
(il sync `claude/` non li copre — D-0e). Una guardia gemella per `memory-capture` **non esiste oggi**
(la copia è tenuta a mano): la nuova guardia **chiude anche questo buco** per i due nuovi hook.
Il `sync_assets_to_claude` resta sul subtree `claude/`; per gli hook rag si propaga manualmente la
copia dogfood e la guardia la verifica.
**Riferimenti**: `test_assets_sync.py:31-41` (forma della guardia), `install_rag.py:526`
(`memory_hook_target` = owned_file dogfood).

---

## D-4 — Reclassificazione del rituale (CLAUDE.md, FR-019)

**Decision**: gli step 5 (re-index) e 8 (smoke) del *Rituale di step* (`CLAUDE.md:360`, `:400`)
vengono **annotati** «enforced via hook (E10-FEAT-011)» con la nota D↔N: *l'hook re-indicizza e
verifica (meccanico); l'agente esegue la correzione indotta all'avvio se lo stato è degradato
(giudizio)*. Non si **rimuovono** i passi (restano la rete fino a quando l'hook non è distribuito su
ogni ospite e fino a quando il buco filtro-metadata non è chiuso da E12 — vedi D-5): si
**riclassificano** da «standing behavior» a «enforced + rete agente».
**Rationale**: FR-019 chiede riclassificazione, non rimozione; US5/R-4 ricorda che il punto 8
dell'agente resta la rete per il buco `where`.

---

## D-5 — Promozione degli Out-of-Scope (regola «si promuovono, non restano appesi»)

Tre rinvii reali, ognuno mappato a una casa durevole (NON solo in `specs/`):

| Out-of-Scope | Casa durevole | Azione al plan |
|---|---|---|
| **Smoke col filtro metadata `where`** (buco `doctor`) | Backlog epica **usabilità E12** (owner di `doctor`), `requirements/usabilita/epic.md` §8 | Nuova riga **FEAT-011** «estensione `doctor` con check-query metadata-filtered» (Should) — QA-1 |
| **Staleness forte cross-processo del server MCP** | Epica **osservabilita** / server MCP (già tracciato, finding 2026-06-23) | Cross-ref, nessuna riga nuova (debito già esistente) |
| **Drift-detection** («è cambiato qualcosa?») | Epica **osservabilita** FEAT-012 (già esistente) | Cross-ref, nessuna riga nuova |

**Nota**: il backlog E12 (`epic.md`) ha già FEAT-001..FEAT-010; la nuova voce smoke-`where` è
**FEAT-011** dell'epica usabilità (da non confondere con FEAT-011 dell'epica debito-tecnico = questa
feature). La numerazione è per-epica.

---

## D-6 — Confini e non-regressione (vincoli)

- **`sertor-core` INVARIATO**: nessun import, nessun motore/porta/comando nuovo (Principio XI,
  FR-004/NFR-5). La feature è 100% installer + asset + governance.
- **`sertor-install-kit`**: unica modifica = `+ ".sertor/.rag-health.json"` in `RUNTIME_IGNORES`
  (additiva, non-breaking; tutti i consumatori usano la costante). Nessun nuovo seam.
- **`sertor` (installer)**: estensione del plan-builder `build_rag_plan` (+2 FILE, +2 SETTINGS_MERGE
  per SessionEnd/SessionStart × per-assistente) + `sertor_owned_paths` (+owned_files,
  +shared_edit per la voce SessionStart) + uninstall/upgrade dispatch (già art-aware, riuso).
- **Non-regressione**: le suite esistenti (`packages/sertor`, root, kit) restano verdi; il default
  `claude` non regredisce; il comportamento a indice fresco è invariato (FR-003/NFR-1).
