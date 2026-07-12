# Research — Rituale wiki anti-skip (097-rituale-anti-skip)

Phase 0. Risoluzione delle incognite di design. Le forche di scope sono già chiuse in clarify (DA-1/2/4);
qui si risolve **DA-3** (segnale drift) + i dettagli d'ancoraggio al codice reale.

## Decisione 1 — Scope dello step: git-diff vs base, con fallback graceful (DA-1)

- **Decisione:** `ritual-check` determina «le pagine dello step» via **`git diff --name-only <base>...HEAD`**
  (default base = merge-base con `master`; override `--base <ref>` o `--pages a.md,b.md`), filtrando ai file
  **sotto i `source_dirs`** del profilo (le pagine wiki). Confronta HEAD vs base anche per i **link** (per
  i backlink «nuovi»).
- **Rationale:** uno step/feature ≈ un branch → il diff vs base è il confine naturale e preciso di «cosa ho
  toccato in questo step», deterministico e offline (git locale). Più preciso del mtime-vs-log di `scan.py`
  (che può spannare più step).
- **Fallback host-agnostico (Principio X + XII):** se il repo non è git, o la base non è risolvibile, e non
  sono passate `--pages`, il tool **fallisce loud** con messaggio azionabile (usa `--base`/`--pages`), **mai**
  un insieme vuoto silenzioso (REQ-006). `--pages` è l'override esplicito che rende il tool usabile anche su
  host non-git.
- **Alternative:** mtime-vs-ultima-voce-log (come `scan.py`) — respinta come default (grossolana, spanna step);
  resta disponibile concettualmente ma non è il canale scelto.

## Decisione 2 — Superficie: nuovo sottocomando `ritual-check` (DA-2)

- **Decisione:** nuovo verbo `ritual-check` (non estensione di `scan`), con `--json`/summary propri, coerente
  con `scan`/`lint`/`append-log`. Modulo `ritual_check.py`, contract `RitualCheckResult` (`wiki.ritual_check/1`).
- **Rationale:** responsabilità distinta (suggerimento rituale ≠ inventario mtime di `scan`); superficie
  chiara, richiamabile esplicitamente nel rituale e distribuibile.

## Decisione 3 — Euristica dei candidati a distillazione

- **Decisione:** dai file changed (Decisione 1), costruire il **sotto-grafo dei backlink** tra le pagine
  changed e segnalare come **candidato** un gruppo di **≥2 pagine changed** che (a) condividono **≥2 backlink
  incrociati nuovi** (link tra loro presenti in HEAD ma non in base) **e** (b) **nessuna** delle pagine
  changed è una **nuova pagina** sotto `concepts/`/`tech/` (tassonomia da `wiki.config.toml`). Interpretazione:
  «più pagine parlano insieme di qualcosa di nuovo, ma nessuno ha creato la pagina-entità».
- **Rationale:** è esattamente il pattern dei due feedback (Noetix: pattern riapplicato su 2 pagine, mai
  distillato). Segnali **puramente strutturali** (link-graph + tassonomia + git), zero semantica. Il backlink
  graph è già costruito in `lint.py` → riuso/estrazione di un helper.
- **Confine:** il tool **elenca** i gruppi candidati; **non** decide se creare la pagina (giudizio → agente).

## Decisione 4 — Segnali di drift deterministici (DA-3)

- **Decisione (MVP):** due segnali **puramente wiki-interni** (host-agnostici), più uno **config-driven**:
  - **(a) `updated:` stantio** — pagina **changed** in git il cui frontmatter `updated:` **non** è stato
    portato alla data di modifica (updated < data del commit/diff): il contenuto è cambiato ma la pagina non è
    stata «rinfrescata» → candidata a lint. Deterministico via `frontmatter` + git.
  - **(b) vicini-di-modifica** — pagine **linkate dalle** pagine changed (via backlink-graph) che **non** sono
    esse stesse changed: il cambiamento potrebbe averle rese stantie → candidate a lint. Deterministico via
    link-graph.
  - **(c) *(config-driven, opzionale)* capability↔exec** — **se** `wiki.config.toml` definisce un blocco
    `[ritual]` con `capability_globs` (es. `src/**`, `specs/**`, `requirements/**`) e `exec_page` (es.
    `syntheses/roadmap.md`): se il diff tocca `capability_globs` ma **non** `exec_page`, segnala `exec_page`
    come candidato a drift. È **esattamente** il danno reale (EXEC stantio mentre lo stato di capacità cambia),
    ma **NON hardcodato** — vive nella config, così resta host-agnostico (Principio X). **Assente la config →
    segnale (c) disattivato** (nessuna assunzione).
- **Rationale:** (a)+(b) sono host-agnostici per costruzione (solo wiki+git). (c) cattura il caso di punta dei
  feedback ma solo se l'ospite lo configura → nessun path fisso. Tutti e tre producono **candidati**, mai un
  verdetto semantico (che resta all'agente col lint B).
- **Alternative:** confronto numerico di claim / freshness semantica — respinte (è **giudizio**, sconfina in
  D↔N; resta all'agente).

## Decisione 5 — Scaffold di dichiarazione emesso dal tool (DA-4)

- **Decisione:** l'output di `ritual-check` include lo **scaffold** della dichiarazione pre-popolato coi
  conteggi dei candidati, es.:
  `Rituale: record: <?> · distill: <N candidati → verdetto?> · lint: <M pagine drift → verdetto?>` —
  nel summary umano e nel JSON (campo `declaration_scaffold`). L'agente **sostituisce i `<?>`** coi verdetti.
- **Rationale:** mette i candidati **davanti** al verdetto → «distill: non serve» diventa una scelta
  consapevole, non un'omissione. Aggancia parte 1 e parte 3 (DA-4).

## Decisione 6 — Parte 3: contratto host-facing + distribuzione

- **Decisione:** aggiungere al blocco `SERTOR:WIKI-RITUAL` (claude-md-block) e al `wiki-playbook.md` la regola
  di **dichiarazione forzata** (`Rituale: record ✅ · distill: <verdetto> · lint: <verdetto>`, «non serve»
  incluso) + il rimando a `sertor-wiki-tools ritual-check` come strumento di scoperta. Bundlare gli asset
  (`packages/sertor/.../assets/**`) e coprire con `sertor_installer.sync` + `test_assets_sync` (parità
  Claude/Copilot). Il dogfood aggiorna anche la **prosa IT** del proprio `CLAUDE.md`/playbook (ownership-note).
- **Rationale:** REQ-010 (host-facing → distribuibile, non dogfood-only). La dichiarazione è **contratto di
  comportamento** (giudizio, non hook-enforced come i passi meccanici di FEAT-011): la leva è lo scaffold
  deterministico a cui rispondere.

## Sintesi

Tutte le incognite risolte (DA-1/2/3/4 + git-fallback + distribuzione). Nessun `NEEDS CLARIFICATION` residuo.
Entità dati → `data-model.md`; contratto CLI/JSON → `contracts/ritual-check.md`. Pronto per `/speckit-tasks`.
