# Quickstart — Installer `sertor install wiki` (FEAT-012)

**Branch**: `012-sertor-install-wiki` | **Spec**: [`spec.md`](spec.md) | **Plan**: [`plan.md`](plan.md)

Guida operativa: come si installa il sistema-wiki su un repo ospite, e come si esegue/verifica la
feature in sviluppo. Tutto **offline, senza LLM, senza cloud** (Principio V; SC-005/006).

---

## 1. Installare il pacchetto `sertor`

Il pacchetto `sertor` (distinto da `sertor-core`, D1) vive in `packages/sertor/`. In sviluppo:

```powershell
# editable: legge gli artefatti dagli assets nel source tree, nessun rebuild del wheel (DI-5)
uv pip install -e packages/sertor          # installa sertor + dipendenza sertor-core
# verifica
sertor --help
sertor install --help
```

Distribuzione interim (epica DA-4, fuori ambito di questa feature ma non preclusa):
```powershell
uv add "git+https://<host>/<repo>.git#subdirectory=packages/sertor"
```

## 2. Installare il sistema-wiki su un ospite (US1)

```powershell
cd C:\path\al\repo\ospite
sertor install wiki
```

Crea, sotto la directory corrente:
- `.claude/skills/wiki-author/` (SKILL.md, wiki-playbook.md, `*-craft.md`, `ops/*.md`),
- `.claude/commands/wiki.md`, `.claude/agents/wiki-curator.md`,
- `.claude/hooks/wiki-pending-check.ps1` + voci hook in `.claude/settings.json`,
- sezione step-ritual in `CLAUDE.md` (blocco a marker),
- `wiki.config.toml` (default inferiti),
- struttura `wiki/` (cartelle tassonomia + `index.md` + `log/`).

Report finale su stdout (vedi `contracts/install-report.md`), exit 0.

### Opzioni di governo (US3)

```powershell
sertor install wiki --target C:\altro\repo          # installa altrove
sertor install wiki --language it                    # lingua del wiki = it
sertor install wiki --source-dirs src,docs,lib       # override cartelle sorgente
sertor install wiki --json                           # report JSON (Could)
```

## 3. Verificare che l'install sia operativo (SC-008, dogfood)

```powershell
cd <ospite>
sertor-wiki-tools scan --config wiki.config.toml --json       # lavoro pendente
sertor-wiki-tools validate --config wiki.config.toml --json   # convenzioni pagine
sertor-wiki-tools lint --config wiki.config.toml --json       # link/orfani/frontmatter
```

Tutti devono girare senza errori sulla config generata (la struttura `wiki/` esiste).

## 4. Re-run e non-distruttività (US2)

```powershell
sertor install wiki        # secondo run: tutto skipped/merged(0), stesso stato, exit 0
```

Garanzie: zero byte di contenuto utente sovrascritti fuori dai blocchi gestiti (CLAUDE.md
fuori-marker, voci utente di settings.json); zero duplicati.

> **Nota `settings.json`:** il merge preserva tutte le voci utente **semanticamente**; la
> formattazione JSON può essere normalizzata (reindentata) — è config strutturata, non prosa (D5).
> Su `CLAUDE.md` invece la garanzia è **byte-per-byte** fuori dai marker.

## 5. Prerequisiti dell'ospite

- **Python ≥ 3.11** con `sertor-core` nell'ambiente (dipendenza del pacchetto `sertor`).
- **PowerShell** (`pwsh`/`powershell`) per l'esecuzione degli **hook** di sessione (D6). Su un
  ospite Linux senza `pwsh` il sistema-wiki resta usabile a mano e via `/wiki`; solo i promemoria
  automatici degli hook non scattano (rischio residuo documentato; nessun SC dipende dall'hook).

## 6. Sviluppo: sincronia assets ⇄ `.claude/` (D2)

Gli artefatti bundlati sono in `packages/sertor/src/sertor_installer/assets/`. Fonte = **assets**;
il `.claude/` del repo Sertor è **derivato**.

```powershell
# propaga gli assets al .claude/ del repo Sertor (direzione: assets → .claude)
python -m sertor_installer.sync     # (nome del comando: definito in tasks)
# il test di guardia fallisce se assets e .claude/ divergono
uv run pytest packages/sertor/tests/test_assets_sync.py
```

## 7. Eseguire i test della feature

```powershell
uv run pytest packages/sertor/tests -m "not cloud"   # unit + integrazione su repo temporaneo
```

Test chiave (Phase: tasks):
- repo vuoto → tutti `created`, exit 0 (US1/SC-001);
- repo pre-popolato → fuori-marker intoccato, voci utente preservate, exit 0 (US2/SC-002);
- doppio run → stesso stato (US2/SC-003);
- scansione artefatti → zero «Sertor» (SC-004);
- config generata → passa `load_profile` (D7);
- nessuna rete/LLM in tutta la suite (SC-005/006).
