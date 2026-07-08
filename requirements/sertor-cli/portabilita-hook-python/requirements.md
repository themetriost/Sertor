# Requisiti — Portabilità POSIX degli hook (hook portabili)

<!-- Deriva da: E2-FEAT-010 (parte "hook Linux"), promossa da Could a Must dall'assessment SWOT
     2026-07-02 come A-09 (P1). -->

## 1. Contesto e problema (perché)

`sertor install rag`/`wiki` distribuiscono **8 hook host-facing** che si auto-eseguono agli eventi
dell'agente (SessionStart/SessionEnd/PreToolUse/Stop). Oggi sono **PowerShell** (`.ps1`), wirati
`"shell": "powershell"` (Claude) / `pwsh -File` (Copilot). Su **macOS/Linux senza PowerShell Core
(`pwsh`)** questi hook sono **non-operativi**: E10-FEAT-018 li **rileva** e emette una nota azionabile
(«installa `pwsh`»), ma **non offre un'alternativa funzionante** → su un ospite POSIX tipico
(sviluppatore mac/Linux senza `pwsh`) le capacità di freschezza RAG, cattura memoria, avviso versione e
rituale wiki **non scattano**. È una violazione pratica del **Principio X** (host-agnostico): la
capacità è installata ma inerte su un intero OS-family.

Gli 8 hook e la loro funzione (ancoraggio verificato, `packages/sertor/src/sertor_installer/assets/`):
| Hook | Evento | Funzione |
|------|--------|----------|
| `memory-capture` | SessionEnd | legge i transcript (`events.jsonl`), invoca il vehicle di cattura |
| `rag-freshness` | SessionEnd | avvia un **worker detached** che re-indicizza + `doctor` → `.sertor/.rag-health.json` |
| `rag-freshness-start` | SessionStart | legge lo stato, induce la correzione se `degraded` |
| `sertor-rag-usage-check` | PreToolUse | promemoria MCP-first non-bloccante (fail-open) |
| `version-check` | SessionEnd | GET HTTP di `/VERSION` (cache ~24h) → `.sertor/.version-check.json` |
| `version-check-start` | SessionStart | avvisa se la versione installata è indietro |
| `wiki-pending-check` | Stop/SessionEnd | rileva lavoro non ancora registrato (mtime) |
| `wiki-session-start` | SessionStart | carica il contesto wiki a inizio sessione |

**Direzione decisa (utente, 2026-07-08):** **una sola implementazione portabile** degli hook che gira
sul runtime già installato (`.sertor/`), invece di una seconda copia per shell — così si elimina alla
radice la dipendenza da `pwsh`/`bash` e il rischio di **drift** tra due implementazioni. Tutte le
funzioni degli hook sono realizzabili con strumenti portabili senza dipendenze nuove.

## 2. Obiettivi e criteri di successo

- **O1 (portabilità reale).** Gli 8 hook sono **operativi** su **Windows, macOS e Linux** senza
  richiedere `pwsh`.
- **O2 (parità funzionale).** Ogni hook portabile produce **esattamente** gli stessi effetti osservabili
  del `.ps1` che sostituisce (stesso evento, stessi file di stato, stesso contratto di output
  per-assistente, stessa semantica fail-safe).
- **O3 (nessuna regressione Windows).** Sugli ospiti Windows (dove i `.ps1` funzionavano) gli hook
  restano operativi.
- **O4 (una implementazione).** Nessuna duplicazione per-OS: un solo corpo per hook (host-agnostico, X).

**Criteri di successo (misurabili, tech-agnostici):**
- **SC-1:** su un ospite macOS/Linux **senza `pwsh`**, ognuno degli 8 hook al suo evento **scatta e
  completa** l'effetto atteso (verificabile: file di stato scritto, avviso emesso, re-index avviato).
- **SC-2:** per ogni hook, l'**output per-assistente** (Claude: `additionalContext`/`decision`;
  Copilot: formato nativo) è **identico** a quello del `.ps1` corrispondente, su tutti gli OS.
- **SC-3:** l'esito è **fail-safe**: ogni hook esce **sempre `0`**, non blocca la sessione, e in caso di
  errore scrive il breadcrumb `.sertor/.last-hook-error` **senza segreti** (parità con E10-FEAT-019).
- **SC-4:** **0** dipendenze runtime nuove introdotte dagli hook.
- **SC-5:** `sertor-core` **invariato**; la logica hook vive negli **asset dell'installer**, non nel core.
- **SC-6:** la **nota** «installa `pwsh`» (E10-FEAT-018) non è più necessaria per l'operatività degli hook
  (aggiornata o rimossa di conseguenza).

## 3. Stakeholder e attori

- **Ospite macOS/Linux senza `pwsh`** — oggi penalizzato; riceve hook funzionanti.
- **Ospite Windows** — non deve subire regressioni.
- **Manutentore Sertor** — una sola implementazione da mantenere (meno drift).
- **CI** — deve poter verificare la parità cross-OS.

## 4. Ambito

### In ambito
- Riscrivere gli **8 hook** in forma **portabile** (una implementazione) e cablarli in modo
  OS-indipendente in `settings.json` (Claude) e nel wiring Copilot.
- Preservare **parità funzionale** e **contratto di output per-assistente** di ciascun hook.
- Aggiornare/rimuovere la nota di indisponibilità `pwsh` (E10-FEAT-018) resa obsoleta.
- Verifica di parità/portabilità (test).

### Fuori ambito
- Cambiare **cosa** fanno gli hook (nuove capacità): è una **riscrittura iso-funzionale**, non un
  ampliamento.
- Modifiche a `sertor-core`.
- Il layout/gli asset **non-hook** (skill, agenti, blocchi `CLAUDE.md`).
- La disciplina di versioning `/VERSION` (E2-FEAT-014, separata).

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous).** The installer-distributed hooks shall be **operational on Windows, macOS and
  Linux** without requiring PowerShell Core (`pwsh`) on the host.
- **REQ-002 (Ubiquitous).** For each of the 8 hooks, the portable implementation shall produce the
  **same observable effects** as the `.ps1` it replaces: same triggering event, same state files
  (`.sertor/.rag-health.json`, `.sertor/.version-check.json`), same side-effects (re-index launched,
  transcript captured, context loaded, reminder emitted).
- **REQ-003 (Event-driven).** When a hook runs, it shall emit the **per-assistant output contract**
  unchanged — Claude (`additionalContext` / `decision` on the correct stream) and Copilot (its native
  format) — so the assistant behaves identically to today.
- **REQ-004 (Ubiquitous).** Each hook shall be **fail-safe**: it shall exit `0` regardless of internal
  failure, shall never block the session, and the `PreToolUse` reminder shall stay **non-blocking
  (fail-open)**.
- **REQ-005 (Unwanted behaviour).** If a hook's standard input is redirected/absent, then the hook shall
  **not hang** waiting for input (parity with the E10-FEAT-014 stdin guard).
- **REQ-006 (Event-driven).** When `rag-freshness` runs at SessionEnd, it shall launch the re-index work
  in a **detached/background** manner that does **not block** the session close, on **all** operating
  systems.
- **REQ-007 (Unwanted behaviour).** If a hook errors, then it shall write the breadcrumb
  `.sertor/.last-hook-error` (schema `hook.error/1`) **without any secret** and still exit `0` (parity
  with E10-FEAT-019).
- **REQ-008 (Ubiquitous).** The hooks shall introduce **no new runtime dependency** beyond what the
  installed runtime already provides.
- **REQ-009 (Ubiquitous).** The change shall leave `sertor-core` **unmodified**; the hook logic shall
  live in the **installer's distributed assets**, not in the core library.
- **REQ-010 (Event-driven).** When the installer wires the hooks, the wiring shall be **OS-independent**
  (no dependency on a Windows-only shell such as `"shell": "powershell"`), for both Claude and Copilot.
- **REQ-011 (Unwanted behaviour).** If the installed runtime needed to run a hook is **absent** (e.g. a
  wiki-only install without the RAG runtime), then the affected hook shall **degrade fail-safe** (no
  error, no block, an inspectable breadcrumb), never crash the session.
- **REQ-012 (Event-driven).** When the portable hooks are in place, the installer shall **no longer
  require** the `pwsh`-unavailability note (E10-FEAT-018) as a precondition for hook operability; the
  note is updated or removed accordingly.
- **REQ-013 (Ubiquitous).** A **verification** shall exist that demonstrates functional parity between
  each portable hook and its prior behaviour (per-assistant output + state effects), runnable in CI.

## 6. Requisiti non funzionali

- **NFR-1 (portabilità):** una sola implementazione host-agnostica per hook (nessuna copia per-OS) —
  Principio X.
- **NFR-2 (osservabilità):** ogni hook resta ispezionabile (breadcrumb fail-loud su errore) — Principio
  XII, parità E10-FEAT-019.
- **NFR-3 (performance):** l'hook `PreToolUse` (scatta a **ogni** Bash/Write/Edit) deve avere overhead
  trascurabile e non bloccare mai; gli hook di sessione non devono ritardare percettibilmente
  start/close.
- **NFR-4 (manutenibilità):** ridurre la superficie di manutenzione a **un** corpo per hook (no drift).
- **NFR-5 (install≠run):** il deposito/wiring degli hook non avvia da solo ingestioni costose (Principio
  VI); solo l'evento a runtime li esegue.

## 7. Vincoli, assunzioni e dipendenze

- **Assunzione (runtime disponibile):** il runtime `.sertor/` installato fornisce l'interprete su cui gli
  hook portabili girano, su ogni OS (verificato: `sertor install rag` crea `.sertor/.venv`).
- **Dipendenza:** parità con i contratti host-facing esistenti — E10-FEAT-011 (freschezza RAG),
  E2-FEAT-013 (version-check), E4 (memoria), rituale wiki — che i nuovi hook devono riprodurre.
- **Vincolo (no-regressione Windows):** gli hook portabili devono funzionare **anche** su Windows; la
  migrazione dai `.ps1` non deve lasciare gli ospiti Windows scoperti in nessun momento.
- **Vincolo (D↔N):** gli hook restano **deterministici** (nessun LLM nel corpo); il confine
  segnale-vs-azione (l'hook segnala, l'agente/utente agisce) è invariato.
- **Assunzione (byte-copy dogfood):** gli hook portabili viaggiano come asset byte-copiati → guardie
  di sync dogfood↔bundle da aggiornare di conseguenza.

## 8. Rischi

- **R-1 (parità imperfetta):** un dettaglio del `.ps1` (formato output, timing del detach, encoding) non
  riprodotto → l'assistente si comporta diversamente. *Mitigazione:* REQ-002/003 + verifica di parità
  (REQ-013) prima di ritirare i `.ps1`.
- **R-2 (regressione Windows):** rimuovere i `.ps1` prima che la parità sia provata su Windows.
  *Mitigazione:* strategia di migrazione (coesistenza vs sostituzione) da fissare al plan; ritiro dei
  `.ps1` **solo** a parità dimostrata.
- **R-3 (detach cross-OS):** il worker background del re-index si comporta diversamente per OS (zombie,
  blocco). *Mitigazione:* REQ-006 con verifica per-OS.
- **R-4 (runtime assente):** un hook wirato ma senza runtime (wiki-only) crasha. *Mitigazione:* REQ-011
  (degrado fail-safe).

## 9. Prioritizzazione (MoSCoW)

- **Must:** REQ-001, REQ-002, REQ-003, REQ-004, REQ-009, REQ-010, REQ-013.
- **Should:** REQ-005, REQ-006, REQ-007, REQ-008, REQ-011, REQ-012, NFR-1..4.
- **Could:** ritiro completo dei `.ps1` (se la strategia di migrazione lo prevede una volta provata la
  parità) — vedi DA-1.

## 10. Domande aperte

- **DA-1 [design→plan]:** strategia di migrazione — **sostituire** i `.ps1` con i portabili ovunque
  subito, oppure **coesistenza** (portabile su POSIX, `.ps1` su Windows) finché la parità Windows è
  provata, poi ritiro? *(Il target è una implementazione sola — NFR-1/O4 — ma il "quando" ritirare i
  `.ps1` è una scelta di rischio.)*
- **DA-2 [plan]:** meccanismo di **invocazione** portabile dal wiring (l'esatto comando che
  `settings.json`/il wiring Copilot lancia) — è "come", si fissa al plan; qui basta REQ-010 (OS-indip.).
- **DA-3 [scope]:** i due hook **wiki** (`wiki-pending-check`, `wiki-session-start`) sono depositati da
  `sertor install wiki` che **potrebbe non creare** il runtime `.sertor/.venv` (install wiki-only) →
  serve confermare l'interprete disponibile per loro, o la loro degradazione (REQ-011). Da chiarire al
  plan.
- **DA-4 [verifica]:** la verifica di parità (REQ-013) è offline (asserzioni su output/stato con input
  simulati) o richiede un ospite reale per-OS (CI matrix)? *Raccomandazione:* offline per il grosso +
  smoke cross-OS in CI dove fattibile.

---

**Commit proposto:** `docs(requirements): E2 A-09 — portabilità hook (hook portabili, promuove FEAT-010)`
