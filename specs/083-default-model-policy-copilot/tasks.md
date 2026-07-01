# Tasks — Default model-policy per i subagent Copilot CLI (E2-FEAT-015)

**Branch**: `083-default-model-policy-copilot` · **Generato**: 2026-07-01
**Spec**: [`spec.md`](spec.md) · **Piano**: [`plan.md`](plan.md) · **Ricerca**: [`research.md`](research.md)
**Dati**: [`data-model.md`](data-model.md) · **Contratti**: [`contracts/model-policy.md`](contracts/model-policy.md)
**Quickstart**: [`quickstart.md`](quickstart.md)

> **Nota di processo.** `.specify/scripts/powershell/setup-tasks.ps1` e uno skill dedicato
> `speckit-tasks` **NON esistono** nel repo → parametri/struttura per convenzione dai `tasks.md`
> precedenti (forma da `075`/`082`); **nessun hook SpecKit eseguito**. Git **mai** qui: brief di
> commit al fondo per il `configuration-manager`.
>
> I task marcati `[P]` sono parallelizzabili nella stessa fase (file disgiunti, nessuna dipendenza
> reciproca). Il suffisso `→ dipende da` lista i prerequisiti.

## Natura del cambiamento (vincolante, non riaprire)

**ADDITIVA / distribuzione-installer, ZERO runtime di `sertor_core` (Principio XI).** Tocca
esclusivamente i pacchetti di distribuzione:

- `sertor-install-kit` (nuovo modulo `model_policy.py` + `ModelPolicyError` + firma di
  `render_custom_agent` + re-export) — **fonte unica** condivisa, nessuna dipendenza da `sertor-core`;
- `sertor` (`install_rag.py`: concierge · `install_wiki.py`: wiki-curator + guardie riconciliate);
- `sertor-flow` (`install_governance.py`: requirements-analyst/configuration-manager/requirements +
  guardia riconciliata);
- Documentazione utente (`docs/install-copilot.md` + `packages/sertor/docs/install.md`).

`sertor_core` **INVARIATO**. Nessun nuovo `ArtifactKind`/`WriteStrategy`/`Surface`/seam del kit oltre
al parametro `model` di `render_custom_agent` (sostituisce `include_model`, stesso seam esistente) e
al modulo `model_policy.py` (nuovo, ma minimale: una mappa costante + una funzione risolutrice).

**⚠️ Scoperta in fase di generazione dei task (ancoraggio verificato oltre la tabella di
`data-model.md` §5).** Rileggendo il codice reale (non solo gli asset citati dal design), sono stati
trovati **6 test reali aggiuntivi** che asseriscono oggi «`model:` sempre assente» su un **artefatto
reso dal piano d'installazione vero** (non sul renderer isolato) e che quindi **si romperebbero** non
appena i call-site iniettano la policy — non erano enumerati nella tabella di `data-model.md` §5:

- `packages/sertor/tests/test_install_rag.py::test_concierge_agent_deposited_copilot`
- `packages/sertor/tests/test_install_rag.py::test_concierge_copilot_frontmatter_no_claude_names`
  (rischio di **falso positivo**: la policy `claude-haiku-4.5` contiene la sottostringa `claude`)
- `packages/sertor/tests/test_install_rag.py::test_concierge_upgrade_copilot_render_aware`
- `packages/sertor/tests/test_install_wiki_copilot_cli.py::test_custom_agent_omits_model`
- `packages/sertor-flow/tests/test_install_governance_copilot.py::test_cli_custom_agent_omits_model`
- `packages/sertor/tests/test_schema_copilot_frontmatter.py::test_custom_agent_include_model_opt_in_for_completeness`
  (usa il kwarg `include_model=True` **rimosso** dalla firma → `TypeError`, non solo asserzione errata)

Questi 6 sono stati **aggiunti allo scope della riconciliazione** (Fase 4) accanto ai 3 file già
enumerati in `data-model.md` §5 (`test_assets_copilot_guard.py`, `test_schema_copilot_frontmatter.py`,
`test_assets_copilot_parity.py::_render_rag`), perché altrimenti la non-regressione (RNF-4/CS-4)
sarebbe falsa. **Verificato anche l'inverso:** `test_assets_copilot_parity.py::test_copilot_bodies_have_no_claude_product_names`
usa un regex a parola intera **maiuscola** (`\bHaiku\b`/`\bClaude\b`) — i model-ID di policy sono
tutti minuscoli (`claude-haiku-4.5`), quindi quel test **resta verde senza modifiche** (non è tra i
6 sopra).

## Strategia MVP/incrementale

- **Fase 1 (Foundational, blocca tutto)**: il modulo `model_policy.py` + `ModelPolicyError` + la
  nuova firma di `render_custom_agent` sono il **prerequisito condiviso** di ogni user story — senza
  di essi nessun call-site può iniettare la policy.
- **Fase 2/3 (US1+US2+US6, P1 Must, parallele tra loro)**: applicare la policy ai 5 agenti nei due
  pacchetti (`sertor`, `sertor-flow`) — ciascun call-site iniettato è anche il punto in cui si
  implementa il fail-loud (US2) e, per costruzione (stesso renderer su install e upgrade), l'idempotenza
  (US6).
- **Fase 4 (US3+US4, P1 Must)**: riconciliare le guardie esistenti + le 6 scoperte + una nuova guardia
  cross-pacchetto di coerenza/real-asset — è ciò che **dimostra** US1/US2/US3/US4/US6 sui piani veri.
- **Fase 5 (US5+US7+US8, P1 Must/P2 Should)**: documentazione utente, stesso step (DoD).
- **Fase 6 (Polish)**: suite completa + lint + quickstart + verifica trasversale CS-1..7.

La sequenza vincolante è: `TASK-S01` → `Fase 1` (tutti) → `{Fase 2 ‖ Fase 3}` → `Fase 4` → `Fase 5` (può
girare in parallelo a `Fase 4`, tocca solo `.md` di documentazione) → `Fase 6`.

---

## Fase 0 — Setup: pre-flight (1 task)

### TASK-S01 — Pre-flight: sincronizza il venv e verifica lo stato di partenza

```powershell
cd C:\Workspace\Git\Sertor
uv sync --all-packages --extra dev
```

- [ ] Verifica che `uv sync --all-packages --extra dev` completi senza errori.
- [ ] Verifica che i file **da modificare** esistano (baseline):
  - `packages/sertor-install-kit/src/sertor_install_kit/errors.py`
  - `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py`
  - `packages/sertor-install-kit/src/sertor_install_kit/__init__.py`
  - `packages/sertor/src/sertor_installer/install_rag.py`
  - `packages/sertor/src/sertor_installer/install_wiki.py`
  - `packages/sertor-flow/src/sertor_flow/install_governance.py`
  - `packages/sertor/tests/test_assets_copilot_guard.py`
  - `packages/sertor/tests/test_schema_copilot_frontmatter.py`
  - `packages/sertor/tests/test_assets_copilot_parity.py`
  - `packages/sertor/tests/test_install_rag.py`
  - `packages/sertor/tests/test_install_wiki_copilot_cli.py`
  - `packages/sertor-flow/tests/test_install_governance_copilot.py`
  - `docs/install-copilot.md`
  - `packages/sertor/docs/install.md`
- [ ] Verifica che i file **nuovi** da creare non esistano già:
  - `packages/sertor-install-kit/src/sertor_install_kit/model_policy.py`
  - `packages/sertor-install-kit/tests/unit/test_model_policy.py`
  - `packages/sertor-install-kit/tests/unit/test_surfaces_agent_model.py`
  - `packages/sertor/tests/test_model_policy_guard.py`
- [ ] Verifica la baseline **verde** (nessun fallimento pre-modifica) sulle suite che la Fase 4 dovrà
      poi far tornare verdi dopo la riconciliazione:
      ```powershell
      uv run pytest packages/sertor-install-kit/tests -q
      uv run pytest packages/sertor/tests/test_assets_copilot_guard.py `
                    packages/sertor/tests/test_schema_copilot_frontmatter.py `
                    packages/sertor/tests/test_assets_copilot_parity.py `
                    packages/sertor/tests/test_install_rag.py `
                    packages/sertor/tests/test_install_wiki_copilot_cli.py -q
      uv run pytest packages/sertor-flow/tests -q
      ```
- [ ] Registra il conteggio di collection (`--co -q`) per la suite root, per confrontare a fine
      lavoro (nessuna regressione di raccolta):
      ```powershell
      uv run pytest --co -q -m "not cloud" 2>&1 | Select-String "ERROR"
      ```
      Nessun `ERROR` di import atteso.

---

## Fase 1 — Foundational (blocca TUTTE le fasi successive): kit `sertor-install-kit` (6 task)

> Prerequisiti: TASK-S01. Nessuna user story è implementabile prima che questa fase sia completa
> (tutti i call-site dipendono da `resolve_model`/`ModelPolicyError`/la nuova firma del renderer).

### TASK-F01 [P] — `ModelPolicyError` in `sertor_install_kit/errors.py`

→ dipende da: TASK-S01 · **Mappa**: FR-008 · CS-5 · US2 · contratto C1/R3 · data-model §2

- [ ] Aggiungi a `packages/sertor-install-kit/src/sertor_install_kit/errors.py`:
      ```python
      class ModelPolicyError(InstallerError):
          """The model-policy profile has no entry for an in-scope Copilot custom-agent
          (E2-FEAT-015).

          Fail-loud install-time (Principio XII): raised at PLAN-BUILD time (before any artifact
          is written), never rendered as a silently-omitted/incomplete `model:` field.
          """
      ```
- [ ] Verifica: `uv run python -c "from sertor_install_kit.errors import ModelPolicyError, InstallerError; assert issubclass(ModelPolicyError, InstallerError)"`.

### TASK-F02 [P] — Firma di `render_custom_agent`: `include_model: bool` → `model: str | None`

→ dipende da: TASK-S01 (nessuna dipendenza da TASK-F01) · **Mappa**: FR-001/002/013 · CS-1/CS-2 · US1/US4
· contratto C2/R6-R9 · data-model §3 · research DA-D-2

**Contesto di ancoraggio.** `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py:53-74`.
Oggi `include_model=False` (default) omette `model:`; `include_model=True` fa **eco verbatim** del
valore canonico (`model: haiku`, alias Claude invalido su Copilot). Nessuna via per emettere un
valore *diverso* da quello canonico.

- [ ] Sostituisci la funzione (stessa collocazione, `packages/sertor-install-kit/src/sertor_install_kit/surfaces.py`):
      ```python
      def render_custom_agent(canonical_text: str, *, model: str | None = None) -> str:
          """Renders a Copilot custom-agent (`*.agent.md`) from the canonical agent asset.

          The persona **body** is the shared substrate (reused verbatim); the frontmatter is
          translated to the Copilot custom-agent shape (`name`/`description`/`tools` preserved
          when present).

          E2-FEAT-015: `model`, when given, is a POLICY-resolved model-ID (e.g. `claude-haiku-4.5`)
          SUBSTITUTED for whatever `model:` the canonical frontmatter carries — a Claude alias
          (e.g. `haiku`) is INVALID on Copilot and is NEVER echoed. `model=None` (default) OMITS
          the field entirely (byte-identical to the pre-FEAT-015 `include_model=False` behaviour);
          the Claude plan never calls this renderer (byte-copy `.claude/**`), so this is a no-op
          there (FR-012/RNF-5).
          """
          front, body = split_frontmatter(canonical_text)
          fields = _parse_simple_frontmatter(front)
          lines = [_FRONTMATTER_FENCE]
          for key in ("name", "description", "tools"):
              if key in fields:
                  lines.append(f"{key}: {_yaml_scalar(fields[key])}")
          if model is not None:
              lines.append(f"model: {_yaml_scalar(model)}")
          lines.append(_FRONTMATTER_FENCE)
          lines.append("")
          return "\n".join(lines) + "\n" + body.lstrip("\n")
      ```
      Nota: la funzione non legge **mai** più `fields["model"]` (il valore canonico non è più
      raggiungibile) — l'eco verbatim (bug del vecchio `include_model=True`) è impossibile per
      costruzione, non solo per convenzione.
- [ ] Verifica al volo (nessun test-runner ancora, solo import):
      ```powershell
      uv run python -c "
      from sertor_install_kit.surfaces import render_custom_agent, split_frontmatter
      asset = '---\nname: x\nmodel: haiku\n---\n\nbody\n'
      assert 'model:' not in split_frontmatter(render_custom_agent(asset))[0]
      assert 'model: claude-haiku-4.5' in split_frontmatter(render_custom_agent(asset, model=\"claude-haiku-4.5\"))[0]
      print('ok')
      "
      ```

### TASK-F03 — Modulo `model_policy.py` (fonte unica versionata)

→ dipende da: TASK-F01 (importa `ModelPolicyError`) · **Mappa**: FR-005/006/007 · CS-3 · US3 ·
contratto C1/R1-R5 · data-model §1 · research DA-D-1

- [ ] Crea `packages/sertor-install-kit/src/sertor_install_kit/model_policy.py`:
      ```python
      """Versioned model-policy profile for Copilot CLI custom-agents (E2-FEAT-015).

      Single source of truth, agent -> model-ID, shared by `sertor` and `sertor-flow` without
      either depending on `sertor-core` (the kit is the one dependency both already share). Bump
      a model-ID by editing ONE entry here (RNF-2/CS-3); bump `MODEL_POLICY_VERSION` when the bump
      is a deliberate POLICY change (FR-007/NFR-004), not merely a persona/body edit elsewhere.
      """
      from __future__ import annotations

      from sertor_install_kit.errors import ModelPolicyError

      MODEL_POLICY_VERSION = "1"

      # Fonte unica agente -> model-ID (FR-005). Default ragionato iniziale (spec §Policy):
      # meccanico/dispatcher -> economico/veloce; scrittura/reasoning/sintesi -> capace.
      _MODEL_POLICY: dict[str, str] = {
          "concierge": "claude-haiku-4.5",
          "configuration-manager": "claude-haiku-4.5",
          "requirements-analyst": "claude-sonnet-4.6",
          "requirements": "claude-sonnet-4.6",
          "wiki-curator": "claude-sonnet-4.6",
      }

      IN_SCOPE_AGENTS: frozenset[str] = frozenset(_MODEL_POLICY)


      def resolve_model(agent_name: str) -> str:
          """Returns the policy model-ID for `agent_name`; fail-loud if uncovered (FR-008).

          Raises `ModelPolicyError` naming the missing agent — never a silent `None`/default
          (Principio IV/XII). Deterministic (RNF-3): same name + same profile version -> same id.
          """
          try:
              return _MODEL_POLICY[agent_name]
          except KeyError:
              raise ModelPolicyError(
                  f"model-policy profile (v{MODEL_POLICY_VERSION}) has no entry "
                  f"for in-scope agent {agent_name!r}"
              ) from None
      ```
- [ ] Verifica al volo:
      ```powershell
      uv run python -c "
      from sertor_install_kit.model_policy import resolve_model, IN_SCOPE_AGENTS
      print({a: resolve_model(a) for a in sorted(IN_SCOPE_AGENTS)})
      "
      ```
      Atteso: 5 voci, concierge/configuration-manager → `claude-haiku-4.5`, le altre tre →
      `claude-sonnet-4.6`.

### TASK-F04 — Re-export dal kit (`__init__.py`)

→ dipende da: TASK-F01, TASK-F02, TASK-F03 · **Mappa**: FR-006 · US3

- [ ] In `packages/sertor-install-kit/src/sertor_install_kit/__init__.py`, aggiungi l'import (dopo
      `from sertor_install_kit.mcp_merge import ...`, prima di `from sertor_install_kit.observability
      import log_event`):
      ```python
      from sertor_install_kit.model_policy import IN_SCOPE_AGENTS, MODEL_POLICY_VERSION, resolve_model
      ```
- [ ] Aggiungi `ModelPolicyError` all'import esistente da `errors`:
      ```python
      from sertor_install_kit.errors import ConfigError, InstallerError, ModelPolicyError
      ```
- [ ] Aggiorna `__all__`: aggiungi `"ModelPolicyError"` nella sezione `# errors` esistente, e una
      nuova sezione dopo `# sync`:
      ```python
          # sync
          "sync_assets",
          "sync_subtree",
          # model policy (E2-FEAT-015)
          "resolve_model",
          "MODEL_POLICY_VERSION",
          "IN_SCOPE_AGENTS",
      ]
      ```
- [ ] Verifica: `uv run python -c "from sertor_install_kit import resolve_model, MODEL_POLICY_VERSION, IN_SCOPE_AGENTS, ModelPolicyError; print('ok')"`.

### TASK-F05 [P] — Test unitari kit C1: `test_model_policy.py`

→ dipende da: TASK-F03 · **Mappa**: contratto C1/R1-R5 · US2/US3

- [ ] Crea `packages/sertor-install-kit/tests/unit/test_model_policy.py`:
      ```python
      """Unit tests for the model-policy profile (E2-FEAT-015, contract C1).

      Pure/offline: no I/O, no network. `resolve_model` is the single fail-loud accessor.
      """
      from __future__ import annotations

      import pytest

      from sertor_install_kit.errors import ModelPolicyError
      from sertor_install_kit.model_policy import IN_SCOPE_AGENTS, MODEL_POLICY_VERSION, resolve_model


      def test_r1_all_five_in_scope_agents_resolve():
          for name in IN_SCOPE_AGENTS:
              assert resolve_model(name)  # non-empty


      def test_r1_exactly_five_agents_in_scope():
          assert IN_SCOPE_AGENTS == frozenset({
              "concierge", "configuration-manager", "requirements-analyst",
              "requirements", "wiki-curator",
          })


      def test_r2_deterministic():
          assert resolve_model("concierge") == resolve_model("concierge")


      def test_r3_fail_loud_names_missing_agent():
          with pytest.raises(ModelPolicyError, match="unknown-agent"):
              resolve_model("unknown-agent")


      def test_r3_anti_pattern_never_returns_none_or_empty():
          """Anti-pattern: an uncovered name never silently resolves to None/''."""
          try:
              value = resolve_model("nonexistent")
          except ModelPolicyError:
              pass
          else:
              pytest.fail(f"expected ModelPolicyError, got a silent value: {value!r}")


      def test_r5_version_marker_is_a_non_empty_string():
          assert isinstance(MODEL_POLICY_VERSION, str) and MODEL_POLICY_VERSION


      def test_pin_initial_reasoned_defaults():
          """Pin (regression on accidental edits): the initial reasoned policy values (spec table)."""
          assert resolve_model("concierge") == "claude-haiku-4.5"
          assert resolve_model("configuration-manager") == "claude-haiku-4.5"
          assert resolve_model("requirements-analyst") == "claude-sonnet-4.6"
          assert resolve_model("requirements") == "claude-sonnet-4.6"
          assert resolve_model("wiki-curator") == "claude-sonnet-4.6"
      ```
- [ ] `uv run pytest packages/sertor-install-kit/tests/unit/test_model_policy.py -v` — 7 `PASSED`.

### TASK-F06 [P] — Test unitari kit C2: `test_surfaces_agent_model.py`

→ dipende da: TASK-F02 · **Mappa**: contratto C2/R6-R9 · US1/US4 · research DA-D-3

- [ ] Crea `packages/sertor-install-kit/tests/unit/test_surfaces_agent_model.py`:
      ```python
      """Unit tests for `render_custom_agent`'s `model` parameter (E2-FEAT-015, contract C2).

      Pure/offline, kit-level (where the function is defined) — complements the package-level
      guard suites in `sertor`'s tests.
      """
      from __future__ import annotations

      from sertor_install_kit.surfaces import render_custom_agent, split_frontmatter

      _ASSET_WITH_CLAUDE_ALIAS = (
          "---\nname: x\ndescription: y\ntools: z\nmodel: haiku\n---\n\npersona body\n"
      )


      def _model_value(front: str) -> str | None:
          for line in front.splitlines():
              if line.strip().startswith("model:"):
                  return line.split(":", 1)[1].strip()
          return None


      def test_r6_omits_model_by_default():
          front = split_frontmatter(render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS))[0]
          assert _model_value(front) is None


      def test_r7_substitutes_policy_model_over_canonical_alias():
          front = split_frontmatter(
              render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS, model="claude-haiku-4.5")
          )[0]
          assert _model_value(front) == "claude-haiku-4.5"


      def test_r8_no_bare_claude_alias_leak_even_though_id_contains_substring():
          """A policy id like `claude-haiku-4.5` legitimately CONTAINS the substring `haiku` — the
          anti-pattern is a BARE alias (`haiku`/`sonnet`/`opus`), not the substring (research DA-D-3).
          """
          front = split_frontmatter(
              render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS, model="claude-haiku-4.5")
          )[0]
          value = _model_value(front)
          assert value not in {"haiku", "sonnet", "opus"}
          assert value is not None and "haiku" in value  # sanity: substring IS present, by design


      def test_r9_persona_identity_preserved_with_model():
          rendered = render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS, model="claude-haiku-4.5")
          front, body = split_frontmatter(rendered)
          assert "name: x" in front
          assert "description: y" in front
          assert "tools: z" in front
          assert body.strip() == "persona body"


      def test_model_none_matches_pre_feat015_omission_byte_for_byte():
          """Anti-drift on the signature change: `model=None` (new default) omits identically to the
          pre-FEAT-015 `include_model=False` behaviour."""
          front_explicit = split_frontmatter(render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS, model=None))[0]
          front_default = split_frontmatter(render_custom_agent(_ASSET_WITH_CLAUDE_ALIAS))[0]
          assert front_explicit == front_default
          assert "model:" not in front_default
      ```
- [ ] `uv run pytest packages/sertor-install-kit/tests/unit/test_surfaces_agent_model.py -v` —
      5 `PASSED`.

**Verifica di chiusura Fase 1:**

- [ ] `uv run pytest packages/sertor-install-kit/tests -q` — tutto verde (nessuna regressione sul
      resto del kit).
- [ ] `uv run ruff check packages/sertor-install-kit/src/sertor_install_kit/model_policy.py packages/sertor-install-kit/src/sertor_install_kit/errors.py packages/sertor-install-kit/src/sertor_install_kit/surfaces.py packages/sertor-install-kit/src/sertor_install_kit/__init__.py packages/sertor-install-kit/tests/unit/test_model_policy.py packages/sertor-install-kit/tests/unit/test_surfaces_agent_model.py` — zero errori.

---

## Fase 2 — US1+US2+US6 (P1 Must): applicazione della policy nel pacchetto `sertor` [P con Fase 3]

> Prerequisiti: Fase 1 completa. Parallelizzabile con Fase 3 (pacchetto diverso). I due task di
> questa fase toccano file diversi (`install_rag.py`/`install_wiki.py`) → `[P]` tra loro.

### TASK-US1-01 [P] — `install_rag.py`: iniezione policy su `concierge` + fail-loud in `build_rag_plan`

→ dipende da: Fase 1 (TASK-F01..F04) · **Mappa**: FR-001/002/003/008/009/010/011/012 · CS-1/2/4/5/7 ·
US1/US2/US6 · contratto C3/R10-R13 · data-model §4 · research DA-D-2/DA-D-4

**Contesto di ancoraggio.** `packages/sertor/src/sertor_installer/install_rag.py`: `_render_rag_file`
(`:363-375`), `build_rag_plan` (`:378-...`, `is_copilot = assistant is AssistantId.COPILOT_CLI` alla
riga `:396`). `_apply_rag_upgrade` (`:939`) già chiama `_render_rag_file` → l'iniezione qui copre
anche l'upgrade (idempotenza, US6) senza toccare quella funzione.

- [ ] Aggiungi l'import (ordine alfabetico, dopo `from sertor_install_kit.mcp_merge import merge_mcp,
      remove_mcp_server`, prima di `from sertor_install_kit.observability import log_event`):
      ```python
      from sertor_install_kit.model_policy import resolve_model
      ```
- [ ] Modifica `_render_rag_file`:
      ```python
      def _render_rag_file(art: Artifact) -> str:
          """Content for a rag FILE artifact: rendered for a Copilot custom-agent, byte-copy otherwise.

          Local render-aware helper (a `_render_for_target` twin of `install_wiki`/
          `install_governance`), NOT a new kit seam (`render_custom_agent` is already exported).
          The `.agent.md` branch maps the Claude frontmatter to the Copilot custom-agent shape,
          substituting the POLICY model-ID (E2-FEAT-015) — never echoing the Claude alias. Every
          other FILE (native skill `.md`, hook `.ps1`) is reused verbatim (byte-copy).
          """
          assert art.source is not None
          text = read_asset_text(art.source)
          if art.target_rel.endswith(".agent.md"):
              name = art.target_rel.rsplit("/", 1)[-1].removesuffix(".agent.md")
              return render_custom_agent(text, model=resolve_model(name))
          return text
      ```
- [ ] In `build_rag_plan`, subito dopo la riga `is_copilot = assistant is AssistantId.COPILOT_CLI`,
      aggiungi la validazione fail-loud **prima** di costruire qualunque `Artifact`:
      ```python
      is_copilot = assistant is AssistantId.COPILOT_CLI
      if is_copilot:
          # Fail-loud BEFORE any artifact is written (FR-008/009, DA-D-4): this plan deposits a
          # single Copilot agent (`concierge`) — validate the policy covers it up front.
          resolve_model("concierge")
      ```
- [ ] Verifica al volo:
      ```powershell
      uv run python -c "
      from pathlib import Path
      import tempfile
      from sertor_install_kit.assistant import AssistantId
      from sertor_installer.install_rag import build_rag_plan, _render_rag_file
      from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
      with tempfile.TemporaryDirectory() as d:
          profile = RagHostProfile.from_options(RagInstallOptions(target_root=Path(d), backend='azure', with_deps=False))
          plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
          concierge = next(a for a in plan if a.target_rel.endswith('concierge.agent.md'))
          rendered = _render_rag_file(concierge)
          assert 'model: claude-haiku-4.5' in rendered
          print('ok')
      "
      ```

### TASK-US1-02 [P] — `install_wiki.py`: iniezione policy su `wiki-curator` + fail-loud in `_build_copilot_wiki_plan`

→ dipende da: Fase 1 (TASK-F01..F04) · **Mappa**: FR-001/002/003/008/009/010/011/012 · CS-1/2/4/5/7 ·
US1/US2/US6 · contratto C3/R10-R13 · data-model §4 · research DA-D-2/DA-D-4

**Contesto di ancoraggio.** `packages/sertor/src/sertor_installer/install_wiki.py`: `_render_for_target`
(`:278-296`), `_build_copilot_wiki_plan` (`:208-270`, chiamata da `build_install_plan` quando
`assistant is AssistantId.COPILOT_CLI`, riga `:148`). L'upgrade (riga `:491`) chiama già
`_render_for_target` → idempotenza (US6) coperta senza modifiche lì.

- [ ] Aggiungi l'import (ordine alfabetico, dopo il blocco `from sertor_install_kit.lifecycle import
      execute_lifecycle as _kit_execute_lifecycle`, prima di `from sertor_install_kit.settings_merge
      import remove_settings_entries`):
      ```python
      from sertor_install_kit.model_policy import resolve_model
      ```
- [ ] Modifica il ramo `.agent.md` di `_render_for_target`:
      ```python
      def _render_for_target(art: Artifact) -> str:
          """Content for a FILE artifact: rendered for Copilot skill/agent files, byte-copy otherwise.
          ...
          """
          assert art.source is not None
          canonical = read_asset_text(art.source)
          if art.target_rel == _COPILOT_SKILL_MD and art.source == _WIKI_COMMAND_SRC:
              return render_native_skill(canonical, _WIKI_SKILL_NAME)
          if art.target_rel.endswith(_RENDER_PROMPT_SUFFIX):
              return render_prompt_file(canonical)
          if art.target_rel.endswith(_RENDER_AGENT_SUFFIX):
              name = art.target_rel.rsplit("/", 1)[-1].removesuffix(_RENDER_AGENT_SUFFIX)
              return render_custom_agent(canonical, model=resolve_model(name))
          return canonical
      ```
- [ ] In `_build_copilot_wiki_plan`, subito all'inizio della funzione (prima di `plan: list[Artifact]
      = []`), aggiungi la validazione fail-loud:
      ```python
      def _build_copilot_wiki_plan(assistant: AssistantId) -> list[Artifact]:
          """... (docstring invariata) ..."""
          # Fail-loud BEFORE any artifact is written (FR-008/009, DA-D-4): this plan deposits a
          # single Copilot agent (`wiki-curator`) — validate the policy covers it up front.
          resolve_model("wiki-curator")

          plan: list[Artifact] = []
          ...
      ```
- [ ] Verifica al volo:
      ```powershell
      uv run python -c "
      from sertor_install_kit.assistant import AssistantId
      from sertor_installer.install_wiki import build_install_plan, _render_for_target
      plan = build_install_plan(AssistantId.COPILOT_CLI)
      curator = next(a for a in plan if a.target_rel.endswith('wiki-curator.agent.md'))
      rendered = _render_for_target(curator)
      assert 'model: claude-sonnet-4.6' in rendered
      print('ok')
      "
      ```

**Verifica di chiusura Fase 2:**

- [ ] `uv run pytest packages/sertor/tests/test_install_rag.py packages/sertor/tests/test_install_wiki_copilot_cli.py -q`
      → atteso **rosso** a questo punto (i 4 test scoperti nella nota di apertura non sono ancora
      riconciliati) — normale, la riconciliazione è Fase 4. Non bloccante per procedere alla Fase 3.

---

## Fase 3 — US1+US2+US6 (P1 Must): applicazione della policy nel pacchetto `sertor-flow` [P con Fase 2]

> Prerequisiti: Fase 1 completa. Parallelizzabile con Fase 2 (pacchetto diverso, nessuna dipendenza
> reciproca).

### TASK-US1-03 — `install_governance.py`: iniezione policy sui 3 agenti + fail-loud in `build_governance_plan`

→ dipende da: Fase 1 (TASK-F01..F04) · **Mappa**: FR-001/002/003/004/008/009/010/011/012 ·
CS-1/2/3/4/5/7 · US1/US2/US3/US6 · contratto C3/R10-R13 · data-model §4 · research DA-D-2/DA-D-4

**Contesto di ancoraggio.** `packages/sertor-flow/src/sertor_flow/install_governance.py`:
`_SERTOR_AUTHORED` (`:103-111`, tuple `(source, surface, claude_name, copilot_name)` — i tre
`copilot_name` sono **esattamente** le chiavi di `_MODEL_POLICY`: `requirements-analyst`,
`configuration-manager`, `requirements`); `build_governance_plan` (`:127-191`); `_render_for_target`
(`:199-211`). L'upgrade (riga `:412`) chiama già `_render_for_target` → idempotenza (US6) coperta.
**Unico plan-builder con >1 agente in ambito** → la validazione fail-loud DEVE precedere l'intero
loop di costruzione (altrimenti un profilo incompleto lascerebbe scritti gli agenti già processati).

- [ ] Aggiungi `resolve_model` all'import esistente `from sertor_install_kit import (...)` (ordine
      alfabetico: dopo `render_prompt_file`, prima di `update_file_if_changed`):
      ```python
      from sertor_install_kit import (
          Artifact,
          ArtifactKind,
          ArtifactOutcome,
          AssistantId,
          AssistantProfile,
          CommandRunner,
          ConfigError,
          InstallerError,
          InstallReport,
          LifecycleOp,
          Outcome,
          SertorOwnedPaths,
          SharedEdit,
          SharedEditKind,
          Surface,
          WriteStrategy,
          project_removal,
          project_update,
          read_asset_text,
          remove_marker_block,
          remove_path,
          render_custom_agent,
          render_prompt_file,
          resolve_model,
          update_file_if_changed,
          update_marker_block,
          write_marker_block,
      )
      ```
- [ ] In `build_governance_plan`, subito dopo `plan: list[Artifact] = []` e **prima** del loop
      `for source, surface, claude_name, copilot_name in _SERTOR_AUTHORED:`, aggiungi la validazione
      fail-loud per tutti e 3 gli agenti:
      ```python
      aprofile = AssistantProfile.for_assistant(AssistantId.from_str(profile.assistant))
      plan: list[Artifact] = []

      if aprofile.assistant is AssistantId.COPILOT_CLI:
          # Fail-loud BEFORE any artifact is written (FR-008/009, DA-D-4): this plan deposits
          # THREE Copilot agents in one list — validate the policy covers all of them up front,
          # so a profile gap never leaves the first N already written (partial install).
          for _source, _surface, _claude_name, copilot_name in _SERTOR_AUTHORED:
              resolve_model(copilot_name)

      # 1+2. Sertor-authored AGENT/COMMAND surfaces, routed per-assistant via the AssistantProfile.
      for source, surface, claude_name, copilot_name in _SERTOR_AUTHORED:
          ...
      ```
- [ ] Modifica il ramo `.agent.md` di `_render_for_target`:
      ```python
      def _render_for_target(art: Artifact) -> str:
          """Content for a FILE artifact: rendered for Copilot prompt/agent files, byte-copy otherwise.
          ...
          """
          assert art.source is not None
          canonical = read_asset_text(_ANCHOR, art.source)
          if art.target_rel.endswith(_RENDER_PROMPT_SUFFIX):
              return render_prompt_file(canonical)
          if art.target_rel.endswith(_RENDER_AGENT_SUFFIX):
              name = art.target_rel.rsplit("/", 1)[-1].removesuffix(_RENDER_AGENT_SUFFIX)
              return render_custom_agent(canonical, model=resolve_model(name))
          return canonical
      ```
- [ ] Verifica al volo:
      ```powershell
      uv run python -c "
      from pathlib import Path
      import tempfile
      from sertor_flow.install_governance import build_governance_plan, _render_for_target
      from sertor_flow.profile import build_governance_profile
      with tempfile.TemporaryDirectory() as d:
          profile = build_governance_profile(Path(d), assistant='copilot-cli')
          plan = build_governance_plan(profile)
          for name, model in (('requirements-analyst', 'claude-sonnet-4.6'),
                              ('configuration-manager', 'claude-haiku-4.5'),
                              ('requirements', 'claude-sonnet-4.6')):
              art = next(a for a in plan if a.target_rel.endswith(f'{name}.agent.md'))
              rendered = _render_for_target(art)
              assert f'model: {model}' in rendered, (name, rendered)
      print('ok')
      "
      ```

**Verifica di chiusura Fase 3:**

- [ ] `uv run pytest packages/sertor-flow/tests/test_install_governance_copilot.py -q` → atteso
      **rosso** su `test_cli_custom_agent_omits_model` (riconciliazione = Fase 4); il resto verde.

---

## Fase 4 — US3+US4 (P1 Must): riconciliazione guardie esistenti + nuova guardia cross-pacchetto (7 task)

> Prerequisiti: Fase 2 **e** Fase 3 complete (le guardie leggono i render/piani reali dei tre
> pacchetti). I task di file distinti sono `[P]`; l'ultimo (nuova guardia cross-pacchetto) dipende
> da tutti i precedenti di questa fase essendo l'unico che tocca tutti e tre i piani insieme.

### TASK-US4-01 [P] — Riconcilia `test_assets_copilot_guard.py` (sertor)

→ dipende da: TASK-F02 · **Mappa**: FR-013 · CS-2 · US4 · contratto C2/R7-R8 · research DA-D-3

**Nota di verifica (Fase generazione task):** `test_custom_agent_omits_model_field` e
`test_custom_agent_drops_injected_model` chiamano `render_custom_agent` **senza** `model=` →
restano **invariati** (l'omissione di default non cambia). Aggiungiamo **solo** una copertura
ADDITIVA per il percorso di sostituzione (nessuna asserzione esistente rimossa).

- [ ] In `packages/sertor/tests/test_assets_copilot_guard.py`, aggiungi (dopo
      `test_custom_agent_drops_injected_model`):
      ```python
      def _model_value(front: str) -> str | None:
          """Parsed value of a `model:` line (not a substring check — `claude-haiku-4.5` legitimately
          contains `haiku`; research DA-D-3)."""
          for line in front.splitlines():
              if line.strip().startswith("model:"):
                  return line.split(":", 1)[1].strip()
          return None


      def test_custom_agent_substitutes_policy_model_never_echoes_claude_alias():
          """E2-FEAT-015: an asset with `model: haiku` (Claude alias) + a policy model-id →
          the rendered file carries the POLICY id, never the Claude alias, even though the
          policy id may contain it as a substring (e.g. `claude-haiku-4.5`)."""
          asset = "---\nname: x\ndescription: y\ntools: z\nmodel: haiku\n---\n\nbody\n"
          front = split_frontmatter(render_custom_agent(asset, model="claude-haiku-4.5"))[0]
          assert _model_value(front) == "claude-haiku-4.5"
          assert _model_value(front) not in {"haiku", "sonnet", "opus"}
          assert "name: x" in front
          assert "description: y" in front
          assert "tools: z" in front
      ```
- [ ] `uv run pytest packages/sertor/tests/test_assets_copilot_guard.py -v` — tutto verde (compreso
      il nuovo test).

### TASK-US4-02 [P] — Riconcilia `test_schema_copilot_frontmatter.py` (sertor)

→ dipende da: TASK-F02 · **Mappa**: FR-013 · CS-2 · US4 · contratto C2/R6-R9 · research DA-D-3

**Rottura reale:** `test_custom_agent_include_model_opt_in_for_completeness` usa il kwarg
`include_model=True`, **rimosso** dalla firma → `TypeError` (non solo asserzione errata). Le altre
due (`test_custom_agent_has_no_model`, `test_anti_pattern_custom_agent_drops_claude_model`) non
passano kwarg → restano **invariate**.

- [ ] Sostituisci **solo** `test_custom_agent_include_model_opt_in_for_completeness`:
      ```python
      def test_custom_agent_include_model_opt_in_for_completeness():
          """E2-FEAT-015 (was: `include_model=True` echo): the model is caller-supplied POLICY,
          never an echo of the canonical value — passing `model=<policy-id>` emits exactly that
          value, never the Claude alias (`haiku`) the canonical asset carries."""
          front = split_frontmatter(
              render_custom_agent(_AGENT_ASSET, model="claude-haiku-4.5")
          )[0]
          assert _model_value(front) == "claude-haiku-4.5"
          assert _model_value(front) not in {"haiku", "sonnet", "opus"}
      ```
- [ ] Aggiungi l'helper `_model_value` in cima al file (dopo gli import, prima di `_PROMPT_ASSET`):
      ```python
      def _model_value(front: str) -> str | None:
          """Parsed value of a `model:` line (not a substring check — `claude-haiku-4.5` legitimately
          contains `haiku`; research DA-D-3)."""
          for line in front.splitlines():
              if line.strip().startswith("model:"):
                  return line.split(":", 1)[1].strip()
          return None
      ```
- [ ] `uv run pytest packages/sertor/tests/test_schema_copilot_frontmatter.py -v` — tutto verde.

### TASK-US4-03 [P] — Allinea `_render_rag` in `test_assets_copilot_parity.py` (sertor)

→ dipende da: TASK-US1-01 · **Mappa**: FR-002 · CS-2 · US4 · data-model §5 · research DA-D-3

**Perché.** `_render_rag` è il mirror del render reale usato dalle guardie (a)(b)(c) no-leak; se non
inietta la policy, il mirror **diverge** dalla realtà (il piano vero ora inietta, il mirror no) e le
guardie testerebbero un rendering diverso da quello che un host Copilot riceve davvero.

- [ ] Aggiungi l'import: `from sertor_install_kit.model_policy import resolve_model`.
- [ ] Sostituisci `_render_rag`:
      ```python
      def _render_rag(art: Artifact) -> str:
          # G1 (E12, R-1 CRITICAL): mirror the REAL render of the plan
          # (`install_rag._render_rag_file`). A Copilot custom-agent (`.agent.md`, e.g.
          # `concierge`) is rendered via `render_custom_agent` with the POLICY model
          # substituted (E2-FEAT-015); every other FILE/MARKER_BLOCK body is byte-copy. If this
          # byte-copied the `.agent.md` source instead — or omitted the policy model — the Claude
          # `model: sonnet` frontmatter (or a bare alias) could slip past the no-leak checks
          # (a/b/c) on Copilot.
          assert art.source is not None
          text = read_asset_text(art.source)
          if art.target_rel.endswith(".agent.md"):
              name = art.target_rel.rsplit("/", 1)[-1].removesuffix(".agent.md")
              return render_custom_agent(text, model=resolve_model(name))
          return text
      ```
- [ ] `uv run pytest packages/sertor/tests/test_assets_copilot_parity.py -v` — tutto verde,
      **incluso** `test_copilot_bodies_have_no_claude_product_names` (verificato: i model-ID di
      policy sono minuscoli, `\bHaiku\b`/`\bClaude\b` non li intercettano — nessuna modifica
      necessaria a quel test).

### TASK-US4-04 [P] — Riconcilia i 3 test reali in `test_install_rag.py` (sertor)

→ dipende da: TASK-US1-01 · **Mappa**: FR-001/002/010 · CS-1/2/4/7 · US1/US4/US6 · contratto
C3/R10/R11/R13 · research DA-D-3

**I 3 test scoperti (vedi nota di apertura):**

- [ ] Sostituisci `test_concierge_agent_deposited_copilot`:
      ```python
      def test_concierge_agent_deposited_copilot(tmp_path: Path, make_runner):  # US8-AC1 / R-1
          runner = make_runner()
          _run(tmp_path, runner, backend="azure", assistant=AssistantId.COPILOT_CLI)
          dest = tmp_path / ".github" / "agents" / "concierge.agent.md"
          assert dest.is_file()
          # E2-FEAT-015: Copilot custom-agent → `render_custom_agent` substitutes the POLICY
          # model-id (never a bare Claude alias — FEAT-011/049 non-regression).
          from sertor_install_kit.model_policy import resolve_model

          front = _frontmatter(dest.read_text(encoding="utf-8"))
          assert f"model: {resolve_model('concierge')}" in front
      ```
- [ ] Sostituisci `test_concierge_copilot_frontmatter_no_claude_names`:
      ```python
      def test_concierge_copilot_frontmatter_no_claude_names(tmp_path: Path, make_runner):  # US8-AC3
          """No Claude product/model name leaks into the Copilot frontmatter — EXCEPT the policy
          `model:` line itself, which legitimately carries an id containing the substring "claude"
          (E2-FEAT-015, e.g. `claude-haiku-4.5`, a NATIVE Copilot model id, not a Claude alias)."""
          runner = make_runner()
          _run(tmp_path, runner, backend="azure", assistant=AssistantId.COPILOT_CLI)
          text = (tmp_path / ".github" / "agents" / "concierge.agent.md").read_text(encoding="utf-8")
          fm = _frontmatter(text)
          non_model_lines = "\n".join(
              ln for ln in fm.splitlines() if not ln.strip().startswith("model:")
          )
          for name in ("Claude", "Opus", "Haiku", "claude"):
              assert name not in non_model_lines, (
                  f"Claude product/model name {name!r} leaked into Copilot frontmatter "
                  f"(outside model:)"
              )
          model_line = next(ln for ln in fm.splitlines() if ln.strip().startswith("model:"))
          value = model_line.split(":", 1)[1].strip()
          assert value not in {"haiku", "sonnet", "opus"}
      ```
- [ ] Sostituisci le ultime 2 righe di `test_concierge_upgrade_copilot_render_aware`:
      ```python
      def test_concierge_upgrade_copilot_render_aware(tmp_path: Path, make_runner):  # W7
          runner = make_runner()
          profile = RagHostProfile.from_options(
              RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
          )
          plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
          # simulate a stale Copilot agent (raw Claude source with the `model:` pin) to force an upgrade
          dest = tmp_path / ".github" / "agents" / "concierge.agent.md"
          dest.parent.mkdir(parents=True, exist_ok=True)
          dest.write_text("---\nname: concierge\nmodel: sonnet\n---\nold body\n", encoding="utf-8")
          execute_rag_lifecycle(
              plan, profile, runner, LifecycleOp.UPGRADE, assistant=AssistantId.COPILOT_CLI
          )
          from sertor_install_kit.model_policy import resolve_model

          fm = _frontmatter(dest.read_text(encoding="utf-8"))
          # upgrade re-rendered the agent: the stale Claude `model: sonnet` is replaced by the
          # policy id (E2-FEAT-015, US6 idempotence/lifecycle).
          assert f"model: {resolve_model('concierge')}" in fm
          assert "model: sonnet" not in fm
      ```
- [ ] `uv run pytest packages/sertor/tests/test_install_rag.py -v` — tutto verde (incluse
      `test_concierge_agent_deposited_claude`/`test_concierge_model_pin_in_frontmatter_only`/
      `test_concierge_body_host_agnostic` — INVARIATI, path Claude/asset canonico non toccati).

### TASK-US4-05 [P] — Riconcilia `test_install_wiki_copilot_cli.py::test_custom_agent_omits_model` (sertor)

→ dipende da: TASK-US1-02 · **Mappa**: FR-001/002 · CS-1 · US1/US4 · contratto C3/R10/R11

- [ ] Sostituisci (rinominando, il comportamento non è più «omits»):
      ```python
      def test_custom_agent_has_policy_model(tmp_path: Path):  # E2-FEAT-015 (was FR-017/SC-005)
          _install(tmp_path)
          from sertor_install_kit.model_policy import resolve_model
          from sertor_installer.surfaces import split_frontmatter

          text = (tmp_path / ".github/agents/wiki-curator.agent.md").read_text(encoding="utf-8")
          front = split_frontmatter(text)[0]
          assert f"model: {resolve_model('wiki-curator')}" in front
      ```
- [ ] `uv run pytest packages/sertor/tests/test_install_wiki_copilot_cli.py -v` — tutto verde.

### TASK-US4-06 [P] — Riconcilia `test_install_governance_copilot.py::test_cli_custom_agent_omits_model` (sertor-flow)

→ dipende da: TASK-US1-03 · **Mappa**: FR-001/002/004 · CS-1/3 · US1/US3/US4 · contratto C3/R10/R11

- [ ] Sostituisci (rinominando):
      ```python
      def test_cli_custom_agent_has_policy_model(installed_copilot_cli: Path):
          """E2-FEAT-015 (was FR-017): the CLI custom-agent for the COMMAND carries the POLICY
          model-id, never the omitted/Claude-alias state of FEAT-011/049."""
          from sertor_install_kit import split_frontmatter
          from sertor_install_kit.model_policy import resolve_model

          text = (installed_copilot_cli / ".github/agents/requirements.agent.md").read_text(
              encoding="utf-8"
          )
          front = split_frontmatter(text)[0]
          assert f"model: {resolve_model('requirements')}" in front
      ```
- [ ] `uv run pytest packages/sertor-flow/tests/test_install_governance_copilot.py -v` — tutto verde.

### TASK-US4-07 — Nuova guardia cross-pacchetto: `test_model_policy_guard.py` (sertor)

→ dipende da: TASK-US1-01, TASK-US1-02, TASK-US1-03 (tutti e tre i call-site devono essere già
iniettati) · **Mappa**: FR-004/005/008/009 · CS-1/3/5 · US1/US2/US3/US4 · contratto C3/R10-R12,
C5/R15 · data-model §5

**Collocazione (decisione di implementazione presa in questa fase, non fissata dal design):** un
file NUOVO in `packages/sertor/tests/` (non nel kit, non in `sertor-flow`) che importa
`sertor_flow` **lazily**, replicando esattamente il pattern già usato da
`test_assets_copilot_parity.py` per la stessa esigenza cross-pacchetto (nessuna dipendenza di
`sertor-flow` da `sertor`, solo il test la attraversa). Rende via le funzioni `_render_*` **pure**
dei tre moduli (nessuna scrittura su disco, nessun mock di `specify`/`CommandRunner` — offline puro,
RNF-7), mirrorando `_governance_render`/`_render_wiki`/`_render_rag` di
`test_assets_copilot_parity.py`.

- [ ] Crea `packages/sertor/tests/test_model_policy_guard.py`:
      ```python
      """Real-asset + coherence guard for the model-policy profile (E2-FEAT-015).

      Builds the THREE real install plans (rag/concierge, wiki/wiki-curator, governance/
      {requirements-analyst,configuration-manager,requirements}) for `AssistantId.COPILOT_CLI` and
      renders each `.agent.md` via the plan's OWN render function (no filesystem writes, no
      `specify`/`CommandRunner` mocking needed — mirrors `test_assets_copilot_parity.py`'s pattern).
      Asserts:
        - each of the 5 rendered `.agent.md` carries `model:` == the policy value for that agent,
          never a bare Claude alias (contract C3, R10/R11);
        - `IN_SCOPE_AGENTS` == exactly the 5 names the three plans deposit (contract C5, R15);
        - a synthetic incomplete profile makes each plan-BUILDER raise `ModelPolicyError` naming
          the missing agent, BEFORE any artifact is written (contract C3, R12).

      Offline (RNF-7): `tmp_path` only, no network, no subprocess.
      """
      from __future__ import annotations

      from pathlib import Path

      import pytest

      from sertor_install_kit.assistant import AssistantId
      from sertor_install_kit.errors import ModelPolicyError
      from sertor_install_kit.model_policy import IN_SCOPE_AGENTS, resolve_model
      from sertor_installer.install_rag import _render_rag_file, build_rag_plan
      from sertor_installer.install_wiki import _render_for_target as _wiki_render
      from sertor_installer.install_wiki import build_install_plan
      from sertor_installer.rag_profile import RagHostProfile, RagInstallOptions
      from sertor_installer.surfaces import split_frontmatter


      def _model_value(front: str) -> str | None:
          for line in front.splitlines():
              if line.strip().startswith("model:"):
                  return line.split(":", 1)[1].strip()
          return None


      def _rag_plan(tmp_path: Path):
          options = RagInstallOptions(target_root=tmp_path, backend="azure", with_deps=False)
          profile = RagHostProfile.from_options(options)
          return build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)


      def _governance_plan(tmp_path: Path):
          # Lazy import: sertor-flow is a sibling package (no runtime dependency from sertor),
          # mirrors test_assets_copilot_parity.py's `_governance_plan`.
          from sertor_flow.install_governance import build_governance_plan
          from sertor_flow.profile import build_governance_profile

          profile = build_governance_profile(tmp_path, assistant="copilot-cli")
          return build_governance_plan(profile)


      def _rendered_agent_frontmatters(tmp_path: Path) -> dict[str, str]:
          """(agent_name -> rendered frontmatter) for the 5 `.agent.md` targets, via each plan's
          own render function — no filesystem writes."""
          from sertor_flow.install_governance import _render_for_target as _gov_render

          out: dict[str, str] = {}
          for art in _rag_plan(tmp_path / "rag"):
              if art.target_rel.endswith(".agent.md"):
                  name = art.target_rel.rsplit("/", 1)[-1].removesuffix(".agent.md")
                  out[name] = split_frontmatter(_render_rag_file(art))[0]
          for art in build_install_plan(AssistantId.COPILOT_CLI):
              if art.target_rel.endswith(".agent.md"):
                  name = art.target_rel.rsplit("/", 1)[-1].removesuffix(".agent.md")
                  out[name] = split_frontmatter(_wiki_render(art))[0]
          for art in _governance_plan(tmp_path / "gov"):
              if art.target_rel.endswith(".agent.md"):
                  name = art.target_rel.rsplit("/", 1)[-1].removesuffix(".agent.md")
                  out[name] = split_frontmatter(_gov_render(art))[0]
          return out


      # --- C3/R10/R11: all 5 rendered .agent.md carry the policy model, never a bare alias -------


      def test_all_five_agents_get_explicit_policy_model(tmp_path: Path):
          frontmatters = _rendered_agent_frontmatters(tmp_path)
          assert set(frontmatters) == IN_SCOPE_AGENTS, (
              f"rendered agents {sorted(frontmatters)} != IN_SCOPE_AGENTS {sorted(IN_SCOPE_AGENTS)}"
          )
          for name, front in frontmatters.items():
              value = _model_value(front)
              assert value == resolve_model(name), (
                  f"{name}: model {value!r} != policy {resolve_model(name)!r}"
              )
              assert value not in {"haiku", "sonnet", "opus"}, (
                  f"{name}: bare Claude alias leaked: {value!r}"
              )


      # --- C5/R15: IN_SCOPE_AGENTS coincides exactly with the deposited agent set ----------------


      def test_in_scope_agents_matches_deposited_agents(tmp_path: Path):
          frontmatters = _rendered_agent_frontmatters(tmp_path)
          assert set(frontmatters) == IN_SCOPE_AGENTS


      def test_policy_pins_five_model_ids():
          """Pin (regression on accidental edits)."""
          assert resolve_model("concierge") == "claude-haiku-4.5"
          assert resolve_model("configuration-manager") == "claude-haiku-4.5"
          assert resolve_model("requirements-analyst") == "claude-sonnet-4.6"
          assert resolve_model("requirements") == "claude-sonnet-4.6"
          assert resolve_model("wiki-curator") == "claude-sonnet-4.6"


      # --- C3/R12: fail-loud on an incomplete profile, BEFORE any artifact is written ------------


      def test_incomplete_profile_fails_rag_plan_naming_concierge(tmp_path: Path, monkeypatch):
          import sertor_install_kit.model_policy as mp

          monkeypatch.delitem(mp._MODEL_POLICY, "concierge")
          with pytest.raises(ModelPolicyError, match="concierge"):
              _rag_plan(tmp_path)


      def test_incomplete_profile_fails_wiki_plan_naming_wiki_curator(monkeypatch):
          import sertor_install_kit.model_policy as mp

          monkeypatch.delitem(mp._MODEL_POLICY, "wiki-curator")
          with pytest.raises(ModelPolicyError, match="wiki-curator"):
              build_install_plan(AssistantId.COPILOT_CLI)


      def test_incomplete_profile_fails_governance_plan_naming_agent(tmp_path: Path, monkeypatch):
          import sertor_install_kit.model_policy as mp
          from sertor_flow.install_governance import build_governance_plan
          from sertor_flow.profile import build_governance_profile

          monkeypatch.delitem(mp._MODEL_POLICY, "requirements-analyst")
          profile = build_governance_profile(tmp_path, assistant="copilot-cli")
          with pytest.raises(ModelPolicyError, match="requirements-analyst"):
              build_governance_plan(profile)
      ```
- [ ] `uv run pytest packages/sertor/tests/test_model_policy_guard.py -v` — atteso **7 `PASSED`**
      (2 real-asset + 1 pin + 3 fail-loud + 1 coherence — nota: `test_in_scope_agents_matches_deposited_agents`
      e `test_all_five_agents_get_explicit_policy_model` condividono l'helper, sono 2 test distinti).
- [ ] Verifica offline: nessuna rete, nessun subprocess `uv`/`specify` (tutte le funzioni usate sono
      pure — `build_*_plan`/`_render_*` non eseguono I/O).
- [ ] `uv run ruff check packages/sertor/tests/test_model_policy_guard.py` — zero errori.

**Verifica di chiusura Fase 4:**

- [ ] `uv run pytest packages/sertor/tests/test_assets_copilot_guard.py packages/sertor/tests/test_schema_copilot_frontmatter.py packages/sertor/tests/test_assets_copilot_parity.py packages/sertor/tests/test_install_rag.py packages/sertor/tests/test_install_wiki_copilot_cli.py packages/sertor/tests/test_model_policy_guard.py -q`
      — tutto verde.
- [ ] `uv run pytest packages/sertor-flow/tests -q` — tutto verde.

---

## Fase 5 — US5+US7+US8 (P1 Must / P2 Should): documentazione utente (DoD) (2 task, `[P]`)

> Prerequisiti: nessuno strettamente (i contenuti di doc si basano sul design, non sul codice) — ma
> per coerenza si esegue dopo Fase 1 (i model-ID citati sono quelli reali del profilo). Può girare
> in parallelo con Fase 4 (file `.md` disgiunti dai `.py` della Fase 4).

### TASK-US5-01 [P] — `docs/install-copilot.md`: nuova sezione «Model defaults»

→ **Mappa**: FR-015/016/017/018 · CS-6 · US5/US7/US8

- [ ] Inserisci una nuova sezione in `docs/install-copilot.md`, subito dopo la sezione "## Invoking
      the agent capabilities (no slash-commands)" (dopo la riga con "no agent flag needed.") e
      prima del separatore `---`/"## Migrating from the VS Code target":
      ```markdown
      ## Model defaults for the Sertor-authored agents

      Each of the five Sertor-authored custom-agents gets an explicit **default model** at install
      time, set via the `model:` field of its `.agent.md` frontmatter (a versioned profile shared
      by `sertor` and `sertor-flow` — see
      [`packages/sertor/docs/install.md`](../packages/sertor/docs/install.md)):

      | Agent | Package | Default model | Rationale |
      |---|---|---|---|
      | `concierge` | `sertor` | `claude-haiku-4.5` | thin dispatcher — mechanical task, economical/fast |
      | `wiki-curator` | `sertor` | `claude-sonnet-4.6` | synthesis/curation — capable |
      | `requirements-analyst` | `sertor-flow` | `claude-sonnet-4.6` | requirements analysis/writing — capable |
      | `configuration-manager` | `sertor-flow` | `claude-haiku-4.5` | git operations from a brief — mechanical, economical/fast |
      | `requirements` | `sertor-flow` | `claude-sonnet-4.6` | EARS elicitation/writing — capable |

      **It's a default, not a lock-in.** Change it any time with the CLI's `/subagents` picker
      (persists in `~/.copilot/settings.json`, a file Sertor never touches — the override wins at
      runtime and survives a Sertor upgrade), or by editing the `model:` line in the `.agent.md`
      frontmatter directly (a manual edit is subject to the normal owned-file re-render on the next
      `upgrade`, like the rest of the frontmatter).

      **Out of scope:** the `speckit.*` prompt-files (`speckit.specify`/`clarify`/`plan`/... vendored
      by `specify init`) do **not** receive a model default from this mechanism — GitHub's docs do
      not confirm prompt-file support for `model:` (tracked as a follow-up,
      [`FEAT-016`](../requirements/sertor-cli/epic.md) in the `sertor-cli` backlog).

      **No tenant probe.** The install is fully offline: it never checks whether a model-ID is
      enabled in your Copilot plan/tenant. If a default isn't available to you, Copilot will
      surface that at runtime when you invoke the agent — not at install time.
      ```
- [ ] Verifica manuale: la sezione compare tra "Invoking..." e "Migrating..."; nessun link rotto
      (verificare che `../requirements/sertor-cli/epic.md` risolva dalla posizione di
      `docs/install-copilot.md`).

### TASK-US5-02 [P] — `packages/sertor/docs/install.md`: riga nella tabella "Operability / notes"

→ **Mappa**: FR-015 · CS-6 · US5

- [ ] Aggiungi una riga alla tabella "### Operability / notes (per surface)" (dopo la riga
      `memory-capture (Copilot CLI)`):
      ```markdown
      | Sertor-authored agent `model:` default (Copilot CLI) | Each of the 5 Sertor-authored `.agent.md` custom-agents gets an explicit default model from a versioned profile (`sertor-install-kit`); user-overridable via `/subagents` or by editing the frontmatter. Install is offline — no probe of tenant model availability. See [`docs/install-copilot.md`](../../docs/install-copilot.md#model-defaults-for-the-sertor-authored-agents). |
      ```
- [ ] Verifica manuale: il link relativo `../../docs/install-copilot.md#model-defaults-for-the-sertor-authored-agents`
      risolve dalla posizione di `packages/sertor/docs/install.md` (coerente con gli altri link
      relativi già presenti nello stesso file, es. la riga `memory-capture`).

**Verifica di chiusura Fase 5:**

- [ ] Rileggi entrambi i file per assicurarti che non contraddicano la costituzione del confine
      D↔N (nessuna promessa di probe install-time, nessuna promessa di supporto `speckit.*`).

---

## Fase 6 — Polish e cross-cutting (2 task)

> Prerequisiti: Fase 2, Fase 3, Fase 4, Fase 5 tutte complete. Sequenziale: TASK-P01 → TASK-P02.

### TASK-P01 — Suite completa (kit + sertor + sertor-flow + root) + lint ruff

→ dipende da: tutte le fasi precedenti

- [ ] Suite kit:
      ```powershell
      uv run pytest packages/sertor-install-kit/tests -q
      ```
- [ ] Suite `sertor` (esclusi cloud):
      ```powershell
      uv run pytest packages/sertor/tests -m "not cloud" -q
      ```
- [ ] Suite `sertor-flow`:
      ```powershell
      uv run pytest packages/sertor-flow/tests -q
      ```
- [ ] Suite root (esclusi cloud) — invariata per costruzione (`sertor_core` non toccato):
      ```powershell
      uv run pytest -m "not cloud" -q
      ```
      Zero nuovi fallimenti rispetto alla baseline di TASK-S01.
- [ ] Lint ruff su tutti i file toccati/creati:
      ```powershell
      uv run ruff check `
          packages/sertor-install-kit/src/sertor_install_kit/model_policy.py `
          packages/sertor-install-kit/src/sertor_install_kit/errors.py `
          packages/sertor-install-kit/src/sertor_install_kit/surfaces.py `
          packages/sertor-install-kit/src/sertor_install_kit/__init__.py `
          packages/sertor-install-kit/tests/unit/test_model_policy.py `
          packages/sertor-install-kit/tests/unit/test_surfaces_agent_model.py `
          packages/sertor/src/sertor_installer/install_rag.py `
          packages/sertor/src/sertor_installer/install_wiki.py `
          packages/sertor-flow/src/sertor_flow/install_governance.py `
          packages/sertor/tests/test_assets_copilot_guard.py `
          packages/sertor/tests/test_schema_copilot_frontmatter.py `
          packages/sertor/tests/test_assets_copilot_parity.py `
          packages/sertor/tests/test_install_rag.py `
          packages/sertor/tests/test_install_wiki_copilot_cli.py `
          packages/sertor/tests/test_model_policy_guard.py `
          packages/sertor-flow/tests/test_install_governance_copilot.py
      ```
      Zero errori (regole E,F,I,UP,B; line-length 100).
- [ ] Verifica che `sertor_core` sia byte-per-byte invariato:
      ```powershell
      git diff --name-only -- src/sertor_core
      ```
      Output vuoto atteso.

### TASK-P02 — Verifica CS-1..7, quickstart e chiusura trasversale

→ dipende da: TASK-P01

- [ ] **CS-1 (default esplicito):** `test_all_five_agents_get_explicit_policy_model` verde — i 5
      agenti hanno `model:` non-vuoto pari alla policy. ✓
- [ ] **CS-2 (no leak alias Claude):** `test_r8_no_bare_claude_alias_leak_even_though_id_contains_substring`
      + `test_concierge_copilot_frontmatter_no_claude_names` + `test_copilot_bodies_have_no_claude_product_names`
      verdi — 0 alias Claude nudo, nessuna regressione FEAT-011/049. ✓
- [ ] **CS-3 (fonte unica versionata):** `test_r1_exactly_five_agents_in_scope` +
      `test_in_scope_agents_matches_deposited_agents` verdi; 0 model-ID letterali nei 3 call-site
      (grep di conferma):
      ```powershell
      Select-String -Path packages/sertor/src/sertor_installer/install_rag.py,packages/sertor/src/sertor_installer/install_wiki.py,packages/sertor-flow/src/sertor_flow/install_governance.py -Pattern "claude-(haiku|sonnet)-4\.\d"
      ```
      Nessun match atteso (gli ID vivono **solo** in `model_policy.py`). ✓
- [ ] **CS-4 (idempotenza):** `test_concierge_upgrade_copilot_render_aware` verde (stale `model:
      sonnet` → sostituito dalla policy, non doppia scrittura). ✓
- [ ] **CS-5 (fail-loud):** i 3 test `test_incomplete_profile_fails_*_naming_*` verdi — profilo
      incompleto → `ModelPolicyError` nominante, **prima** di ogni scrittura (nessun `execute_plan`
      raggiunto). ✓
- [ ] **CS-6 (DoD distribuzione + doc):** rileggi `docs/install-copilot.md` (sezione "Model defaults")
      e `packages/sertor/docs/install.md` (riga "Operability / notes") — presenti, coerenti. ✓
- [ ] **CS-7 (zero impatto Claude):** rilancia i test Claude-path invariati:
      ```powershell
      uv run pytest packages/sertor/tests/test_install_rag.py::test_concierge_agent_deposited_claude `
                    packages/sertor/tests/test_install_rag.py::test_concierge_model_pin_in_frontmatter_only `
                    packages/sertor-flow/tests/test_install_governance_copilot.py::test_constitution_identical_to_claude -v
      ```
      Tutti `PASSED` — `model: sonnet` di `concierge` e i frontmatter Claude restano bit-per-bit
      invariati. ✓
- [ ] Esegui il quickstart per intero ([`quickstart.md`](quickstart.md) §1-2):
      ```powershell
      uv run pytest packages/sertor/tests/test_assets_copilot_guard.py `
                    packages/sertor/tests/test_schema_copilot_frontmatter.py `
                    packages/sertor/tests/test_assets_copilot_parity.py `
                    packages/sertor-flow/tests `
                    packages/sertor-install-kit/tests -q
      uv run python -c "from sertor_install_kit.model_policy import resolve_model, IN_SCOPE_AGENTS; print({a: resolve_model(a) for a in sorted(IN_SCOPE_AGENTS)})"
      ```
- [ ] Segnala i follow-up già a casa durevole (non-bloccanti, non da riaprire qui):
      - `FEAT-016` (backlog `sertor-cli`, già presente in `requirements/sertor-cli/epic.md`):
        model-policy per gli agenti `speckit.*` — bloccata da una spike sul supporto `model:` nei
        prompt-file Copilot. **Già promossa** (nessuna azione qui).
      - Nessun altro Out-of-Scope reale rimasto sepolto in `specs/083-default-model-policy-copilot/`.

---

## Grafo delle dipendenze (sintesi)

```
TASK-S01  (pre-flight)
    │
    ├── TASK-F01  [P]  (ModelPolicyError — errors.py)
    ├── TASK-F02  [P]  (render_custom_agent firma — surfaces.py)
    │       │
    │  TASK-F01 → TASK-F03  (model_policy.py, importa ModelPolicyError)
    │       │
    │  {F01,F02,F03} → TASK-F04  (re-export __init__.py)
    │       │
    │  TASK-F03 → TASK-F05  [P]  (kit test C1)
    │  TASK-F02 → TASK-F06  [P]  (kit test C2)
    │
    └── Fase 1 completa (F01..F06)
            │
            ├── TASK-US1-01  [P]  (install_rag.py: concierge)         ─┐
            ├── TASK-US1-02  [P]  (install_wiki.py: wiki-curator)      ├─ Fase 2 ‖ Fase 3
            └── TASK-US1-03       (install_governance.py: 3 agenti)   ─┘
                    │
                    ├── TASK-US4-01  [P]  (guard.py riconciliato)
                    ├── TASK-US4-02  [P]  (frontmatter.py riconciliato)
                    ├── TASK-US4-03  [P]  (_render_rag allineato)
                    ├── TASK-US4-04  [P]  (test_install_rag.py riconciliato — dipende da US1-01)
                    ├── TASK-US4-05  [P]  (test_install_wiki_copilot_cli.py — dipende da US1-02)
                    ├── TASK-US4-06  [P]  (test_install_governance_copilot.py — dipende da US1-03)
                    │
                    └── {US4-01..06} → TASK-US4-07  (guardia cross-pacchetto nuova)
                            │
                    TASK-US5-01 [P] ‖ TASK-US5-02 [P]  (doc, parallelo a Fase 4)
                            │
                    TASK-P01  (suite completa + lint)
                            │
                    TASK-P02  (CS-1..7 + quickstart + chiusura)
```

---

## Criteri di test indipendenti per User Story

| US | Criterio di test indipendente | Task principale | Natura |
|----|-------------------------------|------------------|--------|
| **US1** (default esplicito per-agente, P1) | `test_all_five_agents_get_explicit_policy_model` verde: i 5 `.agent.md` resi hanno ciascuno `model:` == `resolve_model(name)`. | TASK-US4-07 | MECCANICO/OFFLINE |
| **US2** (fail-loud su profilo incompleto, P1) | I 3 `test_incomplete_profile_fails_*_naming_*` verdi: un profilo con una voce mancante fa sollevare `ModelPolicyError` nominante dal **build** del piano, prima di ogni scrittura. | TASK-US4-07 | MECCANICO/OFFLINE |
| **US3** (fonte unica condivisa, P1) | `test_r1_exactly_five_agents_in_scope` + `test_in_scope_agents_matches_deposited_agents` verdi; grep di conferma 0 ID letterali nei 3 call-site. | TASK-F05 + TASK-US4-07 + TASK-P02 | MECCANICO/OFFLINE |
| **US4** (zero impatto Claude + no leak Copilot, P1) | `test_r8_no_bare_claude_alias_leak_even_though_id_contains_substring` + `test_concierge_copilot_frontmatter_no_claude_names` + `test_copilot_bodies_have_no_claude_product_names` verdi; test Claude-path (`test_concierge_agent_deposited_claude` ecc.) invariati. | TASK-F06 + TASK-US4-01..07 + TASK-P02 | MECCANICO/OFFLINE |
| **US5** (DoD distribuzione + doc, P1) | I 5 agenti ricevono la policy via `sertor install rag`/`sertor-flow install` senza passi manuali (verificato dai test reali delle Fasi 2/3); `docs/install-copilot.md` + `packages/sertor/docs/install.md` aggiornati (TASK-US5-01/02). | TASK-US1-01..03 + TASK-US5-01/02 | MISTO (codice + doc) |
| **US6** (idempotenza/lifecycle, P1) | `test_concierge_upgrade_copilot_render_aware` verde: un frontmatter stale (`model: sonnet`) viene ri-renderizzato con la policy, non duplicato. | TASK-US4-04 | MECCANICO/OFFLINE |
| **US7** (default modificabile, override sicuro, P2) | Sezione "Model defaults" di `docs/install-copilot.md` dichiara l'override via `/subagents`/edit frontmatter e la sua sicurezza per costruzione (file separato `~/.copilot/settings.json`). | TASK-US5-01 | DOC |
| **US8** (confine `speckit.*` + onestà tenant, P2) | Sezione "Model defaults" dichiara il confine `speckit.*` (→ `FEAT-016`, già in backlog) e l'assenza di probe install-time; nessun `model:` iniettato nei prompt-file `speckit.*` (invariato per costruzione, nessun call-site li tocca). | TASK-US5-01 | DOC (+ MECCANICO by-construction) |

---

## Parallelizzazione consigliata

```
Passo 1:  TASK-S01  (pre-flight, venv, baseline)

Passo 2:  TASK-F01 ‖ TASK-F02  (errors.py, surfaces.py — indipendenti)
Passo 3:  TASK-F03  (model_policy.py — dipende da F01)
Passo 4:  TASK-F04  (re-export — dipende da F01+F02+F03)
Passo 5:  TASK-F05 ‖ TASK-F06  (kit unit test — indipendenti tra loro)

Passo 6:  TASK-US1-01 ‖ TASK-US1-02 ‖ TASK-US1-03
          └── sertor: install_rag.py (concierge)
          └── sertor: install_wiki.py (wiki-curator)
          └── sertor-flow: install_governance.py (3 agenti)

Passo 7:  TASK-US4-01 ‖ TASK-US4-02 ‖ TASK-US4-03 ‖ TASK-US4-04 ‖ TASK-US4-05 ‖ TASK-US4-06
          (6 file di test riconciliati, tutti indipendenti tra loro)
          ‖ TASK-US5-01 ‖ TASK-US5-02  (doc, indipendenti dal Passo 7 di test)

Passo 8:  TASK-US4-07  (guardia cross-pacchetto — richiede tutto il Passo 6 + coerente col Passo 7)

Passo 9:  TASK-P01  (suite completa + lint)
Passo 10: TASK-P02  (CS-1..7 + quickstart + chiusura)
```

**Costo stimato (passo critico):** il Passo 6 (3 call-site) e il Passo 7 (6 riconciliazioni + 2 doc)
sono i blocchi più larghi ma pienamente paralleli al loro interno; la catena sequenziale minima è
`S01 → F01 → F03 → F04 → US1-0x → US4-07 → P01 → P02` (7 passi in serie, il resto assorbito dal
parallelismo).

---

## Brief di commit (per il `configuration-manager`)

```
docs(tasks): genera tasks.md per E2-FEAT-015 — default model-policy Copilot CLI

Fase SpecKit "tasks" completata per specs/083-default-model-policy-copilot.
21 task in 7 fasi:
  Fase 0 Setup (1 task):
    TASK-S01  uv sync --all-packages --extra dev; baseline verde; verifica file coinvolti.
  Fase 1 Foundational — kit sertor-install-kit, blocca tutto (6 task):
    TASK-F01  ModelPolicyError(InstallerError) in errors.py
    TASK-F02  render_custom_agent: include_model:bool -> model:str|None (sostituzione, mai eco)
    TASK-F03  model_policy.py: MODEL_POLICY_VERSION + _MODEL_POLICY (5 voci) + IN_SCOPE_AGENTS
              + resolve_model() fail-loud
    TASK-F04  re-export in __init__.py
    TASK-F05  test_model_policy.py (contratto C1, 7 test)
    TASK-F06  test_surfaces_agent_model.py (contratto C2, 5 test)
  Fase 2/3 US1+US2+US6 P1 Must — applicazione policy [P tra loro] (3 task):
    TASK-US1-01  install_rag.py: _render_rag_file + fail-loud in build_rag_plan (concierge)
    TASK-US1-02  install_wiki.py: _render_for_target + fail-loud in _build_copilot_wiki_plan
                 (wiki-curator)
    TASK-US1-03  install_governance.py: _render_for_target + fail-loud in build_governance_plan
                 (requirements-analyst/configuration-manager/requirements, validazione PRIMA
                 dell'intero loop — unico piano con 3 agenti)
  Fase 4 US3+US4 P1 Must — riconciliazione guardie + nuova guardia (7 task):
    TASK-US4-01  test_assets_copilot_guard.py: + test additivo sostituzione policy
    TASK-US4-02  test_schema_copilot_frontmatter.py: fix kwarg include_model rimosso (TypeError)
    TASK-US4-03  test_assets_copilot_parity.py: _render_rag allineato al render reale
    TASK-US4-04  test_install_rag.py: 3 test concierge riconciliati (scoperti in fase tasks,
                 non enumerati in data-model.md — vedi nota di apertura)
    TASK-US4-05  test_install_wiki_copilot_cli.py: 1 test wiki-curator riconciliato (scoperto)
    TASK-US4-06  test_install_governance_copilot.py: 1 test requirements riconciliato (scoperto)
    TASK-US4-07  NUOVO test_model_policy_guard.py (sertor): real-asset (5 agenti) + coerenza
                 IN_SCOPE_AGENTS + fail-loud sui 3 plan-builder (profilo sintetico incompleto)
  Fase 5 US5+US7+US8 — documentazione utente, stesso step [P] (2 task):
    TASK-US5-01  docs/install-copilot.md: sezione "Model defaults" (tabella 5 agenti, override,
                 confine speckit.*, no probe tenant)
    TASK-US5-02  packages/sertor/docs/install.md: riga in "Operability / notes"
  Fase 6 Polish (2 task, sequenziali):
    TASK-P01  Suite kit+sertor+sertor-flow+root verdi, lint ruff, sertor_core invariato
    TASK-P02  CS-1..7 + quickstart + grep 0 ID letterali + follow-up FEAT-016 già a casa

Natura: ADDITIVA / distribuzione-installer, ZERO runtime sertor_core (Principio XI).
Nuovo modulo kit: sertor_install_kit/model_policy.py (fonte unica versionata).
Nuovo errore kit: ModelPolicyError(InstallerError).
Firma cambiata (kit): render_custom_agent(include_model:bool) -> render_custom_agent(model:str|None).
3 call-site modificati: install_rag.py, install_wiki.py, install_governance.py.
9 file di test toccati/creati (3 nuovi: test_model_policy.py, test_surfaces_agent_model.py,
test_model_policy_guard.py; 6 riconciliati).
2 file di documentazione utente aggiornati nello stesso step (DoD).
Copertura: FR-001..018, RNF-1..8, CS-1..7, US1..8.
Constitution CHECK: PASS 12/12 + missione (pre e post-design, plan.md §Constitution Check).
Nessuno script/hook SpecKit eseguito (setup-tasks.ps1/skill assenti); nessuna operazione git.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
```

**File da includere nel commit:**
- `specs/083-default-model-policy-copilot/tasks.md` (questo file, nuovo)
