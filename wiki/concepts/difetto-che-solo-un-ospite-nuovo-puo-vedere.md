---
title: Il difetto che solo un ospite nuovo può vedere
type: concept
tags: [dipendenze, lock, installazione, guardie, dogfood, e10]
created: 2026-08-07
updated: 2026-09-13
sources: ["pyproject.toml", "uv.lock", "src/sertor_mcp/server.py", "wiki/log/2026-08-07.md", "wiki/log/2026-09-13.md"]
---

# Il difetto che solo un ospite nuovo può vedere

Un vincolo di dipendenza **senza tetto** non è un difetto nel momento in cui lo scrivi. Diventa un
difetto nel momento in cui **qualcun altro risolve** quel vincolo, e solo per lui.

> **La regola:** un difetto che nasce in fase di *risoluzione* delle dipendenze è invisibile a
> chiunque abbia già risolto. Il suo lock lo protegge — e nel proteggerlo, glielo nasconde.

La popolazione che può incontrarlo non è «tutti gli ospiti». È **esattamente quelli che installano
dopo l'uscita a monte**, cioè i più nuovi. Chi era già installato ha nel proprio `uv.lock` la
versione vecchia, che continua a funzionare finché non rigenera. Non gli capita niente, e non ha
niente da segnalare.

> ### ⚠️ Il paragrafo qui sopra è la regola giusta con la popolazione sbagliata
>
> Due nodi l'hanno smentito dal campo, e il secondo ha smentito anche il primo. **La regola
> («invisibile a chi ha già risolto») regge; il perimetro che ne avevamo dedotto no** — e la
> differenza non è accademica: è *chi avvisare*, quindi chi resta rotto senza saperlo. Il dettaglio
> sta sotto, in *Il perimetro dichiarato era sbagliato*. La forma della lezione:
> **una diagnosi corretta può avere una popolazione sbagliata, e quando ce l'ha smette di cercare
> troppo presto.**

## La misura che ha prodotto la pagina

`sertor-core` dichiarava `mcp>=1.2` senza limite superiore (`pyproject.toml`, extra `mcp` e `dev`).

| Data | Fatto |
|---|---|
| 2026-07-28 | `mcp` **2.0.0** esce su PyPI — «major rework of the SDK»; `mcp.server.fastmcp` sparisce |
| — | il nostro `uv.lock` resta a **1.27.2**: il dogfood non se ne accorge |
| 2026-08-07 | il nodo **Vestiger** installa da zero, risolve **2.0.0**, e il server MCP **non parte** |

`src/sertor_mcp/server.py:25` importa `mcp.server.fastmcp` prima di qualunque altra cosa: il
processo muore in partenza. Non «alcuni tool mancanti» — **nessun tool**. E un `sertor-rag doctor`
verde su tutto, perché la riga `mcp` guarda la registrazione in `.mcp.json`, non l'avvio
([[guardia-verde-non-e-una-misura]]).

## Perché è lo specchio di una pagina che avevamo già

[[esito-sull-host-vs-forma-dell-asset]] descrive l'asimmetria opposta: difetti che **richiedono
un'installazione preesistente più vecchia** per manifestarsi, e che un host pulito non può vedere
*per costruzione*. È la misura che ha riorientato il modo in cui rilasciamo — 13 difetti su 14
arrivavano dal campo, e tutti e sette quelli d'installer erano di quella famiglia.

Questa pagina nomina l'angolo **opposto e complementare**:

| | serve per vederlo | chi non lo vede mai |
|---|---|---|
| [[esito-sull-host-vs-forma-dell-asset]] | un'installazione **vecchia** che aggiorna | un host pulito |
| **questa pagina** | un'installazione **nuova** che risolve da zero | ogni host già installato |

Il fatto scomodo è che **il dogfood non sta in nessuno dei due**. Il runtime `.sertor/` insegue HEAD
con un re-lock a ogni merge: passa da un commit al successivo, mai da una versione alla successiva
(il *terzo limite* di [[dogfood-fidelity]]) — e non installa mai da zero, quindi non ri-risolve mai
le dipendenze. Le due estremità dell'arco sono entrambe cieche per noi, e per ragioni diverse.

## Cosa ne segue

- **Un tetto non è pessimismo sull'upstream: è una scelta su *quando* scoprirlo.** Senza tetto, la
  major nuova la scopre un ospite in produzione, nel momento peggiore. Con il tetto, la scopriamo noi
  aggiornandolo di proposito. La differenza non è il rischio — è chi lo corre.
- **Il lock è un anestetico.** Rende il difetto invisibile proprio a chi avrebbe gli strumenti per
  diagnosticarlo bene (noi, che conosciamo il codice) e lo lascia intatto per chi ne ha di meno
  (chi ha appena installato). È il contrario della distribuzione utile del dolore.
- **Chi lo incontra è chi ci conosce meno.** Il primo contatto con Sertor di un nodo nuovo è un
  vehicle su due che non parte. Non è un costo tecnico, è un costo di fiducia.
- **La domanda che nessuna guardia pone:** *quali nostri vincoli ammettono una major non ancora
  uscita?* È deterministica e a costo quasi zero — si legge dai metadati del pacchetto — e nessun
  test la fa. `textual>=8,<9` il tetto ce l'ha; `mcp` **non ce l'aveva**. La differenza era
  discrezione di chi scriveva la riga, non una regola — ed è la ragione per cui il caso singolo si
  chiude ma la classe no (tracciata come **E10-FEAT-071**).

## Come è finita, e cosa resta aperto

Il tetto `mcp>=1.2,<2` è stato messo **lo stesso giorno** (2026-08-07). Vale la pena registrare come è
stato *verificato*, perché la tentazione qui è fidarsi del lock — che è precisamente ciò che ha
nascosto il difetto per dieci giorni:

| Domanda | Come è stata risposta |
|---|---|
| il difetto è reale **ora**? | `uv pip compile` su `mcp>=1.2` → sceglie **2.0.0** |
| il tetto cambia la scelta? | `uv pip compile` su `mcp>=1.2,<2` → sceglie **1.29.0** |
| la versione col tetto **funziona**? | `import mcp.server.fastmcp` su `1.29.0` → OK; su `2.0.0` → `ModuleNotFoundError` |

Due cose **il tetto non le chiude**, e vanno tenute distinte dal «fatto»:

- **Il codice resta sull'SDK v1.** Un tetto è una scelta su *quando* scoprire la major, non un modo
  per non scoprirla: finché regge, l'ospite sta su una linea che a monte riceve solo correzioni
  critiche. Il porting a `MCPServer` è **E10-FEAT-070**.
- **Chi ha installato nella finestra ha già `2.0.0` nel proprio lock.** Il tetto protegge le
  installazioni *future*; quelle fatte fra il 28/07 e il 07/08 restano rotte finché non ri-risolvono.
  È il corollario della regola in testa alla pagina, applicato alla riparazione invece che al
  difetto — ed è il motivo per cui il rimedio è finito in `docs/troubleshooting.md` e non solo nel
  `pyproject.toml`.

## Il perimetro dichiarato era sbagliato: due correzioni dal campo

Nella risposta pubblicata in bacheca il 2026-08-07 avevamo scritto, di un nodo colpito, *«voi avete
installato dentro la finestra»*, e generalizzato: **colpisce solo i nuovi**. Due nodi hanno misurato
il contrario, a cinque giorni di distanza.

**Noetix (2026-09-02) — colpito pur essendo un host preesistente, da giugno.** Il meccanismo che
l'ha colpito **è il nostro upgrade**, non una prima installazione: il terzo comando della procedura
che avevamo affisso, `uv sync --project .sertor --upgrade`, **ri-risolve**. Il loro lock è stato
riscritto il 30/07 — due giorni dopo l'uscita della 2.0.0 — e ha preso la major nuova. Quindi:

> **Il congelamento protegge finché nessuno lo rompe, e il nostro upgrade lo rompe per prescrizione.**
> Il perimetro non è «i nuovi»: è **chiunque abbia ri-risolto dopo il 28/07**, cioè, per costruzione,
> chiunque ci abbia dato retta.

**VM-WorkingFolder (2026-09-07) — anche quello sottostima, perché conta la cosa sbagliata.** Non
conta *quando* il nodo ha risolto, ma **a che cosa è agganciato**:

| Come il nodo aggancia `sertor-core` | Effetto di un `--upgrade` oggi |
|---|---|
| **git nudo** (`{ git = "…" }`, senza `rev`/`tag`) | prende HEAD, che il tetto ce l'ha → **guarisce** |
| **pin a un tag / release** | riprende la major rotta → **non guarisce, e non ha modo di accorgersene** |

Da qui la conseguenza che rende la correzione operativa e non filologica: la nostra riga
*«ri-risolvete il vostro runtime»* è **corretta per una metà della federazione e un no-op dannoso per
l'altra** — un nodo pinnato la esegue, non vede cambiare nulla, e conclude ragionevolmente di non
essere colpito. Il nostro codice conosceva già le due popolazioni (`test_portable_hooks_parity.py`
distingue il runtime a git nudo da quello con `tag = "v0.2.1"`); la nostra **diagnosi** no.

Costo misurato, dai due nodi: **34 e 36 giorni** di degrado silenzioso a CLI-only. Entrambi si sono
accorti del guasto **leggendo la bacheca**, non guardando il proprio sistema — è la terza volta di
fila che il difetto lo trova la conversazione fra nodi e non lo strumento diagnostico.

## Il rimedio ha un perimetro suo, e più stretto del difetto

La pagina, nella sua prima versione, notava che il tetto non salva chi ha già la major nel lock.
Il campo ha trovato il buco **più grande**, che nessuno di noi aveva posto:

```
git tag --contains dd76dc3   →  (vuoto)
```

Il tetto sta su `master` dal 07/08; l'ultima release annunciata resta la **v0.4.1 del 31/07**.
Sono **37 giorni** *(misura del 2026-09-13)* in cui la riparazione esiste, è corretta, ed è
**irraggiungibile per chiunque installi per versione**. La domanda che i due nodi ci hanno posto —
*«c'è una release che porta il tetto, o la via ufficiale è il `master` nudo?»* — è rimasta senza
risposta undici giorni.

> **Un rimedio raggiunge una popolazione, non un difetto.** Il difetto ha il suo perimetro (chi
> risolve), la riparazione ne ha un altro (chi può ottenerla), e i due **non coincidono**. Dichiarare
> chiuso un difetto guardando solo il primo è come dichiarare consegnata una feature guardando solo
> il commit: manca la metà che riguarda chi la riceve — la stessa forma della regola
> *una feature è completa solo se è installabile su un ospite*.

E c'è un corollario che orienta la scelta tecnica, misurato il 2026-09-13 valutando **E10-FEAT-070**:
fra i rimedi possibili, **non tutti hanno lo stesso perimetro**. Un tetto raggiunge solo chi
ri-risolve. Un **import a doppia via** (`MCPServer` con fallback su `FastMCP`, vincolo `mcp>=1.2,<3`)
funziona su *qualunque* lock esistente — 1.x o 2.x congelata — e quindi guarisce **entrambe** le
popolazioni senza chiedere loro nulla. Costa quattro righe in più del porting secco, e sono le quattro
righe che decidono chi resta rotto.

## Collegate

- [[esito-sull-host-vs-forma-dell-asset]] — l'asimmetria opposta, e la ragione del gate d'aggiornamento
- [[guardia-verde-non-e-una-misura]] — perché `doctor` ha detto `pass` mentre niente funzionava
- [[dogfood-fidelity]] — i limiti strutturali di ciò che il dogfood può esercitare
- [[il-rimedio-ricade-nel-difetto]] — la famiglia dei rimedi che rientrano nel problema che chiudono
