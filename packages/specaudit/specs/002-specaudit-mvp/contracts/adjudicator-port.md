# Contract — `Adjudicator` port (il giudizio: allineamento + classificazione)

L'**unico** stadio di giudizio. SpecAudit NON allinea né classifica in proprio: allineamento (FEAT-002)
e confronto semantico + classificazione (FEAT-003) sono a carico dell'**agente chiamante** (l'assistente
host che guida la skill, dentro **Sertor Flow**). Speculare al port `EarsAuthor` di SpecLift.

Questo contratto isola il core dall'autore del giudizio (Principio I/II): chiunque giudichi — agente
chiamante (produzione) o stub deterministico (test/offline) — il **moat strutturale** del runtime
(citazione-senza-riverifica, completezza, integrità dei riferimenti) è ciò che tiene onesto l'output.

> **Differenza di natura dal moat di SpecLift.** In SpecLift il moat verifica le àncore **sul
> filesystem**. In SpecAudit il moat **non** tocca il filesystem: SpecAudit non legge mai codice/test/CI
> (REQ-A01). Il moat qui è *strutturale* — garantisce che il giudizio dell'agente sia **completo**
> (niente scarti silenziosi), **agganciato** (ogni riferimento risolve a un item del bundle) e
> **citante** (le àncore sono copiate dal bundle, mai reinventate né riverificate). La **correttezza
> semantica** del verdetto resta responsabilità dell'agente — è il moat *di giudizio*, non riproducibile
> in codice.

## Interfaccia (port)

```text
Adjudicator.adjudicate(bundle: AuditBundle) -> Adjudication

Adjudication = {
  changeset_ref: str,               # deve combaciare col bundle
  groups: list[AlignedGroup],       # gruppi allineati + candidati MANCANTE (speclift: [])
  extras: list[ExtraItem],          # item SpecLift "di più" (NON_DOCUMENTATO)
}
```

Forma di `AlignedGroup` / `ExtraItem`: vedi `adjudication.schema.json` e `data-model.md`. L'agente
referenzia gli item **per indice** (`original`, `speclift`), mai per testo àncora.

### Invarianti (vincolanti — verificate da `report`, fail-loud)
- **Riferimenti per indice**: ogni indice in `groups`/`extras` DEVE esistere nel bundle. Indice fuori
  range → `DanglingReferenceError` (R7).
- **Completezza (niente scarti silenziosi)**: ogni indice `original` compare in **esattamente un**
  gruppo; ogni indice `speclift` in **esattamente un** gruppo **o** in `extras`. Copertura mancante o
  doppia → `IncompleteAdjudicationError` (R7, NFR-2 FEAT-002).
- **Nessuna àncora nuova**: l'agente NON scrive àncore; le àncore nel report sono **copiate dal bundle
  per indice** (REQ-A02). Il runtime ignora qualunque testo-àncora che l'agente inserisse.
- **Allineamento N:M**: un originale può avere 0..N item; un item può stare in un solo gruppo o in
  extras (REQ-A05, FEAT-002 REQ-001/002/003).
- **Verdetto peggiore (multi-item)**: nei gruppi con più item divergenti l'agente applica worst-wins e
  lo dichiara nella spiegazione, nominando l'item/gli item responsabili (FR-009a, R2).
- **Spiegazione obbligatoria**: `verdict != SODDISFATTO` ⇒ `explanation` non vuota e **specifica** (non
  intercambiabile tra casi, FEAT-003 REQ-007/NFR-1).
- **Onestà della confidenza**: `verdict_confidence` non supera mai `alignment_confidence` quando questa
  è BASSA (REQ-009/010).
- **DRIFTED proposto**: un verdetto DRIFTED è sempre marcato `proposed` nel report (REQ-A06/REQ-011) —
  garantito dal runtime in base all'enum, non affidato all'agente.
- **Confine di fiducia**: il giudizio si fonda SOLO sul testo dei due artefatti e sulle àncore già nel
  bundle. Nessuna lettura di codice/test/CI (REQ-A01/FEAT-003 REQ-012), nessuna riverifica (REQ-A02).
- **Scoring**: per i non-SODDISFATTO l'agente fornisce `severity` e `detectability` categorici; la
  combinazione in `risk` la fa il runtime (R6), non l'agente.

## Realizzazione: agente chiamante via skill sottile

L'adjudicator non è un callable in-process: è l'**agente chiamante**. La pipeline si spezza al confine
del bundle, orchestrata dalla skill sottile `specaudit`:

1. **CLI — `prepare`** (deterministico): ingest output SpecLift → risolvi fonte originale (cascata) →
   normalizza → **stop**. Output: `AuditBundle` (i due insiemi indicizzati + gap dichiarati).
2. **Agente — giudica**: legge il bundle, allinea (N:M, confidenza d'aggancio) e classifica (verdetto,
   spiegazione specifica, confidenza, e per i non-SODDISFATTO severità/rilevabilità). Rispetta le
   invarianti. Scrive `adjudicated.json`.
3. **CLI — `report`** (deterministico): rilegge bundle + adjudication, **verifica gli invarianti
   strutturali** (integrità refs, completezza), **attacca le àncore dal bundle**, aggrega matrice,
   combina lo scoring, propaga i gap, ordina per rischio ed emette l'`AuditReport`.

### `StubAdjudicator` — solo test/offline (NON la via di produzione)
L'adapter `adjudication_file.py` include uno **stub deterministico** per i test e l'uso offline: allinea
in modo banale (1:1 per posizione, o tutto MANCANTE/NON_DOCUMENTATO se le lunghezze non combaciano) ed
emette verdetti placeholder + una `open_question` "giudizio demandato all'agente chiamante". Serve a
esercitare `report` end-to-end senza un agente; **non** è il percorso con cui SpecAudit produce verdetti
reali.

> **Implicazione (onestà):** la CLI **da sola** non emette verdetti veri (solo placeholder). La capacità
> piena è *CLI + skill + agente* insieme — coerente con "skill + runtime" (FR-022).
