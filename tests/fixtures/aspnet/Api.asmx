<%@ WebService Language="C#" Class="Api" %>
using System.Web.Services;

public class Api : WebService
{
    [WebMethod]
    public string Saluta() { return "ciao"; }
}
