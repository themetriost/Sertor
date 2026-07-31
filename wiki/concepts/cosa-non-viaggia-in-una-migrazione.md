---
title: Cosa non viaggia quando sposti un sottoalbero
type: concept
tags: [migrazione, git, filter-repo, separazione, trappole, e15]
created: 2026-07-31
updated: 2026-07-31
sources: ["specs/127-separazione-quattro-prodotti/migration-plan.md", "specs/127-separazione-quattro-prodotti/file-inventory.md", "wiki/log/2026-07-31.md"]
---

# Cosa non viaggia quando sposti un sottoalbero

Estrarre una cartella in un repo proprio sembra un'operazione di **spostamento**: prendo i file, li
metto altrove, aggiorno i riferimenti. La prima migrazione reale (ProtoSertor, 2026-07-31) ha mostrato
che è invece un'operazione di **ricostruzione** — e che le cose che non arrivano non danno errore:
danno un repo che sembra completo e non lo è.

> **La firma comune alle cinque trappole:** nessuna produce un fallimento. Producono un repo che si
> clona, si apre, si legge — e che è **inerte, monco o contaminato** in un modo che si scopre solo
> usandolo.

## Le cinque, tutte incontrate in una sola migrazione

### 1. Ciò che `.gitignore` esclude non esiste per git

Il prototipo aveva **973 file / 34 MB** di corpus sotto `raw/`, di cui git tracciava **un solo
README**. `filter-repo` porta la storia di git: il corpus non l'avrebbe seguita, e il repo nuovo
sarebbe nato **eseguibile in apparenza e vuoto nei fatti**.

**Regola:** prima di migrare, confronta `git ls-files <dir> | wc -l` con `find <dir> -type f | wc -l`.
Se i numeri divergono, la differenza è materiale che devi trasportare **fuori da git**, e va reso uno
step a sé con verifica numerica — non una nota a piè di pagina.

### 2. Il `.gitignore` stesso non viaggia

Vive in radice, quindi non è dentro il sottoalbero che stai estraendo. Il repo nuovo nasce **senza**,
e il primo `git add` ci mette dentro tutto ciò che l'originale escludeva — inclusi i 34 MB del punto 1.

**Regola:** i file di configurazione della radice (`.gitignore`, `.gitattributes`, `.env.example`,
`pyproject.toml`) **non sono nel sottoalbero e servono al sottoalbero**. Vanno ricreati, non copiati:
i loro pattern erano scritti col prefisso della cartella.

### 3. Una rinomina spezza la storia in due, e `--path` ne vede metà

`git filter-repo --path prototype/` sembra la scelta ovvia. Preservava **3 commit su 34**: la cartella
`prototype/` esiste solo da quando il codice fu isolato, e prima quegli stessi file vivevano in radice.
La storia vera — dalla nascita del progetto — sta sotto i **path precedenti**.

**Regola:** `git log --oneline -- <dir> | wc -l` prima di migrare. Se il numero è sospettosamente
basso, cerca la rinomina (`git show --stat <commit-di-isolamento> | grep "=>"`) e includi **anche i
path vecchi**.

### 4. I path vecchi possono collidere col presente

Includere i path vecchi ha un rovescio: alcuni di quei nomi **oggi appartengono a qualcun altro**. Nel
caso reale, `wiki/`, `tests/`, `README.md` e `.env.example` erano del prototipo nel maggio 2026 e sono
del prodotto adesso — includerli avrebbe portato **547 e 139 commit di produzione** dentro il repo nuovo.

**Regola:** ogni path vecchio va verificato contro la radice di **oggi** (`[ -e <path> ]`). Quelli che
collidono si escludono, accettando per quei file una storia che parte dalla rinomina — e la rinuncia
si **dichiara**, non si subisce. *La quarta collisione (`.env.example`) è emersa solo facendo questo
controllo, dopo che l'elenco era già stato scritto.*

### 5. Il clone locale usa hardlink, e la protezione che lo dice sembra un ostacolo

`git clone` di un repo sulla stessa macchina **non copia** gli oggetti: li collega. `filter-repo` si
rifiuta di lavorarci — *«does not look like a fresh clone»* — e suggerisce due vie: `--no-local` (copia
reale) oppure `--force`.

> **`--force` non rimuove il pericolo, rimuove l'avviso.** Riscrivere la storia su oggetti condivisi
> per hardlink può intaccare **il repo sorgente**: quello che stai cercando di non toccare.

**Regola:** `git clone --no-local`. È la stessa classe di [[guardia-verde-non-e-una-misura]] vista dal
lato opposto — lì una verifica taceva senza poter fallire, qui una verifica parla e la tentazione è
zittirla.

## Il criterio che tiene insieme le cinque

Una migrazione riuscita non si verifica chiedendo *«ha funzionato?»* — ha sempre funzionato, è un
comando che esce 0. Si verifica con **due domande numeriche**, poste sul risultato:

1. **I file sono esattamente quelli attesi?** `diff` fra l'elenco atteso e `git ls-files` del repo
   nuovo. Non «circa 90»: identici.
2. **È entrato qualcosa che non doveva?** Un grep sui prefissi del progetto sorgente
   (`src/`, `packages/`, `specs/`) che **deve dare zero**.

La seconda è quella che nessuno pensa a fare, perché cerca ciò che non ci si aspetta. È l'unica che
distingue un'estrazione **pulita** da una che ha funzionato **portandosi dietro** qualcosa.

## Parenti

- [[confine-di-prodotto-misurato]] — *dove* passa il confine (misura, non deduzione). Questa pagina è
  il seguito operativo: *come* si attraversa senza perdere pezzi.
- [[esito-sull-host-vs-forma-dell-asset]] — verificare l'**esito**, non la forma del comando eseguito.
- [[guardia-verde-non-e-una-misura]] — una protezione che parla va ascoltata, non messa a tacere.
