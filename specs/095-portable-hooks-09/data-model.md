# Data model — portabilità hook (Phase 1)

Nessuna entità di dominio in `sertor-core`. Il «modello» è l'inventario degli 8 hook + il loro contratto
invariante (evento, effetti di stato, output per-assistente) che i portabili devono riprodurre.

## Inventario hook (8) — invarianti di parità

| Hook | Origine | Evento | Effetto di stato / side-effect | Runtime RAG? |
|------|---------|--------|--------------------------------|--------------|
| `memory-capture` | install rag | SessionEnd | legge transcript, invoca cattura via vehicle | sì (vehicle) |
| `rag-freshness` | install rag | SessionEnd | worker **detached** → re-index + `doctor` → `.sertor/.rag-health.json` | sì |
| `rag-freshness-start` | install rag | SessionStart | legge `.rag-health.json`, induce fix se `degraded` | no (solo lettura) |
| `sertor-rag-usage-check` | install rag | PreToolUse | promemoria MCP-first **fail-open** | no |
| `version-check` | install rag | SessionEnd | GET `/VERSION` (cache ~24h) → `.sertor/.version-check.json` | no (rete) |
| `version-check-start` | install rag | SessionStart | legge stato, avvisa se behind | no |
| `wiki-pending-check` | install wiki | Stop/SessionEnd | rileva lavoro non registrato (mtime) | **no** (wiki-only) |
| `wiki-session-start` | install wiki | SessionStart | carica contesto wiki | **no** (wiki-only) |

## Entità di riferimento

- **Hook portabile**: script Python (`<name>.py`) invocato via `uv run --no-project python`; parametrico
  sull'assistente (`--assistant claude|copilot`). *Invariante:* iso-funzionale al `.ps1` omonimo.
- **Contratto di output per-assistente**: Claude → JSON su stdout (`additionalContext` per SessionStart;
  `decision:allow` non-bloccante per Stop; niente payload deny per PreToolUse fail-open) · Copilot → formato
  nativo equivalente. *Invariante:* preservato byte-per-byte.
- **File di stato** (`.sertor/`): `.rag-health.json` (`rag.health/1`), `.version-check.json`,
  `.last-hook-error` (`hook.error/1`, secret-free). *Invariante:* stessi path/schema.
- **Wiring**: voce `settings.json` (Claude) / entry Copilot che invoca l'hook. *Cambio:* da
  `"shell":"powershell"`+`.ps1` a `uv run --no-project python`+`.py`, OS-indipendente.

## Invarianti globali (i «test» del modello)

- **INV-1 (parità output):** per ogni hook e assistente, stdout del portabile == contratto atteso (SC-002).
- **INV-2 (parità stato):** i file `.sertor/*` scritti hanno path+schema invariati (SC-001).
- **INV-3 (fail-safe):** ogni hook esce `0` anche su errore; breadcrumb secret-free; PreToolUse fail-open
  (SC-003).
- **INV-4 (portabilità):** ogni hook esegue su Windows/macOS/Linux senza `pwsh` (SC-001/005); smoke CI
  matrice verde.
- **INV-5 (single-impl):** 0 `.ps1` residui per gli 8 hook; 0 `"shell":"powershell"` nel loro wiring
  (SC-005).
- **INV-6 (core invariato):** `sertor-core` byte-invariato; 0 dip nuove (SC-004/006).
