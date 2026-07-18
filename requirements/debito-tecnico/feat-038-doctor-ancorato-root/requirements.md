# Requisiti — `doctor` ancorato alla radice del progetto
<!-- Deriva da: E10-FEAT-038 (epica debito-tecnico) -->

## 1. Contesto e problema (perché)

`sertor-rag doctor` è il comando «**ha funzionato?**»: raccoglie 4 aree (config/provider/index/mcp) ed
emette pass/warn/fail. Oggi il suo verdetto **dipende dalla directory da cui lo lanci**, non solo dallo
stato reale del sistema.

**Bug provato** (`src/sertor_core/cli/__main__.py:574`, `_cmd_doctor`):
```python
root = Path.cwd()
...
stats = current_source_stats(manifest_state, root)   # sorgenti risolte come root/path
index_area = freshness_from_manifest(manifest_state, stats)
...
registered = read_mcp_registration(root)             # anche mcp usa la stessa root
```
`root = Path.cwd()` è il CWD del **processo**, non la radice del **progetto**. Le sorgenti indicizzate
sono risolte come `root/path`; da una sottocartella (es. `src/`) ogni file «manca» (`os.stat` fallisce →
`stale=True`) e `read_mcp_registration(root)` non trova la registrazione. Prova deterministica, **stesso
indice, stesso istante**, subito dopo un re-index:

| Invocato da | area `index` | area `mcp` (`registered`) |
|---|---|---|
| radice del progetto | `pass` | `True` |
| `src/` | `warn (index_stale)` | `False` |

È lo **stesso difetto d'ancoraggio** già corretto per gli **hook** in E10-FEAT-031 (che li ancorò via
`CLAUDE_PROJECT_DIR`), **mai corretto per `doctor`**. Già sfiorato e archiviato «not-a-bug» come
E15-FEAT-009 (2026-07-04: notammo `registered=False` come «artefatto cwd del *doctor*» e ci fermammo,
senza correggere).

**Perché conta:** `doctor` è la superficie di fiducia dell'utente, e l'hook `rag-freshness` **costruisce
il suo allarme sul verdetto di `doctor`** (E10-FEAT-034 dipende da questo fix). Un verdetto che cambia col
CWD produce **falsi `degraded`** e svaluta l'allarme. È il Principio XII (Fail Loud, Fix the Cause)
applicato alla superficie di salute: il verdetto deve fondarsi sullo stato reale, non su un artefatto
dell'ambiente d'invocazione.

## 2. Obiettivi e criteri di successo

**Obiettivo:** il verdetto di `doctor` è **funzione dello stato del progetto, non del CWD**. Da qualunque
sottocartella del progetto, a parità di indice, `doctor` dà lo **stesso** verdetto.

Criteri di successo (misurabili, tech-agnostici):
- **CS-1 (invarianza al CWD):** `doctor` invocato da **≥2** directory distinte del progetto (radice + una
  sottocartella annidata, es. `src/`) produce verdetto e stato di **ogni area identici**, a parità di
  indice → **0** divergenze.
- **CS-2 (`registered` stabile):** l'area `mcp` non passa `True`→`False` per il solo cambio di CWD → **0**
  flip dovuti alla directory.
- **CS-3 (fail-loud fuori progetto):** invocato da una directory che **non appartiene** a un progetto
  Sertor risolvibile, `doctor` **fallisce a voce alta** (messaggio azionabile, exit non-zero), **non**
  ripiega silenziosamente sul CWD emettendo un verdetto fuorviante.
- **CS-4 (sola lettura preservata):** risolvere la radice **non** crea/sposta/scrive alcun file → `doctor`
  scrive **0** file (invariante SC-009 esistente).
- **CS-5 (host-agnostico, Principio X):** la risoluzione della radice non contiene **alcun** path
  hardcodato host-specifico, verificabile da un **guard test**.

## 3. Stakeholder e attori
- **Utente/owner:** lancia `doctor` da dove sta lavorando (spesso non dalla radice) e deve fidarsi del verdetto.
- **Hook `rag-freshness` (consumatore a valle):** deriva il verdetto di salute da `doctor` (E10-FEAT-034).
- **Agente `concierge` / `guided-setup`:** orchestrano `doctor` come gate di verifica.
- **Ospite terzo:** riceve `doctor` via `sertor install rag`; l'ancoraggio deve funzionare sul suo layout.

## 4. Ambito

### In ambito
- Risoluzione **deterministica** della radice del progetto in `doctor`, indipendente dal CWD.
- Applicazione della radice risolta a **tutte** le aree che oggi usano `Path.cwd()`: `index`
  (`current_source_stats`) e `mcp` (`read_mcp_registration`).
- Comportamento **fail-loud** quando la radice non è risolvibile.
- Guard test di invarianza al CWD + host-agnosticità.

### Fuori ambito
- La **spiegabilità** del verdetto `index` (quale file ha cambiato, naming di `last_index`): resta a
  E10-FEAT-037 (investigata) / eventuale follow-up.
- La **rimisura post-riparazione** di `rag-freshness`: è E10-FEAT-034 (a valle, dipende da questo fix).
- Qualunque cambio allo **schema** del report `doctor.report/1` o alla logica di verdetto delle aree
  config/provider (non toccate dal CWD).
- Il *come* (algoritmo di walk-up, marker scelto, flag): **fase di design** (vedi §10).

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous):** *The doctor command shall determine the project root deterministically,
  independently of the process current working directory.*
- **REQ-002 (Ubiquitous):** *The doctor command shall resolve all indexed source paths and runtime
  artifacts (index manifest, MCP registration) relative to the determined project root, not to the
  process working directory.*
- **REQ-003 (Event-driven):** *When the doctor command is invoked from any subdirectory within a Sertor
  project, the system shall produce the same per-area verdict as when invoked from the project root,
  given the same index state.*
- **REQ-004 (Unwanted):** *If the project root cannot be determined, then the doctor command shall fail
  loud with an actionable message and a non-zero exit, and shall not fall back to the working directory
  to emit a verdict.*
- **REQ-005 (Ubiquitous):** *The doctor command shall remain read-only while resolving the root: it shall
  not create, move, or write any file.*
- **REQ-006 (Ubiquitous):** *The project-root resolution shall contain no host-specific hardcoded path,
  verifiable by a guard test (Principio X).*
- **REQ-007 (Optional):** *Where an explicit project root is provided by the caller, the doctor command
  shall use it as the project root instead of inferring one.* — **[DA CHIARIRE: se esporre un canale
  esplicito e quale — vedi §10]**

## 6. Requisiti non funzionali
- **Deterministico e offline-safe:** nessuna rete, nessun non-determinismo (coerente con `doctor` attuale).
- **Nessuna nuova dipendenza pesante:** risoluzione con stdlib.
- **Coerenza con il resto del CLI:** la radice risolta da `doctor` dovrebbe coincidere con quella che
  usano gli altri vehicle (index/search) sullo stesso progetto — **niente** una terza semantica di root.
- **Non-regressione:** invariati lo schema `doctor.report/1`, l'exit-code gate, l'evento `doctor`
  metrics-only, il comportamento dalla radice (oggi corretto).

## 7. Vincoli, assunzioni e dipendenze
- **Vincolo (Principio XI):** `doctor` è un vehicle; la correzione vive nel core dietro il CLI, non in un
  consumatore.
- **Vincolo (Principio XII):** fail-loud, mai degradare in silenzio.
- **Assunzione:** un «progetto Sertor» è individuabile da un marker deterministico presente sul layout
  reale (candidati in §10); la radice è **unica** risalendo dal CWD.
- **Dipendenza a valle:** E10-FEAT-034 (`rag-freshness` rimisura) **richiede** questo fix per essere
  sensata.
- **Riferimento:** E10-FEAT-031/`_hooklib.project_root()` (ancoraggio hook via `CLAUDE_PROJECT_DIR`) come
  precedente; `Settings.load` self-localizing come possibile fonte unica.

## 8. Rischi
- **R-1 — Marker ambiguo/assente:** un layout senza il marker scelto (o con più candidati) rende la radice
  indeterminata → mitigato da REQ-004 (fail-loud) + scelta del marker in design.
- **R-2 — Divergenza di semantica root** tra `doctor` e gli altri vehicle: se `doctor` risolve la radice
  diversamente da `index`/`Settings.load`, si crea un terzo comportamento → mitigato dall'NFR di coerenza.
- **R-3 — Regressione sul caso «dalla radice»:** oggi funziona; il fix non deve cambiarlo → coperto da CS-1
  (la radice resta un caso valido).
- **R-4 — Falso senso di sicurezza a valle:** finché il fix non è installato sull'ospite, `rag-freshness`
  resta inaffidabile (stessa lezione E10-FEAT-031/032: la consegna conta, non solo il merge).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, REQ-002, REQ-003, REQ-004, REQ-005, REQ-006 (il cuore del bug + fail-loud + read-only
  + host-agnostico).
- **Should:** REQ-007 (canale esplicito di root) — **solo se** la decisione di clarify lo richiede.
- **Could:** —
- **Won't (qui):** spiegabilità del verdetto `index` (E10-FEAT-037), rimisura freshness (E10-FEAT-034).

## 10. Domande aperte — SCIOLTE (clarify, decisione utente 2026-07-18)
- **Ancoraggio della radice: RISOLTO → riuso della self-localization esistente** (opzione 2). `doctor`
  risolve la radice del progetto con la **stessa** semantica già usata dal runtime per `.env`/`.index`
  (`settings._resolve_env_path`: derivazione dalla posizione del venv `Path(sys.prefix).parent`, layout
  `.sertor/`), **non** con `Path.cwd()`. Così `doctor` guarda **lo stesso `.sertor/.index`** che
  `index`/`search` scrivono → **una sola** semantica di root nel CLI (NFR di coerenza §6 onorato, rischio
  R-2 chiuso). **Override:** `doctor` **onora `CLAUDE_PROJECT_DIR`** se presente (parità con gli hook
  FEAT-031). **Fail-loud** se nessuna radice è risolvibile (REQ-004).
- **REQ-007 (canale esplicito `--root`): rinviato** — non necessario al primo taglio (la self-localization
  copre sia il caso interattivo sia quello a valle). Resta **Could**; se `rag-freshness` (FEAT-034) ne avrà
  bisogno per passare la root esplicitamente, si valuterà lì.
- *(Nota di design per `plan`: verificare la differenza di profondità del venv tra runtime installato
  — `.sertor/.venv` → root = `sys.prefix.parent.parent` — e dogfood — `.venv` → root = `sys.prefix.parent`;
  la risoluzione deve gestirle entrambe, coerente con i tre rami di `_resolve_env_path`.)*

---

## Commit proposto
`docs(requirements): E10-FEAT-038 — requisiti feature «doctor ancorato alla radice» (EARS)`
