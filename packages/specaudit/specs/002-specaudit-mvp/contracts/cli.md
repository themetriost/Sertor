# Contract — CLI `specaudit`

Interfaccia pubblica (Principio III). Host-agnostica; la skill sottile la invoca, non la reimplementa.
Stesso pattern a due marce di SpecLift (deterministico → agente → deterministico).

## Sottocomandi

```text
specaudit prepare --speclift <path> [--original <path> | --requirements <dir>] [--provided <path>]
                  [--changeset-ref <ref>] [--out <base>] [--verbose]

specaudit report  --bundle <path> --adjudicated <path>
                  [--format json|md|both] [--out <base>] [--verbose]

specaudit audit   --speclift <path> [--original <path> | --requirements <dir>]
                  [--changeset-ref <ref>] [--format json|md|both] [--out <base>] [--verbose]
```

### `prepare` (deterministico) — FEAT-001
Ingest dell'output SpecLift + risoluzione della fonte originale (cascata) + normalizzazione. Emette
`<out>.audit-bundle.json` (conforme a `audit-bundle.schema.json`): i due insiemi **indicizzati** + i
`declared_gaps`. È l'input per l'agente.
- `--speclift <path>`: il file `*.speclift.json` (output canonico di SpecLift, `output.schema.json` v1).
- `--original <path>`: un file/documento di requisiti originali già pronto (o EARS da altra pipeline).
- `--requirements <dir>`: la cartella canonica `requirements/` da cui estrarre gli EARS (default se
  nessuno dei due è passato: `./requirements`).
- `--provided <path>`: fonte originale **fornita dall'agente** (`provided_source`, per il percorso
  RAG/MCP a monte) — mutuamente esclusiva con `--original`/`--requirements`.
- `--changeset-ref <ref>`: se dato, deve combaciare col `changeset_ref` dell'output SpecLift (altrimenti
  fail-loud, R5).
- Fonte originale assente in ogni step → **gap dichiarato** nel bundle (`original_source: absent`), exit
  `0` (FR-003, non è un errore).

### `report` (deterministico) — FEAT-004
Rilegge il bundle + il file `--adjudicated` scritto dall'agente. **Verifica gli invarianti strutturali**
(integrità dei riferimenti, completezza), **attacca le àncore dal bundle per indice** (mai riverificate),
aggrega la **matrice**, combina lo **scoring di rischio** (severità×rilevabilità → `risk` via matrice
`config.py`), **propaga i gap**, ordina per rischio ed emette l'`AuditReport`.
- `--format`: `json` (canonico), `md` (vista derivata), `both` (default).
- Riferimento a indice inesistente → fail-loud; copertura incompleta → fail-loud (vedi exit codes).

### `audit` (monolitico) — offline/test
Esegue `prepare` → **StubAdjudicator** → `report` in un colpo. Emette verdetti **placeholder** (lo stub
non giudica davvero). Serve all'uso offline e ai test end-to-end; **non** è il percorso di produzione
(che è `prepare` + agente + `report`). Coerente col monolite `speclift <ref>` di SpecLift.

## Comportamento (mappa ai requisiti)

- Consuma l'output SpecLift via il suo **contratto pubblico versionato** (`output.schema.json` v1) —
  mai gli interni di SpecLift, mai `import speclift`/`sertor_core` (Principio III).
- **Non** legge codice/test/CI in nessun sottocomando (REQ-A01). **Non** riverifica le àncore (REQ-A02):
  le trasporta e le cita.
- Emette `AuditReport` conforme a `output.schema.json` (FR-016); la vista Markdown coincide col JSON per
  verdetti e citazioni (SC-006).
- **Exit codes**: `0` ok (anche con fonte originale assente = gap dichiarato); `2` argomenti invalidi
  (opzioni mutuamente esclusive combinate, file non indicato); `3` output SpecLift assente/malformato/
  versione non supportata/`changeset_ref` non corrispondente (`SpecLiftArtifactError`/`SpecLiftVersionError`/
  `ChangesetMismatchError`, fail-loud REQ-A04); `5` adjudication non valida — riferimento fuori range
  (`DanglingReferenceError`) o copertura incompleta (`IncompleteAdjudicationError`).
- Nessun output parziale silenzioso su errore: la causa (e lo stadio) sono dichiarati su stderr
  (Principio VI/XI). Nessun segreto nei log (Principio X).

## Esempi

```text
# marcia 1: prepara il fascicolo di audit (fonte = requirements/ canonico)
specaudit prepare --speclift ./out/report.speclift.json --requirements ./requirements --out ./tmp/audit

# (l'agente legge ./tmp/audit.audit-bundle.json e scrive ./tmp/adjudicated.json)

# marcia 2: emetti il report verificato
specaudit report --bundle ./tmp/audit.audit-bundle.json --adjudicated ./tmp/adjudicated.json --out ./out/audit

# offline/test: monolite con stub
specaudit audit --speclift ./out/report.speclift.json --original ./spec/original.md --format md
```
