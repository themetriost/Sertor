# Contratto — Comportamento della guardia `pwsh` (install-time)

Modulo `sertor_install_kit.host_env` (NUOVO, puro stdlib). Definisce la **condizione binaria** e gli
invarianti della guardia. **Zero** import di `sertor_core`, nessun LLM (Principio XI/RNF-2).

## Tabella di verità (emissione della Nota A — indisponibilità `pwsh`)

| OS | `pwsh` in PATH | hook depositati nel piano | → Nota A emessa? | US / FR |
|---|---|---|---|---|
| non-Windows | assente | sì | **SÌ** | US1/US4 · FR-002/003/005 |
| non-Windows | presente | sì | **NO** | US2 · FR-004 |
| Windows | — (irrilevante) | sì | **NO** | US3 · FR-006 |
| qualsiasi | — | nessuno | **NO** (no-op) | edge: nessun hook da segnalare |

> La guardia **non** distingue assistente per la Nota A (vale per claude e copilot-cli su non-Windows).
> La distinzione di operatività per-assistente (es. Claude `shell:powershell` su non-Windows) è
> dichiarata nei **doc utente** (FR-010/012), non nella nota — la nota è narrow su «`pwsh` non trovato»
> (research D-3).

## Invarianti

| Inv | Garanzia | Riferimento |
|---|---|---|
| INV-1 | **Non-fatale:** la guardia non solleva mai; non altera `exit_code()`. | FR-005 · NFR-3 |
| INV-2 | **Non-bloccante:** tutti i surface non-hook installati a prescindere da `pwsh`. | FR-005 |
| INV-3 | **Nessun cambio di wiring:** né `"shell": "powershell"` (Claude) né `pwsh -File` (Copilot) modificati. | research D-3 · NFR-5 |
| INV-4 | **Binario, host-agnostico:** `shutil.which("pwsh")`; nessun test di versione, nessun hardcoding di distro. | NFR-4 · R-1 |
| INV-5 | **Niente falso positivo su Windows:** gating `not is_windows()`. | R-2 · CS-3 |
| INV-6 | **Costo trascurabile:** singola ricerca dell'eseguibile nel PATH. | NFR-3 |
| INV-7 | **Determinismo in CI:** i test simulano l'OS (patch di `host_env.is_windows`/`pwsh_available`), non dipendono dall'OS reale (CI Windows). | R-6 · FR-013 |

## Superficie pubblica (kit)

```
host_env.is_windows() -> bool
host_env.pwsh_available() -> bool
host_env.pwsh_unavailability_note(hook_surfaces: Sequence[str]) -> str
host_env.maybe_note_pwsh(report: InstallReport, hook_surfaces: Sequence[str]) -> None
host_env.PWSH_INSTALL_URL: str
```

`maybe_note_pwsh` è l'unico entry-point chiamato dai consumatori; gli altri sono esposti per test
unitari diretti (builder puro) e per riuso futuro (`sertor-flow`).
