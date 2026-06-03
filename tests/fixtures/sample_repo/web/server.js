// File di esempio per i test di chunking sintattico (JavaScript).

const PORT = 8080;

function startServer(port) {
  return `listening on ${port}`;
}

function handleRequest(req) {
  return { status: 200, body: "ok" };
}
