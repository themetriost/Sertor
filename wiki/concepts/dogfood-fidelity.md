---
title: Fedeltà del dogfood (dogfood-fidelity)
type: concept
tags: [dogfooding, fedelta, runtime, installato, head-tracking, re-lock, e15]
created: 2026-07-03
updated: 2026-07-26
sources: ["requirements/fedelta-dogfood/epic.md", "wiki/syntheses/audit-fedelta-dogfood-2026-07-03.md", "specs/088-relock-runtime/plan.md", ".sertor/pyproject.toml", "scripts/dev/relock-runtime.ps1", "CLAUDE.md"]
---

# Fedeltà del dogfood (dogfood-fidelity)

Il [[dogfooding]] risponde a «usiamo il nostro RAG su di noi». La **fedeltà del dogfood** risponde a una
domanda più stretta e più severa: **il dogfood si comporta *davvero* come un progetto-ospite di Sertor, o
solo *quasi*?** È la stella polare applicata a noi stessi — se il workspace di Sertor gira su qualcosa di
diverso da ciò che un ospite otterrebbe, il dogfooding *mente* (misura uno strumento che nessun cliente ha).
Ogni divergenza dal client è **debito**, non design (direttiva standing *«il dogfood è un client fedele; ogni special-case è debito»*); la direttiva
standing è: il dogfood gira **solo** sulla versione **installata**, mai sul sorgente-repo
(direttiva standing *«dogfood solo via install da version bump»*, 2026-07-03).

## I due livelli di fedeltà

La fedeltà non è monolitica: si rompe su due assi indipendenti.

- **Asset-fidelity** — *gli stessi file*. Gli asset host-facing del dogfood (`.claude/`, hook, skill,
  agenti, blocchi `CLAUDE.md`, `wiki/`) sono byte-identici a quelli che un installer depositerebbe? Oggi
  **parziale**, mantenuta via `sertor_installer.sync` + guardie (E15-FEAT-002).
- **Process-fidelity** — *prodotti dal vero processo*. Quegli asset e quel runtime sono stati prodotti
  **eseguendo i veri installer** (`sertor install rag/wiki`, `sertor-flow install`), o curati a mano /
  sincronizzati? Finché si passa dal sync, la *forma* è fedele ma il *processo* no.

La distinzione conta perché un asset può essere identico (asset-fidelity ✅) pur non essendo mai passato per
l'installer (process-fidelity ✗): il secondo è ciò che verifica davvero il percorso che l'ospite vive.

**Lezione complementare:** vedi anche [[esito-sull-host-vs-forma-dell-asset]] — anche un asset
process-fedele si controlla male se testiamo solo la *forma* e non l'*esito sull'host che aggiorna*.

## Il runtime: `.sertor/` installato, che traccia HEAD

Il cuore del modello (E15-FEAT-001/F1): il **runtime dell'agente** — MCP, hook, skill, la macchina che
serve retrieval — gira sul **runtime installato `.sertor/`**, non sul `.venv` editable del workspace. È un
progetto `uv` a sé (`.sertor/pyproject.toml` + `.sertor/uv.lock` + `.sertor/.venv`) che installa
`sertor-core` da `git=<repo>` a **HEAD**, non da un tag.

- **Il dogfood traccia HEAD; gli ospiti pinnano una versione.** Un cliente esterno pinna un tag e riceve
  l'auto-updater ([[auto-update-version-check|E2-FEAT-013]]); il dogfood insegue `origin/master`. Le due
  storie sono **separate** e non devono mescolarsi.
- **Re-lock post-merge (E15-FEAT-008/F8).** `.sertor/uv.lock` fissa il commit risolto: dopo un merge su
  `master`, HEAD avanza e il runtime resta stantio. Il passo `scripts/dev/relock-runtime.ps1` (check-then-act,
  fail-loud, **dogfood-only**) lo riallinea meccanicamente nel rituale post-merge, *prima* di re-index/smoke.
  Il lock è **gitignorato** (volatile, tracks HEAD); solo `.sertor/pyproject.toml` è versionato (la spec
  stabile). Confine D↔N: lo script è deterministico, l'innesco è giudizio del flusso principale — e resta
  **fuori** dagli asset distribuiti (l'hook `rag-freshness.py` non deve inseguire HEAD).

## Il confine dev↔dogfood (non è uno special-case)

Il workspace **è** Sertor più il suo sviluppo, quindi porta cose che un client non ha (`src/`, `packages/`,
`tests/`, `.venv`). Non è una violazione della fedeltà: è la natura del repo-sorgente. Il confine è netto:

- **dev/test** → sul `.venv` editable del workspace (`uv run pytest`, `ruff`);
- **runtime dell'agente** → sull'installato `.sertor/`.

Sotto questa lente, `.venv` non è un «asset divergente» da eliminare — è l'ambiente di sviluppo del prodotto;
il runtime dell'agente semplicemente non lo usa.

## Il terzo limite: il dogfood è **una** configurazione, e la più favorevole (2026-07-26)

Ai due livelli di fedeltà sopra — *asset* e *processo* — se ne aggiunge un terzo, che non è un grado
minore ma un **limite di principio**: anche un dogfood perfettamente fedele occupa **una sola
configurazione** fra quelle che gli ospiti realizzano. Prova che il codice **gira**; non prova che gira
per le configurazioni che non abbiamo.

E c'è un aggravante che rende il limite sistematico invece che casuale:

> **La nostra configurazione è la più favorevole per costruzione**, perché la ripariamo di continuo e
> informalmente. Ogni fix a mano sul dogfood **cancella una prova** di cosa provi un ospite vero. È un
> canarino che si cura da solo.

### La forma più acuta del terzo limite: **il dogfood non esercita il verbo che spediamo** (2026-07-29)

Il limite non è solo che occupiamo *una* configurazione favorevole. È più netto di così:

> Il runtime `.sertor/` insegue **HEAD** con un re-lock a ogni merge. Passa da un commit al successivo,
> **mai da una versione alla successiva**. Il dogfood non esegue mai `sertor upgrade`.

Quindi non c'è una configurazione «poco coperta»: c'è un **verbo del prodotto che nessuno di noi
esercita**, e che è **l'unico** attraverso cui gli ospiti ricevono qualunque cosa facciamo. E il re-lock
non è un dettaglio d'ambiente: è **prescritto dal rituale** dopo ogni merge, cioè la disciplina che ci
tiene aggiornati è la stessa che ci impedisce di provare l'aggiornamento.

La misura del 2026-07-29 lo rende quantitativo: su ~14 difetti reali dal campo, **7 stanno
nell'installer/upgrade** e **tutti e sette richiedono un'installazione preesistente più vecchia** per
manifestarsi. Un host pulito — l'unico che il nostro smoke costruisce — non può vederne nessuno *per
costruzione*. Rimedio: **E15-FEAT-012** (smoke di upgrade come gate di rilascio); la faccia gemella,
lato guardie, è in [[esito-sull-host-vs-forma-dell-asset]].

**Tre casi, tutti arrivati da fuori, tutti nello stesso senso:**

| Difetto | Perché era invisibile da qui |
|---|---|
| `.mcp.json` con `--directory` (E2-FEAT-022) | il nostro `.mcp.json` aveva `--project`, **corretto a mano** prima che il template esistesse: eravamo l'unico nodo **non** colpito da ciò che spedivamo |
| comando d'upgrade rotto per chi pinna (2026-07-26) | il nostro runtime è **ref-less per progetto** (segue HEAD): il ramo che rompe è **irraggiungibile** qui |
| numero del principio nell'annuncio (E13-FEAT-015) | vero **solo dal punto di vista di chi legge lo starter**, e noi leggiamo la nostra costituzione |

Il secondo caso ha la forma più istruttiva, e la formulazione è del nodo *Acta*:

> **Il difetto seleziona chi segue la disciplina.** Solo l'ospite che pinna a un riferimento immutabile
> riceveva il comando rotto; chi accettava il ref-less riceveva quello giusto.

Un difetto così non è raro: è **anti-correlato** all'utente che ci interessa di più.

### Cosa ne segue, operativamente

La classe si divide in due, e le due metà vogliono strumenti diversi:

- **La parte meccanizzabile** — esercitare il codice contro **configurazioni che non abbiamo**: un
  runtime pinnato al tag, un ospite con la costituzione più vecchia dello starter, una skill più nuova
  del runtime che invoca. Sono fixture, non un secondo dogfood; costano poco e chiudono i casi
  derivabili. *(Esempio realizzato: le guardie del pin in `test_portable_hooks_parity.py`, scritte
  esattamente per occupare la posizione che il nostro nodo non occupa.)*
- **La parte non meccanizzabile** — ciò che è vero solo dal punto di vista di **chi legge**, o di chi
  **adotta davvero** una cosa invece di archiviarla. Qui non esiste un test, e il rilevatore è un
  **lettore esterno**: una federazione di nodi che pubblicano e si leggono non distribuisce solo
  conoscenza, **è un rilevatore** per una classe di guasti che nessun test cattura. È la stessa ragione
  per cui il [[constitution|Principio XIV]] è un **gate al `plan`** e non una guardia.

Cfr. [[esito-sull-host-vs-forma-dell-asset]] (la guardia cieca / complice / dal perimetro stretto) e
[[identita-per-presenza-o-per-contenuto]]: là il punto d'osservazione è sbagliato o il criterio è
sbagliato; qui il punto d'osservazione è **giusto ma unico**.

### Il corollario: un rilevatore esterno va anche *consumato* con disciplina

Se la federazione è un rilevatore, allora ricevere un riscontro non basta: serve una regola per
**leggerlo**, perché una segnalazione arriva sempre **datata a una versione**.

> Prima di costruire il rimedio, verifica che la **causa** segnalata sia ancora viva nella versione
> corrente. Il sintomo è vero *per chi l'ha visto*; la causa può essere già stata chiusa da un fix
> nostro successivo, o essere diversa da quella ipotizzata da chi segnala.

**Caso reale (2026-07-26).** Un nodo segnalava che l'avviso d'aggiornamento suggerisce un comando che
sul suo host «non è nemmeno eseguibile, perché l'installer `sertor` non è presente». Sulla scorta di
quella frase è stata scritta una **rilevazione della presenza dell'installer** per differenziare il
messaggio. Verificando la premessa **dopo** averla implementata: `sertor` **non è mai** un comando
persistente — `uvx --from "git+…"` lo preleva al volo, quindi la forma corretta funziona su qualunque
host con `uv`. La segnalazione riguardava la forma **nuda** del comando, difetto già chiuso due
versioni prima. Il codice è stato **rimosso**: era un'euristica fragile (si appoggiava a un file
introdotto a fine giugno, quindi avrebbe classificato male ogni installazione più vecchia) costruita
per un problema che non esisteva più.

È lo stesso **errore d'ordine** già registrato il 2026-07-24 su un altro rilievo esterno — *«non un
errore di ragionamento ma di ordine: decidere prima, verificare dopo»*. Due occorrenze in tre giorni,
entrambe partite da un riscontro **corretto** a cui è stato applicato un rimedio **sbagliato**: è la
firma del difetto, e la contromisura è banale quanto facile da saltare — **verificare la premessa
prima di scrivere il rimedio, non dopo**.

## Stato (E15 `fedelta-dogfood`)

| Fetta | Stato |
|---|---|
| **F1/F7** runtime installato `.sertor/` da git HEAD, `.mcp.json` → `uv run --project .sertor` | ✅ (#150) |
| **F5** installer preservante `plan-template.md` attraverso `specify init --force` | ✅ (#149) |
| **F8** re-lock post-merge del runtime a HEAD (script dogfood-only + gitignore lock + rituale/gate) | ✅ (#152) |
| **F2** asset-fidelity RAG (sync esteso + guardie) — *interim, via sync non install* | ✅ (#146) |
| **F4 / asset-install** gli asset prodotti dai **veri** `sertor install`/`sertor-flow install`, non dal sync | ✅ (branch 089, 2026-07-06 — E15-FEAT-001 scope B) |

**Entrambi i livelli chiusi (2026-07-06):** F1 ha chiuso il *runtime* (process-fidelity del motore);
l'**asset-install** (F4, E15-FEAT-001 scope B) fa produrre gli asset dai **veri** installer eseguiti sul
dogfood → **process-fidelity raggiunta** (`.env`/costituzione/`.mcp.json`/`wiki.config` preservati, core
invariato, idempotenza provata). Il sync resta come **guardia anti-drift**, non più come *fonte* degli asset.
Vedi [[asset-install-installer-dry-run-2026-07-04]].

## Vedi anche
- La pratica di base che questo modello rende fedele: [[dogfooding]].
- L'audit che ha nominato i due livelli: [[audit-fedelta-dogfood-2026-07-03]].
- Il dry-run empirico che ha verificato l'idempotenza dei veri installer: [[asset-install-installer-dry-run-2026-07-04]].
- L'altro limite del dogfood: non contiene punti di estensione con filtri (che richiedono host reali attenti), vedi [[punti-di-estensione-condivisi]].
- Le direttive standing dell'utente: *«il dogfood è un client fedele»* (2026-07-03) e *«dogfood
  solo via install da version bump»* (2026-07-03). Vivono nella memoria dell'agente, non nel wiki.
