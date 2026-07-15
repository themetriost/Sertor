# Requisiti — Fix cattura memoria: encoding path + fail-loud su source assente (E4-FEAT-011)

<!-- Deriva da: E4-FEAT-011 (bug), fonte handoff Nunzio `memory-archive-silenzioso-path-con-spazi.md`
     (2026-07-09), verificato sul codice + validato empiricamente il 2026-07-14/15. Bug MUST. -->

## 1. Contesto e problema (perché)

La cattura della memoria conversazioni (`memory archive`, adapter `claude-code`) **archivia 0 sessioni
in silenzio** sui progetti il cui percorso contiene caratteri non-alfanumerici che Claude Code collassa
ma `encode_project_path` no. Due difetti indipendenti:

1. **Encoding incompleto.** `encode_project_path` (`adapters/capture/claude_code.py`) sostituisce solo
   `:`/`\`/`/` con `-`. Claude Code, quando nomina la cartella in `~/.claude/projects`, collassa **ogni
   carattere non-alfanumerico** in `-` — **inclusi spazi e punti**. **Validato empiricamente** su 15
   cartelle reali della macchina, es.:
   - `…\Nunzio Summaries` → `…-Nunzio-Summaries` (spazio → `-`)
   - `…\Sinthari\.claude\…` → `…-Sinthari--claude-…` (punto → `-`, dà `--`)
   Con path che contiene spazi/punti la cartella calcolata **non combacia** con quella reale → source
   assente → 0 sessioni. **Impatto misurato (handoff):** 3/13 progetti (VM-WorkingFolder perde 22 sessioni).
   Windows: path con spazi/punti = norma.
2. **Fallimento silenzioso.** Con `SERTOR_MEMORY=true` e source assente, l'esito è
   `op=memory_capture_source_absent … archived=0 skipped=0 errors=0`, exit 0, nessun warning visibile.
   L'utente crede di avere un archivio e non ce l'ha; se ne accorge settimane dopo (search vuota).
   Contraddice il *Fail Loud, Fix the Cause* (Principio XII) che Sertor **prescrive agli ospiti**.

**Adapter `copilot-cli`: NON affetto** — non usa `encode_project_path`, associa le sessioni per
`cwd`/`gitRoot` con path-matching reale (`os.path.normpath`, gestisce spazi/punti). Verificato.

## 2. Obiettivi e criteri di successo

- **O1 (encoding corretto).** `encode_project_path` riproduce **esattamente** il naming di Claude Code su
  tutti i campioni reali → i progetti con spazi/punti trovano le loro sessioni.
- **O2 (fail-loud).** Con memoria abilitata e source assente, l'esito è **visibile** (warning nel report),
  non un `archived=0 errors=0` muto.

**Criteri di successo:**
- **SC-1:** `encode_project_path(p)` == nome cartella reale di Claude Code per **tutti** i 15 path reali
  campionati (drive-letter `C--`, spazi, punti, trattini già presenti preservati come `-`, UNC).
- **SC-2:** eseguendo `memory archive` su un progetto con spazio nel path (source ora combaciante), le
  sessioni vengono archiviate (non più 0).
- **SC-3:** con `SERTOR_MEMORY=true` e source dir assente, `memory archive` emette un **warning visibile**
  (report umano + `--json`) che nomina il path e la causa probabile; **non** un semplice `archived=0`.
- **SC-4:** l'esito resta **fail-safe** (exit 0 — non si rompe l'hook `memory-capture` SessionEnd); il
  fail-loud è un *warning visibile*, non un exit non-zero.
- **SC-5:** il servizio resta **host-agnostico** (nessun `if adapter is ClaudeCode`); il segnale
  source-assente passa per un metodo del **port** `TranscriptCaptureAdapter`.
- **SC-6:** modifiche confinate a `sertor-core`; i due adapter, il port, il servizio archiver, il report,
  il formatter CLI.

## 3. Ambito

### In ambito
- Fix `encode_project_path` (`claude_code.py`) → `re.sub(r"[^A-Za-z0-9]", "-", path)`.
- Nuovo metodo del port `TranscriptCaptureAdapter.source_available() -> bool`; implementato in **entrambi**
  gli adapter (claude-code + copilot-cli), banale (`self._dir.is_dir()`).
- `ArchiveRunReport.source_absent: bool`; impostato in `MemoryArchiveService.archive_all()` (agnostico).
- `format_archive_report` (CLI `output.py`): warning visibile quando `source_absent`.
- Test: encoding sui 15 campioni + regression (UNC/dots/dashes) · source-available/absent · report warning.

### Fuori ambito
- L'adapter `copilot-cli` (non affetto dall'encoding; guadagna solo `source_available()`).
- Il 🐛 **auto-capture E4 distinto** (l'hook non popolava l'archivio) — separato, resta aperto.
- Cambiare l'exit-code o il contratto fail-safe dell'hook.

## 4. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous).** `encode_project_path` shall map **every non-alphanumeric character** of the
  path to `-`, reproducing Claude Code's project-folder naming (`[^A-Za-z0-9] → -`).
- **REQ-002 (Event-driven).** When `memory archive` runs with memory enabled and the adapter's session
  source is **absent**, the system shall emit a **visible warning** (human + `--json`) naming the source
  path and the probable cause, instead of a silent `archived=0`.
- **REQ-003 (Unwanted).** If the source is absent, the run shall still **exit 0** (fail-safe for the
  SessionEnd hook); the fail-loud is a visible warning, not a non-zero exit.
- **REQ-004 (Ubiquitous).** The archiving service shall remain **host-agnostic**: the source-absent
  signal comes from the `TranscriptCaptureAdapter` port (`source_available()`), never from an adapter
  identity check.
- **REQ-005 (Ubiquitous).** The change shall be confined to `sertor-core`; the CLI's fail-safe contract
  is unchanged.

## 5. Vincoli, assunzioni, dipendenze

- **Assunzione (encoding):** Claude Code collassa `[^A-Za-z0-9] → -` — **validato** su 15 campioni reali;
  il caso `_` (underscore) non è tra i campioni ma la regex lo tratta come gli altri (safe generalizzazione).
- **Vincolo (port additivo):** aggiungere `source_available()` al Protocol è additivo; i mock in
  `tests/fixtures` vanno aggiornati.
- **Vincolo (fail-safe):** l'hook `memory-capture` SessionEnd deve continuare a exit-0 (REQ-003).

## 6. Prioritizzazione (MoSCoW)

- **Must:** REQ-001 (fix encoding — è il bug), REQ-002, REQ-004.
- **Should:** REQ-003, REQ-005.

---

**Nota:** decomposizione lean di un bug Must già diagnosticato (handoff + verifica empirica). Prossimo:
implement (encoding + port + service + report + formatter + test) → PR.
