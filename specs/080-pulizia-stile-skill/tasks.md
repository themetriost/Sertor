# Tasks — Pulizia stile delle skill distribuite (E10-FEAT-022)

**Branch**: `080-pulizia-stile-skill` · **Generato**: 2026-06-30
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/style-rules.md`](contracts/style-rules.md) · [`contracts/stable-substrings.md`](contracts/stable-substrings.md) · [`contracts/guard-contract.md`](contracts/guard-contract.md)
**Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: ADDITIVO / igiene host-facing, ZERO codice di core.**
> Tocca esclusivamente:
> - 5 asset Markdown MODIFICATI (`guided-setup/SKILL.md`, `eval-suite-author/SKILL.md`,
>   `eval-feedback/SKILL.md`, `wiki-author/wiki-playbook.md`, `requirements/SKILL.md`);
> - 2 copie dogfood ri-sincronizzate (A4 e A5) via script sync;
> - 2 file di test NUOVI (`test_assets_skill_style.py` in `sertor` + `sertor-flow`);
> - 1 estensione di test (`test_assets_cli_invocation.py`: +`test_eval_skills_point_to_reference`).
>
> `sertor_core` **INVARIATO**. `install_rag.py` **INVARIATO**. Zero nuovi
> `ArtifactKind`/`WriteStrategy`/`Surface`/seam del kit.
>
> **Fuori ambito esplicito (non toccare):**
> - Dogfood `.claude/skills/eval-suite-author/SKILL.md` e `.claude/skills/eval-feedback/SKILL.md`:
>   fork italiano stantio pre-esistente, non coperto da sync (F-6) — nessuna modifica qui.
> - Budget altitude CI → FEAT-024; stub `assets/copilot/` → FEAT-023; traduzione IT→EN → E12.
>
> **Vincoli trasversali:**
> - **RNF-1 (Principio XI):** zero modifiche a `sertor_core`; nessun codice runtime toccato.
> - **RNF-2 (host-agnostico):** body toccati privi di `.claude/`, slash-command, nomi-modello Claude.
> - **RNF-3 (semantica invariata):** ogni regola/istruzione load-bearing preservata (pin in
>   `contracts/stable-substrings.md`); allowlist ALL-CAPS rispettata (`contracts/style-rules.md` R1).
> - **RNF-4 (suite verde):** `test_assets_copilot_parity.py`, `test_assets_sync.py` (sertor + flow),
>   `test_assets_cli_invocation.py` restano verdi senza modifiche da parte di questa feature.
> - **RNF-5 (coerenza FEAT-021):** non re-introdurre né espandere il callout «How to invoke
>   `sertor-rag`» in nessun body; il pointer di FEAT-021 in `guided-setup` resta tale.
>
> **Strategia MVP/incrementale.**
> - **P1 Must prima** (Fase 1): A4 (ToC + wikilink orfano) è il Must critico; bloccante per sync A4
>   e per la guardia G1 (pin `## Contents`).
> - **P2 Should + P3 Could in parallelo** (Fase 2): le 4 edit A1/A2/A3/A5 sono indipendenti [P];
>   A2 e A3 incorporano US5 (pointer, P3 Could) co-locate nella stessa modifica file.
> - **Sync dopo gli edit** (Fase 3): A4-sync dipende da Fase 1; A5-sync dipende da TASK-A5; [P].
> - **Guardie dopo gli asset** (Fase 4): G1/G2/G3 creati/estesi una volta che i body sono stabili; [P].
> - **Polish in chiusura** (Fase 5): suite totale + CS check finale.

---

## Fase 0 — Setup: pre-flight (1 task)

> Prerequisiti: nessuno. Bloccante per tutte le fasi successive.

### TASK-S01 — Pre-flight: sincronizza il venv e verifica i percorsi

```powershell
cd C:\Workspace\Git\Sertor
uv sync --all-packages --extra dev
```

- [ ] Verifica che `uv sync --all-packages --extra dev` completi senza errori.
- [ ] Verifica che la suite colleghi senza crash di import:
      ```powershell
      uv run pytest --co -q -m "not cloud" 2>&1 | Select-String "ERROR"
      ```
      Nessun `ERROR` di import atteso.
- [ ] Verifica che i 5 asset in scope esistano sul branch:
  - `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md`
  - `packages/sertor/src/sertor_installer/assets/rag/skills/eval-suite-author/SKILL.md`
  - `packages/sertor/src/sertor_installer/assets/rag/skills/eval-feedback/SKILL.md`
  - `packages/sertor/src/sertor_installer/assets/claude/skills/wiki-author/wiki-playbook.md`
  - `packages/sertor-flow/src/sertor_flow/assets/claude/skills/requirements/SKILL.md`

---

## Fase 1 — US3/US4 (P1 Must): A4 `wiki-playbook.md` — ToC + wikilink orfano + ALL-CAPS (1 task)

> Prerequisiti: TASK-S01. Bloccante per TASK-US8-01 (sync A4) e TASK-G1 (pin `## Contents`).
> US6 (semantica invariata) e US7 (host-agnosticità) sono verificati inline in questo task.

### TASK-US3-01 — A4 `wiki-playbook.md`: inserisci ToC §0–§7, rimuovi wikilink orfano, normalizza ALL-CAPS

**File**: `packages/sertor/src/sertor_installer/assets/claude/skills/wiki-author/wiki-playbook.md` (MODIFICA)
→ dipende da: TASK-S01

**Mappa FR**: FR-007/008/009/001/002/003/011/012 · CS-1/CS-3/CS-4/CS-5 · US3/US4/US1/US6/US7 · R2/R3/R1(A4)

**A. Table of Contents (R2, FR-007, CS-3):**
- [ ] Apri il file. Individua il blockquote introduttivo iniziale (le righe iniziali con `>`).
- [ ] Immediatamente **dopo** il blockquote introduttivo e **prima** di `## 0.`, inserisci:

  ```markdown
  ## Contents

  - [§0 — Host-agnostic: the host is configured, not assumed](#0-host-agnostic-the-host-is-configured-not-assumed)
  - [§1 — Identity & philosophy](#1-identity--philosophy)
  - [§2 — Deterministic core vs judgment (the boundary)](#2-deterministic-core-vs-judgment-the-boundary)
  - [§3 — Taxonomy (from the config)](#3-taxonomy-from-the-config)
  - [§4 — Conventions](#4-conventions)
  - [§5 — Operations — index (on-demand loading)](#5-operations--index-on-demand-loading)
  - [§6 — Log entry](#6-log-entry)
  - [§7 — Limits & delegations](#7-limits--delegations)
  ```

  (Anchor esatti da `data-model.md` §3; il doppio `-` su §1/§5/§7 è corretto per `&`/`—` rimossi
  dal slug GitHub. Nota: l'anchor `#5-operations--index-on-demand-loading` usa due trattini
  perché `—` produce due trattini nel slug.)

- [ ] Verifica invariante: nessun titolo `## N.` esistente è stato rinominato o spostato.
- [ ] Verifica invariante: il file contiene `## Contents` e almeno 8 heading `## `.

**B. Wikilink orfano (R3, FR-008/009, CS-4):**
- [ ] Individua la riga contenente `[[assistant-targeting]]`
      (testo atteso: `See [[assistant-targeting]] for the targeting mechanism.` o formulazione
      equivalente — verifica il testo esatto prima di rimuovere).
- [ ] **Rimuovi l'intera frase** contenente `[[assistant-targeting]]`.
      Il capoverso che la precede descrive già la parity guard in modo self-contained (A-002).
- [ ] Quick-check: dopo strip dei code span, il file non contiene più `[[`:
      ```powershell
      Select-String -Path "packages/sertor/src/sertor_installer/assets/claude/skills/wiki-author/wiki-playbook.md" `
          -Pattern "\[\[" | Where-Object { $_.Line -notmatch "^\s*\`" }
      ```
      Nessun match atteso fuori code span.

**C. ALL-CAPS enfatico (R1, FR-001/002/003, CS-1):**
- [ ] Normalizza `SAME` — verifica il contesto della frase; scegli `**same**` se il senso è
      «stessa copia byte-identica» (load-bearing) oppure `same` senza bold se è solo shouting.
      Preserva il *why* nella stessa frase (FR-002).
- [ ] Normalizza `JUDGMENT` → `**Judgment**` (maiuscolo iniziale per nome comune enfatizzato;
      la frase tipica è «**Judgment** is left to you» — verifica il testo esatto).
- [ ] Verifica che `JSON` e `YAML` (allowlist, ≥4 lettere) restino intatti.
- [ ] Quick-check residuo ALL-CAPS ≥4 (deve restituire set vuoto):
      ```powershell
      uv run python -c "
      import re, pathlib
      t = pathlib.Path('packages/sertor/src/sertor_installer/assets/claude/skills/wiki-author/wiki-playbook.md').read_text(encoding='utf-8')
      t = re.sub(r'\`\`\`.*?\`\`\`', ' ', t, flags=re.S)
      t = re.sub(r'\`[^\`]*\`', ' ', t)
      allow = {'RAG','CLI','MCP','API','JSON','JSONL','YAML','TOML','URL','NL','POSIX','HTTP','SDLC','MRR','STOP','PASS','FAIL','PATH'}
      found = {m for m in re.findall(r'\b[A-Z]{4,}\b', t)} - allow
      print('Residui:', sorted(found) if found else 'nessuno (OK)')
      "
      ```

**D. Pin semantici e host-agnosticità (FR-011/012, CS-5):**
- [ ] Verifica tutti i pin di A4 (`contracts/stable-substrings.md` §A4):
  - `wiki.config.toml` presente
  - `sertor-wiki-tools` presente
  - `append-log` presente
  - `parity guard` presente
  - `## Contents` presente (appena inserito)
- [ ] Verifica host-agnosticità (RNF-2): zero `.claude/`, slash-command, nome-modello Claude nel file.

---

## Fase 2 — US1/US2/US5 (P2 Should + P3 Could): Pulizia stile A1, A2, A3, A5 (4 task, [P])

> Prerequisiti: TASK-S01. I 4 task sono [P] tra loro (file distinti, nessuna dipendenza reciproca).
> US5 (pointer eval-skill, P3 Could) è co-locato in TASK-A2 e TASK-A3 (stessi file — un solo
> accesso per file è più efficiente).
> Bloccanti: TASK-A5 → TASK-US8-02; TASK-A1+A2+A3 → TASK-G1; TASK-A2+A3 → TASK-G3;
> TASK-A5 → TASK-G2.

### TASK-A1 [P] — A1 `guided-setup/SKILL.md`: normalizza ALL-CAPS, rimuovi «What NOT to do»

**File**: `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md` (MODIFICA)
→ dipende da: TASK-S01

**Mappa FR**: FR-001/002/003/004/005/006/011/012 · CS-1/CS-2/CS-5 · US1/US2/US6/US7 · R1/R5(A1)

**A. Normalizzazione ALL-CAPS (R1, FR-001/002/003, CS-1):**
- [ ] Apri il file. Individua e normalizza i token enfatici da `research.md` F-1 (colonna A1):
  - `ONLY` (×3) → `only`
  - `MANDATORY` → `**required**` (o `**always**` secondo contesto; è load-bearing)
  - `EVERY` → `every`
  - `WITHOUT` → `without`
  - `do NOT` (≤3 lettere, giudizio non enforced dalla guardia) → `do not` o `**never**`
  Per ogni sostituzione: preserva il *why* nella stessa frase o in quella adiacente (FR-002);
  non toccare code span/fenced block (FR-003); lascia intatti `SDLC` e `JSON` (allowlist).
- [ ] Quick-check residuo ≥4 (deve restituire set vuoto):
      ```powershell
      uv run python -c "
      import re, pathlib
      t = pathlib.Path('packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md').read_text(encoding='utf-8')
      t = re.sub(r'\`\`\`.*?\`\`\`', ' ', t, flags=re.S); t = re.sub(r'\`[^\`]*\`', ' ', t)
      allow = {'RAG','CLI','MCP','API','JSON','JSONL','YAML','TOML','URL','NL','POSIX','HTTP','SDLC','MRR','STOP','PASS','FAIL','PATH'}
      print(sorted({m for m in re.findall(r'\b[A-Z]{4,}\b', t)} - allow) or 'OK')
      "
      ```

**B. Condensazione «What NOT to do» (R5/A1, FR-004/005/006, CS-2):**
- [ ] Individua la sezione «What NOT to do» (righe ~182–189, 7 item nel file originale).
- [ ] Verifica item per item che ogni proibizione sia già espressa altrove nel file (A-001).
      Mapping da `contracts/stable-substrings.md` §A1:
  - secret-print → Step 4 (pin `never print`)
  - hand-fill `.sertor/.env` → Step 4 (pin `configure --set`)
  - mutation-without-confirm → Consent gate (pin `explicit confirmation`)
  - import-core → Hard boundary (pin `import the core`)
  - auto-provider → Step 2 (pin `propose`)
  - declare-done prima di doctor verde → Step 6 (pin `green`)
  - install-without-`--assistant` → Hard boundary (pin `--assistant`)
- [ ] **Rimuovi la sezione «What NOT to do»** intera (heading + 7 item), solo dopo aver confermato
      ogni regola altrove. Se un item non ha corrispondenza, conservarlo (FR-005 — no perdita).
- [ ] Verifica che il file non contenga più la heading `## What NOT to do` (o equivalente).

**C. Pin semantici e host-agnosticità:**
- [ ] Verifica pin A1 (`contracts/stable-substrings.md` §A1):
      `import the core` · `build_*` · `through a vehicle` · `--assistant` · `explicit confirmation`
      · `configure --set` · `never print` · `green` · `propose`
- [ ] Verifica host-agnosticità (RNF-2): zero `.claude/`, slash-command, nome-modello Claude.

---

### TASK-A2 [P] — A2 `eval-suite-author/SKILL.md`: ALL-CAPS + pointer «How to invoke» + condensa «What NOT to do»

**File**: `packages/sertor/src/sertor_installer/assets/rag/skills/eval-suite-author/SKILL.md` (MODIFICA)
→ dipende da: TASK-S01

**Mappa FR**: FR-001/002/003/004/005/006/010/011/012 · CS-1/CS-2/CS-5 · US1/US2/US5/US6/US7 · R1/R4/R5(A2)

**A. Pointer «How to invoke» (R4, FR-010, DA-1, CS-2):**
- [ ] Apri il file. Individua il blockquote callout «How to invoke» (righe ~31–37 nel file originale):
      il testo inizia con `> **How to invoke \`sertor-rag\`.** …`.
- [ ] **Sostituisci** l'intero blockquote con il pointer canonico da `data-model.md` §4:
      ```
      > **How to invoke `sertor-rag`.** The runtime CLI lives in the project's `.sertor/.venv` (not on
      > `PATH`); route every call through `uv run --project .sertor sertor-rag <args>`. For the two
      > invocation levels, the venv fallback and the Windows notes, see `sertor-cli-reference.md` (it ships
      > with the RAG capability).
      ```
- [ ] Verifica invarianti del pointer:
  - Contiene `uv run --project .sertor` (forma robusta, RNF-5)
  - Contiene `` `sertor-cli-reference.md` `` (pin A2, closure-safe via A-003/FEAT-021)
  - NON contiene `uvx --from` né `github.com/themetriost/Sertor`
  - NON contiene ALL-CAPS fuori allowlist (`PATH` è in allowlist)

**B. Normalizzazione ALL-CAPS (R1, FR-001/002/003, CS-1):**
- [ ] Normalizza i token enfatici da `research.md` F-1 (colonna A2):
  - `DERIVES` → `derives`
  - `ONLY` (×2) → `only`
  - `BUILD` → `build`
  - `ASSISTED` → `**assisted**` (load-bearing: designa la modalità assistita)
  - `DETERMINISTIC` (×2) → `**deterministic**`
  - `DOES NOT` / `DOES` → `does not` / `does`
  - `DATA` → `data`
  - `NAVIGATION` → `navigation`
  - `DISCOVER` → `discover`
  - `EMPTY` → `empty`
  - `SHOULD` → `should`
  Preserva `POSIX`, `STOP`, `JSON`, `PATH` (allowlist). Per ogni sostituzione: *why* invariato (FR-002).
- [ ] Quick-check residuo ≥4 (deve restituire set vuoto):
      ```powershell
      uv run python -c "
      import re, pathlib
      t = pathlib.Path('packages/sertor/src/sertor_installer/assets/rag/skills/eval-suite-author/SKILL.md').read_text(encoding='utf-8')
      t = re.sub(r'\`\`\`.*?\`\`\`', ' ', t, flags=re.S); t = re.sub(r'\`[^\`]*\`', ' ', t)
      allow = {'RAG','CLI','MCP','API','JSON','JSONL','YAML','TOML','URL','NL','POSIX','HTTP','SDLC','MRR','STOP','PASS','FAIL','PATH'}
      print(sorted({m for m in re.findall(r'\b[A-Z]{4,}\b', t)} - allow) or 'OK')
      "
      ```

**C. Condensazione «What NOT to do» (R5/A2, FR-004/005/006, CS-2):**
- [ ] Individua la sezione «What NOT to do» (righe ~139–145 nel file originale).
- [ ] Verifica item per item:
  - «never write secrets» → presente **solo** qui (UNICO) → **conserva**.
  - «do not invent paths» → presente **solo** qui (UNICO) → **conserva**.
  - «do not run the evaluation on the user's behalf» → duplica Purpose + Hard boundary «No execution»
    → **rimuovi** (FR-004; A-001 confermato da research.md DA-D-5).
- [ ] Applica: la sezione «What NOT to do» rimane con 2 item (secrets + paths); la terza voce è rimossa.
- [ ] Verifica: la sezione non contiene «do not run» né formulazioni equivalenti sull'esecuzione (rimosso).

**D. Pin semantici e host-agnosticità:**
- [ ] Verifica pin A2 (`contracts/stable-substrings.md` §A2):
      `import the core` · `eval add-case` · `approval` · `validate-path` · `graph-eval`
      · `secrets` · `sertor-cli-reference.md`
- [ ] Verifica host-agnosticità (RNF-2): zero `.claude/`, slash-command, nome-modello Claude.

---

### TASK-A3 [P] — A3 `eval-feedback/SKILL.md`: ALL-CAPS + pointer «How to invoke» + fold «What NOT to do»

**File**: `packages/sertor/src/sertor_installer/assets/rag/skills/eval-feedback/SKILL.md` (MODIFICA)
→ dipende da: TASK-S01

**Mappa FR**: FR-001/002/003/004/005/006/010/011/012 · CS-1/CS-2/CS-5 · US1/US2/US5/US6/US7 · R1/R4/R5(A3)

**A. Pointer «How to invoke» (R4, FR-010, DA-1, CS-2):**
- [ ] Apri il file. Individua il blockquote callout «How to invoke» (righe ~30–36 nel file originale).
- [ ] **Sostituisci** con il pointer canonico da `data-model.md` §4 (identico a TASK-A2 §A).
- [ ] Verifica invarianti del pointer (identici a TASK-A2 §A).

**B. Normalizzazione ALL-CAPS (R1, FR-001/002/003, CS-1):**
- [ ] Normalizza i token enfatici da `research.md` F-1 (colonna A3):
  - `OFFER` → `offer`
  - `WAS` (3 lettere, giudizio) → `was`
  - `NOT` (3 lettere, giudizio) → `not` o riformulazione diretta
  Preserva `PATH`, `POSIX`, `STOP` (allowlist). Preserva *why* nelle frasi (FR-002).
- [ ] Quick-check residuo ≥4:
      ```powershell
      uv run python -c "
      import re, pathlib
      t = pathlib.Path('packages/sertor/src/sertor_installer/assets/rag/skills/eval-feedback/SKILL.md').read_text(encoding='utf-8')
      t = re.sub(r'\`\`\`.*?\`\`\`', ' ', t, flags=re.S); t = re.sub(r'\`[^\`]*\`', ' ', t)
      allow = {'RAG','CLI','MCP','API','JSON','JSONL','YAML','TOML','URL','NL','POSIX','HTTP','SDLC','MRR','STOP','PASS','FAIL','PATH'}
      print(sorted({m for m in re.findall(r'\b[A-Z]{4,}\b', t)} - allow) or 'OK')
      "
      ```

**C. Condensazione «What NOT to do» — fold in «Hard boundary» (R5/A3, FR-004/005/006, CS-2):**
- [ ] Individua la sezione «What NOT to do» (righe ~72–76 nel file originale).
- [ ] Verifica item per item (research.md DA-D-5):
  - Item #74 e #75 → duplicano la «Hard boundary (no implicit judgment)» → **rimuovi**.
  - Item #76 «do not write secrets» → UNICO → **piega** come bullet aggiuntivo della «Hard boundary».
- [ ] **Rimuovi la heading «What NOT to do»** (FR-006, single-item fold; il suo unico item unico
      migra in «Hard boundary»).
- [ ] Verifica che la sezione «Hard boundary» ora includa il bullet sui segreti.
- [ ] Verifica che nessuna regola unica sia stata eliminata (FR-005).

**D. Pin semantici e host-agnosticità:**
- [ ] Verifica pin A3 (`contracts/stable-substrings.md` §A3):
      `core library` · `eval add-case` · `explicit` · `automatic mode` · `secrets`
      · `sertor-cli-reference.md`
- [ ] Verifica host-agnosticità (RNF-2): zero `.claude/`, slash-command, nome-modello Claude.

---

### TASK-A5 [P] — A5 `requirements/SKILL.md` (sertor-flow): normalizza ALL-CAPS (lingua IT invariata)

**File**: `packages/sertor-flow/src/sertor_flow/assets/claude/skills/requirements/SKILL.md` (MODIFICA)
→ dipende da: TASK-S01

**Mappa FR**: FR-001/002/003/011/012 · CS-1/CS-5 · US1/US6/US7 · R1(A5) · DA-2

**A. Normalizzazione ALL-CAPS (R1, FR-001/002/003, DA-2, CS-1):**
- [ ] Apri il file. Il solo token enfatico ≥4 in prosa è `SEMPRE` (research.md F-1, colonna A5).
- [ ] Normalizza `SEMPRE` → `sempre` (la lingua resta italiana — DA-2; IT→EN è E12, fuori ambito).
      La frase risultante diventa (es.) «Considera sempre l'input dell'utente» — il pin usa
      già la forma minuscola (`contracts/stable-substrings.md` §A5).
- [ ] Verifica allowlist estesa: `EARS` (×6, notazione requisiti) resta intatto.
- [ ] Quick-check residuo ≥4 con allowlist estesa per sertor-flow:
      ```powershell
      uv run python -c "
      import re, pathlib
      t = pathlib.Path('packages/sertor-flow/src/sertor_flow/assets/claude/skills/requirements/SKILL.md').read_text(encoding='utf-8')
      t = re.sub(r'\`\`\`.*?\`\`\`', ' ', t, flags=re.S); t = re.sub(r'\`[^\`]*\`', ' ', t)
      allow = {'RAG','CLI','MCP','API','JSON','JSONL','YAML','TOML','URL','NL','POSIX','HTTP','SDLC','MRR','STOP','PASS','FAIL','PATH','EARS','FEAT','REQ'}
      print(sorted({m for m in re.findall(r'\b[A-Z]{4,}\b', t)} - allow) or 'OK')
      "
      ```

**B. Pin semantici e host-agnosticità:**
- [ ] Verifica pin A5 (`contracts/stable-substrings.md` §A5):
      `EARS` · `MoSCoW` · `requirements/<epica>/epic.md` · `Considera sempre l'input dell'utente`
      (post-sostituzione usa `sempre` minuscolo — pin già scritto così).
- [ ] Verifica host-agnosticità (RNF-2): zero `.claude/`, slash-command, nome-modello Claude
      (il file è in italiano ma deve restare host-agnostico).

---

## Fase 3 — US8 (P2 Should): Sync dogfood A4 + A5 (2 task, [P])

> Prerequisiti: TASK-US3-01 (A4 modificato) per TASK-US8-01; TASK-A5 per TASK-US8-02.
> I 2 sync sono [P] tra loro (script e target distinti).
> Bloccanti per TASK-P01 (guardie sync devono essere verdi).
> **Non sincronizzare** `.claude/skills/eval-*/`: fork IT stantio, fuori ambito (F-6).

### TASK-US8-01 [P] — Sync dogfood A4: `python -m sertor_installer.sync`

**File**: `.claude/skills/wiki-author/wiki-playbook.md` (RE-SYNC automatico)
→ dipende da: TASK-US3-01

**Mappa FR**: FR-013/015 · CS-6 · US8 · data-model §5 · guard-contract G4

- [ ] Verifica che TASK-US3-01 sia completato (A4 canonico modificato).
- [ ] Esegui il sync `sertor`:
      ```powershell
      uv run python -m sertor_installer.sync
      ```
      Propaga `assets/claude/**` → `.claude/`; aggiorna `.claude/skills/wiki-author/wiki-playbook.md`.
- [ ] Verifica byte-parità con la guardia di sync:
      ```powershell
      uv run pytest tests/unit/test_assets_sync.py -q
      ```
      Deve essere verde.
- [ ] Verifica che A1, A2, A3 (sotto `assets/rag/`) **non** abbiano prodotto copie dogfood non
      volute sotto `.claude/` (il sync propaga solo `assets/claude/**`).

---

### TASK-US8-02 [P] — Sync dogfood A5: `python -m sertor_flow.sync`

**File**: `.claude/skills/requirements/SKILL.md` (RE-SYNC automatico)
→ dipende da: TASK-A5

**Mappa FR**: FR-013/015 · CS-6 · US8 · data-model §5 · guard-contract G4

- [ ] Verifica che TASK-A5 sia completato (A5 canonico modificato).
- [ ] Esegui il sync `sertor-flow`:
      ```powershell
      uv run python -m sertor_flow.sync
      ```
      Propaga gli asset `claude/**` di `sertor-flow` → `.claude/`.
- [ ] Verifica byte-parità con la guardia di sync:
      ```powershell
      uv run pytest packages/sertor-flow/tests/unit/test_assets_sync.py -q
      ```
      Deve essere verde.
- [ ] Verifica che `.claude/skills/requirements/SKILL.md` non contenga `SEMPRE` e contenga
      `sempre` (pin semantico post-sync).

---

## Fase 4 — US9/US6/US7 (P2 Should): Guardie anti-regressione G1, G2, G3 (3 task, [P])

> Prerequisiti:
> - TASK-G1 dipende da TASK-US3-01 + TASK-A1 + TASK-A2 + TASK-A3 (A1–A4 tutti modificati).
> - TASK-G2 dipende da TASK-A5.
> - TASK-G3 dipende da TASK-A2 + TASK-A3 (eval-skill con pointer inserito).
> I 3 task sono [P] tra loro (file distinti). Bloccanti per TASK-P01.
> US6 (semantica invariata) è verificato dai pin. US7 (parità) è verificato dalla guardia
> esistente `test_assets_copilot_parity.py` (guard-contract G4, verde senza modifiche).

### TASK-G1 [P] — Crea `packages/sertor/tests/test_assets_skill_style.py` (guardia G1)

**File**: `packages/sertor/tests/test_assets_skill_style.py` (NUOVO)
→ dipende da: TASK-US3-01, TASK-A1, TASK-A2, TASK-A3

**Mappa FR**: FR-001/008/010/012/014 · CS-1/CS-2/CS-4/CS-5 · US1/US4/US6/US7/US9 · guard-contract G1

- [ ] Crea il file `packages/sertor/tests/test_assets_skill_style.py` con il contenuto seguente.

**Import e costanti:**
```python
import re
import pytest
from sertor_installer.resources import read_asset_text

_IN_SCOPE = (
    "rag/skills/guided-setup/SKILL.md",
    "rag/skills/eval-suite-author/SKILL.md",
    "rag/skills/eval-feedback/SKILL.md",
    "claude/skills/wiki-author/wiki-playbook.md",
)
_ALLOW = frozenset({
    "RAG", "CLI", "MCP", "API", "JSON", "JSONL", "YAML", "TOML",
    "URL", "NL", "POSIX", "HTTP", "SDLC", "MRR", "STOP", "PASS", "FAIL", "PATH",
})
_EVAL = (
    "rag/skills/eval-suite-author/SKILL.md",
    "rag/skills/eval-feedback/SKILL.md",
)


def _strip_code(text: str) -> str:
    """Rimuove fenced block e inline span prima del grep ALL-CAPS (guard-contract G1)."""
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    return text
```

**Test ALL-CAPS (CS-1):**
```python
@pytest.mark.parametrize("asset", _IN_SCOPE)
def test_no_emphatic_allcaps(asset):
    """CS-1: zero ALL-CAPS enfatico (>=4 lettere) fuori allowlist e code span."""
    body = read_asset_text(asset)
    found = {m for m in re.findall(r"\b[A-Z]{4,}\b", _strip_code(body))} - _ALLOW
    assert not found, f"{asset}: ALL-CAPS enfatici residui: {sorted(found)}"
```

**Test wikilink orfani (CS-4):**
```python
@pytest.mark.parametrize("asset", _IN_SCOPE)
def test_no_orphan_wikilink(asset):
    """CS-4: zero wikilink orfani (nessun '[[' fuori code span) negli asset distribuiti."""
    body = read_asset_text(asset)
    assert "[[" not in _strip_code(body), (
        f"{asset}: contiene wikilink orfani fuori code span"
    )
```

**Test pointer eval-skill (US5, CS-2):**
```python
@pytest.mark.parametrize("asset", _EVAL)
def test_eval_skills_use_pointer(asset):
    """US5/CS-2: le eval-skill citano sertor-cli-reference.md e non il callout inline espanso."""
    body = read_asset_text(asset)
    assert "`sertor-cli-reference.md`" in body, (
        f"{asset}: manca il pointer a sertor-cli-reference.md"
    )
    # Il callout originale conteneva questa frase distintiva — non deve piu' esserci:
    assert "is not on `PATH`. Invoke it via" not in body, (
        f"{asset}: contiene ancora il callout inline espanso (deve essere un pointer)"
    )
```

**Test pin semantici (FR-012, CS-5):**
```python
_PINS: dict[str, list[str]] = {
    "rag/skills/guided-setup/SKILL.md": [
        "import the core", "build_*", "through a vehicle", "--assistant",
        "explicit confirmation", "configure --set", "never print", "green", "propose",
    ],
    "rag/skills/eval-suite-author/SKILL.md": [
        "import the core", "eval add-case", "approval", "validate-path",
        "graph-eval", "secrets", "sertor-cli-reference.md",
    ],
    "rag/skills/eval-feedback/SKILL.md": [
        "core library", "eval add-case", "explicit", "automatic mode",
        "secrets", "sertor-cli-reference.md",
    ],
    "claude/skills/wiki-author/wiki-playbook.md": [
        "wiki.config.toml", "sertor-wiki-tools", "append-log",
        "parity guard", "## Contents",
    ],
}


@pytest.mark.parametrize("asset,pins", list(_PINS.items()))
def test_semantic_pins(asset, pins):
    """FR-012/CS-5: ogni pin load-bearing e' presente nel body dopo la pulizia."""
    body = read_asset_text(asset)
    missing = [pin for pin in pins if pin not in body]
    assert not missing, f"{asset}: pin semantici mancanti: {missing}"
```

**Meta-test di non-vacuita' (guard-contract G1 §meta):**
```python
def test_guard_catches_reintroduced_allcaps():
    """Meta: la guardia ALL-CAPS e' non-vacua (MANDATORY non e' in allowlist)."""
    assert {"MANDATORY"} - _ALLOW != set(), (
        "Bug nella guardia: MANDATORY non dovrebbe essere in allowlist"
    )


def test_guard_catches_reintroduced_wikilink():
    """Meta: la guardia wikilink e' non-vacua."""
    assert "[[" in _strip_code("see [[x]] here"), (
        "Bug: _strip_code non preserva il wikilink fuori code span"
    )
```

- [ ] Esegui la guardia G1 per verifica immediata:
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_skill_style.py -v
      ```
      Tutti i test devono essere verdi. Se fallisce `test_no_emphatic_allcaps`, torna al task
      corrispondente (A1/A2/A3 o US3-01) per correggere il residuo.

---

### TASK-G2 [P] — Crea `packages/sertor-flow/tests/unit/test_assets_skill_style.py` (guardia G2)

**File**: `packages/sertor-flow/tests/unit/test_assets_skill_style.py` (NUOVO)
→ dipende da: TASK-A5

**Mappa FR**: FR-001/012/014 · CS-1/CS-5 · US1/US9 · guard-contract G2

- [ ] Crea il file `packages/sertor-flow/tests/unit/test_assets_skill_style.py`:

```python
import re
from sertor_install_kit import read_asset_text

_ALLOW_FLOW = frozenset({
    "RAG", "CLI", "MCP", "API", "JSON", "JSONL", "YAML", "TOML",
    "URL", "NL", "POSIX", "HTTP", "SDLC", "MRR", "STOP", "PASS", "FAIL", "PATH",
    "EARS", "FEAT", "REQ",  # allowlist estesa per sertor-flow (guard-contract G2)
})


def _strip_code(text: str) -> str:
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"`[^`]*`", " ", text)
    return text


def test_requirements_no_emphatic_allcaps():
    """CS-1 (A5): zero ALL-CAPS enfatico in requirements/SKILL.md fuori allowlist estesa.

    Atteso: SEMPRE rimosso -> set vuoto dopo strip e allowlist.
    EARS (x6) e' in allowlist e non deve essere segnalato.
    """
    body = read_asset_text("sertor_flow", "claude/skills/requirements/SKILL.md")
    found = {m for m in re.findall(r"\b[A-Z]{4,}\b", _strip_code(body))} - _ALLOW_FLOW
    assert not found, f"requirements/SKILL.md: ALL-CAPS enfatici residui: {sorted(found)}"
```

- [ ] Esegui la guardia G2:
      ```powershell
      uv run pytest packages/sertor-flow/tests/unit/test_assets_skill_style.py -v
      ```
      Deve essere verde (SEMPRE rimosso; EARS intatto).

---

### TASK-G3 [P] — Estendi `packages/sertor/tests/test_assets_cli_invocation.py` (guardia G3)

**File**: `packages/sertor/tests/test_assets_cli_invocation.py` (MODIFICA — solo aggiunta)
→ dipende da: TASK-A2, TASK-A3

**Mappa FR**: FR-010/014 · CS-2 · US5/US9 · guard-contract G3

- [ ] Apri `packages/sertor/tests/test_assets_cli_invocation.py`.
      Leggi la struttura: identifica `read_asset_text` e le eventuali costanti per le eval-skill.
- [ ] Aggiungi in fondo al file il test `test_eval_skills_point_to_reference`:
      ```python
      def test_eval_skills_point_to_reference():
          """G3: le eval-skill citano sertor-cli-reference.md (FR-010/CS-2).

          La closure del reference (target depositato dal piano RAG) e' gia' garantita da
          test_cli_reference_closure_in_rag_plan in test_assets_copilot_parity.py.
          """
          _EVAL_ASSETS = (
              "rag/skills/eval-suite-author/SKILL.md",
              "rag/skills/eval-feedback/SKILL.md",
          )
          for asset in _EVAL_ASSETS:
              body = read_asset_text(asset)
              assert "`sertor-cli-reference.md`" in body, (
                  f"{asset}: manca il pointer a sertor-cli-reference.md"
              )
      ```
      (Se il file usa costanti come `_EVAL_SUITE = "rag/skills/eval-suite-author/SKILL.md"`,
      riusale per coerenza con lo stile esistente.)

- [ ] Esegui l'intero file di test per verifica (nuovo test + quelli pre-esistenti):
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_cli_invocation.py -v
      ```
      Deve essere verde interamente.

---

## Fase 5 — Polish/cross-cutting (2 task)

> Prerequisiti: tutte le Fasi 0–4 complete. TASK-P01 non dipende da altri polish.
> TASK-P02 dipende da TASK-P01.

### TASK-P01 [P] — Suite verde totale + lint ruff

→ dipende da: tutte le Fasi 0–4

**Mappa FR**: RNF-1/2/3/4/5 · CS-1..6

- [ ] **Guardie nuove (Fase 4):**
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_skill_style.py -v
      uv run pytest packages/sertor-flow/tests/unit/test_assets_skill_style.py -v
      uv run pytest packages/sertor/tests/test_assets_cli_invocation.py -v
      ```
      Tutti verdi (G1/G2/G3 + test pre-esistenti di `cli_invocation`).

- [ ] **Guardie sync (CS-6):**
      ```powershell
      uv run pytest tests/unit/test_assets_sync.py -v
      uv run pytest packages/sertor-flow/tests/unit/test_assets_sync.py -v
      ```
      Entrambe verdi (A4 e A5 dogfood in byte-parità).

- [ ] **Parità Copilot (RNF-2/4, CS-5, guard-contract G4):**
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_copilot_parity.py -v
      ```
      Verde senza modifiche (guardia esistente che copre A1–A4 tramite piano RAG).

- [ ] **Non-regressione suite sertor (RNF-4):**
      ```powershell
      uv run pytest packages/sertor/tests/ -m "not cloud" -q
      ```

- [ ] **Non-regressione suite sertor-flow (RNF-4):**
      ```powershell
      uv run pytest packages/sertor-flow/tests/ -m "not cloud" -q
      ```

- [ ] **Non-regressione suite root (RNF-4):**
      ```powershell
      uv run pytest -m "not cloud" -q
      ```

- [ ] **Lint ruff sui file modificati/creati:**
      ```powershell
      uv run ruff check `
          packages/sertor/tests/test_assets_skill_style.py `
          packages/sertor-flow/tests/unit/test_assets_skill_style.py `
          packages/sertor/tests/test_assets_cli_invocation.py
      ```
      Zero errori (regole E,F,I,UP,B; line-length 100).

- [ ] **Quick-check manuale wikilink (CS-4):**
      ```powershell
      Select-String -Path "packages/sertor/src/sertor_installer/assets/**/*.md" -Pattern "\[\["
      ```
      Ogni match deve essere dentro code span (backtick) — nessun `[[` bare in prosa.

- [ ] **Quick-check manuale ALL-CAPS residuo (CS-1):**
      ```powershell
      Select-String `
          -Path "packages/sertor/src/sertor_installer/assets/rag/skills/**/*.md",`
                "packages/sertor/src/sertor_installer/assets/claude/skills/wiki-author/wiki-playbook.md",`
                "packages/sertor-flow/src/sertor_flow/assets/claude/skills/requirements/SKILL.md" `
          -Pattern "\b[A-Z]{4,}\b"
      ```
      Ogni match deve essere nell'allowlist o dentro code span/fenced block.

---

### TASK-P02 — Verifica CS-1..6 e additività trasversale

→ dipende da: TASK-P01

- [ ] **CS-1 (ALL-CAPS eliminato):** G1 `test_no_emphatic_allcaps` verde su A1–A4;
      G2 `test_requirements_no_emphatic_allcaps` verde su A5. ✓
- [ ] **CS-2 (sezioni ridondanti condensate):** «What NOT to do» di A1 rimossa (7 item tutti
      duplicati); A2 ridotta a 2 item; A3 heading rimossa con bullet secrets in Hard boundary;
      G1 `test_semantic_pins` verde (pin load-bearing tutti presenti). ✓
- [ ] **CS-3 (ToC in `wiki-playbook.md`):** file contiene `## Contents` + 8 voci `- [§N …](#…)`;
      G1 `test_semantic_pins` pin `## Contents` verde. ✓
- [ ] **CS-4 (zero wikilink orfani):** G1 `test_no_orphan_wikilink` verde su A1–A4;
      `[[assistant-targeting]]` rimosso da A4. ✓
- [ ] **CS-5 (nessun cambiamento semantico):** G1 `test_semantic_pins` verde per ogni file;
      `test_assets_copilot_parity.py` verde (parità host-agnostica). ✓
- [ ] **CS-6 (sync dogfood):** `test_assets_sync.py` sertor + sertor-flow verdi dopo i sync. ✓
- [ ] **Additività `sertor_core` — invarianza (RNF-1):** nessun file in `src/sertor_core/`
      modificato; zero import di `sertor_core` nei file di test creati. ✓
- [ ] **Additività installer — nessun nuovo seam:** `install_rag.py` e ogni altro file di codice
      Python del kit/installer **INVARIATI** (RNF-1). ✓
- [ ] **Fork IT dogfood eval — non riconciliato (dichiarato):** `.claude/skills/eval-suite-author/`
      e `.claude/skills/eval-feedback/` restano il fork IT stantio pre-esistente (F-6). ✓
- [ ] Segnala come **follow-up non-bloccanti (già a casa durevole):**
  - Riconciliazione fork IT dogfood eval (F-6) → backlog E10 (debito-tecnico).
  - Budget altitude in CI → **FEAT-024**.
  - Stub `assets/copilot/` → **FEAT-023**.
  - Traduzione IT→EN `requirements/SKILL.md` → **E12**.

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01  (pre-flight)
    │
    ├── TASK-US3-01  (A4: ToC+wikilink+ALL-CAPS) ── TASK-US8-01 [P] (sync A4)
    │                                                              │
    ├── TASK-A1 [P]  (A1: ALL-CAPS+condensa)  ───────────────┐   │
    ├── TASK-A2 [P]  (A2: ALL-CAPS+pointer+condensa) ────────┤   │
    ├── TASK-A3 [P]  (A3: ALL-CAPS+pointer+fold) ────────────┤   │
    └── TASK-A5 [P]  (A5: SEMPRE→sempre) ── TASK-US8-02 [P] ─┤   │
                                                              │   │
                TASK-G1 [P]  (guardia sertor: G1) ←US3+A1+A2+A3  │
                TASK-G2 [P]  (guardia sertor-flow: G2) ← A5       │
                TASK-G3 [P]  (cli_invocation +pointer) ← A2+A3    │
                    │                                              │
                    └──────────────── TASK-P01 [P] ← G1+G2+G3+US8-01+US8-02
                                          │
                                      TASK-P02
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|---|---|---|---|
| **US1** (ALL-CAPS eliminato, P2) | G1 `test_no_emphatic_allcaps` verde su A1–A4; G2 `test_requirements_no_emphatic_allcaps` verde su A5; quick-check manuale restituisce solo allowlist. | TASK-A1, TASK-A2, TASK-A3, TASK-US3-01, TASK-A5, TASK-G1, TASK-G2 | MECCANICO |
| **US2** (sezioni ridondanti, P2) | G1 `test_semantic_pins` verde (pin load-bearing presenti); heading «What NOT to do» assente in A1; A2 con 2 item; A3 senza heading con bullet secrets in Hard boundary. | TASK-A1, TASK-A2, TASK-A3, TASK-G1 | MECCANICO + MANUALE |
| **US3** (ToC wiki-playbook.md, P1 Must) | `## Contents` + lista 8 voci `- [§N …](#…)` in A4; G1 pin `## Contents` verde; nessun titolo di sezione rinominato. | TASK-US3-01, TASK-G1 | MECCANICO |
| **US4** (zero wikilink orfani, P1 Must) | G1 `test_no_orphan_wikilink` verde su A1–A4; grep `[[` senza match fuori code span. | TASK-US3-01, TASK-G1 | MECCANICO |
| **US5** (pointer «How to invoke» eval-skill, P3 Could) | G1 `test_eval_skills_use_pointer` verde (A2/A3 con pointer + assenza callout inline); G3 `test_eval_skills_point_to_reference` verde. | TASK-A2, TASK-A3, TASK-G1, TASK-G3 | MECCANICO |
| **US6** (semantica invariata, P1 Must) | G1 `test_semantic_pins` verde per ogni file (pin = regole load-bearing); confronto manuale pre/dopo: stesse azioni, stesso ordine, stesse restrizioni. | TASK-G1 (pin) + verifica manuale | MECCANICO + GIUDIZIO |
| **US7** (parità host-agnostica, P1 Must) | `test_assets_copilot_parity.py` verde senza modifiche (copre A1–A4 tramite piano RAG); zero `.claude/`, slash-command, nome-modello nei body toccati. | TASK-US3-01, TASK-A1, TASK-A2, TASK-A3 + guardia esistente | MECCANICO |
| **US8** (sync dogfood, P2) | `test_assets_sync.py` sertor verde dopo `python -m sertor_installer.sync` (A4); `test_assets_sync.py` sertor-flow verde dopo `python -m sertor_flow.sync` (A5). | TASK-US8-01, TASK-US8-02 | MECCANICO |
| **US9** (guardia anti-regressione, P2) | G1/G2 verdi allo stato corretto; meta-test `test_guard_catches_reintroduced_allcaps`/`_wikilink` verdi (non-vacuità); G3 verde; reintroducendo MANDATORY/`[[`, G1 fallirebbe. | TASK-G1, TASK-G2, TASK-G3 | MECCANICO |

---

## Parallelizzazione consigliata (MVP)

**Sprint 1 — dopo TASK-S01 (massima parallelizzazione):**
- TASK-US3-01 (A4: P1 Must; bloccante per sync A4 e G1)
- TASK-A1 [P] (A1: ALL-CAPS + condensa)
- TASK-A2 [P] (A2: ALL-CAPS + pointer + condensa; include US5)
- TASK-A3 [P] (A3: ALL-CAPS + pointer + fold; include US5)
- TASK-A5 [P] (A5: SEMPRE→sempre)

**Sprint 2 — dopo i rispettivi prerequisiti:**
- TASK-US8-01 [P] (sync A4 ← US3-01)
- TASK-US8-02 [P] (sync A5 ← A5)
- TASK-G1 [P]    (guardia sertor ← US3-01+A1+A2+A3)
- TASK-G2 [P]    (guardia sertor-flow ← A5)
- TASK-G3 [P]    (estensione cli_invocation ← A2+A3)

**Sprint finale — dopo Sprint 2 completo:**
- TASK-P01 [P] (suite verde totale + lint)
- TASK-P02    (CS-1..6 + additività)

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E10-FEAT-022 — pulizia stile skill distribuite

Fase SpecKit "tasks" completata per specs/080-pulizia-stile-skill.
13 task in 6 fasi:
  Fase 0 Setup (1 task):
    TASK-S01  uv sync --all-packages --extra dev; verifica percorsi 5 asset in scope.
  Fase 1 US3/US4 P1 Must — wiki-playbook.md (1 task):
    TASK-US3-01  A4 wiki-playbook.md: inserisci ToC §0-§7 (anchor da data-model §3) +
                 rimuovi frase [[assistant-targeting]] (riga ~52, non load-bearing) +
                 normalizza SAME/JUDGMENT (→ bold o minuscolo secondo contesto).
  Fase 2 US1/US2/US5 P2+P3 — asset A1/A2/A3/A5 (4 task, [P]):
    TASK-A1 [P]  guided-setup/SKILL.md: ONLY×3/MANDATORY/EVERY/WITHOUT → lowercase/bold;
                 rimuovi «What NOT to do» (7 item, tutti duplicati inline verificati;
                 mapping in stable-substrings §A1).
    TASK-A2 [P]  eval-suite-author/SKILL.md: DERIVES/ONLY×2/BUILD/ASSISTED/DETERMINISTIC×2/
                 DOES/DATA/NAVIGATION/DISCOVER/EMPTY/SHOULD → lowercase/bold;
                 callout → pointer data-model §4 (closure-safe, FEAT-021 A-003);
                 «What NOT to do» → 2 item (secrets+paths; rimuovi «do not run evaluation»).
    TASK-A3 [P]  eval-feedback/SKILL.md: OFFER→offer; callout→pointer data-model §4;
                 fold «What NOT to do» (secrets) in Hard boundary; rimuovi heading.
    TASK-A5 [P]  requirements/SKILL.md (sertor-flow): SEMPRE→sempre (IT invariata; EARS×6 ok).
  Fase 3 US8 P2 — Sync dogfood (2 task, [P]):
    TASK-US8-01 [P]  python -m sertor_installer.sync
                     → .claude/skills/wiki-author/wiki-playbook.md (A4 dogfood).
    TASK-US8-02 [P]  python -m sertor_flow.sync
                     → .claude/skills/requirements/SKILL.md (A5 dogfood).
  Fase 4 US9/US6/US7 P2 — Guardie (3 task, [P]):
    TASK-G1 [P]  packages/sertor/tests/test_assets_skill_style.py (NUOVO):
                 test_no_emphatic_allcaps (parametric _IN_SCOPE, allowlist _ALLOW) +
                 test_no_orphan_wikilink + test_eval_skills_use_pointer (_EVAL) +
                 test_semantic_pins (_PINS per file) + meta non-vacuita'.
    TASK-G2 [P]  packages/sertor-flow/tests/unit/test_assets_skill_style.py (NUOVO):
                 test_requirements_no_emphatic_allcaps (allowlist estesa +EARS/FEAT/REQ).
    TASK-G3 [P]  packages/sertor/tests/test_assets_cli_invocation.py (ESTENSIONE):
                 +test_eval_skills_point_to_reference.
  Fase 5 Polish (2 task):
    TASK-P01 [P]  suite sertor/sertor-flow/root (not cloud) verde; lint ruff; quick-check
                  ALL-CAPS+wikilink manuale.
    TASK-P02      CS-1..6 + additività trasversale; segnala follow-up F-6/FEAT-023/024/E12.

Natura: ADDITIVO / igiene host-facing. ZERO codice runtime di core. sertor_core INVARIATO.
install_rag.py INVARIATO. ZERO nuovi ArtifactKind/WriteStrategy/Surface/seam del kit.
Fuori ambito: dogfood .claude/skills/eval-*/ (fork IT stantio, F-6, non modificato).
Artefatti toccati:
  - 5 asset Markdown MODIFICATI (A1 guided-setup, A2 eval-suite-author, A3 eval-feedback,
    A4 wiki-playbook, A5 requirements)
  - 2 copie dogfood re-syncate (A4 e A5 → .claude/)
  - 2 file di test NUOVI (test_assets_skill_style.py in sertor e sertor-flow)
  - 1 file di test ESTESO (test_assets_cli_invocation.py +test_eval_skills_point_to_reference)
Copertura: FR-001..015, RNF-1..5, CS-1..6, US1..9.
Constitution CHECK: PASS 12/12 + missione (pre e post-design, plan.md §Constitution Check).
Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.
Template tasks da 079 (setup-plan.ps1/SKILL.md assenti nel repo).

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/080-pulizia-stile-skill/tasks.md` (questo file, nuovo)
