---
title: Rituale di step e anti-deriva del wiki
type: concept
tags: [wiki, automazione, hook, governance, processo, delega, fonte-unica, rituale-di-step]
created: 2026-06-04
updated: 2026-06-05
sources: ["CLAUDE.md", ".claude/skills/wiki-author/wiki-playbook.md", ".claude/agents/wiki-curator.md", ".claude/agents/configuration-manager.md", ".claude/settings.json", ".claude/hooks/wiki-pending-check.ps1"]
---

# Rituale di step e anti-deriva del wiki

Il **rituale di step** è la *Definition of Done* di ogni step significativo: a fine lavoro il flusso
principale, di propria iniziativa, registra nel wiki e verifica che il wiki non sia andato in **deriva**
rispetto al repo. Nasce da una discussione del 2026-06-04 ("il wiki è disallineato dal progetto, come lo
impedisco?") e dalla scoperta che, essendo l'LLM **già nel loop**, queste azioni sono *standing behavior*,
non automazione esterna. La retrospettiva sul *come* di quella conversazione è una pagina a sé:
[[retrospettiva-interazione-2026-06-04]].

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

La **delega** (`wiki-curator`, `configuration-manager`) resta un'opzione per non bloccare il flusso, **non**
un modo per saltare il rituale. La responsabilità che le azioni *avvengano* è del flusso principale.

L'architettura *unattended* complementare (script deterministico a `SessionStart`, gate semantico
pre-PR, guard su reset/force-push, routine periodica, distillazione delle conversazioni dai transcript
JSONL già salvati in `~/.claude/projects/<slug>/*.jsonl`) resta valida come **secondo strato**, da
costruire separatamente: copre i casi "quando non c'è nessuno". Ma il primo strato — e quello che mancava
— è il rituale standing.

## 4a. Confine di delega: record vs lint semantico

La delega (`wiki-curator` Haiku, `configuration-manager` Haiku) è uno strumento per **ridurre il carico
del flusso principale** mantenendo il rituale in piedi, **non** per eludere responsabilità. Due azioni,
due modelli di delega diversi:

| Azione | Natura | Delega | Motivo |
|--------|--------|--------|--------|
| **record** | **Trascrizione strutturata** (brief → pagine, backlink, index, voce log) | ✅ Sì, `wiki-curator` (Haiku) | Lavoro di forma, retto dal brief. L'agente legge il brief una volta, esegue i passi meccanici del playbook (creare/aggiornare file, link). Meno costoso in token. |
| **lint semantico di allineamento** | **Giudizio su contenuti** (wiki ↔ codice/spec/repo). Richiede ragionamento e contesto. | ❌ No, flusso principale (Opus) | Il giudizio "il wiki contraddice il codice?" richiedente il contesto dello step appena completato. Rieleggere a freddo per delegare = rileggere 30KB di file, perdere il contesto, rischio di giudizi lossy o falsi positivi. Il flusso principale ha già la visione. Se in casi pesanti serve delega, override a `sonnet` per-invocazione, mai il default Haiku. |

**Implicazione operativa:** il rituale rimane **integralmente responsabilità del flusso principale**, che
può delegare la trascrizione a Haiku per velocità, ma **giudizio e riconciliazione wiki↔repo restano in
casa**. Se il brief del record è povero (pochi dettagli), il wiki rimane disallineato silenziosamente:
il brief è la qualità della trascrizione — il flusso principale deve vigilare che sia ricco abbastanza.

## 5. Fonte unica del rituale: CLAUDE.md come autorità (decisione 2026-06-05)

**Contesto.** Fino al 2026-06-05, il Rituale di step viveva in due posti:
1. `CLAUDE.md` § *"Rituale di step / Definition of Done"* — istanza **operativa** concreta (cita `wiki/log.md`, `src/`, agenti `wiki-curator` / `configuration-manager`, il confine di delega in termini Sertor).
2. `plugins/step-ritual/` — principio **astratto/portabile** repository-agnostico, archivio di asset esportabili (il plugin non era installato, nunca committato; vive in `.claude-plugin/marketplace.json`).

**Riconoscimento chiave.** Non erano "due copie derivate" ma **due livelli di astrazione**:
- **`CLAUDE.md`:** versione concreta, operativa *per questo workspace*; è il contesto vivo che l'LLM legge a ogni step.
- **`plugins/step-ritual/`:** distillazione portabile per il futuro, quando il rituale sia stabile (ora no, è già cambiato 2 volte il 2026-06-04/05).

**Vincolo decisivo.** Il rituale è **standing behavior** (azione da LLM nel loop, sistematica, senza dipendenza da automazione esterna). Standing behavior NON può vivere in un plugin/asset che **non è garantito in contesto**: uno skill di plugin non è iniettato in contesto a ogni step come lo è `CLAUDE.md`. Quindi:

> La versione **operativa** (autorità) **deve** stare in `CLAUDE.md` e **solo** lì, finché il rituale evolve. Non mantenere due autorità parallele a mano.

**Decisione (dall'utente).** **Fonte unica = `CLAUDE.md`.** I file plugin `plugins/step-ritual/` e `.claude-plugin/marketplace.json` sono stati **cancellati** (erano untracked, mai committati → zero "seconde copie", zero causa di deriva).

**Backlog differito (non abbandonato).** Quando la sezione *"Rituale di step"* in `CLAUDE.md` sarà **matura/stabile**, riesportarla come plugin portabile repository-agnostico (asset riusabile; coerente col goal toolset enterprise di Sertor). In quel momento ridecidere il nome (`step-ritual` era provvisorio), il collocamento nel marketplace, e se Sertor debba consumarlo (dogfooding) o limitarsi a esportarlo. La decisione rimanda a una stabilizzazione del rituale stesso.

## La retrospettiva è una pagina a sé

La discussione del 2026-06-04 ha prodotto anche una **retrospettiva onesta sul *come*** l'assistente ha
condotto la conversazione (l'esperienza di "ostruzione" riferita dall'utente, le radici, il correttivo).
Per atomicità — è il *come*, non il *cosa* deciso — vive ora in una pagina separata:
[[retrospettiva-interazione-2026-06-04]].

## Collegamenti

- `CLAUDE.md` → sezione *Rituale di step / Definition of Done* (la regola operativa).
- Sezione *Confine di delega* (4a) — precisazione su quale azione delegare a Haiku (`record`) vs mantenere in casa (`lint semantico`).
- [[retrospettiva-interazione-2026-06-04]] — la retrospettiva sull'interazione che ha originato il rituale.
- [[lint-organizzativo-e-reorg]] — il lint livello C, che estende l'anti-deriva all'organizzazione del wiki.
- [[sistema-wiki-fonte-unica]] — il sistema wiki di cui questo rituale è la disciplina d'uso.
- [[hook-sessionstart-wiki]] — l'hook che inietta lo stato del wiki a inizio sessione (promemoria).
- [[ruolo-wiki-da-w1]] — il wiki come corpus+superficie e la sua autorità.
