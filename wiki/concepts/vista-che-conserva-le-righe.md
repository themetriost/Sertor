---
title: Una vista che conserva le righe (codice incorporato in un altro formato)
type: concept
tags: [chunking, code-graph, aspnet, razor, webforms, tree-sitter, sertor-core, e7, design]
created: 2026-10-12
updated: 2026-10-12
sources: ["src/sertor_core/services/chunking/aspnet.py", "specs/140-pagine-aspnet/research.md", "specs/140-pagine-aspnet/contracts/page-projection.md", "tests/unit/test_aspnet_projection.py"]
---

# Una vista che conserva le righe

**Il problema.** Un file può contenere codice **dentro un altro formato**: il C# lato server di una pagina
ASP.NET dentro il suo markup, ma anche SQL dentro uno script, codice dentro un notebook o un blocco
Markdown. Per analizzarlo con un parser serve estrarlo; per **citarlo** all'agente servono le righe **del
file originale**. Il modo ovvio — tagliare i frammenti e tenere una tabella di offset per rimapparli — è
codice in più e un posto in più dove sbagliare. E una riga sbagliata è peggio di nessuna riga: rende falsa
ogni citazione (`find_symbol` dice «riga 12» e il metodo sta alla 15).

**La soluzione.** Non estrarre: **proiettare**. Si costruisce una vista del file in cui ogni carattere che
non è codice diventa uno spazio e **ogni ritorno a capo resta dov'è**. La vista ha esattamente le righe
dell'originale, quindi il parser esistente, applicato alla vista intera, restituisce **direttamente** le
righe giuste. Nessuna rimappatura: l'errore non è improbabile, è **impossibile per costruzione**.

È la scelta di E7-FEAT-006 (pagine ASP.NET, `services/chunking/aspnet.py`), misurata sul parser
tree-sitter reale prima di scrivere il codice: pagina con lo script alle righe 3–8 → metodi alle righe 4 e
7, scarto 0.

## Tre viste da una sola scansione

Lo stesso testo serve a tre consumatori con esigenze diverse, e una scansione produce le tre viste insieme:

| Vista | Contiene | Serve a |
|---|---|---|
| `chunk_view` | i blocchi di codice | i chunk sintattici (un chunk per metodo) |
| `graph_view` | i blocchi + le espressioni brevi (`<%= x %>` → `x;`) | gli archi `calls` |
| `markup_view` | il resto, con il codice sbiancato | i chunk del markup, ricercabili |

La separazione evita il **doppio conteggio** (ogni riga di codice compare una sola volta nei chunk) e lascia
alle espressioni brevi il solo ruolo che hanno davvero: dire **chi chiama chi**, non essere un risultato di
ricerca da tre parole.

## La sentinella trasparente

Un metodo scritto fuori da una classe, al livello superiore, per la grammatica C# **non è un metodo** (è una
*local function* dentro un'istruzione globale) e il chunker non lo riconoscerebbe. Si avvolge allora il blocco
in una classe sintetica, `class __page__ { … }`, scritta **sopra** il tag d'apertura: la riga si allunga, non
se ne aggiunge una, quindi la proiezione resta valida. La sentinella **non diventa mai un simbolo**: viene
tolta dai chunk e dal grafo, e il suo nome è sostituito dal nome del file (`Default.Page_Load`).

## Cosa insegna, oltre ASP.NET

- **Se un invariante può essere strutturale, rendilo strutturale.** «Le righe sono giuste» qui non è una
  proprietà da verificare caso per caso: è una conseguenza di come la vista è fatta.
- **Il test dell'invariante va esercitato sul caso che lo mette alla prova.** La prima versione dei test
  restava verde anche togliendo i ritorni a capo dal wrapper, perché in tutte le fixture il tag stava su una
  riga sola: una [[guardia-verde-non-e-una-misura|guardia verde che non poteva diventare rossa]]. Il caso con
  il tag su più righe l'ha resa una misura.
- **Il fallimento si dichiara.** Quando la vista non si analizza (codice malformato, linguaggio non C#), la
  pagina entra come testo e un evento `aspnet_page_degraded` dice quale file e perché, con la riga
  dell'errore **più interno** (quello esterno parte dalla classe sentinella, lontano dal punto rotto).

## Dove si potrebbe riusare

Il meccanismo è generale; oggi ha **un solo** consumatore. Candidati: SQL incorporato in script
(E7-FEAT-003, epica `conoscenza-schema-sql`), le relazioni fra file ASP.NET (E7-FEAT-007), un eventuale
supporto VB.NET. Prima del secondo consumatore non vale estrarlo in un'astrazione (Principio III).

**Vedi anche:** [[chunking-dispatch]] (dove si inserisce) · [[code-graph]] (come la usa il grafo) ·
[[omissione-che-diventa-risposta]] (il difetto che E7-FEAT-006 chiude per ASP.NET).
