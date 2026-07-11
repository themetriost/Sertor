---
title: "Richiesta utente Copilot — default model assignment per agenti installati da Sertor"
type: source
tags: [usersfeedback, copilot-cli, subagents, model-policy, installer, distribuzione]
created: 2026-06-30
updated: 2026-07-01
source: utente Copilot (richiesta feature, 2026-06-30)
status: elaborata (2026-07-01)
---

# Richiesta utente: default model assignment per agenti Copilot installati da Sertor

> **Fonte:** richiesta di un utente GitHub Copilot CLI (2026-06-30). Riportata **integrale**
> qui sotto; l'analisi Sertor-side è in fondo, chiaramente separata. Da elaborare → backlog
> (FEAT in epica) + eventuale decomposizione requirements; poi spostare in `processed/`.

## Richiesta (verbatim)

Quando Sertor installa la suite agenti per GitHub Copilot CLI, vorremmo che configuri anche una
policy di default per i modelli dei subagent, invece di lasciare tutto alla selezione implicita
della CLI.

### Motivazione

La suite contiene agenti con profili cognitivi diversi:
- alcuni sono dispatcher o task meccanici;
- altri fanno scrittura strutturata e reasoning;
- altri ancora fanno analisi di coerenza ad alto impatto;
- l'implementazione deve essere affidabile e coerente con il resto del flusso SpecKit.

Avere una mappa modello/agente predefinita riduce variabilità tra installazioni, migliora
costo/latenza dove possibile e mantiene qualità alta sulle fasi critiche.

### Config desiderata per Copilot CLI

La configurazione va applicata al profilo Copilot CLI dell'utente, nel blocco
`subagents.agents.<agent-name>.model`. Policy proposta:

```json
{ "subagents": {
    "agents": {
      "concierge": { "model": "claude-haiku-4.5" },
      "configuration-manager": { "model": "claude-haiku-4.5" },
      "requirements-analyst": { "model": "claude-sonnet-4.6" },
      "requirements": { "model": "claude-sonnet-4.6" },
      "speckit.specify": { "model": "claude-sonnet-4.6" },
      "speckit.clarify": { "model": "claude-sonnet-4.6" },
      "speckit.plan": { "model": "claude-sonnet-4.6" },
      "speckit.tasks": { "model": "gpt-5.4-mini" },
      "speckit.analyze": { "model": "gpt-5.5" },
      "speckit.implement": { "model": "claude-sonnet-4.6" },
      "speckit.constitution": { "model": "gpt-5.5" },
      "speckit.checklist": { "model": "gpt-5.4-mini" },
      "speckit.taskstoissues": { "model": "gpt-5.4-mini" },
      "wiki-curator": { "model": "claude-sonnet-4.6" }
    } }
}
```

### Razionale sintetico (proposto dall'utente)

| Agente | Default | Razionale |
|---|---|---|
| concierge | claude-haiku-4.5 | Dispatcher/setup stub: basso carico cognitivo |
| configuration-manager | claude-haiku-4.5 | Operazioni git guidate e bounded; economico e veloce |
| requirements-analyst / requirements | claude-sonnet-4.6 | Requisiti, EARS, MoSCoW: serve buon giudizio |
| speckit.specify / clarify / plan | claude-sonnet-4.6 | Scrittura e design strutturato |
| speckit.tasks | gpt-5.4-mini | Decomposizione task abbastanza meccanica |
| speckit.analyze | gpt-5.5 | Cross-artifact analysis: alto reasoning |
| speckit.implement | claude-sonnet-4.6 | Implementazione affidabile e coerente con planning/design |
| speckit.constitution | gpt-5.5 | Raro ma critico: principi e versioning |
| speckit.checklist | gpt-5.4-mini | Checklist/unit test dei requisiti: strutturale |
| speckit.taskstoissues | gpt-5.4-mini | Conversione task → issue, meccanica |
| wiki-curator | claude-sonnet-4.6 | Sintesi, anti-drift, link e log richiedono qualità |

### Requisiti implementativi (proposti dall'utente)

1. L'installer Sertor dovrebbe applicare questa configurazione **solo per Copilot CLI**.
2. Deve fare **merge non distruttivo** con eventuali configurazioni utente già presenti.
3. Se un agente ha già un modello esplicitamente configurato dall'utente, **non sovrascriverlo
   senza conferma**.
4. La configurazione dovrebbe essere **idempotente**.
5. I model ID dovrebbero essere **centralizzati in un profilo/versione**, così da poter aggiornare
   la policy quando cambiano i modelli disponibili.
6. Se un modello **non è disponibile** nel tenant/ambiente, l'installer dovrebbe: segnalare
   chiaramente il fallback; **non fallire silenziosamente**; preferire un fallback della stessa
   classe di costo/qualità.

### Nota dell'utente

Questa policy è un **default ragionato, non una regola rigida**: l'utente deve poterla modificare
via `/subagents` dopo l'installazione.

---

## Analisi Sertor-side (NON parte della richiesta — da confermare in elicitazione)

- **Allineamento alla mission:** è UX/qualità della distribuzione (epica E2 `sertor-cli` /
  cross-ref E12 usabilità), periferico al differenziatore code+doc ma serve adozione/coerenza.
- **Da verificare contro la doc ufficiale Copilot CLI** (regola standing «leggi la doc, non
  inventare»): che `subagents.agents.<name>.model` sia il **formato e il percorso reali** della
  config dei subagent Copilot CLI, e **dove** vive il file (profilo utente vs repo). Tutta la
  fattibilità dipende da questo.
- **NON contraddice la regola `model:` omesso** di FEAT-011/049: lì il problema era il `model:`
  nel **frontmatter** dell'agente (invalido su Copilot); qui è un **meccanismo diverso** (config
  dei subagent della CLI). Confine da dichiarare esplicitamente per non confondere i due.
- **Cross-pacchetto:** la policy copre agenti di **`sertor`** (concierge, wiki-curator) **e** di
  **`sertor-flow`** (requirements-analyst, configuration-manager, requirements, `speckit.*`) → il
  wiring tocca **entrambi** gli installer; gli `speckit.*` sono vendorati da spec-kit (i loro nomi
  e l'esistenza dipendono dal `specify init`).
- **Model-ID datati:** gli ID (`gpt-5.5`, `claude-sonnet-4.6`, `claude-haiku-4.5`, `gpt-5.4-mini`)
  invecchiano → centralizzarli in un profilo versionato (requisito 5) è il punto chiave per non
  spargere ID nel codice.
- **Policy di modello mista (Claude + GPT):** la proposta assegna modelli **OpenAI/GPT** ad alcuni
  agenti `speckit.*` — disponibilità per-tenant non garantita (requisito 6 sul fallback è centrale).
  Sertor è agnostico al provider del modello; la policy resta un default modificabile.
- **Idempotenza/merge non distruttivo:** allineato ai pattern installer esistenti (`merge_*`,
  `SETTINGS_MERGE`); il rispetto del modello già scelto dall'utente (req. 3) richiede un merge
  che **non** sovrascriva chiavi pre-esistenti senza conferma.
- **Default modificabile:** coerente con la natura non-distruttiva dell'installer (req. nota utente).

## Esito elaborazione (2026-07-01)

### Elaborazione in E2-FEAT-015

La richiesta è stata **elaborata e implementata** nella feature **E2-FEAT-015** del backlog epica `sertor-cli`:
- **Branch:** `083-default-model-policy-copilot` (PR #135)
- **Status:** ✅ Implementata; CI verde (Win+Linux), Constitution 12/12, ruff clean
- **Scope realizzato:** 5 agenti Sertor-authored (concierge, configuration-manager, requirements-analyst, requirements, wiki-curator)
- **Meccanismo reale:** campo `model:` nel frontmatter `.agent.md` di Copilot CLI (forma nativa), fonte unica versionata `model_policy.py` nel kit, fail-loud install-time, guardie riconciliate
- **Finding di verifica chiave:** il meccanismo config `subagents.agents.<name>.model` è runtime settings di Copilot CLI (user `~/.copilot/settings.json`); il default nel frontmatter è il luogo corretto per install-time e al sicuro dagli upgrade per costruzione

### Scope out dichiarato

- **Agenti vendorati (`speckit.*`):** rimandati a **FEAT-016** (Could, post-verifica supporto `model:` sui prompt-file di spec-kit)

### Pagine wiki di riferimento

- [[feat-083-default-model-policy-copilot]] — Record completo dell'implementazione (experiment)
- [[assistant-targeting]] — Sezione nuova «Default model-policy per-agente» (tech)
- [[sertor-install-kit]] — Nuovo modulo `model_policy.py`
