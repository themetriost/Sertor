# Quickstart — verificare le pagine ASP.NET nel corpus (140)

Verifica end-to-end **via vehicles** (Principio XI), su un repository di prova fuori dal corpus del progetto.
Sottocomandi verificati con `sertor-rag --help` il 2026-10-12: la navigazione del grafo **non** ha un comando
CLI dedicato (`find_symbol`/`who_calls` sono tool MCP); dalla CLI la si verifica con
`graph-eval validate-ref`, che conferma o smentisce i riferimenti attesi.

```powershell
$sertor = "C:\Workspace\Git\Sertor\.sertor"   # runtime installato del dogfood

# 1. Repository di prova con una pagina WebForms e il suo code-behind
$demo = Join-Path $env:TEMP "aspnet-demo"; New-Item -ItemType Directory -Force $demo | Out-Null
@'
<%@ Page Language="C#" CodeBehind="Default.aspx.cs" Inherits="Demo.Default" %>
<html><body>
<asp:GridView ID="OrdiniGrid" runat="server" />
<script runat="server">
    protected void Page_Load(object sender, EventArgs e)
    {
        BindGrid();
    }
</script>
<p><%= FormatTitolo() %></p>
</body></html>
'@ | Set-Content (Join-Path $demo "Default.aspx") -Encoding utf8
@'
namespace Demo {
    public partial class Default {
        void BindGrid() { }
        string FormatTitolo() { return "Ordini"; }
    }
}
'@ | Set-Content (Join-Path $demo "Default.aspx.cs") -Encoding utf8

# 2. Indicizzazione con un embedder locale (nessuna rete), corpus dedicato
Push-Location $demo
$env:SERTOR_EMBED_PROVIDER = "hash"
uv run --project $sertor sertor-rag index . --corpus aspnetdemo

# 3. Il markup si trova (SC-004): atteso Default.aspx fra i primi 5
uv run --project $sertor sertor-rag search "OrdiniGrid" -k 5 --type code --corpus aspnetdemo

# 4. Il metodo inline e' definito nella pagina (SC-002): atteso confermato
uv run --project $sertor sertor-rag graph-eval validate-ref --relation defines --target Page_Load `
    --corpus aspnetdemo "Default.aspx#Default.Page_Load"

# 5. La pagina chiama i metodi del code-behind (SC-003): attesi confermati
uv run --project $sertor sertor-rag graph-eval validate-ref --relation who_calls --target BindGrid `
    --corpus aspnetdemo "Default.aspx#Default.Page_Load"
uv run --project $sertor sertor-rag graph-eval validate-ref --relation who_calls --target FormatTitolo `
    --corpus aspnetdemo "Default.aspx#Default.aspx"
Pop-Location
```

La riga esatta (scarto 0, SC-002) si legge dal tool MCP `find_symbol("Page_Load")` puntato sullo stesso
corpus, oppure dai test d'integrazione della feature, che la asseriscono.

> Il formato del ref del chiamante-modulo (`Default.aspx#Default.aspx`) va confermato all'implementazione: un
> nodo modulo non ha qualname, e `_hit` usa allora il nome (`qualname or name`). Il task del quickstart lo
> verifica e corregge questa riga se serve.

**Degradazione (SC-005):** aggiungere `Vecchia.aspx` con `<%@ Page Language="VB" %>`, re-indicizzare con `-v`
e verificare sullo stderr l'evento `aspnet_page_degraded` con `reason=server_language` e `path=Vecchia.aspx`.
