# Research — Pulizia stile delle skill distribuite (E10-FEAT-022)

Branch: `080-pulizia-stile-skill` · Fase: Phase 0 (design). Ancoraggio: MCP `sertor-rag` +
`Read`/`Grep` sugli asset reali su `master`. **Nessun errore tool MCP** durante la ricognizione.

Questa feature è **forma/leggibilità** di asset host-facing (`.md`), **zero `sertor_core`**. Le
decisioni sotto sono *come* (lo scope è fissato dalla spec); ognuna risolve una forca `DA-D-*`.

---

## Findings (dato di partenza verificato)

### F-1 — Inventario ALL-CAPS reale (≥4 lettere, dopo stripping di code span/fenced block)
Misurato con uno script (regex `\b[A-Z]{4,}\b` su testo privato dei `` `...` `` e dei blocchi ```` ``` ````):

| File (canonico) | Tokens enfatici da convertire | Tokens legittimi da preservare |
|---|---|---|
| `rag/skills/guided-setup/SKILL.md` (189) | `ONLY`×3, `MANDATORY`, `EVERY`, `WITHOUT` | `SDLC`×3, `JSON` |
| `rag/skills/eval-suite-author/SKILL.md` (145) | `DERIVES`, `ONLY`×2, `BUILD`, `ASSISTED`, `DETERMINISTIC`×2, `DOES`×2, `DATA`, `NAVIGATION`, `DISCOVER`, `EMPTY`, `SHOULD` | `PATH`, `POSIX`, `STOP`×3, `JSON` |
| `rag/skills/eval-feedback/SKILL.md` (76) | `OFFER` | `PATH`, `POSIX`, `STOP` |
| `claude/skills/wiki-author/wiki-playbook.md` (281) | `SAME`, `JUDGMENT` | `JSON`, `YAML` |
| `requirements/SKILL.md` (`sertor-flow`, 163) | `SEMPRE` (IT) | `EARS`×6 |

Oltre ai ≥4, la pulizia (giudizio, non enforced dal grep) abbassa anche i **≤3 lettere** enfatici
(`NOT`, `DO NOT`, `WAS`, ecc.): troppo brevi/ambigui per una guardia deterministica, ma chiaro
shouting in prosa. `ONLY`/`EVERY` (≥4) **sono** invece coperti dal grep.

### F-2 — Wikilink orfani: uno solo, e bare
Dopo stripping dei code span, l'**unico** `[[...]]` bare nel `wiki-playbook.md` è
`[[assistant-targeting]]` (riga 52). Gli esempi didattici `` `[[page-name]]` `` /
`` `[[page-name|alias]]` `` (§4 Conventions) sono **dentro code span** → non orfani, non toccati.

### F-3 — Struttura sezioni del `wiki-playbook.md` per la ToC
Le sezioni numerate reali sono **8** `## 0.` … `## 7.`. Il `## [YYYY-MM-DD] …` (riga ~255) è
**dentro un fenced block** (esempio di formato log), **non** una heading → escluso dalla ToC. Le
subsection `### …` (Host-agnostic authoring, Placement, Truth/authority) sono opzionali (DA-D-2).

### F-4 — Callout «How to invoke» nelle eval-skill = ridondante con FEAT-021
`eval-suite-author/SKILL.md` (31–37) e `eval-feedback/SKILL.md` (30–36) portano un blockquote
`> **How to invoke `sertor-rag`.** …` **identico** al contenuto del riferimento unico
`rag/sertor-cli-reference.md` (FEAT-021). Va sostituito con un pointer (DA-1/FR-010).

### F-5 — Mappa sync/guardie reali (verificata)
- `python -m sertor_installer.sync` propaga **solo** `assets/claude/**` → `.claude/`. Copre il
  `wiki-author/wiki-playbook.md`. Guardia: `tests/unit/test_assets_sync.py`.
- `python -m sertor_flow.sync` propaga gli asset `claude/**` di `sertor-flow`. Copre
  `requirements/SKILL.md`. Guardia: `packages/sertor-flow/tests/unit/test_assets_sync.py`.
- Le **rag-skill** (`guided-setup`, `eval-*`) vivono sotto `assets/rag/skills/` → **non** coperte da
  alcun sync `.claude/`. `guided-setup` non ha copia dogfood; `eval-*` ne hanno una.
- Guardie di non-regressione esistenti: `test_assets_cli_invocation.py` (FEAT-021, «How to invoke» in
  una sola fonte + forma robusta + closure del reference), `test_assets_copilot_parity.py` (no
  `.claude/`/slash/nome Claude + reference closure).

### F-6 — ⚠️ FINDING NON PREVISTO: i dogfood `.claude/skills/eval-*` sono un FORK ITALIANO stantio
`diff` su `master`: `.claude/skills/eval-suite-author/SKILL.md` e `.claude/skills/eval-feedback/SKILL.md`
**non** sono copie byte-identiche del canon — sono una **vecchia traduzione italiana** (argument-hint,
User Input, Purpose/Scopo, sezioni in IT) divergente dal canon inglese. **Nessuna guardia di sync** le
copre → drift silenzioso **pre-esistente**, non introdotto da questa feature. La spec stessa (§1.1)
elenca come dogfood sync-guardati **solo** `wiki-playbook.md` e `requirements/SKILL.md`, coerente con
questo. **Decisione:** fuori ambito qui (riconciliare un fork IT→EN è un'azione di lingua/sync, non di
pulizia stile) → **promosso come debito tracciato** (vedi §Tracciamento). Le mie edit alle eval-skill
**canoniche** non toccano questo fork.

---

## Decisioni di design (forche `DA-D-*`)

### DA-D-1 — Criterio operativo «ALL-CAPS → imperativo/bold + why»
**Regola.** Un *ALL-CAPS enfatico* = parola intera in A–Z maiuscole, ≥2 lettere, in **prosa** (corpo
o `description:` del frontmatter), usata come enfasi. Si converte in:
- **bold** quando l'enfasi è load-bearing e merita peso visivo (es. una regola obbligatoria);
- **minuscolo semplice** quando è solo «shouting».

La motivazione/regola che il maiuscolo accompagnava **resta** (stessa frase o adiacente, FR-002).

**Esclusioni (preservate verbatim, FR-003):**
1. token dentro **code span** (`` `...` ``) o **fenced block** (```` ``` ````);
2. **output CLI citato** (`doctor: PASS`, `provider FAIL …` — qui già in code span);
3. **allowlist** di acronimi/keyword legittimi:
   `RAG CLI MCP API JSON JSONL YAML TOML URL NL POSIX HTTP SDLC MRR EARS FEAT REQ STOP PASS FAIL PATH`.
   Razionale dei meno ovvi: `STOP` = keyword letterale che la skill ordina all'agente («STOP and
   report»); `PATH` = nome della variabile d'ambiente; `EARS`/`FEAT`/`REQ` = id/metodo nel
   `requirements/SKILL.md`; `PASS`/`FAIL` = letterali dell'output `doctor`.

**Confine guardia vs giudizio.** La guardia deterministica enforce il **sottoinsieme ≥4 lettere**
(allineato a CS-1 `[A-Z]{4,}`); gli enfatici ≤3 lettere (`NOT`, `DO`, `WAS`) sono abbassati dal
giudizio nella pulizia ma **non** enforced (troppi falsi positivi a 3 lettere). `ONLY`/`EVERY` (4–5)
ricadono nel grep.

### DA-D-2 — Forma della ToC del `wiki-playbook.md`
Solo le **8 sezioni principali §0–§7** (più stabili delle subsection, R-5). Posizione: **subito dopo
il blockquote introduttivo**, prima di `## 0.`, sotto una heading `## Contents`. Link = **anchor
GitHub standard** (slug lowercase, punteggiatura rimossa, spazi→`-`). Gli 8 anchor esatti sono in
`contracts/style-rules.md`. CS-3 soddisfatto: ≥8 heading `## ` + lista `- [§N …](#…)` in testa.

### DA-D-3 — Riscrittura del wikilink orfano
**Rimozione della frase intera** «See `[[assistant-targeting]]` for the targeting mechanism.» (riga
52). Non load-bearing (A-002): il parentetico precedente descrive già *cosa fa* la parity guard
(«renders the distributable plans … and fails on a leaked assistant path, a slash-command, an
assistant name, or a payload file referenced but not deposited — *reference closure*»). Risultato:
il capoverso chiude su `… — *reference closure*).` — self-contained, nessun riferimento esterno
(FR-008/009). Scelta «rimozione» preferita a «riscrittura» perché niente da preservare.

### DA-D-4 — Forma della guardia anti-regressione (FR-014)
Una **nuova** guardia (additiva, non rimpiazza le esistenti):
- `packages/sertor/tests/test_assets_skill_style.py` (4 asset `sertor` via `read_asset_text`):
  1. **ALL-CAPS = 0** — per file: strip code span/fenced, `\b[A-Z]{4,}\b` **meno allowlist** == ∅;
  2. **zero wikilink orfani** — per file di skill distribuita: strip code span, **nessun** `[[`;
  3. **«How to invoke» = pointer** — le 2 eval-skill **non** contengono il callout inline
     `How to invoke `sertor-rag`` e **contengono** `` `sertor-cli-reference.md` ``;
  4. **pin semantico** — per file, una lista di **substring load-bearing stabili** ancora presenti
     (no perdita di regole; lista in `contracts/stable-substrings.md`);
  5. **meta** (positivi): la guardia *fallisce* su un ALL-CAPS reintrodotto e su un `[[` reintrodotto
     (non vacua).
- `packages/sertor-flow/tests/unit/test_assets_skill_style.py`: **ALL-CAPS = 0** per
  `requirements/SKILL.md` (letto via kit `read_asset_text("sertor_flow", …)`; allowlist `{EARS, FEAT,
  REQ}` oltre alla comune). Guardia package-local (no read cross-package), come il sync di `sertor-flow`.
- **Estensione** di `test_assets_cli_invocation.py` (FEAT-021): aggiunto `test_eval_skills_point_to_reference`
  (le eval-skill citano il reference e non il callout). La **closure** del reference è già coperta da
  `test_cli_reference_closure_in_rag_plan` (il reference è target del piano RAG dove citato; le
  eval-skill sono nel piano RAG → closure-safe by construction, come `guided-setup`).

### DA-D-5 — Condensazione «Hard boundary» + «What NOT to do»
Strategia **(A) tieni le sezioni, rimuovi solo i duplicati verbatim/semantici**, file per file, con
verifica item-by-item (A-001). Esito per file (dettaglio e mapping in `contracts/stable-substrings.md`):
- **guided-setup**: tutti e 7 gli item di «What NOT to do» (182–189) **duplicano** regole già inline
  (Step 4 / Consent gate / Hard boundary / Step 2 / Step 6). Verificati uno a uno presenti altrove →
  **sezione rimossa** (FR-006 «remove the heading and fold»: qui il fold è già fatto, ogni regola vive
  inline). I pin garantiscono la sopravvivenza di ciascuna regola.
- **eval-suite-author**: «What NOT to do» (139–145) ha **1 regola unica** («never write secrets») +
  «do not invent paths» (prohibition non verbatim altrove) → **tenute**; «do not run the evaluation on
  the user's behalf» duplica Purpose + Hard boundary («No execution») → **rimossa**. Sezione resta con
  2 item.
- **eval-feedback**: «What NOT to do» (72–76): #74/#75 duplicano la «Hard boundary (no implicit
  judgment)»; **unico** = #76 «do not write secrets» → **piegato** come terzo bullet della Hard
  boundary, heading «What NOT to do» **rimossa** (FR-006, single-item fold).

---

## Constitution Check — PRE design (gate v1.4.0)
- I PASS (zero core) · II PASS · III PASS (riusa guardie, nessuna astrazione nuova) · IV PASS · V PASS
  (aggiunge guardie) · VI PASS (edit idempotenti; install≠run invariato) · **VII PASS — la feature
  *è* leggibilità** · VIII PASS · IX PASS · **X PASS — i body restano host-agnostici; la rimozione del
  wikilink orfano *migliora* l'host-agnosticità** · **XI PASS — zero `sertor_core`, solo asset + test
  installer** · **XII PASS — la guardia fallisce loud sulla reintroduzione; il fork IT eval è
  *segnalato*, non sepolto** · **Missione PASS — contesto agente più pulito/veritiero = qualità del
  contesto reso all'agente (stella polare); rimuovere un link che punta al nulla sull'ospite toglie
  rumore fuorviante**. **12/12 + missione, nessuna deroga** (Complexity Tracking vuoto).

(Il Constitution Check POST-design è identico — vedi `plan.md`: nessuna scelta di design introduce
deroghe.)

---

## Tracciamento dello scope (rinvii promossi, non sepolti)
- **Fork IT dei dogfood `.claude/skills/eval-*`** (F-6): debito reale, **da promuovere** a backlog
  E10 (debito-tecnico) o roadmap — riconciliazione lingua/sync + guardia di sync per le rag-skill
  dogfood. **NON** risolto qui (fuori ambito stile). Segnalato nel report finale.
- Budget altitude in CI → **FEAT-024**. Stub `assets/copilot/` → **FEAT-023**. Traduzione IT→EN di
  `requirements/SKILL.md` → **E12**. (Già in spec §Tracciamento.)
