# Data Model — Default model-policy per i subagent Copilot CLI (E2-FEAT-015)

La feature è **distribuzione/installer pura**: nessuna entità di `sertor_core`, nessuna porta/adapter/
engine. Le entità qui sono value-object e funzioni pure del **kit condiviso** `sertor-install-kit` +
le estensioni ai renderer/errori. Tutto stdlib-only, deterministico, verificabile offline.

## §1 — Profilo di modello versionato (NUOVO, kit)

Modulo: `packages/sertor-install-kit/src/sertor_install_kit/model_policy.py`.

| Simbolo | Tipo | Ruolo |
|---|---|---|
| `MODEL_POLICY_VERSION` | `str` (`"1"`) | Marcatore di versione del profilo (FR-007, NFR-004): distingue un bump di model-ID da una modifica di persona. |
| `_MODEL_POLICY` | `dict[str, str]` | Fonte unica agente→model-ID (privato; 5 voci, vedi tabella). |
| `IN_SCOPE_AGENTS` | `frozenset[str]` | Insieme dei nomi-agente in ambito (= chiavi del profilo). Per test di copertura/coerenza. |
| `resolve_model(agent_name: str) -> str` | funzione pura | Ritorna il model-ID; `KeyError` → `ModelPolicyError` che **nomina** l'agente (FR-008). |

**Contenuto iniziale (default ragionato, versionato — non hardcoded altrove):**

| Agente | model-ID iniziale | Classe |
|---|---|---|
| `concierge` | `claude-haiku-4.5` | dispatcher meccanico → economico/veloce |
| `configuration-manager` | `claude-haiku-4.5` | operazioni git meccaniche → economico/veloce |
| `requirements-analyst` | `claude-sonnet-4.6` | analisi/scrittura → capace |
| `requirements` | `claude-sonnet-4.6` | elicitazione EARS → capace |
| `wiki-curator` | `claude-sonnet-4.6` | sintesi/curation → capace |

**Invarianti.** Determinismo (RNF-3): stesso nome + stessa versione → stesso ID. Fonte unica (CS-3):
0 ID letterali per-agente nel codice installer. Nessuna copia dogfood (importato, non copiato → DA-D-5).

## §2 — Errore di fail-loud (NUOVO, kit)

`packages/sertor-install-kit/src/sertor_install_kit/errors.py`:

```python
class ModelPolicyError(InstallerError):
    """Il profilo di modello non copre un agente in ambito (fail-loud install-time)."""
```

Messaggio nominante, es.: `"model-policy profile (v1) has no entry for in-scope agent 'concierge'"`.
Sotto `InstallerError` → intercettato fail-fast come gli altri errori del kit (Principio IV/XII).

## §3 — Renderer del custom-agent (MODIFICATO, kit)

`render_custom_agent` — firma cambiata:

```python
# prima:  def render_custom_agent(canonical_text: str, *, include_model: bool = False) -> str
# dopo:   def render_custom_agent(canonical_text: str, *, model: str | None = None) -> str
```

| Input `model` | Comportamento |
|---|---|
| `None` (default) | OMETTE `model:` (retrocompat: comportamento odierno con `include_model=False`). |
| `"<policy-id>"` | Emette `model: <policy-id>` come campo, **al posto** di qualunque alias canonico. Mai eco dell'alias Claude. |

Il valore è serializzato da `_yaml_scalar` (invariato): `claude-haiku-4.5`/`claude-sonnet-4.6` escono
come scalari piani. `name`/`description`/`tools` preservati (identità/persona intatti, FR-003).

## §4 — Punti di innesto (MODIFICATI, consumatori)

Ciascun call-site deriva il nome-agente dal **basename del `target_rel`** (`<name>.agent.md` →
`<name>`), risolve via `resolve_model` e passa il model al renderer. Il ramo Claude è invariato.

| File | Funzione | Agente/i | Modifica |
|---|---|---|---|
| `sertor/…/install_rag.py:363` | `_render_rag_file` | `concierge` | `.agent.md` → `render_custom_agent(text, model=resolve_model(name))` |
| `sertor/…/install_rag.py:378` | `build_rag_plan` | `concierge` | se copilot: validazione fail-loud al build |
| `sertor/…/install_wiki.py:278` | `_render_for_target` | `wiki-curator` | idem render |
| `sertor/…/install_wiki.py` | `build_install_plan` | `wiki-curator` | validazione fail-loud al build (copilot) |
| `sertor-flow/…/install_governance.py:199` | `_render_for_target` | `requirements-analyst`/`configuration-manager`/`requirements` | idem render |
| `sertor-flow/…/install_governance.py:127` | `build_governance_plan` | i tre | validazione fail-loud al build (copilot) |

**Upgrade (FR-010/011).** `_apply_rag_upgrade` (`install_rag.py:939`) usa già `_render_rag_file` +
`update_file_if_changed` → il render policy-aware è idempotente per costruzione (contenuto byte-identico
a parità di versione profilo). `wiki-curator`/governance seguono i rispettivi `_render_for_target`.
**Uninstall** invariato (sola rimozione, nessuna semantica di modello — FR-011).

## §5 — Guardie riconciliate (test)

| File | Test | Da → A |
|---|---|---|
| `sertor/tests/test_assets_copilot_guard.py` | `test_custom_agent_omits_model_field` | invariato (no-arg render omette) |
| » | `test_custom_agent_drops_injected_model` | «substring `haiku` assente» → «con policy: `model:` == policy-id, non alias nudo» |
| » | *(nuovo)* real-asset guard | i 5 `.agent.md` resi dai piani → `model:` == `resolve_model(name)`, mai alias nudo |
| `sertor/tests/test_schema_copilot_frontmatter.py` | `test_custom_agent_has_no_model` | invariato (no-arg) |
| » | `test_anti_pattern_custom_agent_drops_claude_model` | precisione: alias **nudo** assente, non substring |
| » | `test_custom_agent_include_model_opt_in_for_completeness` | `include_model=True` → `model="…"` (sostituzione policy) |
| `sertor/tests/test_assets_copilot_parity.py` | `_render_rag` | mirror del render reale (iniezione policy) |
| `sertor-install-kit`/`sertor` | *(nuovo)* coerenza profilo | `IN_SCOPE_AGENTS` == 5 nomi depositati + pin dei 5 ID |

Helper condiviso nei test: `_model_value(front) -> str | None` (parsing riga `model:`), per non
falsare su model-ID che contengono `haiku`/`sonnet` come sottostringa.

## §6 — Fuori entità

- **`speckit.*`**: prompt-file, nessun `model:` assegnato (FR-017); confine documentato + promosso a
  backlog `FEAT-NNN`.
- **`sertor_core`**: invariato (RNF-8, Principio XI).
- **Fallback strutturale per-agente**: assente nel primo taglio (DA-D-6, documentale/globale).
