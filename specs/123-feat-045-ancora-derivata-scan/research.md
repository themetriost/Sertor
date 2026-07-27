# Research — Ancora derivata per la rilevazione del lavoro non registrato

**Feature**: `123-feat-045-ancora-derivata-scan` · **Data**: 2026-07-27

Tutte le decisioni sono state **verificate eseguendo i comandi sul repo reale**, non inferite. I
risultati sono riportati inline: è la lezione di [[dogfood-fidelity]] («leggiamo invece di eseguire»)
applicata in fase di design invece che dopo.

---

## R1 — Quale fatto è l'ancora

**Decisione.** L'ancora è **l'ultima consegna (commit) che ha toccato la cartella di giornale del
wiki**: `git log -1 --format=%H|%cI -- <log_dir>`.

**Rationale.** È il fatto stesso che il proxy cercava di stimare. Sopravvive a `pull`/`merge`/`rebase`/
`checkout`/`clone` perché vive nella storia, non nel filesystem. E il commit trovato è **sempre un
antenato di HEAD** (`git log` cammina solo la storia di HEAD), quindi il confronto a due punti
`<sha> HEAD` è ben definito: non serve `...` (merge-base).

**Verificato:**
```
git log -1 --format='%H|%cI' -- wiki/log/
→ 4292aefc…|2026-07-27T17:33:23+02:00
```

**Alternative scartate.**
- *L'intero wiki root come ancora* — aggiornare una pagina senza scrivere la voce di giornale
  conterebbe come registrazione. Contraddice il rituale («un passo non è chiuso finché commit **e**
  voce di log non sono entrambi fatti») e allargherebbe la semantica senza che nessuno l'abbia chiesto.
- *Il timestamp del commit invece del commit stesso* — funzionerebbe, ma reintrodurrebbe un confronto
  fra orologi: due commit possono avere date non monotone (rebase, cherry-pick, orologi di macchine
  diverse). Il **range di diff** è il fatto; la data è una sua proprietà, buona per l'output, non per
  il calcolo.

---

## R2 — Come si calcola l'insieme in sospeso

**Decisione.** Unione di **due metà**, in due medium diversi:

| Metà | Comando | Risponde a |
|---|---|---|
| **Consegnata** | `git diff --name-only <sha> HEAD` | lavoro committato dopo l'ultima registrazione |
| **Albero di lavoro** | `git status --porcelain` | lavoro scritto e non ancora committato (modificato **e** nuovo) |

**Rationale.** Senza la seconda metà il gate non vedrebbe **mai** il caso per cui esiste: allo `Stop`
il lavoro della sessione è tipicamente ancora non committato. È il requisito emerso scrivendo la spec
(FR-003), assente dal backlog originale.

**Verificato** (albero reale, con i file di questa feature in lavorazione):
```
git status --porcelain
 M specs/123-feat-045-ancora-derivata-scan/spec.md
?? specs/123-feat-045-ancora-derivata-scan/plan.md      ← non tracciato: incluso, giustamente
```

**Nota su `--porcelain` v1:** il formato è **stabile per contratto** (`git status` documenta v1 come
non soggetto a cambiamenti), a differenza dell'output human-readable. I due caratteri di stato + un
path; per i rinomini il campo è `orig -> new` e si prende la **destinazione**.

**Cancellazioni:** un file di lavoro **cancellato** conta come lavoro in sospeso (è una modifica da
registrare). Comparirà dal diff/porcelain con stato `D`; il path non esiste più su disco, quindi il
codice non deve tentare di leggerlo — solo di nominarlo.

---

## R3 — L'esclusione dei file ignorati dal VCS è **gratis** (assorbe E10-FEAT-048)

**Decisione.** Nessun codice dedicato: `git status --porcelain` **esclude di default** i file ignorati
(servirebbe `--ignored` per vederli), e `git diff` opera solo su file tracciati.

**Verificato empiricamente**, perché era il punto su cui non volevo fidarmi della documentazione:
```
echo test > .venv/SCRATCH-TEST.md          # .venv/ è gitignorato
git status --porcelain | grep -c SCRATCH   → 0
```

**Conseguenza.** Il primo rimedio di E10-FEAT-048 («rispettare il `.gitignore`») è **una proprietà
della derivazione**, non una feature da costruire. Il secondo rimedio («nominare i file») lo è
altrettanto: i comandi restituiscono i path, che oggi buttiamo via contandoli.

**Limite dichiarato.** Vale dove c'è il VCS. Sull'ospite non-git l'informazione «ignorato» **non
esiste** — non si simula (FR-014, A-6), si dichiara nella doc utente.

---

## R4 — La registrazione non consegnata, e la sua scadenza

**Decisione.** Una registrazione presente nell'albero di lavoro vale **se e solo se** riguarda la
**partizione del giorno corrente** (`<log_dir>/<oggi>.md`), che sia modificata o non tracciata.
Deciso in `clarify`, vedi *Clarifications* nella spec.

**Rationale.** Necessaria: allo `Stop` nulla è ancora committato, e pretendere una consegna sarebbe un
deadlock di forma nuova. Limitata: senza scadenza, un giornale lasciato non committato spegne il gate
per giorni — rendendo **legittima** la via d'uscita che la feature esiste per togliere.

**Implementazione.** Il profilo ha già `log_partition_path(day)` (`profile.py`): il path della
partizione di oggi è **derivato**, non composto a mano.

**Contromisura all'attrito (FR-004a).** Se esiste una registrazione non consegnata che **non** è di
oggi, la si **nomina con la sua data** e si dichiara che non vale. Senza, chi riceve il blocco vede un
giornale «già modificato» e un gate che blocca lo stesso: diagnosi impossibile.

---

## R5 — Dove vive la macchina git (riuso, non duplicazione)

**Decisione.** Estrarre gli helper git già presenti in `ritual_check.py` in un modulo condiviso del
pacchetto — `wiki_tools/vcs.py` — e farli usare a **entrambi**.

**Rationale.** `ritual_check.py` contiene già `_git`, `_default_base_candidates`, `_resolve_base`,
`_changed_repo_paths`, `_wiki_prefix`. Duplicarli in `scan.py` creerebbe **due copie della stessa
logica**, cioè esattamente la firma del Principio XIV dentro il fix che quel principio motiva. E i due
strumenti oggi **misurano realtà diverse** proprio perché uno deriva e l'altro stima: condividere il
derivatore è il modo di non farli divergere di nuovo.

**Cosa si estrae** (comportamento invariato, solo spostato + reso pubblico al pacchetto):
`_git` (esecuzione che non solleva mai, il chiamante decide) · `_wiki_prefix` (mappa i path di git a
quelli del wiki tramite `git rev-parse --show-prefix`) · il rilevamento «siamo in un repo?».
`_resolve_base`/`_default_base_candidates` restano **specifici di `ritual-check`** (servono il diff
verso il ramo di default, che `scan` non usa): si spostano solo se il modulo li rende più leggibili,
non per completezza.

**Verificato:** `git rev-parse --show-prefix` → vuoto (siamo alla radice del repo), e
`git rev-parse --is-inside-work-tree` → `true`. Il caso wiki-in-sottocartella è già gestito da
`_wiki_prefix`, che riusiamo invece di riscriverlo.

---

## R6 — Forma del contratto: additiva, identificativo invariato

**Decisione.** `wiki.scan/1` **resta la stringa di schema**. Si aggiungono campi:

| Campo | Tipo | Significato |
|---|---|---|
| `anchor_kind` | `"git"` \| `"mtime"` \| `null` | **la natura dell'ancora**, mai desumibile per convenzione |
| `anchor_ref` | `str \| null` | la consegna da cui deriva (solo con `anchor_kind="git"`) |
| `anchor_fallback_reason` | `str \| null` | perché si è ricaduti sul proxy, quando ci si aspettava di derivare |
| `pending_paths` | `list[str]` | **quali** file, non solo quanti (troncato, vedi R7) |
| `pending_truncated` | `int` | quanti path restano fuori dall'elenco |
| `stale_recording` | `str \| null` | partizione non consegnata **di un altro giorno**, se esiste |

`anchor` **resta un timestamp ISO** anche in modalità git (la data del commit ancora): FR-013, un
consumatore che oggi lo legge come istante continua a funzionare.

**Rationale — ed è il punto critico della feature.** I due hook consumatori fanno
`schema != "wiki.scan/1"` → `return` (`wiki-guard.py:101`), cioè **fail-open**. Bumpare la stringa non
romperebbe il gate: lo farebbe **sparire in silenzio** su ogni ospite che aggiorna la libreria ma non
gli asset — nessun errore, nessun breadcrumb, solo sessioni che chiudono sempre. È la quarta forma di
guardia sbagliata distillata su [[esito-sull-host-vs-forma-dell-asset]]. Da qui il vincolo, e una
**guardia anti-regressione** che lo asserisca: non va affidato all'attenzione di chi modificherà.

**Alternativa scartata.** *Bumpare a `wiki.scan/2` e aggiornare gli hook.* Corretto in un mondo dove
tutti aggiornano insieme; qui produce una finestra in cui il gate è assente **e sembra funzionante**.

---

## R7 — Nominare i file senza rompere i messaggi degli ospiti

**Decisione.** I template `strings` dell'ospite continuano a essere renderizzati **come oggi** (`{n}`).
I nomi si **aggiungono in coda** al messaggio renderizzato, con un elenco **limitato a 10** e la coda
dichiarata (`… e altri N`). Se il template dell'ospite contiene il segnaposto `{files}`, lo si
sostituisce **lì** invece di accodare — così chi vuole controllare la posizione può, e chi non sa
nulla del cambiamento non deve fare niente.

**Rationale.** FR-008: l'aggiunta non deve richiedere che l'ospite aggiorni la propria config. Il
limite è leggibilità (A-5): il **conteggio resta sempre esatto**, è l'elenco a essere troncato — e il
troncamento è **dichiarato**, mai silenzioso.

---

## R8 — Politica di ricaduta: dichiarata, non fatale

**Decisione.** Se la derivazione non è possibile, si usa il proxy mtime **dichiarandolo** con un
motivo tipizzato. Tre cause distinte, non un booleano:

| `anchor_fallback_reason` | Quando |
|---|---|
| `not_a_repository` | l'ospite non è sotto controllo di versione (**caso normale**, non un guasto) |
| `git_unavailable` | il comando non è eseguibile nell'ambiente |
| `log_never_committed` | è un repo, ma la cartella di giornale non è mai stata consegnata (ospite nuovo, storia troncata) |

**Rationale.** Un vuoto non tipizzato fa **fabbricare a chi legge un'affermazione falsa** — è la stessa
ragione per cui il contratto di retrieval ha l'assenza tipizzata con tre cause distinte
(`specs/118`). Qui la posta è la stessa: «mtime» senza motivo lascia credere che sia una scelta,
mentre può essere un ripiego.

**Perché non fallire (Principio XII, letto per intero).** Il principio vieta di **silenziare** un
errore, non impone di interrompere: ammette la degradazione graziosa **purché segnalata**. Il
consumatore principale è un gate che per progetto non deve mai intrappolare un turno; sollevare qui
trasformerebbe `not_a_repository` — che è il **funzionamento previsto** su un ospite non-git — in un
guasto. La dichiarazione soddisfa il principio; l'interruzione tradirebbe il Principio X.

---

## R9 — Perimetro invariato (cosa NON cambia)

- **Le esclusioni dell'ospite** (`profile.exclude`) si applicano a **entrambe** le modalità: la
  derivazione non le scavalca (FR-004/A-4). Si riusa `_is_excluded`, già in `scan.py`.
- **`source_dirs`** resta il filtro di pertinenza: un path derivato da git fuori da quelle cartelle non
  è lavoro da registrare.
- **La modalità mtime** resta **byte-per-byte quella odierna** (FR-014), salvo l'aggiunta di
  `anchor_kind`. I test esistenti di `scan` devono passare **senza modifiche**: se ne servisse una,
  vorrebbe dire che il comportamento è cambiato dove non doveva.
