# Research — Portabilità OS degli hook (guardia `pwsh` + gap dichiarato) + onestà surface inerti (E10-FEAT-018)

**Branch**: `078-portabilita-os-hook` · **Data**: 2026-06-30 · **Fase**: 0 (research)

> Nota di processo: `.specify/scripts/powershell/setup-plan.ps1` e `.claude/skills/speckit-plan/SKILL.md`
> **assenti** nel repo (come per 074–077) → parametri ricavati per convenzione dal branch; nessun hook
> eseguito. **MCP `sertor-rag` interrogato** in apertura (`search_code` su `InstallReport.notes` e sul
> wiring hook per-assistente) — **nessun errore tool**. I file indicati dal RAG sono stati letti interi
> con `Read` (RAG trova, Read trasporta).

## Sintesi del problema

Due classi di disonestà negli asset distribuiti da `sertor install`:
1. **Fallimento silenzioso su non-Windows.** Gli hook sono `.ps1`; il wiring Claude li invoca con
   `"shell": "powershell"` (verificato: `assets/rag/settings.rag-freshness.json:8`,
   `assets/settings.hooks.json:8`, `assets/rag/settings.rag-usage.json`). `powershell` (Windows
   PowerShell 5.1) **non esiste** su macOS/Linux → l'hook non parte, nessun messaggio, exit 0. Il wiring
   Copilot usa `pwsh -File` (`_PWSH = "pwsh -File"`, `install_rag.py:123`, `install_wiki.py:104`):
   portabile **se** `pwsh` (PowerShell Core) è in PATH, altrimenti fallisce silenzioso.
2. **Claim impliciti su surface inerti (Copilot CLI).** `memory-capture` è wired/depositato su Copilot
   ma funzionalmente inerte di default (`SERTOR_MEMORY=false`; e con memoria attiva l'adapter di default
   `claude-code` legge sessioni Claude, non Copilot). L'adapter Copilot **esiste** (FEAT-008 memorie,
   2026-06-22) ma l'installer non distribuisce `SERTOR_MEMORY_ADAPTER=copilot-cli` (→ FEAT-009 memorie).

Strategia **FISSATA** (non riaprire): guardia `pwsh` + gap dichiarato, hook **PowerShell-only** (nessun
gemello `.sh`). Onestà sui surface inerti via il meccanismo **esistente** `InstallReport.notes`.

## Ancoraggio verificato (MCP + Read)

- **`InstallReport.notes` + `.note()`** esistono e sono testati: `sertor-install-kit/report.py:44,74`.
  `render_human` emette righe `Note: …` (`:101-102`); `render_json` include `notes[]` **solo se
  non-vuoto** (`:126-127`). Schema `install.report/1` **invariato** (additivo). Oggi `notes` è
  inutilizzato in produzione (solo i test `test_cli_report_has_no_vscode_gap`/
  `test_claude_report_has_no_gap_note` asseriscono `[]`). **FEAT-018 è la prima emissione reale.**
- **Punto di emissione (seam):** la `InstallReport` è prodotta da `_kit_execute_plan` dentro
  `execute_rag_plan` (`install_rag.py:735-749`) e `execute_plan` wiki (`install_wiki.py:380-396`).
  Entrambe **ritornano il report**: il punto naturale per aggiungere le note è **dopo** il ritorno
  dell'executor, **dentro** queste due funzioni (la CLI `_cmd_install_rag`/`_cmd_install_wiki` resta
  thin e si limita a `render_*`).
- **Hook surfaces derivabili dal piano:** i target hook sono gli `Artifact` con `target_rel.endswith(".ps1")`
  (claude `.claude/hooks/*.ps1`, copilot `.github/hooks/*.ps1`). Nessuna lista hardcoded: la guardia
  legge i `.ps1` dal piano (dichiarativo).
- **OS/pwsh detection già in casa:** `shutil.which` è già usato dal kit (`command_runner.py:46`,
  `SubprocessRunner.is_available`). `os.name`/`shutil.which("pwsh")` = stdlib, deterministici,
  **mockabili** (la CI gira su Windows → i test del ramo non-Windows simulano l'OS).
- **Convenzione breadcrumb FEAT-019** (`Write-HookBreadcrumb` / `.sertor/.last-hook-error`) presente in
  `version-check.ps1`/`memory-capture.ps1`/`rag-freshness.ps1`: è il segnale **runtime** «lo script gira
  ma l'operazione interna fallisce». FEAT-018 è complementare: copre **install-time** «lo script non può
  nemmeno partire perché manca `pwsh`». La breadcrumb runtime **non** è riusata qui (a runtime, senza
  `pwsh`, lo script non parte affatto → niente da scrivere; il punto d'intervento è l'install-time).
- **Guardia sync** `tests/unit/test_assets_sync.py` copre `assets/claude/**` ↔ `.claude/`. FEAT-018
  **non** tocca alcun asset (`.ps1`/JSON/claude): le note vivono in **codice Python** (kit + install_rag)
  e i doc utente non sono sotto `.claude/`. La guardia resta verde **per costruzione** (nessun byte di
  asset cambia). Nessuna nuova guardia di sync necessaria (≠ FEAT-018 di altre epiche).

## Decisioni di design (le 2 forche residue + il quesito sul wiring)

### D-1 (DA-D-r1) — Dove vive la logica del check `pwsh`: **helper condiviso nel `sertor-install-kit`**

**Decisione.** Nuovo modulo puro nel kit, `host_env.py`, con:
- `is_windows() -> bool` (`os.name == "nt"`);
- `pwsh_available() -> bool` (`shutil.which("pwsh") is not None`);
- `pwsh_unavailability_note(hook_surfaces: Sequence[str]) -> str` (builder **puro**: elenca i surface +
  URL d'installazione PowerShell Core + la frase «installati ma non-operativi»);
- `maybe_note_pwsh(report: InstallReport, hook_surfaces: Sequence[str]) -> None` (gating: **non-Windows
  AND `pwsh` assente AND ci sono hook** → `report.note(pwsh_unavailability_note(...))`; altrimenti no-op).

I consumatori (`execute_rag_plan`, wiki `execute_plan`) derivano `hook_surfaces` dal piano
(`[a.target_rel for a in plan if a.target_rel.endswith(".ps1")]`) e chiamano `maybe_note_pwsh`.

**Razionale (vs duplicazione nei singoli install-builder):**
1. **DRY (Principio III):** due consumatori **oggi** (rag + wiki) condividono la stessa logica OS/pwsh,
   lo stesso URL, la stessa forma di nota. Duplicarla = due copie da tenere allineate.
2. **Riuso futuro `sertor-flow`:** anche la governance distribuisce script `.ps1` (hook wiki riusati);
   il kit è già la sua unica dipendenza condivisa (non dipende da `sertor-core`). L'helper nel kit è
   disponibile a tutti i bundle senza accoppiamenti nuovi.
3. **Seam di mock unico:** i test patchano `host_env.is_windows`/`host_env.pwsh_available` una sola volta
   → deterministico su CI Windows (R-6).
4. **Principio XI/X:** è codice **installer** stdlib (`os`/`shutil`), **zero** import di `sertor_core`,
   nessun LLM. Il «quali surface sono hook» resta **dichiarativo** (derivato dal piano), non hardcoded.

La **nota `memory-capture`** (Copilot, rag-specifica) **NON** va nel kit: referenzia `SERTOR_MEMORY`/
`SERTOR_MEMORY_ADAPTER` e l'epica memorie → resta in `install_rag.py` (single consumer, YAGNI III).

### D-2 (DA-D-r2) — Nota `memory-capture`: **sempre su install rag Copilot CLI** (indipendente da `SERTOR_MEMORY`)

**Decisione.** Emessa **sempre** su `sertor install rag --assistant copilot-cli`, a prescindere dal
valore runtime di `SERTOR_MEMORY`.

**Razionale.** (a) È una nota **anticipatoria**: chi abiliterà la memoria in futuro deve già sapere ora
che su Copilot serve `SERTOR_MEMORY_ADAPTER=copilot-cli`; gating su `SERTOR_MEMORY=true` la
**nasconderebbe** proprio agli utenti nello stato di default (la stragrande maggioranza). (b) L'installer
scrive il template `.env` con `SERTOR_MEMORY=false` di default → all'install-time il valore «vero» di
runtime non è un segnale affidabile (l'utente lo cambierà dopo). (c) Coerente con la raccomandazione
esplicita della spec (US5/edge case) e Principio XII (rendere il gap **visibile presto**). La nota
**cross-referenzia** la capacità pianificata (FEAT-009 memoria-conversazioni — distribuzione del valore
adapter nel template `.env`) così è chiaro che (i) un fix è pianificato, (ii) l'utente può optare
manualmente nel frattempo. **R-4 (staleness):** la nota cita la FEAT successiva → al merge di quella, la
nota va rimossa/condizionata (tracciabile).

**Tabella capability in `packages/sertor/docs/install.md`:** **SÌ, aggiornarla.** FR-012 richiede già la
distinzione «operativo out-of-the-box vs richiede config» per target in `docs/install.md`; per coerenza
DoD «setup→doc utente» la **mappa capability** in `packages/sertor/docs/install.md` (la tabella
user-facing dei surface) riceve una **colonna/nota di operatività** per target (Claude su Windows ·
Copilot CLI), che annota: hook richiedono `pwsh` su mac/Linux; `memory-capture` su Copilot richiede
config adapter. Una sezione testuale **e** la nota in tabella (la tabella è il colpo d'occhio).

### D-3 (quesito del finding) — La guardia **rileva e segnala**, **NON** riscrive il wiring

Il finding chiede se la guardia debba anche **allineare il comando per-OS** (es. `pwsh` su non-Windows)
o solo rilevare+segnalare. **Decisione: solo rilevare+segnalare; nessuna modifica al wiring** (né
Claude `"shell": "powershell"`, né Copilot `pwsh -File`).

**Razionale:**
- **Strategia FISSATA** = «detect + declare», non «rewrite wiring».
- **Non-regressione Windows (NFR-5/US3).** Cambiare `"shell": "powershell"` → `"shell": "pwsh"`
  impatterebbe **anche Windows**: gli utenti con la sola Windows PowerShell 5.1 (`powershell`, senza
  PowerShell Core `pwsh`) — il **target primario** — si troverebbero gli hook rotti. Il wiring attuale è
  Windows-first **per scelta corretta**.
- **Copilot già portabile.** `pwsh -File` è già l'interprete portabile; l'unico gap è la *disponibilità*
  di `pwsh`, coperta dalla nota. Nessuna riscrittura serve lì.

**Finding/limite dichiarato (Principio XII — onestà, non invenzione).** C'è un'**incertezza tecnica
aperta** su come Claude Code risolve `"shell": "powershell"` su non-Windows: se **non** mappa a `pwsh`,
allora su Claude/non-Windows **installare `pwsh` da solo potrebbe non bastare** a far girare gli hook
(servirebbe un wiring portabile, es. `pwsh -File`, che però impatterebbe Windows). Non lo si **inventa**
(regola «leggi la doc del tool, non inferire»): si tiene la nota **stretta** sul fatto verificabile
(«`pwsh` non trovato»), si dichiara il limite nei doc utente (la sezione operatività-per-target distingue
ciò che è pienamente operativo da ciò che richiede config/può non bastare), e si **promuove** «wiring
hook Claude portabile su non-Windows» a **candidata di follow-up** (verificare la semantica `shell` di
Claude Code, poi decidere). Così US2/FR-004 restano **fedeli e onesti**: l'assenza della nota
«`pwsh` non disponibile» **non** è un claim di «hook pienamente operativi» — è solo «`pwsh` c'è»; il
quadro completo di operatività vive nei doc (FR-010/012). La nota è **narrow-scope by design**.

## Forche già risolte a monte (non riaperte)

- **DA-1 strategia OS** (guardia + gap, no `.sh`) — decisione utente, §Fuori ambito spec.
- **DA-2 onestà surface inerti** via `InstallReport.notes` — decisione utente.
- **DA-3 `memory-capture` Copilot** — verifica codice: adapter esiste, manca distribuzione → nota.
- **DA-4 SessionStart Copilot** — verifica codice: `type:"prompt"` funzionale, **non** inerte → E10-FEAT-008.

## Estensioni / debiti promossi (casa durevole, non sepolti in `specs/`)

- **Distribuzione `SERTOR_MEMORY_ADAPTER=copilot-cli` nel template `.env`** → **FEAT-009 epica
  memoria-conversazioni** (già tracciata). Qui solo la nota.
- **Visibilità SessionStart Copilot** → **E10-FEAT-008** (cross-ref, non assorbito).
- **Wiring hook Claude portabile su non-Windows** (incertezza D-3) → **candidata follow-up** epica
  debito-tecnico (verificare semantica `shell` Claude Code; se serve, design dedicato — non in questa
  scope fissata). Da annotare nella roadmap → *Nuove funzionalità da discutere*.
- **Nota `pwsh`/`memory-capture` anche sul percorso `upgrade`** (oggi `execute_rag_lifecycle`/
  `execute_wiki_lifecycle`, distinto da `execute_*_plan`): la nota è un advisory **install-time** e tutti
  gli US la inquadrano sull'install → fuori dalla scope immediata; estensione triviale futura (gli stessi
  builder sono riusati). Non una FEAT nuova.
- **Pulizia stile/altitude body hook + blocchi `CLAUDE.md`** → **FEAT-021/FEAT-022**.
- **Gemello `.sh` + guardia `pwsh` runtime** → **Won't** (decisione utente).

## Costante di rimediazione

URL d'installazione PowerShell Core (ufficiale, version-agnostico):
`https://learn.microsoft.com/powershell/scripting/install/installing-powershell`.
