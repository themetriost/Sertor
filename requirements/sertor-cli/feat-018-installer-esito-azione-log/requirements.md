# Requisiti — L'installer descrive l'AZIONE (non la precondizione) + log ispezionabile
<!-- Deriva da: E2-FEAT-018 (epica sertor-cli). Assorbe E10-FEAT-036. -->

## 1. Contesto e problema (perché)

Il report dell'installer **dichiara ciò che presume, non ciò che è successo** — è il 3° item della coda
dell'analisi [[setup-dichiara-presunzione-non-azione]] (dopo FEAT-038 e FEAT-033, entrambe consegnate).
Due prove verificate sul codice:

- **Prova regina** (`packages/sertor/src/sertor_installer/install_rag.py:708-717`, `_apply_deps`):
  ```python
  already = (sertor_dir / "pyproject.toml").exists()
  ...                                    # `uv add` gira SEMPRE (il comando è eseguito)
  outcome = Outcome.SKIPPED if already else Outcome.CREATED   # 'already' = la dir c'era
  ```
  L'esito descrive **se la directory esisteva**, non **cosa ha fatto il comando**. Contraddizione interna:
  `detail = "uv add {spec}"` (comando eseguito) mentre `outcome = SKIPPED`.
- **`Outcome` conflaziona** (`packages/sertor-install-kit/src/sertor_install_kit/artifacts.py:63`):
  `SKIPPED` significa sia *«identico, giustamente nulla da fare»* sia *«presente ma diverso, non l'ho
  toccato»* — il buco esatto da cui sono passati FEAT-031/032. In install, `_apply_file`
  (`install_governance.py`) fa `if dest.exists(): return SKIPPED "already present"` **senza confrontare il
  contenuto**. **Ironia:** il confronto di contenuto **esiste già** in uninstall
  (`lifecycle.py:159-164`: legge il dest, normalizza CRLF, confronta col contenuto atteso → «preserved:
  modified since install»); l'install semplicemente non lo chiede.

Corollario (assorbe **E10-FEAT-036**): `upgrade` che installa una capability ex-novo oggi è indistinguibile
nel report da un vero refresh. Con un esito che descrive l'azione, «upgrade ha **creato** 3 artefatti
ex-novo» diventa un **fatto nel report**, non un caso speciale da `if` hard-coded.

**Perché conta:** l'utente (e le nostre guardie) si fidano del report; se dice «skipped» quando un comando
è girato, o «0 removed» lasciando artefatti rotti, il report non è un racconto affidabile. È il Principio
XII (Fail Loud, Fix the Cause) applicato al *racconto* del setup.

## 2. Obiettivi e criteri di successo

**Obiettivo:** ogni artefatto/step dell'installer riporta **ciò che ha fatto** e su **quale evidenza**;
un log ispezionabile è la **verità** di ciò che è successo, con il report a schermo come sintesi. Nessuna
precondizione spacciata per azione.

Criteri di successo (misurabili, tech-agnostici):
- **CS-1 (esito = azione, P1):** per un artefatto **presente ma con contenuto diverso** da quello che
  l'installer depositerebbe, il report lo distingue esplicitamente da **presente e identico** (≥2 esiti
  distinti osservabili), invece di collassare entrambi in `SKIPPED`.
- **CS-2 (deps oneste, P1):** l'esito dello step dipendenze riflette **se il comando è stato eseguito**,
  non solo se la directory preesisteva (niente `SKIPPED` quando `uv add` è girato).
- **CS-3 (036 assorbita):** un `upgrade` che installa una capability **assente** è **leggibile dal report**
  come creazione ex-novo (≥1 esito che lo dichiara), senza logica dedicata a 036.
- **CS-4 (log ispezionabile, P2):** dopo un `install`/`upgrade`/`uninstall`, esiste un log locale
  (`.sertor/.install-log.jsonl`) con, per ogni step/artefatto: **verbo reale**, capability, comando
  eseguito (se c'è), esito col **perché**, e la revisione risolta. Ispezionabile a posteriori.
- **CS-5 (`--dry-run` fedele):** ciò che `--dry-run` proietta e ciò che l'esecuzione reale scrive nel log
  provengono dallo **stesso codice** (nessuna scorciatoia divergente): gli esiti proiettati coincidono con
  quelli reali sugli stessi input.
- **CS-6 (backward-compat):** gli esiti **esistenti** (CREATED/SKIPPED-identico/MERGED/…) restano
  **byte-compatibili** nel report dove non c'è divergenza (nessuna regressione delle suite installer/kit).
- **CS-7 (host-facing completo):** la capacità è installabile e **documentata** per l'ospite (bundle
  sync + doc utente), non solo nel dogfood (regola «feature completa» + regola «doc utente»).

## 3. Stakeholder e attori
- **Utente/owner che installa:** legge il report/log e deve potersi fidare (richiesta 2026-07-16: «loggare
  cosa succede così non ci dobbiamo fidare alla cieca»).
- **Ospite che *evita* un blocco** (caso Noetix, E2-FEAT-019): un `upgrade` che crea ex-novo dev'essere visibile.
- **Le nostre guardie** (es. esito d'upgrade di FEAT-032): hanno bisogno di un esito osservabile e veritiero.
- **Nodo Noetix:** origine (verifica indipendente che ha smentito 3 nostre affermazioni sull'installer).

## 4. Ambito

### In ambito
- **P1 — l'esito descrive l'azione:** distinguere `presente-identico` da `presente-divergente` (riusando
  il confronto di contenuto di `lifecycle.py`), e rendere onesto lo step dipendenze (`_apply_deps`).
- **Fold di E10-FEAT-036:** l'upgrade-crea-ex-novo diventa un fatto del report (nessun `if` dedicato).
- **P2 — log ispezionabile** `.sertor/.install-log.jsonl` estendendo `log_event` (già esistente).
- **`--dry-run` fedele** (stesso codice di proiezione ed esecuzione).
- **Distribuzione host-facing:** sync del bundle installer + aggiornamento della **doc utente**.

### Fuori ambito
- **P3 (lettore unico / `doctor` che legge i segnali runtime) + E2-FEAT-017 (onestà auto-updater):** item
  successivi della coda; qui ci si ferma al *produrre* l'esito/log onesto, non all'aggregarli.
- Ridisegno del formato del report a schermo oltre il minimo per esporre i nuovi esiti.
- Il *come* esatto (nuovi membri `Outcome` vs reason strutturato, schema del log): §10 (clarify) + design.

## 5. Requisiti funzionali (EARS)

- **REQ-001 (Event-driven):** *When the installer encounters an artifact already present at an owned path,
  it shall compare its content with what it would deploy and report `present-identical` and
  `present-divergent` as DISTINCT outcomes.*
- **REQ-002 (Ubiquitous):** *The installer shall report the outcome of an executed command (e.g. `uv add`)
  as an action performed, not as `skipped` merely because a precondition (directory present) held.*
- **REQ-003 (Event-driven):** *When `upgrade` deposits a previously-absent capability, the report shall
  express it as a creation, distinguishable from a refresh of an existing one (absorbs E10-FEAT-036).*
- **REQ-004 (Ubiquitous):** *The installer shall write an inspectable local log (`.sertor/.install-log.jsonl`)
  recording, per step/artifact: the operation verb, capability, the command run (if any), the outcome with
  its reason, and the resolved revision.*
- **REQ-005 (Ubiquitous):** *The dry-run projection and the real run shall derive outcomes from the same
  code path, producing identical outcomes for identical inputs (no divergent shortcut).*
- **REQ-006 (Ubiquitous):** *Existing outcomes shall remain backward-compatible where no divergence exists
  (no regression of the current report for identical/created/merged cases).*
- **REQ-007 (Unwanted):** *If writing the log fails, then the installer shall not abort the installation;
  it shall surface the log-write failure without losing the primary operation (fail-safe, exit preserved).*
- **REQ-008 (Ubiquitous):** *The new capability (honest outcomes + install log) shall be installable on a
  host via the installer and reflected in the user documentation (host-facing completeness).*

## 6. Requisiti non funzionali
- **Determinismo, offline, no rete;** stdlib + ciò che l'installer già usa; nessuna nuova dipendenza pesante.
- **Segreti:** il log **non** deve contenere segreti (scrub coerente con l'osservabilità esistente).
- **Non-distruttività / idempotenza** dell'installer invariate (Principio VI).
- **Osservabilità (Principio IX):** riusa `log_event`/lo strato d'osservabilità del kit, non un canale nuovo slegato.

## 7. Vincoli, assunzioni e dipendenze
- **Riuso, non reinvenzione:** il confronto di contenuto (`lifecycle.py:159-164`) e `log_event`
  (`observability.py:38`) **esistono già** → estenderli, non duplicarli.
- **Vincolo (Principio X):** il log e gli esiti sono host-agnostici (path relativi a `.sertor/`, nessun assunto host).
- **Vincolo (Principio XII):** l'esito onesto è il cuore; il fail-safe di REQ-007 non deve *nascondere* il fallimento del log.
- **Dipendenza:** nessuna a monte; **abilita** la guardia sull'esito d'upgrade (FEAT-032) e la P3 futura (lettore unico).

## 8. Rischi
- **R-1 — Rottura backward-compat del report:** cambiare gli esiti esistenti romperebbe guardie/test →
  mitigato da REQ-006 + scelta additiva (§10).
- **R-2 — Log rumoroso/segreti:** un log troppo verboso o con segreti → scrub + campi a cardinalità chiusa dove possibile.
- **R-3 — `--dry-run` che diverge:** se proiezione ed esecuzione usano rami diversi → REQ-005 lo vieta esplicitamente.
- **R-4 — Scope creep verso P3/017:** tenere il confine (produrre, non aggregare) — l'aggregazione è item successivo.
- **R-5 — Distribuzione dimenticata:** la feature non è «done» finché bundle+doc utente non riflettono (CS-7, regola feature completa).

## 9. Prioritizzazione (MoSCoW)
- **Must:** REQ-001, REQ-002, REQ-003 (P1 + fold 036), REQ-006 (no regressione), REQ-008 (host-facing).
- **Should:** REQ-004, REQ-005 (P2 log + dry-run fedele), REQ-007 (fail-safe log).
- **Could:** arricchimenti del report a schermo oltre il minimo.
- **Won't (qui):** P3 lettore unico, E2-FEAT-017 (item successivi della coda).

## 10. Domande aperte — SCIOLTE (clarify, decisioni utente 2026-07-18)
- **FORCELLA 1 — modello dell'esito: RISOLTA → un SOLO nuovo membro `Outcome`** per lo stato oggi **non
  rappresentato** («presente ma divergente / left-stale»), es. `PRESENT_DIVERGENT` (nome esatto in design).
  L'`identico` resta `SKIPPED` (byte-invariato). Additivo → osservabile dalle guardie (type-safe) e
  backward-compat sugli esiti esistenti (REQ-006). **Scartati:** il reason-only (distinzione «soft») e il
  set completo di nuovi membri (tocca tutti i consumatori + rischio cambio report).
- **FORCELLA 2 — schema del log: RISOLTA → JSONL append**, **una riga JSON per artefatto/step**, schema
  versionato **`install.event/1`**, campi a **cardinalità chiusa** (`op` ∈ install/upgrade/uninstall,
  `capability`, `verb`, `outcome`, `reason`, `cmd` se presente, `rev` risolta). **Nessuna rotazione** al
  primo taglio (append semplice). Scrub segreti coerente con l'osservabilità esistente (RNF).
- **FORCELLA 3 — `_apply_deps` onesto: DECISO (default)** → l'esito riflette l'**esecuzione**: `uv add`
  eseguito su ambiente già presente ma idempotente non è `SKIPPED` per «dir c'era»; il design sceglie fra un
  esito «eseguito-idempotente» e il riuso di un membro esistente, purché **non** dichiari «skipped» quando il
  comando è girato (REQ-002).
- **FORCELLA 4 — dove risiede il log-writer: DECISO (default)** → nel **kit**
  (`sertor_install_kit/observability.py`, accanto a `log_event`), riusabile dai **tre** installer
  (`sertor install rag`/`wiki`, `sertor-flow`) — coerenza e riuso (Principio X/riuso).

---

## Commit proposto
`docs(requirements): E2-FEAT-018 — requisiti «installer esito-azione + log» (EARS, assorbe E10-FEAT-036)`
