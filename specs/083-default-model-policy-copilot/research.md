# Research — Default model-policy per i subagent Copilot CLI (E2-FEAT-015)

**Branch**: `083-default-model-policy-copilot` · **Fase**: Phase 0 (risoluzione ignoti)

Le decisioni di *scope* sono FISSE nella spec (Meccanismo A, 5 agenti, profilo nel kit, `sertor-core`
invariato, no probe tenant). Qui si risolvono le **6 forche di *come*** (DA-D-1..6) ancorandole al
codice reale, verificato via MCP `sertor-rag` (`find_symbol`/`search_code`/`who_calls`, **nessun
errore tool**) + `Read` dei file.

## Ancoraggio verificato (fatti di partenza)

- **Renderer**: `render_custom_agent(canonical_text, *, include_model: bool = False)` —
  `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py:53-74`. Oggi con
  `include_model=False` OMETTE `model:`; con `include_model=True` fa **eco verbatim** del valore
  canonico (`model: haiku`) — cioè emette l'alias Claude, invalido su Copilot. Non esiste alcuna
  via per emettere un valore *diverso* da quello dell'asset. Riesportato da
  `sertor_installer.surfaces` (shim `packages/sertor/src/sertor_installer/surfaces.py`) e da
  `sertor_install_kit.__init__`.
- **Tre soli call-site** (`who_calls render_custom_agent`), tutti nel ramo `.agent.md`:
  - `concierge` → `install_rag.py:363` `_render_rag_file` (usato anche a upgrade da
    `_apply_rag_upgrade` `install_rag.py:939`).
  - `wiki-curator` → `install_wiki.py:278` `_render_for_target`.
  - `requirements-analyst`/`configuration-manager`/`requirements` → `install_governance.py:199`
    `_render_for_target`. `install_governance.py:48` importa `render_custom_agent` dal kit.
  - + `test_assets_copilot_parity.py:68` `_render_rag` (mirror del render reale, da riallineare).
- **Deposito**: i 5 agenti sono `Artifact(ArtifactKind.FILE, …, CREATE_IF_ABSENT)`; il `target_rel`
  Copilot è sempre `.github/agents/<name>.agent.md` (basename → nome logico dell'agente). A upgrade
  la FILE passa per `update_file_if_changed` con il contenuto ri-renderizzato (idempotente).
- **Errori del kit**: `errors.py` espone `InstallerError`/`ConfigError` (stdlib-only, **nessuna**
  dipendenza da `sertor-core`). Il kit NON importa `sertor_core`.
- **Modello dati kit**: il kit espone già costanti/funzioni pure e piccoli value-object
  (`HookEntrySpec` in `surfaces.py`; `AssistantId`/`AssistantProfile` in `assistant.py`).

---

## DA-D-1 — Forma e collocazione del profilo versionato

**Decisione.** Nuovo modulo **`sertor_install_kit/model_policy.py`** con una **mappa costante Python**
come fonte unica, un **marcatore di versione** costante e una **funzione risolutrice** fail-loud:

```python
MODEL_POLICY_VERSION = "1"                      # marcatore versione (FR-007, NFR-004)
_MODEL_POLICY: dict[str, str] = {               # unica fonte agente→model-ID (FR-005)
    "concierge":             "claude-haiku-4.5",
    "configuration-manager": "claude-haiku-4.5",
    "requirements-analyst":  "claude-sonnet-4.6",
    "requirements":          "claude-sonnet-4.6",
    "wiki-curator":          "claude-sonnet-4.6",
}
IN_SCOPE_AGENTS: frozenset[str] = frozenset(_MODEL_POLICY)   # per test di copertura/coerenza
def resolve_model(agent_name: str) -> str: ...  # KeyError → ModelPolicyError nominante (FR-008)
```

Riesportato da `sertor_install_kit.__init__` (come `render_custom_agent`/`HookEntrySpec`).

**Motivazione (ancorata).** Il kit è la **casa già condivisa** da `sertor` e `sertor-flow`, senza
legame con `sertor-core` (DA-3 spec, FR-006). Una **mappa costante** è la forma minima (Principio III
YAGNI): fonte unica, importata (non copiata → vedi DA-D-5), versionata da una costante, bump = modifica
di **un solo** simbolo (RNF-2/CS-3). È coerente con come il kit espone già dati/logica pura
(`surfaces.py`, `assistant.py`).

**Scartati.** (a) *File dati versionato* (TOML/JSON sotto `assets/**`): aggiungerebbe I/O + parsing +
**un asset da sincronizzare** con la copia dogfood → riapre esattamente il drift R-5 che DA-D-5 chiude
scegliendo il codice. (b) *Funzione risolutrice con lookup esterno/env*: over-engineering, viola il
determinismo (RNF-3, NFR-002) e la trasparenza (i valori devono essere ispezionabili nel sorgente).

---

## DA-D-2 — Punto di innesto della sostituzione nel renderer

**Decisione.** **Estendere `render_custom_agent`** sostituendo il parametro-eco `include_model: bool`
con **`model: str | None = None`** che, quando valorizzato, emette `model: <policy-id>` **al posto**
di qualunque valore canonico; quando `None`, OMETTE `model:` (retrocompatibilità del comportamento
odierno). L'alias canonico non viene **mai** eco-emesso.

I **3 call-site** derivano il nome-agente dal **basename del `target_rel`** (`concierge.agent.md` →
`concierge`), chiamano `resolve_model(name)` e passano `render_custom_agent(text, model=<id>)`.

**Motivazione (ancorata).** `render_custom_agent` è l'**unico** punto dove il frontmatter Copilot è
serializzato (con `_yaml_scalar` che già gestisce il quoting). Iniettare qui è DRY e sfrutta la
serializzazione esistente; il model-ID `claude-haiku-4.5`/`claude-sonnet-4.6` non contiene `": "`,
non è quotato, esce come scalare piano `model: claude-haiku-4.5`. Il parametro `include_model` (echo)
ha **un solo uso** (un test di completezza) → si riformula senza costo. Il basename è la chiave logica
naturale: su Copilot il container è sempre `.github/agents/<name>.agent.md` (`AssistantProfile`
`assistant.py:178-183`).

**Scartato.** *Post-processing sul frontmatter reso* (regex/riscrittura del testo dopo il render):
fragile, duplicherebbe la logica YAML di `_yaml_scalar`, e richiederebbe di ri-parsare ciò che il
renderer ha appena serializzato.

**Isolamento Claude (FR-012).** Il path Claude **non** usa questo renderer (byte-copia `.claude/**`,
`_concierge_artifact` `install_rag.py:352-353`): `model:` param resta `None`/inutilizzato → frontmatter
Claude byte-identici (incluso il `model: sonnet` di `concierge`). Zero effetto collaterale.

---

## DA-D-3 — Riconciliazione delle guardie esistenti

**Sottigliezza critica scoperta.** Le anti-pattern odierne asseriscono `assert "haiku" not in front`
(`test_assets_copilot_guard.py:48`, `test_schema_copilot_frontmatter.py:56`). Ma il model-ID di policy
`claude-haiku-4.5` **contiene** la sottostringa `haiku` → l'assert vecchio darebbe **falso positivo**.
La riconciliazione DEVE passare da «substring `haiku`/`sonnet` assente» a «**valore `model:` non è un
alias Claude *nudo*** (`haiku`/`sonnet`/`opus`)», parsando la riga `model:`.

**Decisione — forma degli assert.** Un helper `_model_value(front) -> str | None` (parsing della riga
`model:`). Riformulazioni:

- **No-arg → omette** (invariato, comportamento del renderer senza policy):
  `render_custom_agent(canonical)` → `_model_value(front) is None`.
- **Con policy → sostituisce**: `render_custom_agent(asset_con_alias, model="claude-haiku-4.5")` →
  `_model_value(front) == "claude-haiku-4.5"` **e** `_model_value(front) not in {"haiku","sonnet","opus"}`.
  (rimpiazza `test_custom_agent_drops_injected_model` / `test_anti_pattern_custom_agent_drops_claude_model`
  e `test_custom_agent_include_model_opt_in_for_completeness`).
- **Guardia real-asset NUOVA** (`test_assets_copilot_guard.py`): costruisce i piani Copilot reali
  (`build_rag_plan` + `build_governance_plan` + `build_install_plan`) in `tmp_path`, legge i **5**
  `.agent.md` resi e per ciascuno asserisce `_model_value == resolve_model(name)` **e** non-nudo-alias.
  È la guardia di *presenza+correttezza* che coglie sia un leak sia una mancata iniezione (CS-1/CS-2).
- **`_render_rag`** (`test_assets_copilot_parity.py:68`): allineato al render reale (iniezione policy sul
  `.agent.md`), così i check no-`.claude/`/no-slash/no-alias del parity restano validi.

**Collocazione.** Le guardie restano nei rispettivi file (`sertor`: i due file citati; il parity
mirror; `sertor-flow`: la parity di governance se presente). Nessuna guardia rimossa — riformulate.

---

## DA-D-4 — Meccanismo del fail-loud su profilo incompleto

**Decisione.** Nuovo errore **`ModelPolicyError(InstallerError)`** in `sertor_install_kit/errors.py`,
messaggio che **nomina** l'agente: es. `"model-policy profile has no entry for in-scope agent
'concierge' (profile v1)"`. Materializzato al **build del piano** (non al render del singolo file):
ogni plan-builder — `build_rag_plan` (concierge), `install_wiki.build_install_plan` (wiki-curator),
`build_governance_plan` (i tre) — quando `assistant is COPILOT_CLI` **risolve** il modello di ciascun
agente in ambito che sta per depositare, **prima** di restituire il piano.

**Motivazione.** `execute_plan` scrive gli `Artifact` uno a uno; se la risoluzione fallisse *durante*
il render (in `apply`), i primi agenti sarebbero già scritti → deposito parziale, violazione FR-009.
Il build precede interamente l'esecuzione: una `ModelPolicyError` lì **fa fallire prima di ogni
scrittura** (CS-5: 0 installazioni silenziosamente incomplete). Il render richiama la stessa
`resolve_model` (fonte unica, deterministica) → coerenza garantita, nessun secondo path.

**Errore nuovo vs riuso.** Nuovo `ModelPolicyError` (non `ConfigError`): la semantica è «profilo
spedito incompleto» (bug del profilo, non input utente), il tipo dedicato rende il messaggio e il test
espliciti (Principio IV/XII). Resta sotto `InstallerError` → `execute_plan`/CLI lo intercettano
fail-fast come gli altri.

---

## DA-D-5 — Sync bundlato↔dogfood del profilo

**Decisione.** Il profilo **NON** entra nel meccanismo di sync/anti-drift degli asset
(`sertor_installer.sync` + `tests/unit/test_assets_sync.py`) perché **non è un asset**: è un modulo
Python del kit **importato** (non copiato) da entrambi i pacchetti. Non esiste una seconda copia →
**non può divergere per costruzione**. Questo scioglie R-5 alla radice.

**Guardia di coerenza (al posto della sync-guard).** Un test pin: `IN_SCOPE_AGENTS` coincide
**esattamente** con l'insieme dei 5 nomi-agente che i piani Copilot depositano (aggiungere un 6°
agente senza voce nel profilo → rosso, gemello del fail-loud) + assert dei 5 model-ID attesi (pin
della policy). Poiché `sertor` e `sertor-flow` importano lo **stesso** modulo, la coerenza
cross-pacchetto (CS-3/FR-004) è vera per costruzione.

---

## DA-D-6 — Fallback per-agente (minore)

**Decisione.** **Nessun fallback strutturale** nel primo taglio. Con DA-2 risolta (installer offline,
no probe tenant), il «fallback» di FR-018/REQ-009 è **documentale + runtime Copilot**: se un model-ID
non è abilitato nel tenant, il segnale arriva a runtime da Copilot; la doc avverte del rischio. Il
profilo resta una mappa piatta `nome→singolo model-ID`. Granularità dell'eventuale fallback futuro:
**globale documentale**, non un campo per-agente (YAGNI III; il valore della mappa potrebbe diventare
una struttura se e quando servirà). Non blocca il primo taglio.

---

## Promozione di scope (tracciamento, non sepolto)

Il rinvio reale **assegnazione di modello agli `speckit.*`** (prompt-file vendorati da spec-kit; la
doc ufficiale non conferma `model:` sui prompt-file → serve spike) va promosso a **nuova voce di
backlog `FEAT-NNN` nell'epica `sertor-cli`** (`requirements/sertor-cli/epic.md`). Dichiarato qui;
l'edit del backlog è del flusso principale. Non resta sepolto in `specs/`.
