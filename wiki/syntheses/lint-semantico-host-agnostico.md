---
title: Lint Semantico Host-Agnostico — estensione a controllo globale
type: synthesis
tags: [lint, semantico, host-agnostico, anti-deriva, audit, requirements, spec, tracker, principio-x, n5]
created: 2026-06-06
updated: 2026-06-07
sources: [
  "wiki.config.toml",
  ".claude/skills/wiki-author/wiki-playbook.md",
  "CLAUDE.md",
  "requirements/sertor-core/wiki-creazione/requirements.md",
  "requirements/sertor-core/wiki-llm/TODO.md"
]
---

# Lint Semantico Host-Agnostico — Anti-deriva oltre il wiki

Il **lint semantico** (livello B) è il controllo anti-deriva che verifica che i **claim** di un artefatto
non siano contraddetti dalla **realtà del repo** (codice, test, stato git). Questa pagina ne descrive
l'estensione da "solo wiki" a un **audit globale** su 4 `kind` di artefatti (`wiki`/`requirements`/`spec`/
`tracker`), dichiarati nella sezione `audit` della config.

## Problema reale che risolve

Nel 2026-06-04, il flusso principale ha lavorato su una tabella dati (roadmap di FEAT-003)
in `requirements/sertor-core/wiki-llm/TODO.md` senza verificarla: il contenuto era **stantio**. 
Nessun meccanismo controllava la **coerenza tra artefatti (requirements/spec/tracker) e realtà del progetto** 
(codice in `src/`, stato git). Il lint semantico finora copriva **solo il wiki** (root), 
lasciando fuori il **monte di documentazione** da cui un agente attinge al progetto — un **buco critico di copertura**.

**Lezione:** l'essenza di Sertor è impedire che un agente operi su contesto non reale. Il lint non basta 
su una sola superficie; serve una **rete globale di anti-deriva** su TUTTI gli artefatti.

## Decisione: estendere il lint semantico a host-agnostico (audit globale)

Il 2026-06-06 è stata **formalizzata l'estensione** in tre parti:

### 1. Configurazione: 4 tipi (`kind`) di artefatti da controllare

**`wiki.config.toml` sezione audit** — nuova (2026-06-06). La config dichiara quattro `kind` di artefatti:

1. **Tracker** — TODO.md, tasks.md, checklists: file di stato (`glob: **/TODO.md, specs/**/tasks.md, …`).
2. **Requirements** — tutti i file in `requirements/**/*.md`.
3. **Spec** — tutti i file in `specs/**/*.md` (non-task).
4. **Wiki** — tutti i file in `wiki/**/*.md`.

**Regola matching:** il **primo glob che matcha un file vince**. 
Così `requirements/sertor-core/wiki-llm/TODO.md` cade in **tracker** (non requirements), 
perché il pattern `**/TODO.md` è più specifico e dichiarato prima. 
Ordine nella config: metti i glob più specifici davanti. 
Così anche `specs/007-mcp-sertor-core/tasks.md` cade in tracker anche se sta sotto specs/.

### 2. Playbook: profilo universale di coerenza per `kind`

**`.claude/skills/wiki-author/wiki-playbook.md` operazione `lint` (livello B, semantico):**

| `kind` | Cosa conta come "deriva" | Azione | Note |
|---|---|---|---|
| `wiki` | Claim descrittivo **contraddetto da codice/test**; contraddizioni tra pagine; sommario stantio; coverage | report | [[architettura-wiki-llm]], [[rituale-step-e-allineamento-wiki]] |
| `requirements` | **Solo claim di STATO** (`implementato`, `mergiato`, conteggi, ID); **NON** `«shall X»` non-implementato (= backlog, autorità: codice=comportamento, requisiti=perché) | report | tassonomia: stato git/PR/branch superato, numeri incoerenti, ID inesistenti |
| `spec` | Come `requirements` + coerenza col **codice SE lo stato dichiara "implementato"** | report | idem + verifica signature/funzioni se implementate |
| `tracker` | **Tabelle/checkbox di stato** (`FATTO`/`da fare`, `[x]`/`[ ]`) **contraddette dalla realtà** = **deriva diretta** | report | verità = progresso effettivo (commit, PR, test) |

**Discriminante cruciale:** 
- Un requisito `«REQ-001: shall implementare foo»` **non ancora in codice = BACKLOG, NON DERIVA**. L'autorità è: codice/test = comportamento; requisiti/spec = intento/design.
- Una riga di tracker `[x] linkata a PR #42 mergiata` ma PR #42 **ancora aperta** = DERIVA DIRETTA (lo stato mente sulla realtà).

### 3. Operazione `lint` nel playbook (livello B)

Procedura ripetibile (già documentata in playbook §5.4, ma qui riassunto per contesto):

1. **Baseline:** lint strutturale via CLI (`sertor-wiki-tools lint --json` + `validate`) per wikis.
2. **Estrai claim verificabili** da TUTTE le pagine dell'audit (wiki + requirements + spec + tracker):
   - Conteggi (`53 test`, `4 lingue`, `42 moduli`).
   - Stati (`mergiata`, `in progress`, `branch/PR/commit hash`).
   - Versioni, date, percorsi/simboli citati come esistenti.
   - Checkbox/FATTO di stato.
3. **Recupera ground truth dal repo** (senza reinventare strumenti):
   - **git** (PR/branch/commit) → delega al ruolo VCS (`[roles].vcs`).
   - **Esistenza file/simboli, valori nel codice** → RAG dell'ospite (`search_code`/`find_symbol`) se disponibile; altrimenti `Read`/`Grep`.
   - **Conteggi build/test** → tool dell'ospite (`uv run pytest --collect-only -q`).
4. **Confronta claim ↔ ground truth** → giudica: è una **deriva** se il repo la contraddice.
5. **Report con severità** (Alto/Medio/Basso/Info) + proposta di correzione.
6. **Correggi su conferma** — aggiorna pagine attive; NON riscrivere il registro storico (log.md).

**Host-agnostico (degradazione per profilo):**
- Su ospite **code+doc** (Sertor): tutti i probe.
- Su ospite **solo-doc**: salta probe di codice (simboli, test).
- Su ospite **solo-code**: salta probe doc-specifici (coverage wiki).
- **RAG è acceleratore se c'è, mai prerequisito** (fallback su `Read`/`Grep`).

## Al commit: A + B incrementale (non bloccante)

**Comportamento-obiettivo** (quando automazione B sarà cablata):

- **Livello A (strutturale):** CLI su **target wiki** → 100% meccanico.
- **Livello B (semantico):** su **artefatti del changeset** (incrementale, non repo intero) → per ogni `kind` applicare il profilo della tabella sopra → **report + warning NON bloccante** (mai auto-fix; il valore sta nella rilevazione).

**Caveat di automazione:** B è un giudizio LLM → esecuzione automatica al commit dipende da orchestrazione/trigger (lato deterministico). Per ora il warning al commit copre A e **ricorda di lanciare B incrementale** manualmente (`/wiki lint` sul changeset).

Vedi [[architettura-wiki-llm]] item **"2a FR-004: chiudere il trigger"**.

## Motivazione e lezione assorbita

**Perché:** il controllo di coerenza è una rete, non un muro. Un documento stantio nasconde velocemente se non c'è uno strato di verifica che stacca il suo contenuto dalla realtà. 

**Nessun auto-fix:** il passo di oggi ha deciso che il valore sta nella **RILEVAZIONE** (mettere il segnale davanti all'occhio del flusso principale), non nella correzione automatica. Un esperimento passato di auto-fix LLM si era rivelato troppo rumoroso per la produzione. Default: report-only, correggi su conferma esplicita.

**Host-agnostico (Principio X):** la tassonomia di coerenza (profilo universale per `kind`) è **codificata una volta nel playbook**; la mappatura dei file (config audit) è **ospite-specifica e rileggibile da altri progetti**. Stessa implementazione, due ospiti, due file di config → due reti di audit diversi, senza replicare la logica. Questo è disaccoppiamento vero.

## Collegamento all'architettura

- **[[architettura-wiki-llm]]** — mappa il lint a due livelli nello schema D↔N, item "N5 lint semantico — metodo documentato (variante b)".
- **[[rituale-step-e-allineamento-wiki]]** — il lint semantico è il punto 2 della Definition of Done, eseguito dal flusso principale (Opus, non Haiku) a ogni step.
- **[[ponte-d-n-host-agnostico]]** — il confine operazionale: lint A è 100% D (CLI), lint B è giudizio N (LLM).
- **[[costituzione-v1]]** — Principio X (host-agnosticità) e Principio I (isolamento core) garantiscono che il metodo resti astratto e portabile.
- **Config audit** — la sezione `wiki.config.toml` che mappa artefatti ospite a `kind` universali (documento di configurazione).

## Stato (2026-06-06)

- ✅ Config (sezione audit) estesa a 4 `kind` e 4 `paths` glob nel `wiki.config.toml` di Sertor.
- ✅ Playbook recritto (§5.4 operazione `lint`, tabella profilo universale, procedura ripetibile).
- ✅ Delega chiara: ruolo VCS per git, RAG-ospite o `Read`/`Grep` per simboli, tool locale per test.
- ◑ Automazione B al commit: metodo sì, cablaggio a trigger (FR-004) differito.

---

**Prossimi passo:** esercitare il metodo su contenuti reali.
