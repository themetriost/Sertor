---
title: Un riassunto invecchia quando cresce ciò che descrive
type: concept
tags: [deriva, documentazione, principio-xiv, lint-semantico, problema-aperto, e10, e13]
created: 2026-07-28
updated: 2026-07-31
sources: ["src/sertor_core/config/settings.py", "CLAUDE.md", "wiki/log/2026-07-27.md", "wiki/log/2026-07-28.md", "wiki/log/2026-07-31.md", "requirements/debito-tecnico/epic.md", "wiki/syntheses/roadmap.md"]
---

# Un riassunto invecchia quando cresce ciò che descrive

> **⚠️ Pagina scritta come *problema aperto*, non come soluzione.** Il rimedio (un rilevatore
> deterministico) **non esiste ancora**: vive come [[roadmap|E10-FEAT-049]] con due prototipi da ~40
> righe. La pagina esiste perché il rinvio è stato dichiarato **tre volte** (27/07, 28/07 e di nuovo
> oggi) e alla terza il rinvio diventa un modo per non decidere — così era stato messo per iscritto
> nel log del 28. Descrive quindi il *difetto*, non la sua cura.

Ogni **riassunto** — un indice, un executive summary, un CHANGELOG, un blocco di istruzioni per
l'agente — è una **copia descrittiva** di un fatto che vive altrove. Il fatto cresce; la copia no.
Nessuno confronta i due.

> **La firma:** la copia continua a leggersi bene. Non è rotta, è **obsoleta** — e siccome è l'unica
> cosa che il lettore (umano o agente) *legge davvero*, l'obsolescenza si propaga come verità.

È la faccia in **prosa** del [[constitution|Principio XIV — «Derived State, Not Declared»]]: un fatto
che vive in più posti va **derivato**, e dove derivarlo è impossibile serve un **riconciliatore
nominato** che **dichiari** la divergenza. Conservare una copia stantia può essere giusto; conservarla
**in silenzio** no.

## Sette superfici, sette istanze reali

| # | Superficie | Istanza |
|---|---|---|
| 1 | **Indice del wiki** ↔ pagina puntata | quattro casi dal lint del 27/07: `ports-adapters` «otto» / indice «sei» · `constitution` «14 principi» / indice «10» · `speclift` «8 stadi» / indice «9» · pannello «fatto» / indice «in sviluppo» |
| 2 | **EXEC della roadmap** ↔ backlog | l'EXEC citava `E10-FEAT-052` fra le direzioni nuove **prima** che la riga esistesse su `master` |
| 3 | **Doc utente / CHANGELOG** ↔ asset spedito | cinque punti della doc dicevano «usa `--project`, mai `--directory`» mentre **il template spediva `--directory`** — e un test lo certificava giusto (E2-FEAT-022) |
| 4 | **Blocchi distribuiti** (`claude-md-block`) ↔ capacità reale | rigenerati dall'installer, quindi la copia dell'ospite invecchia fino al prossimo `upgrade` |
| 5 | **`wiki/log/index.md`** ↔ cartella del giornale | duplica un fatto **derivabile dalla cartella**, senza riconciliatore, e il `lint` non lo vede (E10-FEAT-047) — prima istanza del XIV, dieci minuti dopo la ratifica |
| 6 | **Prosa always-loaded di `CLAUDE.md`** ↔ `Settings` | **2026-07-28** — vedi sotto |
| 7 | **Blocco SPECKIT nel `CLAUDE.md`** ↔ stato effettivo | **nuova, 2026-07-31** — il blocco dichiarava attivo un **vincolo sciolto** (E15-FEAT-012 mergiato il 30/07 con v0.4.0 rilasciata) e un **branch chiuso** (126-ritual-check-perimetro mergiato il 31/07); un controllo automatico l'ha colto *(non era un lint umano, era un harness)*. È la prima volta che una **superficie always-loaded entra in una checklist automatica** — il danno più grave di tutte perché la fonte di errore non è il vago incombing, è la lettura sistematica d'ogni sessione. Vedi sezione La settima |

## La sesta: l'istruzione che sopravvive alla manopola

Trovata durante un `/doctor` (igiene dell'harness), **non** da un lint. Il `CLAUDE.md` — il file che
l'agente legge a **ogni** sessione — insegnava `RAG_BACKEND` in **quattro punti**, incluso un
`RAG_BACKEND=local` presentato come condizione per far passare i test. Ma `RAG_BACKEND` **non è più
onorata** da `Settings.load` (`settings.py:373`): viene **ignorata** con un WARNING
`config_rag_backend_ignored`. Il knob reale è `SERTOR_EMBED_PROVIDER` (+ `SERTOR_STORE_BACKEND`), e
`.env.example` — la copia *versionata* — era **già corretta**.

Perché questa istanza è la peggiore delle sei:

- **Il lettore è l'agente, a ogni sessione.** Le altre cinque le legge chi va a cercarle; questa entra
  nel contesto **sempre**, e orienta il lavoro prima che qualcuno la verifichi.
- **Non fa rumore.** La manopola non solleva: emette un warning e prosegue. Un'istruzione che dice di
  impostarla produce quindi un comportamento **plausibile** — il default — non un errore. Cugino di
  [[default-masked-defect]], dove la prudenza che protegge l'utente protegge anche il bug.
- **Nessuna guardia guardava.** Il `lint` strutturale non legge la prosa; il lint semantico è
  **giudizio**, quindi vede solo ciò che qualcuno decide di guardare quel giorno.

## 🔍 La riparazione ricade nello stesso difetto

Il fatto più utile della giornata: **correggendo la copia stantia ne ho scritta un'altra.** Sostituendo
i quattro punti ho affermato che `Settings.load` «**fallisce loud**». Falso: **ignora e segnala**. Lo
`search_code` dello smoke test l'ha smentito subito — tre test lo dicono nel nome
(`test_rag_backend_residual_warns_and_ignored`) — e `specs/068-embedder-locale/quickstart.md` lo
confermava già in modo indipendente.

> **Riscrivere un riassunto a memoria è esattamente l'operazione che l'ha fatto invecchiare.** La copia
> non è invecchiata perché era vecchia: è invecchiata perché era una **riformulazione non ancorata**.
> Una nuova riformulazione, anche fatta oggi, è già il prossimo drift.

Corollario operativo, ed è il vero contenuto della pagina: **quando ripari una copia derivata, non
riformulare — punta.** Il rimedio adottato nei sette tagli del 28/07 non è stato riscrivere meglio, è
stato **eliminare la copia** e rimandare alla fonte (`pyproject.toml`, `.env.example`,
`settings.py`, `ls`): −92 righe di `CLAUDE.md`, e quelle righe **non possono più invecchiare**. Dove la
copia è servita davvero (le manopole non ovvie), la si tiene **con la citazione della fonte**
(`settings.py:373`), che è un riconciliatore leggibile a mano.

## La settima: la superficie always-loaded scoperta da un harness

La più grave di tutte, perché è l'unica mai **verificata da una checklist automatica** (le precedenti
erano lint umani o segnalate dagli utenti). Scoperta il **31/07 durante un rilascio** — il blocco
SPECKIT in coda al `CLAUDE.md` dichiarava *«corrente»* un **vincolo sciolto** (E15-FEAT-012 mergiato
il 30/07 con v0.4.0 già rilasciata, il vincolo era quindi **obsoleto dal 31/07 00:00**) e *«attivo»*
un **branch chiuso** (`126-ritual-check-perimetro` mergiato come PR #262 lo stesso 31/07).

Un controllo manuale di pre-rilascio leggeva il blocco di setup-prova (che ogni agente carica), vedeva
il vincolo dichiarato attivo, e **si fermava** per chiedere conferma prima di procedere. Il controllo
**non aveva sbagliato**: il testo mentiva. Questo contraddistingue la settima istanza dalle precedenti
sei — **non è la prosa a essere vaga, è letteralmente falsa**, e l'ha scoperto un harness, non una
lettura.

> **Aggravante:** il blocco è sempre-caricato (ogni sessione lo legge), quindi **due sessioni diverse**
> non hanno alcun modo di sincronizzarsi sulla sua verità. La correzione non è — come per le altre —
> «aggiorna la copia»; è «il blocco non deve diventare un fatto** (solo una referenza all'artefatto
> vero, la PR, la branch, il commit).

## Cosa la chiuderebbe

- **[[roadmap|E10-FEAT-049]]** — il lint semantico guarda i **riferimenti entranti**: indice ↔ pagina
  puntata, e `sources:` ↔ data dell'ultimo commit. Due prototipi già scritti (~40 righe), quattro casi
  di prova reali. Copre le superfici 1, 2, 5.
- **[[roadmap|E13-FEAT-014]]** — guardia deterministica anti-drift della **doc utente** (richiesta del
  nodo *Acta*). Copre 3 e 4. *È la stessa forma di 049: conviene progettarle insieme.*
- **Scoperto: nessuna delle due copre la 6.** La prosa `CLAUDE.md` non ha né un indice che la punti né
  un `sources:` da confrontare. Il presidio praticabile è **strutturale, non diagnostico**: non
  scrivere nel file always-loaded ciò che è derivabile da una fonte a due `Read` di distanza —
  esattamente il criterio di derivabilità applicato il 28/07.

## Vedi anche

- [[constitution]] — Principio XIV, di cui questa è la faccia in prosa.
- [[identita-per-presenza-o-per-contenuto]] — la gemella *sull'idempotenza*: là la scelta sbagliata
  produce un no-op che sembra successo, qui una copia che sembra vera.
- [[default-masked-defect]] — perché una manopola che non solleva nasconde l'errore.
- [[deterministic-vs-judgment]] — il lint semantico è giudizio: vede solo ciò che si guarda. Questa
  pagina è l'argomento per spostarne una parte nel deterministico.
- [[step-ritual]] — il punto 3 (lint semantico) è il presidio umano; questa è la sua lista di posti
  dove guardare.
