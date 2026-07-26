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
Ogni divergenza dal client è **debito**, non design (vedi [[feedback_dogfood_client_fedele]]); la direttiva
standing è: il dogfood gira **solo** sulla versione **installata**, mai sul sorgente-repo
([[feedback_dogfood_solo_via_install_versionbump]]).

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
- Le direttive standing: [[feedback_dogfood_client_fedele]], [[feedback_dogfood_solo_via_install_versionbump]].
