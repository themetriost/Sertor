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

> **Revisione 2026-06-19 — meccanismo NATIVO.** D2/D3 sono stati corretti dopo aver letto la
> **documentazione ufficiale Copilot** (docs.github.com/copilot CLI «add-skills»): Copilot ha le **agent
> skills native** (cartelle `.github/skills/`, `.claude/skills/`, `.agents/skills/`; `SKILL.md`+corpo) e
> **auto-scopre tutti i file della cartella della skill** (incl. sotto-cartelle come `ops/`). L'approccio
> precedente (skill→custom-agent + container `.github/sertor/` + placeholder `{SKILL_DIR}`) era una
> **reinvenzione** del meccanismo nativo ed è abbandonato. Vincolo: leggere i doc ufficiali prima di
> progettare integrazioni con tool esterni.

- **D1** Body **neutralizzati** alla sorgente (no `.claude/` letterale, no `/slash` come comando, no nomi
  assistente, no `$ARGUMENTS`). Il **payload** (playbook/ops/craft) resta **byte-identico** Claude↔Copilot
  (stessa fonte unica). NON si traduce il payload per-target.
- **D2** La capacità wiki su Copilot è **una sola skill NATIVA** `.github/skills/wiki-author/**`
  (`SKILL.md` + `wiki-playbook.md` + `ops/*.md` + `*-craft.md`), auto-scoperta dal client. La skill
  **assorbe il ruolo del command `/wiki`**: il suo `SKILL.md` è il **dispatcher delle 8 operazioni**
  (corpo derivato dalla fonte unica `commands/wiki.md`), perché su Copilot una skill nativa è già
  user-invocabile (`/skills`) e model-invocabile → nessuna skill `wiki` separata, nessun custom-agent per
  la skill, nessun container `.github/sertor/`. Claude invariato (`.claude/skills/wiki-author/` + command
  `/wiki` separato). `wiki-curator` resta custom-agent `.github/agents/wiki-curator.agent.md`.
- **D3** Deposito via **riuso `iter_asset_dir` + byte-copy** dell'albero skill in `.github/skills/`;
  niente nuovi `ArtifactKind`; **eliminati** il render skill/command→custom-agent e il placeholder
  `{SKILL_DIR}`; aggiornare `sertor_owned_paths` (ramo Copilot → `.github/skills/wiki-author`).
- **D4** Nuova **guardia di parità offline** con **closure dei riferimenti**.
- **D5** Governance dual-target in tre artefatti (playbook, `assistant-targeting.md`, DoD del rituale).
- **D6** Scope = **full sweep** (wiki + governance + rag).

> **Semplificazione rispetto alla versione `.github/sertor/`:** con i container **strutturalmente
> paralleli** (`.claude/skills/wiki-author/` ↔ `.github/skills/wiki-author/`), il payload è **co-locato**
> con la skill su entrambi gli host. Quindi i **riferimenti relativi** (`wiki-playbook.md`,
> `ops/<op>.md`, `../page-craft.md`) risolvono **identici** su Claude e Copilot: svanisce la tensione
> "path divergenti" che la versione precedente risolveva col riferimento-per-nome / `{SKILL_DIR}`.
> Conseguenza sul byte-identico: il **payload** è byte-identico Claude↔Copilot; il `SKILL.md` di Copilot
> **diverge** (è il dispatcher derivato dal command) — wrapper sottile host-shaped, fonte unica
> comunque preservata (sorgente = `commands/wiki.md`).

## 4. Requisiti funzionali (EARS)

### Deposito della skill nativa (US1)
- **REQ-001 (Must, Ubiquitous):** Il sistema DEVE depositare, per `--assistant copilot-cli`, l'intera
  skill `wiki-author` come **skill nativa** sotto `.github/skills/wiki-author/` (`SKILL.md` +
  `wiki-playbook.md` + `ops/*.md` + `*-craft.md`), preservando la struttura relativa, così che Copilot
  la auto-scopra e inietti i suoi file alla cartella della skill.
- **REQ-002 (Must, Ubiquitous):** Il `SKILL.md` Copilot DEVE essere il **dispatcher delle 8 operazioni**
  (corpo derivato dalla fonte unica `commands/wiki.md`, neutralizzato) con frontmatter nativo
  (`name`/`description`); i file di payload (playbook/ops/craft) DEVONO essere copiati **byte-per-byte**
  dagli asset canonici Claude.
- **REQ-003 (Must, Ubiquitous):** L'albero skill DEVE provenire dalla **stessa fonte unica** degli asset
  Claude (`assets/claude/skills/wiki-author/`) via `iter_asset_dir`, senza enumerazione hardcoded dei file.
- **REQ-004 (Must, Ubiquitous):** `sertor_owned_paths` (ramo Copilot) DEVE dichiarare
  `.github/skills/wiki-author` come directory di proprietà, così uninstall/upgrade la rimuovono in blocco;
  il render skill→custom-agent e il container `.github/sertor/` NON DEVONO più essere prodotti.

### Neutralizzazione dei body (US2, US3)
- **REQ-005 (Must, Ubiquitous):** Gli asset sorgente distribuibili NON DEVONO contenere path `.claude/`
  letterali nei body; i riferimenti al payload DEVONO essere host-agnostici (per nome file).
- **REQ-006 (Must, Ubiquitous):** Gli asset sorgente distribuibili NON DEVONO citare comandi slash
  (`/wiki`, `/requirements`, …) come modo d'invocazione; DEVONO usare linguaggio capability-neutro.
- **REQ-007 (Should, Ubiquitous):** I body NON DOVREBBERO contenere nomi di assistente ("Claude Code")
  in contesto istruzionale LLM-facing.
- **REQ-008 (Must, Ubiquitous):** Dopo neutralizzazione, i **file di payload** (playbook/ops/craft)
  DEVONO restare **byte-identici** tra deposito Claude e deposito Copilot (sono byte-copiati dalla stessa
  fonte). Il `SKILL.md` Copilot (dispatcher) deriva dalla fonte unica `commands/wiki.md` e differisce dal
  `SKILL.md` Claude (autore): la guardia byte-identica esistente resta verde per le superfici che ancora
  rende custom-agent (`wiki-curator`).
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
- **NFR-02:** Nessun nuovo `ArtifactKind`; riuso dell'infrastruttura esistente (`iter_asset_dir` +
  byte-copy come nel ramo Claude). Si **rimuovono** il render skill/command→custom-agent e `{SKILL_DIR}`.
- **NFR-03:** `sertor-flow` resta **senza dipendenza** da `sertor-core`/`sertor`.
- **NFR-04:** install≠run, non distruttivo, idempotente; uninstall rimuove `.github/skills/wiki-author/`
  in blocco.
- **NFR-05:** La guardia di parità è **offline** (nessuna rete/credenziali), eseguibile in CI senza cloud.
- **NFR-06:** La guardia byte-identica esistente (`test_assets_copilot_guard.py`) resta verde.
- **NFR-07:** Host Copilot **già installati** ricevono il fix via `sertor upgrade` (FEAT-008); nessun
  meccanismo di migrazione speciale (Q-5).

## 6. Criteri di successo

- **CS-1:** Dopo `install wiki --assistant copilot-cli`, `.github/skills/wiki-author/` contiene `SKILL.md`
  (dispatcher) + `wiki-playbook.md` + `ops/*` + craft **esistono** sull'host (oggi assenti).
- **CS-2:** **0** occorrenze di `.claude/` nei file resi per Copilot (tutti gli installer).
- **CS-3:** **0** comandi slash come invocazione nei file resi per Copilot.
- **CS-4:** **0** riferimenti dangling (closure verde) su piano Copilot **e** Claude.
- **CS-5:** Suite Claude di non-regressione + guard byte-identico **verdi**.
- **CS-6:** I link relativi interni della skill (SKILL.md→playbook, playbook→ops/craft) risolvono
  nella cartella skill Copilot (co-locazione preservata).
- **CS-7:** Governance dual-target presente nei tre artefatti (playbook, assistant-targeting, DoD).
- **CS-8 (empirico, Spike):** `/skills` su Copilot CLI 1.0.63 mostra la skill `wiki-author`; invocandola,
  la prima azione (Read del playbook co-locato) **riesce**; la cartella `.github/skills/wiki-author/`
  **non** è interpretata come agente-fantasma.

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
- **A4:** `.github/skills/wiki-author/` è una skill nativa auto-scoperta da Copilot CLI (documentato);
  la verifica empirica (CS-8) la conferma sul campo.

## 9. Rischi

- **R1 (guardia):** falsi positivi/negativi nel distinguere `/wiki` comando da `wiki/` path e nell'estrarre
  i riferimenti dai body. *Mitigazione:* regex mirate + test-del-test; un falso negativo riaprirebbe il bug.
- **R2 (audit incompleto):** payload nascosti in rag/governance non coperti. *Mitigazione:* il full sweep
  + closure sui tre piani li espone.
- **R3 (precisione body):** body neutri meno espliciti su Claude. *Mitigazione:* riferimenti relativi
  co-locati funzionano su entrambi; verifica CS-8.
- **R4 (skill nativa Copilot):** la skill nativa `.github/skills/wiki-author/` potrebbe non essere
  auto-scoperta come atteso. *Mitigazione:* è il **meccanismo documentato** (docs.github.com); **validare
  empiricamente su Spike** (CS-8 — `/skills` la elenca, la prima azione legge il playbook co-locato).

## 10. Prioritizzazione (MoSCoW)

- **Must:** REQ-001..006, 008..011, 013, 019 (payload + neutralizzazione core + closure + guardia base).
- **Should:** REQ-007, 012, 014, 015..018 (Claude-Code naming, "Claude Code" check, closure Claude,
  governance dual-target, ri-sync dogfood).
- **Could:** estensione della guardia ad altri pattern host-specifici futuri.
- **Won't (qui):** promozione `derive-entity-types`; rename `copilot`; migrazione automatica host esistenti.

## 11. Domande aperte — risolte

- **Q-1** Deposito skill Copilot → **skill nativa `.github/skills/wiki-author/**`** (D2, rivisto
  2026-06-19 sui doc ufficiali); skill unica che assorbe il command `/wiki`.
- **Q-2** Neutralizzazione path → con i container **paralleli** i riferimenti restano **relativi**
  co-locati (no path d'assistente letterale), risolti identici su entrambi gli host.
- **Q-3** Pattern slash nella guardia → match istruzionale (es. inizio token `` `/wiki` `` / `/wiki ` ),
  con test-del-test su falsi positivi (URL, path POSIX). Dettaglio d'implementazione.
- **Q-4** Verifica Copilot reale → **Spike** (CS-8), non `xfail`.
- **Q-5** Host già installati → **`sertor upgrade`** (NFR-07), nessuna migrazione speciale.
