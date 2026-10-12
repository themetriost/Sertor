# Fixture — pagine ASP.NET (specs/140-pagine-aspnet)

Piano-fixture dichiarato (Principio XIII): servono a verificare l'ingestione e l'estrazione del C# lato
server dalle pagine. Le righe attese sono **1-based** e i test le asseriscono: se modifichi un file,
aggiorna questa tabella e i test.

| File | Ruolo | Simboli attesi (qualname → riga) |
|---|---|---|
| `Default.aspx` | WebForms completa: direttiva, commento server, due `<script runat="server">`, `<% %>` su più blocchi, `<%= %>`, `<%# %>` | `Default.Page_Load` → 5 · `Default.Helper` → 9 · `Default.Secondo` → 18 |
| `Default.aspx.cs` | code-behind con namespace a blocco | (C#, invariato dalla feature) |
| `Admin/Default.aspx` | omonima in un'altra cartella | `Default.Page_Load` → 3 |
| `Menu.ascx` | solo markup (`has_code=False`) | — |
| `Site.master` | markup + un `<% %>` | — (istruzione di modulo, chiama `RegistraVisita`) |
| `Api.asmx` | web service: tutto dopo la direttiva è C# | `Api` → 4 · `Api.Saluta` → 6 (il metodo inizia dal suo attributo `[WebMethod]`, come nei `.cs`) |
| `Handler.ashx` | handler: tutto dopo la direttiva è C# | `Handler` → 4 · `Handler.ProcessRequest` → 6 |
| `Index.cshtml` | Razor: `@{ }` con riga di markup interna, `@functions`, email, `@@`, commento `@* *@`, graffe in stringhe e commenti | `Index.CalcolaTitolo` → 11 |
| `Counter.razor` | Blazor: `@code`, `@onclick` nel markup | `Counter.IncrementCount` → 8 |
| `Vecchia.aspx` | `Language="VB"` → degradata, `reason=server_language` | — |
| `Rotta.aspx` | C# malformato → degradata, `reason=parse_error` | — |

La pagina con BOM UTF-8 è costruita dentro il test (il BOM non sopravvive in modo affidabile agli editor).
