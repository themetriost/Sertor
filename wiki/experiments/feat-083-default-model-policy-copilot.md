---
title: "E2-FEAT-015 default model-policy per subagent Copilot CLI"
type: experiment
tags: [feat-015, sertor-cli, copilot-cli, installer, model-policy, distribuzione, subagents]
created: 2026-07-01
updated: 2026-07-01
sources: ["packages/sertor-install-kit/src/sertor_install_kit/model_policy.py", "packages/sertor/src/sertor_installer/install_rag.py", "packages/sertor-flow/src/sertor_flow/install_governance.py", "specs/083-default-model-policy-copilot/plan.md", "requirements/sertor-cli/default-model-policy/requirements.md", "PR #135"]
---

# E2-FEAT-015: default model-policy per subagent Copilot CLI — Implementata

**Status:** ✅ **Implementata** (2026-07-01). Branch `083-default-model-policy-copilot`, PR #135, CI verde (Win+Linux).

**Autore:** Utente (richiesta 2026-06-30, elaborata in FEAT-015 backlog epica E2-sertor-cli).

## Che cosa è stato fatto

L'installer Sertor **assegna un modello LLM di default a cada agente Sertor-authored** resi come custom-agent su GitHub Copilot CLI, centralizzando la policy e prevenendo la deriva runtime.

### Sostanza tecnica

#### 1. Fonte unica versionata

Nuovo modulo `packages/sertor-install-kit/src/sertor_install_kit/model_policy.py`:
- Costante `MODEL_POLICY_VERSION = "1.0.0"` (versioning decoupled)
- Mappa esplicita agente→modello per i **5 agenti Sertor-authored** in scope:
  - `concierge`, `configuration-manager` → `claude-haiku-4.5` (dispatcher, basso carico cognitivo)
  - `requirements-analyst`, `requirements`, `wiki-curator` → `claude-sonnet-4.6` (reasoning e sintesi)
- Funzioni pure `resolve_model(agent_name, policy_version)` fail-loud su agente fuori ambito
- Costanti `IN_SCOPE_AGENTS`, `resolve_model`, `MODEL_POLICY_VERSION` importate **da entrambi** i pacchetti (`sertor` + `sertor-flow`) → niente drift, niente dipendenza cross-pacchetto

#### 2. Integrazione con il render

`render_custom_agent(…, model: str | None)` esteso:
- Riceve il modello dal profilo/policy
- Scrive il campo `model:` nel frontmatter `.agent.md` di Copilot CLI
- Claude path byte-identico (niente eco dell'alias)

#### 3. Fail-loud install-time

Nuovo errore `ModelPolicyError` a `build_rag_plan()` / `build_governance_plan()` se:
- Un agente in scope **manca** dalla policy → zero deposito parziale (Principio IV)
- Il profilo Copilot CLI non copre un agente atteso

#### 4. Guardie riconciliate

Ritocche alle guardie di test affinché distinguano:
- Alias Claude **nudo** (`haiku`/`sonnet`/`opus`, **assente**, cattivo) — dichiarato dal CLAUDE.md come vietato FEAT-011
- `model:` **di policy** atteso (`claude-haiku-4.5`, **presente**, buono) — dalla fonte unica

Parsing: ricerca `model:` come chiave YAML, non substring (perché `claude-haiku-4.5` contiene `haiku`).

#### 5. Finding di verifica chiave

La config `subagents.agents.<name>.model` è **runtime settings di Copilot CLI**, NON un meccanismo di repo. La doc ufficiale GitHub stabilisce che il modello di un custom-agent Copilot CLI si **configura mediante il campo `model:` nel frontmatter `.agent.md`** e il changelog Copilot CLI (giugno 2026) conferma che il subagent-model si può impostare anche via user settings `~/.copilot/settings.json` (machine-global, per-tenant). Lì persiste l'override `/subagents`, che vince a runtime → il default nel frontmatter è **al sicuro dagli upgrade per costruzione**.

**Deduzione:** il meccanismo via frontmatter è il luogo corretto per l'install-time default; il file `settings.json` dell'utente può sempre sovrascrittere a runtime senza conflitto.

#### 6. Scope out dichiarato

Gli agenti vendorati di spec-kit (`speckit.*`: specify/clarify/plan/tasks/analyze/constitution/checklist/taskstoissues) rimangono **fuori ambito** — il loro modello va gestito da una **feature separata FEAT-016** (Could), post-verifica del supporto `model:` sui prompt-file.

## Verifica e test

**Suite:** SpecKit completo (spec checklist 18/18 → plan Constitution 12/12 + missione PASS).
- **Test offline:** kit **151** · sertor **487** (not-cloud) · sertor-flow **140** · root **1134 pass / 3 skip**
- **Test skipped:** 3 test di packaging che richiedono branch pushato (`git+url@<branch>`); nessuna regressione
- **Lint:** ruff clean, zero violations
- **Core invariato:** Principio XI preservato; `sertor-core` nessuna modifica

**Commit d'implementazione:** `3a16439` (PR #135).

## Pagine correlate

- [[assistant-targeting]] — Sezione nuova «Default model-policy per-agente» aggiunta con meccanismo durevole
- [[sertor-install-kit]] — Nuovo modulo `model_policy.py` centralizzato
- [[sertor-installer]] — Integrazione plan-builder per Copilot CLI
- [[sertor-flow]] — Integrazione plan-builder per agenti governance
- [[constitution]] — Principio IV (fail-loud) + Principio X (host-agnostico) preservati
- [[deterministic-vs-judgment]] — Decisione versionata = meccanico, policy stessa = giudizio dell'utente

## Backlink

- [[assistant-targeting]]
- [[sertor-install-kit]]
- [[sertor-installer]]
- [[sertor-flow]]
- [[constitution]]

## Prossimi passi (post-implementazione)

1. **Prova LIVE:** validare su ospite Copilot CLI reale (verifica che il frontmatter `model:` sia rispettato dalla CLI)
2. **FEAT-016:** follow-up per agenti vendorati (`speckit.*`), dopo verifica supporto `model:` su prompt-file
3. **Sincronizzazione dogfood:** aggiornare `.github/agents/` se il ramo fosse mergiato

---

**Data registrazione:** 2026-07-01 (ore post-implementazione)
**Record:** E2-FEAT-015 branch `083-default-model-policy-copilot`, PR #135, Constitution 12/12, CI verde, ruff clean, **pronto per merge**.
