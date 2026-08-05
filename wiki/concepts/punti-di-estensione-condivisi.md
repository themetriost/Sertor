---
title: I punti di estensione condivisi non hanno un proprietario
type: concept
tags: [installer, proprieta, asset, upgrade, uninstall, host, e10, principio-x]
created: 2026-08-05
updated: 2026-08-05
sources: ["packages/sertor/src/sertor_installer/install_rag.py", "packages/sertor-install-kit/src/sertor_install_kit/lifecycle.py", "requirements/debito-tecnico/epic.md"]
---

# I punti di estensione condivisi non hanno un proprietario

Il nostro modello di proprietà degli artefatti è **binario**: un file è *nostro* (`owned_files` — lo
scriviamo, lo aggiorniamo, alla disinstallazione lo togliamo) oppure è *dell'ospite con un nostro
innesto* (`shared_edits` — ci fondiamo dentro un blocco delimitato e lasciamo intatto il resto).

Il mondo ha un **terzo caso**, e non ha una casella: i file che non appartengono a nessuno perché
sono **punti di estensione** — luoghi dove strumenti indipendenti dichiarano regole che devono
**coesistere**. `.gitattributes` è esattamente questo: git-crypt, git-lfs, i filtri di redazione e la
nostra normalizzazione dei fine-riga ci scrivono tutti, nessuno lo possiede.

Classificarlo come *nostro* non è un errore di battitura: è **dichiarare che gli altri non esistono**.

## Come si è visto (2026-08-02, nodo VM-WorkingFolder)

Un ospite cifrava il proprio repository con **git-crypt**, dichiarato interamente in `.gitattributes`.
Il nostro `upgrade rag` ha sostituito il file con la propria versione. Il repository **ha smesso di
essere cifrato**: 195 file scritti in chiaro negli oggetti git, per tre commit e nove giorni, prima
che qualcuno se ne accorgesse — e se ne è accorto **per caso**, diagnosticando tutt'altro.

Nulla ha lasciato la macchina, ma per fortuna: il branch non era stato pushato, e la convenzione che
lo teneva locale era stata rimossa mesi prima.

## Le tre asimmetrie che lo rendono difficile da vedere

### 1. La proprietà sbagliata è innocua nel verbo che esercitiamo di più

La `WriteStrategy` dichiarata nel piano è onorata **dal solo ramo INSTALL**:

| Verbo | Cosa fa a un file preesistente | Effetto di una proprietà sbagliata |
|---|---|---|
| `install` | `PRESENT_DIVERGENT` — lo lascia intatto | **nessuno**: la classificazione non viene esercitata |
| `upgrade` | `update_file_if_changed` — **sovrascrive** | il contenuto dell'ospite sparisce |
| `uninstall` | è in `owned_files` → **cancella** | il file dell'ospite sparisce del tutto |

`install_rag.py` dichiara `WriteStrategy.CREATE_IF_ABSENT` per `.gitattributes` e lo commenta
*«non-destructive — a host that already owns a `.gitattributes` keeps its own»*. **È vero per un verbo
su tre.** Il ramo `UPGRADE` non guarda la `WriteStrategy`: dispatcha sul solo `ArtifactKind`, e ogni
`FILE` viene riscritto.

Conseguenza operativa: **un test d'installazione non dice nulla sulla correttezza di una
classificazione di proprietà.** Per esercitarla serve un host con un'installazione **preesistente**
— la stessa condizione che rende invisibili sul dogfood 7 difetti d'installer su 7
([[esito-sull-host-vs-forma-dell-asset]]).

### 2. Il danno è silenzioso *per natura*, non per una svista

Non c'è un rilevatore da aggiungere: togliere le righe di un filtro da `.gitattributes` non produce
errore, warning né exit code diverso da zero. **Git smette di applicare il filtro e committa in
chiaro, riuscendo.** Il solo strumento che lo dice è `git-crypt status`, che nessuno ha motivo di
lanciare in una sessione qualsiasi.

È una differenza di categoria rispetto ai difetti che *falliscono*: qui il sistema fa esattamente ciò
che gli è stato chiesto, e ciò che gli è stato chiesto è sbagliato.

### 3. Il difetto seleziona chi segue la disciplina

Perché si manifesti serve un ospite che abbia **già** un `.gitattributes` proprio, **con dentro
qualcosa che conta**. Cifrare il proprio repository è precisamente ciò che fa un ospite attento: il
difetto non colpisce a caso, colpisce **i più curati**. È la stessa forma già osservata altrove — e la
ragione per cui un campione di host puliti non è un campione.

## La regola

> **Se un terzo può legittimamente scrivere in un file, l'unica operazione corretta è la fusione.**
> Non «sovrascrivere con cautela», non «sovrascrivere avvisando»: fondere.

E se fondere non è praticabile, il ripiego non è sovrascrivere in silenzio — è **dichiarare di non
aver toccato**: `skipped … contiene dichiarazioni di terzi`. *Uno `skipped` dichiarato vale
infinitamente più di un `updated` silenzioso.*

Su `.gitignore`, `CLAUDE.md`, `settings.json` e `.mcp.json` **facciamo già così** (`SharedEdit`), e
infatti non abbiamo mai avuto problemi. La domanda non è quindi «come si fa», che sappiamo: è **perché
un file è finito nella colonna sbagliata**, e la risposta è che la classificazione è un **giudizio
espresso una volta sola** nel plan-builder, come letterale, **senza alcuna guardia che chieda: questo
file può contenere roba d'altri?**

## Corollario per chi scriverà il manifesto dichiarativo

La fase F2 della separazione trasforma i piani-in-codice in **dati dichiarativi**
(`node.manifest.v1.json`). Una classificazione di proprietà sbagliata, oggi, è una riga di Python che
si può leggere accanto al suo commento; domani sarà un campo in uno schema. **La correttezza va nello
schema, non nella riga:** se il manifesto ammette solo `owned` e `shared`, il terzo caso resterà senza
casella e continuerà a essere classificato per approssimazione — cioè male, e in un formato che rende
l'errore ancora meno visibile.

## Vedi anche

- [[esito-sull-host-vs-forma-dell-asset]] — perché la forma dell'asset non dice l'esito sull'host, e
  perché serve un ospite che *aggiorna*.
- [[identita-per-presenza-o-per-contenuto]] — l'altra metà del problema di proprietà: su **quale**
  identità si decide che «c'è già».
- [[guardia-verde-non-e-una-misura]] — un verde risponde a «è andata bene?», non a «ha guardato?».
- [[dogfood-fidelity]] — il dogfood non può contenere questo difetto: non ha un filtro git.
- Tracciato come **E10-FEAT-068** in [`requirements/debito-tecnico/epic.md`](../../requirements/debito-tecnico/epic.md).
