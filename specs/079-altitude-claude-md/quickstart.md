# Quickstart — E10-FEAT-021 (altitude blocchi CLAUDE.md + fonte unica «How to invoke»)

Verifica end-to-end **offline** (no rete, no `uv`) che la feature è *done*. Comandi PowerShell.

## 0. Prerequisiti
```powershell
uv sync --all-packages --extra dev
```

## 1. Altitude ridotta (CS-1)
```powershell
# Le 208 righe always-on attuali scendono misurabilmente.
(Get-Content packages/sertor/src/sertor_installer/assets/claude-md-block.md).Count
(Get-Content packages/sertor/src/sertor_installer/assets/rag/claude-md-block-rag-usage.md).Count
(Get-Content packages/sertor-flow/src/sertor_flow/assets/claude-md-block-sdlc.md).Count
# Atteso: totale misurabilmente < 208 (stima ~166); SDLC invariato (65).
```

## 2. Fonte unica + nessuna copia inline nei blocchi (CS-2, REQ-012)
```powershell
# La sezione completa + Windows note esiste SOLO nel reference.
Select-String -Path packages/sertor/src/sertor_installer/assets/**/*.md -Pattern "How to invoke Sertor's commands"
Select-String -Path packages/sertor/src/sertor_installer/assets/**/*.md -Pattern "pywin32_bootstrap"
# Atteso: entrambe SOLO in rag/sertor-cli-reference.md.
```

## 3. Pointer presenti e per nome (REQ-002/014/015)
```powershell
Select-String packages/sertor/src/sertor_installer/assets/rag/claude-md-block-rag-usage.md -Pattern "sertor-cli-reference.md"
Select-String packages/sertor/src/sertor_installer/assets/claude-md-block.md -Pattern "wiki-playbook.md"
# Nessun percorso .claude/ nei body (host-agnostico):
Select-String packages/sertor/src/sertor_installer/assets/rag/sertor-cli-reference.md -Pattern "\.claude/"
# Atteso: i due pointer presenti; nessun match .claude/.
```

## 4. Guardie verdi (CS-3/CS-5/CS-6, REQ-010/011/012)
```powershell
# Parità + closure (incluso il reference), footgun + guide presence, sync dogfood.
uv run pytest packages/sertor/tests/test_assets_copilot_parity.py `
              packages/sertor/tests/test_assets_cli_invocation.py `
              tests/unit/test_assets_sync.py -q
# Non-reintroduzione SDLC (sertor-flow):
uv run pytest packages/sertor-flow/tests -k "sdlc and (invoke or block)" -q
```

## 5. Sync dogfood riallineato (CS-6)
```powershell
# Dopo l'edit del wiki-playbook (sotto assets/claude/**):
python -m sertor_installer.sync
uv run pytest tests/unit/test_assets_sync.py -q   # verde = .claude/ in byte-parità
```

## 6. Non-regressione (RNF-3)
```powershell
uv run pytest -m "not cloud" -q          # suite root
uv run pytest packages/sertor packages/sertor-install-kit packages/sertor-flow -m "not cloud" -q
uv run ruff check .
```

## 7. Closure non-rotta su install per-capacità (CS-3, REQ-007)
La closure è verificata **offline** dalle guardie (G4 nel contract): su install solo-wiki/solo-governance
nessun blocco cita il reference RAG per filename → nessun pointer morto. Il `wiki-playbook` resta
auto-contenuto (forma minima §2). Nessun host reale richiesto.

## Definition of Done
- Tre blocchi ridotti a direttiva standing + pointer; altitude totale < 208 (CS-1).
- «How to invoke» + Windows note in **un** asset (`sertor-cli-reference.md`), citato per nome (CS-2).
- Nessun pointer rotto; closure verde Claude+Copilot (CS-3).
- Contenuto load-bearing preservato (REQ-014/015/016 — C1/C2/C3 del contract) (CS-4).
- Parità host-agnostica verde (CS-5); sync dogfood verde (CS-6).
- `sertor_core` invariato; nessun nuovo `ArtifactKind`/`WriteStrategy`/seam.
