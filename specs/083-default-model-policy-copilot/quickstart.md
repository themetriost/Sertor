# Quickstart — verifica offline della model-policy Copilot (E2-FEAT-015)

Tutte le verifiche sono **offline** (nessuna rete, nessun tenant Copilot) — come le guardie esistenti.

## 1. Suite di test (comando singolo, PowerShell)

```powershell
uv run pytest packages/sertor/tests/test_assets_copilot_guard.py `
              packages/sertor/tests/test_schema_copilot_frontmatter.py `
              packages/sertor/tests/test_assets_copilot_parity.py `
              packages/sertor-flow/tests `
              packages/sertor-install-kit/tests -q
```

Attesi:
- i 5 `.agent.md` Copilot depositati in `tmp_path` hanno `model:` esplicito = policy (C3/R10);
- 0 alias Claude nudi nel frontmatter Copilot (C2/R8, C3/R11);
- profilo incompleto → `ModelPolicyError` nominante, 0 file scritti (C3/R12);
- frontmatter Claude byte-identici al baseline (C4/R14).

## 2. Ispezione manuale di un deposito Copilot

```powershell
uv run python -c "from sertor_install_kit.model_policy import resolve_model, IN_SCOPE_AGENTS; print({a: resolve_model(a) for a in sorted(IN_SCOPE_AGENTS)})"
```

Deve stampare i 5 default ragionati (concierge/configuration-manager → `claude-haiku-4.5`; gli altri
tre → `claude-sonnet-4.6`).

## 3. Bump di un model-ID (manutenzione)

Modificare **un solo** valore in `sertor_install_kit/model_policy.py` (+ `MODEL_POLICY_VERSION` se è un
cambio di policy) → re-run della suite. Nessuna ricerca/sostituzione sparsa (RNF-2/CS-3).

## 4. Documentazione utente (DoD)

Verificare che `docs/install-copilot.md` e la tabella capability di `packages/sertor/docs/install.md`
elenchino: default per-agente, come cambiarlo (`/subagents` o edit del frontmatter), confine `speckit.*`,
caveat disponibilità tenant (nessun probe install-time).
