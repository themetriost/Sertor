---
title: "E12-FEAT-002 guided-setup — guida agentica install→configure→verify"
type: experiment
tags: [usabilita, guided-setup, skill, agente, agentico, setup, onboarding, deterministic, principio-x, principio-xi]
created: 2026-06-23
updated: 2026-06-23
sources: ["specs/075-guided-setup/plan.md", "packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md", "packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md"]
---

# E12-FEAT-002 guided-setup — guida agentica install→configure→verify

## Essenza

**Prima feature agentica dell'epica E12** `usabilità`: una **skill `guided-setup`** (+**agente concierge**) che guida l'utente di Sertor da «repo non configurato» a «RAG verificato» con un flusso a 6 step, **orchestrando solo i vehicle deterministici** (CLI `sertor install`, `sertor configure`, `sertor-rag doctor/index`, mai reimplementandoli). La skill è **host-agnostica** (Claude ↔ Copilot via `sertor install rag` standard) e il nucleo è **puro**: nessun LLM nel processo, gate richiede **consenso esplicito** per mutazioni/download (read-only libero).

Realizza il **confine D↔N** vincolante: il core non chiama mai un LLM, l'agente orchestrator sceglie e invoca i vehicle, la skill incapsula il **come** (le istruzioni).

## Decisioni di design

### DA-G1: Skill + Agente concierge (non skill-only)

Richiesta originaria dell'utente: entrambi, con `sertor-flow` come precedente realizzato. La **skill portava il «come»** (istruzioni ai 6 step, call al vehicle); l'**agente concierge**:
- **Orchestratore:** riceve la richiesta «install RAG» / «configura i segreti», li inida verso la skill
- **Singolo entry point:** per adesso **un solo ramo** (dispatcher sottile), ma in FEAT-009 si espanderà a multi-ramo (concierge pieno: install RAG / configura / recupero errori / ecc.)
- **Model pin:** `model: sonnet` su Claude (omesso su Copilot per lezione FEAT-011/049: gli agenti Copilot senza `model:` usano il default dell'assistente)

### DA-G2: Euristica provider minimale + conferma

**Decisione da FEAT-004** (ricerca semantica memoria): profilazione ricca rimane fuori (Would). La skill propone il provider **adattively ma minimale** (euristica: «hai credenziali cloud? ☁️  ; vedi che la NL semantica è importante? 🔤 ») e chiede **conferma esplicita** — l'utente sceglie, non è scelto. Tre profili: `local-nlp` (default, glove), `local-basic` (hash), `azure` (se credenziali rilevate).

### DA-G3: Esecuzione su conferma (read-only libero)

**Gate di consenso:**
- **Read-only (libero):** mostrare i passi che verranno eseguiti, effettuare `doctor` diagnostico, leggere var env
- **Mutazioni (su conferma):** install CLI, download GloVe (avviso una-tantum e size 822 MB), index (operazione lunga)
- **Segreti (secure):** collect credenziali via getpass (no echo), conferma prima di scrivere su `.sertor/.env`

### Distribuzione dual-target: riuso del pattern `sertor-flow`

Entrambi gli asset (skill + agente) viaggiano via `sertor install rag` standard **riusando il meccanismo agenti** del kit (`Surface.AGENT` + `render_custom_agent` + `AssistantProfile`). **Nessun seam nuovo nel kit:** il kit conosce già come depositare agenti (da FEAT-007/009). Estensione **minima:** `install_rag.py` (render-aware di skill+agent dai parametri), guardia di **parità estesa** (il `model: sonnet` non leakka su Copilot), closure per-nome garantita (ogni pagina/skill citata dai body agenti è depositata, guardia offline lo verifica).

## Architettura

### Componenti

#### Skill `guided-setup` (host-agnostica)

File: `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md`

**Istruzioni a 6 step (body puro, no hardcoded path/comandi Claude/assistente):**

1. **Detect** — Diagnostica: esegui `sertor-rag doctor` (sola lettura, nessun download)
   - Se verde → «Already good, skip to step 6 (verify live)»
   - Se giallo/rosso → prosegui

2. **Choose provider** — Euristica minimale + conferma
   - Chiedi: «Hai credenziali Azure OpenAI o altro cloud?» → proponi `azure`
   - Chiedi: «Vuoi semantica in NL (ricerca per significato)?» → `local-nlp` (glove, 822 MB) vs `local-basic` (hash, offline immediato)
   - Mostra il profilo proposto, chiedi conferma

3. **Install CLI** — Su conferma: `sertor install rag` (il vehicle, mai reimplementato)
   - Controlla exit code, segnala errori, prosegui

4. **Configure secrets** — Colleziona credenziali (se Azure: AZURE_OPENAI_* o Ollama se local)
   - Via tool getpass (no echo a terminale)
   - Salva via `sertor configure --set KEY=VAL` (il vehicle)
   - Preview: mostra i campi che saranno scritti (valore \***masked\**)

5. **Index** — Su conferma: `sertor-rag index .`
   - Se glove → avviso una-tantum (download 822 MB, 2–5 min dipende latenza)
   - Progressione step, indice completo

6. **Verify** — `sertor-rag doctor` online
   - Tutte le 4 aree passano? → **«RAG ready!»**
   - Gialli/rossi? → mostra rimedi concreti, archivia i log in `.sertor/` per debug futuro

**Proprietà:**
- Puro: nessun LLM, nessuna decisione inferita da ragionamento
- Idempotente: re-run a step N è sicuro (config non distruttiva, upsert idempotente)
- Host-agnostico: nessun `/command` Claude, nessun path assoluto, nessun nome assistente
- Vehicle-only: ogni mutazione delegata ai command CLI vehicle

#### Agente `concierge` (host-agnostico, un ramo per MVP)

File: `packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md`

**Profilo:** **Helper specializzato di setup per Sertor** (disambiguazione dal main assistant). Riceve richieste user come «ho scaricato Sertor, come installo?» e decide il **target skill** (oggi: skill `guided-setup`, ramo unico).

**Frontmatter:**
```yaml
agent: concierge
description: Setup helper for Sertor — guides install/configure/verify
model: sonnet  # ← Claude only (omesso su Copilot, uses default)
model_per_host: {"claude": "sonnet", "copilot-cli": ""}  # fallback Copilot
```

**Body:** Istruzioni esplicite
- Intento: se l'utente chiede help con install/config/diagnostica, invia verso skill `guided-setup`
- Scope: setup/onboarding di base
- Out-of-scope: uso avanzato (memoria, multi-corpus, reranking), troubleshooting custom, feature request → rimanda al main assistant

**Architettura di FEAT-009 (futura):** concierge si espande a multi-ramo — per ora dispatcher sottile.

### Distribuzione dual-target: estensione build plan

**`install_rag.py` → `build_rag_assets_plan`** (modificato da FEAT-007/009):
- Legge from package come prima:
  - skill `wiki-author` + agente `requirements-analyst`
  - agente `concierge` (NEW)
- Deposita via `Surface.AGENT` + `render_custom_agent`:
  - Claude `.claude/agents/concierge.md` (con `model: sonnet` preesente)
  - Copilot `.github/agents/concierge.md` (con `model:` omesso)

**Guardia di parità estesa:**
- Sentinella: `model: sonnet` solo in body Claude, non in Copilot
- Closure: ogni wikilink citato dai body agenti risolve a skill depositata (guardia offline lo verifica)
- Test `test_assets_copilot_parity.py` FAIL se `model: sonnet` leaked su Copilot

### Osservabilità

Evento `guided_setup_executed` metrics-only:
```json
{
  "operation": "guided_setup",
  "profile_chosen": "local-nlp|local-basic|azure",
  "steps_completed": 6,
  "exit_code": 0,
  "index_size_mb": 42
}
```

Niente query, niente credenziali, niente path.

## Scope e non-scope

**Incluso:**
- 6-step flusso assist + euristica provider minimale
- Consenso esplicito per mutazioni
- Skill `guided-setup` + agente concierge distribuiti
- Dual-target (Claude/Copilot) via installler standard

**Escluso (deferred):**
- Profilazione ricca provider (FEAT-004, Would) — euristica minimale adesso
- Troubleshooting custom (es. «perché il doctor dice WARN su MCP?») — FEAT-009 concierge multi-ramo
- Auto-remediation (es. «fix, restart, retry») — agente con porte a build_doctor (più in là)
- Integrazione interattiva terminal (es. TUI durante setup) — FEAT-006 (gui/tui future)
- Multi-language UX (EN/IT) — FEAT-012 epica (governess)

## Esiti

### Test
- Root **363 passed / 0 skipped** (sertor-core invariato, non regression)
- Sertor **363 passed** (installer package invariato, test nuovi nel plan/spec check)
- Sertor-flow **134 passed** (invariato)
- Install-kit **131 passed** (invariato)
- ruff clean

### Constitution
**PASS 12/12 + missione senza deroghe:**
- Principio X (host-agnosticità): skill e agente body puri, NO hardcoded assistente path/comandi
- Principio XI (vehicle-only): skill orchestra SOLO CLI vehicle, mai call diretta a core
- Principio XII (fail-loud): diagnostica via `doctor`, non inferenza

### File

Nuovi:
- `packages/sertor/src/sertor_installer/assets/rag/skills/guided-setup/SKILL.md` (istruzioni)
- `packages/sertor/src/sertor_installer/assets/rag/agents/concierge.md` (agente + model pinning)
- `tests/unit/test_guided_setup_parity.py` (guardia parità `model: sonnet` leak)
- `tests/unit/test_guided_setup_closure.py` (verifica closure skill+agent references)

Modificati:
- `packages/sertor/src/sertor_installer/install_rag.py` → deposita skill + agente, `render_custom_agent` preso da `AssistantProfile`
- `packages/sertor/tests/unit/test_assets_copilot_parity.py` → esteso (nuovo agente + check model field)

## Backlink

- [[assistant-targeting]] — Embodiment del dual-target: skill+agente per due assistenti, riuso pattern FEAT-007
- [[sertor-flow]] — Modello di riferimento per skill+agente (governance installer)
- [[feat-074-doctor-salute]] — Il `doctor` che la skill usa per verify (6-step Step 1 e 6)
- [[mission-vision]] — Principio X operativo: setup agentico host-agnostico
- [[memoria-conversazioni]] — Approfondimento futuro: guided-setup salva sessioni di setup in archivio episodico

## Pendente (non-bloccante)

- **Prova LIVE su ospiti reali:** Claude Code + GitHub Copilot CLI con `sertor install rag` e skill `guided-setup` invocata (non ancora eseguita, R-4)
- **FEAT-009 concierge multi-ramo:** oggi dispatcher sottile, si espande in FEAT-009 a gestire install/configure/recover (prossimo step)
- **FEAT-010 integrazione MCP:** agente concierge potrebbe esporre un tool MCP «skip to step X» per integrazione deep con conversation flow (futuro)
- **Tema lingua asset:** skill/agente in EN (FEAT-012 è la feature per localizzazione host)

## Note

La **skill + agente** è la realizzazione più semplice del pattern agentico: la skill incapsula il «come deterministico», l'agente è il «quando/perché» e scelge il modello. Non è CQRS (command-query), è orchestrazione + istruzione. La decisione DA-G1 (entrambi, non skill-only) riflette la pratica FEAT-007/009 che non ha permesso semplificazione oltre, e aumenta la *serendipità* dell'esperienza (l'agente accoglie, la skill guida, il finale è controllato).

Il **ripubblicheur UA** dell'entità ospite FEAT-003 wizard + FEAT-009 memoria capisce il flusso: wizard vede le scelte di provider, ospite che riceve l'installer via FEAT-009 ha già skill+agente disponibili, non crea link rotto all'attivazione.
