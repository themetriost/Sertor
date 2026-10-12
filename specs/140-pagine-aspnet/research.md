# Research — Pagine ASP.NET nel corpus (140)

**Data:** 2026-10-12 · **Spec:** [`spec.md`](spec.md) · **Requisiti:** [`requirements.md`](../../requirements/ingestione-estesa/pagine-aspnet/requirements.md)

Ogni decisione è stata **misurata sul parser reale** (`tree-sitter-language-pack`, grammatica `csharp`,
la stessa già usata per i `.cs`) con due probe in scratchpad, non dedotta. Gli esiti sono citati in ogni voce.

---

## D-1 — Una «vista C#» della pagina, con le stesse righe del file

**Decisione.** La pagina non viene spezzata in frammenti analizzati uno per uno: si costruisce una **vista
proiettata** con **lo stesso numero di righe** del file originale, in cui ogni carattere che non è codice
lato server diventa uno spazio (i `\n` restano). Il parser C# esistente analizza la vista intera e restituisce
**direttamente le righe del file originale**, senza alcuna tabella di rimappatura.

**Perché.** R-2 dei requisiti (righe sbagliate = citazioni false) è il rischio più grave per la qualità resa
all'agente. Una tabella di offset fra frammenti e file è codice in più e un posto in più dove sbagliare; una
vista che conserva le righe **per costruzione** rende l'errore impossibile invece che improbabile.

**Misura (probe 1).** Pagina con `<script runat="server">` alle righe 3–8 e un `foreach` in `<% %>` alle righe
10–12: `method_declaration` a riga 4 e 7 (reali), `global_statement` a riga 10. Righe esatte, scarto 0.

**Alternative scartate.**
- *Frammenti analizzati separatamente + offset:* più codice, e i frammenti di `<% %>` non sono autonomi (un
  `foreach {` si chiude in un blocco successivo) — analizzati isolati darebbero errore.
- *Parser ASP.NET/Razor dedicato:* nessuna grammatica tree-sitter matura nel pack; dipendenza nuova contro
  NFR-1 e Principio III.

## D-2 — I blocchi `<script runat="server">` e `@code`/`@functions` si avvolgono in una classe sentinella

**Decisione.** Nella vista, il tag d'apertura `<script runat="server">` è sostituito da `class __page__ {` e
la chiusura `</script>` da `}`; in Razor la parola chiave `@code` / `@functions` è sostituita da
`class __page__` (la graffa del blocco resta quella originale). La classe sentinella **non diventa mai un
simbolo**: viene rimossa dai chunk e dal grafo, e il suo nome è sostituito dal **nome del file senza
estensioni** nei nomi qualificati (FR-007a, `Default.Page_Load`).

**Perché.** Un metodo scritto fuori da una classe, al livello superiore, è per la grammatica una *local
function* dentro un'istruzione globale, non un `method_declaration`: il chunker non lo riconoscerebbe come
simbolo. Avvolgerlo lo rende un metodo senza toccare il chunker. La sostituzione può allungare la riga del
tag (non aggiunge righe), quindi D-1 resta valida.

**Misura (probe 1 e 2).** WebForms: `class_declaration` → due `method_declaration` alle righe reali. Razor
`@code`: `method_declaration` a riga 5, con l'`invocation_expression` dentro.

**Scartato:** usare direttamente il nome del file come nome di classe (`class Default {`). Un nome di file non è
sempre un identificatore valido (`404.aspx`, `my-page.aspx`), e il grafo mostrerebbe una classe `Default` che
nel sorgente non esiste.

## D-3 — Handler e web service: tutto dopo la direttiva è C#

**Decisione.** Se la direttiva iniziale è `<%@ WebHandler … %>` o `<%@ WebService … %>`, la vista è il file con
la sola direttiva sbiancata: il resto è C# ordinario, con classi vere e nomi qualificati normali (FR-004,
FR-007a). La distinzione si fa **sul contenuto** (il tipo di direttiva), non sull'estensione: nessuna seconda
lista di estensioni da tenere allineata (Principio XIV).

**Misura (probe 2).** Vista `.ashx`: `class_declaration` a riga 3, `method_declaration` a riga 4, chiamata
interna riconosciuta. Nessun errore.

## D-4 — Le righe di markup dentro un blocco Razor `@{ }` si sbiancano

**Decisione.** Dentro un blocco `@{ … }` lo scanner tratta come markup, e sbianca, ogni riga il cui primo
carattere non spazio è `<` seguito da una lettera o da `/` (un tag), e ogni riga che inizia con `@:`. È la
regola con cui Razor stesso decide la transizione codice → markup.

**Perché.** È il caso comune nei `.cshtml` (`<p>@item.Name</p>` dentro un ciclo). **Misura (probe 2):** lo
stesso blocco con la riga di markup lasciata produce `has_error=True` (nodi `ERROR` a riga 4); con la riga
sbiancata `has_error=False` e la chiamata resta riconosciuta. Senza questa regola quasi ogni `.cshtml` reale
finirebbe degradato.

**Limite dichiarato.** Un elemento di markup su più righe il cui testo interno non inizia con `<` resta nella
vista come C#, il parsing fallisce e la pagina è **degradata con evento** (D-6). È il comportamento giusto:
rumoroso, mai silenzioso. Un riconoscimento completo dei tag annidati è fuori da questa feature.

## D-5 — Le espressioni brevi entrano solo nella vista per il grafo

**Decisione.** Si producono **due viste C#**:
- `chunk_view`: blocchi di script, blocchi di codice, blocchi Razor — fonte dei chunk sintattici;
- `graph_view`: la `chunk_view` più le espressioni brevi (`<%= x %>`, `<%: x %>`, `<%# x %>`) scritte come
  istruzioni `x;` — fonte degli archi `calls`.

Il testo delle espressioni resta nella `markup_view`, che è la fonte dei chunk del markup (clarify Q3).

**Misura (probe 2).** `Eval("Nome");` e `FormatPrice(Item.Price);` come istruzioni globali: due
`invocation_expression` riconosciute, nessun errore.

## D-6 — Degradazione: decisa una volta, dichiarata con un evento

**Decisione.** La pagina è **degradata** (chunk dimensionali sull'intero testo originale, nessun simbolo, nessun
arco) quando:
1. la direttiva o il tag di script dichiara un linguaggio diverso da C# (`Language="VB"`) → motivo
   `server_language`;
2. la `chunk_view` analizzata ha errori (`has_error()`) → motivo `parse_error`.

L'evento è `aspnet_page_degraded` (livello WARNING, via `log_event`), con `path`, `reason` e `detail` (il
linguaggio dichiarato o la prima riga dell'errore). Lo emette **il chunker**, che è il primo a decidere;
l'estrazione del grafo ricalcola la stessa proiezione (deterministica) e salta la pagina **senza un secondo
evento**.

**API misurata (probe 1).** Il nodo radice espone `has_error()`: `True` su `class _{ void F( { }`, `False` su
codice valido.

**Errori nella sola `graph_view`.** Se la `chunk_view` è pulita ma un'espressione breve è malformata, gli
archi si estraggono comunque con il recupero d'errore del parser: è la stessa politica best-effort già in uso
per gli archi (`_walk_relations` attraversa i nodi che trova). Non si degrada la pagina per un binding; il caso
è coperto da un test che fissa il comportamento.

## D-7 — Chi chiama dal codice della pagina: la pagina stessa

**Decisione.** Le chiamate fuori da qualunque metodo (istruzioni di `<% %>`, `@{ }` ed espressioni) sono
attribuite al **nodo modulo della pagina** (il suo percorso). Oggi `_walk_relations` scarta le chiamate senza
simbolo racchiudente (`enclosing_id is None`): per le pagine la visita parte con `enclosing_id = path`.

**Perché.** SC-003: `who_calls` su un metodo del code-behind deve restituire la pagina. L'adapter
(`networkx_graph.who_calls` → `_incoming`) restituisce qualunque nodo con un arco `calls` uscente, moduli
compresi: **nessuna modifica all'adapter né alla porta**.

**Confine.** L'attribuzione al modulo vale **solo per le pagine**: per i linguaggi esistenti il comportamento
non cambia (FR-015).

## D-8 — Identità di linguaggio: `webforms` e `razor`

**Decisione.** `_EXT_LANG` mappa `.aspx .ascx .master .asmx .ashx` → `webforms` e `.cshtml .razor` → `razor`.
Le due costanti vivono nel modulo della proiezione e sono **importate** da `ingestion.py` e da
`graph_extraction.py`, non riscritte. In `_REL` le due voci sono **derivate** da quella di `c_sharp`
(`_REL["webforms"] = _REL["razor"] = _REL["c_sharp"]`), così `COVERAGE` le dichiara con le stesse relazioni del
C# senza una seconda copia (FR-009, Principio XIV).

## D-9 — Ordine dei chunk e identità stabili

**Decisione.** Per una pagina non degradata i chunk sono emessi in ordine fisso: prima i chunk sintattici della
`chunk_view` (nell'ordine del chunker esistente), poi i chunk dimensionali della `markup_view`. Gli id restano
`doc_id#index` posizionali come per ogni documento (REQ-010): stesso contenuto → stessi id (FR-014). Il
testo della sentinella (`class __page__`) viene rimosso dal testo dei chunk prima dell'embedding.

## D-10 — BOM e codifica

**Decisione.** Nessun trattamento speciale: `_read_text` legge UTF-8 con `errors="ignore"` e il BOM resta come
primo carattere della prima riga, che nella vista è markup o direttiva e quindi viene sbiancato. Le righe non
cambiano. Un test con BOM lo fissa (edge case della spec).

## D-11 — Documentazione e riconciliatore

**Decisione.** `src/sertor_core/README.md` (sezione *Languages supported*) viene corretto: elenca le famiglie
WebForms e Razor e **toglie** la frase falsa *«any other language falls back without error»*, sostituendola con
la verità (le estensioni fuori elenco non entrano nel corpus; E10-FEAT-079). Poiché quella sezione è prosa che
descrive `_EXT_LANG` (Principio XIV), un test unitario fa da **riconciliatore**: fallisce se un'estensione di
`_EXT_LANG` non compare nel README.

## Estensioni (tracciate, non in questa feature)

| Rinvio | Casa durevole |
|---|---|
| Relazioni pagina ↔ code-behind / master / controlli registrati (REQ-014, *Could*) | **E7-FEAT-007** nel backlog di `ingestione-estesa` (promossa in questo piano) |
| VB.NET (`.aspx` con `Language="VB"`, `.aspx.vb`, `.vbhtml`) | riga roadmap *Nuove funzionalità da discutere*: nessun ospite l'ha chiesto, resta un'idea |
| JavaScript lato client nei `<script>` non server | stessa riga roadmap |
| Dichiarare le estensioni scartate (la classe) | già **E10-FEAT-079** |
