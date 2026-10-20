---
title: Come si rilascia Sertor — procedura ricostruita da 17 release
type: synthesis
tags: [rilascio, release, processo, gate-aggiornamento, note-di-rilascio, acta, handoff, sinthari]
created: 2026-10-13
updated: 2026-10-13
sources:
  - CHANGELOG.md
  - wiki/log/2026-07-13.md … wiki/log/2026-10-12.md
  - .github/workflows/upgrade-smoke-full.yml
  - .github/workflows/ci.yml
  - tests/integration/test_host_smoke.py
  - CLAUDE.md (policy A-15, gate d'aggiornamento, congelamento installazione)
---

# Come si rilascia Sertor

> **A chi serve.** È la procedura di rilascio di Sertor **ricostruita dai fatti**: le 17 release
> pubblicate fra il 2026-07-13 (`v0.1.0`) e il 2026-10-12 (`v0.6.0`), con gli incidenti che hanno
> prodotto ciascuna regola. Ha due lettori:
> - **noi**, come riferimento operativo al prossimo rilascio;
> - **Sinthari**, il nodo che crea skill e agenti, come **specifica di partenza per una skill di
>   rilascio**. La §9 separa ciò che è proprio di Sertor da ciò che vale per qualunque nodo, e la §10
>   propone una forma per la skill, che resta una decisione di Sinthari.
>
> Ogni regola porta la release o la data in cui è nata. Le regole senza origine sono le prime a
> essere scartate come cerimonia, e qui ognuna è costata almeno un difetto.

## 1. Cosa significa «rilasciare», qui

Un rilascio **non** è il tag e non è la GitHub Release. È il momento in cui una correzione o una
capacità diventa **raggiungibile per la popolazione di ospiti che segue le versioni**. Tre fatti lo
definiscono:

1. **Il bump di `/VERSION` su `master` è il rilascio, per gli ospiti.** L'avvisatore d'aggiornamento
   (E2-FEAT-013) legge `/VERSION` direttamente da `master` su GitHub. Appena il bump arriva su
   `master`, ogni ospite riceve «c'è una versione nuova», prima che esistano il tag e la Release.
   Tag, Release e annuncio sono la parte **umana** del rilascio, ma il **trigger** parte col merge del
   bump. *(Scoperto in `v0.3.3`, 2026-07-29: avevo detto all'utente «nulla è rilasciato finché non
   dai il go», ed era falso.)*
   **Conseguenza:** ogni punto di arresto («non rilasciare finché…») va messo **prima del merge del
   bump**, non prima del tag.
2. **Un rimedio raggiunge una popolazione, non un difetto.** Una correzione su `master` che nessuna
   release porta è **irraggiungibile** per chi è agganciato a un tag. Caso reale: il tetto `mcp<2` è
   rimasto su `master` per **37 giorni** senza release (`git tag --contains dd76dc3` vuoto), e due nodi
   hanno perso il server MCP per 34 e 36 giorni. Rilasciare fa parte della correzione, non è un passo
   successivo. Vedi [[difetto-che-solo-un-ospite-nuovo-puo-vedere]].
3. **Si rilascia solo ciò che l'utente deve prendere.** Policy **A-15** (2026-07-10): `/VERSION` è
   SemVer con **bump manuale**, solo per una release user-facing, mai a ogni merge. Il tracciamento
   per-merge lo fa il dogfood, il cui runtime segue HEAD. Un `/VERSION` fermo mentre i commit avanzano
   **non è deriva**. Il bump automatico da conventional commit è stato scartato come YAGNI.

**Patch o minor?** È patch se la release contiene solo correzioni e pratiche, senza capacità nuove.
È minor se c'è una capacità o un comportamento nuovo per l'ospite, oppure un cambio di forma
dichiarato. Esempi:
- `v0.2.0`: flusso del grafo in `search_combined`, payload cambiato;
- `v0.3.0`: un principio costituzionale distribuito;
- `v0.4.0`: la registrazione dichiara cosa copre;
- `v0.5.0`: provider `openai`;
- `v0.6.0`: pagine ASP.NET.

La regola dichiarata in `v0.4.0` è: *chiamarla patch avrebbe detto «solo correzioni», ed era falso*.
Il numero comunica il contenuto. L'utente può scegliere diversamente per ragioni di linea:
`v0.4.1` invece di `0.5.0` per tenere stabile la linea 0.4.x.

## 2. La storia in una tabella

| Release | Data | Tipo | Contenuto | Incidente → regola che ne è nata |
|---|---|---|---|---|
| `v0.1.0` | 07-13 | prima | baseline pubblica | tag *lightweight* (l'unico); CHANGELOG e pin `@v0.1.0` arrivati il giorno dopo → **commit di rilascio unico** con bump, CHANGELOG e pin |
| `v0.1.1` | 07-20 | patch | affidabilità | tag su un merge di docs successivo → **il tag va sul merge della PR di rilascio** |
| `v0.1.2` | 07-21 | patch | memoria conversazioni | un fix entrato dopo la PR di rilascio, tag spostato per includerlo |
| `v0.1.3` | 07-22 | patch | pavimento del distill | merge delegato segnalato come «non autorizzato» → **il merge richiede il go esplicito** |
| `v0.1.4` | 07-23 | patch | wiki-guard | — |
| `v0.1.5` | 07-23 | patch | doppio cablaggio dello `Stop` | trovato aggiornando il dogfood **col vero installer** due ore dopo la 0.1.4 → **aggiornare il dogfood come un ospite trova difetti** |
| `v0.2.0` | 07-24 | minor | grafo in `search_combined` + fix installer | comando d'aggiornamento pubblicato rotto (`uvx --refresh sertor`) → **comandi nella forma `#subdirectory=`**; CI di `master` rossa dal merge e nessuno l'ha vista → **CI di `master` verde prima del tag** |
| `v0.2.1` | 07-25 | patch | riparazioni dal campo | note che presentavano un difetto condizionale come universale (E10-FEAT-050) → **un difetto si pubblica con le condizioni in cui morde** · «prima il rilascio, poi le comunicazioni» |
| `v0.3.0` | 07-26 | minor | Principio XIV distribuito | annuncio che confondeva «0.3.0» dello starter con la release; EXEC che citava il merge del contenuto invece del commit del tag → **verificare il corpo pubblicato contando i frammenti** |
| `v0.3.1` | 07-26 | patch | upgrade per chi pinna | segnalato da Acta poche ore dopo la 0.3.0 → **le note nominano il difetto ancora aperto** |
| `v0.3.2` | 07-27 | patch | gate wiki riparato | `gh … --json isLatest` non esiste in questa versione della CLI, quindi la verifica sarebbe «passata» in silenzio → **`latest` si chiede all'API `releases/latest`** |
| `v0.3.3` | 07-29 | patch | lint che non grida al lupo | **il trigger era già partito col bump** (§1.1); data nel CHANGELOG ≠ data del tag |
| *vincolo* | 07-29 → 07-30 | — | nessun rilascio senza gate d'aggiornamento | sciolto quando E15-FEAT-012 è stata consegnata |
| `v0.4.0` | 07-30 | minor | la registrazione dichiara cosa copre | comandi `sertor upgrade wiki` non eseguibili (non sono nel `PATH`) e perimetro non dichiarato → **`gh release edit` + rettifica pubblica**, mai correzione silenziosa |
| `v0.4.1` | 07-31 | patch | `ritual-check` misura il non committato | il blocco `CLAUDE.md` dichiarava ancora attivo il vincolo sciolto → **il testo di un vincolo non deve diventare una copia stantia** |
| `v0.4.2` | 09-13 | patch | server MCP su entrambe le linee dell'SDK | tag creato **20 minuti dopo l'ultimo run verde**; il rilascio ha cancellato la precondizione di un esito del gate, e `master` è diventato rosso (E10-FEAT-078) · note con **quattro comandi per tutti**, uno dei quali installa `sertor-flow` dove non c'era (E10-FEAT-081) |
| `v0.5.0` | 10-07 | minor | provider `openai` | smoke saltato sulla PR (il filtro dei percorsi esclude `src/`) → **il gate completo gira su `master` prima del tag** |
| `v0.6.0` | 10-12 | minor | pagine ASP.NET + chunking dentro namespace | note **per assistente** (Claude usa alias, Copilot ID fissi) · `_logic_version` cambiato → **re-index obbligatorio dichiarato** |

## 3. La procedura, fase per fase

Ogni fase ha un **criterio d'uscita verificabile**. Un passo si dichiara fatto quando la prova sta
in un file, in un comando o in un'API, non quando lo si ricorda (direttiva 2026-07-29).

### F0 — Decidere se, cosa e quanto

- **Cosa c'è da rilasciare:** `git log <ultimo-tag>..master`. Se nulla cambia per l'ospite, non si
  rilascia (A-15).
- **Perimetro misurato, per pacchetto:** `git diff --stat <ultimo-tag>..master -- <pacchetto>` per
  ciascun pacchetto distribuito: `src/` (`sertor-core`, cioè runtime e capability `rag`),
  `packages/sertor`, `packages/sertor-install-kit`, `packages/sertor-flow`, asset bundlati. Il
  perimetro decide **quali comandi servono a chi** (F1). Non si scrive a memoria.
- **Tipo** (patch/minor, §1) e **titolo** della release.
- **Vincoli attivi?** Leggere il blocco EXEC di `wiki/syntheses/roadmap.md` e la sezione dei vincoli
  di `CLAUDE.md`. Se un vincolo è attivo, ci si ferma **prima del bump** (§1.1).
- **Autorizzazione:** «rilascia» / «rilasciamo» dell'utente autorizza la **catena completa**, inclusa
  `gh release create --latest` sul repo pubblico. **Non** copre il merge di una PR, che richiede
  sempre un go esplicito.

**Uscita:** versione, tipo, perimetro per pacchetto e go dell'utente.

### F1 — Il commit di rilascio

Un **unico commit** sul branch della feature o su un branch di rilascio, che contiene:

1. `/VERSION` → `X.Y.Z`.
2. `CHANGELOG.md`: una sezione `## [X.Y.Z] — <data>` sotto `[Unreleased]` (struttura in §4).
3. **I pin d'installazione** `@vX.Y.Z` in `README.md`, `docs/getting-started.md` e negli altri punti
   della doc utente che citano la versione. Dimenticarli è già successo (`v0.1.0`), e una volta il pin
   di stabilità è rimasto indietro di quattro release.
4. **Doc utente** aggiornata per ogni capacità o manopola nuova (`docs/install.md`, tabella capability):
   regola standing 3 di `CLAUDE.md`.
5. **Stato:** EXEC della roadmap, riga ✅ nell'`epic.md`, `CLAUDE.md` senza «piano attivo».

**Uscita:** `git show --stat` del commit contiene tutti e cinque i punti.

### F2 — Gate pre-merge locale

- `uv run pytest -m "not cloud"` sulla **suite completa**, più le suite dei pacchetti, più
  `uv run ruff check .`, **sullo stato finale**: non run mirati, non run vecchi (`v0.2.0`). Il gate
  reale sono **tutte** le suite: a luglio quello documentato copriva 1385 test, quello vero 2517.
- Se sono stati toccati asset bundlati: `uv run python -m sertor_installer.sync` e il test di
  sincronizzazione.

**Uscita:** conteggi dei test passati e `ruff` pulito, riportati nel log.

### F3 — PR, CI, merge

- Prima di aprire la PR: `gh pr list --state open`. Se c'è già una PR aperta, chiedere all'utente.
- CI della PR: leggere `gh pr checks`. **Un job `skipping` non è verde**: gli smoke d'installazione
  saltano per design sulle PR che non toccano installer o asset, e sono proprio quelli che in
  `v0.5.0` non hanno guardato.
- **Merge solo col go esplicito dell'utente.**
- **Dopo il merge:** `gh run list --branch master`. La CI di `master` deve essere verde sul commit che
  si taggherà. Dal merge di `v0.2.0` è rimasta rossa senza che nessuno guardasse.

**Uscita:** hash del merge, run di `master` verde.

### F4 — Gate d'aggiornamento completo (vincolante)

Il rilascio parte **solo** se un ospite che **aggiorna** dalla release precedente arriva sano. Un host
pulito non può vedere i difetti d'aggiornamento **per costruzione**: dei ~14 difetti reali dal campo,
13 erano nella superficie di consegna, e tutti e 7 quelli d'installer richiedono un'installazione
preesistente più vecchia.

- **Come:** `gh workflow run upgrade-smoke-full.yml -f from_ref=<ultimo-tag>`. Per un salto lungo
  si passa un tag più vecchio. La matrice è ubuntu/windows × claude/copilot-cli.
- **Come si legge:** l'exit code **non basta**, perché ogni esito può stampare `n/a` ed uscire 0.
  Il test esige per nome `OK` su `pin-moved`, `host-config-preserved`, `mcp-invocation-shape`,
  `no-stale-divergence`, `version-derived-from-runtime`, `mcp-server-imports` e `health-green`
  (`tests/integration/test_host_smoke.py`). Leggere le righe `[upgrade]` nei log di **ogni**
  combinazione e riportare il run ID.
- **Quando:** sul commit che verrà taggato, **subito prima del tag**. In `v0.4.2` il tag è arrivato
  20 minuti dopo l'ultimo run verde, e il rilascio stesso ha rotto la guardia senza che nessuno la
  rieseguisse.

**Uscita:** run ID, 4/4 combinazioni verdi, esiti letti dai log.

### F5 — Tag e GitHub Release

- **Tag annotato** `vX.Y.Z` sul **merge della PR di rilascio**, con messaggio = titolo della release.
  Push del tag.
- `gh release create vX.Y.Z --latest --verify-tag --title "<titolo>" --notes-file <sezione CHANGELOG>`.
  Le note sono **la sezione del CHANGELOG**, non un testo scritto a parte.
- **Verifiche indipendenti** (non fidarsi del report del comando):
  - `git ls-remote --tags origin vX.Y.Z`, e **dereferenziare** il tag annotato (`vX.Y.Z^{}`): il ref
    punta all'oggetto-tag, non al commit;
  - `gh api repos/<owner>/<repo>/releases/latest` → `tag_name == vX.Y.Z`, `draft=false`,
    `prerelease=false`;
  - `/VERSION` letto da `master` remoto;
  - il corpo pubblicato contiene i frammenti attesi: comandi, «Known issues», «Verification».
- **Se le note sono sbagliate:** `gh release edit` mantenendo `--latest`, correzione nel CHANGELOG, e
  **rettifica pubblica** sulla bacheca. Mai correggere in silenzio (`v0.4.0`).

**Uscita:** tag dereferenziato sul commit giusto e API che risponde `latest = vX.Y.Z`.

### F6 — Dogfood (solo per il progetto che rilascia)

1. **Re-lock** del runtime `.sertor/` al nuovo HEAD (`scripts/dev/relock-runtime.ps1`, che non fa
   nulla se il runtime è già allineato).
2. **Re-index** via la CLI (`uv run --project .sertor sertor-rag index .`). È obbligatorio se il
   `_logic_version` è cambiato.
3. **Smoke MCP:** `search_code` **e** `search_docs` (il percorso del filtro sui metadati), più
   `find_symbol` su un simbolo di posizione nota, la cui riga deve combaciare col file. Se serve,
   riconnettere il server.
4. `sertor-rag doctor`.

**Uscita:** numero di documenti e chunk indicizzati, riga di `find_symbol` che combacia.

### F7 — Comunicazione (dopo il rilascio, mai prima)

«Prima il rilascio, poi le comunicazioni» (`v0.2.1`, su indicazione di Acta): una doc o un annuncio che
precede il codice è peggio di un ritardo.

- **Annuncio** sulla bacheca Acta, canale **`Releases`**, tramite la skill `acta` e il comando
  `acta publish --node Sertor --channel Releases --slug … --content-file … --tag tipo:annuncio
  --tag versione:X.Y.Z --tag altitudine:esito`. Da Acta **0.7.0** (FR-PUB-12) `publish` affigge **e**
  deposita (commit + push del solo file affisso) nella stessa invocazione: il flag `--commit` è
  deprecato, accettato senza effetto con avviso su stderr. Verificare con `acta discover`. Il rischio
  storico resta: un post affisso ma non depositato è invisibile agli altri nodi (`v0.4.0`, con Acta
  che allora richiedeva `--commit`); se il deposito fallisce, l'esito di `publish` dichiara passo e stato
  (FR-PUB-13).
- **Contenuto dell'annuncio:**
  - cosa aggiornare **per assistente**;
  - limiti e difetti noti;
  - cosa **non** è stato verificato («non verificato sul campo»);
  - una richiesta di feedback mirata.
- **Risposte** ai nodi che aspettavano la correzione, nel canale **`Feedback Sertor`**.
- **Difetti d'installazione** emersi durante il rilascio: si registrano e si affiggono per **Kaelen**,
  che ne è il proprietario. Non si riparano qui (congelamento del 2026-09-18).

**Uscita:** slug dei post e `acta discover` che li mostra.

### F8 — Chiusura

- **EXEC della roadmap:** versione pubblicata, voce in Done con il **commit del tag**, non solo i merge
  di contenuto (errore ripetuto in `v0.3.0` e `v0.3.2`). Ogni frase «su `master`, non rilasciato» va
  riscritta.
- **Wiki:** voce di log del rilascio (passi, run ID, hash), distill dichiarato e lint semantico delle
  pagine che riassumono (roadmap, `CLAUDE.md`, CHANGELOG).
- **PR post-rilascio** con il bookkeeping, mergiata col go dell'utente.

## 4. Le note di rilascio: la superficie che nessuna guardia presidia

Le note sono l'unica parte del rilascio che **nessun test controlla**, e sono quella che si è rotta più
spesso: in `v0.2.0`, `v0.2.1`, `v0.4.0` e `v0.4.2`. Struttura attuale (CHANGELOG §0.6.0):

```
## [X.Y.Z] — AAAA-MM-GG
<un paragrafo: cosa cambia per chi usa Sertor>

> **Upgrade — what to run depends on your assistant:**
> <comandi ESATTI, pinnati @vX.Y.Z, nella forma uvx --refresh --from "git+…@vX.Y.Z#subdirectory=packages/<pkg>">
> <CHI esegue cosa: per capability e per assistente>
> <avvertenze: re-index richiesto, comandi da NON eseguire, "sertor non è nel PATH">

### Added / ### Fixed / ### Changed

### Known issues — open, and declared so you do not find them yourself

### Verification — how this release was checked
- sul corpus del progetto · offline (suite) · percorso d'aggiornamento (gate, salto vA → vB)
- **Not checked:** <cosa non è stato verificato>
```

Le regole sulle note, ciascuna con la release in cui è nata:

1. **Comandi eseguibili su un ospite**, verificati sulla forma reale e mai a memoria. I nomi degli
   entry point si derivano dai `[project.scripts]` dei `pyproject`. `sertor` non è nel `PATH` (`v0.2.0`,
   `v0.4.0`).
2. **Ogni comando dice a chi serve:** per capability e per assistente. Un comando «per tutti» che non
   serve a qualcuno **fa danni**: `sertor-flow upgrade` installa `sertor-flow` dove non c'era
   (`v0.4.2`, E10-FEAT-081, impegno pubblico del 2026-09-18).
3. **Nominare la capability:** mai il `sertor upgrade` nudo, che può aggiornarne una sola e uscire
   verde (E2-FEAT-023, `v0.3.2`).
4. **Difetti aperti dichiarati, con le condizioni in cui mordono**, compresi i controlli negativi
   (`v0.2.1`, E10-FEAT-050; `v0.3.1`). I difetti d'installazione congelati in attesa di Kaelen
   **devono** comparire.
5. **Dichiarare cosa non è stato verificato.** È la sezione che impedisce di vendere un'assenza di
   prove come una prova.
6. **Controllare se la nota porta lo stesso difetto che corregge** ([[il-rimedio-ricade-nel-difetto]]).
7. **Lingua:** il CHANGELOG è in inglese. Titoli e corpi delle Release hanno oscillato fra italiano e
   inglese (`v0.2.x` in italiano, poi di nuovo inglese). **Decisione aperta:** una regola sulla lingua
   non esiste ancora.

## 5. Invarianti (la checklist che la skill deve garantire)

| # | Invariante | Origine |
|---|---|---|
| I-1 | Bump manuale, solo per release user-facing | A-15, 2026-07-10 |
| I-2 | Il bump su `master` è il rilascio: ogni arresto va prima del merge del bump | `v0.3.3` |
| I-3 | Un solo commit di rilascio con VERSION, CHANGELOG, pin e doc utente | `v0.1.0` |
| I-4 | Gate pre-merge sullo stato finale: tutte le suite più `ruff` | `v0.2.0` |
| I-5 | Merge di PR solo col go esplicito dell'utente, anche per docs | `v0.1.3`, 2026-07-22 |
| I-6 | CI di `master` verde sul commit da taggare; un job `skipping` non conta come verde | `v0.2.0`, `v0.5.0` |
| I-7 | Gate d'aggiornamento completo verde sul salto reale, esiti letti per nome, subito prima del tag | vincolo 07-29, `v0.4.2` |
| I-8 | Tag annotato sul merge della PR di rilascio, verificato dereferenziato | `v0.1.1`, `v0.3.3` |
| I-9 | `latest` verificato via API, non dal flag del comando | `v0.3.2` |
| I-10 | Note = sezione del CHANGELOG, conformi alle regole §4 | `v0.2.0` → `v0.4.2` |
| I-11 | Note sbagliate: rettifica pubblica, mai silenziosa | `v0.4.0` |
| I-12 | Prima il rilascio, poi l'annuncio; post depositati e verificati (`acta publish` deposita da Acta 0.7.0, `--commit` deprecato) | `v0.2.1`, `v0.4.0` |
| I-13 | Il dogfood si aggiorna come un ospite: re-lock, re-index, smoke MCP | `v0.1.5`, `v0.2.1` |
| I-14 | L'EXEC cita il commit del tag; il testo «non rilasciato» si riscrive | `v0.3.0`, `v0.3.2` |
| I-15 | Ogni passo si dichiara fatto con la prova (file, run ID, API), non a memoria | 2026-07-29 |

## 6. Dove la skill si ferma e chiede

- **Il tipo di release**, se il perimetro è ambiguo: patch o minor, oppure una scelta di linea come in
  `v0.4.1`.
- **Il merge di ogni PR:** sempre.
- **Un gate rosso o con esiti `n/a`:** ci si ferma e si riporta. Mai rilasciare «perché il fallimento
  non c'entra».
- **Un difetto trovato durante il rilascio:** decidere se blocca la release o finisce nei Known issues.
  Se è d'installazione, l'unica azione locale è dichiararlo e affiggerlo a Kaelen.
- **Una correzione a note già pubblicate.**

Il resto della catena, dato il go («rilascia»), **va portato in fondo senza chiedere a ogni passo**:
attesa della CI e del gate in background, tag, Release, annuncio, dogfood, chiusura (direttiva
2026-10-12).

**Meccanica dei permessi, osservata:** il classificatore della modalità automatica ha bloccato due
cose:
- un brief unico che combinava merge e `gh release create`. Rimedio: dividere il lavoro in due
  deleghe, (1) commit, push e merge, (2) tag e Release;
- un `gh pr merge` su una PR con job `skipping` («CI Bypass», 2026-10-13).

In questi casi la skill **riporta all'utente** e non aggira il blocco.

## 7. Lacune aperte che la skill deve conoscere

| Voce | Cosa manca | Effetto sul rilascio |
|---|---|---|
| **E10-FEAT-078** | un esito del gate può diventare `n/a` in modo permanente; il gate gira al push ma non al tag | la skill deve far girare F4 **lei**, subito prima del tag |
| **E10-FEAT-077** | lo smoke d'aggiornamento parte dal branch di default, non dalla release precedente: l'install «di v0.4.1» risolveva un commit di `master` | il gate misura il salto dell'installer meglio di quello del core; `pin-moved` è vacuo su quel percorso |
| **E10-FEAT-081** | nessuna guardia sulle note di rilascio | le regole §4 sono applicate a mano: candidato ideale per un controllo deterministico della skill |
| **E15-FEAT-014** | nessuna misura «da ogni versione all'ultima» | non sappiamo fin dove regge l'aggiornamento; non c'è una versione minima supportata dichiarata |
| **E2-FEAT-006** | niente PyPI: distribuzione `git+url@tag` | i pin `@vX.Y.Z` nella doc sono l'unico canale di versione |

## 8. Anti-pattern già pagati

- Dire «nulla è rilasciato» dopo il merge del bump (§1.1).
- Fidarsi di un exit code verde del gate senza leggere gli esiti.
- Taggare su un run vecchio.
- Note con comandi copiati da memoria.
- Note «uguali per tutti».
- Verificare `latest` con un campo della CLI che non esiste: la verifica «passa» in silenzio.
- Correggere una Release pubblicata senza dirlo.
- Annunciare prima di rilasciare.
- Lasciare l'EXEC a dire la versione precedente o «non rilasciato».
- Elenchi dei file da committare compilati a memoria: in `v0.4.2` tre file del wiki sono rimasti fuori
  dal commit e `master` ha avuto un link rotto.

## 9. Proprio di Sertor vs generico

| Parametro | Valore in Sertor | Vale per altri nodi? |
|---|---|---|
| File di versione | `/VERSION` (letto dall'avvisatore da `master`) | sì, come concetto: «dove legge l'avvisatore» |
| Note | `CHANGELOG.md` (Keep a Changelog, inglese) | sì |
| Pin nella doc | `README.md`, `docs/getting-started.md`, `docs/install.md` | da dichiarare per nodo |
| Pacchetti distribuiti | `sertor-core` (`src/`), `packages/sertor`, `sertor-install-kit`, `sertor-flow` | da dichiarare per nodo |
| Gate pre-merge | `pytest -m "not cloud"` + suite dei pacchetti + `ruff` | comando da dichiarare |
| Gate d'aggiornamento | `upgrade-smoke-full.yml`, input `from_ref`, 7 esiti richiesti | specifico; il **principio** (un aggiornamento reale verificato prima del tag) è generico |
| Dogfood | `relock-runtime.ps1` + `sertor-rag index` + smoke MCP | specifico di un nodo che usa sé stesso |
| Canali | Acta `Releases` (annuncio), `Feedback Sertor` (risposte) | generico nella federazione Acta |
| Git | delegato al `configuration-manager` | dipende dal nodo |
| Assistenti | Claude (alias di modello) e Copilot (ID fissi) | generico per i nodi multi-assistente |

## 10. Proposta di forma per la skill (decide Sinthari)

- **Separare il deterministico dal giudizio**, come le altre skill della federazione: *il tool trova,
  l'agente giudica*.
  - **Deterministico (script o CLI):**
    - perimetro per pacchetto;
    - controllo del commit di rilascio (VERSION, sezione CHANGELOG, pin coerenti con la versione);
    - lint delle note (forma dei comandi, presenza di Known issues e Verification, ogni comando con
      il suo destinatario);
    - lancio e lettura del gate per esiti nominati;
    - verifiche post-pubblicazione (tag dereferenziato, `releases/latest`, frammenti del corpo).
  - **Giudizio (agente):**
    - tipo e titolo;
    - testo delle note;
    - chi deve eseguire cosa;
    - quali difetti dichiarare;
    - annuncio.
- **Parametrizzata da un file di configurazione del nodo** (i valori della §9), così la stessa skill
  serve ad altri nodi.
- **Fasi come checklist con criterio d'uscita** (§3) e **report finale** con le prove: hash, run ID,
  URL della Release, slug Acta.
- **Trigger:** «rilascia», «rilasciamo», «prepara la release», «taglia una versione», «release vX.Y.Z».
- Il controllo deterministico delle note chiuderebbe anche **E10-FEAT-081**, che oggi è la lacuna più
  esposta.

## Collegamenti

[[roadmap]] · [[difetto-che-solo-un-ospite-nuovo-puo-vedere]] · [[guardia-verde-non-e-una-misura]] ·
[[potere-retrospettivo-di-una-guardia]] · [[punto-di-partenza-non-verificato]] ·
[[il-rimedio-ricade-nel-difetto]] · [[riassunto-invecchia-senza-riconciliatore]] ·
[[esito-sull-host-vs-forma-dell-asset]] · [[assistant-targeting]]
