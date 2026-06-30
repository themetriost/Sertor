# Contract — Substring load-bearing da preservare (pin semantici)

Pin per la guardia `test_semantic_pins` (FR-012/CS-5): ogni substring **deve restare presente** nel
file dopo la pulizia (la formulazione cambia, la regola no). Sono substring **stabili** (non
toccati dalla normalizzazione ALL-CAPS): scelte per non rompersi quando un maiuscolo diventa minuscolo.

## A1 — guided-setup/SKILL.md
| Pin (substring) | Regola load-bearing che ancora |
|---|---|
| `import the core` | no-import-core (Hard boundary) |
| `build_*` | non chiamare le factory |
| `through a vehicle` | vehicle-only |
| `--assistant` | `--assistant <host>` obbligatorio |
| `explicit confirmation` | consent gate sulle mutazioni |
| `configure --set` | mai hand-edit di `.sertor/.env` |
| `never print` | segreti mai a schermo |
| `green` | doctor verde prima di «done» |
| `propose` | provider proposto, mai auto-selezionato |

> Mapping rimozione «What NOT to do» (A1) — ogni item ha una casa inline (A-001):
> secret-print→Step 4; hand-fill→Step 4; mutation-without-confirm→Consent gate; import-core→Hard
> boundary; auto-provider→Step 2; declare-done→Step 6; install-without-`--assistant`→Hard boundary.

## A2 — eval-suite-author/SKILL.md
| Pin | Regola |
|---|---|
| `import the core` | no-import-core |
| `eval add-case` | scrittura solo via vehicle |
| `approval` | solo casi approvati |
| `validate-path` | path verificati, mai inventati |
| `graph-eval` | navigazione via subcomandi vehicle |
| `secrets` | mai segreti nella suite |
| `sertor-cli-reference.md` | pointer «How to invoke» |

## A3 — eval-feedback/SKILL.md
| Pin | Regola |
|---|---|
| `core library` | no-import-core |
| `eval add-case` | scrittura solo via vehicle |
| `explicit` | nessun verdetto inferito/auto |
| `automatic mode` | nessuna modalità automatica |
| `secrets` | mai segreti nella suite (folded in Hard boundary) |
| `sertor-cli-reference.md` | pointer «How to invoke» |

## A4 — wiki-author/wiki-playbook.md
| Pin | Regola |
|---|---|
| `wiki.config.toml` | host-specifics in config |
| `sertor-wiki-tools` | CLI deterministica |
| `append-log` | write-back log via CLI |
| `parity guard` | regole host-agnostic enforced |
| `## Contents` | ToC presente |

## A5 — requirements/SKILL.md (sertor-flow)
| Pin | Regola |
|---|---|
| `EARS` | notazione requisiti |
| `MoSCoW` | prioritizzazione |
| `requirements/<epica>/epic.md` | artefatto livello epica |
| `Considera sempre l'input dell'utente` | input utente (post `SEMPRE`→`sempre`) |
