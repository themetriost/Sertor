# Requisiti — `ritual-check` misura un perimetro diverso da `wiki-guard`, e non lo dichiara
<!-- Deriva da: E10-FEAT-060 (epica debito-tecnico) -->

## 1. Contesto e problema (perché)

`sertor-wiki-tools ritual-check` (E10-FEAT-026) esiste per **preparare la dichiarazione di fine step**:
dato lo scope dello step, *trova* i candidati a distillazione e a drift che l'agente poi *giudica*
(confine D↔N). È il lato-scoperta della rete anti-skip del rituale; la sua gemella lato-enforcement è
`wiki-guard`, l'hook `Stop` **bloccante** che poggia su `scan`.

I due strumenti derivano il perimetro da **due domande diverse**:

```python
# src/sertor_core/wiki_tools/ritual_check.py:84 — SOLO il committato
rc, out = run_git(["diff", "--name-only", f"{base}...HEAD"], config_dir)
```

```python
# src/sertor_core/wiki_tools/scan.py:167-223 — committato dall'ancora UNITO all'albero di lavoro
_committed_since(profile, ref)      # diff <ancora> HEAD
_worktree_changes(profile)          # diff HEAD (content-aware) + status --porcelain -z -uall
```

Il rituale prescrive che la voce di giornale si scriva **nello stesso momento del commit**; chi chiude
uno step invoca dunque `ritual-check` **prima** di committare — cioè nella finestra esatta in cui il suo
perimetro è vuoto. Il gate allo `Stop`, che guarda l'albero di lavoro, vede eccome del lavoro e blocca.

**Riscontrato dal vivo il 2026-07-28:** dopo aver riscritto ~100 righe di `CLAUDE.md`,
`ritual-check --base master` ha risposto **0 candidati su tutto**.

**Il tool non sbaglia il calcolo: risponde a un'altra domanda, e tace sulla differenza.** È la stessa
famiglia di [[riuso-che-eredita-il-presupposto]] — un artefatto corretto per la *sua* domanda, usato per
un'altra, coi presupposti che viaggiano invisibili.

## 2. Analisi degli scenari (misurata, non dedotta)

Matrice eseguita su **host git effimeri**, un host per riga, `source_dirs = ["src"]`, invocando la
**CLI** (Principio XI: mai importando `sertor_core`). Harness: `matrix_060.py` in scratchpad.

**Nota sulla fixture, dovuta.** La prima esecuzione dava `pending=1` anche sulla baseline pulita: la
fixture non conteneva **alcun giornale committato**, quindi `scan` ripiegava su mtime
(`anchor_fallback_reason: log_never_committed`) e contava i file del commit iniziale. Numeri veri della
fixture, falsi del prodotto — la «fixture troppo povera» di [[guardia-verde-non-e-una-misura]].
Riparata aggiungendo un giornale al commit di base; da lì `anchor_kind: git` e baseline `pending=0`.

| # | Scenario (stesso contenuto, stato VCS diverso) | `ritual-check` | `scan` | Verdetto |
|---|---|---|---|---|
| **1** | wiki modificato, **committato** sul branch | `pages=2 distill=1 drift=0` | `pending=0` | ✅ corretto |
| **2** | **lo stesso lavoro, non committato** (tracciato) | `pages=0 distill=0 drift=0` | `pending=0` | ❌ **cieco** |
| **3** | pagina **nuova, non tracciata** | `pages=0 distill=0 drift=0` | `pending=0` | ❌ **cieco** |
| **4** | solo `src/` modificato, non committato | `pages=0 distill=0 drift=0` | **`pending=1`** | ❌ **il caso riscontrato** |
| **5** | misto: A committato, **B modificato non committato** | `pages=1 distill=0 **drift=1**` | `pending=0` | ❌ **falso positivo** |
| **6** | albero pulito, nessun lavoro (baseline) | `pages=0 distill=0 drift=0` | `pending=0` | ✅ corretto |

### 2.1 Il confronto 1 ↔ 2 isola la causa

Righe 1 e 2 hanno **contenuto identico**; l'unica differenza è `git commit`. Il candidato a distillazione
**esiste o non esiste a seconda dello stato VCS**, non del contenuto. Il commit non è un fatto di
conoscenza: è un fatto di bookkeeping.

### 2.2 Il caso 4 è quello riscontrato dal campo

`scan` dice `pending=1` (il gate `Stop` **blocca**), `ritual-check` dice `0 candidati su tutto` —
letteralmente *«non c'è niente da dichiarare»*. Lo strumento che deve **preparare** la dichiarazione è
muto proprio mentre il gate esige quella dichiarazione.

### 2.3 Il caso 5 è il peggiore, e non era nella riga d'epica

Con A committata e B modificata-ma-non-committata, `ritual-check` emette:

```json
{"page": "experiments/b.md", "signal": "neighbor-of-change",
 "detail": "linked from changed page experiments/a.md, not itself updated"}
```

B **è** stata aggiornata — è la pagina appena riscritta. Il `detail` afferma sul contenuto dell'albero
una cosa **falsa**. Nello stesso passaggio il candidato a distillazione, presente sulla riga 1 con lo
stesso contenuto, **sparisce** (`distill=0`), perché il nuovo backlink di B è invisibile.

**Il difetto ha quindi due facce, non una:** omissione silenziosa **e** positivo fabbricato. La seconda è
più dannosa, perché manda l'agente a controllare per drift esattamente la pagina che ha appena scritto —
e consuma la fiducia nello strumento nel modo più rapido possibile.

### 2.4 Sintesi causale

Una sola causa (perimetro committato-solo) produce tre effetti distinti: **(a)** candidati mancanti,
**(b)** candidati falsi, **(c)** nessuna traccia, nell'output, di quale realtà sia stata misurata.
Il rimedio deve chiudere tutti e tre: **(a)** e **(b)** allineando il perimetro, **(c)** dichiarandolo.

## 3. Un secondo difetto, nello stesso file (Principio XII)

`ritual_check.py:256-262` interroga git per le pagine **aggiunte**:

```python
rc, out = run_git(["diff", "--name-only", "--diff-filter=A", f"{base_ref}...HEAD"], config_dir)
if rc == 0:
    ...   # se rc != 0, added_pages resta VUOTO, in silenzio
```

Se git non risponde, `added_pages` resta vuoto senza che nulla lo dichiari; `has_new_distill_page`
diventa `False` e il candidato a distillazione viene emesso **come se non avessi distillato**. È la
stessa classe del difetto R1 di E10-FEAT-062 — *un'invocazione git che fallisce degrada verso l'insieme
vuoto in silenzio* — e viola il Principio XII (*Fail Loud, Fix the Cause*).

Incluso in questo lavoro per la **regola del boy scout** (E10-FEAT-059): la guardia trova rotto
nell'area che si sta toccando, si aggiusta nello stesso passaggio.

## 4. Obiettivi e criteri di successo

| ID | Criterio | Come si verifica |
|----|----------|------------------|
| **SC-001** | Sugli scenari **2, 3, 4, 5** della matrice §2, `ritual-check` riporta lo stesso insieme di candidati che riporterebbe **a parità di contenuto committato** | ri-esecuzione della matrice: righe 1 e 2 devono dare esiti **identici** |
| **SC-002** | Il falso `neighbor-of-change` dello scenario 5 **non viene più emesso** | asserzione dedicata sullo scenario 5 |
| **SC-003** | Ogni output (JSON **e** summary umano) dichiara **quale perimetro** ha misurato e **quanto** ha contribuito ciascuna sorgente | test sul contratto JSON + test sul summary umano |
| **SC-004** | Nessuna invocazione git che fallisce può produrre un insieme vuoto silenzioso | test che simula il fallimento di **ciascuna** invocazione git e attende un errore dichiarato |
| **SC-005** | Un file **ignorato dal VCS** non entra mai nel perimetro | test dedicato (eredita la semantica di E10-FEAT-048) |
| **SC-006** | Una differenza di **soli fine-riga** non produce candidati | test dedicato (eredita la lezione *content-aware* di `scan.py:191-195`) |

**SC-001 è falsificabile e va calcolato, non affermato:** la matrice §2 è lo strumento di misura, e le
righe 1↔2 sono il paragone che rende l'esito un numero.

## 5. Forma del rimedio (cosa, non come)

Decisione utente (2026-07-30): **allineare il perimetro E dichiararlo**, non l'uno o l'altro.

1. **Perimetro allineato.** Lo scope di uno step è l'**unione** di: (a) il committato `base...HEAD` e
   (b) le modifiche dell'albero di lavoro, derivate con la **stessa semantica** già consegnata in
   `scan._worktree_changes` — diff tracciato *content-aware* vs `HEAD` più i non-tracciati con `-uall`.
2. **Perimetro dichiarato.** L'output riporta, in forma leggibile e nel JSON, **quali** sorgenti hanno
   contribuito e con quanti path — così un disallineamento futuro è **visibile**, non deducibile.
3. **Fail-loud uniforme.** Ogni invocazione git che fallisce produce un errore dichiarato, mai un
   insieme vuoto silenzioso.

**Non è in questa forma** l'unificazione della derivazione in un modulo condiviso fra `scan` e
`ritual_check` (opzione valutata e **non scelta**): toccherebbe un modulo che oggi regge un gate
bloccante su ogni ospite. Vedi §11.

## 6. Requisiti funzionali (EARS)

### Perimetro

- **REQ-001** — Il sistema DEVE derivare il perimetro di uno step come **unione** del changeset
  committato (`base...HEAD`) e delle modifiche non consegnate dell'albero di lavoro.
- **REQ-002** — QUANDO una pagina del wiki è modificata ma **non ancora committata**, il sistema DEVE
  includerla nelle pagine in scope.
- **REQ-003** — QUANDO una pagina del wiki è **nuova e non tracciata**, il sistema DEVE includerla nelle
  pagine in scope e trattarla come pagina **aggiunta** nello step.
- **REQ-004** — DOVE una pagina nuova non tracciata risieda in una cartella-casa della distillazione
  (`concepts/`/`tech/` da tassonomia), il sistema DEVE considerarla come «nuova pagina di distillazione»
  ai fini della soppressione del candidato — al pari di una pagina aggiunta e committata.
- **REQ-005** — Il sistema DEVE derivare le modifiche tracciate dell'albero in modo **content-aware**:
  un file la cui unica differenza è la normalizzazione dei fine-riga NON DEVE entrare nel perimetro.
- **REQ-006** — Il sistema NON DEVE far entrare nel perimetro i path **ignorati dal VCS**.
- **REQ-007** — QUANDO l'utente fornisce `--pages`, il sistema DEVE usare quell'insieme esplicito come
  perimetro, senza unirvi né il committato né l'albero di lavoro.

### Dichiarazione del perimetro

- **REQ-008** — Il sistema DEVE riportare nell'output JSON quali sorgenti hanno composto il perimetro e
  **quanti path** ciascuna ha contribuito.
- **REQ-009** — Il sistema DEVE riportare la stessa informazione nel **summary umano**, non solo nel JSON:
  è il summary che l'agente e la persona leggono.
- **REQ-010** — QUANDO il perimetro proviene da `--pages`, il sistema DEVE dichiararlo esplicitamente
  come perimetro fornito dall'utente.
- **REQ-011** — Il sistema DEVE mantenere l'identificativo di contratto `wiki.ritual_check/1`,
  estendendone lo schema in modo **additivo**.

### Fail-loud (Principio XII)

- **REQ-012** — SE una qualunque invocazione git necessaria alla derivazione del perimetro fallisce,
  ALLORA il sistema DEVE segnalare l'errore in modo dichiarato e NON DEVE proseguire con un insieme
  parziale o vuoto presentato come completo.
- **REQ-013** — SE la determinazione delle pagine **aggiunte** fallisce, ALLORA il sistema NON DEVE
  trattare il risultato come «nessuna pagina aggiunta».
- **REQ-014** — SE lo scope non è determinabile (nessun git e nessun `--pages`), ALLORA il sistema DEVE
  fallire in modo esplicito, come già fa oggi.

### Invarianti da non rompere

- **REQ-015** — Il sistema DEVE restare **sola lettura, zero-LLM, offline**.
- **REQ-016** — Il sistema DEVE restare **host-agnostico**: scope, tassonomia e soglie continuano a
  provenire da `wiki.config.toml`, e il branch di default continua a essere **rilevato a runtime**
  (E10-FEAT-033), mai assunto.
- **REQ-017** — Il sistema DEVE continuare a **trovare** senza **giudicare**: nessuna pagina creata,
  nessun drift corretto (confine D↔N, Principio XI).

## 7. Requisiti non funzionali

- **NFR-001** — Costo: l'aggiunta non DEVE introdurre più di **due** invocazioni git per esecuzione
  (`diff HEAD` e `status --porcelain`), le stesse che `scan` già paga.
- **NFR-002** — Determinismo: a parità di albero, due esecuzioni DEVONO produrre lo stesso output.
- **NFR-003** — L'ordine dei path in output DEVE essere stabile (ordinamento esplicito), perché l'output
  finisce in una dichiarazione che viene diffata.

## 8. Vincoli, assunzioni e dipendenze

- **V-1** — Il contratto `wiki.ritual_check/1` **non ha consumatori programmatici**: lo citano il
  playbook e le `specs/`. Verificato il 2026-07-30 (`grep` su tutto il repo). Quindi il vincolo critico
  di E10-FEAT-062 — *non bumpare, i consumatori confrontano per uguaglianza e vanno in fail-open* — **qui
  non si applica**. Si estende comunque in modo additivo (REQ-011) per prudenza.
- **V-2** — `ritual-check` è **distribuito agli ospiti** col sistema-wiki (viaggia in `sertor-core`):
  è installabile per costruzione, ma la sua **descrizione** host-facing va riallineata (§10).
- **A-1** — Si assume che la semantica di derivazione dell'albero di lavoro consegnata in `scan`
  (content-aware + `-uall` + `None` invece di `[]`) sia **corretta e collaudata**: è in produzione dalla
  v0.3.2/v0.4.0 e confermata dal campo. Questo lavoro la **riusa**, non la ridiscute.
- **D-1** — Nessuna dipendenza da feature non consegnate.

## 9. Rischi

| ID | Rischio | Mitigazione |
|----|---------|-------------|
| **R-1** | **Più rumore**: l'albero di lavoro contiene anche modifiche accidentali, quindi i candidati aumentano e il segnale si diluisce | La soglia hub (`hub_threshold`) esiste già per questo; misurare il delta di candidati sul dogfood **prima** di chiudere |
| **R-2** | Il `detail` dei candidati oggi dice «changed page X» senza distinguere committato da non committato: unendo le sorgenti, un messaggio ambiguo diventa **fuorviante** | La dichiarazione del perimetro (REQ-008/009) è anche il rimedio a questo |
| **R-3** | Riuso della semantica di `scan` **per copia** anziché per estrazione → le due possono divergere di nuovo, ed è esattamente il difetto che stiamo chiudendo | Accettato consapevolmente (§5); tracciato come debito in §11, con un test che confronta i due perimetri |
| **R-4** | Un test che «pianta» il fallimento di git può passare **gratis** se la fixture non può fallire | Ogni test di REQ-012/013 deve mostrare l'errore atteso, non solo un `assert` verde ([[guardia-verde-non-e-una-misura]]) |

## 10. Domande aperte (da sciogliere in `clarify`, non da assumere)

- **DA-1** — Serve un'opzione per **restringere** il perimetro al solo committato (es. `--committed-only`)
  per il caso «cosa ha cambiato questo branch»? Oppure è YAGNI finché nessuno lo chiede?
- **DA-2** — Il perimetro unito deve entrare **anche** nel confronto dei backlink «nuovi»
  (`_links_at(base, ...)`)? Per una pagina non tracciata `git show base:path` fallisce e tutti i suoi
  link risultano nuovi — comportamento probabilmente corretto, ma va **dichiarato** invece che ereditato.
- **DA-3** — Il summary umano deve dichiarare il perimetro **sempre**, o solo quando è composito? Sempre
  costa una riga a ogni invocazione; solo-quando-composito reintroduce un silenzio nel caso semplice.

## 11. Fuori ambito (promossi, non sepolti)

Secondo la regola 2 del `CLAUDE.md` — *gli «Out of Scope» si promuovono, non restano appesi*:

- **Unificare la derivazione del perimetro in un modulo condiviso** fra `scan` e `ritual_check`, così che
  la divergenza sia impossibile per costruzione anziché corretta una volta. Valutata e **non scelta** qui
  perché toccherebbe `scan.py`, che regge un gate bloccante su ogni ospite. → **promossa il 2026-07-30 a
  `E10-FEAT-066`** (Could/P2) nel backlog dell'epica, con la mitigazione più economica già nominata: un
  **test di equivalenza** che confronta i due perimetri sullo stesso albero (R-3).
- **Il perimetro di `scan` esclude `packages/` e i file di radice** (`source_dirs`) — problema reale ma
  **distinto**, già tracciato: **E10-FEAT-063**. Citato, non duplicato.

## Commit proposto

```
docs(requirements): il perimetro di ritual-check non e' quello del gate, e non lo dichiara

E10-FEAT-060. Matrice misurata su host git effimeri: a parita' di contenuto,
il candidato a distillazione esiste o meno a seconda del solo stato VCS, e il
caso misto emette un candidato drift FALSO sulla pagina appena riscritta.
```
