# Requisiti — Parità funzionale completa su Copilot CLI + governance dual-target

> Epica: **`debito-tecnico`** · decomposizione di **FEAT-001** ("Host-agnosticità degli asset residui").
> Assistente target: **copilot-cli** (VS Code rimosso in FEAT-012). Branch: `056-parita-asset-copilot`.

## 1. Contesto e problema

Verifica empirica su host Copilot reale (Spike, Copilot CLI 1.0.63): la **capacità wiki è non
funzionante** su Copilot, nonostante la "parità funzionale" dichiarata da FEAT-007/009. Due cause:

1. **Payload multi-file perso.** La skill `wiki-author` ha un payload di supporto — `wiki-playbook.md`,
   9 moduli `ops/*.md`, `page-craft.md`/`wiki-craft.md`/`log-craft.md` — che il plan Claude deposita
   tutto (`install_wiki.py:_build_claude_wiki_plan` via `iter_asset_dir("claude")`, riga ~149), mentre il
   plan Copilot (`_build_copilot_wiki_plan`, ~198-251) rende **solo `SKILL.md`** → `.github/agents/wiki-author.agent.md`.
2. **Body con riferimenti Claude.** Il seam (`surfaces.py:render_custom_agent`) traduce il *contenitore*
   ma riusa il *body* **verbatim**; così i path `.claude/skills/wiki-author/wiki-playbook.md`
   (`SKILL.md:10`, `wiki-curator.md:13`, `commands/wiki.md:9`, `requirements-analyst.md:13`) e il comando
   `/wiki` sopravvivono nel reso Copilot — path/comandi inesistenti su quell'host.

La guardia esistente (`test_assets_copilot_guard.py`) verifica il body **byte-identico** canonical↔reso
ma **non** i path interni né la presenza dei file referenziati → il bug è passato.

## 2. User stories

- **US1 (P1) — Wiki funzionante su Copilot CLI.** Come utente con host Copilot, installo la capacità
  wiki e l'agente wiki **esegue con successo** la sua prima azione (leggere il playbook), invece di
  fallire perché il playbook non esiste.
- **US2 (P1) — Zero riferimenti Claude sull'host Copilot.** Come utente Copilot, nessun artefatto reso
  contiene path `.claude/`, comandi slash o nomi di assistente che non esistono sul mio host.
- **US3 (P2) — Parità su tutte le superfici.** Stessa garanzia per governance (`requirements`) e rag,
  non solo wiki (full sweep).
- **US4 (P2) — Regressione impossibile.** Come manutentore, una guardia offline fallisce se un asset
  reso per Copilot reintroduce un riferimento Claude o un riferimento a un file non depositato.
- **US5 (P3) — Dual-target by construction.** Come manutentore, il processo (playbook + DoD) impone che
  ogni nuovo asset host-facing nasca host-agnostico, così la parità non regredisce in futuro.

## 3. Decisioni di design (vincolanti, già approvate)

- **D1** Body **neutralizzati** alla sorgente (no `.claude/` letterale, no `/slash` come comando, no nomi
  assistente) → restano **byte-identici** Claude↔Copilot. NON si traduce il body per-target.
- **D2** Payload multi-file su Copilot in **container dedicato `.github/sertor/wiki-author/`** (dir
  non-agente, fuori da `.github/agents/` per evitare agent-discovery). Claude invariato (`.claude/skills/wiki-author/`).
- **D3** Deposito via **riuso `iter_asset_dir` + byte-copy**; niente nuovi `Surface`/`ArtifactKind`;
  aggiornare `sertor_owned_paths` (ramo Copilot).
- **D4** Nuova **guardia di parità offline** con **closure dei riferimenti**.
- **D5** Governance dual-target in tre artefatti (playbook, `assistant-targeting.md`, DoD del rituale).
- **D6** Scope = **full sweep** (wiki + governance + rag).

> **Affinamento (risolve la tensione D1×D2):** poiché il body è byte-identico ma il payload vive in path
> **diversi** per host (`.claude/skills/wiki-author/` vs `.github/sertor/wiki-author/`), il body **non può
> contenere un path assoluto** valido per entrambi. Regola di neutralizzazione: i body referenziano il
> payload **per nome di file** (`wiki-playbook.md`, `ops/<op>.md`, …) con formulazione host-agnostica
> ("il playbook fornito con questa skill"), lasciando all'agente la localizzazione (nome univoco,
> reperibile). I **link interni del playbook** restano **relativi** (`ops/record.md`, `../page-craft.md`)
> e funzionano perché la struttura della cartella è preservata byte-per-byte su entrambi i container.

## 4. Requisiti funzionali (EARS)

### Deposito del payload (US1)
- **REQ-001 (Must, Ubiquitous):** Il sistema DEVE depositare, per `--assistant copilot-cli`, l'intero
  payload di supporto della skill `wiki-author` (`wiki-playbook.md`, `ops/*.md`, `*-craft.md`) sotto
  `.github/sertor/wiki-author/`, preservando la struttura relativa.
- **REQ-002 (Must, Event):** QUANDO il plan Copilot deposita i file di supporto, il sistema DEVE copiarli
  **byte-per-byte** (sono documenti senza frontmatter, non resi come agenti).
- **REQ-003 (Must, Ubiquitous):** Il payload DEVE provenire dalla **stessa fonte unica** degli asset
  Claude (`assets/claude/skills/wiki-author/`) via `iter_asset_dir`, senza enumerazione hardcoded dei file.
- **REQ-004 (Must, Ubiquitous):** `sertor_owned_paths` (ramo Copilot) DEVE dichiarare
  `.github/sertor/wiki-author` come directory di proprietà, così uninstall/upgrade la rimuovono in blocco.

### Neutralizzazione dei body (US2, US3)
- **REQ-005 (Must, Ubiquitous):** Gli asset sorgente distribuibili NON DEVONO contenere path `.claude/`
  letterali nei body; i riferimenti al payload DEVONO essere host-agnostici (per nome file).
- **REQ-006 (Must, Ubiquitous):** Gli asset sorgente distribuibili NON DEVONO citare comandi slash
  (`/wiki`, `/requirements`, …) come modo d'invocazione; DEVONO usare linguaggio capability-neutro.
- **REQ-007 (Should, Ubiquitous):** I body NON DOVREBBERO contenere nomi di assistente ("Claude Code")
  in contesto istruzionale LLM-facing.
- **REQ-008 (Must, Ubiquitous):** Dopo neutralizzazione, il body sorgente DEVE restare **byte-identico**
  tra reso Claude e reso Copilot (la guardia byte-identica esistente resta verde).
- **REQ-009 (Must, Ubiquitous):** La neutralizzazione DEVE applicarsi a **tutti** gli asset distribuibili:
  wiki (`sertor`), governance `requirements`/agenti (`sertor-flow`), rag.

### Guardia di parità (US4)
- **REQ-010 (Must, Ubiquitous):** Una suite offline DEVE rendere i piani Copilot (wiki+governance+rag) e
  verificare, per ogni file reso, l'**assenza** di `.claude/`.
- **REQ-011 (Must, Ubiquitous):** La suite DEVE verificare l'assenza di comandi slash come invocazione.
- **REQ-012 (Should, Ubiquitous):** La suite DEVE verificare l'assenza di "Claude Code" nei body resi.
- **REQ-013 (Must, Ubiquitous):** La suite DEVE verificare la **closure dei riferimenti**: ogni file
  citato da un body reso DEVE essere presente tra i target del piano (risolvendo i relativi rispetto al
  container del referente). *(È il controllo che avrebbe preso il bug originale.)*
- **REQ-014 (Should, Ubiquitous):** Il controllo di closure DEVE essere eseguito **anche sul piano
  Claude**, per garantire che la neutralizzazione non abbia rotto i riferimenti del ramo dogfood.

### Governance dual-target (US5)
- **REQ-015 (Should, Ubiquitous):** Il **Wiki Playbook** DEVE contenere una sezione "authoring
  host-agnostico" che codifichi le regole REQ-005/006/007 e la regola di riferimento-per-nome.
- **REQ-016 (Should, Ubiquitous):** `wiki/tech/assistant-targeting.md` DEVE documentare la "parità by
  construction" (il *come*) e la guardia di parità come enforcement.
- **REQ-017 (Should, Ubiquitous):** Il blocco rituale distribuibile (`claude-md-block.md`) DEVE includere
  una voce di **Definition of Done**: toccare un asset distribuibile richiede la verifica di parità.
- **REQ-018 (Should, Ubiquitous):** Il dogfood di Sertro (`.claude/**` di questo repo + `CLAUDE.md`) DEVE
  essere ri-sincronizzato con gli asset neutralizzati (coerenza dogfood↔asset, guard test del repo).

### Non-regressione (US4)
- **REQ-019 (Must, Unwanted):** SE viene reintrodotto un riferimento Claude o un riferimento dangling in
  un asset distribuibile, ALLORA almeno un test della guardia di parità DEVE fallire.

## 5. Requisiti non funzionali

- **NFR-01:** Ramo `_build_claude_wiki_plan` **invariato** (non-regressione dogfood Claude).
- **NFR-02:** Nessun nuovo `Surface`/`ArtifactKind`; riuso dell'infrastruttura esistente.
- **NFR-03:** `sertor-flow` resta **senza dipendenza** da `sertor-core`/`sertor`.
- **NFR-04:** install≠run, non distruttivo, idempotente; uninstall rimuove `.github/sertor/wiki-author/`
  in blocco.
- **NFR-05:** La guardia di parità è **offline** (nessuna rete/credenziali), eseguibile in CI senza cloud.
- **NFR-06:** La guardia byte-identica esistente (`test_assets_copilot_guard.py`) resta verde.
- **NFR-07:** Host Copilot **già installati** ricevono il fix via `sertor upgrade` (FEAT-008); nessun
  meccanismo di migrazione speciale (Q-5).

## 6. Criteri di successo

- **CS-1:** Dopo `install wiki --assistant copilot-cli`, `.github/sertor/wiki-author/wiki-playbook.md` +
  `ops/*` + craft **esistono** sull'host (oggi assenti).
- **CS-2:** **0** occorrenze di `.claude/` nei file resi per Copilot (tutti gli installer).
- **CS-3:** **0** comandi slash come invocazione nei file resi per Copilot.
- **CS-4:** **0** riferimenti dangling (closure verde) su piano Copilot **e** Claude.
- **CS-5:** Suite Claude di non-regressione + guard byte-identico **verdi**.
- **CS-6:** I link relativi interni del payload risolvono nel container Copilot.
- **CS-7:** Governance dual-target presente nei tre artefatti (playbook, assistant-targeting, DoD).
- **CS-8 (empirico, Spike):** invocando l'agente wiki su Copilot CLI 1.0.63, la prima azione (Read del
  playbook) **riesce**; e `.github/sertor/` **non** genera agenti-fantasma (validazione rischio R4).

## 7. Ambito

**In ambito:** payload multi-file su Copilot; neutralizzazione body (wiki+governance+rag); guardia di
parità con closure; governance dual-target (3 artefatti); ri-sync dogfood; aggiornamento `sertor_owned_paths`.

**Fuori ambito:** commenti "Claude Code" negli **script** `.ps1` (non body LLM-facing); rename
`copilot-cli`→`copilot` (E10-FEAT-007); **promozione di `derive-entity-types`** a capacità di produzione
(prototipo-coupled → **backlog separato**); eventuali payload RAG residui scoperti dall'audit (→ follow-up
nella stessa FEAT-001 se trovati).

## 8. Assunzioni

- **A1:** I file di supporto della skill **non hanno frontmatter** → byte-copy corretto (verificare in audit).
- **A2:** Un agente LLM su Copilot CLI localizza un file di payload citato per nome univoco (Read/ricerca).
- **A3:** Spike è disponibile come host Copilot reale per la verifica empirica pre-merge.
- **A4:** `.github/sertor/` non è interpretato da Copilot CLI come area di agent-discovery (da confermare, R4).

## 9. Rischi

- **R1 (guardia):** falsi positivi/negativi nel distinguere `/wiki` comando da `wiki/` path e nell'estrarre
  i riferimenti dai body. *Mitigazione:* regex mirate + test-del-test; un falso negativo riaprirebbe il bug.
- **R2 (audit incompleto):** payload nascosti in rag/governance non coperti. *Mitigazione:* il full sweep
  + closure sui tre piani li espone.
- **R3 (precisione body):** body neutri meno espliciti su Claude. *Mitigazione:* riferimento-per-nome è
  reperibile su entrambi; verifica CS-8.
- **R4 (container Copilot):** `.github/sertor/` potrebbe essere scandito per agenti. *Mitigazione:* scelto
  apposta fuori da `.github/agents/`; **validare empiricamente su Spike** (CS-8). Fallback: altro path
  non-agent + aggiornare il riferimento-per-nome.

## 10. Prioritizzazione (MoSCoW)

- **Must:** REQ-001..006, 008..011, 013, 019 (payload + neutralizzazione core + closure + guardia base).
- **Should:** REQ-007, 012, 014, 015..018 (Claude-Code naming, "Claude Code" check, closure Claude,
  governance dual-target, ri-sync dogfood).
- **Could:** estensione della guardia ad altri pattern host-specifici futuri.
- **Won't (qui):** promozione `derive-entity-types`; rename `copilot`; migrazione automatica host esistenti.

## 11. Domande aperte — risolte

- **Q-1** Container Copilot → **`.github/sertor/wiki-author/`** (D2, deciso).
- **Q-2** Neutralizzazione path → **riferimento-per-nome host-agnostico** (no path assoluto; vedi §3
  affinamento), così il body resta byte-identico e valido su entrambi.
- **Q-3** Pattern slash nella guardia → match istruzionale (es. inizio token `` `/wiki` `` / `/wiki ` ),
  con test-del-test su falsi positivi (URL, path POSIX). Dettaglio d'implementazione.
- **Q-4** Verifica Copilot reale → **Spike** (CS-8), non `xfail`.
- **Q-5** Host già installati → **`sertor upgrade`** (NFR-07), nessuna migrazione speciale.
