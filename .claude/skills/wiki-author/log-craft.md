# Come si scrive una voce di log ben fatta — anatomia del log-craft

> **Pagina di riferimento (foglia).** Descrive *com'è fatta una buona voce del log* — cosa ci va, cosa no,
> quanto, come. È **linkata da** chi appende una voce: il playbook §6 (la *convenzione*: grammatica
> dell'heading + vocabolario delle operazioni) e ogni operazione che chiude con una voce di log
> (`ops/record.md`, `ops/ingest.md`, `ops/lint.md`, `ops/reorg.md`, …). È una **foglia**: non dipende da
> altri documenti del sistema — le operazioni la referenziano, non viceversa. È la **gemella** di
> [`page-craft.md`](page-craft.md): se quella dice come si scrive una *pagina* (evergreen), questa dice come
> si scrive una *voce di log* (datata).
>
> **Host-agnostica (Principio X).** I principi valgono su qualunque host; ciò che *varia* — il vocabolario
> delle operazioni, la sintassi dei link, il formato dell'heading — viene dal profilo (`wiki.config.toml`) e
> dal playbook §6. Gli esempi concreti (`[[wikilink]]`, `record`, `lint A`) sono il **profilo Sertor**.

Il log è l'artefatto **append-only** del wiki: non si riscrive. Con la rotazione è **un file per giorno**
(`log/YYYY-MM-DD.md`); la voce la scrive `append-log` — tu componi il **corpo curato**, il deterministico la
**piazza** nel file del giorno (FEAT-008). È un *diario
datato*, non una pagina. Una voce ben fatta ha tre qualità: sta dalla **parte giusta del confine
log↔pagina**, ha un'**anatomia** prevedibile, ed è **densa** (niente deriva verso il dump).

## 1. Cos'è una voce — e cosa NON è (il confine log↔pagina)

È il **duale** di [`page-craft.md`](page-craft.md) §3. La pagina cattura la **conoscenza distillata e
riusabile** (*cosa resta*, evergreen); la voce di log registra l'**evento datato** (*cosa è successo*, e
dove vive ora ciò che resta).

| Va nel **log** (voce datata) | Va nella **pagina** (evergreen) |
|---|---|
| *cosa* è stato fatto in questo step e *quando* | il *concetto* / il metodo / il razionale riusabile |
| la decisione presa + un **puntatore** al *perché* | il *perché* esteso, le alternative scartate |
| **dove** vive il risultato (`[[pagina]]`, file, commit) | il contenuto vero e proprio |
| l'**esito/verifica** (test, lint, hash) | claim atemporale ancorato |

- **La voce punta, non ri-dumpa.** Se uno step ha creato/aggiornato una pagina, la voce dice *quale* pagina
  e *in una riga* il succo, poi linka — **non** ricopia il contenuto della pagina. Il contenuto duplicato
  invecchia in due posti (il log non si aggiorna mai: è append-only → la copia diventa subito stale).
- **La voce è una traccia, non un backup.** Non serve a ricostruire *tutto* lo step: serve a sapere, a
  freddo, *che* è successo, *dove* guardare e *com'è andata*. Git traccia già i file e i diff: la voce non
  è l'elenco dei file toccati.

## 2. Anatomia di una voce

```
## [YYYY-MM-DD] <operazione> | <titolo>

<lead: 1–2 frasi — il perché/contesto/trigger dello step>
- **<etichetta>:** <fatto saliente, una riga>
- **Verifica:** <esito ancorato: lint A 0/0/0/0 · test verdi · commit hash>
```

1. **Heading** — `## [data] <op> | <titolo>`. `<op>` dal **vocabolario del playbook §6**
   (`setup·record·ingest·query·lint·reorg·generate-from-diff·rag-sync`); `<titolo>` descrive **una** cosa,
   come il titolo di una pagina (no "varie", no due step in un titolo).
2. **Lead (1–2 frasi)** — apre col **perché/contesto/trigger**, non col primo file toccato. È ciò che si
   legge a colpo d'occhio scorrendo il log. («Risolto uno smell segnalato dal proprietario: …», non
   «Pagina creata: …»).
3. **Bullet piatti con etichetta in grassetto** — `**Cosa** · **Perché** · **File** · **Verifica** ·
   **Origine**`. Etichette stabili rendono il log scansionabile. **Massimo un livello di nesting**: se ti
   serve il quarto livello di indentazione, stai mettendo nel log il *contenuto* (→ pagina) o stai facendo
   il dump dei file (→ togli).
4. **Riga di esito** quando applicabile — il log è anche la prova che lo step è *chiuso*: `lint A 0/0/0/0`,
   `6 test verdi`, `commit c6930e9`. Una riga, ancorata.

## 3. Granularità — quando una voce, quante voci

- **Una voce per operazione.** L'heading porta *una* `<op>`: se uno step ha fatto cose di natura diversa
  (un `record` **e** un `lint`), sono **due voci** con la loro `<op>`. Operazioni della **stessa** natura
  nello stesso step si **accorpano** in una voce.
- **La voce segue lo step significativo,** non il singolo Edit. Cinque modifiche che realizzano *una*
  decisione = *una* voce.
- **Regola anti-banale (quando NON loggare).** Modifiche puramente meccaniche o di poco conto non meritano
  una voce (è la stessa *regola aurea* del wiki). Casi tipici: `structure` che non ha creato nulla
  (tutto `skipped_existing` → niente voce, è idempotente); refactoring di battitura; rinomina senza
  conseguenze. Se la voce direbbe solo «sistemati typo», non scriverla.

## 4. Densità — l'anti-deriva (il difetto storico del log)

Il log degenera quando le voci diventano **mini-pagine**: nesting profondo, contenuto ricopiato dalle
pagine, elenchi esaustivi. Le contromisure:

- **Soft cap.** Una voce sta di norma in **~6–10 bullet di un livello**. Se cresce, di solito è perché stai
  mettendoci *contenuto* (→ pagina) o *file* (→ git): togli, non comprimere.
- **Niente liste-file esaustive.** Cita 1–2 file **chiave** inline; l'elenco completo lo dà `git` (delegato
  al ruolo VCS). Una sotto-lista «File toccati» con tutti i path è rumore.
- **Niente "Benefici" ad aggettivi.** Frasi-riassunto tipo «più manutenibile, più pulito, pronto a scalare»
  non portano informazione: tagliale. Se un beneficio è reale e riusabile, è un claim da **pagina**.
- **Niente duplicazione del contenuto della pagina.** Il succo in una riga + `[[pagina]]`; il resto vive
  nella pagina (vedi §1).

## 5. Esempio — la stessa attività, scritta male → bene

✗ **Deriva** (mini-pagina nel log):
```
## [data] record | Consolidamento sistema wiki
- **Pagina creata:** syntheses/sistema-wiki-fonte-unica.md documenta:
  - Visione: wiki è LLM Wiki Karpathy; regole erano duplicate → fonte unica…
  - Fonte unica: nuovo file playbook.md (identità + tassonomia + 6 operazioni: record, ingest…)
    1. Skill: hyperlink a playbook…
    2. Comando: brief + parametri…
- **File toccati:** Nuovi: …; Aggiornati: SKILL.md, wiki.md, agente, settings.json, CLAUDE.md
- **Benefici:** Regole consolidate, tassonomia univoca, meno duplicazione, manutenzione centralizzata. Pronto a scalare.
```
*— 4 livelli di nesting, ricopia il contenuto della pagina, dump dei file (li traccia git), "Benefici" ad
aggettivi. Il log fa il lavoro della pagina.*

✓ **Buona** (traccia + puntatori + esito):
```
## [data] record | Consolidamento sistema wiki (fonte unica + tre interfacce)
Le regole del wiki erano duplicate in skill/comando/agente → consolidate in una fonte unica con interfacce sottili.
- **Cosa:** nuovo playbook come fonte unica; skill/comando/agente diventano wrapper che lo leggono.
- **Dove:** il razionale e l'architettura in [[sistema-wiki-fonte-unica]].
- **File chiave:** `.claude/skills/.../wiki-playbook.md` (nuovo).
- **Verifica:** lint A 0/0/0/0.
```
*— lead col perché, bullet piatti, punta alla pagina per il contenuto, chiude con l'esito.*

## Checklist veloce

| Criterio | Domanda da farsi |
|---|---|
| Confine | Sto registrando *cosa è successo* (log) e non *la conoscenza* (→ pagina)? |
| Heading | `<op>` dal vocabolario §6, titolo su **una** cosa? |
| Lead | Apre col **perché/trigger**, non col primo file? |
| Bullet | Piatti, con etichetta, **max 1 livello**? |
| Puntatori | Il contenuto è **linkato** alla pagina, non ricopiato? |
| Rumore | Niente lista-file esaustiva (git) né "Benefici" ad aggettivi? |
| Esito | C'è la riga di verifica (lint/test/commit) se applicabile? |
| Anti-banale | Vale la pena? (meccanico/banale → niente voce) |
