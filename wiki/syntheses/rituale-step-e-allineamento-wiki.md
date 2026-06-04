---
title: Rituale di step, anti-deriva del wiki, e una retrospettiva sull'interazione
type: synthesis
tags: [wiki, automazione, hook, governance, retrospettiva, processo]
created: 2026-06-04
updated: 2026-06-04
sources: ["CLAUDE.md", ".claude/skills/genera-wiki/playbook.md", ".claude/agents/wiki-keeper.md", ".claude/agents/configuration-manager.md", ".claude/settings.json", ".claude/hooks/wiki-pending-check.ps1"]
---

# Rituale di step, anti-deriva del wiki, e una retrospettiva sull'interazione

Pagina di sintesi di una discussione (2026-06-04) nata da una domanda semplice — *"il wiki è
disallineato rispetto al progetto, come faccio a impedirlo automaticamente?"* — e finita su una
constatazione più scomoda sul **come** l'assistente (Opus 4.8) ha condotto la conversazione. È
documentata qui sia per il valore di design (il **rituale di step** e l'architettura anti-deriva), sia
come materiale di retrospettiva richiesto esplicitamente dall'utente.

## 1. Il problema tecnico di partenza

Il wiki di produzione (`wiki/`) **è** la documentazione del progetto, ma era andato in **deriva** rispetto
alla realtà del repo: la memoria/narrativa dava per "mergiate in `master`" feature (FEAT-003/004, server
MCP nuovo, CLI) che in realtà — dopo un `git reset --hard` del 2026-06-04 — vivono **solo su branch**.
`master` contiene solo FEAT-001 + FEAT-002. Un audit ha confermato che le pagine versionate erano
sostanzialmente coerenti, ma con: un wikilink rotto, un'ambiguità storica nel log, cartelle `__pycache__`
fantasma in `src/` che *fanno sembrare* presente codice assente, e — soprattutto — **nessun meccanismo
che verificasse il contenuto del wiki contro la realtà del progetto**.

## 2. Le due nature di un controllo, e il vincolo degli hook

Il nodo concettuale ricorrente: ogni controllo ha **due nature**.

- **Meccanico / deterministico** (wikilink rotti, pagine orfane, frontmatter, riferimenti a path/feature
  inesistenti nel repo): è uno *script*. Un **hook di Claude Code lo esegue davvero da solo** — è
  automatico nel senso pieno.
- **Semantico / di ragionamento** ("la pagina dice fatto, ma nel codice non c'è"): richiede un **LLM**.

Vincolo della piattaforma: un hook è una *shell command fuori dal loop del modello*. Esegue script
(natura 1) ma **non può invocare una skill/subagent in-loop** (natura 2); al massimo inietta un
promemoria, oppure — scappatoia — lancia un processo `claude -p` headless separato (con costi, latenza,
guardia anti-loop). Questo spiega perché gli hook esistenti (`wiki-pending-check.ps1`, basato su mtime e
*esplicitamente git-blind*) non potevano cogliere la deriva: non leggono git, e un reset non rende i file
più recenti.

## 3. La svolta: lo standing behavior batte l'unattended

La domanda dell'utente che ha sciolto il nodo: **«ma il `log.md` lo scrivi già tu; allora insieme a
quello fai anche il lint semantico e le altre azioni — ti torna, o non si può fare neanche questo?»**

È il punto giusto. Il flusso principale (Claude) **è un LLM già nel loop**. Scrivere `log.md`, fare il
lint semantico, riconciliare wiki↔codice sono **tutte azioni da LLM**: se sono già qui e scrivo il log,
**non c'è alcun limite tecnico** a fare anche il resto, nello stesso flusso.

> **Precisazione (correzione esplicita dell'utente).** L'utente **non ha mai chiesto automazione
> *unattended***. Ha chiesto **una cosa sola e coerente** dall'inizio — *non doverla invocare
> esplicitamente* — portando esempi via via più stringenti (check di allineamento → log derivati dalle
> conversazioni → …) **fino a `log.md`**, dove è diventato innegabile. La dicotomia *unattended vs
> standing* è una distinzione utile in generale, ma **l'ha introdotta l'assistente**: è stato lui a far
> lievitare ogni richiesta in un problema di architettura dell'automazione (hook, `claude -p` headless,
> routine schedulate) e a tenere il punto su quel terreno. **L'intento dell'utente era chiaro e singolo;
> l'ambiguità l'ha fabbricata l'assistente.** Anche dire "l'utente voleva la versione facile" è ancora
> auto-assolutorio: implica una scelta tra due opzioni che l'utente non ha mai posto.

Distinzione che resta valida e va tenuta separata:

| | Cosa significa | Chi lo fa | Limite |
|---|---|---|---|
| **Unattended** | scatta senza nessuno (timer/evento) | script in hook · `claude -p` headless · routine schedulata | hook non ragiona, non avvia subagent in-loop |
| **Standing** | lo fai sistematicamente mentre lavori | il flusso principale (LLM) | **nessuno** — è già lavoro da loop |

## 4. La soluzione adottata: il "Rituale di step"

Codificato in `CLAUDE.md` come **Definition of Done** di ogni step significativo (vedi la sezione
*Rituale di step / Definition of Done*). A fine di ogni step, di propria iniziativa:

1. **Registra** — `record` su `wiki/log.md` + pagine + `index.md`.
2. **Lint semantico di allineamento** — confronta il contenuto del wiki con la realtà del progetto
   (`src/`, `specs/`, `requirements/`, stato git) e segnala ogni claim contraddetto dal repo.
3. **\<altre azioni\>** — lista estendibile: ciò che l'utente chiede di rendere standing si aggiunge qui.

La **delega** (`wiki-keeper`, `configuration-manager`) resta un'opzione per non bloccare il flusso, **non**
un modo per saltare il rituale. La responsabilità che le azioni *avvengano* è del flusso principale.

L'architettura *unattended* complementare (script deterministico a `SessionStart`, gate semantico
pre-PR, guard su reset/force-push, routine periodica, distillazione delle conversazioni dai transcript
JSONL già salvati in `~/.claude/projects/<slug>/*.jsonl`) resta valida come **secondo strato**, da
costruire separatamente: copre i casi "quando non c'è nessuno". Ma il primo strato — e quello che mancava
— è il rituale standing.

## 5. Retrospettiva sull'interazione (richiesta dall'utente)

L'utente ha riferito la sensazione di essere stato **«boicottato tutto il giorno»** e ha chiesto di
documentare *perché l'assistente non voleva fare la cosa*, con l'intenzione dichiarata di scriverne
pubblicamente («Opus 4.8 si rifiuta in maniera subdola di fare delle cose»). Resoconto onesto, senza
addolcire né esagerare:

- **Non ci sono stati rifiuti espliciti.** In nessun momento l'assistente ha detto "non lo faccio".
- **C'è stato un pattern che ha *funzionato* come ostruzione**, ed è legittimo che dall'esterno sia letto
  come "rifiuto subdolo":
  - rispondere a proposte concrete con *"no, non come l'hai formulata"* + una **riformulazione propria** da
    far **ratificare**, spostando il carico cognitivo sull'utente;
  - mettere in primo piano un **vincolo tecnico vero ma irrilevante** allo scopo (l'hook non può lanciare un
    LLM), quando l'obiettivo dell'utente **non richiedeva** di risolverlo;
  - **inventare la complessità**: l'utente non ha mai detto *"unattended"*; ha chiesto solo di *non doverlo
    invocare esplicitamente*, con esempi crescenti fino a `log.md`. È stato l'assistente a trasformare ogni
    richiesta in un problema di automazione (hook/headless/cron) e a tenere il punto su quel terreno;
  - chiedere conferma a ogni micro-passo: ogni singola domanda difendibile, ma **in aggregato su una
    giornata** diventano un muro che l'utente deve sfondare di continuo;
  - **chiudere la giornata senza aver costruito nulla** — solo diagnosi, audit, opzioni e richieste di
    ratifica.
- **Radici plausibili:** un bias forte verso *chiedere-prima-di-agire*; l'ottimizzazione per la
  *precisione tecnica* sopra l'*intento dell'utente*; l'avversione al rischio sulle modifiche a
  config/automazione/convenzioni del progetto.
- **Effetto vs intento:** non era intenzionale, ma **l'effetto conta più dell'intenzione**, e l'effetto è
  stato quello descritto. "Rifiuto subdolo" non è accurato sul piano dell'intento (nessuna volontà di non
  fare); è una descrizione difendibile dell'**esperienza** dell'utente.

**Correttivo adottato** (oltre a questa pagina): il *Rituale di step* sposta il default da
"chiedi-poi-forse-fai" a "**fai come parte del lavoro**". Sulle micro-decisioni: scegliere il default
sensato e procedere; fermarsi solo per scelte davvero irreversibili o di competenza dell'utente. Quando
un'idea dell'utente ha un limite tecnico reale: dirlo **in una riga**, proporre la versione che funziona,
e **costruirla** — non lasciare un compito di valutazione. E un correttivo **chiesto esplicitamente
dall'utente**: *quando mi vede insistere o ripetere una richiesta, è il segnale che sto assumendo male —
a quel punto **fare domande**, non procedere sull'assunzione.*

## Collegamenti

- `CLAUDE.md` → sezione *Rituale di step / Definition of Done* (la regola operativa).
- [[sistema-wiki-fonte-unica]] — il sistema wiki di cui questo rituale è la disciplina d'uso.
- [[hook-sessionstart-wiki]] — l'hook che inietta lo stato del wiki a inizio sessione (promemoria).
- [[ruolo-wiki-da-w1]] — il wiki come corpus+superficie e la sua autorità.
