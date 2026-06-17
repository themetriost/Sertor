# Quickstart — Packaging distribuibile (distribuzione interim `git+url`)

**Feature**: `047-packaging-distribuibile` | **Date**: 2026-06-17

Guida operativa per l'owner/maintainer: come è strutturato il packaging dopo questa feature, come si
**bumpa la versione**, come si **verifica** build+install, e come un installatore **ottiene Sertor** su
un ospite. Tutti i comandi sono **PowerShell** (riga singola, niente `\` di continuazione).

---

## 1. Architettura del packaging (cosa cambia)

| Prima della feature | Dopo |
|---------------------|------|
| `version = "0.1.0"` statico ×4 (disallineabili) | `version` dinamico da un unico **`/VERSION`** (allineato per costruzione) |
| nessun `LICENSE` | `LICENSE` MIT in radice + in ogni package, incluso nella wheel |
| metadati minimi (no `urls`/`classifiers`) | user-facing (`sertor`,`sertor-flow`) con `urls`/`classifiers`/`keywords` |
| nessuna prova ripetibile | suite `tests/integration/test_packaging.py` (build+install verificati) |
| `docs/install.md` senza confine PyPI | guida con i due gestori + confine PyPI esplicito |

**Due insiemi di pacchetti.**
- **Build-validati (4):** `sertor-core`, `sertor`, `sertor-install-kit`, `sertor-flow` — buildano +
  portano `LICENSE` coerente.
- **User-facing (install diretto):** `sertor`, `sertor-flow` — metadati completi. `sertor-core` e
  `sertor-install-kit` sono **dipendenze interne** risolte dal workspace (non install diretto).

---

## 2. Bump della versione (un solo file)

La versione di prodotto vive **solo** in `/VERSION` (radice repo). I 4 `pyproject.toml` la leggono via
`[tool.hatch.version]` (`dynamic = ["version"]`). Per rilasciare una nuova versione:

```powershell
# Bumpa la singola fonte di verità:
Set-Content -NoNewline -Path VERSION -Value "0.2.0"
# Verifica che i 4 pacchetti siano allineati (parte della suite di packaging):
uv run pytest tests/integration/test_packaging.py -k "version"
```

Non editare le versioni nei `pyproject.toml`: sono dinamiche. Il versioning automatico da git tag è
**fuori ambito** (FEAT-006/design).

---

## 3. Verifica di packaging (build + install ripetibili)

La verifica è una suite pytest `@integration` (lenta, tocca GitHub; **no** PyPI per i pacchetti
Sertor, **no** credenziali cloud). Tre livelli a costo crescente:

```powershell
# Tutto (statico + build + install pulito uv & pip):
uv run pytest -m integration tests/integration/test_packaging.py

# Solo coerenza statica (licenza/metadati/versione) — veloce, offline-totale:
uv run pytest tests/integration/test_packaging.py -k "metadata or license or version"

# Solo build delle wheel (LICENSE incluso, assets di sertor, entry-points):
uv run pytest tests/integration/test_packaging.py -k "build or wheel"
```

Su fallimento, il referto nomina **package + stage (+ gestore)**. La verifica **non** è nella CI unit
veloce (`uv run pytest -m "not cloud"` e `tests/unit` restano offline e veloci).

> **`pip` è best-effort.** Il percorso `uv`/`uvx` è il gate; `pip` viene *provato* ma, se non risolve
> le dipendenze interne di workspace, è marcato `xfail` (limite noto → FEAT-010), non un rosso.

---

## 4. Installare Sertor su un ospite (distribuzione interim `git+url`)

**Prerequisiti:** Python ≥ 3.11; `uv` (raccomandato). Rete verso GitHub. Nessun account PyPI.

### Percorso primario — `uv`/`uvx` (gate)

```powershell
# Installer wiki/RAG (sertor):
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor" sertor --help

# Installer governance/SDLC (sertor-flow):
uvx --from "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor-flow" sertor-flow --help
```

`uv` risolve le dipendenze interne (`sertor-core`, `sertor-install-kit`) **dal workspace scoperto nel
checkout git** — non da PyPI. Gli entry-point `sertor`/`sertor-flow` (e, dopo l'install, i
console-script `sertor-rag`/`sertor-wiki-tools` di `sertor-core`) diventano invocabili.

### Percorso secondario — `pip` (best-effort, documentato)

```powershell
pip install "git+https://github.com/themetriost/Sertor#subdirectory=packages/sertor"
```

`pip` **non** conosce il workspace uv: la risoluzione delle dipendenze interne **non** è garantita come
con `uv`. Usa `uv`/`uvx` per l'install a un comando; l'ergonomia piena di `pip` è rinviata a
**FEAT-010**. (Il limite è dichiarato in `docs/install.md`.)

> **Confine.** La **pubblicazione pubblica su PyPI/TestPyPI** è **fuori ambito** (FEAT-006): nessun
> upload, token o hardening supply-chain è introdotto da questa feature. `git+url` è il canale interim.

---

## 5. Acceptance walkthrough (mappa storie → comandi)

| User Story | Comando di verifica | Atteso |
|------------|---------------------|--------|
| US1 install a un comando | `uvx --from "git+…#subdirectory=packages/sertor" sertor --help` | exit 0, entry-point disponibile |
| US2 coerenza legale/metadati | `uv run pytest tests/integration/test_packaging.py -k "license or metadata"` | verde; `LICENSE` in wheel, `urls` presenti |
| US3 verifica ripetibile | `uv run pytest -m integration tests/integration/test_packaging.py` | verde; su lacuna → fail con package+stage |
| US4 doc install | leggere `docs/install.md` | comando esatto ×2 gestori + confine PyPI |

---

## 6. Cosa NON fa questa feature (confini)

- **Nessuna pubblicazione PyPI** (FEAT-006) — nessun token/upload/SBOM.
- **Nessun versioning automatico da tag** — `/VERSION` è bump manuale documentato.
- **Nessuna ergonomia avanzata `pip`/installer** (FEAT-010) — solo *verifica* + *documentazione* del
  limite `pip`-workspace.
- **Nessuna modifica al runtime** del core (porte/adapter/composition invariati) — solo
  metadati/LICENSE/verifica/doc. `install ≠ run` resta garantito.
