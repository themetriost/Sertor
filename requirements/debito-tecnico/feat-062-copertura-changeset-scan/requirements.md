# Requisiti — la registrazione copre un *changeset*, non una *data*
<!-- Deriva da: E10-FEAT-062 (epica debito-tecnico) -->

## 1. Contesto e problema (perché)

`sertor-wiki-tools scan` risponde a *«c'è lavoro non ancora registrato nel wiki?»*. È la rilevazione su
cui poggiano **due** consumatori host-facing: l'hook **`wiki-guard`** (`Stop`), l'unico **bloccante**, e
`wiki-pending-check` (`SessionEnd`, promemoria).

Dalla E10-FEAT-045 (v0.3.2) l'ancora è **derivata dalla storia** — l'ultimo commit che ha toccato il
giornale, unito alle modifiche non consegnate dell'albero. Quel lavoro ha chiuso il **deadlock** (una
sessione non poteva chiudersi sul proprio ultimo merge) ed è confermato risolto dal campo. Ma ha lasciato
in piedi la decisione **A-2** — *«una voce non committata vale, ma solo quella di oggi»* — implementata
come **azzeramento globale**:

```python
# src/sertor_core/wiki_tools/scan.py:286-292
recorded_today = today is not None and today in worktree
pending_paths = ([] if recorded_today else sorted({p for p in touched if _in_scope(profile, p)}))
```

`recorded_today` è vero per la **sola presenza** del path della partizione di oggi fra le modifiche
dell'albero. Da quel momento `pending` è **0 per costruzione**, qualunque lavoro ci sia intorno.

**Segnalato dal campo** (nodo *Acta*, 2026-07-29, canale *Feedback Sertor*): `scan` risponde `pending: 0`
in tre situazioni di lavoro non registrato, mentre `ritual-check` sullo stesso albero vede `drift=4`.
La loro formulazione è il criterio di gravità: *«un gate che non blocca mai è indistinguibile da un gate
disinstallato»* — e conta **otto** nodi con la capability wiki sul proprio host.

**La classe è già nostra.** Il gate verifica la **presenza** di una registrazione, non la **copertura**
del lavoro: quinta istanza di [[identita-per-presenza-o-per-contenuto]], e con il segno peggiore — le
altre producono un no-op che *sembra* un successo, questa un **via libera che sembra pulizia**. Il test
`test_todays_uncommitted_entry_satisfies_the_gate_without_a_commit` **certifica** il comportamento:
guardia e test condividono lo stesso errore di identità, per questo nessuno dei due l'ha visto.

**Il verso dell'errore è però migliorato** e va detto: un gate cieco è meno dannoso di un gate che
impedisce di chiudere la sessione. Questa feature non torna indietro sulla FEAT-045 — la completa.

## 2. Analisi degli scenari (misurata, non dedotta)

Matrice eseguita su host git effimeri, `source_dirs = ["src", "specs"]`, un solo file di lavoro.
Strumento: matrice comportamentale in scratchpad; ogni riga è una `scan()` reale.

### 2.1 Scenari A–G (il nucleo del difetto)

| # | Scenario | `pending` | Verdetto |
|---|---|---|---|
| **A** | lavoro non committato · nessun giornale di oggi | **1** | ✅ corretto |
| **B** | lavoro non committato · giornale di oggi **committato** | **1** | ✅ corretto |
| **C** | lavoro non committato · giornale di oggi **non tracciato** | **0** | ❌ non rilevato |
| **D** | lavoro non committato · giornale di oggi **modificato** | **0** | ❌ non rilevato |
| **E** | lavoro **committato** non registrato · albero pulito | **1** | ✅ corretto |
| **F** | lavoro **committato** non registrato · giornale non tracciato | **0** | ❌ non rilevato |
| **G** | giornale scritto · **lavoro prodotto DOPO di esso** | **0** | ❌ non rilevato |

**G è il caso che conta.** Il rituale prescrive di scrivere la voce di giornale; nel momento in cui la
scrivi — file nuovo, non ancora committato — `scan` smette di vedere tutto il lavoro successivo per il
resto della giornata. **Chi soddisfa la regola la disattiva**, e lo fa nella finestra esatta in cui lo
`Stop` interroga il gate.

### 2.2 Scenari H–N2 (estensione: cosa altro non viene rilevato)

| # | Scenario | `pending` | Verdetto |
|---|---|---|---|
| **H** | giornale di oggi **senza alcuna voce** (solo il titolo) | **0** | ❌ non rilevato |
| **I** | giornale di oggi **file vuoto (0 byte)** | **0** | ❌ non rilevato |
| **J** | giornale toccato con **una sola riga vuota** | **0** | ❌ non rilevato |
| **K** | lavoro **staged** non committato | **1** | ✅ corretto |
| **L** | file sorgente **cancellato** | **1** | ✅ corretto |
| **M** | lavoro **fuori** da `source_dirs` (`packages/`, `CLAUDE.md`) | **0** | ⚠️ fuori perimetro |
| **N** | lavoro in path **gitignorato** | **0** | ✅ by design (FEAT-048) |
| **N2** | giornale di **ieri** non tracciato | **1** | ✅ corretto + `stale_recording` nominato |

**H, I, J sono il difetto sotto il difetto:** il gate non richiede una *voce*, richiede un *file*. Un
file vuoto lo soddisfa. Una riga vuota appesa lo soddisfa. È la regola git che abbiamo appena distribuito
— *«modificato» ha due significati* — non applicata al lato-giornale.

**M non è questo difetto ma va nominato** (vedi §11): sul nostro host `source_dirs = ["src", "specs",
"requirements", ".claude"]`, quindi le modifiche a `packages/` (**l'installer**, cioè gli asset
host-facing) e ai file di radice come `CLAUDE.md` **non innescano mai** il gate.

### 2.3 Race e degradazioni

| # | Scenario | `pending` | Verdetto |
|---|---|---|---|
| **R1** | `git diff`/`git status` **falliscono** (index.lock concorrente) | **0** | ❌ **falso pulito silenzioso** |
| **R1b** | *controprova:* stesso albero, git sano | **1** | ✅ |
| **R2** | **merge in conflitto** in corso (albero transitorio) | **1** | ✅ conservativo |
| **R3** | **sessione 2** lavora, giornale già sporco per la sessione 1 | **0** | ❌ non rilevato |

**R1 è un secondo difetto, indipendente da `recorded_today`.** Ogni invocazione git che fallisce degrada
verso l'insieme vuoto, in silenzio:

```python
# _committed_since
return _split_z(out) if rc == 0 else []
# _worktree_changes
paths = _split_z(tracked_out) if tracked_rc == 0 else []
if rc != 0: return paths
```

E l'output continua a dichiarare `anchor_kind: "git"` con `anchor_fallback_reason: null` — cioè **afferma
di aver derivato** ciò che non ha derivato. Il consumatore non può distinguere «pulito» da «non ho
potuto guardare». È esattamente il Principio XII: la degradazione è ammessa **solo se segnala**.

**Non è teorico su questo progetto:** la nostra governance delega git al `configuration-manager` **in
background**, quindi un `git add`/`commit` concorrente che tiene `index.lock` mentre lo `Stop` esegue
`scan` è una configurazione **normale**, non un caso patologico.

**R3** è la stessa causa di C–J vista in multi-sessione: due assistenti (o due finestre) sullo stesso
repo condividono la partizione del giorno; la registrazione dell'uno spegne il gate per l'altro.

### 2.4 Sintesi causale

**Otto scenari** (C · D · F · G · H · I · J · R3) hanno **una sola causa**: `recorded_today` come
azzeramento globale basato su presenza-di-file e data. **Uno** (R1) è indipendente: degradazione
silenziosa verso l'insieme vuoto. **Uno** (M) è perimetro di configurazione, non codice.

## 3. Costi (misurati)

**Costo attuale, pagato a ogni turno** — `wiki-guard` è cablato su `Stop`:

| Voce | Misura |
|---|---|
| Invocazioni git per `scan()` | **7** spawn (`rev-parse --is-inside-work-tree` · `log -1` · `diff HEAD` · `status` · `diff ref HEAD` · `rev-parse --show-prefix` ×2) |
| Tempo in-process | ~93 ms |
| **Tempo end-to-end come lo paga l'hook** | **~330 ms** (3 giri: 338 · 326 · 335 ms) |

Il costo dominante non è git, è l'avvio del processo CLI via `uv run --project .sertor`. `repo_prefix` è
invocato **due volte** per la stessa risposta (una per il ramo committed, una per il worktree): margine
deterministico già disponibile, ~1 spawn.

**Costo aggiuntivo del rimedio proposto** (§5):

| Voce | Misura / stima |
|---|---|
| Changeset del giornale (`git diff -U0 -- <log>`) | **+1** spawn, ~15–20 ms — ~6% sul baseline end-to-end |
| Calcolo della copertura in `append-log` | **una** `scan` per voce scritta (~330 ms), **non** per turno |
| Identità di contenuto (variante forte) | **+1** spawn totale: `git hash-object --stdin-paths` accetta N path in una sola invocazione — **verificato** |
| Dimensione della voce | una riga per path coperto (o elenco troncato con conteggio dichiarato) |

**Fatto di costo verificato che vincola il design:** `git diff --raw HEAD` **non** serve — restituisce
`0000000` sul lato albero-di-lavoro (il blob non committato non è nell'object DB). L'identità di
contenuto del non-committato si ottiene con `git hash-object --stdin-paths`, **un solo spawn per N
path**, e coincide esattamente con `git rev-parse HEAD:<path>` quando il file è intatto (controprova
eseguita). La variante forte è quindi **quasi gratis**, non costosa come sembrerebbe.

**Costi non computazionali, che sono i veri:**
- `append-log` è **host-facing** → scattano la regola 1 (dev'essere installabile su un ospite) e la
  regola 3 (documentazione utente aggiornata nello stesso step).
- La stringa di schema **`wiki.scan/1` non si bumpa**: i due hook la confrontano per **uguaglianza** e
  vanno in **fail-open**, quindi un bump non romperebbe il gate — lo farebbe **sparire in silenzio**
  sugli ospiti non aggiornati. Aggiungere *campi* è compatibile; cambiare la *stringa* no.
- La migrazione delle voci già scritte è un bivio con due esiti opposti (§10).

## 4. Obiettivi e criteri di successo

**Obiettivo:** `scan` risponde `pending: 0` **solo quando il lavoro è effettivamente coperto da una
registrazione**, e quando non può stabilirlo lo **dichiara** invece di rispondere «pulito».

- **CS-1 (nessun azzeramento globale):** in tutti gli scenari **C · D · F · G · H · I · J · R3** `scan`
  riporta `pending > 0` con i path nominati → **0** falsi negativi sugli otto casi misurati.
- **CS-2 (non-regressione anti-deadlock):** gli scenari della FEAT-045 restano verdi — in particolare
  *«merge poi pull non blocca la sessione»* e *«lavoro e giornale nello stesso commit non lasciano nulla
  di pendente»* → **0** regressioni sulla suite `test_wiki_tools_scan_git.py`.
- **CS-3 (una voce vale per ciò che copre):** dopo aver registrato, il lavoro **prodotto in seguito**
  torna pendente (scenario G) → il gate resta vivo per il resto della sessione.
- **CS-4 (voce = contenuto, non file):** una partizione vuota, senza voci, o toccata con sola
  spaziatura **non** soddisfa il gate (H · I · J) → **0** casi soddisfatti senza una voce reale.
- **CS-5 (mai un falso pulito silenzioso):** se le informazioni necessarie non sono ottenibili (git che
  fallisce, R1), `scan` **non** riporta `0` come se avesse guardato: dichiara la condizione in un campo
  ispezionabile e il consumatore bloccante **non** interpreta l'esito come «pulito».
- **CS-6 (indipendenza dalla data):** l'esito non dipende dal fatto che la voce stia nella partizione di
  *oggi* → rimuovere la data dalla logica non cambia alcun verdetto corretto.
- **CS-7 (compatibilità del contratto):** la stringa `wiki.scan/1` è **invariata**; un consumatore vecchio
  che riceve l'output nuovo continua a funzionare, verificato da una guardia.
- **CS-8 (costo):** il costo end-to-end di `scan` non cresce oltre **+15%** rispetto al baseline
  misurato (~330 ms).

## 5. Forma del rimedio (cosa, non come)

Sostituire *«esiste una voce oggi?»* con *«questo lavoro è coperto da una registrazione?»*:

```
una voce AGGIUNTA (verificata sul changeset del giornale) dichiara l'INSIEME DI PATH che copre
pending = lavoro_in_perimetro − copertura
```

Conseguenze:
- **La data sparisce dalla logica.** Una voce di ieri è semplicemente una voce che non copre nulla di
  nuovo; `stale_recording` — che oggi esiste apposta per nominare la voce-non-di-oggi — diventa
  superfluo. La data torna a essere ciò che è sempre stata: **il nome di un file**.
- **Lo scenario G cade fuori gratis:** il lavoro successivo non è nell'insieme coperto.
- **La copertura si DERIVA, non si dichiara a mano:** è `append-log` a calcolarla (Principio XIV — un
  fatto derivato, non una copia scritta a mano), restando interamente sul lato deterministico (zero LLM).
- **Effetto collaterale positivo:** la voce di giornale diventa leggibile come *ciò che copre*, utile al
  lint semantico e a `distill-audit`. E se l'agente barasse dichiarando di coprire tutto, resterebbe
  **scritto nel record**: il verso dell'errore passa da accecamento silenzioso a **dichiarazione
  falsificabile**.

**Limite dichiarato, non nascosto:** la copertura è a granularità di **path**, non di significato. Una
voce può dichiarare di coprire un file di cui non parla. Resta *presenza* a un livello più fine — è un
miglioramento grande, non l'eliminazione del giudizio.

## 6. Requisiti funzionali (EARS)

- **REQ-001 (Ubiquitous):** *The scan operation shall determine pending work by comparing the changed
  work set against the set of paths covered by recordings, and shall not treat the mere existence of a
  log partition as covering anything.*
- **REQ-002 (Ubiquitous):** *The scan operation shall recognise a recording only when the log changeset
  adds a log entry, and shall not recognise a whitespace-only, empty, or entry-less log file as a
  recording.*
- **REQ-003 (Event-driven):** *When work is authored after a recording has been written, the scan
  operation shall report that work as pending.*
- **REQ-004 (Ubiquitous):** *The scan operation shall determine coverage independently of the calendar
  date of the log partition in which a recording resides.*
- **REQ-005 (Ubiquitous):** *The append-log operation shall derive and persist the set of paths that the
  appended entry covers, without requiring the caller to supply it.*
- **REQ-006 (Unwanted):** *If the information required to determine pending work cannot be obtained,
  then the scan operation shall declare that condition in an inspectable field and shall not report a
  zero pending count as though the determination had succeeded.*
- **REQ-007 (Unwanted):** *If a version-control command fails during a derived-mode scan, then the
  operation shall not silently substitute an empty change set.*
- **REQ-008 (Event-driven):** *When the blocking consumer receives a scan result whose determination did
  not succeed, the consumer shall not treat it as clean.*
- **REQ-009 (Ubiquitous):** *The scan result schema identifier shall remain `wiki.scan/1`, and any new
  information shall be conveyed by additive fields.*
- **REQ-010 (Ubiquitous):** *The scan operation shall name the pending paths, preserving the existing
  truncation-with-declared-count behaviour.*
- **REQ-011 (Optional):** *Where content identity is available from version control, the scan operation
  shall consider a covered path pending again if its content has changed since it was covered.*
- **REQ-012 (Ubiquitous):** *The coverage mechanism shall be host-agnostic, deriving all host-specific
  settings from the wiki configuration file, with no hardcoded path.*
- **REQ-013 (Ubiquitous):** *In declared-proxy mode (non-repository hosts), the operation shall keep its
  current behaviour and continue to declare the typed fallback reason.*

## 7. Requisiti non funzionali

- **Deterministico, offline, stdlib + git:** nessuna rete, nessun LLM (confine D↔N invariato).
- **Costo:** vedi CS-8; il percorso caldo è lo `Stop`, cioè **ogni turno**.
- **Non-regressione:** invariati lo schema `wiki.scan/1`, il comportamento in modalità proxy, l'esclusione
  dei file gitignorati (FEAT-048), il fail-open degli hook quando `scan` è **assente** (diverso dal caso
  in cui `scan` risponde «non ho potuto determinare»).
- **Host-agnostico (Principio X):** funziona su ospiti con root, tassonomia e lingua diverse.
- **Vehicle-only (Principio XI):** i consumatori restano CLI/hook; nessun import diretto del core.

## 8. Vincoli, assunzioni e dipendenze

- **Vincolo critico:** la stringa `wiki.scan/1` **non si bumpa** (§3). Guardia dedicata già esistente
  dalla FEAT-045: va estesa, non sostituita.
- **Vincolo:** `append-log` è host-facing → regola 1 (installabile) + regola 3 (doc utente nello stesso
  step). Non è un fix interno.
- **Assunzione:** il formato dell'intestazione di voce è un contratto stabile
  (`## [YYYY-MM-DD] <op> | <titolo>`), già parsato in `distill-floor.py:74` — **riuso, non nuova
  macchina**, come la FEAT-045 riusò `ritual_check.py`.
- **Dipendenza:** convergente con **E10-FEAT-060** (`ritual-check` e `wiki-guard` misurano realtà
  diverse). Le due vanno progettate guardandosi: qui si definisce *cosa* è coperto, lì *quale* base di
  confronto. Da valutare al `plan` se chiuderle insieme.
- **Fonte esterna:** riscontro nodo *Acta* del 2026-07-29 (canale *Feedback Sertor*), verificato sul
  nostro codice e riprodotto.

## 9. Rischi

- **R-1 — Riaprire il deadlock.** Il rimedio tocca esattamente il meccanismo che la FEAT-045 ha usato per
  chiuderlo. Mitigazione: CS-2 come gate esplicito, i test del deadlock come non-regressione **prima**
  dell'implementazione.
- **R-2 — Gate troppo severo alla consegna.** Se la migrazione tratta le voci prive di copertura come
  «non coprono nulla», al primo upgrade il gate blocca **su ogni nodo**. Mitigazione: §10, decisione
  esplicita prima del design.
- **R-3 — Copertura dichiarata a vuoto.** L'agente può registrare una voce che copre tutto senza aver
  scritto nulla di sostanziale. Non eliminabile deterministicamente; mitigato dal fatto che la
  dichiarazione è **scritta e falsificabile** (vs. l'accecamento attuale, invisibile).
- **R-4 — Rumore da un gate più sensibile.** Rendere il gate vivo per tutta la sessione può produrre
  blocchi frequenti e insegnare ad aggirarlo — lo stesso difetto che il lint aveva prima della v0.3.3.
  Mitigazione: il blocco **nomina i file**, ed è risolvibile registrando.
- **R-5 — Consegna, non merge.** Come per FEAT-031/032, il fix conta quando **arriva sugli ospiti**: fino
  ad allora gli otto nodi di *Acta* restano con il gate cieco.

## 10. Domande aperte (da sciogliere in `clarify`, non da assumere)

- **DA-1 — Migrazione delle voci esistenti.** Due regole possibili, con esiti opposti: *(a)* voce senza
  copertura dichiarata = **copre tutto** → compatibile, nessun blocco improvviso, ma si porta dietro il
  buco finché le voci vecchie sono nel worktree (in pratica: un giorno); *(b)* = **non copre nulla** →
  corretto da subito, ma al primo upgrade il gate blocca ovunque. **Decisione utente**, non di design.
- **DA-2 — Granularità della copertura.** Solo path (semplice, voce leggibile) oppure `(path, blob)`
  (REQ-011: un file registrato e poi modificato ancora torna pendente). Il costo non è più un
  discriminante (§3: un solo spawn); la scelta è fra **precisione** e **verbosità della voce**.
- **DA-3 — Dove vive la copertura.** Dentro la voce di giornale (visibile, umana, parte del record — e
  coerente col Principio XIV) oppure in un sidecar (invisibile, ma è **una copia in più da
  riconciliare**, che il XIV sconsiglia). *Raccomandazione: dentro la voce.*
- **DA-4 — Comportamento del consumatore bloccante su determinazione fallita** (REQ-008): bloccare
  (conservativo, ma un git rotto impedisce di chiudere la sessione) oppure lasciar passare **dichiarando
  a voce alta**. *Raccomandazione: lasciar passare + dichiarare*, coerente col fail-open attuale degli
  hook, perché il verso «gate cieco» è meno dannoso di «sessione non chiudibile» — che è la lezione
  della FEAT-045 stessa.
- **DA-5 — Se chiudere insieme E10-FEAT-060.** Da valutare al `plan`.

## 11. Fuori ambito (promossi, non sepolti)

- **Perimetro di `scan` sul dogfood** (scenario M): `packages/` — cioè **l'installer e gli asset
  host-facing** — e i file di radice come `CLAUDE.md` non sono in `source_dirs`, quindi non innescano
  mai il gate. È **configurazione**, non codice, ma è una decisione con effetti reali → promosso a
  **E10-FEAT-063**.
- **Divergenza `ritual-check` ↔ `wiki-guard`**: resta **E10-FEAT-060**.
- **Doppia invocazione di `repo_prefix`** (§3): micro-ottimizzazione, da cogliere in implementazione se
  gratuita, non un obiettivo.
- **Copertura semantica** (la voce parla davvero di quel file): è **giudizio**, fuori dal confine D.

---

## Commit proposto
`docs(requirements): E10-FEAT-062 — la registrazione copre un changeset, non una data (EARS)`
