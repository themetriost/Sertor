# Feature Spec: `rag-freshness` verdetto post-riparazione + auto-heal del lock stantio

**Branch**: `113-feat-034-freshness-postrepair-lock` · **Requisiti**: `../../requirements/debito-tecnico/feat-034-freshness-postrepair-lock/requirements.md` · **Epica**: `debito-tecnico` (E10-FEAT-034, fonde FEAT-035)

**Date**: 2026-07-20

## Cosa & perché

Due difetti nello **stesso** hook `rag-freshness` (SessionEnd, E10-FEAT-011) ne minano l'affidabilità.

**A (FEAT-034).** Il worker misura la salute con `doctor` e **scrive** `.sertor/.rag-health.json` **prima**
di ri-indicizzare. Il verdetto persistito è quindi **pre-riparazione**: il caso normale (indice stantio →
re-index lo ripara) persiste comunque `degraded`, e al SessionStart successivo l'agente riceve un allarme
per un problema già risolto. L'allarme «grida al lupo» → viene svalutato → il degrado **reale** passa
liscio. Piegato: `reason` tiene solo il primo warn → con più aree degradate ne dichiara una sola.

**B (FEAT-035).** Il worker gira detached; se muore durante il re-index lascia `.sertor/.index/.index.lock`
con un **PID morto**, e ogni `sertor-rag index` successivo fallisce con `IndexLockedError` finché non si
rimuove il lock **a mano** (osservato dal vivo 2026-07-17, PID 33516). Il lockfile registra già il PID:
basta verificarne la liveness, come l'auto-heal di Chroma/code-graph.

**Fusi** (decisione utente 2026-07-20): stesso hook, difetti complementari. A a valle di E10-FEAT-038
(`doctor` ancorato, consegnato): rimisurare con `doctor` ha senso solo se `doctor` è affidabile.

## Comportamento (l'esito osservabile)

**A — SessionEnd:**
- Il worker esegue **re-index → `doctor` → scrittura del verdetto** (in quest'ordine).
- Caso normale (stantio riparabile): dopo il re-index `doctor` è `pass` → stato `healthy` → **nessun**
  allarme al SessionStart.
- Re-index fallito o area ancora degradata dopo il re-index → stato `degraded` con `reason` che **elenca
  tutte** le aree degradate → allarme legittimo.
- Scrittura **atomica** (`os.replace`): un lettore non vede mai un file lacero.

**B — `index()`:**
- Lockfile con PID **morto** → `index()` reclama il lock e procede (nessun intervento manuale).
- Lockfile con PID **vivo** (o holder non confermabile morto) → `IndexLockedError` come oggi.
- Reclamo → **segnale osservabile** (`log_event` WARNING che nomina il PID morto).

## Criteri di accettazione
Vedi CS-1..CS-8 in requirements §2. In sintesi:
- **AC-1:** normale → `healthy` persistito (CS-1); degrado reale → `degraded` (CS-2).
- **AC-2:** `reason` elenca tutte le aree degradate (CS-3).
- **AC-3:** PID morto → lock reclamato + run procede (CS-4); PID vivo → `IndexLockedError` (CS-5).
- **AC-4:** reclamo emette un segnale osservabile (CS-6); liveness cross-OS senza perturbare il processo.
- **AC-5:** scrittura stato atomica, mai lacera (CS-7).
- **AC-6:** un ospite che fa `upgrade rag` riceve l'ordine nuovo — guard sull'esito d'upgrade (CS-8);
  byte-parity bundle↔dogfood.

## Out of scope
- Rimisura nel SessionStart (rompe D↔N: lo start-hook induce, non esegue vehicle).
- Spiegabilità del verdetto `index` / `last_index` (E10-FEAT-037).
- Lease/mtime-lock o gestione del PID-reuse (limite accettato del lock PID-based).
- Cambi allo schema `rag.health/1` o al contratto `IndexLockedError`.

## Note di design (forcelle già sciolte)
- **Rimisura in SessionEnd, non SessionStart** — per non violare il confine D↔N e non aggiungere latenza
  all'avvio.
- **Reclamo del lock solo su PID decimale confermato morto** — un lockfile vuoto/garbage (possibile run
  vivo tra `create` e `write`) **non** viene reclamato: conservativo, fail-loud sull'ambiguità (chiude la
  race create→write, R-1).
- **Liveness senza `os.kill(pid,0)` su Windows** (che *termina* il processo): `OpenProcess` +
  `GetExitCodeProcess`/errore `ACCESS_DENIED` via `ctypes`; `os.kill(pid,0)` solo su POSIX.
