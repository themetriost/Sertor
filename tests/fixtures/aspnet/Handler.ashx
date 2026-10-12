<%@ WebHandler Language="C#" Class="Handler" %>
using System.Web;

public class Handler : IHttpHandler
{
    public void ProcessRequest(HttpContext context)
    {
        Scrivi(context);
    }

    public bool IsReusable { get { return false; } }
}
