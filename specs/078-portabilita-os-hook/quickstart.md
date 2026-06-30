# Quickstart — Verifica E10-FEAT-018 (portabilità OS hook + onestà surface inerti)

**Branch**: `078-portabilita-os-hook` · **Data**: 2026-06-30

Verifiche **offline**, deterministiche, su host simulato (`tmp_path`) con OS mocking (la CI gira su
Windows). Nessuna rete, nessun `sertor_core` runtime, nessun LLM. Esegui dalla radice del repo.

## 0. Suite di guardia

```powershell
uv run pytest packages/sertor-install-kit/tests/unit/test_host_env.py     # builder/gating puri
uv run pytest packages/sertor/tests/ -k "pwsh or memory_note or gap_note"  # note su install rag/wiki
uv run pytest tests/unit/test_assets_sync.py                              # sync dogfood↔bundle (verde)
uv run ruff check .
```

## 1. Nota `pwsh` su non-Windows senza `pwsh` (US1/US4 — CS-1)

Simula host non-Windows senza `pwsh`; un `install rag`/`wiki` che deposita hook produce la Nota A.

```python
import sertor_install_kit.host_env as host_env
monkeypatch.setattr(host_env, "is_windows", lambda: False)
monkeypatch.setattr(host_env, "pwsh_available", lambda: False)
report = execute_rag_plan(plan, profile, FakeRunner(), AssistantId.CLAUDE)
assert any("pwsh" in n for n in report.notes)                        # A1
assert any("learn.microsoft.com/powershell" in n for n in report.notes)  # A2
assert any(".ps1" in n for n in report.notes)                        # A3 (surface affetti)
payload = json.loads(report.render_json())
assert any("pwsh" in n for n in payload["notes"])                    # nota anche in JSON (FR-003)
assert report.exit_code() == 0                                        # non-fatale (FR-005)
```

## 2. Nessun falso allarme con `pwsh` presente (US2 — CS-2)

```python
monkeypatch.setattr(host_env, "is_windows", lambda: False)
monkeypatch.setattr(host_env, "pwsh_available", lambda: True)
report = execute_rag_plan(plan, profile, FakeRunner(), AssistantId.CLAUDE)
assert not any("pwsh" in n.lower() and "not found" in n.lower() for n in report.notes)
```

## 3. Non-regressione Claude + Windows (US3 — CS-3)

```python
monkeypatch.setattr(host_env, "is_windows", lambda: True)   # default su CI Windows
report = execute_plan(build_install_plan(AssistantId.CLAUDE), profile, AssistantId.CLAUDE)
assert report.notes == []   # né pwsh né Copilot (test_claude_report_has_no_gap_note, esteso/preservato)
```

## 4. Nota `memory-capture` su install rag Copilot CLI (US5 — CS-4)

```python
monkeypatch.setattr(host_env, "is_windows", lambda: True)   # indipendente dall'OS e da SERTOR_MEMORY
plan = build_rag_plan(profile, with_deps=False, assistant=AssistantId.COPILOT_CLI)
report = execute_rag_plan(plan, profile, FakeRunner(), AssistantId.COPILOT_CLI)
assert any("memory-capture" in n and "SERTOR_MEMORY_ADAPTER" in n for n in report.notes)  # B1/B2
# Su Claude la nota NON c'è:
report_claude = execute_rag_plan(plan_claude, profile, FakeRunner(), AssistantId.CLAUDE)
assert not any("memory-capture" in n for n in report_claude.notes)   # FR-009
```

## 5. Documentazione utente (US6 — CS-5)

Lettura manuale:
- `docs/install.md` dichiara **`pwsh` prerequisito su macOS/Linux** per i surface hook (URL + elenco
  surface + frase «installati ma non-operativi») **e** una sezione/tabella **operatività per target**
  (Claude su Windows · Copilot CLI: pienamente operativo vs richiede config).
- `docs/install-copilot.md` dichiara, per Copilot CLI: (a) hook richiedono `pwsh` su mac/Linux; (b)
  `memory-capture` richiede config adapter esplicita (`SERTOR_MEMORY=true` + `SERTOR_MEMORY_ADAPTER`).
- `packages/sertor/docs/install.md`: la mappa capability annota operatività/note per target.

## 6. Determinismo CI (US7 — CS-6)

I test del ramo non-Windows usano `monkeypatch.setattr(host_env, ...)` (simulano l'OS), **non**
dipendono dall'OS reale → verdi sulla CI Windows. La guardia di sync `test_assets_sync.py` resta verde
(la feature non tocca alcun asset).
