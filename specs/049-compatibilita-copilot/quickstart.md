# Quickstart — Verifica della compatibilità Copilot (FEAT-011)

Guida operativa per validare, **offline**, che gli asset Copilot generati dall'installer siano conformi
allo schema nativo. Tutto gira senza un client Copilot reale (NFR-5 / SC-007). Comandi PowerShell.

---

## 0. Prerequisiti
```powershell
# dal workspace root
uv sync --extra dev
```

## 1. Suite di validità-schema Copilot (gruppo G)
```powershell
# suite mirata della feature (i nomi esatti dei file di test sono fissati in /speckit-tasks)
uv run pytest packages/sertor/tests -k copilot
uv run pytest packages/sertor-flow/tests -k copilot
```
Asserzioni attese (contracts/):
- hook JSON: `version:1`, struttura piatta, `timeoutSec`, niente `shell`/`statusMessage` (copilot-hook-schema.md).
- output script per evento: `additionalContext`/`decision:allow`/no-stdout/fail-open; mai dual-field (hook-output-contract.md).
- frontmatter: prompt-file `agent:`, custom-agent senza `model:` (copilot-frontmatter.md).
- veicolo COMMAND su `copilot-cli` = custom-agent, mai solo-prompt-file (copilot-frontmatter.md §3).

## 2. Reintroduzione difetti (test di regressione dell'audit, SC-007)
Verifica manuale che la rete prenda i bug: reintroduci artificialmente un difetto e attendi un fail.
```powershell
# esempio: rimuovere "version" da un hook generato → almeno un test fallisce
# (da fare in un branch sporco, mai committato)
uv run pytest packages/sertor/tests -k "copilot and hook"
```

## 3. Installazione simulata per target (acceptance offline)
```powershell
# wiki su Copilot CLI (host simulato in una cartella temporanea)
uv run python -c "from pathlib import Path; from sertor_install_kit.assistant import AssistantId; from sertor_installer.config_gen import build_host_profile; from sertor_installer.install_wiki import build_install_plan, execute_plan; t=Path('.tmp-host'); t.mkdir(exist_ok=True); p=build_host_profile(t); r=execute_plan(build_install_plan(AssistantId.COPILOT_CLI), p, AssistantId.COPILOT_CLI); print(r.render_json())"
```
Atteso (copilot-cli): comandi wiki come `.github/agents/*.agent.md` (NON solo prompt-file); hook wiring
`.github/hooks/sertor-hooks.json` con `version:1`.

## 4. Non-regressione Claude (gate duro, SC-010)
```powershell
uv run pytest -m "not cloud" packages/sertor packages/sertor-flow packages/sertor-install-kit
```
Atteso: tutta la suite Claude esistente resta verde; il comportamento del target `claude` è invariato.

## 5. Verifica empirica runtime (FUORI AMBITO di prodotto — promemoria operativo)
La conferma su client reale (Copilot CLI e soprattutto **VS Code** per [ASSUNTO-VSC]) è validazione
operativa: NON è coperta dalla suite. Quando eseguita, aggiornare la surface-mapping
(contracts/surface-mapping-and-gaps.md §2) con l'esito.
