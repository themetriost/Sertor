# Phase 1 — Data Model: Packaging distribuibile

**Feature**: `047-packaging-distribuibile` | **Date**: 2026-06-17

Questa feature non introduce entità di dominio runtime (nessun nuovo tipo in `sertor_core`). Le
"entità" sono **artefatti di packaging e i loro metadati**: pacchetti del workspace, la versione
unica, gli artefatti di distribuzione, e il *referto* della verifica. Le modelliamo come **strutture
di configurazione/dato statiche** (file `pyproject.toml`, `VERSION`, `LICENSE`, wheel/sdist) e — per
la sola verifica — eventuali piccole dataclass interne al modulo di test (non parte dell'API pubblica
del core). Non vengono toccate le 8 porte `Protocol` né `composition.py`.

---

## E1 — Prodotto distribuibile (`DistributablePackage`)

Un'unità del `uv workspace` che viene buildata in artefatti. Quattro istanze, in **due insiemi**
(DA-P3/P4).

| Campo | Tipo | Valore (per istanza) | Vincolo |
|-------|------|----------------------|---------|
| `name` | str | `sertor-core` · `sertor` · `sertor-install-kit` · `sertor-flow` | da `[project].name` |
| `pyproject_path` | path | `pyproject.toml` · `packages/<n>/pyproject.toml` | esiste |
| `kind` | enum | `user-facing` (`sertor`, `sertor-flow`) · `internal` (`sertor-core`, `sertor-install-kit`) | DA-P3/P4 |
| `license` | str | `MIT` (coerente con `LICENSE`) | REQ-002, REQ-004 |
| `requires_python` | str | `>=3.11` | REQ-012 |
| `entry_points` | list[str] | `sertor`→`sertor`; `sertor-flow`→`sertor-flow`; `sertor-core`→`sertor-rag`,`sertor-wiki-tools`; `sertor-install-kit`→— | REQ-023 |
| `package_data` | list[glob] | solo `sertor`: `assets/**` | REQ-021 |

**Regole d'insieme.**
- *Build-validati* = tutti e 4 → bersaglio gruppi A (licenza) e C (build). REQ-020/022/024.
- *User-facing* = `sertor`, `sertor-flow` → bersaglio gruppo B (metadati completi). REQ-010/013/014.
- *Internal* = `sertor-core`, `sertor-install-kit` → build-validati ma **esonerati** dalla checklist
  user-facing (`urls`/`classifiers` non obbligatori; per `sertor-core` consigliati, non gate).

**Stato attuale → target (lo "schema" che la feature porta a conformità).**

| Campo | Stato 2026-06-16 | Target feature |
|-------|------------------|----------------|
| `LICENSE` file | assente (radice + ogni pkg) | presente in radice e in ogni pkg, incluso in wheel |
| `version` | `0.1.0` statico ×4 | dinamico da `/VERSION` (E2), allineato |
| `urls` (user-facing) | assente | `Repository = github.com/themetriost/Sertor` |
| `classifiers`/`keywords` (user-facing) | assenti | presenti (Should, REQ-013) |
| `authors` | `[{ name = "Sertor" }]` ×4 | invariato (adeguato) |
| `description` | presente ×4 | invariato |

---

## E2 — Versione di prodotto (`ProductVersion`)

L'unica versione allineata, **fonte di verità singola** (DA-P1, REQ-011, NFR-4).

| Campo | Tipo | Valore | Vincolo |
|-------|------|--------|---------|
| `value` | semver str | es. `0.1.0` | un solo file `/VERSION` |
| `source` | path | `/VERSION` (radice repo) | letto da `[tool.hatch.version]` in ogni pyproject (`dynamic = ["version"]`) |

**Invariante (SC-007).** I 4 metadati buildati riportano **la stessa** stringa, identica al contenuto
di `/VERSION`. La verifica (C-VERIFY) asserisce l'uguaglianza tutti-e-4 == `VERSION`; 0 disallineamenti.
**Bump** = modifica della sola riga di `/VERSION` → i 4 artefatti ereditano per costruzione (nessun
editing manuale ripetuto). Versioning automatico da tag = fuori ambito (Won't).

---

## E3 — Artefatto di distribuzione (`DistributionArtifact`)

L'output buildato da un prodotto: **coppia sdist + wheel** (REQ-020).

| Campo | Tipo | Vincolo |
|-------|------|---------|
| `sdist` | file `.tar.gz` | prodotto senza errori |
| `wheel` | file `.whl` | prodotto senza errori |
| `contains_license` | bool | `LICENSE` dentro la wheel (REQ-003) — vero per tutti |
| `contains_assets` | bool | `assets/**` dentro la wheel — **solo** `sertor` (REQ-021) |
| `declares_entry_points` | bool | `entry_points.txt`/`METADATA` dichiarano i console-script attesi (REQ-023) |
| `metadata` | mapping | `name/version/license/requires-python` (+ `urls/classifiers` se user-facing) |

**Ispezione (stdlib).** wheel = zip (`zipfile`); METADATA = RFC822 (`email.parser`); `entry_points.txt`
= INI (`configparser`). Nessuna dipendenza nuova.

---

## E4 — File di licenza (`LicenseFile`)

| Campo | Tipo | Valore | Vincolo |
|-------|------|--------|---------|
| `path` | path | `/LICENSE` + `packages/<n>/LICENSE` | REQ-001 |
| `spdx` | str | `MIT` | coerente con `[project].license` (REQ-002) |
| `text` | str | testo MIT con `Copyright (c) 2026 Sertor` | nessun segreto/dato personale |

**Regola d'incoerenza (REQ-004).** Se un pyproject dichiara `license = MIT` ma manca il `LICENSE` nel
sorgente o nella wheel → la verifica **fallisce** (edge "licenza dichiarata senza testo").

---

## E5 — Sorgente di distribuzione interim (`InterimSource`)

Il canale corrente (DA-4): **checkout git** raggiungibile via `git+url`, **non** PyPI.

| Campo | Tipo | Valore |
|-------|------|--------|
| `url` | str | `git+https://github.com/themetriost/Sertor` |
| `subdirectory` | str | `packages/sertor` · `packages/sertor-flow` (per i user-facing) |
| `resolves_internal_deps` | enum | `uv`: dal workspace del checkout (sì) · `pip`: best-effort (R-2) |

Risoluzione dipendenze interne (`sertor-core`, `sertor-install-kit`): garantita con `uv` (workspace
scoperto dal checkout); con `pip` non garantita → limite documentato (Decision 3). Nessun indice
pubblico richiesto (REQ-032, SC-004).

---

## E6 — Referto di verifica (`PackagingVerificationReport`)

Output osservabile della verifica (concettuale; in pratica = asserzioni pytest + messaggi). Quando
fallisce, identifica in modo **non ambiguo** package + percorso (REQ-024, REQ-035).

| Campo | Tipo | Significato |
|-------|------|-------------|
| `package` | str | quale prodotto (su fallimento) |
| `stage` | enum | `metadata` · `license` · `build` · `wheel-contents` · `entry-points` · `clean-install` |
| `manager` | enum? | `uv`/`uvx` · `pip` (per lo stage clean-install) |
| `status` | enum | `pass` · `fail` (gate) · `known-limitation` (pip-workspace, xfail) |
| `detail` | str | messaggio azionabile (campo mancante / file assente / build error) |

`known-limitation` esiste **solo** per il caso `pip`-workspace (Decision 3): non rosso, ma tracciato e
documentato → FEAT-010. Tutto il resto è `pass`/`fail` binario.

---

## Relazioni e invarianti trasversali

```
ProductVersion(/VERSION) ──(dynamic version)──► DistributablePackage ×4
DistributablePackage ──build──► DistributionArtifact (sdist + wheel)
DistributionArtifact ──contains──► LicenseFile (sempre) + assets (solo sertor)
InterimSource ──install (uv gate / pip soft)──► entry_points invocabili
PackagingVerificationReport ◄── asserisce ── {metadati, licenza, wheel, install}
```

Invarianti chiave mappate ai Success Criteria:
- **SC-001/SC-007**: `LICENSE` coerente in ogni pkg+wheel · versione unica == `/VERSION`.
- **SC-002**: user-facing espongono `name/version/license/authors/urls/description`.
- **SC-003/SC-005**: build produce sdist+wheel attesi · entry-point primari invocabili (exit 0).
- **SC-008/SC-009**: 0 azioni di pubblicazione pubblica · 0 segreti in file versionati/artefatti.

Nessuna nuova porta `Protocol`, nessun nuovo adapter, nessuna modifica a `composition.py` o ai servizi
del core: la feature opera su **metadati di packaging e una suite di verifica**, non sul runtime.
