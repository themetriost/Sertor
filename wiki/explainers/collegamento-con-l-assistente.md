---
title: Il collegamento con l'assistente (in parole semplici)
type: explainer
tags: [non-tecnici, mcp, assistente, integrazione, spiegazione]
created: 2026-06-14
updated: 2026-06-14
sources: ["wiki/tech/mcp-server.md", "wiki/concepts/thin-consumer.md"]
---

# Il collegamento con l'assistente

## Il problema

Sertor sa cercare nel progetto, ma da solo non parla con nessuno. Perché serva davvero, un assistente
AI deve poterlo **usare** mentre lavora: chiedergli «trovami il pezzo su X» e ricevere le pagine giuste.
Serve quindi una *presa di corrente standard* a cui l'assistente si attacca.

## L'idea

Sertor espone i suoi strumenti di ricerca attraverso un **collegamento standard** (si chiama MCP). È
come una presa universale: qualunque assistente compatibile ci si attacca e può usare Sertor senza
sapere come è fatto dentro. L'assistente chiede, Sertor cerca e restituisce le pagine con la fonte.

## Perché è importante

- **Le capacità non dipendono da un solo assistente.** Oggi si usa con un certo assistente, domani con
  un altro: la presa è la stessa.
- L'assistente diventa molto più **affidabile**: smette di rispondere "a memoria" e comincia a
  rispondere **guardando davvero dentro il tuo progetto**.
- È un collegamento **locale e privato**: gira sulla tua macchina, non manda il tuo codice su un sito
  pubblico.

## L'immagine

È la presa elettrica a muro: tu non sai (né ti interessa) com'è fatta la centrale, attacchi la spina e
hai corrente. Allo stesso modo l'assistente attacca la "spina" a Sertor e ha la ricerca.

---

*Dettaglio tecnico:* il collegamento è il [[mcp-server|server MCP]]; il principio per cui le interfacce
restano sottili (la libreria è il prodotto) è [[thin-consumer]].
