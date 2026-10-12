<%@ Page Language="C#" AutoEventWireup="true" CodeBehind="Default.aspx.cs" Inherits="Demo.Default" %>
<%-- Pagina di prova per E7-FEAT-006 --%>
<html>
<script runat="server">
    protected void Page_Load(object sender, EventArgs e)
    {
        BindGrid();
    }
    void Helper() { }
</script>
<body>
<asp:GridView ID="OrdiniGrid" runat="server" />
<h1><%= FormatTitolo() %></h1>
<% foreach (var riga in CaricaRighe()) { %>
  <p><%# Eval("Nome") %></p>
<% } %>
<script runat="server">
    void Secondo()
    {
        Helper();
    }
</script>
</body>
</html>
