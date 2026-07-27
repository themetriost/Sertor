# Contratto — `wiki.scan/1` (esteso, additivo)

**Vehicle**: `sertor-wiki-tools scan --json` (Principio XI — i consumatori passano di qui, non
importano `sertor_core`)

---

## ⚠️ Il vincolo che viene prima di tutto il resto

**La stringa `"wiki.scan/1"` NON si tocca.** I due consumatori installati la verificano per uguaglianza:

```python
# packages/sertor/src/sertor_installer/assets/claude/hooks/wiki-guard.py:101
if not scan or scan.get("schema") != "wiki.scan/1" or int(scan.get("pending", 0)) <= 0:
    return   # ← fail-open: NON blocca
```

Un bump a `wiki.scan/2` **non romperebbe** il gate: lo farebbe **sparire**. Nessun errore, nessun
breadcrumb, nessun `pending` — solo sessioni che chiudono sempre, su ogni ospite che ha aggiornato la
libreria ma non gli asset. È il caso peggiore, perché **l'assenza somiglia al successo**.

`fail-open` è la risposta **corretta** a «non so» — un gate di fine turno che si inceppa
intrappolerebbe la sessione. Diventa un difetto quando la stessa risposta copre anche «tu e io non
parliamo più la stessa lingua», che è un **fatto noto** e come tale va dichiarato.

> **Regola di evoluzione:** finché esistono consumatori che si spengono su mismatch, questo contratto
> evolve **solo per aggiunta** — campi nuovi, identificativo invariato.

**Presidiato da una guardia** (`packages/sertor/tests/test_scan_schema_frozen.py`), non
dall'attenzione: la guardia asserisce che la stringa emessa da `scan` è **letteralmente** quella che
gli hook confrontano, leggendo **entrambe le fonti** invece di ripetere la costante — altrimenti
sarebbe essa stessa un valore duplicato senza riconciliatore (Principio XIV).

---

## Forma

```jsonc
{
  "pending": 3,                                  // invariato — conteggio ESATTO (mai troncato)
  "anchor": "2026-07-27T17:33:23",               // invariato nel tipo: ISO-8601 | null
  "dirs_scanned": ["src", "specs", "requirements", ".claude"],
  "message": "…",                                // invariato nella semantica (+ nomi, vedi sotto)
  "schema": "wiki.scan/1",                       // CONGELATO

  // ── additivi ──────────────────────────────────────────────────────────
  "anchor_kind": "git",                          // "git" | "mtime" | null
  "anchor_ref": "4292aefc540f…",                 // non-null ⟺ anchor_kind == "git"
  "anchor_fallback_reason": null,                // non-null ⟺ anchor_kind == "mtime"
  "pending_paths": ["specs/…/spec.md", "…"],     // elenco troncato
  "pending_truncated": 0,                        // quanti restano fuori dall'elenco
  "stale_recording": null                        // "wiki/log/2026-07-24.md" se non consegnata e non di oggi
}
```

## Invarianti verificabili

| # | Invariante | Perché |
|---|---|---|
| C-1 | `schema == "wiki.scan/1"` **sempre** | vedi sopra |
| C-2 | `anchor_kind == "git"` ⟹ `anchor_ref != null` | un'ancora derivata dev'essere **citabile** |
| C-3 | `anchor_kind == "mtime"` ⟹ `anchor_fallback_reason != null` | **mai un proxy muto** |
| C-4 | `anchor_kind == null` ⟺ `anchor == null` | nessuna registrazione ⇒ tutto in sospeso |
| C-5 | `pending == len(pending_paths) + pending_truncated` | il conteggio è esatto, l'elenco è troncato |
| C-6 | `pending == 0` ⟹ `pending_paths == []` | |
| C-7 | `anchor_fallback_reason ∈ {not_a_repository, git_unavailable, log_never_committed, null}` | tassonomia **chiusa** |
| C-8 | I campi preesistenti conservano tipo e significato | un consumatore vecchio non si accorge del cambiamento |

## Compatibilità dei messaggi (`strings` dell'ospite)

Il template dell'ospite continua a essere renderizzato **come oggi** (`{n}` → conteggio). I nomi:

- se il template contiene `{files}` → sostituiti **lì** (l'ospite controlla la posizione);
- altrimenti → **accodati** al messaggio renderizzato.

Un ospite che non sa nulla del cambiamento **non deve fare niente**: è FR-008.

## Esempi

**Ospite git, tutto registrato**
```json
{"pending": 0, "anchor": "2026-07-27T17:33:23", "anchor_kind": "git",
 "anchor_ref": "4292aef…", "anchor_fallback_reason": null,
 "pending_paths": [], "pending_truncated": 0, "stale_recording": null,
 "message": "No files newer than the last log entry.", "schema": "wiki.scan/1"}
```

**Ospite git, lavoro non registrato + voce stantia non consegnata**
```json
{"pending": 2, "anchor": "2026-07-24T09:12:00", "anchor_kind": "git",
 "anchor_ref": "9cb2fb1…", "anchor_fallback_reason": null,
 "pending_paths": ["src/sertor_core/wiki_tools/scan.py", "specs/123-…/plan.md"],
 "pending_truncated": 0, "stale_recording": "wiki/log/2026-07-24.md",
 "message": "Work not yet recorded in the wiki: 2 files… — src/…/scan.py, specs/123-…/plan.md",
 "schema": "wiki.scan/1"}
```

**Ospite non-git (il proxy, dichiarato)**
```json
{"pending": 1, "anchor": "2026-07-27T16:27:19", "anchor_kind": "mtime",
 "anchor_ref": null, "anchor_fallback_reason": "not_a_repository",
 "pending_paths": ["src/foo.py"], "pending_truncated": 0, "stale_recording": null,
 "message": "Work not yet recorded in the wiki: 1 file… — src/foo.py", "schema": "wiki.scan/1"}
```
*I path si nominano **anche qui** (FR-006 non è condizionato alla modalità): l'attraversamento li
conosce già, oggi li butta via contandoli. **Ciò che manca in questa modalità è solo il filtro
«ignorato dal VCS»** — quindi l'elenco può contenere uno scratch che in modalità derivata non ci
sarebbe. È un limite **dichiarato** (A-6, `anchor_kind` lo rende leggibile), non simulato: nominare
un file di troppo lascia comunque a chi legge una diagnosi migliore di un numero nudo.*
