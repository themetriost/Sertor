# Contract — Proiezione di una pagina ASP.NET (140)

Contratto **interno al core** (servizio puro, nessun consumatore esterno nuovo). I contratti verso l'esterno —
tool MCP (`search_code`, `find_symbol`, `who_calls`, `get_context`) e CLI (`sertor-rag index/search`) — **non
cambiano forma**: cambia solo cosa contiene il corpus.

## `project_page(text: str, language: str) -> PageProjection`

- **Puro e deterministico:** stesso input → stesso output; nessun I/O, nessun log.
- **Precondizione:** `language ∈ {"webforms", "razor"}`; altrimenti `ValueError` (errore di programmazione, non
  di dati).
- **Postcondizione (invariante delle righe):**
  `view.count("\n") == text.count("\n")` per `chunk_view`, `graph_view`, `markup_view`.
- **Mai eccezioni sui dati:** un markup malformato (tag non chiusi, graffe sbilanciate) produce viste comunque
  valide; l'eventuale codice incompleto emerge come `parse_error` a valle.

### WebForms — cosa finisce in quale vista

| Costrutto | `chunk_view` | `graph_view` | `markup_view` |
|---|---|---|---|
| `<%@ … %>` direttiva | spazi | spazi | resta |
| `<%-- … --%>` commento server | spazi | spazi | spazi |
| `<script runat="server"> … </script>` | `class __page__ {` … `}` | idem | spazi |
| `<% … %>` codice | il codice | il codice | spazi |
| `<%= x %>` `<%: x %>` `<%# x %>` `<%#: x %>` | spazi | `x;` | resta |
| `<%$ … %>` expression builder | spazi | spazi | resta |
| tutto il resto (markup) | spazi | spazi | resta |
| file con direttiva `WebHandler`/`WebService` | tutto dopo la direttiva | idem | spazi |

### Razor — cosa finisce in quale vista

| Costrutto | `chunk_view` | `graph_view` | `markup_view` |
|---|---|---|---|
| `@code { … }`, `@functions { … }` | `class __page__ { … }` | idem | spazi |
| `@{ … }` | ` { … }` con le righe di markup interne sbiancate | idem | spazi (tranne le righe di markup interne, che restano) |
| `@* … *@` commento | spazi | spazi | spazi |
| `@@`, `@` preceduto da carattere alfanumerico (email) | spazi | spazi | resta |
| espressioni inline (`@Model.X`) e direttive (`@page`, `@model`, `@using`) | spazi | spazi | resta |

Il riconoscimento della fine di un blocco Razor segue le graffe ignorando quelle dentro stringhe (`"…"`,
`@"…"`, `'…'`) e commenti (`//`, `/* */`).

## `chunk_document(doc, settings)` — comportamento per `webforms`/`razor`

1. `projection = project_page(doc.text, doc.language)`.
2. Se `server_language` non è C# → evento `aspnet_page_degraded(reason=server_language)`; chunk dimensionali
   dell'intero testo.
3. Se `has_code` → chunk sintattici della `chunk_view` con la grammatica C#; se il parsing ha errori → evento
   `aspnet_page_degraded(reason=parse_error)`; chunk dimensionali dell'intero testo.
4. Altrimenti: chunk sintattici (sentinella rimossa, qualname riscritti) **seguiti** dai chunk dimensionali
   della `markup_view`.

## `extract_graph(...)` — comportamento per `webforms`/`razor`

- Pagina degradata (stessa decisione del chunker, ricalcolata) → solo il nodo `module`, nessun evento.
- Altrimenti visita della `graph_view` con le regole del C#; la sentinella è trasparente (prefisso `Stem`, nessun
  nodo); chiamate fuori da un simbolo attribuite al nodo `module` della pagina.
