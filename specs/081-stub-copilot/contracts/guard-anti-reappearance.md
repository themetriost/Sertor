# Contratto — Guardia anti-ricomparsa dello stub `assets/copilot/`

**Feature**: E10-FEAT-023 · **Branch**: `081-stub-copilot` · **FR**: FR-008 · **Decisione**: R-1 (DA-D-1)

La feature non introduce interfacce di runtime (è sottrattiva). L'unico «contratto» nuovo è la
**guardia di test** che asserisce — e mantiene enforced — l'assenza del tree stub. Questo documento ne
fissa forma, semantica e criteri di accettazione.

---

## Collocazione

**Estensione** del file esistente
`packages/sertor/tests/test_assets_copilot_guard.py` (non un file nuovo — decisione R-1: coesione con la
famiglia di guardie Copilot, la cui docstring già documenta l'architettura generativa e il vincolo
«nessun body sotto `copilot/`»).

## Funzione

```python
def test_no_copilot_asset_directory():
    """E10-FEAT-023: no static Copilot asset tree exists under `assets/`.

    All Copilot-facing payloads are GENERATED at runtime from `assets/claude/**` and `assets/rag/**`
    via render_copilot_hooks / render_custom_agent / render_prompt_file (sertor_install_kit.surfaces).
    A `copilot/` asset directory is a MISLEADING stub (suggests static assets that do not exist); this
    guard fails loud if it reappears (e.g. a `.gitkeep` re-added "to hold the place").
    """
    from sertor_installer.resources import asset_path

    assert not asset_path("copilot").is_dir()
```

## Semantica

| Stato del repo | `asset_path("copilot").is_dir()` | Esito guardia |
|----------------|----------------------------------|---------------|
| `assets/copilot/` assente (stato corretto post-feature) | `False` | **PASS** (verde) |
| `assets/copilot/<x>/.gitkeep` ricreato (ricomparsa stub) | `True` | **FAIL** (rosso) — segnala la ricomparsa |

- `asset_path(rel)` (`sertor_installer/resources.py:18`) ritorna un `Traversable` per
  `sertor_installer/assets/<rel>`; su path inesistente `.is_dir()` è `False`. **API esistente, nessuna
  dipendenza nuova.**
- **Offline / deterministico**: nessuna rete, nessun `uv`; parità con la suite esistente (NFR-05 di
  FEAT-056, ereditata).

## Criteri di accettazione

- **AC-1.** Allo stato corretto (dir assente), la guardia **passa**. *(US6.1)*
- **AC-2.** Ricreando `assets/copilot/agents/.gitkeep` (o qualsiasi file sotto `copilot/`), la guardia
  **fallisce**. *(US6.2)*
- **AC-3.** La guardia è **additiva e leggera** (singola asserzione di assenza directory), senza
  vincoli di stack né modifiche ai test esistenti. *(US6.3, FR-008)*
- **AC-4.** Le guardie esistenti (`test_no_hand_maintained_copilot_prompt_bodies`,
  `test_assets_copilot_parity.py`) restano **invariate e verdi**. *(FR-007, CS-3)*

## Fuori dal contratto

- Una guardia **CI-enforced** oltre il test pytest (es. check di repo) → fuori ambito (R-2
  requirements; eventuale FEAT-024).
- Qualunque commento aggiuntivo in `install_rag.py` (DA-D-2): **scartato** — l'intento vive nella
  docstring di questa funzione, `install_rag.py` resta invariato.
