# Tasks — Rimozione stub `assets/copilot/` (E10-FEAT-023)

**Branch**: `081-stub-copilot` · **Generato**: 2026-06-30
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Dati**: [`data-model.md`](data-model.md)
**Contratti**: [`contracts/guard-anti-reappearance.md`](contracts/guard-anti-reappearance.md)
**Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** I task marcati `[P]` sono parallelizzabili all'interno della stessa fase
> (nessuna dipendenza reciproca). Il suffisso `→ dipende da` lista i task prerequisiti. Git **mai**
> qui: brief di commit al fondo per il `configuration-manager`.
>
> **Natura del cambiamento: SOTTRATTIVO / igiene host-facing, ZERO codice di core.**
> Tocca esclusivamente:
> - 4 file `.gitkeep` RIMOSSI (`assets/copilot/agents/`, `hooks/`, `instructions/`, `prompts/`);
> - 1 estensione di test ADDITIVA (`test_assets_copilot_guard.py`: `+test_no_copilot_asset_directory`).
>
> `sertor_core` **INVARIATO**. `install_rag.py` **INVARIATO**. `pyproject.toml` **INVARIATO**.
> Zero nuovi `ArtifactKind`/`WriteStrategy`/`Surface`/seam del kit.
>
> **Fuori ambito esplicito (non toccare):**
> - `install_rag.py` e `surfaces.py`: invariati (DA-D-2 risolta: no commento aggiunto).
> - `assets/claude/**` e `assets/rag/**`: sorgenti della generazione Copilot, non toccate.
> - `test_assets_copilot_parity.py` e `test_install_rag_copilot_cli.py`: test esistenti, invariati.
> - Budget altitude CI → FEAT-024; parity guard esteso a `.ps1`/`.json` → FEAT-024.
>
> **Vincoli trasversali:**
> - **RNF-1 (Principio XI):** zero modifiche a `sertor_core`; zero codice runtime toccato.
> - **RNF-2 (comportamento invariato):** `build_rag_plan(copilot-cli)` produce artefatti identici
>   prima e dopo (la generazione Copilot non legge mai `assets/copilot/`).
> - **RNF-3 (suite verde):** suite `sertor`, `sertor-install-kit`, `sertor-flow`, root — zero nuovi
>   fallimenti; `test_assets_copilot_guard.py` (guardie esistenti) e
>   `test_assets_copilot_parity.py` restano verdi senza modifiche.
> - **RNF-4 (impatto minimale):** al massimo 4 file rimossi + 1 funzione di test aggiunta.
>
> **Strategia MVP/incrementale.**
> - La feature è atomica: **un solo passo critico** (rimozione dei 4 `.gitkeep`) + **una guardia**
>   (estensione del test guard). Nessuna suddivisione MVP/incrementale è necessaria.
> - La sequenza vincolante è: verifica zero-consumatori → rimozione → guardia → polish.
> - TASK-G01 (guardia) è scritto prima del polish ma dipende da TASK-R01 per risultare verde.

---

## Fase 0 — Setup: pre-flight (1 task)

> Prerequisiti: nessuno. Bloccante per tutte le fasi successive.

### TASK-S01 — Pre-flight: sincronizza il venv e verifica i percorsi in scope

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
- [ ] Verifica che i 4 `.gitkeep` in scope esistano sul branch (saranno rimossi in Fase 1):
  - `packages/sertor/src/sertor_installer/assets/copilot/agents/.gitkeep`
  - `packages/sertor/src/sertor_installer/assets/copilot/hooks/.gitkeep`
  - `packages/sertor/src/sertor_installer/assets/copilot/instructions/.gitkeep`
  - `packages/sertor/src/sertor_installer/assets/copilot/prompts/.gitkeep`
- [ ] Verifica che il file da estendere esista:
  - `packages/sertor/tests/test_assets_copilot_guard.py`
- [ ] Verifica che la suite corrente sia verde come baseline (zero fallimenti pre-modifica):
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_copilot_guard.py `
                    packages/sertor/tests/test_assets_copilot_parity.py -q
      ```

---

## Fase 1 — US1/US2/US3 (P1 Must): Verifica zero-consumatori + Rimozione stub (2 task, sequenziali)

> Prerequisiti: TASK-S01.
> TASK-V01 è **bloccante** per TASK-R01: se emerges un consumatore, va prima corretto.
> TASK-R01 è bloccante per TASK-G01 (Fase 2) e TASK-P01 (Fase 3).

### TASK-V01 — Riconferma zero-consumatori di `assets/copilot/` (FR-005)

→ dipende da: TASK-S01

**Mappa FR**: FR-005 · A-001 · US3 · R-0 (research.md)

- [ ] Esegui la grep di sicurezza — atteso **zero righe** (le letture Python rooted a `copilot/`):
      ```powershell
      Select-String `
          -Path "packages\sertor\src\**\*.py", `
                "packages\sertor\tests\**\*.py" `
          -Pattern 'read_asset_text\("copilot|iter_asset_dir\("copilot|asset_path\("copilot'
      ```
      Atteso: nessun output (l'unica occorrenza della stringa `copilot/instructions` in
      `test_assets_copilot_guard.py:79` è dentro una **stringa di commento/docstring**, non una
      chiamata — non viene rilevata da questo pattern di chiamata di funzione).

- [ ] **Se emerge un consumatore reale** (una chiamata `read_asset_text("copilot/...)`
      o `iter_asset_dir("copilot/...")`): **STOP** — correggere o rimuovere quel consumatore
      prima di procedere con TASK-R01; la suite verde (RNF-3) lo segnalerebbe comunque.

- [ ] Se l'output è vuoto (caso atteso), annota «zero consumatori confermati» e procedi a TASK-R01.

---

### TASK-R01 — Rimozione dei 4 `.gitkeep` + verifica assenza directory (FR-001/002/003)

→ dipende da: TASK-V01 (zero consumatori confermati)

**Mappa FR**: FR-001/002/003 · CS-1 · US1/US2 · data-model §1

Git è delegato al `configuration-manager`; i comandi seguenti descrivono l'intento da passargli
nel brief.

**A. Rimozione dei 4 file `.gitkeep` (FR-001/002):**

- [ ] Rimuovi i 4 `.gitkeep` tramite `git rm`:
      ```powershell
      git rm packages/sertor/src/sertor_installer/assets/copilot/agents/.gitkeep
      git rm packages/sertor/src/sertor_installer/assets/copilot/hooks/.gitkeep
      git rm packages/sertor/src/sertor_installer/assets/copilot/instructions/.gitkeep
      git rm packages/sertor/src/sertor_installer/assets/copilot/prompts/.gitkeep
      ```
      (Git non traccia directory vuote: rimosso l'ultimo file di ciascuna sottocartella, le 4 dir
      `agents/`, `hooks/`, `instructions/`, `prompts/` e `copilot/` stessa scompaiono dal tree.)

**B. Nessun file di rimpiazzo (FR-003, Opzione A fissata):**

- [ ] Verifica che **non** sia stato aggiunto alcun file sotto `assets/copilot/` (README, marker o
      altro — l'Opzione B README è scartata nella spec e nel research):
      ```powershell
      git ls-files packages/sertor/src/sertor_installer/assets/copilot/
      ```
      Deve restituire **zero righe** (nessun file tracciato sotto `assets/copilot/`).

- [ ] Verifica che `assets/copilot/` non esista più nella working tree:
      ```powershell
      Test-Path "packages\sertor\src\sertor_installer\assets\copilot"
      ```
      Atteso: `False`.

**C. Verifica che le sorgenti reali siano intatte:**

- [ ] Verifica che `assets/claude/` e `assets/rag/` esistano e non siano state toccate:
      ```powershell
      Test-Path "packages\sertor\src\sertor_installer\assets\claude"
      Test-Path "packages\sertor\src\sertor_installer\assets\rag"
      ```
      Entrambi devono restituire `True`.

---

## Fase 2 — US6 (P2 Should): Guardia anti-ricomparsa (1 task)

> Prerequisiti: TASK-R01 (la dir deve essere assente perché il test risulti verde).
> Bloccante per TASK-P01.

### TASK-G01 — Estendi `test_assets_copilot_guard.py` con `test_no_copilot_asset_directory` (FR-008)

→ dipende da: TASK-R01

**Mappa FR**: FR-008 · CS-3 · US6 · R-1/DA-D-1 · contracts/guard-anti-reappearance.md

**A. Scrittura del test (contratto esatto da `contracts/guard-anti-reappearance.md`):**

- [ ] Apri `packages/sertor/tests/test_assets_copilot_guard.py`.
      Leggi la struttura: il file termina con `test_no_hand_maintained_copilot_prompt_bodies`
      (riga ~93). Aggiungi in fondo:

      ```python
      def test_no_copilot_asset_directory():
          """E10-FEAT-023: no static Copilot asset tree exists under `assets/`.

          All Copilot-facing payloads are GENERATED at runtime from `assets/claude/**` and
          `assets/rag/**` via render_copilot_hooks / render_custom_agent / render_prompt_file
          (sertor_install_kit.surfaces). A `copilot/` asset directory is a MISLEADING stub
          (suggests static assets that do not exist); this guard fails loud if it reappears
          (e.g. a `.gitkeep` re-added "to hold the place").
          """
          from sertor_installer.resources import asset_path

          assert not asset_path("copilot").is_dir()
      ```

      Note implementative:
      - `asset_path("copilot")` (`sertor_installer/resources.py:18`) ritorna un `Traversable`
        per `sertor_installer/assets/copilot`; su path inesistente `.is_dir()` è `False`.
      - **Nessun import aggiuntivo** in testa al file: `asset_path` è importata localmente
        nella funzione (coerente con lo stile del file per `sertor_installer.surfaces`).
      - **Nessuna modifica ai test esistenti**: solo aggiunta in fondo.

**B. Verifica immediata del nuovo test:**

- [ ] Esegui la sola guardia nuova (deve essere verde con `assets/copilot/` assente):
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_copilot_guard.py::test_no_copilot_asset_directory -v
      ```
      Atteso: `PASSED`.

- [ ] Verifica la semantica di failure simulata (opzionale, sanity check):
      Il test sarebbe rosso se `assets/copilot/agents/.gitkeep` venisse ricreato —
      `asset_path("copilot").is_dir()` ritornerebbe `True`, la guardia fallirebbe.
      Non è necessario eseguirla effettivamente: il contratto è ancorato alla semantica di
      `Traversable.is_dir()` su path inesistente.

**C. Verifica che le guardie esistenti restino verdi (FR-007, AC-4):**

- [ ] Esegui l'intero file di guardia:
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_copilot_guard.py -v
      ```
      Tutti i test esistenti + il nuovo devono essere `PASSED`.
      In particolare `test_no_hand_maintained_copilot_prompt_bodies` non deve regredire
      (non asserisce l'esistenza dei `.gitkeep`).

---

## Fase 3 — Polish/cross-cutting (2 task)

> Prerequisiti: tutte le Fasi 0–2 complete. TASK-P01 non dipende da altri polish.
> TASK-P02 dipende da TASK-P01.

### TASK-P01 — Non-regressione suite completa + build (CS-2/CS-3/CS-4)

→ dipende da: TASK-R01, TASK-G01

**Mappa FR**: FR-004/006/007/008 · RNF-1/2/3/4 · CS-2/CS-3/CS-4

**A. Guardia anti-ricomparsa + guardie Copilot (CS-3):**
- [ ] Guardia nuova + guardie esistenti (verifica complessiva del file guard):
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_copilot_guard.py -v
      ```
      Tutti verdi (`test_no_copilot_asset_directory` + guardie pre-esistenti).

**B. Parità Copilot — generazione invariata (CS-4, FR-004):**
- [ ] Verifica che `build_rag_plan(copilot-cli)` produca gli stessi artefatti (suite parity):
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_copilot_parity.py -v
      ```
      Verde senza modifiche (la generazione legge solo `assets/claude/**` e `assets/rag/**`).

- [ ] Verifica non-regressione test install Copilot:
      ```powershell
      uv run pytest packages/sertor/tests/test_install_rag_copilot_cli.py -v
      ```
      Verde (i test di installazione non dipendono da `assets/copilot/`).

**C. Build e packaging (CS-2, FR-006):**
- [ ] Verifica che `uv build` del pacchetto `sertor` completi senza errori
      (hatchling glob ricorsivo — nessuna modifica a `pyproject.toml` necessaria):
      ```powershell
      uv build -p sertor
      ```
      Deve completare senza errori e produrre il wheel.

- [ ] Verifica il test di packaging (integration):
      ```powershell
      uv run pytest -m integration tests/integration/test_packaging.py -v
      ```
      Verde (il wheel non dipende da file sotto `assets/copilot/`).

**D. Suite suite completa (RNF-3):**
- [ ] Non-regressione suite `sertor`:
      ```powershell
      uv run pytest packages/sertor/tests/ -m "not cloud" -q
      ```
      Zero nuovi fallimenti.

- [ ] Non-regressione suite root (incluse tutte le suite dei workspace member):
      ```powershell
      uv run pytest -m "not cloud" -q
      ```
      Zero nuovi fallimenti rispetto al baseline.

**E. Lint ruff sul file di test esteso:**
- [ ] Lint sul file modificato:
      ```powershell
      uv run ruff check packages/sertor/tests/test_assets_copilot_guard.py
      ```
      Zero errori (regole E,F,I,UP,B; line-length 100).

**F. Quick-check `pyproject.toml` invariato (FR-006, A-002):**
- [ ] Verifica che `packages/sertor/pyproject.toml` non sia stato toccato:
      ```powershell
      git diff packages/sertor/pyproject.toml
      ```
      Nessun diff atteso.

---

### TASK-P02 — Verifica CS-1..4 e invarianza trasversale

→ dipende da: TASK-P01

- [ ] **CS-1 (zero stub fuorvianti):** `git ls-files packages/sertor/src/sertor_installer/assets/copilot/`
      restituisce zero righe; `assets/copilot/` assente nella working tree. ✓
- [ ] **CS-2 (nessuna regressione build/wheel):** `uv build -p sertor` verde; `test_packaging.py`
      verde; `pyproject.toml` invariato. ✓
- [ ] **CS-3 (nessuna regressione suite):** `test_assets_copilot_guard.py` (incluse le guardie
      pre-esistenti + `test_no_copilot_asset_directory`), `test_assets_copilot_parity.py`,
      `test_install_rag_copilot_cli.py` e suite completa root verdi. ✓
- [ ] **CS-4 (comportamento installer invariato):** `test_assets_copilot_parity.py` verde;
      `test_install_rag_copilot_cli.py` verde; zero modifiche a `surfaces.py`/`install_rag.py`. ✓
- [ ] **Invarianza `sertor_core` (RNF-1):** nessun file in `src/sertor_core/` modificato;
      zero import di `sertor_core` nel test esteso. ✓
- [ ] **Invarianza codice Python di runtime (RNF-1/NFR-4):** `install_rag.py`, `surfaces.py`,
      `resources.py`, `install_wiki.py` **INVARIATI** — nessun commento aggiunto (DA-D-2). ✓
- [ ] **Nessun file di rimpiazzo (FR-003):** `assets/copilot/` assente e non sostituita da
      README/marker (Opzione A confermata). ✓
- [ ] Segnala come **follow-up non-bloccanti (già a casa durevole):**
  - Budget altitude CI → **FEAT-024**.
  - Parity guard esteso a `.ps1`/`.json` → **FEAT-024**.
  - Riconciliazione fork IT eval-skill → **FEAT-025**.
  - Guardia CI-enforced oltre il test pytest → eventuale **FEAT-024** (oggi non necessaria).

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01  (pre-flight)
    │
    ├── TASK-V01  (zero-consumatori grep — FR-005)
    │       │
    │   TASK-R01  (git rm 4 .gitkeep + verifica assenza — FR-001/002/003)
    │       │
    │   TASK-G01  (estensione test guard — FR-008)
    │       │
    └───────┴──── TASK-P01  (suite verde + uv build + lint)
                       │
                  TASK-P02  (CS-1..4 + invarianza trasversale)
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principali | Natura |
|----|-------------------------------|-----------------|--------|
| **US1** (manutentore non trova dir vuote, P1) | `git ls-files .../assets/copilot/` = zero righe; `Test-Path assets\copilot` = `False`. | TASK-R01 | MECCANICO |
| **US2** (nessun file di rimpiazzo, P2) | `git diff --name-only` non mostra file aggiunti sotto `assets/copilot/`; nessun README/marker. | TASK-R01 | MECCANICO |
| **US3** (generazione Copilot invariata, P1) | `test_assets_copilot_parity.py` verde; `test_install_rag_copilot_cli.py` verde; nessuna modifica a `surfaces.py`/`install_rag.py`. | TASK-P01 | MECCANICO |
| **US4** (build e packaging invariati, P1) | `uv build -p sertor` verde; `test_packaging.py` verde; `pyproject.toml` invariato. | TASK-P01 | MECCANICO |
| **US5** (suite e guardie esistenti verdi, P1) | `test_assets_copilot_guard.py` (guardie pre-esistenti) + `test_assets_copilot_parity.py` + suite root — zero nuovi fallimenti. | TASK-P01 | MECCANICO |
| **US6** (stub non riappare, P2) | `test_no_copilot_asset_directory` verde allo stato corretto; rossa se `assets/copilot/<x>/.gitkeep` viene ricreato (`asset_path("copilot").is_dir()` = `True`). | TASK-G01 | MECCANICO |

---

## Parallelizzazione consigliata

**Sprint unico** (la feature è quasi atomica — 4 file rimossi + 1 test esteso):

```
Passo 1: TASK-S01 (pre-flight) — obbligatorio primo
Passo 2: TASK-V01 (zero-consumatori grep) — obbligatorio secondo
Passo 3: TASK-R01 (rimozione .gitkeep)
         TASK-G01 (scrittura del test) ← scrivibile in [P] con R01 ma verificabile solo dopo
Passo 4: TASK-P01 (non-regressione totale + build)
Passo 5: TASK-P02 (CS check finale)
```

TASK-G01 può essere **scritto in parallelo** a TASK-R01 (sono file distinti), ma il suo verde
dipende dall'avvenuta rimozione (`TASK-R01`).

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E10-FEAT-023 — rimozione stub assets/copilot/

Fase SpecKit "tasks" completata per specs/081-stub-copilot.
6 task in 4 fasi:
  Fase 0 Setup (1 task):
    TASK-S01  uv sync --all-packages --extra dev; verifica 4 .gitkeep in scope +
              test_assets_copilot_guard.py; baseline suite verde.
  Fase 1 US1/US2/US3 P1 Must — Verifica + Rimozione stub (2 task, sequenziali):
    TASK-V01  Grep zero-consumatori su *.py (read_asset_text/iter_asset_dir/asset_path
              con root "copilot/") — atteso zero match; bloccante per TASK-R01.
    TASK-R01  git rm dei 4 .gitkeep:
                packages/sertor/src/sertor_installer/assets/copilot/agents/.gitkeep
                packages/sertor/src/sertor_installer/assets/copilot/hooks/.gitkeep
                packages/sertor/src/sertor_installer/assets/copilot/instructions/.gitkeep
                packages/sertor/src/sertor_installer/assets/copilot/prompts/.gitkeep
              Nessun file di rimpiazzo (Opzione A); verifica git ls-files zero righe.
  Fase 2 US6 P2 Should — Guardia anti-ricomparsa (1 task):
    TASK-G01  Estensione packages/sertor/tests/test_assets_copilot_guard.py:
              +test_no_copilot_asset_directory (assert not asset_path("copilot").is_dir())
              Contratto esatto da contracts/guard-anti-reappearance.md.
  Fase 3 Polish (2 task):
    TASK-P01  Suite verdi (guard+parity+install_copilot_cli+root), uv build -p sertor,
              test_packaging.py (integration), lint ruff, pyproject.toml invariato.
    TASK-P02  CS-1..4 + invarianza trasversale; segnala FEAT-024/025.

Natura: SOTTRATTIVO / igiene host-facing. ZERO codice runtime di core. sertor_core INVARIATO.
install_rag.py INVARIATO. pyproject.toml INVARIATO. Zero nuovi ArtifactKind/WriteStrategy/seam.
Artefatti toccati:
  - 4 file .gitkeep RIMOSSI (assets/copilot/{agents,hooks,instructions,prompts}/.gitkeep)
  - 1 file di test ESTESO (test_assets_copilot_guard.py: +test_no_copilot_asset_directory)
Copertura: FR-001..008, RNF-1..4, CS-1..4, US1..6.
Constitution CHECK: PASS 12/12 + missione (pre e post-design, plan.md §Constitution Check).
Nessun hook SpecKit eseguito (script assenti nel repo); nessuna operazione git.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/081-stub-copilot/tasks.md` (questo file, nuovo)
