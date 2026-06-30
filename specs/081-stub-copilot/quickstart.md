# Quickstart — Rimozione stub `assets/copilot/` (E10-FEAT-023)

**Branch**: `081-stub-copilot` · **Spec**: [spec.md](./spec.md) · **Plan**: [plan.md](./plan.md)

Sequenza operativa per implementare e verificare la feature (sottrattiva, igiene host-facing). Comandi
**PowerShell** (Windows). Git delegato al `configuration-manager` — qui i comandi servono solo a
descrivere l'intento.

---

## 1. Riconferma zero-consumatori (FR-005)

Ripetere la verifica prima di rimuovere (un consumatore introdotto dopo la spec va corretto prima):

```powershell
# nessun output atteso (zero letture rooted a copilot/)
Select-String -Path packages\sertor\src\**\*.py, packages\sertor\tests\**\*.py `
  -Pattern 'read_asset_text\("copilot|iter_asset_dir\("copilot|asset_path\("copilot'
```

Atteso: nessuna riga (l'unica occorrenza di `copilot/instructions` è un commento di documentazione in
`test_assets_copilot_guard.py`, non una lettura).

## 2. Rimuovere il tree stub (FR-001/002)

```powershell
git rm packages/sertor/src/sertor_installer/assets/copilot/agents/.gitkeep
git rm packages/sertor/src/sertor_installer/assets/copilot/hooks/.gitkeep
git rm packages/sertor/src/sertor_installer/assets/copilot/instructions/.gitkeep
git rm packages/sertor/src/sertor_installer/assets/copilot/prompts/.gitkeep
```

Git non traccia directory vuote → rimosso l'ultimo file, le 4 dir e `copilot/` scompaiono dal tree.
**Nessun file di rimpiazzo** (FR-003): non aggiungere README/marker.

## 3. Aggiungere la guardia anti-ricomparsa (FR-008, R-1)

Estendere `packages/sertor/tests/test_assets_copilot_guard.py` con `test_no_copilot_asset_directory`
(forma esatta in [contracts/guard-anti-reappearance.md](./contracts/guard-anti-reappearance.md)):

```python
def test_no_copilot_asset_directory():
    """E10-FEAT-023: no static Copilot asset tree — payloads are generated at runtime."""
    from sertor_installer.resources import asset_path
    assert not asset_path("copilot").is_dir()
```

Nessuna modifica ai test esistenti né a `install_rag.py` (DA-D-2 = no commento).

## 4. Verifiche di non-regressione

```powershell
# guardia nuova + guardie Copilot esistenti
uv run pytest packages/sertor/tests/test_assets_copilot_guard.py packages/sertor/tests/test_assets_copilot_parity.py

# generazione Copilot invariata
uv run pytest packages/sertor/tests/test_install_rag_copilot_cli.py

# build/packaging (FR-006): nessuna modifica a pyproject.toml
uv build -p sertor
uv run pytest -m integration tests/integration/test_packaging.py

# suite complete (zero nuovi fallimenti)
uv run pytest
uv run ruff check .
```

## Criteri «done» (dalla spec)

- `git ls-files packages/sertor/src/sertor_installer/assets/copilot/` → **zero righe** (CS-1).
- Nessun file aggiunto sotto `assets/copilot/` (FR-003).
- `uv build -p sertor` + `test_packaging.py` **verdi** (CS-2).
- Zero nuovi fallimenti di suite; `build_rag_plan(copilot-cli)` produce gli stessi artefatti (CS-3/CS-4).
- `test_no_copilot_asset_directory` **verde** allo stato corretto, **rosso** se lo stub riappare (US6).
