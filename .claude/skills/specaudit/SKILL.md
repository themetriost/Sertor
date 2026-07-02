---
name: "specaudit"
description: "Confronta un requisito ORIGINALE (da requirements/, un'altra specifica, o EARS di un'altra pipeline) con l'output ANCORATO di SpecLift per lo stesso changeset, ed emette un verdetto per requisito (SODDISFATTO / PARZIALE / MANCANTE / DRIFTED / NON-DOCUMENTATO) con la citazione dell'àncora, SENZA mai leggere codice: la CLI deterministica prepara i due insiemi e assembla/verifica, tu (l'agente) allinei e giudichi. Usa questa skill ogni volta che l'utente vuole verificare se il codice rispetta la spec, auditare la conformità requisito↔implementazione, sapere cosa è stato promesso ma non consegnato (o consegnato ma non promesso), o riconciliare i requisiti originali con ciò che SpecLift ha estratto dal codice — anche se non nomina esplicitamente 'SpecAudit'."
argument-hint: "Il changeset da auditare + l'output SpecLift (*.speclift.json) e la fonte originale (requirements/ o un documento)"
compatibility: "Richiede la CLI `specaudit` installata nel progetto e un output SpecLift (*.speclift.json) per il changeset"
metadata:
  author: "sinthari"
  capability: "specaudit"
user-invocable: true
disable-model-invocation: false
---

## User Input

```text
$ARGUMENTS
```

`$ARGUMENTS` indica cosa auditare: tipicamente il percorso dell'output SpecLift (`*.speclift.json`) per
un changeset e la fonte dei requisiti originali (la cartella `requirements/` o un documento di spec).

## Cosa sei, in questo flusso

Tu sei **il giudizio** di SpecAudit. La CLI fa la parte deterministica e verificabile (recupera i due
insiemi, li indicizza, poi assembla il report, cita le àncore, calcola matrice e rischio, garantisce la
completezza); **tu allinei i requisiti e classifichi i verdetti**. Non leggi mai codice, test o CI: ti
basi **solo** sul testo dei due artefatti e sulle àncore che SpecLift ha già prodotto. Referenzi gli item
per **indice**; la CLI attacca le àncore reali dal fascicolo — così non puoi inventarle. È il contratto
del port `Adjudicator` (vedi `contracts/adjudicator-port.md`).

> Invoca la CLI come `specaudit …` (se il progetto la espone via un runner, es. `uv run specaudit …`). Se
> un comando `specaudit` fallisce *loud* (output SpecLift assente/di versione errata, riferimento a un
> changeset diverso, adjudication incompleta), **fermati e riporta**: non aggirare l'errore.

## Il confine di fiducia (non attraversarlo)

- **Non** leggere codice sorgente, **non** eseguire test, **non** interrogare la CI. Zero
  `search_code`/`find_symbol`/`who_calls`.
- **Non** riverificare le àncore di SpecLift: le **citi**, non le controlli. Se un'àncora era
  `unverified`, riportalo — non promuoverla.
- Erediti gli eventuali errori di retrieval di SpecLift; non li correggi (un falso MANCANTE lato SpecLift
  resta un limite dichiarato, non un tuo compito di verifica).

## Procedura

### 1 — Prepara il fascicolo di audit (marcia 1, deterministica)

Esegui:

```text
specaudit prepare --speclift <PATH_SPECLIFT_JSON> --requirements <DIR_REQUIREMENTS> --out <TMP>/audit
```

(usa `--original <FILE>` invece di `--requirements <DIR>` se la fonte originale è un singolo documento).
Produce `<TMP>/audit.audit-bundle.json`: i due insiemi **indicizzati** (`original[]`, `speclift[]`) +
`declared_gaps`. Se la fonte originale è assente, il bundle lo dichiara (`original_source: absent`) e non
è un errore: riportalo.

### 2 — Allinea e giudica (la TUA parte)

Leggi `<TMP>/audit.audit-bundle.json`. `original` è la lista dei requisiti originali (con `index`, `id`,
`text`); `speclift` è la lista degli item reverse-engineered (con `index`, `statement`, `anchor`, e
`origin` = requirement/drift).

**Allinea (N:M)** ogni requisito originale con l'insieme (anche vuoto) di item SpecLift che parlano della
stessa cosa. Un originale ampio può mappare a più item; un item può stare in un solo gruppo o restare
"di più".

**Classifica** ogni gruppo:

- **SODDISFATTO** — l'originale è pienamente realizzato dagli item allineati, senza scostamenti.
- **PARZIALE** — realizzato solo in parte (copre un sottoinsieme del promesso).
- **MANCANTE** — nessun item SpecLift pertinente (gruppo con `speclift: []`).
- **DRIFTED** — realizzato nello *spirito* ma divergente in un dettaglio (tempistica, condizione, effetto
  collaterale). È il verdetto più prezioso: **spiega specificamente come diverge**, e resta una
  **proposta** (mai confermato in automatico).

Gli item SpecLift che non mappano a nessun originale vanno in **extras** come **NON_DOCUMENTATO** (a meno
che il testo suggerisca un riaggancio a un requisito esistente).

Regole (invarianti — la CLI le verifica, fail-loud):
- **Copri tutto**: ogni indice `original` in **esattamente un** gruppo; ogni indice `speclift` in **un**
  gruppo **o** in extras. Niente scarti silenziosi.
- **Worst-wins**: se un gruppo ha più item con esiti diversi, il verdetto del gruppo è il **peggiore**
  (DRIFTED > PARZIALE > MANCANTE; SODDISFATTO solo se tutti gli item lo sono) e la spiegazione nomina
  l'item/gli item che divergono.
- **Spiegazione specifica** obbligatoria per ogni verdetto ≠ SODDISFATTO (non un'etichetta generica).
- **Confidenza onesta**: se l'aggancio è a `alignment_confidence: bassa`, non dare un verdetto ad alta
  confidenza.
- Per ogni verdetto ≠ SODDISFATTO fornisci `severity` e `detectability` (alta/media/bassa): la gravità
  dello scostamento e quanto facilmente sfuggirebbe a una revisione manuale.

Scrivi `<TMP>/adjudicated.json` con questa forma (referenzia per **indice**, non scrivere àncore):

```json
{
  "changeset_ref": "<lo stesso changeset_ref del bundle>",
  "groups": [
    {
      "original": 0, "speclift": [0], "alignment_confidence": "alta",
      "verdict": "DRIFTED", "verdict_confidence": "media",
      "explanation": "L'originale promette X 'subito'; l'item 0 lo realizza in modo bufferato.",
      "severity": "media", "detectability": "bassa"
    },
    { "original": 1, "speclift": [1], "alignment_confidence": "alta",
      "verdict": "SODDISFATTO", "verdict_confidence": "alta" }
  ],
  "extras": [
    { "speclift": 2, "verdict": "NON_DOCUMENTATO",
      "explanation": "Comportamento non promesso da alcun requisito originale.",
      "verdict_confidence": "media", "severity": "bassa", "detectability": "alta" }
  ],
  "open_questions": ["…eventuali dubbi di allineamento…"]
}
```

### 3 — Assembla e verifica (marcia 2, deterministica)

Esegui:

```text
specaudit report --bundle <TMP>/audit.audit-bundle.json --adjudicated <TMP>/adjudicated.json --out <OUT>/audit
```

Produce `<OUT>/audit.json` (canonico) e `<OUT>/audit.md` (vista). La CLI **verifica** l'integrità dei
riferimenti e la completezza (fallisce se qualcosa è scoperto o referenzia un indice inesistente),
**attacca le àncore dal bundle**, ordina i verdetti per rischio ed emette il report.

### 4 — Riporta

Mostra all'utente:
- il percorso del report (`.md` e `.json`);
- la **matrice** (quanti SODDISFATTO / PARZIALE / MANCANTE / DRIFTED / NON-DOCUMENTATO);
- i verdetti **più a rischio** in cima, con la spiegazione del *come diverge*;
- i **DRIFTED** come *proposte* da confermare (non decisioni);
- ogni **gap dichiarato** (fonte originale assente, agganci deboli, àncore SpecLift non verificate):
  **dillo esplicitamente** — indicano dove il verdetto va letto con cautela.

## Done When

- [ ] Fascicolo di audit prodotto (`prepare`).
- [ ] Allineamento N:M + verdetti scritti da te, referenziati per indice, su solo testo + àncore.
- [ ] Report verificato prodotto (`report`): completezza e integrità garantite dalla CLI.
- [ ] Esito riportato all'utente, con matrice, rischio, DRIFTED come proposte e gap resi espliciti.
