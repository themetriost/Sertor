# Quickstart — SpecAudit MVP

SpecAudit confronta due rappresentazioni indipendenti dello stesso requisito — il **requisito
originale** e l'**output di SpecLift** (EARS ancorati) — e per ogni requisito emette un verdetto
citabile, **senza mai leggere codice**. È il gemello "top-down" di SpecLift nel *gate del pre-merge*.

## Prerequisiti

- Python 3.12+; `specaudit` installato nel progetto (secondo package accanto a `speclift`).
- Un **output SpecLift reale** (`*.speclift.json`, contratto `output.schema.json` v1) per il changeset
  da auditare. Dipendenza vincolante: SpecAudit non lo produce, lo consuma.
- Una **fonte originale**: la cartella `requirements/` canonica, oppure un documento di requisiti/EARS.

## Il sandwich (chi fa cosa)

```text
[prepare]  CLI deterministica  → audit-bundle.json   (i due insiemi indicizzati + gap dichiarati)
[giudizio] AGENTE chiamante     → adjudicated.json    (allineamento N:M + verdetti, per indice)
[report]   CLI deterministica  → audit.json + audit.md (àncore citate, matrice, rischio, gap)
```

La CLI **non giudica**: prepara i fatti e poi verifica/assembla. L'**agente** allinea e classifica. Il
runtime garantisce l'**onestà strutturale** (citazione senza riverifica, completezza, integrità dei
riferimenti); la **qualità del giudizio** è dell'agente (il vero moat di SpecAudit).

## Flusso tipico (produzione: CLI + agente)

```text
# 1) marcia 1 — prepara il fascicolo di audit
specaudit prepare --speclift ./out/report.speclift.json --requirements ./requirements --out ./tmp/audit

# 2) l'AGENTE legge ./tmp/audit.audit-bundle.json, allinea + classifica, scrive ./tmp/adjudicated.json
#    (referenzia gli item per INDICE; non scrive àncore; applica worst-wins nei gruppi multi-item)

# 3) marcia 2 — emetti il report verificato
specaudit report --bundle ./tmp/audit.audit-bundle.json --adjudicated ./tmp/adjudicated.json --out ./out/audit
```

Output: `./out/audit.json` (canonico) + `./out/audit.md` (vista). Il report ordina in cima i verdetti
non-SODDISFATTO più a rischio, e **dichiara** ogni gap (fonte originale assente, agganci deboli, àncore
SpecLift `unverified`).

## Uso offline / test (monolite con stub)

```text
specaudit audit --speclift ./out/report.speclift.json --original ./spec/original.md --format md
```

Usa lo `StubAdjudicator` (allineamento banale, verdetti placeholder): serve a esercitare la pipeline
senza un agente. **Non** è il percorso di produzione — i verdetti veri li scrive l'agente.

## Cosa NON fa (confine di fiducia)

- **Non** legge codice, test o stato CI (REQ-A01). Zero chiamate `search_code`/`find_symbol`/`who_calls`.
- **Non** riverifica le àncore SpecLift (REQ-A02): le **cita** copiandole dal bundle. Eredita gli
  eventuali errori di retrieval di SpecLift, non li corregge.
- **Non** conferma un DRIFTED da solo: lo marca `proposed` (REQ-A06) — la conferma è di un umano.

## Verifica rapida

- `specaudit prepare` senza fonte originale risolvibile → esce `0` con `declared_gaps` contenente
  `original_source: absent` (mai un MANCANTE inventato).
- `specaudit report` con un'adjudication che referenzia un indice inesistente o non copre tutti gli
  item → **fail-loud** (exit `5`).
- Il set di verdetti/citazioni in `audit.md` coincide con `audit.json` (SC-006).
