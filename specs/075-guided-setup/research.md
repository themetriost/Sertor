# Research — guided-setup (E12-FEAT-002)

**Branch**: `075-guided-setup` · **Fase**: Phase 0 (design) · **Lingua**: italiano

Questa feature è **non-core**: una **skill agentica** (asset di istruzioni markdown) + uno **stub
dell'agente *concierge*** + il **wiring di distribuzione dual-target** nell'installer + l'estensione
della **guardia di parità**. Nessun codice runtime del core, nessun motore/porta/comando nuovo. La
ricerca è interamente di **ancoraggio al pattern esistente** (Principio X — distribuzione collaudata
`wiki-author`/`eval-suite-author`/`eval-feedback`): si **riusa**, non si reinventa.

> **Nota MCP (dogfooding).** Ancoraggio condotto con il server `sertor-rag` (`find_symbol`
> `AssistantProfile`, `search_code` sul plan-builder/guardia, `search_docs` su `assistant-targeting`).
> **Nessun errore tool** (i tool hanno risposto, citazioni `path#chunk` valide). Letture intere via
> `Read` su: `install_rag.py`, `install_wiki.py`, `assistant.py`, `surfaces.py`,
> `test_assets_copilot_parity.py`, asset `assets/rag/skills/eval-suite-author/SKILL.md`.

---

## D-0 — Pattern di distribuzione accertato (dato di partenza, NON da progettare)

### D-0.1 Dove vivono gli asset sorgente delle skill RAG

Le skill di capacità RAG vivono come **asset bundled del pacchetto `sertor`**, non in `.claude/` di
root (quelli sono il dogfood di Sertor). Sorgente accertata:

```
packages/sertor/src/sertor_installer/assets/rag/skills/<name>/SKILL.md
```

(`eval-suite-author`, `eval-feedback`). Costanti in `install_rag.py:94-96`:
`_EVAL_SKILL_NAMES = ("eval-suite-author", "eval-feedback")`,
`_CLAUDE_SKILLS_BASE = ".claude/skills"`, `_COPILOT_SKILLS_BASE = ".github/skills"`.

### D-0.2 Come sono dichiarate nel piano d'installazione

`_eval_skill_artifacts(is_copilot)` (`install_rag.py:160-171`) produce un `Artifact` per skill:

```python
Artifact(ArtifactKind.FILE, f"rag/skills/{name}/SKILL.md", f"{base}/{name}/SKILL.md",
         WriteStrategy.CREATE_IF_ABSENT)
```

Iniettati nel piano da `build_rag_plan` con `plan.extend(_eval_skill_artifacts(is_copilot))`
(`install_rag.py:263`). Lifecycle: in `sertor_owned_paths` le skill sono `owned_dirs`
(`install_rag.py:475-479`: `eval_skill_dirs = tuple(f"{skills_base}/{name}" …)`), rimosse/aggiornate
in blocco da uninstall/upgrade.

### D-0.3 Render dual-target = **byte-copy identica** (nessuna traduzione)

Le eval skill hanno frontmatter **già nativo agent-skill** (`name`/`description`/`user-invocable`/
`disable-model-invocation`) — valido su **entrambi** i target. Quindi NON passano per
`render_native_skill`/`render_custom_agent`: sono `ArtifactKind.FILE` byte-copiate. La guardia di
parità le rende con `_render_rag = read_asset_text(art.source)` — **byte identici** Claude↔Copilot
(`test_assets_copilot_parity.py:67-70`).

**Contrasto con wiki:** il wiki ha un `/wiki` command Claude che su Copilot va TRADOTTO a native skill
(`render_native_skill`) e un agente `wiki-curator` tradotto a `*.agent.md` (`render_custom_agent`,
no `model:`). Le eval skill **non** hanno questo problema perché sono già skill native host-agnostiche.
**Decisione di design (vedi D-1):** `guided-setup` e lo stub concierge seguono il **modello eval**
(skill native byte-identiche), non il modello wiki (traduzione di contenitore).

### D-0.4 Il seam `AssistantProfile`/`Surface` (FEAT-007, kit)

`packages/sertor-install-kit/src/sertor_install_kit/assistant.py`:
- `AssistantId ∈ {CLAUDE="claude", COPILOT_CLI="copilot-cli"}` (`assistant.py:21-25`).
- `Surface ∈ {INSTRUCTION_BLOCK, MCP_SERVER, COMMAND, AGENT, HOOK}` (`assistant.py:39-49`).
- `AssistantProfile.for_assistant(id)` mappa ogni Surface al contenitore nativo.

**Punto sottile per il design:** le skill RAG (eval, e ora guided-setup) **non** passano dal
`Surface`/`render_path`: usano direttamente `_CLAUDE_SKILLS_BASE`/`_COPILOT_SKILLS_BASE` come prefisso.
Il `Surface.COMMAND`/`AGENT` + `render_path` è il meccanismo del **wiki** (che ha contenitori
divergenti per command/agent). Le skill native condividono lo stesso layout `skills/<name>/SKILL.md`
su entrambi → il prefisso esplicito è sufficiente e più semplice (YAGNI III). **Riusare il pattern
eval, non introdurre `Surface` per guided-setup.**

### D-0.5 La guardia di parità offline

`packages/sertor/tests/test_assets_copilot_parity.py` rende i piani (wiki + governance + rag) per
Copilot e asserisce 4 invarianti su ogni body LLM-facing reso:
- **(a)** nessun path-string `.claude/` (`test_copilot_bodies_have_no_claude_path`);
- **(b)** nessuna slash-command invocata `/wiki`,`/requirements` (`_SLASH_COMMAND`);
- **(c)** nessun nome assistente "Claude Code" + nomi prodotto/modello Claude
  (`CLAUDE.md`/`Claude`/`Opus`/`Haiku`/`$ARGUMENTS`, `_CLAUDE_NAMES`);
- **(d)** **closure dei riferimenti**: ogni file citato per nome da un body è un target del piano.

Il rag plan è **già** incluso in `_all_copilot_bodies` (`test_assets_copilot_parity.py:133` via
`_rag_plan`/`_render_rag`) → gli invarianti (a)(b)(c) si applicheranno **automaticamente** ai nuovi
asset guided-setup non appena entrano nel piano. La **closure (d)** oggi gira solo su wiki+governance
(`test_copilot_reference_closure`/`test_claude_reference_closure`); per le eval skill è triviale
(single-file, nessun riferimento incrociato). Guardia complementare: `test_assets_copilot_guard.py`
(`test_no_hand_maintained_copilot_prompt_bodies`) vieta un secondo corpo Copilot a mano.

### D-0.6 Agenti distribuiti dual-target — il pattern `sertor-flow` (riferimento citato)

`sertor-flow` (`install_governance.py`) è il **riferimento** per distribuire **agenti veri** su
entrambi i target — distribuisce agenti (`requirements-analyst`, `configuration-manager`) **E** una
skill (`requirements`), esattamente la combinazione richiesta qui. Meccanismo accertato (da replicare):

- **Sorgente unica** = `assets/claude/agents/<name>.md` (frontmatter `name`/`description`/`tools`/
  `model: <tier>`, body sotto). Esempio reale `.claude/agents/configuration-manager.md`: `model: haiku`.
- **Tabella di routing** `_SERTOR_AUTHORED` (`install_governance.py:103-111`) = tupla
  `(canonical_source, Surface, claude_name, copilot_name)`. Per gli agenti:
  `(_AGENT_…, Surface.AGENT, "agents/<name>.md", "<name>")`; per la skill:
  `(_SKILL_…, Surface.COMMAND, "skills/<name>/SKILL.md", "<name>")`.
- **Plan-builder** (`install_governance.py:147-157`): `name = claude_name if CLAUDE else copilot_name`;
  `target_rel = aprofile.render_path(Surface.AGENT, name)`. Risolve (`assistant.py:115-130`,`178-181`):
  - Claude → `.claude/agents/<name>.md` (prefisso `.claude/`, byte-copy → **`model:` preservato**);
  - Copilot → `.github/agents/<name>.agent.md` (`_agent_dir`+`_agent_suffix`).
- **Render** (`install_governance.py:199-211`): `.agent.md` → `render_custom_agent(canonical)`
  (frontmatter tradotto a `name`/`description`/`tools`, **`model:` OMESSO** di default perché invalido
  su Copilot — FEAT-011/049, `surfaces.py:53-74`); altrimenti byte-copy (Claude tiene il `model:`).
- **Lifecycle** (`install_governance.py:355-370`): gli agenti sono `owned_files` (derivati dal piano);
  uninstall li rimuove, upgrade li `update_file_if_changed`.

**Il kit espone già tutto** (`render_custom_agent`, `Surface.AGENT`, `render_path`, `AssistantProfile`),
riusabile dal rag plan **SENZA nuovo seam nel kit**: `install_rag.py` importa già `AssistantProfile`/
`Surface` (`install_rag.py:19`) e `sertor_installer.surfaces` re-esporta `render_custom_agent`.

**Contenitore = agent-discovery nativo, NON auto-attivazione indebita.** Gli agenti di Copilot vivono
in `.github/agents/` (il contenitore agent-discovery nativo, dove DEVONO stare per essere invocabili —
come `requirements-analyst`/`configuration-manager`). L'attivazione è governata dal `description`
dell'agente (mirato al setup): non si auto-attiva fuori contesto. La cautela FEAT-001/056 «no
agente-fantasma» (R4 di 056) riguardava il **payload** della skill wiki finito per errore in
`.github/agents/` — caso diverso (un albero di supporto, non un agente). Qui il concierge è un agente
legittimo nel contenitore agente.

**Nota: il rag plan oggi NON deposita agenti** (`test_no_wiki_artifacts_created`:71 asserisce
`not .claude/agents`). Questo test va **rivisto** (D-5): il rag plan ORA deposita l'agente concierge in
`agents/`, quindi l'asserzione «nessun agente» diventa «nessun agente **wiki**» (l'agente concierge è
atteso, come le eval/usability skill sono attese).

---

## D-1 (DA-D-r1, parte A) — Concierge = AGENTE vero + skill `guided-setup` (decisione utente)

**Decisione (rivista — utente).** Distribuire **ENTRAMBI**:
1. la **skill `guided-setup`** — porta il *«come»*: le istruzioni del flusso install→configure→verify
   (D-2);
2. un **agente vero `concierge`** — la *persona/orchestratore*, un **dispatcher sottile a un ramo** che
   instrada le richieste di setup verso la skill `guided-setup`, con un **model pin** nel frontmatter
   sul lato Claude (es. `model: sonnet`).

**NON skill-only.** Lo stub-skill `concierge-setup` della versione precedente è **rimosso**: il
dispatcher è ora un **agente**, distribuito come `requirements-analyst`/`configuration-manager` di
`sertor-flow` (`agents/`, non `skills/`).

**Forma dell'agente `concierge`** (sorgente `assets/rag/agents/concierge.md`):
- frontmatter Claude: `name: concierge`, `description: …` (mirato al setup — è il selettore di
  attivazione, US9), `tools: …` (gli strumenti che servono per instradare/eseguire la skill),
  **`model: sonnet`** (pin esplicito — la decisione di modello richiesta dall'utente: orchestratore su
  `sonnet`, non `opus`);
- body host-agnostico (EN): «sei il concierge del setup di Sertor; per le richieste di
  installazione/configurazione, instrada verso la skill `guided-setup` e segui il suo flusso»; **un
  solo ramo**, nessun riferimento a config-recommender/search-diagnose (FEAT-004/007);
- Copilot: reso da `render_custom_agent` → `name`/`description`/`tools` tradotti, **`model:` omesso**
  (invalido su Copilot, lezione FEAT-011/049).

**Razionale.** È il pattern `sertor-flow` (riferimento citato): skill = «come» (istruzioni), agente =
«persona» (orchestratore con modello fissato). Riuso integrale del meccanismo del kit
(`Surface.AGENT`/`render_custom_agent`/`render_path`), nessun nuovo seam. Il model pin sul versante
Claude è preservato by construction (byte-copy del frontmatter), omesso su Copilot dal renderer
esistente.

**Nome.** Agente `concierge` (non `concierge-setup`): è l'agente concierge vero, anticipato come stub a
un ramo. Skill `guided-setup` (invariata). Tracciato come anticipo **FEAT-009** (§Tracciamento scope).

---

## D-2 (DA-D-r1, parte B) — Struttura del body della skill `guided-setup`

**Decisione.** Single-file `SKILL.md` (come le eval skill — nessun payload multi-file → closure
triviale), frontmatter nativo agent-skill, body host-agnostico byte-identico in **inglese** (parità
con le eval skill/wiki — i body asset sono in EN; gli artefatti SpecKit/report in IT). Sezioni del body
(prescritte, non sovra-specificate — RNF-6):

1. **User Input / When to use** — l'intento «metti su Sertor / configura il RAG» innesca la skill.
2. **Hard boundary (deterministic vs judgment).** Riprende la formula delle eval skill: *no execution
   of core logic, no library import; ogni accesso a Sertor passa per un vehicle* (`sertor install`,
   `sertor configure --set`, `sertor-rag doctor`/`index`); la skill **orchestra**, non reimplementa
   (FR-001/013, RNF-1). **MAI** importare `sertor_core`/`build_*`.
3. **Consenso (gate di mutazione).** I check di **sola lettura** (`doctor`, rilevazione `.sertor/.env`)
   sono liberi; ogni passo che **muta l'ospite o scarica** (`install`, `configure --set`, primo
   `index`/download GloVe) è **proposto** e parte **solo dopo conferma esplicita** (FR-008, DA-G3). Il
   body istruisce a chiedere prima di ogni mutazione e a non procedere senza un «sì».
4. **Step 1 — Rileva lo stato (sola lettura).** Lancia `sertor-rag doctor --json` e legge le 4 aree
   (`config`/`provider`/`index`/`mcp`) dal contratto `doctor.report/1` (074). Determina cosa manca →
   **idempotenza** (FR-009): se tutto è verde, dichiara «già configurato e verificato» e si ferma; se
   parziale, conduce **solo** i passi mancanti.
5. **Step 2 — Scegli il provider (euristica minima + conferma).** Vedi D-3.
6. **Step 3 — Install (su conferma).** Se manca la capacità RAG (area `mcp`/`config` segnala assenza),
   propone `sertor install rag` (eventualmente `--assistant <host>`). Su conferma, lo esegue.
7. **Step 4 — Configure (su conferma, segreti sicuri).** Riempie `.sertor/.env` **solo** via
   `sertor configure --set KEY=VALUE` / prompt sicuro; per i **segreti** usa il percorso `getpass` del
   wizard e **non stampa mai** il valore (FR-006, RNF-3). Se un segreto è già in `.env`, non lo
   ri-chiede né lo espone (US3.3).
8. **Step 5 — Index (su conferma, con annuncio GloVe).** Se il provider è `glove` e il modello non è
   in cache, **annuncia** il download una-tantum (~822 MB) **prima** di lanciare `sertor-rag index .`
   (FR-007; degrado onesto: solo annuncio finché FEAT-003 non porta il progress). Con cache presente,
   nessun annuncio.
9. **Step 6 — Verify (fail-loud).** Rilancia `sertor-rag doctor`; se `doctor: PASS` (exit 0) dichiara
   «verificato» con l'esito a supporto; se non verde, espone **area + rimedio** (presi dal report,
   es. la riga `provider FAIL provider config incomplete (AZURE_OPENAI_API_KEY)`) e **non** dichiara
   successo (FR-002/003, RNF-4, Principio XII).
10. **What NOT to do.** Non stampare segreti; non riempire `.env` a mano (sempre via `configure`); non
    eseguire mutazioni senza conferma; non importare il core; non dichiarare «fatto» senza `doctor`.

**Riferimento-per-nome agli asset (lezione FEAT-001/056).** Il body **non** cita `.claude/` path,
slash-command, né nomi-modello/prodotto Claude. Cita i vehicle per **nome di comando**
(`sertor install`, `sertor configure --set`, `sertor-rag doctor`, `sertor-rag index`) — host-agnostici.

**Agente `concierge` (sorgente `assets/rag/agents/concierge.md`).** Vedi D-1: dispatcher sottile a un
ramo, frontmatter Claude con `name`/`description`/`tools`/`model: sonnet`; body host-agnostico che cita
**per nome** la skill `guided-setup` (closure: la skill è depositata dal piano). Il body dell'agente
rispetta gli stessi vincoli anti-leak (no `.claude/`/slash/nomi Claude); il **`model:`** è un campo del
frontmatter (non del body), preservato su Claude e omesso su Copilot dal renderer.

---

## D-3 (DA-D-r1, parte C) — Segnali dell'euristica provider e dove la skill li legge

**Decisione (euristica minima, DA-G2).** Tre segnali, letti **via vehicle/file** (mai importando il
core):

| Segnale | Come la skill lo rileva (vehicle/file, no core) | Effetto sulla raccomandazione |
|---------|--------------------------------------------------|-------------------------------|
| **Credenziali cloud presenti?** | `sertor-rag doctor --json` → area `config`/`provider` (chiavi `AZURE_OPENAI_*` mancanti = no creds); in alternativa ispezione read-only di `.sertor/.env` e dell'ambiente per `AZURE_OPENAI_ENDPOINT`/`_API_KEY` | assenti → **raccomanda locale** (`glove`/`hash`); presenti → cloud **proponibile** |
| **Host airgapped / offline?** | segnale conversazionale (l'utente dichiara airgapped) oppure `doctor --online` che riporta provider `unreachable`; la skill NON sonda la rete da sé | airgapped → **forza locale** (`glove`/`hash`); il cloud non è un'opzione |
| **Serve semantica NL sui documenti?** | segnale conversazionale (la skill **chiede**: «il corpus è ricco di documentazione/NL?») | NL marcata + creds cloud → cloud o `glove` (semantica); NL non necessaria/airgapped → `hash` (pavimento deterministico) |

**Regole di raccomandazione (proposta, mai imposizione — FR-004/005):**
- creds cloud **assenti** O airgapped → **locale**: `glove` se serve semantica NL (default locale del
  core, FEAT-011), `hash` se basta il pavimento deterministico/airgapped stretto;
- creds cloud **presenti** + esigenza NL → propone **cloud** (Azure) **con motivazione** (qualità
  semantica), oppure `glove` locale se l'utente preferisce on-machine;
- in **ogni** caso la skill **propone con motivazione** e l'utente **conferma**; nessuna selezione
  automatica.

**Dove si applica.** Lo `SERTOR_EMBED_PROVIDER` scelto entra in `.sertor/.env` via
`sertor configure --set SERTOR_EMBED_PROVIDER=<glove|hash|azure|ollama>` (Step 4). I segnali sono
**solo input alla conversazione** — il core non viene mai interrogato programmaticamente (RNF-1).

**Confine.** La profilazione **ricca** del repo (linguaggi/dimensione/struttura per la scelta provider)
è **FEAT-004** (config-recommender), fuori ambito (spec §Fuori ambito). Qui solo questi 3 segnali +
conferma.

---

## D-4 (DA-D-r2, parte A) — Punti di wiring nel plan-builder dell'installer `sertor`

Due meccanismi, entrambi riusati dall'esistente: la **skill** segue il pattern eval (byte-copy in
`skills/`); l'**agente** segue il pattern `sertor-flow` (`Surface.AGENT`/`render_custom_agent` in
`agents/`). Modifiche in `packages/sertor/src/sertor_installer/install_rag.py`:

**Skill `guided-setup`:**
1. **Costante asset.** Nuova `_USABILITY_SKILL_NAMES = ("guided-setup",)` accanto a
   `_EVAL_SKILL_NAMES`, sorgente `assets/rag/skills/<name>/SKILL.md`. (Solo `guided-setup`: lo
   stub-skill `concierge-setup` è **rimosso** — il dispatcher è l'agente.)
2. **Artifact factory.** Generalizzare `_eval_skill_artifacts` a `_skill_artifacts(names, is_copilot)`
   (DRY, III); chiamarla per `_EVAL_SKILL_NAMES` e `_USABILITY_SKILL_NAMES`.
3. **Iniezione nel piano.** In `build_rag_plan`, accanto a `plan.extend(_skill_artifacts(_EVAL…))`
   aggiungere `plan.extend(_skill_artifacts(_USABILITY_SKILL_NAMES, is_copilot))`.

**Agente `concierge` (pattern `sertor-flow`, riuso del kit):**
4. **Costante asset + routing.** Nuova `_CONCIERGE_AGENT_SRC = "rag/agents/concierge.md"` e una tabella
   gemella di `_SERTOR_AUTHORED`:
   `_CONCIERGE = (_CONCIERGE_AGENT_SRC, Surface.AGENT, "agents/concierge.md", "concierge")`.
5. **Artifact factory agente.** Nuova `_concierge_artifact(assistant)` che replica
   `install_governance.py:147-157`:
   ```python
   aprofile = AssistantProfile.for_assistant(assistant)
   name = "agents/concierge.md" if assistant is AssistantId.CLAUDE else "concierge"
   target_rel = aprofile.render_path(Surface.AGENT, name)
   return Artifact(ArtifactKind.FILE, _CONCIERGE_AGENT_SRC, target_rel,
                   WriteStrategy.CREATE_IF_ABSENT)
   ```
   → Claude `.claude/agents/concierge.md` (byte-copy, `model: sonnet` preservato); Copilot
   `.github/agents/concierge.agent.md`.
6. **Render per-target.** Il rag plan oggi usa `_apply_rag_hook_file` (byte-copy puro) per i `FILE`.
   Per l'agente Copilot serve `render_custom_agent`. **Decisione:** introdurre un render-aware analogo
   a `install_wiki._render_for_target`/`install_governance._render_for_target` — un helper
   `_render_rag_file(art)` che: se `art.target_rel.endswith(".agent.md")` → `render_custom_agent(text)`;
   altrimenti byte-copy. Usato dall'apply del `FILE` (sia install che upgrade). **Confine:** è un helper
   **locale a `install_rag.py`** (come quello di wiki/governance), **NON** un nuovo seam nel kit — il kit
   espone già `render_custom_agent`. La skill (`.md`, non `.agent.md`) resta byte-copia.
7. **Iniezione nel piano.** In `build_rag_plan`, `plan.append(_concierge_artifact(assistant))`.

**Lifecycle (`sertor_owned_paths`, `install_rag.py:475-487`):**
8. **owned_dirs (skill):** `usability_skill_dirs = tuple(f"{skills_base}/{name}" …)` aggiunte a
   `owned_dirs`.
9. **owned_files (agente):** il file agente `aprofile.render_path(Surface.AGENT, …)` aggiunto a
   `owned_files` (come `sertor-flow` tratta gli agenti — owned_files, non owned_dir, perché è un singolo
   file in un contenitore condiviso `agents/`). Così uninstall lo rimuove e upgrade lo
   `update_file_if_changed`. Il **test di copertura** `plan ⊆ owned` continua a passare.
10. **upgrade.** `_apply_rag_upgrade` per il `FILE` usa già `update_file_if_changed` con
    `read_asset_text(art.source)` — va reso **render-aware** (usare `_render_rag_file(art)` invece di
    `read_asset_text`) così l'agente Copilot è aggiornato con il frontmatter tradotto.

**Nessuna nuova `ArtifactKind`/`Surface`/`WriteStrategy`** (riuso `FILE`/`CREATE_IF_ABSENT`,
`Surface.AGENT`); **nessun nuovo seam nel kit** (render già esportato). Helper di render **locale** a
`install_rag.py` (com'è già per wiki/governance). **Additività piena** (RNF-7): install RAG invariato
salvo +1 skill +1 agente nel piano.

---

## D-5 (DA-D-r2, parte B) — Guardia di parità per skill E agente + closure dei riferimenti

**Decisione.**
1. **(a)(b)(c) automatici per skill e agente.** I nuovi asset (skill `guided-setup` + agente
   `concierge`) entrano in `_all_copilot_bodies` via `_rag_plan`. **MA** il renderer del test
   `_render_rag` oggi fa byte-copy puro (`read_asset_text(art.source)`) — non traduce gli `.agent.md`.
   Va **allineato** al render reale: `_render_rag` deve usare lo stesso `_render_rag_file` (o
   equivalente) del plan, così il body Copilot dell'agente testato è quello **realmente** depositato
   (frontmatter tradotto, `model:` omesso). Allineato il renderer, gli invarianti
   no-`.claude/`/no-slash/no-nomi-Claude coprono **anche l'agente** (il frontmatter tradotto NON deve
   contenere `model: sonnet`/nomi Claude; il body non deve avere leak). *Questo è il punto critico: la
   guardia DEVE rendere come il plan, altrimenti il `model:` Claude potrebbe sfuggire al check.*
2. **(d) closure: l'agente cita la skill per nome.** L'agente `concierge` cita **per nome**
   `guided-setup`. È un riferimento per-nome-skill, non un riferimento-a-file `.md` (la closure
   file-based su `_BACKTICK_REF` non lo cattura). **Closure mirata**: estrai i nomi-asset di usabilità
   citati nei body (regex sui nomi noti `guided-setup`/`concierge`) e verifica che ogni nome citato
   corrisponda a un asset **depositato dal rag plan** su quel target (skill `guided-setup` →
   `{base}/skills/guided-setup/SKILL.md`; agente `concierge` → contenitore agente). Copre «il dispatcher
   instrada verso una skill non installata» (forma del bug FEAT-001 per asset agentici).
3. **Anti-corpo-a-mano.** `test_no_hand_maintained_copilot_prompt_bodies` continua a valere: nessun
   secondo corpo Copilot a mano per skill/agente (resi da fonte unica).

**Conseguenza sul test esistente `test_no_wiki_artifacts_created` (`:71`).** Asserisce oggi
`not (.claude/agents)` per il rag plan. Ora il rag plan **deposita** `.claude/agents/concierge.md` →
l'asserzione va **ristretta** a «nessun agente **wiki**» (`wiki-curator`), non «nessun agente». L'agente
concierge è atteso, come le eval/usability skill.

---

## D-6 — Test di deposito (offline)

Estendere `packages/sertor/tests/test_install_rag.py`:

**Skill `guided-setup`:**
- `test_guided_setup_skill_deposited_claude`: dopo `install rag --assistant claude`,
  `.claude/skills/guided-setup/SKILL.md` esiste.
- `test_guided_setup_skill_deposited_copilot`: dopo `--assistant copilot-cli`,
  `.github/skills/guided-setup/SKILL.md` esiste.
- `test_guided_setup_body_byte_identical`: body Claude == body Copilot (skill byte-copia, parità).

**Agente `concierge`:**
- `test_concierge_agent_deposited_claude`: `.claude/agents/concierge.md` esiste **e** il suo
  frontmatter contiene `model: sonnet` (il pin è preservato su Claude).
- `test_concierge_agent_deposited_copilot`: `.github/agents/concierge.agent.md` esiste **e** il suo
  frontmatter **non** contiene `model:` (omesso da `render_custom_agent`) né leak Claude — è il punto
  della lezione FEAT-011/049.
- `test_concierge_routes_to_guided_setup`: il body dell'agente cita `guided-setup` e **non** cita
  `config-recommender`/`search-diagnose`/`FEAT-004`/`FEAT-007` (stub a un ramo, US9.2).

**Lifecycle:**
- `test_no_wiki_artifacts_created` (`:71`) **ristretto**: il rag plan NON deposita l'agente **wiki**
  (`wiki-curator`), ma SÌ l'agente `concierge` e le usability/eval skill (asserzioni aggiornate).
- `test_idempotence`/`test_uninstall` esistenti coprono i nuovi asset (skill = owned_dir, agente =
  owned_file) — asserzioni aggiuntive su SKIPPED a re-run e rimozione su uninstall.

**Guardia di parità** (`test_assets_copilot_parity.py`): allineare `_render_rag` al render reale del
plan (traduce `.agent.md`), così (a)(b)(c) coprono l'agente; aggiungere la **closure mirata**
(D-5.2). Tutto **offline** (`Fake*Runner`, niente rete/`uv`); prova LIVE = follow-up.

---

## D-7 — Tracciamento dello scope (promozione durevole)

- **Agente concierge = anticipo FEAT-009 (parzialmente avviata).** Aggiornare la riga FEAT-009 nel
  backlog d'epica (`requirements/usabilita/epic.md:180`) a **«parzialmente avviata (stub agente
  `concierge` a un ramo) — gli altri rami (config-recommender/search-diagnose) + i check proattivi
  restano FEAT-009»**. NON duplicare, NON marcarla done. Aggiornare la riga FEAT-002:172 a «in
  progress → spec/plan 075».
- **Sinergia FEAT-003 / FEAT-004** = consumo opzionale: restano voci del backlog (FEAT-003:174 /
  FEAT-004:175), citate dalla skill «quando disponibili». Nessun rinvio nuovo da promuovere.
- **Out-of-scope reali** (profilazione ricca, compiti pieni concierge, progress GloVe) → FEAT-004/009/
  003 già nel backlog → nessuna voce orfana in `specs/`.

---

## Sintesi delle decisioni

| ID | Decisione |
|----|-----------|
| D-1 | Concierge = **AGENTE vero** `concierge` (`agents/`, `model: sonnet` su Claude) + **skill `guided-setup`** (`skills/`). Pattern `sertor-flow` (agenti + skill). Lo stub-skill `concierge-setup` è RIMOSSO. |
| D-2 | `guided-setup` = single-file `SKILL.md` EN, body host-agnostico a 10 sezioni (boundary, consenso, 6 step, what-NOT). Riferimento-per-nome. |
| D-3 | Euristica = 3 segnali (creds cloud via `doctor --json`/`.env` read-only; airgapped; NL conversazionale) → proposta+conferma; provider in `.env` via `configure --set`. |
| D-4 | Wiring = skill via `_skill_artifacts`/byte-copy; agente via `Surface.AGENT`/`render_path`/`render_custom_agent` (helper `_render_rag_file` locale, NO nuovo seam kit); owned_dirs (skill) + owned_files (agente); upgrade render-aware. |
| D-5 | Parità: `_render_rag` allineato al render reale (traduce `.agent.md`) → (a)(b)(c) coprono l'agente (il `model:` Claude NON deve sfuggire); closure mirata «ogni asset citato per nome è depositato»; `test_no_wiki_artifacts_created` ristretto a «no agente wiki». |
| D-6 | Test di deposito offline per skill + agente (incl. `model: sonnet` su Claude / assente su Copilot); routing a un ramo; lifecycle. |
| D-7 | FEAT-009 → «parzialmente avviata (stub agente a un ramo)»; FEAT-002 → in progress; nessun rinvio orfano. |

---

## Nota: serve un seam nel kit?

**No.** Il kit espone già `render_custom_agent`, `Surface.AGENT`, `render_path`, `AssistantProfile`,
tutti riusabili dal rag plan (li usa già `sertor-flow`). L'unica novità in `install_rag.py` è un helper
di render **locale** `_render_rag_file(art)` (traduce `.agent.md`, byte-copia il resto) — esattamente
com'è già locale a `install_wiki.py` (`_render_for_target`) e `install_governance.py`
(`_render_for_target`). Nessuna modifica a `sertor-install-kit`, nessuna modifica a `sertor-core`.
